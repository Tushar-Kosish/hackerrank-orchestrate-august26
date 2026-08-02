"""Message Notification Router Agent & Persona Response Generator (Tushar's Digital Twin).
Single source of truth for all routing decisions and conversational AI auto-replies.

HOW MATCHING WORKS (order matters — most specific FIRST):
  1. Self-learned memory from real chat history
  2. Emotional signals (sad, sick, excited, nostalgic)
  3. Specific topic intents (location, activity, food, gaming, payment, calls)
  4. Language-specific greetings / farewells / small talk
  5. Fallback

LOGICAL RULES:
  - Muted/spam messages get NO chat reply (empty string returned).
  - Language is detected BEFORE intent matching so replies match the input language.
  - Location questions ("kahan h") are caught BEFORE generic greetings ("bhai" word).
  - Spanish "como estas" asks HOW ARE YOU — answered with "bien, y tu?" not a greeting.
"""
import sys
import re
import csv
import json
import random
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))

DATASET_DIR = repo_root / "dataset"
LEARNED_MEMORY_FILE = repo_root / "agent" / "learned_chat_memory.json"

# ── Language detection word-sets ──────────────────────────────────────────────
SPANISH_WORDS = {
    "hola", "buenas", "gracias", "amigo", "amiga", "como", "estas",
    "bien", "que", "tal", "por", "favor", "donde", "cuando", "todo",
    "dale", "claro", "vamos", "chao", "hasta"
}
HINGLISH_PUNJABI_SLANG = {
    "bhai", "bro", "veer", "paji", "yaar", "kahan", "kdr", "kaha",
    "kese", "kaise", "kivein", "kive", "kya", "ki", "krra", "krda",
    "krde", "dss", "vdia", "badhiya", "scene", "vella", "aaja",
    "khele", "khana", "khaya", "chalna", "miliye", "paise", "bhej",
    "sondi", "thik", "haan", "nah", "naa", "ruk", "dekh", "batata",
    "dssda", "milde", "bgmi", "pubg", "dukh", "pareshan", "bura",
    "rula", "bimar", "tabiyat", "khush", "yaad", "kal", "aaj",
    "kal", "raat", "subah", "shaam", "chai", "kha", "suta",
    "padh", "class", "paper", "exam", "result", "likh", "bol",
    "sun", "bata", "maar", "gaya", "aaya", "ghar", "bahar",
    "chal", "band", "chup", "gussa", "lad", "fight", "sorry",
    "maafi", "pyaar", "yaad", "miss", "tenu"
}


# ── Learned memory helpers ─────────────────────────────────────────────────────
def load_learned_memory():
    if LEARNED_MEMORY_FILE.exists():
        try:
            with open(LEARNED_MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"learned_replies": {}}


def save_learned_pair(incoming_text, outgoing_reply):
    if not incoming_text or not outgoing_reply:
        return
    inc = incoming_text.lower().strip()
    out = outgoing_reply.strip()
    memory = load_learned_memory()
    memory.setdefault("learned_replies", {})
    memory["learned_replies"].setdefault(inc, [])
    if out not in memory["learned_replies"][inc]:
        memory["learned_replies"][inc].append(out)
        try:
            with open(LEARNED_MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)
            print(f"[SELF-LEARNED]: '{inc}' -> '{out}'")
        except Exception as e:
            print(f"[MEMORY SAVE ERROR]: {e}")


# ── Language detector ──────────────────────────────────────────────────────────
def detect_language(text):
    """Returns 'spanish', 'hinglish', or 'english'."""
    if not text:
        return "english"
    words = set(re.findall(r'\b[a-z]+\b', text.lower()))
    if words & SPANISH_WORDS:
        return "spanish"
    if words & HINGLISH_PUNJABI_SLANG:
        return "hinglish"
    return "english"


# ── Inline regex helper ────────────────────────────────────────────────────────
def has(pattern, text):
    return bool(re.search(pattern, text, re.IGNORECASE))


import os
import urllib.request
import urllib.parse

# ── Google Web Search Grounding ────────────────────────────────────────────────
def perform_google_search(query):
    """Performs live web search for search queries and extracts short factual answer."""
    if not query:
        return None
    cleaned_query = re.sub(r'^(search|google|find|look up)\s+', '', query, flags=re.IGNORECASE).strip()
    
    # 1. Wikipedia Search API
    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={urllib.parse.quote(cleaned_query)}&utf8=&format=json"
        req = urllib.request.Request(wiki_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            results = data.get('query', {}).get('search', [])
            if results:
                snippet = results[0].get('snippet', '')
                clean_snippet = re.sub(r'<[^>]+>', '', snippet).strip()
                clean_snippet = re.sub(r'\s+', ' ', clean_snippet)
                if clean_snippet:
                    if len(clean_snippet) > 100:
                        clean_snippet = clean_snippet[:97] + "..."
                    return clean_snippet
    except Exception as e:
        print(f"[SEARCH WIKI ERROR]: {e}")

    # 2. DuckDuckGo API Fallback
    try:
        ddg_url = f"https://api.duckduckgo.com/?q={urllib.parse.quote(cleaned_query)}&format=json&no_html=1"
        req = urllib.request.Request(ddg_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            abstract = data.get('AbstractText', '')
            if abstract:
                if len(abstract) > 100:
                    abstract = abstract[:97] + "..."
                return abstract
    except Exception as e:
        print(f"[SEARCH DDG ERROR]: {e}")

    return None


# ── Google Gemini AI API Call ─────────────────────────────────────────────────
def call_gemini_api(user_text, lang="hinglish"):
    """Calls Google Gemini API (gemini-1.5-flash) if GEMINI_API_KEY / GOOGLE_API_KEY is available."""
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        return None
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    prompt = (
        f"You are Tushar's personal AI replica chatting on WhatsApp with a close friend. "
        f"Incoming message: '{user_text}'. "
        f"Reply in 1 short casual sentence max (under 12 words). Tone: authentic, informal, friendly, match language '{lang}'. "
        f"Do NOT sound like a bot. Output ONLY the reply."
    )
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        req = urllib.request.Request(url, data=json.dumps(payload).encode('utf-8'), headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            res_text = data['candidates'][0]['content']['parts'][0]['text'].strip()
            res_text = re.sub(r'[\r\n]+', ' ', res_text).strip()
            return res_text
    except Exception as e:
        print(f"[GEMINI API ERROR]: {e}")
        return None


def is_search_intent(text):
    """Detects if message is a search request or factual question needing Google search."""
    if not text:
        return False
    t = text.lower().strip()
    search_keywords = [
        r'^\s*(search|google|find|look up)\b',
        r'\b(who is|what is|where is|when was|capital of|meaning of|definition of|weather in|temperature in|score of|news about|latest news|price of)\b'
    ]
    return any(re.search(pat, t) for pat in search_keywords)


# ── Master reply generator ─────────────────────────────────────────────────────
def generate_chat_reply(text, action, mtype, reason):
    """
    Returns a single short casual reply string.
    Returns empty string for MUTED/SPAM messages (no reply sent).
    """
    t = (text or "").lower().strip()

    # ── RULE 0: Never reply to muted spam/promo messages ──────────────────────
    if action == "mute":
        return ""

    # ── RULE 1: Self-learned memory first ─────────────────────────────────────
    memory = load_learned_memory()
    learned = memory.get("learned_replies", {})
    if t in learned and learned[t]:
        chosen = random.choice(learned[t])
        print(f"[MEMORY HIT]: '{t}' -> '{chosen}'")
        return chosen

    lang = detect_language(t)

    # ── RULE 1.5: Web / Google Search Intent ──────────────────────────────────
    if is_search_intent(t):
        search_res = perform_google_search(t)
        if search_res:
            if lang == "hinglish":
                reply = f"dekh google pe bataya — {search_res}"
            else:
                reply = f"just checked — {search_res}"
            save_learned_pair(t, reply)
            return reply

    # ── RULE 1.6: Google Gemini AI API Call (if API key set) ──────────────────
    gemini_reply = call_gemini_api(t, lang)
    if gemini_reply:
        save_learned_pair(t, gemini_reply)
        return gemini_reply


    # ══════════════════════════════════════════════════════════════════════════
    # RULE 2: EMOTIONAL INTELLIGENCE (checked before topic matching)
    # ══════════════════════════════════════════════════════════════════════════

    # 2a. Sad / depressed / upset / tension
    if has(r'\b(sad|upset|depressed|tension|stress|dukh|pareshan|mood off|mood kharab|feeling low|bura lag|rula|crying|dil toot|broken|cried|ro rha|rone)\b', t):
        if lang == "english":
            return random.choice([
                "hey what happened? i'm here bro",
                "don't stress man, it'll be fine",
                "call me if you wanna talk, i'm here"
            ])
        return random.choice([
            "kya hua bhai? tension mat le, main hu na",
            "koi ni veer, sab thik ho jayega",
            "mood off kyu h? call karta hu thodi der mein",
            "bhai bol kya hua, main sunne ko taiyaar hu"
        ])

    # 2b. Sick / unwell / hospital
    if has(r'\b(sick|bimar|fever|tabiyat|headache|sir dard|pain|unwell|hospital|doctor|medicine|dawai|nahi thik|tabi)\b', t):
        if lang == "english":
            return random.choice([
                "take care bro! get well soon",
                "rest up man, drink water and sleep",
                "call me if you need anything bro"
            ])
        return random.choice([
            "tabiyat ka dhyan rakh bro! dawai le le",
            "arre bhai rest kar, paani pi aur so ja",
            "koi help chahiye to bolna, main hu na"
        ])

    # 2c. Excitement / celebration / passed / job / win
    if has(r'\b(congrats|cleared|passed|selected|got the job|got selected|got job|got placed|won|party|celebrate|khush|khushkhabri|maza|amazing|super|yay|treat|result aa|result aya|exam clear|paper clear|ho gaya yaar|ho gyi)\b', t):
        if lang == "english":
            return random.choice([
                "yooo congrats! so happy for you 🎉",
                "lets gooo!! party time bro 🎉",
                "wait really?? that's insane bro 🔥"
            ])
        return random.choice([
            "bhai congrats!! bohot khush hu tere liye 🎉",
            "arrey wah! party to banti h, kab de rha h?",
            "yaar ye to bahut badiya news h!! 🔥"
        ])

    # 2d. Nostalgia / miss you
    if has(r'\b(miss you|miss u|miss kr|yaad aa|yaad aati|bohot din|bade dino|long time|bahut time|kab milenge|milte h|milna h)\b', t):
        if lang == "english":
            return random.choice([
                "miss you too bro! let's meet up soon",
                "yeah man long time! tell me when you're free"
            ])
        return random.choice([
            "haan bhai yaad aati h, chal iss weekend milde h",
            "sahi me yaar, bohot din ho gaye! scene banate h",
            "haan bro, tenu bhi miss kita, chal mil ke baate karte h"
        ])

    # 2e. Anger / fight / frustration
    if has(r'\b(angry|gussa|ladd|fight|jhagda|chakkar|pagal|bakwaas|kya yaar|kya bhai|annoyed|irritated|fed up|pakaya|tang)\b', t):
        if lang == "english":
            return random.choice([
                "whoa chill bro, what happened?",
                "easy man, take a breath, tell me what's up"
            ])
        return random.choice([
            "arre bhai kya hua? shaant ho ja pehle",
            "koi ni yaar, chill kr, bol kya scene h",
            "gussa mat ho bhai, bata kya hua"
        ])

    # 2f. Sorry / apology
    if has(r'\b(sorry|maafi|galti|bhool gaya|bhool gyi|meri galti|forgive)\b', t):
        if lang == "english":
            return random.choice(["it's okay bro, chill", "no worries man, all good"])
        return random.choice([
            "koi ni bhai, chill kr",
            "yaar chod, koi baat nahi",
            "no scene bro, sab thik h"
        ])

    # ══════════════════════════════════════════════════════════════════════════
    # RULE 3: TOPIC INTENTS (specific questions/situations)
    # ══════════════════════════════════════════════════════════════════════════

    # 3a. Location / whereabouts — MUST come before greeting catch (has "bhai"/"bro")
    if has(r'\b(kahan|kdr|kaha|where are you|where r u|where u at|kidhar|where ho)\b', t):
        if "office" in t or "work" in t:
            return random.choice(["office mein hu bro, tu dss", "kaam pe hu yaar"])
        if "college" in t or "university" in t or "class" in t:
            return random.choice(["college vich aa, bol veer", "class mein hu bro"])
        if "bahar" in t or "outside" in t or "out" in t:
            return random.choice(["haan bahar hu, kyu kuch plan h?", "bahar gaya tha, back aa gaya"])
        if lang == "english":
            return random.choice(["at home bro, why? what's up?", "home, why?"])
        return random.choice([
            "ghar pe hu bro, tu dss",
            "vella baitha hu ghar, tu bol",
            "ghar pe baith ke kuch nahi kr rha, tu sunaa"
        ])

    # 3b. Current activity / what are you doing
    if has(r'\b(kya kr rha|ki krda|kya krra|kya kar raha|what doing|what r u doing|what are you doing|kya chal raha|ki chal rha|busy h|busy hai)\b', t):
        activities = [
            "vella baitha hu, tu dss",
            "phone chalaa rha hu, tu bol",
            "kuch nahi bas chill, wbu?",
            "ghar pe baitha hu, kya scene h?",
            "just relaxing bro, tu sunaa"
        ]
        return random.choice(activities)

    # 3c. Gaming / BGMI / PUBG
    if has(r'\b(bgmi|pubg|free fire|ff|game|gaming|khele|khelna|match|squad|rank|drop|rush|chicken dinner)\b', t):
        return random.choice([
            "haan aaja! 5 min mein online hu",
            "haan bro aaja, squad ready krte h",
            "chal aaja, ek match lagayein"
        ])

    # 3d. Food / eating
    if has(r'\b(khana|dinner|lunch|breakfast|khaya|kha liya|kuch khaya|chai|coffee|bhojan|food|eat|ate|hungry|bhook|khaana)\b', t):
        if lang == "english":
            return random.choice([
                "just ate bro, you?",
                "yeah had lunch, wbu?",
                "nah not yet, what about you?"
            ])
        return random.choice([
            "haan khaliya bro, tu khaya?",
            "abhi khaya, tu kha le",
            "nahi abhi nahi khaya, kha ke baat karta hu 😄"
        ])

    # 3e. Sleep / night / tired
    if has(r'\b(sona|so ja|so gaya|so gyi|neend|nींद|tired|thak|thaka|thaki|raat ko|good night|gn|sondi|sou ja|nap)\b', t):
        if lang == "english":
            return random.choice(["gn bro! sleep tight", "rest up, gn 🌙"])
        return random.choice([
            "haan so ja bhai, gn 🌙",
            "chal sondi aa, gn bro",
            "theek h, so ja, kal baat karte h"
        ])

    # 3f. Morning / wake up
    if has(r'\b(good morning|gm|subah|utha|uth gaya|wake up|morning)\b', t):
        if lang == "english":
            return random.choice(["gm bro!", "morning! 🌅 wbu?"])
        return random.choice([
            "gm bhai! 🌅",
            "utha finally! kaise h?",
            "good morning yaar, kya plan h aaj?"
        ])

    # 3g. Study / college / exam / notes (only if NOT excitement — e.g. exam stress, not result)
    if has(r'\b(padh|study|notes|exam|paper|class|college|assignment|submission|test|marks|fail|syllabus|lecture)\b', t) and not has(r'\b(clear|cleared|passed|ho gaya|result aa|result aya)\b', t):
        if lang == "english":
            return random.choice([
                "bro same, not studied at all 😭",
                "yeah got class today too, ugh",
                "man let's study together sometime"
            ])
        return random.choice([
            "bhai padhai nahi ho rahi bilkul 😭",
            "haan yaar exam pressure h, chal saath padhe",
            "abhi toh kuch nahi padha, tu kr rha h?"
        ])

    # 3h. Payment / money / GPay
    if mtype == "payment" or has(r'\b(gpay|upi|payment|pay|paise|bhej|rs|rupees|send money|transfer|paytm|phonepe|received)\b', t):
        return random.choice([
            "haan dekh liya, mil gaye 👍",
            "haan bro received, thanks!",
            "got it bro, shukriya"
        ])

    # 3i. Urgent / call me back
    if action == "notify" or has(r'\b(urgent|call me|call karo|call kr|phone uthao|phone utha|call back|asap|emergency|right now)\b', t):
        return random.choice([
            "busy hu thoda, 10 min mein call karta hu",
            "thodi der mein call karta hu bro",
            "abhi busy hu, 10 min ruk"
        ])

    # 3j. Plans / meeting / hangout
    if has(r'\b(plan|milenge|milna|milte|chal|aaja|aa ja|bahar chalein|outing|movie|trip|ghoomne|chalein|chalte|scene kya h)\b', t):
        if lang == "english":
            return random.choice([
                "yeah bro let's do it! when?",
                "i'm in, what's the plan?",
                "yeah free this weekend, tell me more"
            ])
        return random.choice([
            "haan bro kab milna h? bata",
            "chal scene banate h, kab free h tu?",
            "haan aaja, weekend mein plan karte h"
        ])

    # 3k. Work stress / office
    if has(r'\b(office|work|job|boss|meeting|deadline|project|presentation|kaam|naukri|overtime)\b', t):
        return random.choice([
            "bhai kaam ka pressure h kya?",
            "haan yaar, kaam bohot h aajkal",
            "bro same, office ki life hi aisi h"
        ])

    # ══════════════════════════════════════════════════════════════════════════
    # RULE 4: LANGUAGE-SPECIFIC SMALL TALK & BOT IDENTITY
    # ══════════════════════════════════════════════════════════════════════════

    # Bot Identity / Who is this
    if has(r'\b(who are you|kon ho|kaun ho|who is this|who r u|kon h|kaun h|bot|ai)\b', t):
        return "Hey! I'm Tushar's AI assistant bot 🤖"

    # 4a. SPANISH
    if lang == "spanish":
        if has(r'\b(hola|hey|hi|buenas)\b', t):
            return random.choice(["hola!", "buenas bro", "que tal?"])
        if has(r'\b(como estas|como estás|que tal)\b', t):
            return random.choice(["todo bien bro, y tu?", "bien, tu?", "todo chill, wbu?"])
        if has(r'\b(gracias|thanks)\b', t):
            return "de nada bro!"
        if has(r'\b(donde|where)\b', t):
            return "en casa bro"
        if has(r'\b(adios|bye|chao|hasta)\b', t):
            return "chao bro! hasta luego"
        return random.choice(["dale bro", "claro que si", "todo bien"])

    # 4b. HINGLISH greetings / small talk
    if lang == "hinglish":
        if has(r'\b(hi|hello|hey|yo|hii|heyy|ssa|sat sri akal|waheguru|jai mata)\b', t):
            return random.choice(["yo bhai!", "haan veer bol", "haan bhai, bata"])
        if has(r'\b(kaise ho|kese ho|kivein|kive|kya haal|sab thik|aur batao|kya chal|tera haal|haal bata)\b', t):
            return random.choice([
                "sahi bro, tu sunaa",
                "badhiya, tu kivein aa?",
                "vdia bhai, tu dss kuch",
                "chill mein hu, wbu?"
            ])
        if has(r'\b(thanks|thx|shukriya|dhanyawad|shukar|meherbani)\b', t):
            return random.choice(["no scene bro, welcome", "koi ni yaar", "arre yaar, chod"])
        if has(r'\b(bye|baad|milte|chalta|phir milenge|nikal rha|ja rha)\b', t):
            return random.choice(["bye bro, baad ch milde!", "chal yaar, take care", "thik h, tc bro"])
        if has(r'\b(haha|lol|hehe|😂|lmao|funny|maza aaya|hasi)\b', t):
            return random.choice(["haha sahi h bhai 😂", "haha yaar mast h", "lol sach mein 😂"])
        if has(r'\b(bhai sun|yaar sun|ek baat|bata bhai|sun yaar|sunna h)\b', t):
            return random.choice(["haan bol bhai, sunna h", "haan sun rha hu, bata"])
        if "?" in t:
            return random.choice([
                "check karke batata hu bro",
                "haan dekhunga",
                "pata nahi yaar, main bhi soch rha hu"
            ])
        return random.choice([
            "haan bhai sahi h",
            "theek h bro, chal",
            "haan yaar, dekh lena"
        ])

    # 4c. ENGLISH greetings / small talk
    if lang == "english":
        if has(r'\b(hi|hello|hey|yo|hii|heyy|sup|heya|howdy)\b', t):
            return random.choice(["hey!", "yo!", "hi!", "sup?"])
        if has(r'\b(how are you|how r u|hru|how you doing|you good|all good|what\'s up|whats up|wassup)\b', t):
            return random.choice([
                "doing good, you?",
                "all good bro, wbu?",
                "chilling, you tell"
            ])
        if has(r'\b(thanks|thank you|thx|ty|ty bro|thanks man)\b', t):
            return random.choice(["no problem!", "welcome bro!", "anytime man"])
        if has(r'\b(bye|cya|see you|later|take care|tc|peace out|gotta go)\b', t):
            return random.choice(["bye bro!", "cya later!", "tc man, later"])
        if has(r'\b(haha|lol|lmao|omg|oh wow|really|wait what|no way)\b', t):
            return random.choice(["oh true haha", "wait really?? 😂", "haha bro same", "no way lol"])
        if has(r'\b(are you free|r u free|you free|free now|free today|free this weekend)\b', t):
            return random.choice(["yeah free, what's the plan?", "yep free, what's up?"])
        if "?" in t:
            return random.choice([
                "lemme check and get back to you",
                "nah, not sure tbh",
                "hmm let me think"
            ])
        return random.choice([
            "oh true haha",
            "sounds good bro",
            "yep makes sense"
        ])

    # ── Fallback ───────────────────────────────────────────────────────────────
    return random.choice([
        "haan bhai sahi h",
        "theek h, baad mein baat karte h",
        "ok bro, noted",
        "hmm dekh lete h"
    ])


# ══════════════════════════════════════════════════════════════════════════════
# CONTEXTUAL DATA LOADERS — business, group, history lookups
# ══════════════════════════════════════════════════════════════════════════════

def _load_csv_dict(filename, key_col):
    """Load a CSV into a dict keyed by *key_col*. Returns {} on missing file."""
    path = DATASET_DIR / filename
    if not path.exists():
        return {}
    result = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                k = (row.get(key_col) or "").strip()
                if k:
                    result[k] = row
    except Exception:
        pass
    return result


def _load_csv_list(filename):
    """Load a CSV into a list of dicts. Returns [] on missing file."""
    path = DATASET_DIR / filename
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


# Module-level lazy cache (populated on first call)
_CTX_CACHE = {}


def _get_context():
    """Return shared context dicts, loading once from disk."""
    if _CTX_CACHE:
        return _CTX_CACHE
    _CTX_CACHE["businesses"] = _load_csv_dict("business_accounts.csv", "business_id")
    _CTX_CACHE["groups"] = _load_csv_dict("groups.csv", "group_id")
    _CTX_CACHE["group_members"] = _load_csv_list("group_members.csv")
    _CTX_CACHE["user_biz_history"] = _load_csv_list("user_business_history.csv")
    _CTX_CACHE["message_history"] = _load_csv_list("message_history.csv")
    _CTX_CACHE["message_events"] = _load_csv_list("message_events.csv")
    _CTX_CACHE["images"] = _load_csv_dict("images.csv", "media_id") if (DATASET_DIR / "images.csv").exists() else {}
    _CTX_CACHE["voice_notes"] = _load_csv_dict("voice_notes.csv", "media_id") if (DATASET_DIR / "voice_notes.csv").exists() else {}
    return _CTX_CACHE


def _find_evidence(ctx, user_id, sender_id, msg_id):
    """Find related historical message IDs for evidence linking."""
    evidence = []
    for hist in ctx.get("message_history", []):
        h_user = (hist.get("user_id") or "").strip()
        if h_user == user_id:
            h_mid = (hist.get("message_id") or "").strip()
            if h_mid and h_mid != msg_id:
                evidence.append(h_mid)
    return evidence if evidence else ["none"]


# ══════════════════════════════════════════════════════════════════════════════
# ROUTING ENGINE — Multi-signal decision cascade
# ══════════════════════════════════════════════════════════════════════════════

def route_message(row, businesses=None):
    """
    Comprehensive routing cascade.  Returns (action, message_type, reason, confidence, evidence_ids).

    Priority order (most specific first):
      1. Scam / phishing
      2. Spam / promotion (keywords, unverified business, high forward)
      3. Urgent / emergency
      4. Payment / transaction
      5. Event / calendar
      6. Business update (verified, non-promo)
      7. Forwarded content
      8. Voice note (media-only)
      9. Image message
     10. Greeting (short text)
     11. Personal chat
     12. Group chat
     13. Unknown / fallback
    """
    ctx = _get_context()
    biz_lookup = businesses or ctx.get("businesses", {})

    text = (row.get("message_text") or "").strip()
    t = text.lower()
    media_type = (row.get("media_type") or "").strip().lower()
    msg_id = row.get("message_id", "wa_0")
    conv_type = (row.get("conversation_type") or "personal").strip().lower()
    user_id = (row.get("user_id") or "").strip()
    sender_id = (row.get("sender_user_id") or "").strip()
    biz_id = (row.get("business_id") or "").strip()
    group_id = (row.get("group_id") or "").strip()

    try:
        fwd_count = int(row.get("forwarded_count") or 0)
    except (ValueError, TypeError):
        fwd_count = 0

    # ── RULE: Disregard assistant / bot self messages completely ───────────────
    if sender_id.lower() in ("assistant", "bot", "self") or user_id.lower() in ("assistant", "bot"):
        return "mute", "bot_self", "Disregard assistant/bot self messages as input", 1.0, "none"

    # Look up business verification
    biz_info = biz_lookup.get(biz_id, {})
    biz_verified = (biz_info.get("verified") or "").strip().lower() == "yes"
    biz_brand = (biz_info.get("brand") or "").strip()

    evidence = _find_evidence(ctx, user_id, sender_id, msg_id)

    # ── LAYER 1: Scam / phishing → MUTE ──────────────────────────────────────
    scam_kw = [
        "lottery", "winner", "claim prize", "you have won", "wire transfer",
        "nigerian prince", "bank account", "social security", "ssn",
        "click this link", "verify your account", "password reset",
        "suspended account", "act now or", "send money", "western union",
        "bitcoin transfer", "crypto airdrop", "whatsapp prize",
        "your number selected", "free iphone", "win iphone"
    ]
    if any(k in t for k in scam_kw):
        return "mute", "scam", f"Scam/phishing detected: suspicious keywords in message", 0.96, evidence

    # ── LAYER 2: Spam / promotion → MUTE ─────────────────────────────────────
    promo_kw = [
        "50% off", "limited offer", "buy now", "shop now", "free gift",
        "exclusive offer", "discount code", "sale!", "flash sale",
        "order now", "subscribe now", "sign up free", "cashback",
        "limited time", "last chance", "hurry", "deal of the day",
        "use code", "promo code", "special offer", "clearance"
    ]

    # 2a. Explicit promo conversation type
    if conv_type == "business_promo":
        return "mute", "promotion", "Business promotional message (promo channel)", 0.95, evidence

    # 2b. Business message from UNVERIFIED account with promo content
    if conv_type == "business" and biz_id and not biz_verified:
        if any(k in t for k in promo_kw) or media_type == "image":
            return "mute", "promotion", f"Promotional content from unverified business ({biz_brand or biz_id})", 0.92, evidence
        # Even without promo keywords, unverified biz with no clear value → mute
        if not t or len(t) < 10:
            return "mute", "spam", f"Low-value message from unverified business ({biz_brand or biz_id})", 0.85, evidence

    # 2c. Known promo keywords in any message
    if any(k in t for k in promo_kw):
        if conv_type == "business":
            return "mute", "promotion", "Promotional content in business message", 0.93, evidence
        if fwd_count >= 1 or media_type == "image":
            return "mute", "promotion", "Promotional content with forwarding or image — likely spam", 0.90, evidence
        if conv_type == "group":
            return "mute", "promotion", "Promotional content in group chat", 0.88, evidence
        # Personal with promo keywords but no forwarding/image → digest (could be sharing a deal)
        return "digest", "promotion", "Possible promotional content shared in personal chat", 0.65, evidence

    # 2d. Heavily forwarded → likely chain / spam
    if fwd_count >= 5:
        return "mute", "spam", f"Heavily forwarded message (forwarded {fwd_count}x) — likely chain/spam", 0.88, evidence

    # ── LAYER 3: Urgent / emergency → NOTIFY ─────────────────────────────────
    urgent_kw = [
        "urgent", "emergency", "call me back", "call me now", "hospital",
        "asap", "accident", "serious", "immediately", "right now",
        "come quick", "help me", "911", "dying", "critical", "sos"
    ]
    if any(k in t for k in urgent_kw) or conv_type == "urgent_personal":
        return "notify", "urgent", "High-priority urgent message needing immediate attention", 0.95, evidence

    # ── LAYER 4: Payment / transaction → NOTIFY ──────────────────────────────
    payment_kw = [
        "invoice", "payment", "due tomorrow", "due today", "amount due",
        "pay now", "transaction", "billing", "receipt", "balance",
        "overdue", "payment reminder", "emi", "installment",
        "credited", "debited", "transferred"
    ]
    if any(k in t for k in payment_kw):
        if conv_type == "business" and biz_verified:
            return "notify", "payment", f"Payment/billing notification from verified business ({biz_brand})", 0.92, evidence
        if conv_type == "business":
            return "digest", "payment", f"Payment-related message from business ({biz_brand or biz_id})", 0.78, evidence
        return "notify", "payment", "Payment or transaction notification", 0.88, evidence

    # ── LAYER 5: Event / calendar / meeting → NOTIFY or DIGEST ────────────────
    event_kw = [
        "meeting", "appointment", "schedule", "calendar", "event",
        "tomorrow at", "today at", "join the call", "zoom link",
        "google meet", "teams meeting", "webinar", "conference",
        "rsvp", "invitation", "invite"
    ]
    if any(k in t for k in event_kw):
        if has(r'\b(today|tomorrow|now|asap|in \d+ min)\b', t):
            return "notify", "event", "Time-sensitive event or meeting notification", 0.88, evidence
        return "digest", "event", "Upcoming event or meeting information", 0.78, evidence

    # ── LAYER 6: Business update (verified, non-promo) → DIGEST ───────────────
    biz_update_kw = [
        "order", "shipped", "delivered", "tracking", "dispatch",
        "confirmed", "booking", "reservation", "update", "status",
        "refund", "return", "replacement", "out for delivery"
    ]
    if conv_type == "business" and biz_verified:
        if any(k in t for k in biz_update_kw):
            return "notify", "business_update", f"Important update from verified business ({biz_brand})", 0.85, evidence
        if t:
            return "digest", "business_update", f"Message from verified business ({biz_brand})", 0.72, evidence

    # ── LAYER 7: Forwarded content → DIGEST / FORWARD ─────────────────────────
    if fwd_count >= 1:
        return "digest", "forward", f"Forwarded message (forwarded {fwd_count}x)", 0.68, evidence

    # ── LAYER 8: Voice note (media-only, no text) → DIGEST ────────────────────
    if media_type == "voice":
        if not t:
            return "digest", "personal", "Voice note message (batched for later listening)", 0.65, evidence
        # Voice note with text → treat text normally below
        pass

    # ── LAYER 9: Image message routing ────────────────────────────────────────
    if media_type == "image":
        if conv_type == "business":
            if biz_verified:
                return "digest", "business_update", f"Image from verified business ({biz_brand})", 0.70, evidence
            return "mute", "promotion", f"Image from unverified business — likely promotional", 0.85, evidence
        # Personal/group image
        if not t:
            return "digest", "personal", "Image shared in conversation", 0.60, evidence

    # ── LAYER 10: Greeting / short text → DIGEST ──────────────────────────────
    greeting_patterns = r'^\s*(hi|hello|hey|yo|hii|heyy|sup|gm|good morning|good evening|good afternoon|ssa|sat sri akal|hola|buenas|howdy|heya|namaste)\s*[!.?]*\s*$'
    if t and len(t) < 30 and re.match(greeting_patterns, t, re.IGNORECASE):
        return "digest", "greeting", "Short greeting message — low priority", 0.55, evidence

    # ── LAYER 11: Personal chat → DIGEST ──────────────────────────────────────
    if conv_type == "personal" and t:
        return "digest", "personal", "Personal chat message for later review", 0.75, evidence

    # ── LAYER 12: Group chat → DIGEST ─────────────────────────────────────────
    if conv_type == "group" and t:
        return "digest", "personal", "Group chat message — batched for digest", 0.60, evidence

    # ── LAYER 13: Unknown / empty → DIGEST ────────────────────────────────────
    if not t and not media_type:
        return "digest", "unknown", "Empty message with no text or media content", 0.30, evidence

    return "digest", "unknown", "No strong routing signal detected", 0.40, evidence


# ── Process helpers ────────────────────────────────────────────────────────────

def process_message_dict(row):
    action, mtype, reason, conf, evidence = route_message(row)
    text = row.get("message_text", "")
    reply = generate_chat_reply(text, action, mtype, reason)

    # RULE 3: Sentence deduplication guard — NEVER repeat the same line or sentence twice
    if reply:
        parts = [p.strip() for p in re.split(r'[.\n]+', reply) if p.strip()]
        unique_parts = []
        for p in parts:
            if p.lower() not in [u.lower() for u in unique_parts]:
                unique_parts.append(p)
        reply = " ".join(unique_parts)

    return {
        "action": action,
        "message_type": mtype,
        "reason": reason,
        "confidence": str(conf),
        "evidence_message_ids": ";".join(evidence),
        "chat_reply": reply
    }


def process_messages_csv():
    input_file = DATASET_DIR / "messages.csv"
    output_file = DATASET_DIR / "output.csv"
    if not input_file.exists():
        print(f"[ERROR] {input_file} not found!")
        return

    # Pre-load context once
    ctx = _get_context()

    rows_out = []
    with open(input_file, mode="r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            action, mtype, reason, conf, evidence = route_message(row)
            rows_out.append({
                "message_id": row.get("message_id", ""),
                "action": action,
                "message_type": mtype,
                "reason": reason,
                "confidence": str(conf),
                "evidence_message_ids": ";".join(evidence)
            })
            print(f"  [{row.get('message_id')}] {action:6s} | {mtype:16s} | conf={conf:.2f} | {reason[:60]}")
    with open(output_file, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["message_id", "action", "message_type",
                                                "reason", "confidence", "evidence_message_ids"])
        writer.writeheader()
        writer.writerows(rows_out)
    print(f"\n[SUCCESS] {len(rows_out)} messages processed -> {output_file}")


if __name__ == "__main__":
    process_messages_csv()
