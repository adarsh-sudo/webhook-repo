from flask import Blueprint, request, jsonify, render_template
from datetime import datetime, timezone
from app.extensions import mongo
from dateutil import parser

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
            "timestamp": datetime.now(timezone.utc)
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
                "timestamp": datetime.now(timezone.utc)
            }
        else:
            document = {
                "request_id": pr["id"],
                "author": pr["user"]["login"],
                "action": "pull_request",
                "from_branch": pr["head"]["ref"],
                "to_branch": pr["base"]["ref"],
                "timestamp": datetime.now(timezone.utc)
            }

    else:
        return jsonify({"message": "Event ignored"}), 200

    mongo.db.events.insert_one(document)

    return jsonify({"message": "Webhook received"}), 200

# Endpoint to retrieve events, with filtering by timestamp (since) after 1st request
@webhook.route('/events', methods=["GET"])
def get_events():
    since = request.args.get("since")

    query = {}

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", ""))
            query = {"timestamp": {"$gt": since_dt}}

        except Exception as e:
            print("PARSE ERROR:", e)

    events_cursor = (
        mongo.db.events
        .find(query, {"_id": 0})
        .sort("timestamp", -1)
        .limit(100)
    )

    events = []
    for event in events_cursor:
        event["timestamp"] = event["timestamp"].isoformat() + "Z"
        events.append(event)
    return jsonify(events)

# Simple home page for displaying the events in a interactive UI(index.html)
@webhook.route("/")
def home():
    return render_template("index.html")
