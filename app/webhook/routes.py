from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timezone
from app.extensions import mongo

webhook = Blueprint('webhook', __name__)


@webhook.route("/health", methods=["GET"])
def health_check():
    return jsonify({
        "status": "Flask is running"
    }), 200


@webhook.route('/receiver', methods=["POST"])
def receiver():
    if request.headers.get("Content-Type") != "application/json":
        return jsonify({"message": "Invalid content type"}), 400

    data = request.get_json()
    event_type = request.headers.get("X-GitHub-Event")

    if event_type == "push":
        document = {
            "request_id": data["head_commit"]["id"],
            "author": data["pusher"]["name"],
            "action": "push",
            "from_branch": None,
            "to_branch": data["ref"].split("/")[-1],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    elif event_type == "pull_request":
        pr = data["pull_request"]

        if data["action"] == "closed" and pr.get("merged"):
            document = {
                "request_id": pr["id"],
                "author": pr["user"]["login"],
                "action": "merge",
                "from_branch": pr["head"]["ref"],
                "to_branch": pr["base"]["ref"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            document = {
                "request_id": pr["id"],
                "author": pr["user"]["login"],
                "action": "pull_request",
                "from_branch": pr["head"]["ref"],
                "to_branch": pr["base"]["ref"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    else:
        return jsonify({"message": "Event ignored"}), 200

    mongo.db.events.insert_one(document)

    return jsonify({"message": "Webhook received"}), 200


@webhook.route('/events', methods=["GET"])
def get_events():
    events = list(mongo.db.events.find({}, {"_id": 0}).sort("timestamp", -1).limit(100))
    return jsonify(events)

# Simple home page for displaying the events in a interactive UI(index.html)
@webhook.route("/")
def home():
    return render_template("index.html")
