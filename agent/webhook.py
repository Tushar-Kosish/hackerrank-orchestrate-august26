"""Flask webhook receiver and Web Dashboard for WhatsApp Message Notification Router.

Provides:
- Web UI dashboard at `/` for interactive testing and dataset exploration.
- `/api/dataset` endpoint for fetching dataset message predictions and stats.
- `/api/route` POST endpoint for real-time routing evaluation.
- `/webhook` POST receiver returning TwiML XML for instant WhatsApp replies.
"""
from flask import Flask, request, jsonify, render_template, send_from_directory, Response
import os
import sys
import logging
import csv
from pathlib import Path

# Ensure the repository root is on sys.path when running this file directly.
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from agent import run_agent

app = Flask(__name__, template_folder="templates", static_folder="static")
logging.basicConfig(level=logging.INFO)

# In-memory live message log for WhatsApp incoming traffic
live_incoming_messages = []


def twilio_payload_to_row(form):
    message_id = form.get("MessageSid") or form.get("SmsSid") or f"msg_{len(live_incoming_messages)+1}"
    user_id = form.get("To") or "unknown_user"
    text = form.get("Body", "")
    media_type = ""
    media_id = ""
    if int(form.get("NumMedia", "0")) > 0:
        content_type = form.get("MediaContentType0", "")
        if content_type.startswith("image"):
            media_type = "image"
        elif content_type.startswith("audio"):
            media_type = "voice"
        media_id = form.get("MediaUrl0", "")

    row = {
        "message_id": message_id,
        "user_id": user_id,
        "conversation_type": "personal",
        "group_id": "",
        "business_id": "",
        "sender_user_id": form.get("From") or "WhatsApp User",
        "created_at": "",
        "message_text": text,
        "media_type": media_type,
        "media_id": media_id,
        "forwarded_count": form.get("Forwarded", "0") or "0",
    }
    return row


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/dataset", methods=["GET"])
def get_dataset():
    dataset_dir = repo_root / "dataset"
    messages_file = dataset_dir / "messages.csv"
    if not messages_file.exists():
        messages_file = dataset_dir / "sample_messages.csv"

    messages = []
    stats = {"total": 0, "notify": 0, "digest": 0, "mute": 0}

    # First add live WhatsApp messages
    for item in live_incoming_messages:
        messages.append(item)
        act = (item.get("action") or "digest").lower()
        stats["total"] += 1
        if act in stats:
            stats[act] += 1

    # Then append CSV dataset
    if messages_file.exists():
        with open(messages_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                res = run_agent.process_message_dict(row)
                combined = {**row, **res}
                messages.append(combined)
                act = (res.get("action") or "digest").lower()
                stats["total"] += 1
                if act in stats:
                    stats[act] += 1

    return jsonify({"messages": messages, "stats": stats})


@app.route("/api/route", methods=["POST"])
def route_api():
    data = request.get_json(force=True, silent=True) or request.form.to_dict() or {}
    result = run_agent.process_message_dict(data)
    return jsonify(result)


@app.route("/webhook", methods=["GET", "POST"])
def webhook():
    form = request.form or request.args or {}
    row = twilio_payload_to_row(form)
    result = run_agent.process_message_dict(row)

    # Track in live list
    combined = {**row, **result}
    live_incoming_messages.insert(0, combined)

    action = (result.get("action") or "digest").upper()
    chat_reply = result.get("chat_reply") or "Thanks for reaching out!"

    xml_response = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Message>{chat_reply}</Message>
</Response>"""

    logging.info("WhatsApp Webhook triggered: %s -> %s", row.get("message_text"), action)
    return Response(xml_response, mimetype="text/xml")


@app.route("/media/<path:filename>")
def serve_media(filename):
    media_dir = repo_root / "dataset" / "media"
    return send_from_directory(media_dir, filename)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Notification Router Web Dashboard on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
