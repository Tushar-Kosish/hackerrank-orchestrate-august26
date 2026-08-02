"""Live Test Simulator — full edge-case coverage for Tushar's Persona + Routing Engine."""
import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))
from agent import run_agent

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 1: PERSONA CHAT REPLY TESTS
# ═══════════════════════════════════════════════════════════════════════════════
persona_cases = [
    # Basic greetings
    ("hi",                          "Rahul",      "personal"),
    ("hey bro",                     "Vikas",      "personal"),
    ("hola amigo como estas",       "Carlos",     "personal"),
    # Location — MUST reply with location, not greeting
    ("kahan h bro",                 "Aman",       "personal"),
    ("where are you bro?",          "Dev",        "personal"),
    # Activity
    ("kya kr rha h yaar",           "Ravi",       "personal"),
    ("what are you doing?",         "Sam",        "personal"),
    # Gaming
    ("aaja BGMI khele free h kya",  "Vikas",      "personal"),
    # Food
    ("bhai khana khaya?",           "Rahul",      "personal"),
    ("bro did you eat yet?",        "Dev",        "personal"),
    # Plans / hangout
    ("chal bahar chalte h aaj",     "Aman",       "personal"),
    ("bro let's meet this weekend", "Sam",        "personal"),
    # Emotional — sad
    ("bhai mood kharab h tension",  "Amit",       "personal"),
    ("feeling low today man",       "Dev",        "personal"),
    # Emotional — sick
    ("bimar hu fever h yaar",       "Rohan",      "personal"),
    ("bro i'm sick, bad headache",  "Sam",        "personal"),
    # Emotional — excited
    ("exam clear ho gaya yaaar!!!", "Rohit",      "personal"),
    ("bro i got selected!! 🎉",     "Dev",        "personal"),
    # Emotional — miss you
    ("bohot din ho gaye miss u bro","Simran",     "personal"),
    ("long time bro, miss you man", "Dev",        "personal"),
    # Anger
    ("yaar bahut gussa h mujhe",    "Aman",       "personal"),
    ("so annoyed bro ugh",          "Sam",        "personal"),
    # Sorry
    ("bhai sorry yaar, galti hui",  "Rahul",      "personal"),
    ("bro sorry for yesterday",     "Dev",        "personal"),
    # Sleep / night
    ("chal so ja yaar raat ho gyi", "Aman",       "personal"),
    ("gn bro, sleep tight",         "Sam",        "personal"),
    # Morning
    ("good morning bhai!",          "Rahul",      "personal"),
    ("gm bro 🌅",                   "Dev",        "personal"),
    # Study / exam stress
    ("bhai paper kal h, padh rha?", "Amit",       "personal"),
    ("bro exam tomorrow, stressed", "Dev",        "personal"),
    # Payments
    ("gpay pe 500 bhej diye dekh",  "Karan",      "personal"),
    # Urgent — NOTIFY routing
    ("URGENT call me back NOW",     "Mom",        "personal"),
    # Spam — MUTE, NO reply
    ("50% off click now buy",       "HDFC Promo", "business_promo"),
    # Thanks / goodbye
    ("thanks bro, you're the best", "Dev",        "personal"),
    ("bye bro, nikal rha hu",       "Aman",       "personal"),
]

# ═══════════════════════════════════════════════════════════════════════════════
# SECTION 2: ROUTING ENGINE TESTS — verify action + message_type
# ═══════════════════════════════════════════════════════════════════════════════
routing_cases = [
    # (row_dict, expected_action, expected_message_type, label)
    (
        {"message_id": "rt1", "user_id": "u1", "conversation_type": "personal",
         "sender_user_id": "s1", "message_text": "Hey, are we still on for lunch?",
         "media_type": "", "forwarded_count": "0"},
        "digest", "personal", "Personal lunch question → digest/personal"
    ),
    (
        {"message_id": "rt2", "user_id": "u1", "conversation_type": "personal",
         "sender_user_id": "s2", "message_text": "URGENT: Please call me back asap about the meeting.",
         "media_type": "", "forwarded_count": "0"},
        "notify", "urgent", "Urgent message → notify/urgent"
    ),
    (
        {"message_id": "rt3", "user_id": "u2", "conversation_type": "business",
         "business_id": "b1", "sender_user_id": "",
         "message_text": "Your invoice #12345 is due tomorrow.",
         "media_type": "", "forwarded_count": "0"},
        "notify", "payment", "Verified biz invoice → notify/payment"
    ),
    (
        {"message_id": "rt4", "user_id": "u3", "conversation_type": "group",
         "group_id": "g1", "sender_user_id": "s3",
         "message_text": "Great sale! 50% OFF - shop now!",
         "media_type": "image", "media_id": "img1", "forwarded_count": "1"},
        "mute", "promotion", "Group promo + image + forwarded → mute/promotion"
    ),
    (
        {"message_id": "rt5", "user_id": "u4", "conversation_type": "personal",
         "sender_user_id": "s4", "message_text": "Forwarded many times",
         "media_type": "", "forwarded_count": "5"},
        "mute", "spam", "Heavily forwarded (5x) → mute/spam"
    ),
    (
        {"message_id": "rt6", "user_id": "u1", "conversation_type": "personal",
         "sender_user_id": "s5", "message_text": "",
         "media_type": "voice", "media_id": "voice1", "forwarded_count": "0"},
        "digest", "personal", "Voice note no text → digest/personal"
    ),
    (
        {"message_id": "rt7", "user_id": "u1", "conversation_type": "group",
         "group_id": "g2", "sender_user_id": "s6",
         "message_text": "hi", "media_type": "", "forwarded_count": "0"},
        "digest", "greeting", "Group 'hi' → digest/greeting"
    ),
    (
        {"message_id": "rt8", "user_id": "u5", "conversation_type": "business",
         "business_id": "b2", "sender_user_id": "",
         "message_text": "Exclusive offer just for you!",
         "media_type": "image", "media_id": "img2", "forwarded_count": "0"},
        "mute", "promotion", "Unverified biz + promo image → mute/promotion"
    ),
    # Extra: scam detection
    (
        {"message_id": "rt9", "user_id": "u1", "conversation_type": "personal",
         "sender_user_id": "s99", "message_text": "Congratulations! You have won a lottery. Click this link to claim prize.",
         "media_type": "", "forwarded_count": "0"},
        "mute", "scam", "Scam lottery message → mute/scam"
    ),
    # Extra: event/meeting
    (
        {"message_id": "rt10", "user_id": "u1", "conversation_type": "personal",
         "sender_user_id": "s1", "message_text": "Team meeting tomorrow at 10am, join the call",
         "media_type": "", "forwarded_count": "0"},
        "notify", "event", "Meeting tomorrow → notify/event"
    ),
    # Extra: forwarded once (non-promo)
    (
        {"message_id": "rt11", "user_id": "u1", "conversation_type": "personal",
         "sender_user_id": "s1", "message_text": "Check this funny video out",
         "media_type": "", "forwarded_count": "2"},
        "digest", "forward", "Forwarded content (2x) → digest/forward"
    ),
    # Extra: empty message, no media
    (
        {"message_id": "rt12", "user_id": "u1", "conversation_type": "personal",
         "sender_user_id": "s1", "message_text": "",
         "media_type": "", "forwarded_count": "0"},
        "digest", "unknown", "Empty message → digest/unknown"
    ),
]


# ═══════════════════════════════════════════════════════════════════════════════
# RUN SECTION 1: PERSONA TESTS
# ═══════════════════════════════════════════════════════════════════════════════
print("=" * 76)
print("  SECTION 1: PERSONA CHAT REPLY TESTS — Tushar's Digital Twin")
print("=" * 76)

ok1 = 0
fails1 = []
for msg, sender, ctype in persona_cases:
    row = {
        "message_id": "sim_1",
        "user_id": sender,
        "conversation_type": ctype,
        "message_text": msg,
        "media_type": "",
        "forwarded_count": "0"
    }
    res = run_agent.process_message_dict(row)
    reply = res["chat_reply"]
    action = res["action"].upper()

    flag = ""
    if action == "MUTE" and reply:
        flag = " ⚠️  BUG: MUTED msg should have NO reply!"
        fails1.append(msg)
    elif action != "MUTE" and not reply:
        flag = " ⚠️  BUG: Non-muted msg has EMPTY reply!"
        fails1.append(msg)
    else:
        ok1 += 1

    print(f"\n[{sender}] \"{msg}\"")
    print(f"  Action : {action} | Reply: \"{reply}\"{flag}")

print("\n" + "=" * 76)
print(f"  Section 1 Results: {ok1}/{len(persona_cases)} PASSED")
if fails1:
    print("  FAILED cases:")
    for f in fails1:
        print(f"    - \"{f}\"")
print("=" * 76)


# ═══════════════════════════════════════════════════════════════════════════════
# RUN SECTION 2: ROUTING ENGINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 76)
print("  SECTION 2: ROUTING ENGINE TESTS — Action + Message Type Accuracy")
print("=" * 76)

ok2 = 0
fails2 = []
for row_dict, exp_action, exp_mtype, label in routing_cases:
    res = run_agent.process_message_dict(row_dict)
    got_action = res["action"]
    got_mtype = res["message_type"]

    passed = got_action == exp_action and got_mtype == exp_mtype
    if passed:
        ok2 += 1
        status = "✅"
    else:
        fails2.append(label)
        status = "❌"

    print(f"\n  {status} {label}")
    print(f"    Expected: {exp_action}/{exp_mtype}")
    print(f"    Got:      {got_action}/{got_mtype}  (conf={res['confidence']}, reason={res['reason'][:50]})")

print("\n" + "=" * 76)
print(f"  Section 2 Results: {ok2}/{len(routing_cases)} PASSED")
if fails2:
    print("  FAILED cases:")
    for f in fails2:
        print(f"    - {f}")
print("=" * 76)


# ═══════════════════════════════════════════════════════════════════════════════
# OVERALL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
total_ok = ok1 + ok2
total_cases = len(persona_cases) + len(routing_cases)
print(f"\n\n{'=' * 76}")
print(f"  OVERALL: {total_ok}/{total_cases} PASSED")
if fails1 or fails2:
    print(f"  Total Failures: {len(fails1) + len(fails2)}")
print("=" * 76)
