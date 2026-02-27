from flask import Flask
from flask_pymongo import PyMongo
from dotenv import load_dotenv
import os
load_dotenv()
app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)