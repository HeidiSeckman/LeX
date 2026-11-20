import os
import base64
import urllib.parse
from datetime import date
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from audio_engine import ANTHEM_TRACKS, generate_anthem_wav

st.set_page_config(page_title="LeX // Social by LexiTech Studio", page_icon="✦", layout="wide")
ST_OPEN = "<" + "style>"
ST_CLOSE = "<" + "/style>"
LK_OPEN = "<" + "link "
SV_OPEN = "<" + "svg "
SV_CLOSE = "<" + "/svg>"
SC_OPEN = "<" + "script>"
SC_CLOSE = "<" + "/script>"
SVG_NS = "http://" + ".".join(["www", "w3", "org"]) + "/2000/svg"
GFONTS_BASE = "https://" + ".".join(["fonts", "googleapis", "com"]) + "/css2?family="
SPOTIFY_EMBED = "https://" + ".".join(["open", "spotify", "com"]) + "/embed/track/"
YT_EMBED_BASE = "https://" + ".".join(["www", "youtube-nocookie", "com"]) + "/embed/"
LEXITECH_HUB_URL = "https://" + ".".join(["heidiseckman", "github", "io"]) + "/lexitech-hub/"
MAX_FRIENDS = 1000

SEVERE_BLOCKED_TERMS = {
    "rape", "raping", "rapist", "molest", "pedophile", "pedo", "csam",
    "murder", "murdering", "homicide", "kill yourself", "kys", "suicide",
    "mass shooting", "school shooting", "behead", "dismember", "gore",
    "bestiality", "necrophilia", "nigger", "faggot", "kike", "chink"
}
NSFW_DRESS_CODE_TERMS = {
    "onlyfans", "only fans", "fansly", "manyvids", "chaturbate", "pornhub",
    "xvideos", "xnxx", "camgirl", "cam girl", "nsfw", "nude", "nudes",
    "naked", "topless", "bottomless", "lingerie", "bikini", "thong",
    "cleavage", "nipple", "nipples", "boobs", "tits", "pussy", "dick",
    "cock", "penis", "vagina", "porn", "porno", "hentai", "xxx", "erotic",
    "erotica", "stripper", "stripping", "fetish", "bdsm", "lewd", "upskirt",
    "sideboob", "underboob", "explicit", "18+ content", "playboy", "sex tape"
}
def clean_handle_str(raw: str) -> str:
    s = (raw or "").strip().lstrip("@")
    safe = "".join(c for c in s if c.isalnum() or c in ("_", "."))
    return safe[:24]

def is_handle_taken(sb_client, raw_handle: str, exclude_uid: str = "") -> bool:
    ch = clean_handle_str(raw_handle)
    if not ch or not sb_client:
        return True
    res = sb_client.table("lex_profiles").select("user_id, handle").ilike("handle", f"@{ch}").execute().data or []
    for row in res:
        if exclude_uid and str(row.get("user_id", "")) == str(exclude_uid):
            continue
        return True
    return False

def check_safety_and_dress_code(text_val: str, extra_name: str = ""):
    blob = " ".join(f"{text_val or ''} {extra_name or ''}".lower().split())
    for term in SEVERE_BLOCKED_TERMS | NSFW_DRESS_CODE_TERMS:
        if term in blob:
            return False, "Blocked by LeX Safety & Dress Code Shield: nudity, adult links, and severe violence are not allowed."
    return True, ""

def scan_image_safely(uploaded_file, caption_text: str = ""):
    if uploaded_file is None:
        return True, ""
    fname = getattr(uploaded_file, "name", "")
    mime = str(getattr(uploaded_file, "type", ""))
    if not mime.startswith("image/"):
        return False, "Only valid image files are permitted."
    ok_txt, msg_txt = check_safety_and_dress_code(caption_text, fname)
    if not ok_txt:
        return False, msg_txt
    api_u = st.secrets.get("SIGHTENGINE_USER", "")
    api_s = st.secrets.get("SIGHTENGINE_SECRET", "")
    if api_u and api_s:
        try:
            r = requests.post(
                "https://sightengine.com",
                files={"media": (fname, uploaded_file.getvalue())},
                data={"models": "nudity-2.1,gore-2.0", "api_user": api_u, "api_secret": api_s},
                timeout=12,
            )
            jd = r.json() if r.status_code == 200 else {}
            nud = jd.get("nudity") or {}
            gor = jd.get("gore") or {}
            scores = [
                nud.get("sexual_activity", 0), nud.get("sexual_display", 0),
                nud.get("erotica", 0), nud.get("very_suggestive", 0),
                nud.get("mildly_suggestive", 0), gor.get("prob", 0),
            ]
            if any(float(sc or 0) > 0.25 for sc in scores):
                return False, "Upload rejected: Everyone on LeX must be fully dressed. Nudity, swimwear, lingerie, and suggestive photos are prohibited."
        except Exception:
            pass
    return True, ""
def get_blocked_handles() -> set:
    bl = st.session_state.lex_theme.get("blocked_users") or []
    return {str(x).strip().lower() for x in bl if x}

def block_or_report_member(target_handle: str, mode: str, reason: str = ""):
    th_ref = st.session_state.lex_theme
    tgt = "@" + clean_handle_str(target_handle)
    if len(tgt) <= 1:
        return
    if mode == "block":
        cur = list(th_ref.get("blocked_users") or [])
        if tgt.lower() not in {x.lower() for x in cur}:
            cur.append(tgt)
        th_ref["blocked_users"] = cur
        st.session_state.lex_friends = [f for f in st.session_state.lex_friends if f.get("handle", "").lower() != tgt.lower()]
        st.session_state.lex_top8 = [t for t in st.session_state.lex_top8 if t.get("handle", "").lower() != tgt.lower()]
        th_ref["following"] = [x for x in (th_ref.get("following") or []) if x.lower() != tgt.lower()]
    elif mode == "report":
        reps = list(th_ref.get("reports_log") or [])
        reps.append({"target": tgt, "reason": (reason or "Reported by member")[:240], "date": str(date.today())})
        th_ref["reports_log"] = reps
    save_profile_to_cloud()

@st.cache_resource
def get_sb():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key) if (url and key) else None

FONT_MAP = {
    "Clean Studio Sans": ("Inter", "'Inter', sans-serif"),
    "Girl Punk / Spray Marker": ("Permanent Marker", "'Permanent Marker', cursive"),
    "Cyber Glitch": ("Rubik Glitch", "'Rubik Glitch', system-ui"),
    "Y2K Arcade Pixel": ("Press Start 2P", "'Press Start 2P', monospace"),
    "Gothic Editorial": ("Cinzel", "'Cinzel', serif"),
    "Futuristic Orbitron": ("Orbitron", "'Orbitron', sans-serif"),
}
BACKDROP_OPTIONS = [
    "Architectural Grid", "Punk Spray-Paint Graffiti", "Y2K Stars & Sparkles",
    "Leopard Rosette Print", "Cherry Hearts & Kisses", "Coquette Ribbon Bows",
    "Butterfly Dreamscape", "Checkered Ska / Vans", "Skull & Crossbones Punk",
    "Lightning Bolts & Voltage", "Gothic Bats & Moons", "Cyber Matrix Rain",
    "Carbon Fiber Hex", "Retro Cassette & Vinyl", "Flame & Hotrod Stripes",
    "Crown & Diamond Luxe", "Rose Thorns & Petals", "8-Bit Arcade Invaders",
    "Tactical Urban Camo", "Cosmic Planets & Rings",
]
DEFAULT_LEFT = ["Profile Card", "Photo Albums", "Profile Anthem", "Profile Wall"]
DEFAULT_RIGHT = ["Top 8 Friends", "Main Social Hub"]
DEFAULT_THEME = {
    "name": "LexiTech Obsidian (Official)", "bg": "#000000", "card": "#070709",
    "accent": "#EC4899", "text": "#F4F4F5", "font": "Clean Studio Sans",
    "backdrop": "Architectural Grid", "border_style": "solid", "glow_borders": True,
    "card_opacity": 92, "card_radius": 12,
    "marquee_text": "✦ WELCOME TO MY LeX PROFILE // ZERO ALGORITHMS ✦",
    "marquee_on": True, "pinned_note": "", "custom_css": "",
    "int_general": "", "int_music": "", "int_movies": "", "int_tv": "", "int_books": "",
    "spray_word": "LeX!", "custom_wall": "", "website": "",
    "left_blocks": DEFAULT_LEFT.copy(), "right_blocks": DEFAULT_RIGHT.copy(),
    "followers": [], "following": [], "playlist": [], "albums": [],
    "blocked_users": [], "reports_log": [],
}
DEFAULT_TOP8 = [
    {"handle": "@LeX", "name": "LeX Official", "mood": "Building the Future ⚡", "anthem": "Y2K Cobalt Synth"},
    {"handle": "@Vex", "name": "Vex ⚡", "mood": "Late Night Coding 💻", "anthem": "Midnight Synthwave"},
    {"handle": "@Nova", "name": "Nova ✦", "mood": "Making Beats 🎧", "anthem": "Cyberpunk Bassline"},
    {"handle": "@Roxy", "name": "Roxy 🎸", "mood": "Rehearsal Mode 🔊", "anthem": "Punk Garage Riff"},
    {"handle": "@Kairo", "name": "Kairo 🕹", "mood": "High Score Run 🎮", "anthem": "8-Bit Arcade Boss"},
    {"handle": "@Luna", "name": "Luna 🌙", "mood": "Stargazing ✨", "anthem": "Lo-Fi Dreamscape"},
    {"handle": "@Jax", "name": "Jax 🔥", "mood": "Skatepark Session 🛹", "anthem": "Neon Pop-Punk"},
    {"handle": "@Zoe", "name": "Zoe 💎", "mood": "Designing Themes 🎨", "anthem": "Velvet Hyperpop"},
]

def founder_badge_html(handle: str) -> str:
    h = (handle or "").strip().lower()
    if h in {"@heidi", "@heidiseckman"}:
        return '<span style="display:inline-block;margin-left:8px;padding:2px 8px;border-radius:999px;font-size:0.7rem;font-weight:800;letter-spacing:0.06em;background:linear-gradient(90deg,#EC4899,#8B5CF6);color:#FFF;box-shadow:0 0 10px rgba(236,72,153,0.65);">👑 CREATOR &amp; FOUNDER</span>'
    return ""

def founder_studio_link_html(handle: str) -> str:
    h = (handle or "").strip().lower()
    if h in {"@heidi", "@heidiseckman"}:
        return f' <a href="{LEXITECH_HUB_URL}" target="_blank" style="color:#EC4899;font-weight:700;text-decoration:none;margin-left:8px;">✦ LexiTech Studio Hub</a>'
    return ""
def build_backdrop_url(style_name: str, accent: str, spray_word: str = "LeX!") -> str:
    c = accent or "#EC4899"
    w = "".join(ch for ch in (spray_word or "LeX!") if ch.isalnum() or ch in ("!", "✦", "⚡"))[:10] or "LeX!"
    patterns = {
        "Architectural Grid": f'<path d="M 40 0 L 0 0 0 40" fill="none" stroke="{c}" stroke-opacity="0.16" stroke-width="1"/>',
        "Punk Spray-Paint Graffiti": f'<text x="8" y="28" fill="{c}" fill-opacity="0.22" font-family="sans-serif" font-weight="900" font-size="14" transform="rotate(-12 20 20)">{w}</text><circle cx="46" cy="44" r="3" fill="{c}" fill-opacity="0.2"/>',
        "Y2K Stars & Sparkles": f'<polygon points="20,4 24,15 36,15 26,22 30,33 20,26 10,33 14,22 4,15 16,15" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.2"/>',
        "Leopard Rosette Print": f'<path d="M12,14 C16,8 26,10 24,18 C22,25 10,22 12,14 Z" fill="none" stroke="{c}" stroke-opacity="0.24" stroke-width="2.2"/><circle cx="38" cy="36" r="5" fill="none" stroke="{c}" stroke-opacity="0.2" stroke-width="2"/>',
        "Cherry Hearts & Kisses": f'<path d="M20,30 C10,20 8,12 15,10 C18,9 20,12 20,14 C20,12 22,9 25,10 C32,12 30,20 20,30 Z" fill="none" stroke="{c}" stroke-opacity="0.24" stroke-width="1.4"/>',
        "Coquette Ribbon Bows": f'<path d="M12,20 L20,24 L12,28 Z M28,20 L20,24 L28,28 Z M20,24 L16,34 M20,24 L24,34" fill="none" stroke="{c}" stroke-opacity="0.24" stroke-width="1.4"/>',
        "Butterfly Dreamscape": f'<path d="M20,22 C12,10 6,16 14,24 C8,28 14,34 20,26 C26,34 32,28 26,24 C34,16 28,10 20,22 Z" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.3"/>',
        "Checkered Ska / Vans": f'<rect x="0" y="0" width="20" height="20" fill="{c}" fill-opacity="0.12"/><rect x="20" y="20" width="20" height="20" fill="{c}" fill-opacity="0.12"/>',
        "Skull & Crossbones Punk": f'<circle cx="20" cy="16" r="7" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.4"/><line x1="10" y1="32" x2="30" y2="24" stroke="{c}" stroke-opacity="0.22" stroke-width="1.4"/><line x1="10" y1="24" x2="30" y2="32" stroke="{c}" stroke-opacity="0.22" stroke-width="1.4"/>',
        "Lightning Bolts & Voltage": f'<polyline points="22,4 12,22 21,22 16,38 30,18 20,18 22,4" fill="none" stroke="{c}" stroke-opacity="0.24" stroke-width="1.4"/>',
        "Gothic Bats & Moons": f'<path d="M28,10 A9,9 0 1,0 34,24 A7,7 0 1,1 28,10 Z" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.3"/>',
        "Cyber Matrix Rain": f'<text x="10" y="18" fill="{c}" fill-opacity="0.22" font-family="monospace" font-size="11">101</text><text x="26" y="36" fill="{c}" fill-opacity="0.18" font-family="monospace" font-size="11">010</text>',
        "Carbon Fiber Hex": f'<polygon points="20,4 34,12 34,28 20,36 6,28 6,12" fill="none" stroke="{c}" stroke-opacity="0.18" stroke-width="1.2"/>',
        "Retro Cassette & Vinyl": f'<circle cx="20" cy="20" r="13" fill="none" stroke="{c}" stroke-opacity="0.2" stroke-width="1.4"/><circle cx="20" cy="20" r="4" fill="none" stroke="{c}" stroke-opacity="0.25" stroke-width="1.4"/>',
        "Flame & Hotrod Stripes": f'<path d="M16,36 C10,26 18,18 18,8 C24,16 30,24 22,36 Z" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.4"/>',
        "Crown & Diamond Luxe": f'<polyline points="8,28 10,14 16,22 20,12 24,22 30,14 32,28 8,28" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.4"/>',
        "Rose Thorns & Petals": f'<circle cx="20" cy="18" r="8" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.3"/><line x1="20" y1="26" x2="20" y2="38" stroke="{c}" stroke-opacity="0.22" stroke-width="1.3"/>',
        "8-Bit Arcade Invaders": f'<rect x="12" y="12" width="16" height="10" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.4"/><rect x="14" y="22" width="4" height="5" fill="{c}" fill-opacity="0.2"/><rect x="22" y="22" width="4" height="5" fill="{c}" fill-opacity="0.2"/>',
        "Tactical Urban Camo": f'<path d="M4,12 L18,8 L24,20 L10,24 Z" fill="{c}" fill-opacity="0.12"/><path d="M24,26 L38,22 L42,36 L28,38 Z" fill="{c}" fill-opacity="0.1"/>',
        "Cosmic Planets & Rings": f'<circle cx="22" cy="22" r="8" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.3"/><ellipse cx="22" cy="22" rx="17" ry="5" transform="rotate(-22 22 22)" fill="none" stroke="{c}" stroke-opacity="0.22" stroke-width="1.2"/>',
    }
    inner = patterns.get(style_name, patterns["Architectural Grid"])
    svg_raw = f'{SV_OPEN}xmlns="{SVG_NS}" width="48" height="48" viewBox="0 0 48 48">{inner}{SV_CLOSE}'
    return "data:image/svg+xml;base64," + base64.b64encode(svg_raw.encode("utf-8")).decode("ascii")
def calc_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def encode_image_data_url(up_file) -> str:
    if up_file is None:
        return ""
    mime = getattr(up_file, "type", "image/png") or "image/png"
    b64 = base64.b64encode(up_file.getvalue()).decode("ascii")
    return f"data:{mime};base64,{b64}"

def normalize_url(raw_u: str) -> str:
    u = (raw_u or "").strip()
    if not u:
        return ""
    return u if u.startswith(("http://", "https://")) else "https://" + u

def extract_yt_id(url: str) -> str:
    u = (url or "").strip()
    if "youtu.be/" in u:
        _, _, rest = u.partition("youtu.be/")
        vid, _, _ = rest.partition("?")
        return vid.strip("/")
    if "v=" in u:
        _, _, rest = u.partition("v=")
        vid, _, _ = rest.partition("&")
        return vid.strip()
    if "/embed/" in u:
        _, _, rest = u.partition("/embed/")
        vid, _, _ = rest.partition("?")
        return vid.strip("/")
    return ""

def save_profile_to_cloud():
    sb_c = get_sb()
    u = st.session_state.get("lex_user")
    if not sb_c or not isinstance(u, dict) or not u.get("user_id"):
        return
    tj = dict(st.session_state.lex_theme)
    tj["avatar"] = u.get("avatar", "")
    tj["website"] = u.get("website", "")
    tj["all_friends"] = st.session_state.lex_friends
    payload = {
        "user_id": u["user_id"], "handle": u["handle"], "display_name": u["name"],
        "bio": u.get("bio", ""), "who_to_meet": u.get("who_to_meet", ""),
        "mood": u.get("mood", "Online Now • Vibing ⚡"), "anthem": u.get("anthem", "Y2K Cobalt Synth"),
        "custom_song_url": u.get("custom_song_url", ""), "custom_song_title": u.get("custom_song_title", ""),
        "theme_json": tj, "top8_json": st.session_state.lex_top8, "wall_json": st.session_state.lex_wall,
    }
    sb_c.table("lex_profiles").upsert(payload, on_conflict="user_id").execute()

def toggle_follow_user(my_handle: str, target_handle: str):
    fol = list(st.session_state.lex_theme.get("following") or [])
    if target_handle in fol:
        fol.remove(target_handle)
    else:
        fol.append(target_handle)
    st.session_state.lex_theme["following"] = fol
    save_profile_to_cloud()
def render_popular_song_embed(url: str, title: str = "Profile Anthem"):
    u = normalize_url(url)
    if not u:
        return
    if "://spotify.com" in u:
        _, _, rest = u.partition("track/")
        tid, _, _ = rest.partition("?")
        components.iframe(f"{SPOTIFY_EMBED}{tid}?theme=0", height=80)
    else:
        vid = extract_yt_id(u)
        if vid:
            components.iframe(f"{YT_EMBED_BASE}{vid}?autoplay=0&controls=1", height=46)
        else:
            st.markdown(f"🎵 **{title}:** [{u}]({u})")

def render_mini_yt_audio_bar(url: str, label: str = "Track"):
    vid = extract_yt_id(normalize_url(url))
    if vid:
        st.caption(f"🎧 {label}")
        components.iframe(f"{YT_EMBED_BASE}{vid}?autoplay=0&controls=1", height=46)

for k_init, v_init in [
    ("lex_user", None), ("lex_theme", DEFAULT_THEME.copy()),
    ("lex_top8", [x.copy() for x in DEFAULT_TOP8]),
    ("lex_friends", [x.copy() for x in DEFAULT_TOP8]),
    ("lex_wall", [{"sender": "@LeX", "msg": "Welcome to LeX Social ✦ Customize your profile in LeX Studio!"}]),
    ("viewing_handle", None),
]:
    if k_init not in st.session_state:
        st.session_state[k_init] = v_init

sb = get_sb()
th = st.session_state.lex_theme
g_font, css_font = FONT_MAP.get(th.get("font", "Clean Studio Sans"), FONT_MAP["Clean Studio Sans"])
wall_url = th.get("custom_wall") or build_backdrop_url(th.get("backdrop", "Architectural Grid"), th.get("accent", "#EC4899"), th.get("spray_word", "LeX!"))
op_hex = f"{int(max(40, min(100, th.get('card_opacity', 92))) * 2.55):02x}"
glow_css = f"0 0 16px {th['accent']}55" if th.get("glow_borders", True) else "none"

st.markdown(
    f'{LK_OPEN}rel="stylesheet" href="{GFONTS_BASE}{urllib.parse.quote(g_font)}&display=swap">'
    f'{ST_OPEN}.stApp{{background-color:{th["bg"]};background-image:url("{wall_url}");background-repeat:repeat;color:{th["text"]};font-family:{css_font};}}'
    f'.lex-card{{background:{th["card"]}{op_hex};border:1.5px {th.get("border_style","solid")} {th["accent"]};border-radius:{th.get("card_radius",12)}px;padding:16px;margin-bottom:14px;box-shadow:{glow_css};}}'
    f'{th.get("custom_css","")}{ST_CLOSE}',
    unsafe_allow_html=True,
)

if not st.session_state.lex_user:
    st.markdown(f'<div class="lex-card" style="text-align:center;"><h1>✦ LeX // SOCIAL</h1><p style="color:{th["accent"]};font-weight:700;">Next-Gen Custom Social Architecture by LexiTech Studio • 13+ Only</p></div>', unsafe_allow_html=True)
    t_in, t_up = st.tabs(["🔑 Sign In", "✨ Create Account (13+)"])
    with t_in:
        with st.form("lex_login_form"):
            l_email, l_pass = st.text_input("Email"), st.text_input("Password", type="password")
            if st.form_submit_button("Sign In to My LeX Profile ✦", use_container_width=True) and sb:
                try:
                    res = sb.auth.sign_in_with_password({"email": l_email.strip(), "password": l_pass})
                    uid = res.user.id
                    prof = sb.table("lex_profiles").select("*").eq("user_id", uid).execute().data
                    r = next(iter(prof), None) if isinstance(prof, list) else prof
                    if isinstance(r, dict):
                        tj = r.get("theme_json") or {}
                        st.session_state.lex_user = {
                            "user_id": uid, "name": r.get("display_name", "LeX Member"), "handle": r.get("handle", "@Member"),
                            "bio": r.get("bio", ""), "who_to_meet": r.get("who_to_meet", ""),
                            "mood": r.get("mood", "Online Now • Vibing ⚡"), "anthem": r.get("anthem", "Y2K Cobalt Synth"),
                            "custom_song_url": r.get("custom_song_url", ""), "custom_song_title": r.get("custom_song_title", ""),
                            "avatar": tj.get("avatar", ""), "website": tj.get("website", ""),
                        }
                        st.session_state.lex_theme.update(tj)
                        lb = list(st.session_state.lex_theme.get("left_blocks") or [])
                        rb = list(st.session_state.lex_theme.get("right_blocks") or [])
                        if "Photo Albums" not in lb and "Photo Albums" not in rb:
                            st.session_state.lex_theme["left_blocks"] = ["Profile Card", "Photo Albums"] + [b for b in lb if b != "Profile Card"]
                        if r.get("top8_json"):
                            st.session_state.lex_top8 = r["top8_json"]
                        st.session_state.lex_friends = tj.get("all_friends") or [i.copy() for i in st.session_state.lex_top8]
                        if r.get("wall_json"):
                            st.session_state.lex_wall = r["wall_json"]
                    else:
                        prefix, _, _ = l_email.strip().partition("@")
                        base_h = clean_handle_str(prefix) or "Member"
                        cand = base_h
                        suffix = 1
                        while is_handle_taken(sb, cand, uid):
                            cand = f"{base_h}{suffix}"
                            suffix += 1
                        st.session_state.lex_user = {
                            "user_id": uid, "name": cand.capitalize(), "handle": f"@{cand}", "avatar": "", "website": "",
                            "mood": "Online Now • Vibing ⚡", "bio": "Back on LeX ✦", "who_to_meet": "Creators & music lovers.",
                            "anthem": "Y2K Cobalt Synth", "custom_song_url": "", "custom_song_title": "",
                        }
                    save_profile_to_cloud()
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign in failed: {e}")
    with t_up:
        with st.form("lex_signup_form"):
            s_email, s_pass = st.text_input("Email"), st.text_input("Password (6+ chars)", type="password")
            d_name, r_handle = st.text_input("Display Name"), st.text_input("@handle (Must be unique)")
            dob = st.date_input("Date of Birth (13+ Only)", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today())
            site_in = st.text_input("Profile Link / Website (Optional)", placeholder="heidiseckman.github.io/lexitech-hub")
            if st.form_submit_button("Create Permanent LeX Account ✦", use_container_width=True) and sb:
                ch = clean_handle_str(r_handle)
                ok_s, msg_s = check_safety_and_dress_code(f"{d_name} {ch} {site_in}")
                if calc_age(dob) < 13:
                    st.error("Must be 13+ to join LeX.")
                elif not ok_s:
                    st.error(msg_s)
                elif not ch:
                    st.error("Please enter a valid @handle using letters, numbers, or underscores.")
                elif is_handle_taken(sb, ch):
                    st.error(f"@{ch} is already taken! Every LeX handle must be unique—please choose another.")
                elif s_email.strip() and len(s_pass) >= 6 and d_name.strip():
                    try:
                        ares = sb.auth.sign_up({"email": s_email.strip(), "password": s_pass})
                        st.session_state.lex_user = {
                            "user_id": ares.user.id, "name": d_name.strip(), "handle": f"@{ch}",
                            "avatar": "", "website": normalize_url(site_in), "mood": "Online Now • Vibing ⚡",
                            "bio": "Zero algorithms. Custom vibes on LeX.", "who_to_meet": "Creators & music lovers.",
                            "anthem": "Y2K Cobalt Synth", "custom_song_url": "", "custom_song_title": "",
                        }
                        save_profile_to_cloud()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Signup error: {e}")
    st.stop()
user = st.session_state.lex_user
h_col1, h_col2 = st.columns([0.82, 0.18])
h_col1.markdown(
    f'<div class="lex-card"><h2 style="margin:0;">✦ LeX // SOCIAL — {user["name"]} '
    f'<span style="color:{th["accent"]};">{user["handle"]}</span>{founder_badge_html(user["handle"])}'
    f'{founder_studio_link_html(user["handle"])}</h2></div>',
    unsafe_allow_html=True,
)
if h_col2.button("🚪 Sign Out", use_container_width=True):
    st.session_state.lex_user = None
    st.session_state.viewing_handle = None
    st.rerun()

if th.get("marquee_on") and th.get("marquee_text"):
    st.markdown(
        f'<div class="lex-card" style="padding:8px 14px;overflow:hidden;white-space:nowrap;">'
        f'<marquee behavior="scroll" direction="left" style="color:{th["accent"]};font-weight:800;">{th["marquee_text"]}</marquee></div>',
        unsafe_allow_html=True,
    )

if st.session_state.get("viewing_handle"):
    vh = st.session_state.viewing_handle
    if st.button("← Back to My Profile"):
        st.session_state.viewing_handle = None
        st.rerun()
    v_rows = sb.table("lex_profiles").select("*").ilike("handle", vh).execute().data or [] if sb else []
    vp = next(iter(v_rows), None)
    if isinstance(vp, dict):
        vtj = vp.get("theme_json") or {}
        v_av = vtj.get("avatar", "")
        v_img = f'<img src="{v_av}" style="width:96px;height:96px;border-radius:50%;object-fit:cover;border:2px solid {th["accent"]};"/>' if v_av else ""
        st.markdown(
            f'<div class="lex-card">{v_img}<h3>{vp.get("display_name")} <span style="color:{th["accent"]};">{vp.get("handle")}</span>{founder_badge_html(vp.get("handle",""))}</h3>'
            f'<p><strong>Mood:</strong> {vp.get("mood","")}</p><p>{vp.get("bio","")}</p></div>',
            unsafe_allow_html=True,
        )
        ac1, ac2, ac3, ac4 = st.columns([0.32, 0.32, 0.18, 0.18])
        is_fol = vp.get("handle") in (th.get("following") or [])
        if ac1.button("✓ Following" if is_fol else "⚡ Follow (Unlimited)", use_container_width=True):
            toggle_follow_user(user["handle"], vp["handle"])
            st.rerun()
        is_fr = any(f["handle"].lower() == vp.get("handle", "").lower() for f in st.session_state.lex_friends)
        if is_fr:
            ac2.button("✓ In Friends List", disabled=True, use_container_width=True)
        elif len(st.session_state.lex_friends) >= MAX_FRIENDS:
            ac2.button(f"Max {MAX_FRIENDS} Friends", disabled=True, use_container_width=True)
        elif ac2.button(f"+ Add Friend ({len(st.session_state.lex_friends)}/{MAX_FRIENDS})", use_container_width=True):
            st.session_state.lex_friends.append({"handle": vp["handle"], "name": vp["display_name"], "mood": vp.get("mood", "Online ⚡"), "anthem": vp.get("anthem", "Y2K Cobalt Synth")})
            save_profile_to_cloud()
            st.rerun()
        if ac3.button("🚫 Block", key=f"pub_blk_{vp['handle']}", use_container_width=True):
            block_or_report_member(vp["handle"], "block")
            st.session_state.viewing_handle = None
            st.toast(f"Blocked {vp['handle']}")
            st.rerun()
        if ac4.button("🚩 Report", key=f"pub_rep_{vp['handle']}", use_container_width=True):
            block_or_report_member(vp["handle"], "report", "Reported from Public Profile")
            st.toast(f"Reported {vp['handle']} to LeX Safety")
        if vp.get("custom_song_url"):
            render_popular_song_embed(vp["custom_song_url"], vp.get("custom_song_title") or "Profile Anthem")
        for alb in (vtj.get("albums") or []):
            st.markdown(f"#### 📸 {alb.get('title', 'Album')}")
            pcols = st.columns(3)
            for idx_p, ph in enumerate(alb.get("photos") or []):
                pcols[idx_p % 3].image(ph.get("img", ""), caption=ph.get("caption", ""), use_container_width=True)
    st.stop()
def render_module(mod_name: str):
    if mod_name == "Profile Card":
        av_html = f'<img src="{user["avatar"]}" style="width:110px;height:110px;border-radius:50%;object-fit:cover;border:2px solid {th["accent"]};margin-bottom:10px;"/>' if user.get("avatar") else ""
        site_html = f'<p><a href="{user["website"]}" target="_blank" style="color:{th["accent"]};font-weight:700;">🔗 {user["website"]}</a></p>' if user.get("website") else ""
        pin_html = f'<div style="padding:8px;border-left:3px solid {th["accent"]};margin:8px 0;background:{th["accent"]}18;">📌 {th["pinned_note"]}</div>' if th.get("pinned_note") else ""
        st.markdown(
            f'<div class="lex-card">{av_html}<h3>{user["name"]} <span style="color:{th["accent"]};">{user["handle"]}</span>{founder_badge_html(user["handle"])}</h3>'
            f'<p><strong>Mood:</strong> {user.get("mood","")}</p>{pin_html}<p>{user.get("bio","")}</p>'
            f'<p><strong>Who I\'d Like to Meet:</strong> {user.get("who_to_meet","")}</p>{site_html}'
            f'<p style="font-size:0.85rem;opacity:0.85;"><strong>General:</strong> {th.get("int_general","")} • <strong>Music:</strong> {th.get("int_music","")} • <strong>Movies:</strong> {th.get("int_movies","")} • <strong>TV:</strong> {th.get("int_tv","")} • <strong>Books:</strong> {th.get("int_books","")}</p></div>',
            unsafe_allow_html=True,
        )
    elif mod_name == "Photo Albums":
        with st.expander("📸 Photo Albums", expanded=True):
            albums = list(th.get("albums") or [])
            new_alb_name = st.text_input("Album Title", placeholder="Concert Pics 2026", key="alb_title_in")
            alb_up = st.file_uploader("Upload Photo (Fully clothed only)", type=["png", "jpg", "jpeg", "webp"], key="alb_file_in")
            alb_cap = st.text_input("Photo Caption", key="alb_cap_in")
            if st.button("Add Photo to Album ✦", key="alb_save_btn"):
                t_clean = new_alb_name.strip()
                ok_a, msg_a = scan_image_safely(alb_up, f"{t_clean} {alb_cap}")
                if not ok_a:
                    st.error(msg_a)
                elif t_clean and alb_up is not None:
                    img_data = encode_image_data_url(alb_up)
                    found = next((a for a in albums if a["title"].lower() == t_clean.lower()), None)
                    if found:
                        found["photos"].append({"img": img_data, "caption": alb_cap.strip()})
                    else:
                        albums.append({"title": t_clean, "photos": [{"img": img_data, "caption": alb_cap.strip()}]})
                    st.session_state.lex_theme["albums"] = albums
                    save_profile_to_cloud()
                    st.rerun()
            for a_i, alb in enumerate(albums):
                st.markdown(f"**{alb['title']}**")
                acols = st.columns(3)
                for p_i, ph in enumerate(alb.get("photos") or []):
                    acols[p_i % 3].image(ph["img"], caption=ph.get("caption", ""), use_container_width=True)
                    if acols[p_i % 3].button("🗑", key=f"del_p_{a_i}_{p_i}"):
                        alb["photos"].pop(p_i)
                        st.session_state.lex_theme["albums"] = [x for x in albums if x.get("photos")]
                        save_profile_to_cloud()
                        st.rerun()
    elif mod_name == "Profile Anthem":
        with st.expander("🎵 Profile Anthem & Playlist", expanded=True):
            if user.get("custom_song_url"):
                render_popular_song_embed(user["custom_song_url"], user.get("custom_song_title") or "Profile Anthem")
            else:
                tr_name = user.get("anthem", "Y2K Cobalt Synth")
                st.caption(f"Built-In Synth Anthem: **{tr_name}**")
                st.audio(generate_anthem_wav(tr_name), format="audio/wav")
            for idx_pl, item in enumerate(th.get("playlist") or []):
                render_mini_yt_audio_bar(item.get("url", ""), item.get("title", f"Track {idx_pl+1}"))
    elif mod_name == "Profile Wall":
        with st.expander("💬 Profile Wall", expanded=True):
            w_msg = st.text_input("Sign profile wall...", key="wall_in")
            if st.button("Post Wall Note", key="wall_btn") and w_msg.strip():
                ok_w, msg_w = check_safety_and_dress_code(w_msg)
                if not ok_w:
                    st.error(msg_w)
                else:
                    st.session_state.lex_wall.insert(0, {"sender": user["handle"], "msg": w_msg.strip()})
                    save_profile_to_cloud()
                    st.rerun()
            for wn in st.session_state.lex_wall[:15]:
                st.markdown(f"**{wn['sender']}:** {wn['msg']}")
    elif mod_name == "Top 8 Friends":
        with st.expander(f"👑 Top 8 Friends ({len(st.session_state.lex_friends)}/{MAX_FRIENDS} Total Friends)", expanded=True):
            tcols = st.columns(4)
            for idx_t, fr in enumerate(st.session_state.lex_top8[:8]):
                with tcols[idx_t % 4]:
                    st.markdown(f'<div class="lex-card" style="padding:10px;text-align:center;"><strong>#{idx_t+1} {fr["name"]}</strong><br><span style="color:{th["accent"]};font-size:0.82rem;">{fr["handle"]}</span><br><small>{fr.get("mood","")}</small></div>', unsafe_allow_html=True)
                    if st.button("View", key=f"t8v_{idx_t}_{fr['handle']}", use_container_width=True):
                        st.session_state.viewing_handle = fr["handle"]
                        st.rerun()
    elif mod_name == "Main Social Hub":
        render_social_hub()
def render_social_hub():
    t_feed, t_friends, t_dm, t_studio = st.tabs(["⚡ Feed", "🌐 Search & Friends", "✉ Direct Messages", "🎨 LeX Studio"])
    with t_feed:
        with st.form("feed_post_form", clear_on_submit=True):
            new_post = st.text_area("Share a status update, photo, or link... (Fully clothed & respectful content only)", height=68)
            fc1, fc2 = st.columns(2)
            post_img = fc1.file_uploader("Attach Photo", type=["png", "jpg", "jpeg", "webp"], key="fp_img")
            post_link = fc2.text_input("Attach Link / URL", placeholder="https://...", key="fp_link")
            if st.form_submit_button("Publish Status ✦") and (new_post.strip() or post_img or post_link.strip()) and sb:
                ok_t, msg_t = check_safety_and_dress_code(f"{new_post} {post_link}")
                ok_i, msg_i = scan_image_safely(post_img, new_post)
                if not ok_t:
                    st.error(msg_t)
                elif not ok_i:
                    st.error(msg_i)
                else:
                    packed = new_post.strip()
                    if post_link.strip():
                        packed += f"\n[LEX_LINK]{normalize_url(post_link)}"
                    if post_img is not None:
                        packed += f"\n[LEX_IMG]{encode_image_data_url(post_img)}"
                    sb.table("lex_posts").insert({"handle": user["handle"], "author": user["name"], "body": packed, "likes": 0}).execute()
                    st.rerun()
        blocked_set = get_blocked_handles()
        posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(35).execute().data or [] if sb else []
        for p in posts:
            if (p.get("handle") or "").strip().lower() in blocked_set:
                continue
            clean_txt, img_src, lnk_src = (p.get("body") or ""), "", ""
            if "[LEX_IMG]" in clean_txt:
                clean_txt, img_src = clean_txt.split("[LEX_IMG]", 1)
            if "[LEX_LINK]" in clean_txt:
                clean_txt, lnk_src = clean_txt.split("[LEX_LINK]", 1)
            clean_txt, lnk_src, img_src = clean_txt.strip(), lnk_src.strip(), img_src.strip()
            img_tag = f'<img src="{img_src}" style="width:100%;max-height:360px;object-fit:cover;border-radius:10px;margin-top:10px;border:1px solid {th["accent"]};" />' if img_src else ""
            lnk_tag = f'<div style="margin-top:8px;"><a href="{lnk_src}" target="_blank" style="display:inline-block;padding:6px 12px;border-radius:8px;background:{th["accent"]}22;border:1px solid {th["accent"]};color:{th["accent"]};font-weight:700;text-decoration:none;">🔗 {lnk_src}</a></div>' if lnk_src else ""
            st.markdown(f'<div class="lex-card"><strong>{p["author"]}</strong> <span style="color:{th["accent"]};">{p["handle"]}</span>{founder_badge_html(p.get("handle", ""))}<p style="margin-top:6px;">{clean_txt}</p>{lnk_tag}{img_tag}</div>', unsafe_allow_html=True)
            rx_key = f"rx_{p['id']}"
            if rx_key not in st.session_state:
                st.session_state[rx_key] = {"🔥": p.get("likes", 0), "💖": 0, "🎸": 0, "💀": 0}
            rcols = st.columns(5)
            for idx_e, emo in enumerate(["🔥", "💖", "🎸", "💀"]):
                if rcols[idx_e].button(f"{emo} {st.session_state[rx_key][emo]}", key=f"b_{p['id']}_{emo}"):
                    st.session_state[rx_key][emo] += 1
                    if emo == "🔥" and sb:
                        sb.table("lex_posts").update({"likes": st.session_state[rx_key]["🔥"]}).eq("id", p["id"]).execute()
                    st.rerun()
            if p.get("handle", "").lower() != user["handle"].lower():
                if rcols.button("🚩 Report", key=f"rep_post_{p['id']}"):
                    block_or_report_member(p.get("handle", ""), "report", f"Reported post #{p['id']}: {clean_txt[:80]}")
                    st.toast("Post reported to LeX Safety")
    with t_friends:
        st.markdown("#### 🌐 Search Entire LeX Platform & Discover Members")
        with st.form("global_platform_search_form", clear_on_submit=False):
            sc_1, sc_2 = st.columns([0.72, 0.28])
            q_in = sc_1.text_input("Search all users by @handle or display name", placeholder="Type name or @handle (leave blank to browse all)", label_visibility="collapsed")
            do_search = sc_2.form_submit_button("🔍 Search Platform", use_container_width=True)
        if do_search:
            st.session_state["lex_global_q"] = q_in.strip().lower()
        q_search = st.session_state.get("lex_global_q", "")
        blocked_set = get_blocked_handles()
        all_profiles = sb.table("lex_profiles").select("user_id, handle, display_name, mood, anthem, theme_json").execute().data or [] if sb else []
        my_handles = {f["handle"].lower() for f in st.session_state.lex_friends}
        following_set = set(th.get("following") or [])
        matches = [
            r for r in all_profiles
            if r.get("handle")
            and r["handle"].lower() != user["handle"].lower()
            and r["handle"].lower() not in blocked_set
            and (not q_search or q_search in r["handle"].lower() or q_search in (r.get("display_name") or "").lower())
        ]
        st.caption(f"Showing {len(matches)} member(s) across LeX Social")
        if not matches:
            st.info("No matching members found. Make sure they created their account and saved their profile.")
        for m in matches[:25]:
            m_fol = len((m.get("theme_json") or {}).get("followers") or [])
            c1, c2, c3, c4, c5, c6 = st.columns([0.34, 0.13, 0.14, 0.15, 0.12, 0.12])
            c1.markdown(f"**{m['display_name']}** (`{m['handle']}`) • ⚡ {m_fol}")
            if c2.button("View", key=f"vw_{m['handle']}"):
                st.session_state.viewing_handle = m["handle"]
                st.rerun()
            is_f = m["handle"] in following_set
            if c3.button("✓ Following" if is_f else "⚡ Follow", key=f"fol_{m['handle']}"):
                toggle_follow_user(user["handle"], m["handle"])
                st.rerun()
            if m["handle"].lower() not in my_handles:
                if len(st.session_state.lex_friends) >= MAX_FRIENDS:
                    c4.caption("Max 1k")
                elif c4.button("+ Friend", key=f"addf_{m['handle']}"):
                    st.session_state.lex_friends.append({"handle": m["handle"], "name": m["display_name"], "mood": m.get("mood", "Online ⚡"), "anthem": m.get("anthem", "Y2K Cobalt Synth")})
                    save_profile_to_cloud()
                    st.rerun()
            else:
                c4.caption("✓ Friend")
            if c5.button("🚫 Block", key=f"blk_{m['handle']}"):
                block_or_report_member(m["handle"], "block")
                st.toast(f"Blocked {m['handle']}")
                st.rerun()
            if c6.button("🚩 Report", key=f"rep_{m['handle']}"):
                block_or_report_member(m["handle"], "report", "Reported from Global Directory")
                st.toast(f"Reported {m['handle']}")
        st.markdown(f"#### 👥 My Friends List ({len(st.session_state.lex_friends)}/{MAX_FRIENDS})")
        for idx_f, fr in enumerate(st.session_state.lex_friends):
            fc_a, fc_b, fc_c = st.columns([0.6, 0.2, 0.2])
            fc_a.write(f"**{fr['name']}** ({fr['handle']})")
            if fc_b.button("View", key=f"fvw_{idx_f}_{fr['handle']}"):
                st.session_state.viewing_handle = fr["handle"]
                st.rerun()
            if fc_c.button("Remove", key=f"fdel_{idx_f}_{fr['handle']}"):
                st.session_state.lex_friends.pop(idx_f)
                save_profile_to_cloud()
                st.rerun()
    with t_dm:
        blocked_set = get_blocked_handles()
        all_m = sb.table("lex_messages").select("*").order("id", desc=False).limit(150).execute().data or [] if sb else []
        inbox_handles = {x["sender_handle"] for x in all_m if x["recipient_handle"] == user["handle"]} | {x["recipient_handle"] for x in all_m if x["sender_handle"] == user["handle"]}
        dm_targets = sorted({
            f["handle"] for f in st.session_state.lex_friends
            if f["handle"] != user["handle"] and f["handle"].lower() not in blocked_set
        } | {h for h in inbox_handles if h.lower() not in blocked_set} | {"@LeX"})
        dc1, dc2 = st.columns([0.55, 0.45])
        picked_chat = dc1.selectbox("Select Conversation", dm_targets)
        custom_dm = dc2.text_input("Or DM any @handle", placeholder="@Roxy")
        active_chat = ("@" + clean_handle_str(custom_dm)) if clean_handle_str(custom_dm) else picked_chat
        if active_chat.lower() in blocked_set:
            st.warning("You have blocked this user.")
        else:
            for m in [x for x in all_m if {x["sender_handle"], x["recipient_handle"]} == {user["handle"], active_chat}]:
                st.markdown(f"**{m['sender_handle']}:** {m['body']}")
            dm_txt = st.text_input(f"Message {active_chat}...", key="dm_in")
            if st.button("Send DM ✉") and dm_txt.strip() and sb:
                ok_d, msg_d = check_safety_and_dress_code(dm_txt)
                if not ok_d:
                    st.error(msg_d)
                else:
                    sb.table("lex_messages").insert({"sender_handle": user["handle"], "recipient_handle": active_chat, "body": dm_txt.strip()}).execute()
                    st.rerun()
    with t_studio:
        st.markdown("### 🎨 LeX Studio — Full Profile Architect")
        all_mods = ["Profile Card", "Photo Albums", "Top 8 Friends", "Profile Anthem", "Profile Wall", "Main Social Hub"]
        lc1, lc2 = st.columns(2)
        new_left = lc1.multiselect("Left Column Modules", all_mods, default=[m for m in th.get("left_blocks", DEFAULT_LEFT) if m in all_mods])
        new_right = lc2.multiselect("Right Column Modules", all_mods, default=[m for m in th.get("right_blocks", DEFAULT_RIGHT) if m in all_mods])
        if st.button("Save Column Layout ✦"):
            st.session_state.lex_theme["left_blocks"] = new_left
            st.session_state.lex_theme["right_blocks"] = new_right
            save_profile_to_cloud()
            st.rerun()
        cc1, cc2, cc3 = st.columns(3)
        bg_c = cc1.color_picker("Background Color", th.get("bg", "#000000"))
        card_c = cc2.color_picker("Card Surface Color", th.get("card", "#070709"))
        acc_c = cc3.color_picker("Accent & Neon Glow", th.get("accent", "#EC4899"))
        sc_a, sc_b, sc_c = st.columns(3)
        op_v = sc_a.slider("Card Glass Opacity (%)", 40, 100, int(th.get("card_opacity", 92)))
        rad_v = sc_b.slider("Corner Roundness (px)", 0, 24, int(th.get("card_radius", 12)))
        glow_v = sc_c.checkbox("✨ Neon Glowing Borders", value=bool(th.get("glow_borders", True)))
        fc_a, fc_b, fc_c = st.columns(3)
        font_v = fc_a.selectbox("Font Style", list(FONT_MAP.keys()), index=list(FONT_MAP.keys()).index(th.get("font", "Clean Studio Sans")) if th.get("font") in FONT_MAP else 0)
        bdr_v = fc_b.selectbox("Border Style", ["solid", "dashed", "double"], index=["solid", "dashed", "double"].index(th.get("border_style", "solid")) if th.get("border_style") in ["solid", "dashed", "double"] else 0)
        wall_v = fc_c.selectbox("20 Vector Wall Backdrops", BACKDROP_OPTIONS, index=BACKDROP_OPTIONS.index(th.get("backdrop", "Architectural Grid")) if th.get("backdrop") in BACKDROP_OPTIONS else 0)
        spray_v = st.text_input("Graffiti Spray Tag Word", value=th.get("spray_word", "LeX!"))
        mq_on = st.checkbox("Enable Scrolling Neon Marquee", value=bool(th.get("marquee_on", True)))
        mq_txt = st.text_input("Marquee Banner Text", value=th.get("marquee_text", ""))
        cust_css = st.text_area("Power-User Custom CSS", value=th.get("custom_css", ""), height=68)
        if st.button("Apply Visual Theme ✦"):
            ok_v, msg_v = check_safety_and_dress_code(f"{spray_v} {mq_txt}")
            if not ok_v:
                st.error(msg_v)
            else:
                st.session_state.lex_theme.update({"bg": bg_c, "card": card_c, "accent": acc_c, "card_opacity": op_v, "card_radius": rad_v, "glow_borders": glow_v, "font": font_v, "border_style": bdr_v, "backdrop": wall_v, "spray_word": spray_v.strip() or "LeX!", "marquee_on": mq_on, "marquee_text": mq_txt.strip(), "custom_css": cust_css})
                save_profile_to_cloud()
                st.rerun()
        new_av = st.file_uploader("Upload Profile Picture (Fully clothed only)", type=["png", "jpg", "jpeg", "webp"], key="upd_av")
        if new_av is not None and st.button("Save Profile Picture"):
            ok_av, msg_av = scan_image_safely(new_av, "avatar")
            if not ok_av:
                st.error(msg_av)
            else:
                user["avatar"] = encode_image_data_url(new_av)
                save_profile_to_cloud()
                st.rerun()
        wall_up = st.file_uploader("Upload Custom Wallpaper (Fully clothed only)", type=["png", "jpg", "jpeg", "webp"], key="upd_wall")
        wc1, wc2 = st.columns(2)
        if wall_up is not None and wc1.button("Set Wallpaper 🖼"):
            ok_wl, msg_wl = scan_image_safely(wall_up, "wallpaper")
            if not ok_wl:
                st.error(msg_wl)
            else:
                st.session_state.lex_theme["custom_wall"] = encode_image_data_url(wall_up)
                save_profile_to_cloud()
                st.rerun()
        if th.get("custom_wall") and wc2.button("Clear Custom Wallpaper"):
            st.session_state.lex_theme["custom_wall"] = ""
            save_profile_to_cloud()
            st.rerun()
        st.markdown("#### 🎵 Profile Anthem & Audio Playlist")
        synth_pick = st.selectbox("Built-In Synth Anthem", list(ANTHEM_TRACKS.keys()), index=list(ANTHEM_TRACKS.keys()).index(user.get("anthem")) if user.get("anthem") in ANTHEM_TRACKS else 0)
        song_url = st.text_input("Spotify Track or YouTube URL (Optional)", value=user.get("custom_song_url", ""))
        song_title = st.text_input("Anthem Title", value=user.get("custom_song_title", ""))
        if st.button("Save Profile Anthem 🎵"):
            user["anthem"] = synth_pick
            user["custom_song_url"] = song_url.strip()
            user["custom_song_title"] = song_title.strip()
            save_profile_to_cloud()
            st.rerun()
        st.markdown("#### 📝 Bio, Pinned Bulletin & Interests")
        pin_in = st.text_input("Pinned Bulletin Note", value=th.get("pinned_note", ""))
        new_site = st.text_input("Profile Link / Website", value=user.get("website", ""))
        new_mood = st.text_input("Current Mood", value=user.get("mood", ""))
        new_bio = st.text_area("About Me / Bio", value=user.get("bio", ""), height=68)
        new_meet = st.text_input("Who I'd Like to Meet", value=user.get("who_to_meet", ""))
        ic1, ic2 = st.columns(2)
        i_gen = ic1.text_input("General Interests", value=th.get("int_general", ""))
        i_mus = ic2.text_input("Music", value=th.get("int_music", ""))
        i_mov = ic1.text_input("Movies", value=th.get("int_movies", ""))
        i_tv = ic2.text_input("Television", value=th.get("int_tv", ""))
        i_bk = st.text_input("Books & Heroes", value=th.get("int_books", ""))
        if st.button("Save All Profile Details ✦"):
            ok_bio, msg_bio = check_safety_and_dress_code(f"{pin_in} {new_site} {new_mood} {new_bio} {new_meet} {i_gen} {i_mus} {i_mov} {i_tv} {i_bk}")
            if not ok_bio:
                st.error(msg_bio)
            else:
                user["website"] = normalize_url(new_site)
                user["mood"] = new_mood.strip()
                user["bio"] = new_bio.strip()
                user["who_to_meet"] = new_meet.strip()
                st.session_state.lex_theme.update({"pinned_note": pin_in.strip(), "int_general": i_gen.strip(), "int_music": i_mus.strip(), "int_movies": i_mov.strip(), "int_tv": i_tv.strip(), "int_books": i_bk.strip()})
                save_profile_to_cloud()
                st.rerun()
        blocked_list = list(st.session_state.lex_theme.get("blocked_users") or [])
        if blocked_list:
            st.markdown("#### 🚫 Blocked Users")
            for b_idx, b_user in enumerate(blocked_list):
                bc1, bc2 = st.columns([0.7, 0.3])
                bc1.write(b_user)
                if bc2.button("Unblock", key=f"unblk_{b_idx}"):
                    blocked_list.pop(b_idx)
                    st.session_state.lex_theme["blocked_users"] = blocked_list
                    save_profile_to_cloud()
                    st.rerun()

col_left, col_right = st.columns([0.38, 0.62])
with col_left:
    for mod in (th.get("left_blocks") or DEFAULT_LEFT):
        render_module(mod)
with col_right:
    for mod in (th.get("right_blocks") or DEFAULT_RIGHT):
        render_module(mod)

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only.")
