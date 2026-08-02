# HackerRank Orchestrate — Message Notification Router & WhatsApp Digital Twin AI

An AI-powered multimodal message routing and persona auto-responder system built for the **HackerRank Orchestrate Challenge**.

This system evaluates incoming WhatsApp messages in real-time to determine whether a message should:
- `notify`: Interrupt the user immediately for high-priority or urgent events
- `digest`: Batch for later review (low-priority personal, group, or routine messages)
- `mute`: Suppress low-value, promotional, repetitive, spam, or scam messages

It also features a **Google Gemini AI-powered Digital Twin Engine** with **Live Google Web Search Grounding** to automatically handle conversational chat replies on WhatsApp.

---

## 📋 Problem Statement Reference

For the full participant-facing challenge specification, rules, and problem details, see [problem_statement.md](file:///c:/Users/Tushar%20kosish/hacker%20rank/hackerrank-orchestrate-august26/problem_statement.md).

---

## 🏗️ System Architecture & Key Components

```
                ┌────────────────────────────────────────────────────────┐
                │               Incoming Multimodal Message               │
                └───────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
                ┌────────────────────────────────────────────────────────┐
                │          Message Routing Cascade Engine                │
                │                 (agent/run_agent.py)                   │
                └──────┬────────────────────┬────────────────────┬───────┘
                       │                    │                    │
                       ▼                    ▼                    ▼
                ┌──────────────┐     ┌──────────────┐     ┌──────────────┐
                │    NOTIFY    │     │    DIGEST    │     │     MUTE     │
                │(Immediate UI)│     │(Batched Queue│     │ (Suppressed) │
                └──────┬───────┘     └──────┬───────┘     └──────────────┘
                       │                    │
                       └──────────┬─────────┘
                                  │
                                  ▼
                ┌────────────────────────────────────────────────────────┐
                │            Conversational Persona Generator            │
                │        (Google Gemini AI + Google Search API)          │
                └───────────────────────────┬────────────────────────────┘
                                            │
                                            ▼
                ┌────────────────────────────────────────────────────────┐
                │          WhatsApp Web Bot & Twilio Webhook             │
                │      (whatsapp_web_bot.py / agent/webhook.py)         │
                └────────────────────────────────────────────────────────┘
```

### Core Components inside `agent/`

1. **Routing & Persona Generator ([run_agent.py](file:///c:/Users/Tushar%20kosish/hacker%20rank/hackerrank-orchestrate-august26/agent/run_agent.py))**:
   - **Cascade Router**: Evaluates scam, promo, payment, event, urgent, voice note, and group signals.
   - **Google Search Grounding (`perform_google_search`)**: Answers factual Q&A, weather, scores, and news inquiries using live web search.
   - **Google Gemini AI API Integration (`call_gemini_api`)**: Generates 1-line authentic conversational friend replies using Google Gemini models (`gemini-1.5-flash`).
   - **Multi-Lingual Engine**: Automatic language matching for English, Hinglish/Punjabi, and Spanish.
   - **Self-Learning Memory Cache (`learned_chat_memory.json`)**: Persists learned Q&A pairs for offline execution.

2. **WhatsApp Web Auto-Responder ([whatsapp_web_bot.py](file:///c:/Users/Tushar%20kosish/hacker%20rank/hackerrank-orchestrate-august26/agent/whatsapp_web_bot.py))**:
   - Real-time WhatsApp Web automation for sub-second auto-replies.
   - Safeguards: Strict 1-to-1 turn-taking, incoming bubble isolation (`message-in`), and group chat exclusion.

3. **Twilio Webhook Endpoint ([webhook.py](file:///c:/Users/Tushar%20kosish/hacker%20rank/hackerrank-orchestrate-august26/agent/webhook.py))**:
   - Instant TwiML XML response server for Twilio WhatsApp Sandbox testing.

4. **Live Test Simulator ([test_sim.py](file:///c:/Users/Tushar%20kosish/hacker%20rank/hackerrank-orchestrate-august26/agent/test_sim.py))**:
   - Comprehensive test suite covering 47 test cases across persona chat and routing engine rules.

---

## 🚀 Quickstart & Execution

### 1. Installation
Install project dependencies:

```bash
pip install -r agent/requirements.txt
```

### 2. Process Dataset Messages
Run the main router to evaluate `dataset/messages.csv` and generate `dataset/output.csv`:

```bash
python agent/run_agent.py
```

### 3. Run Test Suite
Run the 47-test simulation suite:

```bash
python agent/test_sim.py
```

### 4. Launch WhatsApp Web Auto-Responder Bot
To run the real-time WhatsApp Web digital twin auto-responder:

```bash
python agent/whatsapp_web_bot.py
```

---

## 📁 Repository Structure

```text
hackerrank-orchestrate-august26/
├── AGENTS.md                   # Single source of truth & rules for AI coding agents
├── README.md                   # Project overview & system documentation (this file)
├── problem_statement.md        # Official HackerRank challenge specification
├── agent/                      # Core AI routing agent & WhatsApp automation
│   ├── run_agent.py            # Master router, Gemini model & Google Search engine
│   ├── whatsapp_web_bot.py     # Live WhatsApp Web auto-responder bot
│   ├── webhook.py              # Flask server & Twilio WhatsApp webhook endpoint
│   ├── test_sim.py             # 47-case simulation test suite
│   ├── package_submission.py   # Submission packaging helper script
│   ├── learned_chat_memory.json# Self-learned Q&A persistent memory store
│   └── requirements.txt        # Python package dependencies
└── dataset/                    # Input dataset, context files & submission target
    ├── messages.csv            # Input messages to route
    ├── output.csv              # Required submission file output
    ├── sample_messages.csv     # Example predictions & schema reference
    ├── users.csv               # User notification preferences & behavior
    ├── groups.csv              # Group chat metadata
    ├── group_members.csv       # Group member roles & mute settings
    ├── business_accounts.csv   # Business senders & verification status
    ├── user_business_history.csv # User-business transaction history
    ├── message_history.csv     # Historical message records
    ├── message_events.csv      # User reactions (opened, dismissed, muted, reported)
    ├── images.csv              # Image media references
    ├── voice_notes.csv         # Voice note media references
    ├── daily_notification_summary.csv
    └── media/                  # Audio and image media files
```

---

## 📊 Output Schema Contract

The system generates `dataset/output.csv` matching the required HackerRank contract:

```text
message_id,action,message_type,reason,confidence,evidence_message_ids
```

| Column | Allowed Values / Format | Description |
|---|---|---|
| `message_id` | String | Unique message ID |
| `action` | `notify`, `digest`, `mute` | Routing action |
| `message_type` | `personal`, `urgent`, `event`, `payment`, `business_update`, `promotion`, `greeting`, `forward`, `spam`, `scam`, `unknown` | Best-fit message category |
| `reason` | String | Short human-readable explanation |
| `confidence` | Float (`0.0` to `1.0`) | Calibration score |
| `evidence_message_ids` | Semicolon-separated IDs or `none` | Historical evidence linkage |

---

## 👥 Contributors

- **Tushar Kosish** ([@Tushar-Kosish](https://github.com/Tushar-Kosish)) — Creator & Lead Developer

