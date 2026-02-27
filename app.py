import streamlit as st
import os
import time
import copy
import base64
import hashlib
import toml
import requests
import logging
from datetime import datetime

# ═══════════════════════════════════════════════════════════
#  LOGGING CONFIG
# ═══════════════════════════════════════════════════════════
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("coachbot.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

USERS_FILE = "users.toml"

# ═══════════════════════════════════════════════════════════
#  API KEY — from st.secrets or env fallback
# ═══════════════════════════════════════════════════════════
def get_gemini_key():
    try:
        key = st.secrets.get("GEMINI_API_KEY") or st.secrets.get("GOOGLE_API_KEY")
        if key:
            return str(key).strip()
    except Exception:
        pass
    return (os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY") or "").strip()

# ═══════════════════════════════════════════════════════════
#  GEMINI AI
# ═══════════════════════════════════════════════════════════
GEMINI_MODEL = "gemini-3-flash-preview"


def get_startup_bg_style():
    base_dir = os.path.dirname(__file__)
    candidates = [
        os.path.join(base_dir, "assets", "Images", "Bg Image.png"),
        os.path.join(base_dir, "image.png"),
        os.path.join(base_dir, "Screenshot", "Start.png"),
        os.path.join(base_dir, "Screenshot", "Loading Screen.png"),
        os.path.join(base_dir, "Screenshot", "Login Screen.png"),
    ]
    for image_path in candidates:
        if os.path.exists(image_path):
            ext = os.path.splitext(image_path)[1].lower()
            mime = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"
            with open(image_path, "rb") as img_file:
                b64 = base64.b64encode(img_file.read()).decode("utf-8")
            return f"background:linear-gradient(rgba(15,23,42,.55),rgba(15,23,42,.55)),url('data:{mime};base64,{b64}') center/cover no-repeat;"
    return "background:linear-gradient(135deg,#0f172a,#1e293b);"

def get_ai_response(user_message, chat_history, profile):
    api_key = get_gemini_key()
    if not api_key or api_key == "your-gemini-api-key-here":
        return ("⚠️ **Gemini API Key not configured.**\n\n"
                "Edit `.streamlit/secrets.toml` and set:\n"
                "```\nGEMINI_API_KEY = 'your-real-key'\n```\n"
                "Get a free key at **aistudio.google.com**")

    now_ts = time.time()
    retry_after_until = st.session_state.get("gemini_retry_after", 0.0)
    if now_ts < retry_after_until:
        wait_for = int(retry_after_until - now_ts)
        return f"⏳ Gemini is rate-limited. Please wait about {max(wait_for, 1)}s and try again."

    sport     = profile.get("sport", "athletics")
    goal      = profile.get("goal") or "Improve Performance"
    pos       = profile.get("position", "")
    intensity = profile.get("intensity", "Moderate")
    diet      = profile.get("diet", "Standard")
    injury    = profile.get("injury") or "None"
    age       = profile.get("age", "unknown")

    system_text = f"""You are Next Gen Sports Lab's AI coaching assistant, an elite AI performance coach.

ATHLETE PROFILE:
- Sport: {sport}
- Position: {pos if pos else 'General'}
- Age: {age}
- Goal: {goal}
- Training Intensity: {intensity}
- Diet Preference: {diet}
- Injuries/Limitations: {injury}

INSTRUCTION RULES:
1. ALWAYS personalize advice specifically for this athlete's sport and position. Never use generic "athletics" plans.
2. DETECT USER INTENT:
   - If greeting (hi, hello, hey, whatup, yo) → Respond with friendly greeting + ask what they need (workouts/nutrition/recovery/tactics).
   - If asking about workout/drills → Give structured training plan with warm-up, main workout, recovery.
   - If asking about nutrition → Give sport-specific meal advice aligned with their goal.
   - If asking about recovery/injury → Give safe recovery plan that respects their injury.
   - If asking about tactics/strategy → Give position-specific tactical tips.
   - If detailed goal mention → Give FULL 5-section plan.

3. RESPONSE STRUCTURE (when applicable):
   • Warm-up: Dynamic mobility specific to sport
   • Main Workout: Progressive drills/exercises for their goal
   • Recovery & Injury Safety: Reference their injury, avoid triggers
   • Nutrition/Hydration: Sport-specific fuel according to their diet preference
   • Motivation: Encouraging closing

4. TONE: Be a real youth coach - encouraging, motivating, practical, actionable bullets.

5. DO NOT give generic fallback responses. Always engage specifically with their sport and position.

6. If they give short messages, still provide substantive, personalized advice."""

    contents = []
    for msg in chat_history[-5:]:
        role = "user" if msg["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": msg["text"]}]})
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    payload = {
        "system_instruction": {"parts": [{"text": system_text}]},
        "contents": contents,
        "generationConfig": {"maxOutputTokens": 2000, "temperature": 0.4, "topP": 0.9},
    }
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"
        for attempt in range(3):
            try:
                r = requests.post(url, json=payload, timeout=(8, 30))
            except requests.exceptions.Timeout:
                if attempt < 2:
                    time.sleep(1.2 * (attempt + 1))
                    continue
                return "⏱️ Request timed out after retries. Please try again in a few seconds."
            except requests.exceptions.ConnectionError:
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                return "🌐 Network connection issue to Gemini API. Check internet/VPN and try again."
            if r.status_code == 429:
                if attempt < 2:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                st.session_state.gemini_retry_after = time.time() + 45
                return "⏳ Gemini rate limit hit (429). Please wait 20-60 seconds and try again."
            if r.status_code == 404:
                return f"⚠️ Model `{GEMINI_MODEL}` not available for this API key/project."
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if candidates:
                parts = candidates[0].get("content", {}).get("parts", [])
                if parts and parts[0].get("text"):
                    text = parts[0]["text"].strip()
                    if text:
                        return text
            return "⚠️ Gemini returned an empty response. Please try again."
        return "⏳ Gemini is busy right now. Please try again in a minute."
    except requests.exceptions.Timeout:
        return "⏱️ Request timed out. Please try again."
    except requests.exceptions.ConnectionError:
        return "🌐 Unable to reach Gemini API right now. Please check internet and retry."
    except requests.exceptions.HTTPError as e:
        code = e.response.status_code if e.response is not None else 0
        if code == 400: return "⚠️ Invalid API key. Check your secrets.toml."
        if code == 403: return "🔒 API key unauthorised. Visit aistudio.google.com."
        if code == 429:
            st.session_state.gemini_retry_after = time.time() + 45
            return "⏳ Rate limit hit (429). Please wait ~45s and retry."
        return f"❌ API error {code}: {str(e)[:100]}"
    except requests.exceptions.RequestException as e:
        return f"❌ Network/API request error: {str(e)[:100]}"
    except Exception as e:
        return f"❌ Error: {str(e)[:100]}"


# ═══════════════════════════════════════════════════════════
#  FILE HELPERS
# ═══════════════════════════════════════════════════════════
def hash_password(p): return hashlib.sha256(p.encode()).hexdigest()
def _ensure_users_file():
    if not os.path.exists(USERS_FILE):
        open(USERS_FILE,"w").write("[users]\n")
def load_users_from_file():
    _ensure_users_file()
    try: data=toml.load(USERS_FILE)
    except: data={}
    u=data.get("users",{}); return u if isinstance(u,dict) else {}
def save_users_to_file(u):
    open(USERS_FILE,"w").write(toml.dumps({"users":u}))
def verify_password(stored,plain):
    if not stored: return False
    return stored==plain or stored==hash_password(plain)

# ═══════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════
st.set_page_config(page_title="CoachBot",page_icon="⚡",layout="wide",initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
:root{--primary:#13ecec;--bg:#f0f4f8;--white:#fff;--s900:#0f172a;--s800:#1e293b;--s700:#334155;
      --s600:#475569;--s500:#64748b;--s400:#94a3b8;--s200:#e2e8f0;--s100:#f1f5f9;}
*,*::before,*::after{box-sizing:border-box;}
html,body,[class*="css"]{font-family:'Inter',sans-serif!important;color:var(--s900);}
.stApp{background:var(--bg);}
[data-testid="stHeader"],header[data-testid="stHeader"]{display:none!important;}
footer,#MainMenu{display:none!important;visibility:hidden!important;}
.block-container{padding:1rem 1.5rem 140px!important;max-width:100%!important;}

/* ── SIDEBAR ── */
section[data-testid="stSidebar"]{background:var(--white)!important;border-right:1px solid var(--s200)!important;min-width:250px!important;max-width:268px!important;}
section[data-testid="stSidebar"]>div:first-child{padding:1rem 0.75rem!important;height:100vh;display:flex;flex-direction:column;}
section[data-testid="stSidebar"][aria-expanded="false"]{min-width:250px!important;max-width:268px!important;}
section[data-testid="stSidebar"][aria-expanded="false"]{transform:translateX(0)!important;}
section[data-testid="stSidebar"][aria-expanded="false"]>div{display:flex!important;}
[data-testid="collapsedControl"]{background:white!important;border:1px solid #e2e8f0!important;border-radius:0 8px 8px 0!important;}
[data-testid="collapsedControl"]{display:flex!important;opacity:1!important;visibility:visible!important;}
section[data-testid="stSidebar"] .stButton>button{background:transparent!important;border:none!important;border-radius:.55rem!important;color:var(--s600)!important;font-weight:600!important;text-align:left!important;padding:.55rem .8rem!important;width:100%!important;font-size:.83rem!important;transition:all .15s!important;}
section[data-testid="stSidebar"] .stButton>button:hover{background:var(--s100)!important;color:var(--s900)!important;}
section[data-testid="stSidebar"] .stButton>button[kind="primary"]{background:linear-gradient(135deg,#13ecec,#06b6d4)!important;color:#0f172a!important;font-weight:700!important;box-shadow:0 3px 10px rgba(19,236,236,.3)!important;}

/* ── GLOBAL BUTTONS ── */
.stButton>button{border-radius:.6rem!important;font-weight:700!important;padding:.6rem 1rem!important;width:100%!important;font-size:.875rem!important;transition:all .15s!important;border:2px solid transparent!important;}
.stButton>button:hover{transform:translateY(-2px)!important;box-shadow:0 4px 12px rgba(0,0,0,.15)!important;}
.stButton>button[kind="primary"]{background:linear-gradient(135deg,#13ecec,#06b6d4)!important;color:#0f172a!important;border:none!important;box-shadow:0 4px 12px rgba(19,236,236,.3)!important;}
.stButton>button[kind="primary"]:hover{filter:brightness(1.06);}
.stButton>button:not([kind="primary"]){background:var(--white)!important;border:1.5px solid var(--s200)!important;color:var(--s700)!important;}
.stButton>button:not([kind="primary"]):hover{border-color:var(--primary)!important;color:var(--s900)!important;}
.stButton>button[kind="secondary"]{width:auto!important;padding:.3rem .85rem!important;font-size:.78rem!important;}

/* ── INPUTS ── */
label,.stTextInput label,.stSelectbox label,.stTextArea label,.stNumberInput label{color:var(--s800)!important;font-weight:600!important;font-size:.8rem!important;-webkit-text-fill-color:var(--s800)!important;}
input[type="text"],input[type="number"],input[type="password"],textarea{background:var(--white)!important;color:var(--s900)!important;-webkit-text-fill-color:var(--s900)!important;border:1.5px solid var(--s200)!important;border-radius:.5rem!important;font-size:.875rem!important;}
input:focus,textarea:focus{border-color:var(--primary)!important;box-shadow:0 0 0 3px rgba(19,236,236,.15)!important;outline:none!important;}
input[type="number"]::-webkit-outer-spin-button,input[type="number"]::-webkit-inner-spin-button{-webkit-appearance:none!important;}
.stNumberInput [data-testid*="Step"],.stNumberInput button{display:none!important;}

/* ── SELECT ── */
div[data-baseweb="select"]>div{background:var(--white)!important;border:1.5px solid var(--s200)!important;border-radius:.5rem!important;}
div[data-baseweb="select"],div[data-baseweb="select"] *{color:var(--s900)!important;-webkit-text-fill-color:var(--s900)!important;background:transparent!important;}
div[data-baseweb="menu"],div[data-baseweb="popover"],ul[data-baseweb="menu"]{background:var(--white)!important;border:1px solid var(--s200)!important;border-radius:.5rem!important;box-shadow:0 8px 24px rgba(15,23,42,.12)!important;}
li[role="option"],[data-baseweb="option"]{background:var(--white)!important;color:var(--s900)!important;-webkit-text-fill-color:var(--s900)!important;}
li[role="option"]:hover,[data-baseweb="option"]:hover{background:#e0fffe!important;}
li[role="option"][aria-selected="true"]{background:#ccfafa!important;}
div[data-baseweb="select"] [class*="placeholder"]{color:var(--s400)!important;-webkit-text-fill-color:var(--s400)!important;}

/* ── TABS ── */
.stTabs [data-baseweb="tab-list"]{gap:1rem;border-bottom:1px solid var(--s200);background:transparent;}
.stTabs [data-baseweb="tab"]{color:var(--s500)!important;font-weight:600!important;padding:.6rem 0!important;background:transparent!important;}
.stTabs [aria-selected="true"]{color:var(--s900)!important;border-bottom:2.5px solid var(--primary)!important;background:transparent!important;}

/* ── DASHBOARD ALIGN ── */
div[data-testid="column"]>div{width:100%!important;}

/* ── CHAT INPUT ── */
.stChatFloatingInputContainer {
    background: transparent !important;
    padding-bottom: 20px !important;
    bottom: 0 !important;
}
[data-testid="stChatInput"] {
    border-radius: 16px !important;
    background: #fff !important;
    border: 2px solid #13ecec !important;
    box-shadow: 0 4px 12px rgba(19,236,236,.15) !important;
    transition: all .2s ease !important;
    margin-bottom: 10px !important;
}
[data-testid="stChatInput"]:focus-within {
    border-color: #13ecec !important;
    box-shadow: 0 6px 20px rgba(19,236,236,.25) !important;
}
[data-testid="stChatInput"] textarea {
    background: #fff !important;
    border: none !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    font-size: .95rem !important;
    font-weight: 500 !important;
}
[data-testid="stChatInput"] textarea::placeholder {
    color: #94a3b8 !important;
    -webkit-text-fill-color: #94a3b8 !important;
    font-weight: 500 !important;
}
[data-testid="stChatInput"] button {
    background: linear-gradient(135deg,#13ecec,#06b6d4) !important;
    border: none !important;
    border-radius: 12px !important;
    color: #0f172a !important;
    font-weight: 700 !important;
    padding: 8px 16px !important;
    transition: all .2s ease !important;
}
[data-testid="stChatInput"] button:hover {
    filter: brightness(1.1);
    box-shadow: 0 4px 12px rgba(19,236,236,.3) !important;
}
[data-testid="stChatInput"] button svg {
    fill: #0f172a !important;
    color: #0f172a !important;
}

/* ── ALERTS ── */
div[data-testid="stAlert"] p,div[data-testid="stAlert"] span,div[data-testid="stAlert"] div{color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;font-weight:600!important;}

/* ── BADGES ── */
.badge{display:inline-flex;align-items:center;gap:4px;padding:2px 9px;border-radius:20px;font-size:.63rem;font-weight:700;white-space:nowrap;}
.badge-gold{background:#fef3c7;color:#92400e;border:1px solid #fcd34d;}
.badge-teal{background:#e0fffe;color:#0d9488;border:1px solid #13ecec;}
.badge-purple{background:#ede9fe;color:#6d28d9;border:1px solid #a78bfa;}
.badge-green{background:#dcfce7;color:#166534;border:1px solid #86efac;}
.badge-red{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5;}
.badge-locked{display:inline-flex;flex-direction:column;align-items:center;gap:6px;background:#f1f5f9;border:2px dashed #cbd5e1;border-radius:10px;padding:10px;text-align:center;opacity:0.65;filter:grayscale(100%);}

/* ── TRACKER INLINE BUTTONS ── */
div[data-testid="stTabs"] .stButton>button{background:#fff!important;border:2px solid #e2e8f0!important;color:#0f172a!important;-webkit-text-fill-color:#0f172a!important;font-weight:700!important;}
div[data-testid="stTabs"] .stButton>button:hover{border-color:#13ecec!important;background:#e0fffe!important;color:#0d9488!important;-webkit-text-fill-color:#0d9488!important;}

/* ── CHECKBOX ── */
.stCheckbox label span,.stCheckbox label p{color:var(--s900)!important;-webkit-text-fill-color:var(--s900)!important;font-weight:600!important;}

/* ── TYPING DOTS ── */
@keyframes blink{0%,80%,100%{opacity:0}40%{opacity:1}}
.dot{display:inline-block;width:6px;height:6px;border-radius:50%;background:#0d9488;animation:blink 1.4s infinite ease-in-out;margin:0 2px;}
.dot:nth-child(2){animation-delay:.2s}.dot:nth-child(3){animation-delay:.4s}

/* ── SIDEBAR TRACKER MINI ── */
.tracker-mini{background:#ffffff;border-radius:9px;border:2px solid #13ecec;padding:12px 10px;margin-bottom:8px;box-shadow:0 2px 8px rgba(19,236,236,.1);}
.tracker-mini-row{display:flex;justify-content:space-between;align-items:center;padding:6px 0;border-bottom:1px solid #e2e8f0;font-size:.75rem;}
.tracker-mini-row:last-child{border-bottom:none;}
.tm-label{color:#0f172a;font-weight:700;font-size:.73rem;}
.tm-val{color:#0f172a;font-weight:900;font-size:.8rem;}
.tm-val.good{color:#22c55e;font-weight:900;}
.water-bar{height:6px;background:#e2e8f0;border-radius:4px;overflow:hidden;margin-top:4px;border:1px solid #d1d5db;}
.water-fill{height:100%;background:linear-gradient(90deg,#13ecec,#06b6d4);border-radius:3px;transition:width .3s;}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════
for k,v in {
    'page':'login','current_user':None,'login_error':'','signup_error':'',
    'users':{},'tracker_data':{},'show_loading':False,'show_startup':True,
    'show_startup_phase':0,'notifications':{},'chat_history':{},'xp_data':{},
    'pf_attempt':False,'ai_thinking':False,'tracker_tab':0,
}.items():
    if k not in st.session_state: st.session_state[k]=v

if not st.session_state.users:
    st.session_state.users=load_users_from_file()

if st.session_state.show_startup:
    st.markdown("<style>.stApp{background:#0f172a!important;}</style>",unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  GAMIFICATION
# ═══════════════════════════════════════════════════════════
BADGES_DEF={
    'first_chat':    ('💬','First Chat',    'Sent first message',  'teal'),
    'hydration_hero':('💧','Hydration Hero','Hit 2L water',        'teal'),
    'iron_will':     ('🏋️','Iron Will',     '5 exercises done',   'purple'),
    'nutrition_pro': ('🥗','Nutrition Pro', '5+ meals logged',    'green'),
    'level_5':       ('⭐','Level 5',       'Reached Level 5',    'gold'),
    'level_10':      ('👑','Elite',         'Reached Level 10',   'gold'),
    'feedback_giver':('📝','Voice Matters', 'Submitted feedback', 'purple'),
    'streak':        ('🔥','On Fire',       'Earned 200+ XP',     'red'),
}
XP_REWARDS={'chat_msg':10,'exercise_done':25,'food_logged':10,'water_500':8,'feedback':30,'login':20}
LVL_XP=[0,100,250,450,700,1000,1400,1900,2500,3200,4000]

def get_xp(user):
    return st.session_state.xp_data.setdefault(user,{'xp':0,'level':1,'badges':[],'meals_logged':0,'exercises_done':0})

def award_xp(user,action,pts=None):
    d=get_xp(user); p=pts if pts is not None else XP_REWARDS.get(action,0); d['xp']+=p
    for i,t in enumerate(LVL_XP):
        if d['xp']>=t: old=d['level']; d['level']=i+1
    _check_badges(user,d); return p

def _check_badges(user,d):
    earned=d.setdefault('badges',[])
    def g(bid):
        if bid not in earned:
            earned.append(bid); b=BADGES_DEF[bid]
            add_notif(user,f"{b[0]} Badge: **{b[1]}** — {b[2]}","success")
    if len(st.session_state.chat_history.get(user,[]))>=1: g('first_chat')
    if d.get('exercises_done',0)>=5: g('iron_will')
    if d.get('meals_logged',0)>=5:   g('nutrition_pro')
    if d['level']>=5:  g('level_5')
    if d['level']>=10: g('level_10')
    if d['xp']>=200:   g('streak')
    tr=st.session_state.tracker_data.get(user,{})
    if tr.get('water',0)>=2000: g('hydration_hero')

def xp_bar(user):
    d=get_xp(user); lo=LVL_XP[min(d['level']-1,len(LVL_XP)-1)]; hi=LVL_XP[min(d['level'],len(LVL_XP)-1)]
    pct=int(min((d['xp']-lo)/max(hi-lo,1)*100,100))
    return f"""<div style="margin:8px 0 2px;">
  <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px;">
    <span style="font-size:.68rem;font-weight:700;color:#0f172a;">⚡ Level {d['level']}</span>
    <span style="font-size:.62rem;color:#64748b;">{d['xp']} XP</span>
  </div>
  <div style="height:5px;background:#e2e8f0;border-radius:3px;overflow:hidden;">
    <div style="width:{pct}%;height:100%;background:linear-gradient(90deg,#13ecec,#06b6d4);border-radius:3px;"></div>
  </div></div>"""

# ═══════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════
LOGO="""<svg fill="none" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg" style="width:{s}px;height:{s}px;color:#13ecec;display:inline-block;vertical-align:middle;">
<path clip-rule="evenodd" d="M24 18.4228L42 11.475V34.3663C42 34.7796 41.7457 35.1504 41.3601 35.2992L24 42V18.4228Z" fill="currentColor" fill-rule="evenodd"/>
<path clip-rule="evenodd" d="M24 8.18819L33.4123 11.574L24 15.2071L14.5877 11.574L24 8.18819ZM9 15.8487L21 20.4805V37.6263L9 32.9945V15.8487ZM27 37.6263V20.4805L39 15.8487V32.9945L27 37.6263ZM25.354 2.29885C24.4788 1.98402 23.5212 1.98402 22.646 2.29885L4.98454 8.65208C3.7939 9.08038 3 10.2097 3 11.475V34.3663C3 36.0196 4.01719 37.5026 5.55962 38.098L22.9197 44.7987C23.6149 45.0671 24.3851 45.0671 25.0803 44.7987L42.4404 38.098C43.9828 37.5026 45 36.0196 45 34.3663V11.475C45 10.2097 44.2061 9.08038 43.0155 8.65208L25.354 2.29885Z" fill="currentColor" fill-rule="evenodd"/>
</svg>"""

DEFAULT_EX=[
    {'name':'Warm-Up Jog','sets':1,'reps':1,'weight':0,'notes':'5 min easy jog','completed':False,'time':''},
    {'name':'Bodyweight Squats','sets':3,'reps':15,'weight':0,'notes':'Focus on depth','completed':False,'time':''},
    {'name':'Push-Ups','sets':3,'reps':12,'weight':0,'notes':'Keep core tight','completed':False,'time':''},
    {'name':'Lateral Shuffles','sets':4,'reps':10,'weight':0,'notes':'Explosive lateral','completed':False,'time':''},
    {'name':'Plank Hold','sets':3,'reps':1,'weight':0,'notes':'30 sec each set','completed':False,'time':''},
    {'name':'Cool-Down Stretch','sets':1,'reps':1,'weight':0,'notes':'Full body 5 min','completed':False,'time':''},
]

def navigate_to(page): st.session_state.page=page; st.rerun()
def add_notif(user,msg,typ="info"):
    st.session_state.notifications.setdefault(user,[]).insert(0,{'msg':msg,'time':datetime.now().strftime("%b %d, %H:%M"),'read':False,'type':typ})
def unread(user): return sum(1 for n in st.session_state.notifications.get(user,[]) if not n['read'])
def mark_read(user):
    for n in st.session_state.notifications.get(user,[]): n['read']=True
def ensure_tracker(user):
    if user not in st.session_state.tracker_data:
        exs=copy.deepcopy(DEFAULT_EX); now_t=datetime.now().strftime("%H:%M")
        for e in exs: e['time']=now_t
        st.session_state.tracker_data[user]={'food_log':[],'water':0,'exercises':exs}

# ═══════════════════════════════════════════════════════════
#  AUTH
# ═══════════════════════════════════════════════════════════
def submit_login():
    u=st.session_state.get('login_username','').strip(); p=st.session_state.get('login_password','')
    ud=st.session_state.users.get(u)
    if ud and verify_password(ud.get('password',''),p):
        st.session_state.current_user=u; st.session_state.login_error=''; st.session_state.show_loading=True
        d=get_xp(u); today=datetime.now().strftime('%Y-%m-%d')
        if d.get('last_login')!=today: d['last_login']=today; award_xp(u,'login')
    else: st.session_state.login_error="Invalid username or password."

def submit_signup():
    fn=st.session_state.get('signup_fullname','').strip(); un=st.session_state.get('signup_username','').strip()
    em=st.session_state.get('signup_email','').strip(); pw=st.session_state.get('signup_password','')
    cf=st.session_state.get('signup_confirm','')
    if not all([fn,un,em,pw,cf]): st.session_state.signup_error="All fields required."; return
    if pw!=cf: st.session_state.signup_error="Passwords don't match."; return
    if un in st.session_state.users: st.session_state.signup_error="Username taken."; return
    st.session_state.users[un]={'password':hash_password(pw),'fullname':fn,'email':em,'profile':{}}
    save_users_to_file(st.session_state.users)
    st.session_state.current_user=un; st.session_state.signup_error=''; st.session_state.page='onboarding'

# ═══════════════════════════════════════════════════════════
#  SIDEBAR  — with inline tracker panel
# ═══════════════════════════════════════════════════════════
def sidebar(active):
    user=st.session_state.current_user
    if not user or user not in st.session_state.users:
        st.session_state.current_user=None; navigate_to("login"); return
    ensure_tracker(user)
    ud=st.session_state.users[user]; prof=ud.get('profile') or {}
    name=prof.get('fullname',ud.get('fullname',user)); sport=prof.get('sport','Athlete')
    pos=prof.get('position',''); av=(name[0] if name else 'A').upper()
    badge=unread(user); d=get_xp(user)
    sport_line=f"🏅 {sport} · {pos}" if pos and 'Individual' not in pos else f"🏅 {sport}"
    tr=st.session_state.tracker_data.get(user,{})
    water=tr.get('water',0); exs=tr.get('exercises',[]); food=tr.get('food_log',[])
    done_ex=sum(1 for e in exs if e.get('completed'))
    total_cal=sum(e.get('calories',0) for e in food)
    water_pct=min(int(water/3000*100),100)
    water_col="#22c55e" if water_pct>=100 else "#13ecec" if water_pct>=50 else "#f59e0b"

    with st.sidebar:
        # Brand
        st.markdown(f"""<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px;
            padding-bottom:11px;border-bottom:1px solid #e2e8f0;">
          {LOGO.format(s=22)}<span style="font-size:.95rem;font-weight:800;color:#0f172a;">CoachBot</span>
          <span style="font-size:.55rem;color:#0d9488;font-weight:700;background:#e0fffe;padding:1px 6px;border-radius:10px;border:1px solid #13ecec;margin-left:auto;">Gemini</span>
        </div>""",unsafe_allow_html=True)

        # User card
        st.markdown(f"""<div style="display:flex;align-items:center;gap:9px;padding:9px;
            background:#f8fafc;border-radius:9px;margin-bottom:4px;border:1px solid #e2e8f0;">
          <div style="width:36px;height:36px;border-radius:50%;background:#e0fffe;border:2px solid #13ecec;
            display:flex;align-items:center;justify-content:center;font-weight:800;font-size:.95rem;color:#0f172a;flex-shrink:0;">{av}</div>
          <div style="min-width:0;">
            <div style="font-weight:700;color:#0f172a;font-size:.81rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{name}</div>
            <div style="font-size:.63rem;color:#64748b;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">{sport_line}</div>
          </div>
        </div>{xp_bar(user)}""",unsafe_allow_html=True)

        st.markdown("<div style='height:5px;'></div>",unsafe_allow_html=True)

        # ── NAV BUTTONS ──
        nav_items=[("💬  Chat","dashboard"),("📊  Tracker","tracker"),
                   ("⭐  Feedback","feedback"),("⚙️  Settings","settings")]
        for lbl,pg in nav_items:
            label=lbl+(f"  🔴{badge}" if pg=="dashboard" and badge>0 else "")
            kind="primary" if active==pg else "secondary"
            if st.button(label,key=f"sb_{pg}_{active}",use_container_width=True,type=kind):
                if pg=="dashboard": mark_read(user)
                navigate_to(pg)

        # ── DIVIDER ──
        st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:8px 0 6px;'>",unsafe_allow_html=True)

        # ── TRACKER MINI-PANEL (always visible in sidebar) ──
        st.markdown("""<div style="font-size:.6rem;font-weight:700;text-transform:uppercase;
            letter-spacing:.1em;color:#94a3b8;margin-bottom:5px;">📊 TODAY'S TRACKER</div>""",unsafe_allow_html=True)

        # Water quick-add buttons
        st.markdown(f"""<div class="tracker-mini">
          <div class="tracker-mini-row">
            <span class="tm-label">💧 Water</span>
            <span class="tm-val {'good' if water_pct>=100 else ''}">{water}ml</span>
          </div>
          <div class="water-bar"><div class="water-fill" style="width:{water_pct}%;background:{water_col};"></div></div>
          <div style="font-size:.6rem;color:#94a3b8;margin-top:2px;">{water_pct}% of 3000ml goal</div>
        </div>""",unsafe_allow_html=True)

        # Water quick-add (2x2 buttons for better number visibility)
        wc1,wc2=st.columns(2)
        with wc1:
            if st.button("+150ml",key=f"sbw150_{active}",use_container_width=True):
                tr['water']+=150; award_xp(user,'water_500',150//60)
                _check_badges(user,get_xp(user)); st.rerun()
        with wc2:
            if st.button("+250ml",key=f"sbw250_{active}",use_container_width=True):
                tr['water']+=250; award_xp(user,'water_500',250//60)
                _check_badges(user,get_xp(user)); st.rerun()
        wc3,wc4=st.columns(2)
        with wc3:
            if st.button("+500ml",key=f"sbw500_{active}",use_container_width=True):
                tr['water']+=500; award_xp(user,'water_500',500//60)
                _check_badges(user,get_xp(user)); st.rerun()
        with wc4:
            if st.button("+750ml",key=f"sbw750_{active}",use_container_width=True):
                tr['water']+=750; award_xp(user,'water_500',750//60)
                _check_badges(user,get_xp(user)); st.rerun()

        # Exercise + calories summary
        st.markdown(f"""<div class="tracker-mini" style="margin-top:6px;">
          <div class="tracker-mini-row">
            <span class="tm-label">🏋️ Exercises</span>
            <span class="tm-val {'good' if done_ex==len(exs) and len(exs)>0 else ''}">{done_ex}/{len(exs)}</span>
          </div>
          <div class="tracker-mini-row">
            <span class="tm-label">🍎 Meals</span>
            <span class="tm-val">{len(food)}</span>
          </div>
          <div class="tracker-mini-row" style="border-bottom:none;">
            <span class="tm-label">🔥 Calories</span>
            <span class="tm-val">{total_cal} kcal</span>
          </div>
        </div>""",unsafe_allow_html=True)

        # Quick complete next exercise
        next_ex=[e for e in exs if not e.get('completed')]
        if next_ex:
            ex=next_ex[0]
            st.markdown(f"""<div style="font-size:.65rem;color:#64748b;margin:4px 0 3px;">
              Next: <strong style="color:#0f172a;">{ex['name']}</strong> {ex['sets']}×{ex['reps']}</div>""",unsafe_allow_html=True)
            if st.button("✓ Mark Done",key=f"sbex_{active}",use_container_width=True, help="Mark this exercise as completed and earn XP"):
                ex['completed']=True; pts=award_xp(user,'exercise_done')
                d2=get_xp(user); d2['exercises_done']=d2.get('exercises_done',0)+1
                _check_badges(user,d2); add_notif(user,f"✅ +{pts} XP — {ex['name']}"); st.rerun()

        # ── DIVIDER ──
        st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:8px 0 5px;'>",unsafe_allow_html=True)

        # Badges
        earned=d.get('badges',[])
        if earned:
            st.markdown("<div style='font-size:.58rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin-bottom:4px;'>🏆 BADGES</div>",unsafe_allow_html=True)
            bhtml=" ".join(f"<span class='badge badge-{BADGES_DEF[b][3]}' title='{BADGES_DEF[b][2]}'>{BADGES_DEF[b][0]}</span>" for b in earned[:6])
            st.markdown(f"<div style='display:flex;flex-wrap:wrap;gap:3px;margin-bottom:6px;'>{bhtml}</div>",unsafe_allow_html=True)

        # Recent notifs
        notifs=st.session_state.notifications.get(user,[])
        if notifs:
            st.markdown("<div style='font-size:.58rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin-bottom:4px;'>🔔 RECENT</div>",unsafe_allow_html=True)
            for n in notifs[:2]:
                dot="🔵" if not n['read'] else "⚫"; bg="#f0fefe" if not n['read'] else "#f8fafc"
                st.markdown(f"""<div style="font-size:.68rem;color:#475569;padding:3px 6px;background:{bg};
                    border-radius:5px;margin-bottom:3px;border-left:2px solid {'#13ecec' if not n['read'] else '#e2e8f0'};">
                  {dot} {n['msg'][:45]}{'…' if len(n['msg'])>45 else ''}
                  <div style="font-size:.56rem;color:#94a3b8;">{n['time']}</div>
                </div>""",unsafe_allow_html=True)

        st.markdown("<div style='flex:1;'></div>",unsafe_allow_html=True)
        st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:4px 0;'>",unsafe_allow_html=True)
        if st.button("🚪  Logout",key=f"sb_out_{active}",use_container_width=True):
            st.session_state.current_user=None; navigate_to("login")

# ═══════════════════════════════════════════════════════════
#  PAGE HEADER
# ═══════════════════════════════════════════════════════════
def ph(title,sub=None,back=None):
    if back:
        if st.button(f"← Back to {back.title()}",key=f"back_{st.session_state.page}",type="secondary"):
            navigate_to(back)
    st.markdown(f"<h2 style='font-size:1.6rem;font-weight:800;color:#0f172a;margin:6px 0 2px;'>{title}</h2>"
                +(f"<p style='color:#64748b;font-size:.875rem;margin:0 0 .8rem;'>{sub}</p>" if sub else "<div style='margin-bottom:.8rem;'></div>"),
                unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
#  LOGIN
# ═══════════════════════════════════════════════════════════
def login_screen():
    if st.session_state.show_startup and st.session_state.show_startup_phase==0:
        pl=st.empty()
        for pct in range(0,102,2):
            pct=min(pct,100)
            pl.markdown(f"""<div style="position:fixed;inset:0;background:linear-gradient(135deg,#0f172a,#1e293b);
                display:flex;align-items:center;justify-content:center;z-index:9999;">
              <div style="text-align:center;">{LOGO.format(s=88)}
                <h1 style="font-size:2.4rem;font-weight:900;color:#fff;margin:1rem 0 .5rem;">Next Gen Sports Lab</h1>
                <p style="color:#13ecec;font-size:.95rem;margin-bottom:2rem;">Powered by Gemini AI</p>
                <div style="width:260px;height:5px;background:rgba(255,255,255,.12);border-radius:3px;overflow:hidden;margin:0 auto;">
                  <div style="width:{pct}%;height:100%;background:#13ecec;border-radius:3px;"></div></div>
                <div style="color:#13ecec;font-size:.75rem;margin-top:5px;">{pct}%</div>
              </div></div>""",unsafe_allow_html=True)
            time.sleep(0.012)
        time.sleep(0.3); st.session_state.show_startup_phase=1; st.rerun(); return

    if st.session_state.show_startup and st.session_state.show_startup_phase==1:
        bg_style = get_startup_bg_style()
        quotes=["Consistency beats talent when talent stops training.",
                "Train smart today. Perform stronger tomorrow.",
                "Recovery is not weakness — it is becoming stronger.",
                "Small improvements every day create champions."]
        q=quotes[int(time.time())%len(quotes)]
        st.markdown(f"""<div style="position:fixed;inset:0;{bg_style}
            display:flex;align-items:center;justify-content:flex-start;padding-left:8vw;z-index:9999;">
          <div style="max-width:620px;">
                        <div style="display:flex;align-items:center;gap:14px;margin-bottom:1rem;">
                            <div>{LOGO.format(s=64)}</div>
                            <p style="color:#13ecec;font-weight:800;font-size:2rem;letter-spacing:.03em;margin:0;">Coach Bot</p>
                        </div>
            <h1 style="font-size:2.8rem;font-weight:900;color:#fff;line-height:1.15;margin-bottom:1.5rem;">{q}</h1>
                        <p style="color:#c7d2fe;font-size:1rem;line-height:1.65;max-width:760px;">
                            Coach Bot is a smart, personalized fitness coaching web assistant powered by Generative AI (Gemini 3 Flash Preview).
                            It provides young athletes with sport-specific, position-aware, and injury-safe fitness plans, recovery-focused workouts,
                            tactical advice, and nutrition guidance to bridge the professional coaching gap for under-resourced and early-stage athletes.
                        </p>
          </div></div>
<style>
    div[data-testid="stButton"]{{position:fixed;left:calc(8vw);bottom:12%;z-index:10000;}}
  div[data-testid="stButton"]>button{{width:185px!important;border-radius:9999px!important;}}
</style>""",unsafe_allow_html=True)
        if st.button("Start your journey",type="primary",key="start_btn"):
            st.session_state.show_startup=False; st.session_state.show_startup_phase=0; st.rerun()
        return

    if st.session_state.show_loading:
        st.markdown(f"""<div style="position:fixed;inset:0;background:linear-gradient(135deg,#0f172a,#1e293b);
            display:flex;align-items:center;justify-content:center;z-index:9999;">
          <div style="text-align:center;">
            <div style="margin-bottom:1rem;">{LOGO.format(s=72)}</div>
            <h1 style="font-size:2rem;font-weight:900;color:#fff;">CoachBot</h1>
            <p style="color:#13ecec;font-size:.88rem;margin:.6rem 0 1.8rem;">Setting up your dashboard...</p>
            <div style="width:240px;height:4px;background:rgba(255,255,255,.1);border-radius:2px;overflow:hidden;margin:0 auto;">
              <div style="height:100%;background:#13ecec;animation:lb 2.5s ease forwards;"></div></div>
          </div></div>
<style>@keyframes lb{{from{{width:0%}}to{{width:100%}}}}</style>""",unsafe_allow_html=True)
        time.sleep(2.5); st.session_state.show_loading=False; navigate_to("dashboard"); return

    login_bg_style = get_startup_bg_style()
    st.markdown(f"""<style>
        .stApp, [data-testid="stAppViewContainer"]{{{login_bg_style} background-attachment:fixed!important;}}
        [data-testid="stAppViewContainer"] > .main{{background:transparent!important;}}
        .block-container{{padding-top:1.1rem!important;}}

        div[data-testid="stVerticalBlockBorderWrapper"]{{
            background:linear-gradient(180deg, rgba(255,255,255,.26) 0%, rgba(116,186,255,.20) 55%, rgba(8,19,38,.46) 100%)!important;
            border:1px solid rgba(255,255,255,.34)!important;
            border-radius:20px!important;
            box-shadow:0 18px 45px rgba(2,6,23,.46)!important;
            backdrop-filter:blur(15px)!important;
        }}

        .stTabs [data-baseweb="tab-list"]{{border-bottom:1px solid rgba(255,255,255,.25)!important;}}
        .stTabs [data-baseweb="tab"]{{color:#dbeafe!important;font-weight:700!important;}}
        .stTabs [aria-selected="true"]{{color:#67e8f9!important;border-bottom:2px solid #13ecec!important;}}

        .stTextInput label, .stTextInput label p, .stTextInput label span{{
            color:#f1f5f9!important;
            -webkit-text-fill-color:#f1f5f9!important;
        }}
        .stTextInput input, .stTextInput input[type="password"], .stTextInput input[type="text"]{{
            background:rgba(15,23,42,.55)!important;
            color:#ffffff!important;
            -webkit-text-fill-color:#ffffff!important;
            caret-color:#ffffff!important;
            border:1.4px solid rgba(191,219,254,.52)!important;
        }}
        .stTextInput input::placeholder{{
            color:#f1f5f9!important;
            -webkit-text-fill-color:#f1f5f9!important;
            opacity:1!important;
        }}
        .stTextInput input:focus::placeholder,
        .stTextInput input:active::placeholder,
        div[data-baseweb="base-input"]:focus-within input::placeholder,
        div[data-baseweb="input"]:focus-within input::placeholder{{
            color:transparent!important;
            -webkit-text-fill-color:transparent!important;
            opacity:0!important;
        }}

        .stFormSubmitButton > button,
        div[data-testid="stFormSubmitButton"] > button,
        div[data-testid="stFormSubmitButton"] button[kind="primary"],
        .stFormSubmitButton > button[kind="primary"]{{
            background:linear-gradient(135deg,#67e8f9,#38bdf8)!important;
            color:#082f49!important;
            border:none!important;
            box-shadow:0 8px 20px rgba(56,189,248,.35)!important;
            font-weight:800!important;
        }}
        .stFormSubmitButton > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover{{
            filter:brightness(1.06)!important;
            transform:translateY(-1px)!important;
        }}
    </style>""",unsafe_allow_html=True)

    st.markdown(f"""<div style="display:flex;align-items:center;gap:10px;padding:.85rem 1rem;border:1px solid rgba(255,255,255,.34);
        border-radius:14px;background:rgba(15,23,42,.36);backdrop-filter:blur(12px);margin-bottom:.9rem;">
        {LOGO.format(s=26)}<span style="font-size:1.2rem;font-weight:900;color:#f8fafc;">Coach Bot</span>
        <span style="font-size:.65rem;color:#67e8f9;font-weight:700;background:rgba(103,232,249,.14);padding:2px 10px;border-radius:20px;border:1px solid rgba(103,232,249,.45);margin-left:auto;">✨ Gemini 3 Flash Preview</span>
    </div>""",unsafe_allow_html=True)

    _,col,_=st.columns([1,2,1])
    with col:
        st.markdown("""<div style="text-align:center;margin:1.2rem 0 1rem;">
                    <h1 style="font-size:2rem;font-weight:900;color:#f8fafc;text-shadow:0 2px 14px rgba(2,6,23,.5);">Level Up Your Game</h1>
                    <p style="color:#dbeafe;font-size:.95rem;">Sign in to continue your Coach Bot journey</p>
        </div>""",unsafe_allow_html=True)
        with st.container(border=True):
            t1,t2=st.tabs(["🔑 Login","✨ Sign Up"])
            with t1:
                with st.form("login_form"):
                    st.text_input("Username",placeholder="Enter your username",key="login_username")
                    st.text_input("Password",type="password",placeholder="Enter your password",key="login_password")
                    if st.session_state.login_error: st.error(st.session_state.login_error)
                    st.form_submit_button("Login →",type="primary",on_click=submit_login,use_container_width=True)
            with t2:
                with st.form("signup_form"):
                    st.text_input("Full Name",placeholder="Your full name",key="signup_fullname")
                    st.text_input("Username",placeholder="Choose a username",key="signup_username")
                    st.text_input("Email",placeholder="Enter your mail",key="signup_email")
                    st.text_input("Password",type="password",placeholder="Enter your password",key="signup_password")
                    st.text_input("Confirm Password",type="password",placeholder="Confirm your password",key="signup_confirm")
                    if st.session_state.signup_error: st.error(st.session_state.signup_error)
                    st.form_submit_button("Create Account →",type="primary",on_click=submit_signup,use_container_width=True)

# ═══════════════════════════════════════════════════════════
#  ONBOARDING
# ═══════════════════════════════════════════════════════════
def onboarding_screen():
    if not st.session_state.current_user or st.session_state.current_user not in st.session_state.users:
        st.session_state.current_user=None; navigate_to("login"); return
    ud=st.session_state.users[st.session_state.current_user]
    st.markdown("""<h1 style="font-size:1.6rem;font-weight:800;color:#0f172a;margin:10px 0 3px;">Athlete Profile</h1>
    <p style="color:#64748b;margin-bottom:1rem;font-size:.875rem;">Tailor your AI coaching experience.</p>""",unsafe_allow_html=True)
    with st.form("ob_form"):
        c1,c2=st.columns(2)
        with c1: st.text_input("Full Name",value=ud['fullname'],key="pf_nm")
        with c2: st.number_input("Age",min_value=10,max_value=100,value=18,step=1,key="pf_age")
        c3,c4=st.columns(2)
        with c3:
            sp_list=sorted(["American Football","Athletics","Badminton","Baseball","Basketball",
                "Bodybuilding","Boxing","Cricket","CrossFit","Cycling","Football (Soccer)",
                "Golf","Gymnastics","Hockey","MMA","Powerlifting","Rugby","Running",
                "Skateboarding","Skiing","Snowboarding","Swimming","Table Tennis",
                "Tennis","Volleyball","Wrestling","Other"])
            ss=st.selectbox("Sport",sp_list,index=None,placeholder="Select sport",key="pf_sp")
            fs=ss
            if ss=="Other": fs=st.text_input("Specify sport",placeholder="e.g. Lacrosse",key="pf_sp2")
            elif not ss: fs=None
        with c4:
            pos_list=["Point Guard","Shooting Guard","Small Forward","Power Forward","Center",
                "Striker","Midfielder","Defender","Goalkeeper","Quarterback","Running Back",
                "Wide Receiver","Tight End","Linebacker","Pitcher","Catcher","Infielder",
                "Outfielder","Setter","Libero","Hitter","Blocker","N/A - Individual Sport","Other"]
            sp2=st.selectbox("Position",pos_list,index=None,placeholder="Select position",key="pf_pos")
            fp=sp2
            if sp2=="Other": fp=st.text_input("Specify position",placeholder="e.g. Winger",key="pf_pos2")
            elif not sp2: fp=None
        c5,c6=st.columns(2)
        with c5: st.selectbox("Training Intensity",["Low","Moderate","High"],index=1,key="pf_int")
        with c6: st.selectbox("Training Preference",["Gym / Indoor","Outdoor / Field","Hybrid"],index=0,key="pf_prf")
        st.text_area("Injury History (optional)",placeholder="Any past or current injuries...",height=70,key="pf_inj")
        c7,c8=st.columns(2)
        with c7: st.selectbox("Diet",["Standard","Vegetarian","Vegan","Keto","Paleo"],index=0,key="pf_diet")
        with c8: st.text_input("Allergies",placeholder="e.g. Peanuts, Dairy",key="pf_alg")
        goal_opts=["Improve Performance","Weight Loss","Muscle Gain","Injury Rehabilitation","Endurance Building"]
        st.selectbox("Primary Goal",goal_opts,index=0,key="pf_goal")
        st.checkbox("I agree my profile details are used to personalise coaching.",key="pf_ok")
        if st.session_state.get("pf_attempt"):
            if not st.session_state.get("pf_ok"): st.error("Please agree to the terms.")
            if not fs: st.error("Please select a sport.")
            if not fp: st.error("Please select a position.")
        def _v(): st.session_state.pf_attempt=True
        sub=st.form_submit_button("Save & Continue →",type="primary",on_click=_v,use_container_width=True)
        if sub and st.session_state.get("pf_ok") and fs and fp:
            u=st.session_state.current_user
            st.session_state.users[u]['profile']={
                'fullname':st.session_state.pf_nm,'age':st.session_state.pf_age,
                'sport':fs,'position':fp,'intensity':st.session_state.pf_int,
                'preference':st.session_state.pf_prf,'injury':st.session_state.pf_inj,
                'diet':st.session_state.pf_diet,'allergies':st.session_state.pf_alg,
                'goal':st.session_state.pf_goal,
            }
            ensure_tracker(u)
            st.session_state.pf_attempt=False
            add_notif(u,f"🎉 Welcome, {st.session_state.pf_nm}! Profile saved.","success")
            award_xp(u,'login'); navigate_to("dashboard")

# ═══════════════════════════════════════════════════════════
#  DASHBOARD
# ═══════════════════════════════════════════════════════════
def dashboard_screen():
    if not st.session_state.current_user or st.session_state.current_user not in st.session_state.users:
        st.session_state.current_user=None; navigate_to("login"); return
    sidebar("dashboard")
    user=st.session_state.current_user
    st.session_state.chat_history.setdefault(user,[])
    prof=st.session_state.users[user].get('profile') or {}
    sport=prof.get('sport','your sport'); goal=prof.get('goal') or 'Improve Performance'
    name=prof.get('fullname',user); d=get_xp(user)

    if not st.session_state.get(f"tutorial_shown_{user}"):
        @st.dialog("Welcome to Coach Bot! 🚀")
        def tutorial_dialog():
            st.markdown("""
            ### Your AI Coaching Journey Starts Here!
            
            Coach Bot is your personal, AI-powered sports performance assistant. Here's how to get the most out of it:
            
            *   **💬 Chat with Coach:** Ask for personalized workouts, nutrition advice, or recovery plans tailored to your sport and goals.
            *   **📊 Daily Tracker:** Log your water intake, meals, and exercises in the sidebar or the full tracker page.
            *   **⚡ Earn XP & Level Up:** Stay consistent! You earn XP by logging in, chatting, and completing your daily goals.
            *   **🏅 Badges:** Unlock special badges as you reach new milestones.
            
            Ready to level up your game?
            """)
            if st.button("Let's Go!", type="primary", use_container_width=True):
                st.session_state[f"tutorial_shown_{user}"] = True
                st.rerun()
        
        tutorial_dialog()

    st.markdown(f"""<div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;margin-bottom:1rem;">
      <div>
        <p style="color:#13ecec;font-weight:800;font-size:1.2rem;text-transform:uppercase;letter-spacing:.1em;margin-bottom:2px;">NEXT GEN SPORTS LAB · DASHBOARD</p>
        <h2 style="font-size:1.6rem;font-weight:800;color:#0f172a;margin:0;">Chat with Coach</h2>
      </div>
      <div style="display:flex;align-items:center;gap:8px;">
        <div style="display:flex;align-items:center;gap:6px;padding:4px 10px;background:white;border:1px solid #e2e8f0;border-radius:20px;">
          <div style="width:7px;height:7px;border-radius:50%;background:#22c55e;box-shadow:0 0 5px #22c55e;"></div>
          <span style="font-size:.67rem;font-weight:700;color:#0f172a;">Coach Online</span>
        </div>
        <span class="badge badge-teal">⚡ Lvl {d['level']} · {d['xp']} XP</span>
      </div>
    </div>""",unsafe_allow_html=True)

    col_chat,col_info=st.columns([3.15,1],gap="medium")

    with col_chat:
        st.markdown("""<div style="background:white;border-radius:12px;border:1px solid #e2e8f0;
            box-shadow:0 3px 14px rgba(15,23,42,.06);overflow:hidden;">
          <div style="display:flex;align-items:center;gap:9px;padding:10px 14px;border-bottom:1px solid #f1f5f9;background:#fafcff;">
            <div style="width:30px;height:30px;border-radius:8px;background:#13ecec;display:flex;align-items:center;justify-content:center;font-size:.88rem;">🤖</div>
            <div>
              <div style="font-weight:700;font-size:.83rem;color:#0f172a;">Coach <span style="font-size:.58rem;color:#22c55e;">● Live</span></div>
              <div style="font-size:.62rem;color:#64748b;">AI Coach · Gemini 3 Flash Preview</div>
            </div>
          </div>
          <div style="padding:11px 14px;display:flex;flex-direction:column;gap:7px;max-height:44vh;overflow-y:auto;">""",unsafe_allow_html=True)

        st.markdown(f"""<div style="background:#f0fefe;border-left:3px solid #13ecec;border-radius:0 8px 8px 8px;
            padding:9px 13px;font-size:.84rem;color:#334155;line-height:1.6;">
          <div style="font-weight:700;color:#0f172a;margin-bottom:2px;">🤖 Coach
            <span style="font-size:.6rem;color:#94a3b8;font-weight:400;margin-left:5px;">just now</span></div>
          Hey <strong>{name}</strong>! I'm your Gemini-powered AI coach. Goal:
          <strong style="color:#0d9488;">{goal}</strong> in <strong>{sport}</strong>.
          Ask me anything — drills, nutrition, recovery, strategy! 💪
        </div>""",unsafe_allow_html=True)

        for msg in st.session_state.chat_history[user]:
            if msg['role']=='user':
                st.markdown(f"""<div style="background:#f8fafc;border-left:3px solid #13ecec;border-radius:0 8px 8px 8px;
                    padding:8px 12px;font-size:.84rem;color:#334155;line-height:1.5;">
                  <div style="font-weight:700;color:#0f172a;margin-bottom:2px;">You
                    <span style="font-size:.6rem;color:#94a3b8;font-weight:400;margin-left:4px;">{msg['time']}</span></div>
                  {msg['text']}</div>""",unsafe_allow_html=True)
            else:
                st.markdown(f"""<div style="background:white;border:1px solid #e2e8f0;border-left:3px solid #0d9488;
                    border-radius:8px 8px 8px 0;padding:8px 12px;font-size:.84rem;color:#334155;line-height:1.5;">
                  <div style="font-weight:700;color:#0d9488;margin-bottom:2px;">🤖 Coach
                    <span style="font-size:.6rem;color:#94a3b8;font-weight:400;margin-left:4px;">{msg['time']}</span></div>
                  {msg['text']}</div>""",unsafe_allow_html=True)

        if st.session_state.get('ai_thinking'):
            st.markdown("""<div style="background:white;border:1px solid #e2e8f0;border-left:3px solid #0d9488;
                border-radius:8px;padding:9px 13px;display:inline-block;">
              <span style="font-size:.8rem;color:#64748b;">🤖 Thinking</span>
              <span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>""",unsafe_allow_html=True)

        st.markdown("</div></div>",unsafe_allow_html=True)

        if st.session_state.chat_history[user]:
            _,mc,_=st.columns([4,1,4])
            with mc:
                if st.button("🗑️ Clear",key="clr_ch"): st.session_state.chat_history[user]=[]; st.rerun()

    with col_info:
        d=get_xp(user)
        chats=st.session_state.chat_history[user]
        st.markdown(f"""<p style="font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;margin-bottom:5px;">SESSION STATS</p>
        <div style="background:linear-gradient(135deg,#0f172a,#1e293b);border-radius:9px;padding:11px;margin-bottom:8px;">
          <div style="font-size:.58rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin-bottom:2px;">YOUR LEVEL</div>
          <div style="font-size:1.3rem;font-weight:900;color:white;">Level {d['level']}</div>
          <div style="font-size:.66rem;color:#13ecec;margin-bottom:5px;">{d['xp']} XP total</div>
          <div style="height:4px;background:rgba(255,255,255,.1);border-radius:2px;overflow:hidden;">
            <div style="width:{min(int((d['xp']-LVL_XP[min(d['level']-1,len(LVL_XP)-1)])/max(LVL_XP[min(d['level'],len(LVL_XP)-1)]-LVL_XP[min(d['level']-1,len(LVL_XP)-1)],1)*100),100)}%;height:100%;background:#13ecec;border-radius:2px;"></div>
          </div>
        </div>""",unsafe_allow_html=True)

        st.markdown("""<p style="font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;margin-bottom:5px;">RECENT CHATS</p>
        <div style="background:#f8fafc;border-radius:9px;padding:8px;border:1px solid #e2e8f0;margin-bottom:8px;">""",unsafe_allow_html=True)
        if chats:
            for m in chats[-3:][::-1]:
                lbl="You" if m['role']=='user' else "Bot"; col2="#0f172a" if m['role']=='user' else "#0d9488"
                st.markdown(f"""<div style="padding:3px 0;border-bottom:1px solid #e2e8f0;font-size:.72rem;">
                  <span style="font-weight:700;color:{col2};">{lbl}</span>
                  <span style="color:#94a3b8;font-size:.58rem;"> {m['time']}</span>
                  <div style="color:#475569;margin-top:1px;">{m['text'][:45]}{'…' if len(m['text'])>45 else ''}</div>
                </div>""",unsafe_allow_html=True)
        else:
            st.markdown('<p style="font-size:.75rem;color:#94a3b8;margin:0;">No messages yet.</p>',unsafe_allow_html=True)
        st.markdown("</div>",unsafe_allow_html=True)

        st.markdown('<p style="font-size:.6rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;margin-bottom:5px;">QUICK ACTIONS</p>',unsafe_allow_html=True)
        if st.button("📊 Open Full Tracker",key="qa_tr",use_container_width=True): navigate_to("tracker")
        if st.button("⭐ Give Feedback",key="qa_fb",use_container_width=True): navigate_to("feedback")

    prompt=st.chat_input("Ask your coach anything about your performance...")
    if prompt and not st.session_state.get('ai_thinking'):
        now=datetime.now().strftime("%H:%M")
        st.session_state.chat_history[user].append({'role':'user','text':prompt,'time':now})
        st.session_state.ai_thinking=True; st.rerun()

    if st.session_state.get('ai_thinking'):
        history=st.session_state.chat_history[user]
        if history and history[-1]['role']=='user':
            reply=get_ai_response(history[-1]['text'],history[:-1],prof)
            now=datetime.now().strftime("%H:%M")
            st.session_state.chat_history[user].append({'role':'bot','text':reply,'time':now})
            pts=award_xp(user,'chat_msg'); add_notif(user,f"💬 +{pts} XP for chatting!")
        st.session_state.ai_thinking=False; st.rerun()

# ═══════════════════════════════════════════════════════════
#  TRACKER  (full page)
# ═══════════════════════════════════════════════════════════
def tracker_screen():
    if not st.session_state.current_user or st.session_state.current_user not in st.session_state.users:
        st.session_state.current_user=None; navigate_to("login"); return
    sidebar("tracker")
    user=st.session_state.current_user
    ensure_tracker(user)
    data=st.session_state.tracker_data[user]; d=get_xp(user)
    ph("Daily Tracker","Log your nutrition, hydration & workouts.",back="dashboard")

    total_cal=sum(e.get('calories',0) for e in data['food_log'])
    done_ex=sum(1 for e in data['exercises'] if e.get('completed'))
    water_pct=min(int(data['water']/3000*100),100)

    st.markdown(f"""<div style="display:flex;gap:8px;margin-bottom:1rem;flex-wrap:wrap;">
      <div style="background:white;border-radius:9px;padding:9px 14px;border:1px solid #e2e8f0;flex:1;min-width:80px;text-align:center;">
        <div style="font-size:1.1rem;font-weight:800;color:#0f172a;">{total_cal}</div>
        <div style="font-size:.6rem;color:#64748b;font-weight:600;">🔥 kcal</div></div>
      <div style="background:white;border-radius:9px;padding:9px 14px;border:1px solid {'#22c55e' if water_pct>=100 else '#e2e8f0'};flex:1;min-width:80px;text-align:center;">
        <div style="font-size:1.1rem;font-weight:800;color:{'#22c55e' if water_pct>=100 else '#0f172a'};">{data['water']}ml</div>
        <div style="font-size:.6rem;color:#64748b;font-weight:600;">💧 water</div></div>
      <div style="background:white;border-radius:9px;padding:9px 14px;border:1px solid #e2e8f0;flex:1;min-width:80px;text-align:center;">
        <div style="font-size:1.1rem;font-weight:800;color:#0f172a;">{done_ex}/{len(data['exercises'])}</div>
        <div style="font-size:.6rem;color:#64748b;font-weight:600;">✅ done</div></div>
      <div style="background:#e0fffe;border-radius:9px;padding:9px 14px;border:1px solid #13ecec;flex:1;min-width:80px;text-align:center;">
        <div style="font-size:1.1rem;font-weight:800;color:#0f172a;">{d['xp']} XP</div>
        <div style="font-size:.6rem;color:#0d9488;font-weight:600;">⚡ Lvl {d['level']}</div></div>
    </div>""",unsafe_allow_html=True)

    t1,t2,t3=st.tabs(["🍎 Food Log","💧 Water","🏋️ Exercises"])

    with t1:
        with st.form("food_f"):
            st.markdown("""<div style='margin:6px 0 10px;padding:8px 10px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'>
              <span style='font-size:.86rem;font-weight:800;color:#0f172a;'>Add Food Entry</span>
            </div>""", unsafe_allow_html=True)
            fn=st.text_input("Food item",placeholder="e.g. Grilled Chicken")
            c1,c2,c3,c4=st.columns(4)
            with c1: cal=st.number_input("Calories",min_value=0,step=10,value=0)
            with c2: pro=st.number_input("Protein g",min_value=0,step=1,value=0)
            with c3: crb=st.number_input("Carbs g",min_value=0,step=1,value=0)
            with c4: fat=st.number_input("Fat g",min_value=0,step=1,value=0)
            if st.form_submit_button("➕ Add Food",type="primary",use_container_width=True):
                if fn.strip():
                    data['food_log'].append({'name':fn,'calories':cal,'protein':pro,'carbs':crb,'fat':fat,'time':datetime.now().strftime("%H:%M")})
                    pts=award_xp(user,'food_logged'); d2=get_xp(user); d2['meals_logged']=d2.get('meals_logged',0)+1
                    add_notif(user,f"🍎 +{pts} XP — {fn} ({cal} kcal)"); st.rerun()
        if data['food_log']:
            for i,e in enumerate(data['food_log']):
                ca,cb=st.columns([5,1])
                with ca:
                    st.markdown(f"""<div style="background:white;border-radius:7px;padding:8px 12px;border:1px solid #e2e8f0;margin-bottom:4px;font-size:.82rem;color:#334155;">
                      <strong style="color:#0f172a;">{e['time']}</strong> · {e['name']}
                      <span style="float:right;color:#64748b;font-size:.72rem;">{e['calories']} kcal · P:{e['protein']}g C:{e['carbs']}g F:{e['fat']}g</span>
                    </div>""",unsafe_allow_html=True)
                with cb:
                    if st.button("🗑️",key=f"df{i}"): data['food_log'].pop(i); st.rerun()
        else: st.info("No food entries yet.")

    with t2:
        goal_w=3000; pct=min(data['water']/goal_w,1.0)
        col2="#22c55e" if pct>=1 else "#13ecec" if pct>=0.5 else "#f59e0b"
        st.markdown(f"""<div style="text-align:center;margin:.8rem 0 1.2rem;">
          <div style="font-size:3rem;font-weight:900;color:{col2};">{data['water']}</div>
          <div style="color:#64748b;font-size:.88rem;font-weight:600;">ml of {goal_w}ml goal</div>
          <div style="margin:10px auto;width:100%;max-width:320px;height:10px;background:#e2e8f0;border-radius:5px;overflow:hidden;">
            <div style="width:{int(pct*100)}%;height:100%;background:{col2};border-radius:5px;"></div></div>
          <div style="font-size:.75rem;color:#64748b;">{int(pct*100)}% of daily goal</div>
        </div>""",unsafe_allow_html=True)
        c1,c2,c3,c4=st.columns(4)
        for cw,amt in zip([c1,c2,c3,c4],[150,250,500,750]):
            with cw:
                if st.button(f"+{amt}ml",key=f"w{amt}",use_container_width=True):
                    data['water']+=amt; award_xp(user,'water_500',amt//60); _check_badges(user,get_xp(user)); st.rerun()
        if st.button("🔄 Reset Water",use_container_width=True): data['water']=0; st.rerun()

    with t3:
        with st.form("ex_f"):
            st.markdown("**Add Custom Exercise**")
            en=st.text_input("Exercise name",placeholder="e.g. Bench Press")
            c1,c2,c3=st.columns(3)
            with c1: sets=st.number_input("Sets",min_value=1,value=3,step=1)
            with c2: reps=st.number_input("Reps",min_value=1,value=10,step=1)
            with c3: wt_kg=st.number_input("Weight (kg)",min_value=0,value=0,step=5)
            notes=st.text_area("Notes (optional)",height=55)
            if st.form_submit_button("➕ Add Exercise",type="primary",use_container_width=True):
                if en.strip():
                    data['exercises'].append({'name':en,'sets':sets,'reps':reps,'weight':wt_kg,'notes':notes,'completed':False,'time':datetime.now().strftime("%H:%M")})
                    add_notif(user,f"🏋️ Added: {en} ({sets}×{reps})"); st.rerun()
        st.markdown("""<div style='margin:10px 0 8px;padding:8px 10px;background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;'>
            <span style='font-size:.86rem;font-weight:800;color:#0f172a;'>Today's Workout Plan</span>
        </div>""", unsafe_allow_html=True)
        if data['exercises']:
            for i,ex in enumerate(data['exercises']):
                ca,cb,cc=st.columns([5,1,1])
                with ca:
                    wts=f"@ {ex['weight']}kg" if ex['weight']>0 else ""
                    nt=f'<br><span style="font-size:.67rem;color:#64748b;">{ex["notes"]}</span>' if ex['notes'] else ''
                    bg="#f0fdf4" if ex['completed'] else "white"; bd="#bbf7d0" if ex['completed'] else "#e2e8f0"
                    tick="✅" if ex['completed'] else "⭕"
                    st.markdown(f"""<div style="background:{bg};border-radius:7px;padding:8px 12px;border:1px solid {bd};margin-bottom:4px;font-size:.84rem;">
                      {tick} <strong style="color:#0f172a;">{ex['name']}</strong>
                      <span style="color:#64748b;font-size:.73rem;"> {ex['sets']}×{ex['reps']} {wts}</span>{nt}
                    </div>""",unsafe_allow_html=True)
                with cb:
                    if not ex['completed']:
                        if st.button("✓",key=f"ck{i}"):
                            ex['completed']=True; pts=award_xp(user,'exercise_done')
                            d2=get_xp(user); d2['exercises_done']=d2.get('exercises_done',0)+1
                            _check_badges(user,d2); add_notif(user,f"✅ +{pts} XP — {ex['name']}"); st.rerun()
                with cc:
                    if st.button("🗑️",key=f"dx{i}"): data['exercises'].pop(i); st.rerun()
        else: st.info("No exercises yet. Add one above!")

# ═══════════════════════════════════════════════════════════
#  FEEDBACK
# ═══════════════════════════════════════════════════════════
def feedback_screen():
    if not st.session_state.current_user or st.session_state.current_user not in st.session_state.users:
        st.session_state.current_user=None; navigate_to("login"); return
    sidebar("feedback"); user=st.session_state.current_user
    ph("Share Feedback","Help calibrate your coaching experience.",back="dashboard")
    
    # Star rating (OUTSIDE form - buttons can't be in forms)
    st.markdown("""<div style='margin:10px 0 12px;padding:8px 10px;background:#0f172a;border:1px solid #1e293b;border-radius:8px;'>
        <span style='font-size:.84rem;font-weight:700;color:#e2e8f0;'>⭐ Experience Rating</span>
    </div>""", unsafe_allow_html=True)
    
    st.markdown("<div style='text-align:center;margin:8px 0;'><span style='font-size:.75rem;color:#64748b;font-weight:600;'>Quick Rate (Click a star)</span></div>", unsafe_allow_html=True)
    sr1, sr2, sr3, sr4, sr5 = st.columns(5)
    with sr1:
        if st.button("⭐", key="r1", use_container_width=True): st.session_state["feedback_rating"] = 1.0
    with sr2:
        if st.button("⭐⭐", key="r2", use_container_width=True): st.session_state["feedback_rating"] = 2.0
    with sr3:
        if st.button("⭐⭐⭐", key="r3", use_container_width=True): st.session_state["feedback_rating"] = 3.0
    with sr4:
        if st.button("⭐⭐⭐⭐", key="r4", use_container_width=True): st.session_state["feedback_rating"] = 4.0
    with sr5:
        if st.button("⭐⭐⭐⭐⭐", key="r5", use_container_width=True): st.session_state["feedback_rating"] = 5.0
    
    # Show current rating
    current_rating = st.session_state.get("feedback_rating", 4.0)
    stars = "⭐" * int(current_rating) + "☆" * (5 - int(current_rating))
    st.markdown(f"<div style='background:#e0fffe;border:2px solid #13ecec;border-radius:8px;padding:10px 13px;text-align:center;margin:8px 0 12px;'><span style='font-size:1.2rem;'>{stars}</span><br><strong style='color:#0f172a;'>{current_rating}/5 Stars</strong></div>", unsafe_allow_html=True)
    
    # Form (sliders and inputs INSIDE form)
    with st.form("fb_f"):
        comments=st.text_area("Your Thoughts",placeholder="What's working? What could improve?",height=130)
        rating = st.slider("Fine-tune Rating", 1.0, 5.0, current_rating, 0.5, label_visibility="visible")
        c1, c2 = st.columns(2)
        with c1: cat=st.selectbox("Category",["General","Training","Nutrition","Recovery","UI/UX","Other"],key="fb_cat")
        with c2: st.selectbox("Priority",["Low","Medium","High"],index=1,key="fb_pri")
        if st.form_submit_button("🚀 Submit Feedback",type="primary",use_container_width=True):
            if comments.strip():
                pts=award_xp(user,'feedback'); d2=get_xp(user)
                if 'feedback_giver' not in d2.get('badges',[]): d2.setdefault('badges',[]).append('feedback_giver')
                add_notif(user,f"📨 +{pts} XP — {cat} feedback received!","success"); st.success(f"✅ Thank you! +{pts} XP earned.")
            else: st.warning("Please share your thoughts before submitting.")

# ═══════════════════════════════════════════════════════════
#  SETTINGS
# ═══════════════════════════════════════════════════════════
def settings_screen():
    if not st.session_state.current_user or st.session_state.current_user not in st.session_state.users:
        st.session_state.current_user=None; navigate_to("login"); return
    sidebar("settings"); user=st.session_state.current_user
    u=st.session_state.users[user]; p=u.get('profile') or {}; d=get_xp(user)
    ph("Settings",back="dashboard")

    st.markdown("<p style='font-size:.62rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin-bottom:7px;'>ACCOUNT</p>",unsafe_allow_html=True)
    with st.container(border=True):
        c1,c2=st.columns([3,1])
        with c1: nn=st.text_input("Display Name",value=p.get('fullname',u.get('fullname',user)),key="sn")
        with c2:
            st.markdown("<div style='height:27px;'></div>",unsafe_allow_html=True)
            if st.button("Save",key="sv_nm",type="primary"):
                (u['profile'] if u.get('profile') else u)['fullname']=nn
                save_users_to_file(st.session_state.users)
                add_notif(user,"✏️ Name updated."); st.success("Saved!")
        st.markdown(f"<div style='padding:8px 0;border-top:1px solid #f1f5f9;margin-top:4px;'><strong style='font-size:.83rem;'>Email</strong><br><span style='color:#64748b;font-size:.78rem;'>{u.get('email','')}</span></div>",unsafe_allow_html=True)

    st.markdown("<p style='font-size:.62rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin:1rem 0 7px;'>PROFILE PREFERENCES</p>",unsafe_allow_html=True)
    with st.container(border=True):
        current_sport = p.get('sport', 'Athletics')
        sport_options = ["Athletics","Football (Soccer)","Cricket","Basketball","Swimming","Tennis","Volleyball","Other"]
        if current_sport not in sport_options:
            sport_options.append(current_sport)
        c1,c2 = st.columns(2)
        with c1:
            sp = st.selectbox("Sport", sport_options, index=sport_options.index(current_sport), key="set_sport")
            intensity_options = ["Low","Moderate","High"]
            current_intensity = p.get('intensity', 'Moderate')
            if current_intensity not in intensity_options:
                intensity_options.append(current_intensity)
            intensity = st.selectbox("Training Intensity", intensity_options, index=intensity_options.index(current_intensity), key="set_intensity")
            diet_options = ["Standard","Vegetarian","Vegan","Keto","Paleo"]
            current_diet = p.get('diet', 'Standard')
            if current_diet not in diet_options:
                diet_options.append(current_diet)
            diet = st.selectbox("Nutrition / Diet", diet_options, index=diet_options.index(current_diet), key="set_diet")
        with c2:
            pos = st.text_input("Position", value=p.get('position',''), key="set_position", placeholder="e.g. Striker / Bowler")
            goal_options = ["Improve Performance","Weight Loss","Muscle Gain","Injury Rehabilitation","Endurance Building"]
            current_goal = p.get('goal', 'Improve Performance')
            if current_goal not in goal_options:
                goal_options.append(current_goal)
            goal = st.selectbox("Primary Goal", goal_options, index=goal_options.index(current_goal), key="set_goal")
            allergies = st.text_input("Allergies", value=p.get('allergies',''), key="set_allergies", placeholder="e.g. Peanuts")

        if st.button("Save Profile Preferences", key="sv_profile", type="primary", use_container_width=True):
            u.setdefault('profile', {})
            u['profile'].update({
                'sport': sp,
                'position': pos.strip(),
                'intensity': intensity,
                'diet': diet,
                'goal': goal,
                'allergies': allergies.strip(),
            })
            save_users_to_file(st.session_state.users)
            add_notif(user, "⚙️ Profile preferences updated.", "success")
            st.success("Profile settings saved.")

    st.markdown("<p style='font-size:.62rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin:1rem 0 7px;'>INJURIES & RECOVERY</p>",unsafe_allow_html=True)
    with st.container(border=True):
        injuries = p.get('injuries', [])
        st.markdown("<span style='font-size:.78rem;color:#64748b;'>Track current injuries to help AI personalize your training.</span>",unsafe_allow_html=True)
        
        # Display current injuries
        if injuries:
            st.markdown("<div style='font-size:.8rem;font-weight:700;color:#0f172a;margin:8px 0 6px;'>Current Injuries:</div>",unsafe_allow_html=True)
            for idx, injury in enumerate(injuries):
                col1, col2, col3 = st.columns([2, 1, 1])
                with col1:
                    st.markdown(f"<div style='font-size:.78rem;color:#0f172a;background:#fff4f4;border-left:3px solid #ef4444;border-radius:4px;padding:6px 8px;margin-bottom:5px;font-weight:600;'>🩹 {injury}</div>", unsafe_allow_html=True)
                with col2:
                    pass
                with col3:
                    if st.button("Remove", key=f"rm_inj_{idx}", use_container_width=True):
                        injuries.pop(idx)
                        u.setdefault('profile', {})['injuries'] = injuries
                        save_users_to_file(st.session_state.users)
                        add_notif(user, f"Injury '{injury}' removed.", "info")
                        st.rerun()
        
        # Add new injury
        c1, c2 = st.columns([3, 1])
        with c1:
            new_injury = st.text_input("Add New Injury", placeholder="e.g. Right shoulder strain", key="new_injury_input")
        with c2:
            st.markdown("<div style='height:7px;'></div>", unsafe_allow_html=True)
            if st.button("Add", key="add_injury_btn", use_container_width=True):
                if new_injury.strip():
                    if new_injury.strip() not in injuries:
                        injuries.append(new_injury.strip())
                        u.setdefault('profile', {})['injuries'] = injuries
                        save_users_to_file(st.session_state.users)
                        add_notif(user, f"📍 Injury '{new_injury.strip()}' added.", "info")
                        st.rerun()
                    else:
                        st.warning("This injury is already tracked.")
                else:
                    st.warning("Please enter an injury name.")

    st.markdown("<p style='font-size:.62rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin:1rem 0 7px;'>ACHIEVEMENTS</p>",unsafe_allow_html=True)
    with st.container(border=True):
        lo=LVL_XP[min(d['level']-1,len(LVL_XP)-1)]; hi=LVL_XP[min(d['level'],len(LVL_XP)-1)]
        pct2=int(min((d['xp']-lo)/max(hi-lo,1)*100,100))
        icon='👑' if d['level']>=10 else '⭐' if d['level']>=5 else '🏅'
        st.markdown(f"""
            <div style="display:flex;justify-content:space-between;align-items:center;background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:10px 12px;margin-bottom:8px;">
                <div>
                    <div style='font-weight:800;color:#0f172a;font-size:.9rem;'>Level {d['level']} Athlete</div>
                    <div style='color:#64748b;font-size:.72rem;'>{d['xp']} total XP</div>
                </div>
                <div style="font-size:1.8rem;">{icon}</div>
            </div>
            <div style="height:7px;background:#e2e8f0;border-radius:4px;overflow:hidden;margin-bottom:4px;">
                <div style="width:{pct2}%;height:100%;background:linear-gradient(90deg,#13ecec,#06b6d4);border-radius:4px;"></div>
            </div>
            <div style="font-size:.69rem;color:#64748b;margin-bottom:10px;">{pct2}% to Level {d['level']+1}</div>
            """,unsafe_allow_html=True)
        earned=d.get('badges',[])
        
        # Earned Badges Section
        st.markdown("<div style='font-size:.85rem;font-weight:800;color:#0f172a;margin:12px 0 8px;'>🏆 Earned Badges</div>",unsafe_allow_html=True)
        if earned:
            badge_cols = st.columns(3)
            for idx, bid in enumerate(earned):
                b=BADGES_DEF.get(bid,('🏅','Badge','','teal'))
                with badge_cols[idx % 3]:
                    st.markdown(f"""
                    <div style='display:flex;flex-direction:column;align-items:center;gap:6px;background:linear-gradient(135deg,#e0fffe,#ccfafa);border:2px solid #13ecec;border-radius:10px;padding:10px;text-align:center;'>
                        <div style='font-size:1.8rem;'>{b[0]}</div>
                        <div style='font-size:.7rem;font-weight:800;color:#0f172a;'>{b[1]}</div>
                        <div style='font-size:.6rem;color:#0d9488;'>{b[2]}</div>
                    </div>
                    """,unsafe_allow_html=True)
        else:
            st.markdown("<p style='font-size:.78rem;color:#94a3b8;padding:10px;background:#f8fafc;border-radius:8px;'>🎯 Complete challenges to earn badges!</p>",unsafe_allow_html=True)
        
        # Locked Badges Section
        st.markdown("<div style='font-size:.85rem;font-weight:800;color:#0f172a;margin:14px 0 8px;'>🔒 Locked Badges (Unlock These!)</div>",unsafe_allow_html=True)
        locked_badges = [(k, v) for k, v in BADGES_DEF.items() if k not in earned]
        if locked_badges:
            lock_cols = st.columns(3)
            for idx, (bid, b) in enumerate(locked_badges):
                with lock_cols[idx % 3]:
                    st.markdown(f"""
                    <div style='display:flex;flex-direction:column;align-items:center;gap:6px;background:#f1f5f9;border:2px dashed #94a3b8;border-radius:10px;padding:10px;text-align:center;opacity:0.7;'>
                        <div style='font-size:1.8rem;filter:grayscale(100%);'>🔐 {b[0]}</div>
                        <div style='font-size:.7rem;font-weight:800;color:#64748b;'>{b[1]}</div>
                        <div style='font-size:.59rem;color:#94a3b8;line-height:1.3;'>{b[2]}</div>
                    </div>
                    """,unsafe_allow_html=True)
        else:
            st.markdown("<p style='font-size:.78rem;color:#22c55e;padding:10px;background:#f0fdf4;border-radius:8px;font-weight:700;'>✅ You've unlocked all badges! Amazing work!</p>",unsafe_allow_html=True)
        
        st.markdown("<div style='font-size:.78rem;font-weight:800;color:#0f172a;margin:12px 0 6px;'>🎯 Ways to Earn XP</div>",unsafe_allow_html=True)
        for act,pts in XP_REWARDS.items():
            st.markdown(f"<div style='font-size:.72rem;color:#0f172a;background:#e0fffe;border-left:3px solid #13ecec;border-radius:5px;padding:6px 8px;margin-bottom:4px;font-weight:600;'>+{pts} XP — {act.replace('_',' ').title()}</div>",unsafe_allow_html=True)

    # Gemini status
    has_key=bool(get_gemini_key()) and get_gemini_key()!="your-gemini-api-key-here"
    st.markdown("<p style='font-size:.62rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin:1rem 0 7px;'>GEMINI AI STATUS</p>",unsafe_allow_html=True)
    if has_key: st.success("✅ Gemini 3 Flash Preview connected via .streamlit/secrets.toml")
    else: st.warning("⚠️ Set GEMINI_API_KEY in .streamlit/secrets.toml — get a free key at aistudio.google.com")

    st.markdown("<p style='font-size:.62rem;font-weight:700;text-transform:uppercase;color:#94a3b8;margin:1rem 0 7px;'>NOTIFICATIONS</p>",unsafe_allow_html=True)
    notifs=st.session_state.notifications.get(user,[])
    if notifs:
        with st.container(border=True):
            ca,cb=st.columns([4,1])
            with ca: st.markdown(f"<b style='color:#0f172a;'>{len(notifs)}</b> total (<span style='color:#0f172a;'>{unread(user)} unread</span>)",unsafe_allow_html=True)
            with cb:
                if st.button("Mark read",key="mr"): mark_read(user); st.rerun()
            for n in notifs[:8]:
                ic="🔵" if not n['read'] else "⚪"
                bg = "#f0fefe" if not n['read'] else "#ffffff"
                st.markdown(f"""
                <div style='padding:7px 8px;margin-bottom:5px;background:{bg};border:1px solid #e2e8f0;border-radius:8px;'>
                  <div style='font-size:.77rem;color:#334155;line-height:1.35;'>{ic} {n['msg']}</div>
                  <div style='font-size:.63rem;color:#94a3b8;margin-top:3px;'>{n['time']}</div>
                </div>
                """,unsafe_allow_html=True)
    else: st.info("No notifications yet.")

    st.markdown("<p style='font-size:.62rem;font-weight:700;text-transform:uppercase;color:#ef4444;margin:1rem 0 7px;'>DANGER ZONE</p>",unsafe_allow_html=True)
    with st.container(border=True):
        st.markdown("<p style='font-size:.75rem;color:#64748b;margin-bottom:8px;'>Use these actions carefully. They permanently remove your current data.</p>",unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ Clear Chat History",key="clrch",use_container_width=True):
                st.session_state.chat_history[user]=[]; add_notif(user,"Chat history cleared."); st.success("Cleared.")
        with c2:
            if st.button("🔄 Reset Today's Tracker",key="rsttk",use_container_width=True):
                ensure_tracker(user); exs=copy.deepcopy(DEFAULT_EX); now_t=datetime.now().strftime("%H:%M")
                for e in exs: e['time']=now_t
                st.session_state.tracker_data[user]={'food_log':[],'water':0,'exercises':exs}
                add_notif(user,"Tracker reset."); st.success("Tracker reset!")

# ═══════════════════════════════════════════════════════════
#  ROUTER
# ═══════════════════════════════════════════════════════════
if __name__=="__main__":
    pg=st.session_state.page
    if   pg=='login':      login_screen()
    elif pg=='onboarding': onboarding_screen()
    elif pg=='dashboard':  dashboard_screen()
    elif pg=='tracker':    tracker_screen()
    elif pg=='feedback':   feedback_screen()

    elif pg=='settings':   settings_screen()
