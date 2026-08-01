# Message Notification Router (baseline)

This folder contains a small rule-based baseline agent that reads `dataset/messages.csv` and writes `dataset/output.csv` with routing decisions.

Quickstart

1. (Optional) Create a Python environment and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r agent/requirements.txt
```

2. Run the agent:

```bash
python agent/run_agent.py
```

Output

- Writes `dataset/output.csv` containing the required columns.

Notes

- This is a deterministic rule-based baseline. Improve by adding evidence retrieval, multimodal classifiers, or user-personalization.
