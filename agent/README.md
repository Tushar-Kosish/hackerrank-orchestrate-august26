# Message Notification Router & WhatsApp Digital Twin Agent

This directory contains the AI-powered Message Notification Router and WhatsApp Digital Twin Auto-Responder.

## Architecture

1. **Routing & Persona Generator (`run_agent.py`)**:
   - Classifies incoming messages into `notify`, `digest`, or `mute`.
   - Google Web Search grounding for factual Q&A and search requests.
   - Google Gemini AI API integration (`GEMINI_API_KEY`) for conversational intelligence.
   - Multi-lingual support (English, Hinglish/Punjabi, Spanish).
   - Self-learning memory persistence in `learned_chat_memory.json`.

2. **WhatsApp Web Auto-Responder (`whatsapp_web_bot.py`)**:
   - Automated WhatsApp Web client for live real-time sub-second auto-replies.
   - Strict 1-to-1 turn-taking and group chat exclusion safeguards.

3. **Twilio Webhook Server (`webhook.py`)**:
   - Instant TwiML XML auto-reply endpoint for WhatsApp Sandbox integration.

4. **Web Dashboard (`templates/index.html`, `static/`)**:
   - Modern glassmorphic dashboard for visual message routing and dataset exploration.

## Quickstart

1. Install requirements:

```bash
pip install -r agent/requirements.txt
```

2. Run the routing agent on `dataset/messages.csv`:

```bash
python agent/run_agent.py
```

3. Run the live test simulator:

```bash
python agent/test_sim.py
```

4. Launch the personal WhatsApp Web auto-responder bot:

```bash
python agent/whatsapp_web_bot.py
```

## Output

- Writes `dataset/output.csv` matching the HackerRank challenge specification (`message_id,action,message_type,reason,confidence,evidence_message_ids`).

