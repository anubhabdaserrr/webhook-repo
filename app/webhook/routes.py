from flask import Blueprint, request, abort
from app.extensions import mongo
import hmac
import hashlib
import os
from datetime import datetime, timezone

github_webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET").encode()

webhook = Blueprint('Webhook', __name__, url_prefix='/webhook')

def to_utc(ts: str) -> str:
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    dt_utc = dt.astimezone(timezone.utc)
    return dt_utc.isoformat().replace("+00:00", "Z")

# Webhook endpoint for github to send events to
@webhook.route('/receiver', methods=["POST"])
def receiver():
    
    payload = request.get_json()
    
    # Check validity of Webhook signature

    event = request.headers.get("X-GitHub-Event")
    if not payload:
        return {"error": "No JSON body"}, 400
    
    # Signature header (GitHub-style)
    signature = request.headers.get("X-Hub-Signature-256")
    if signature is None:
        abort(400, "Missing signature")

    # Compute expected signature
    expected = "sha256=" + hmac.new(
        github_webhook_secret,
        request.get_data(),
        hashlib.sha256
    ).hexdigest()

    # Secure compare
    if not hmac.compare_digest(expected, signature):
        abort(401, "Invalid signature")
    
    # print(event)
    
    flag_event = True
    if event == "push":
        if payload["created"] or (not payload["head_commit"]["message"].startswith("Merge pull request #")):
            # This code block will only be exacuted if 1) branch has been created or 2) user made some pushes to a branch
            # The 2nd half of the OR logic ensures that the PUSH request sent by Github, post a merge-request isn't intercepted here.

            if payload["created"]:
                # Github doesn't send branch creation timestamp
                utc_now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            else:
                utc_now = to_utc(payload["head_commit"]["timestamp"])
            db_obj = {
                "request_id": payload["after"],
                # Many users never set a full name on GitHub, therefore we're using username which is always present
                "author": payload["head_commit"]["author"]["username"],
                "action": "PUSH",
                "from_branch": None,
                "to_branch": payload["ref"].replace("refs/heads/", ""),
                "timestamp": utc_now
            }
        else:
            flag_event = False
    elif event == "pull_request" and payload["action"] == "opened":
        db_obj = {
            "request_id": str(payload["pull_request"]["id"]), # or node_id or number
            "author": payload["pull_request"]["user"]["login"],
            "action": "PULL_REQUEST",
            "from_branch": payload["pull_request"]["head"]["ref"],
            "to_branch": payload["pull_request"]["base"]["ref"],
            "timestamp": to_utc(payload["pull_request"]["created_at"])
        }
    elif event == "pull_request" and payload["action"] == "closed":
        # # For MERGE, GitHub sends a pull_request + push. We're intercepting pull_request here, to get the required info
        db_obj = {
            "request_id": str(payload["pull_request"]["id"]),
            "author": payload["pull_request"]["merged_by"]["login"],
            "action": "MERGE",
            "from_branch": payload["pull_request"]["head"]["ref"],
            "to_branch": payload["pull_request"]["base"]["ref"],
            "timestamp": to_utc(payload["pull_request"]["merged_at"])
        }
    else:
        flag_event = False

    if flag_event:
        # Insert document
        result = mongo.db.webhook_events.insert_one(db_obj)
        inserted_id = str(result.inserted_id)
    else:
        inserted_id = None
    
    return {
        "status": "received",
        "id": inserted_id
    }, 200
