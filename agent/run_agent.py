#!/usr/bin/env python3
"""
Rule-based Message Notification Router

Simple baseline that reads dataset/messages.csv and writes dataset/output.csv
with columns: message_id,action,message_type,reason,confidence,evidence_message_ids

This is intentionally lightweight and deterministic so it runs without ML deps.
"""
import os
import csv
import re
from pathlib import Path

try:
    import pandas as pd
except Exception:
    pd = None


KEYWORDS_NOTIFY = [r"\burgent\b", r"\b asap\b", r"\bimmediate\b", r"\bimportant\b", r"\bcall now\b"]
KEYWORDS_PAYMENT = [r"invoice", r"payment", r"due", r"receipt", r"order", r"transaction"]
KEYWORDS_PROMO = [r"sale", r"offer", r"discount", r"promo", r"shop now", r"buy now"]


def matches_any(text, patterns):
    if not text or not isinstance(text, str):
        return False
    t = text.lower()
    for p in patterns:
        if re.search(p, t):
            return True
    return False


def route_message(row, users=None, groups=None, businesses=None, history=None):
    text = row.get("message_text", "") or ""
    media_type = (row.get("media_type") or "").lower()
    conv_type = (row.get("conversation_type") or "").lower()
    forwarded = int(row.get("forwarded_count") or 0)

    evidence = "none"
    # Strong signals
    if matches_any(text, KEYWORDS_NOTIFY):
        return "notify", "urgent", "contains urgent keywords", 0.9, evidence

    if matches_any(text, KEYWORDS_PAYMENT):
        return "notify", "payment", "payment-related content", 0.85, evidence

    if forwarded >= 3:
        return "mute", "forward", "highly-forwarded message", 0.6, evidence

    if conv_type == "business":
        # If user has business history they likely want updates
        uid = row.get("user_id")
        bid = row.get("business_id")
        if businesses is not None and bid in businesses.get("trusted", set()):
            return "notify", "business_update", "trusted business update", 0.8, evidence
        if matches_any(text, KEYWORDS_PROMO) or media_type == "image":
            return "digest", "promotion", "promotion or poster", 0.45, evidence
        return "digest", "business_update", "business message", 0.5, evidence

    if media_type == "image":
        if matches_any(text, KEYWORDS_PROMO):
            return "digest", "promotion", "image poster (looks promotional)", 0.5, evidence
        return "digest", "personal", "image message", 0.4, evidence

    if media_type == "voice":
        # Voice notes tend to be personal; prefer digest unless flagged by text
        return "digest", "personal", "voice note (batched)", 0.4, evidence

    # Default text-based heuristics
    if matches_any(text, KEYWORDS_PROMO):
        return "mute", "promotion", "promotional keywords", 0.35, evidence

    # Short personal greetings
    if len(text.strip()) < 50 and any(w in text.lower() for w in ["hi", "hello", "hey", "good morning", "gm"]):
        return "digest", "greeting", "short greeting", 0.3, evidence

    # Fallback: treat as digest
    return "digest", "unknown", "no strong signal", 0.3, evidence


def process_message_dict(row):
    """Return routing result as a dict for a single incoming message dict.

    Output keys: message_id, action, message_type, reason, confidence, evidence_message_ids
    """
    action, mtype, reason, conf, evidence = route_message(row, businesses=None)
    return {
        "message_id": row.get("message_id", ""),
        "action": action,
        "message_type": mtype,
        "reason": reason,
        "confidence": float(conf),
        "evidence_message_ids": evidence,
    }


def load_optional_csv(path):
    p = Path(path)
    if not p.exists():
        return None
    if pd:
        return pd.read_csv(p)
    # fallback to csv.DictReader
    with p.open("r", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def main():
    base = Path("dataset")
    in_path = base / "messages.csv"
    sample_path = base / "sample_messages.csv"
    out_path = base / "output.csv"

    if not in_path.exists():
        if sample_path.exists():
            in_path = sample_path
        else:
            print("No dataset/messages.csv or dataset/sample_messages.csv found. Exiting.")
            return

    df = None
    if pd:
        df = pd.read_csv(in_path, dtype=str).fillna("")
    else:
        rows = load_optional_csv(in_path)

    # Minimal business trust example: load business_accounts if present
    businesses = {"trusted": set()}
    bus = load_optional_csv(base / "business_accounts.csv")
    if isinstance(bus, list):
        for r in bus:
            if r.get("verified", "").lower() in ("true", "1", "yes"):
                businesses["trusted"].add(r.get("business_id"))
    elif pd is not None and isinstance(bus, pd.DataFrame):
        try:
            trusted = bus[bus["verified"].astype(str).str.lower().isin(["true", "1", "yes"])]["business_id"].astype(str).tolist()
            businesses["trusted"].update(trusted)
        except Exception:
            pass

    # Prepare output
    out_rows = []
    if pd:
        for _, r in df.iterrows():
            row = r.to_dict()
            action, mtype, reason, conf, evidence = route_message(row, businesses=businesses)
            out_rows.append({
                "message_id": row.get("message_id", ""),
                "action": action,
                "message_type": mtype,
                "reason": reason,
                "confidence": float(conf),
                "evidence_message_ids": evidence,
            })
    else:
        for row in rows:
            action, mtype, reason, conf, evidence = route_message(row, businesses=businesses)
            out_rows.append({
                "message_id": row.get("message_id", ""),
                "action": action,
                "message_type": mtype,
                "reason": reason,
                "confidence": float(conf),
                "evidence_message_ids": evidence,
            })

    # Ensure output directory exists
    out_path.parent.mkdir(parents=True, exist_ok=True)
    # Write CSV
    fieldnames = ["message_id", "action", "message_type", "reason", "confidence", "evidence_message_ids"]
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in out_rows:
            writer.writerow(r)

    print(f"Wrote {len(out_rows)} rows to {out_path}")


if __name__ == "__main__":
    main()
