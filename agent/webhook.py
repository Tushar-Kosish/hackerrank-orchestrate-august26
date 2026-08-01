"""Flask webhook receiver for WhatsApp (Twilio) sandbox testing.

Receives incoming message POSTs, maps to the agent schema, calls
`run_agent.process_message_dict`, and returns JSON with the routing decision.

For local testing use `ngrok` to expose the Flask port and configure Twilio sandbox
to forward messages to the public URL.
"""
from flask import Flask, request, jsonify
import os
import sys
import threading
import logging
from pathlib import Path

# Ensure the repository root is on sys.path when running this file directly.
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from agent import run_agent
try:
    from twilio.rest import Client as TwilioClient
except Exception:
    TwilioClient = None

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)


def twilio_payload_to_row(form):
    # Twilio sends fields like From, Body, NumMedia, MediaContentType0, etc.
    message_id = form.get("MessageSid") or form.get("SmsSid") or ""
    user_id = form.get("To") or "unknown_user"
    text = form.get("Body", "")
    media_type = ""
    media_id = ""
    # Simple mapping for first media
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
        "sender_user_id": form.get("From"),
        "created_at": "",
        "message_text": text,
        "media_type": media_type,
        "media_id": media_id,
        "forwarded_count": form.get("Forwarded", "0") or "0",
    }
    return row


def process_and_maybe_reply(row, to_number=None):
    try:
        result = run_agent.process_message_dict(row)
        logging.info("Processed message %s -> %s", row.get("message_id"), result.get("action"))
        # If Twilio creds available, send reply asynchronously
        sid = os.environ.get("TWILIO_ACCOUNT_SID")
        token = os.environ.get("TWILIO_AUTH_TOKEN")
        from_number = os.environ.get("TWILIO_FROM_NUMBER")
        if sid and token and from_number and TwilioClient is not None and to_number:
            client = TwilioClient(sid, token)
            body = f"Action: {result['action']}; Type: {result['message_type']}; Reason: {result['reason']}"
            try:
                client.messages.create(body=body, from_=from_number, to=to_number)
                logging.info("Sent reply to %s", to_number)
            except Exception as e:
                logging.exception("Failed to send Twilio reply: %s", e)
        return result
    except Exception:
        logging.exception("Error processing message")
        return None


@app.route("/webhook", methods=["POST"])
def webhook():
    form = request.form or {}
    row = twilio_payload_to_row(form)
    to_number = form.get("From")
    # Spawn background thread to process the message so the webhook responds quickly
    thread = threading.Thread(target=process_and_maybe_reply, args=(row, to_number), daemon=True)
    thread.start()
    # Immediate acknowledgement to the sender system
    return jsonify({"status": "accepted", "message_id": row.get("message_id")})


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
