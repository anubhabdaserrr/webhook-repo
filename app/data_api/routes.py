from flask import Blueprint, request, abort
from app.extensions import mongo
from datetime import datetime, timezone
from app.extensions import mongo

api_data = Blueprint('APIData', __name__, url_prefix='/data-api')

# Endpoint to fetch latest git activity
@api_data.route('/', methods=["GET"])
def get_data():

    # Get doc with latest timestamp
    doc = mongo.db.webhook_events.find_one(
        {},
        sort=[("timestamp", -1)]
    )

    if doc:
        doc["_id"] = str(doc["_id"])

    return doc, 200