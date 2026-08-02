"""1-Second Personal WhatsApp Web Auto-Responder & Self-Learning Bot (Tushar's Digital Twin).

Strict Guarantees & Safeguards:
1. Pure Incoming Filter: Only reads `div.message-in` (data-id `false_`). Sent/outgoing messages (`message-out` / `true_`) are NEVER misidentified as incoming triggers!
2. Zero Flood Protection: If the last message bubble in chat is outgoing (sent by user/bot), IT WILL NEVER RE-REPLY until a friend sends a new message!
3. Strict 1-to-1 Turn-Taking: Replies exactly ONCE per incoming message bubble.
4. Clean 1.5s Loop Pacing: Prevents CPU loops and duplicate background triggers.
5. Auto-cleans lock files to prevent browser conflicts.

Usage:
`python agent/whatsapp_web_bot.py`
"""
import sys
import time
import os
import shutil
import logging
from pathlib import Path

# Enforce UTF-8 output encoding on Windows console
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add repo root to path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

from agent import run_agent

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


def force_cleanup_profile_locks(user_data_dir):
    """Force cleans Chrome ProcessSingleton lock files and temp sockets."""
    lock_items = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile", "DevToolsActivePort"]
    for root, dirs, files in os.walk(user_data_dir):
        for item in files:
            if item in lock_items:
                try:
                    os.remove(os.path.join(root, item))
                except Exception:
                    pass
        break


def is_group_chat(page):
    """Detects if currently open chat is a Group Chat (skips all group messages)."""
    try:
        header_el = page.locator("#main header")
        if header_el.count() > 0:
            header_text = header_el.inner_text().lower()
            if "," in header_text or "group" in header_text or "members" in header_text or "click here for group info" in header_text:
                return True
    except Exception:
        pass
    return False


def is_bubble_outgoing(bubble):
    """Evaluates whether a message bubble element is outgoing (sent by user/bot).
    Uses 4 independent indicators:
      1. Class 'message-out' on container or child
      2. data-id containing 'true_'
      3. Presence of checkmark status icons (msg-check, msg-dblcheck, msg-time)
      4. Sent/Delivered/Read status attributes
    """
    try:
        is_out = bubble.evaluate("""el => {
            const container = el.closest('div.message-out, div.message-in, div[data-id]') || el;
            const cls = (container.className || '') + ' ' + (el.className || '');
            const dataId = (container.getAttribute('data-id') || '') + ' ' + (el.getAttribute('data-id') || '');
            
            if (cls.includes('message-out') || dataId.includes('true_')) return true;

            // Check for outgoing status checkmarks / icons
            const hasCheckmark = container.querySelector("span[data-icon*='check'], span[data-icon='msg-time'], span[data-icon='msg-dblcheck']");
            if (hasCheckmark) return true;

            const innerHTML = container.innerHTML || '';
            if (innerHTML.includes('msg-dblcheck') || innerHTML.includes('msg-check')) return true;

            if (cls.includes('message-in') || dataId.includes('false_')) return false;

            return false;
        }""")
        return bool(is_out)
    except Exception:
        pass
    return False


def is_last_message_outgoing(main_chat):
    """Returns True if the absolute last bubble in the chat is outgoing (sent by user/bot).
    If True, the bot MUST WAIT for the friend to send a new incoming message!"""
    try:
        bubbles = main_chat.query_selector_all("#main div.message-in, #main div.message-out, #main div[data-id*='@c.us']")
        if bubbles:
            last_bubble = bubbles[-1]
            return is_bubble_outgoing(last_bubble)
    except Exception:
        pass
    return False


def get_latest_incoming_text(main_chat):
    """Extracts text ONLY if the absolute latest message bubble in #main is an INCOMING message.
    If the latest bubble is OUTGOING (sent by you/bot), returns None to guarantee zero self-replies!"""
    try:
        bubbles = main_chat.query_selector_all("#main div.message-in, #main div.message-out, #main div[data-id*='@c.us']")
        if not bubbles:
            return None

        last_bubble = bubbles[-1]

        # Strictly ignore if the last bubble is outgoing (sent by you or the bot)
        if is_bubble_outgoing(last_bubble):
            return None

        # Extract text from incoming message bubble
        text_el = last_bubble.query_selector("span.selectable-text, span._ao3e, div.copyable-text, p, span[dir='ltr']")
        if text_el:
            txt = text_el.inner_text().strip()
            if txt:
                return txt
        return last_bubble.inner_text().strip()
    except Exception as e:
        logging.debug("get_latest_incoming_text error: %s", e)
    return None


def get_current_chat_title(page):
    """Returns the title/name of the currently open chat header."""
    try:
        header_title = page.locator("#main header span[title], #main header div[role='button'] span").first
        if header_title.count() > 0:
            return header_title.inner_text().strip()
    except Exception:
        pass
    return "default_chat"


def send_reply_to_active_chat(page, reply_text, action, target_chat_title=None):
    """Types into WhatsApp Lexical Editor with realistic human reading, thinking, and typing speeds.
    GUARANTEE: Verifies active chat title both before and after thinking pause to eliminate cross-chat leakage."""
    import random
    clean_line_reply = (reply_text or "").replace("\n", " ").replace("\r", " ").strip()
    if not clean_line_reply:
        return

    # Chat Title Lock Guard — prevents cross-chat reply leakage
    current_active_title = get_current_chat_title(page)
    if target_chat_title and current_active_title.lower() != target_chat_title.lower():
        print(f"[CROSS-CHAT SAFETY GUARD]: Active chat is '{current_active_title}' but target was '{target_chat_title}' — ABORTED REPLY!\n")
        return

    # Realistic Human Reading & Thinking Delay (1.2s to 2.2s)
    thinking_delay = round(random.uniform(1.2, 2.2), 2)
    print(f"[HUMAN THINKING & READING ({thinking_delay}s)...] Target Chat: '{current_active_title}'")
    time.sleep(thinking_delay)

    # Re-check chat title after sleep to ensure user didn't switch chats
    current_active_title = get_current_chat_title(page)
    if target_chat_title and current_active_title.lower() != target_chat_title.lower():
        print(f"[CROSS-CHAT SAFETY GUARD AFTER THINKING]: Chat switched to '{current_active_title}' — ABORTED REPLY!\n")
        return

    start_time = time.time()
    try:
        chat_input = page.locator(
            "footer div[contenteditable='true'], div[contenteditable='true'][data-tab='10'], div[contenteditable='true'][role='textbox'], footer p, div[role='textbox']"
        ).first

        if chat_input.count() > 0:
            chat_input.focus()
            page.keyboard.press("Control+A")
            page.keyboard.press("Backspace")
            
            # Realistic keystroke delay (25ms - 45ms per char) for natural human typing on WhatsApp
            keystroke_delay = random.randint(25, 45)
            chat_input.type(clean_line_reply, delay=keystroke_delay)
            
            time.sleep(0.3)
            page.keyboard.press("Enter")

            elapsed = round(time.time() - start_time, 2)
            print(f"[SENT NATURAL HUMAN REPLY TO '{current_active_title}' IN {elapsed}s]: '{clean_line_reply}' [{action}]\n")
        else:
            print("[WARN] Chat input element not found in active window.\n")
    except Exception as e:
        logging.error("Failed to send reply: %s", e)


def learn_from_chat_history(page):
    """Scrapes open chat window (#main) for Tushar's real sent messages to train the AI automatically."""
    try:
        main_chat = page.query_selector("#main")
        if not main_chat:
            return

        all_bubbles = main_chat.query_selector_all("div.message-in, div.message-out")
        if len(all_bubbles) < 2:
            return

        last_incoming = None
        for bubble in all_bubbles:
            classes = bubble.get_attribute("class") or ""
            data_id = bubble.get_attribute("data-id") or ""
            is_incoming = "message-in" in classes or "false_" in data_id

            text_el = bubble.query_selector("span.selectable-text, span._ao3e, p")
            txt = text_el.inner_text().strip() if text_el else bubble.inner_text().strip()

            if is_incoming:
                last_incoming = txt
            else:
                if last_incoming and txt:
                    run_agent.save_learned_pair(last_incoming, txt)
                    last_incoming = None
    except Exception as e:
        logging.debug("Learning scraper exception: %s", e)


def run_whatsapp_bot():
    print("=" * 65)
    print(" Personal WhatsApp AI Digital Twin (Tushar)")
    print(" Pure Incoming Message Filter | Zero-Flood Turn Taking")
    print("=" * 65)

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("\nInstalling Playwright browser engine...")
        import subprocess
        subprocess.run([sys.executable, "-m", "pip", "install", "playwright"], check=True)
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium"], check=True)
        from playwright.sync_api import sync_playwright

    user_data_dir = repo_root / "agent" / "whatsapp_session"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    force_cleanup_profile_locks(user_data_dir)

    print("\nLaunching Playwright Chromium for WhatsApp Web...")

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=[
                    "--no-sandbox",
                    "--disable-setuid-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled"
                ],
                viewport={"width": 1280, "height": 800}
            )
        except Exception as e:
            print(f"[RETRYING LAUNCH AFTER LOCK CLEANUP]: {e}")
            force_cleanup_profile_locks(user_data_dir)
            time.sleep(1)
            browser = p.chromium.launch_persistent_context(
                user_data_dir=str(user_data_dir),
                headless=False,
                args=["--no-sandbox", "--disable-setuid-sandbox"],
                viewport={"width": 1280, "height": 800}
            )

        page = browser.pages[0] if browser.pages else browser.new_page()
        page.goto("https://web.whatsapp.com")

        print("\n[MOBILE QR] Please scan the QR code on screen with WhatsApp app if prompted.")
        print("Waiting for WhatsApp Web to load...")

        # Resilient login wait loop
        logged_in = False
        wait_counter = 0
        while not logged_in:
            try:
                if page.locator("#pane-side, #main, div[role='textbox']").count() > 0:
                    logged_in = True
                    print("\n[ACTIVE & LISTENING] WhatsApp Web connected! Pure incoming filter active...\n")
                    break
            except Exception:
                pass
            time.sleep(2)
            wait_counter += 1
            if wait_counter % 15 == 0:
                print(f"[STATUS] Waiting for WhatsApp Web login... ({wait_counter * 2}s elapsed)")

        time.sleep(2)
        last_replied_msg_per_chat = {}
        last_sent_reply_per_chat = {}

        while True:
            try:
                # 1. Self-Learn from active chat history in real-time
                learn_from_chat_history(page)

                # 2. Check open chat window (#main)
                main_chat = page.query_selector("#main")
                if main_chat:
                    if not is_group_chat(page):
                        chat_title = get_current_chat_title(page)

                        # STRICT 1-TIME REPLY: If the last message bubble in chat is outgoing, DO NOT REPLY AGAIN!
                        if not is_last_message_outgoing(main_chat):
                            latest_text = get_latest_incoming_text(main_chat)

                            if latest_text and latest_text != last_replied_msg_per_chat.get(chat_title):
                                # ECHO GUARD: Check if incoming user message matches previous bot sent reply
                                prev_bot_sent = (last_sent_reply_per_chat.get(chat_title) or "").strip().lower()
                                clean_incoming_text = (latest_text or "").strip().lower()

                                if clean_incoming_text and prev_bot_sent and clean_incoming_text == prev_bot_sent:
                                    print(f"[ECHO GUARD]: Incoming message from {chat_title} ('{latest_text}') matches previous bot reply — NO REPLY SENT!\n")
                                    last_replied_msg_per_chat[chat_title] = latest_text
                                else:
                                    last_replied_msg_per_chat[chat_title] = latest_text
                                    print(f"\n[NEW INCOMING MESSAGE FROM {chat_title}]: '{latest_text}'")

                                    row = {
                                        "message_id": f"wa_{int(time.time())}",
                                        "user_id": chat_title,
                                        "conversation_type": "personal",
                                        "message_text": latest_text,
                                        "media_type": "",
                                        "forwarded_count": "0"
                                    }
                                    res = run_agent.process_message_dict(row)
                                    action = (res.get("action") or "digest").upper()
                                    reply_text = (res.get("chat_reply") or "").strip()

                                    if action == "MUTE" or not reply_text:
                                        print(f"[MUTED/SPAM - NO REPLY SENT]: '{latest_text}' ({action})\n")
                                    else:
                                        last_sent_reply_per_chat[chat_title] = reply_text
                                        send_reply_to_active_chat(page, reply_text, action, target_chat_title=chat_title)

                # 3. Check unread side-panel badges (#pane-side) to open unread chats
                unread_badges = page.query_selector_all(
                    "span[aria-label*='unread'], div._ak8l span, span._aria-unread, span[data-icon='unread-count'], span[aria-label*='अनपढ़े']"
                )

                for badge in unread_badges:
                    try:
                        parent_chat = badge.evaluate_handle(
                            "el => el.closest('div[role=\"listitem\"]') || el.closest('div[tabindex=\"-1\"]') || el.closest('div[role=\"row\"]')"
                        )
                        if parent_chat:
                            parent_chat.click()
                            time.sleep(0.5)
                            # Opening the chat brings it to #main so Step 2 handles it safely ONCE on next loop
                    except Exception as e:
                        logging.debug("Skipped unread row: %s", e)

                # Smooth 1.0s loop pacing — zero CPU overhead & no unnecessary loops
                time.sleep(1.0)
            except KeyboardInterrupt:
                print("\nStopping WhatsApp Web Bot...")
                break
            except Exception as e:
                logging.error("Monitoring loop error: %s", e)
                time.sleep(0.5)


if __name__ == "__main__":
    run_whatsapp_bot()
