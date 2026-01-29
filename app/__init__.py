from flask import Flask
from flask_cors import CORS
import os

from dotenv import load_dotenv

# Loading variables from .env
load_dotenv()

from app.webhook.routes import webhook
from app.data_api.routes import api_data
from app.extensions import mongo


# Creating our flask app
def create_app():

    app = Flask(__name__)

    # Enable CORS
    CORS(app)
    
    # Setting Mongo Connection String
    app.config["MONGO_URI"] = os.getenv("MONGO_CONNECTION_STR")

    mongo.init_app(app)

    # 🔍 PING MONGO to test connection
    try:
        mongo.cx.admin.command("ping")
        print("✅ MongoDB connected successfully")
    except Exception as e:
        print("❌ MongoDB connection failed:", e)
    
    # registering all the blueprints
    app.register_blueprint(webhook)
    app.register_blueprint(api_data)
    
    return app
