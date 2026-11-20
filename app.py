import os
import re
import json
import base64
import urllib.parse
import urllib.request
from datetime import date
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
OPENAI_MOD_URL = "https://" + ".".join(["api", "openai", "com"]) + "/v1/moderations"
MAX_FRIENDS = 1000
MAX_IMG_BYTES = 5 * 1024 * 1024

BANNED_TERMS = {
    "nsfw", "porn", "xxx", "gore", "snuff", "bestiality", "csam", "beheading",
    "selfharm", "kill yourself", "kys", "doxx", "swat",
}
UNSAFE_DOMAINS = {
    "pornhub.com", "xvideos.com", "xnxx.com", "onlyfans.com", "redtube.com",
    "youporn.com", "liveleak.com", "bestgore.com", "grabify.link", "iplogger.org",
}

@st.cache_resource
def get_sb():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    return create_client(url, key) if (url and key) else None
def check_url_safety(raw_url: str) -> tuple[bool, str]:
    clean = (raw_url or "").strip()
    if not clean:
        return True, ""
    low = clean.lower()
    if low.startswith(("javascript:", "data:", "vbscript:", "file:")):
        return False, "Blocked unsafe link scheme."
    norm = clean if low.startswith(("http://", "https://")) else ("https://" + clean)
    try:
        parsed = urllib.parse.urlparse(norm)
        host = (parsed.hostname or "").lower().lstrip("www.")
        if not host or "." not in host:
            return False, "Please enter a valid web domain."
        if any(host == d or host.endswith("." + d) for d in UNSAFE_DOMAINS):
            return False, "Blocked domain: adult, gore, or IP-tracker links are not allowed."
    except Exception:
        return False, "Invalid URL format."
    return True, ""

def call_openai_moderation(payload_inputs: list) -> tuple[bool, str]:
    api_key = st.secrets.get("OPENAI_API_KEY", "")
    if not api_key or not payload_inputs:
        return True, ""
    try:
        body = json.dumps({"model": "omni-moderation-latest", "input": payload_inputs}).encode("utf-8")
        req = urllib.request.Request(
            OPENAI_MOD_URL,
            data=body,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        res_list = data.get("results") or [{}]
        res = res_list[0] if isinstance(res_list, list) and res_list else {}
        if res.get("flagged"):
            cats = [k for k, v in (res.get("categories") or {}).items() if v]
            reason = ", ".join(cats[:3]) if cats else "policy violation"
            return False, f"Blocked by AI safety filter ({reason})."
    except Exception:
        pass
    return True, ""

def check_text_and_links(text: str, url: str = "") -> tuple[bool, str]:
    raw = (text or "").strip()
    low = raw.lower()
    if re.search(r"<\s*(script|iframe|object|embed|form)|on\w+\s*=|javascript:", low):
        return False, "Blocked unsafe HTML or script code."
    for term in BANNED_TERMS:
        if re.search(r"\b" + re.escape(term) + r"\b", low):
            return False, "Blocked prohibited or graphic keyword."
    for found_url in re.findall(r"https?://[^\s<>\"']+", raw):
        ok_u, msg_u = check_url_safety(found_url)
        if not ok_u:
            return False, msg_u
    if url:
        ok_l, msg_l = check_url_safety(url)
        if not ok_l:
            return False, msg_l
    if raw:
        return call_openai_moderation([{"type": "text", "text": raw[:2000]}])
    return True, ""
def validate_and_scan_media(uploaded_file) -> tuple[bool, str]:
    if uploaded_file is None:
        return True, ""
    raw_bytes = uploaded_file.getvalue()
    if len(raw_bytes) > MAX_IMG_BYTES:
        return False, "Image exceeds 5 MB safety limit."
    is_png = raw_bytes.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpg = raw_bytes.startswith(b"\xff\xd8\xff")
    is_webp = raw_bytes[:4] == b"RIFF" and raw_bytes[8:12] == b"WEBP"
    if not (is_png or is_jpg or is_webp):
        return False, "Invalid image file header. Upload a real PNG, JPG, or WEBP."
    mime = "image/png" if is_png else ("image/jpeg" if is_jpg else "image/webp")
    b64 = base64.b64encode(raw_bytes).decode("ascii")
    return call_openai_moderation([{"type": "image_url", "image_url": {"url": f"data:{mime};base64,{b64}"}}])

def sanitize_custom_css(raw_css: str) -> str:
    clean = (raw_css or "").replace("<", "").replace(">", "")
    clean = re.sub(r"(?i)(expression|javascript:|behavior:|@import|url\s*\(\s*['\"]?\s*(?!data:image/))", "", clean)
    return clean[:3000]

def get_blocked_set() -> set:
    bl = st.session_state.lex_theme.get("blocked_users") or []
    return {h.strip().lower() for h in bl if h}

def toggle_block_user(target_handle: str):
    th_handle = (target_handle or "").strip()
    if not th_handle:
        return
    blocked = list(st.session_state.lex_theme.get("blocked_users") or [])
    low_map = {h.lower(): h for h in blocked}
    if th_handle.lower() in low_map:
        blocked = [h for h in blocked if h.lower() != th_handle.lower()]
    else:
        blocked.append(th_handle)
        st.session_state.lex_friends = [f for f in st.session_state.lex_friends if f["handle"].lower() != th_handle.lower()]
        st.session_state.lex_top8 = [t for t in st.session_state.lex_top8 if t["handle"].lower() != th_handle.lower()]
        for idx, item in enumerate(st.session_state.lex_top8):
            item["rank"] = idx + 1
    st.session_state.lex_theme["blocked_users"] = blocked
    save_profile_to_cloud()

def submit_content_report(reporter_handle: str, target_handle: str, reason: str, post_id=None, snippet: str = ""):
    rep_key = f"post:{post_id}" if post_id is not None else f"user:{target_handle.lower()}"
    reported = list(st.session_state.lex_theme.get("reported_items") or [])
    if rep_key not in reported:
        reported.append(rep_key)
        st.session_state.lex_theme["reported_items"] = reported
        save_profile_to_cloud()
    if sb:
        try:
            clean_snip = (snippet or "")[:120].replace("\n", " ")
            alert_body = f"[MOD_REPORT] Target: {target_handle} | Item: {rep_key} | Reason: {reason} | Preview: {clean_snip}"
            sb.table("lex_messages").insert({
                "sender_handle": reporter_handle,
                "recipient_handle": "@Heidi",
                "body": alert_body,
            }).execute()
            if post_id is not None:
                all_reps = sb.table("lex_messages").select("sender_handle").ilike("body", f"%Item: post:{post_id} %").execute().data or []
                unique_reporters = {r.get("sender_handle", "").lower() for r in all_reps if r.get("sender_handle")}
                if len(unique_reporters) >= 3:
                    sb.table("lex_posts").update({"body": "[HIDDEN_BY_COMMUNITY_MODERATION]"}).eq("id", post_id).execute()
        except Exception:
            pass
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
    "blocked_users": [], "reported_items": [],
}

DEFAULT_TOP8 = [
    {"rank": 1, "handle": "@LeX", "name": "LeX (Studio Co-Pilot)", "mood": "Online • Remixing Vibes ⚡", "anthem": "Y2K Cobalt Synth"},
    {"rank": 2, "handle": "@Heidi", "name": "Heidi Seckman", "mood": "Founder @ LexiTech Studio ✦", "anthem": "Velvet Chrome Rhodes"},
    {"rank": 3, "handle": "@Nova", "name": "Nova Chen", "mood": "Late-night synth session 🎧", "anthem": "Midnight Tokyo Lo-Fi"},
    {"rank": 4, "handle": "@Kai", "name": "Kai Mercer", "mood": "Zero algorithms, pure vibes ✦", "anthem": "Neon Arcade Pulse"},
    {"rank": 5, "handle": "@Roxy", "name": "Roxy Riot", "mood": "Spray-painting my profile wall 🎸", "anthem": "Y2K Cobalt Synth"},
    {"rank": 6, "handle": "@Zane", "name": "Zane Vance", "mood": "2006 playlist on repeat 🔥", "anthem": "Neon Arcade Pulse"},
    {"rank": 7, "handle": "@Mina", "name": "Mina Solis", "mood": "Night owl mode 🌙", "anthem": "Midnight Tokyo Lo-Fi"},
    {"rank": 8, "handle": "@Jax", "name": "Jax Sterling", "mood": "Hanging in Vibe-Sync 💠", "anthem": "Velvet Chrome Rhodes"},
]

def founder_badge_html(handle: str) -> str:
    if (handle or "").strip().lower() not in {"@heidi", "@heidiseckman"}:
        return ""
    return '<span style="display:inline-block;margin-left:8px;padding:3px 10px;border-radius:99px;background:linear-gradient(90deg,#F59E0B,#EC4899);color:#000000;font-size:11px;font-weight:900;letter-spacing:0.06em;box-shadow:0 0 12px #EC4899;">👑 CREATOR &amp; FOUNDER</span>'

def founder_studio_link_html(handle: str, accent: str) -> str:
    if (handle or "").strip().lower() not in {"@heidi", "@heidiseckman"}:
        return ""
    return f'<div style="margin-top:6px;"><a href="{LEXITECH_HUB_URL}" target="_blank" style="display:inline-block;padding:4px 12px;border-radius:99px;background:{accent}26;border:1.5px solid {accent};color:#FFFFFF;font-size:12px;font-weight:800;text-decoration:none;box-shadow:0 0 10px {accent}66;">✦ LexiTech Studio ↗</a></div>'
def build_backdrop_url(style_name: str, accent: str, tag_word: str = "LeX!") -> str:
    w = (tag_word or "LeX!")[:14].replace("<", "").replace(">", "").replace("&", "")
    if style_name == "Architectural Grid":
        return "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)"
    if style_name == "Checkered Ska / Vans":
        return f"repeating-conic-gradient({accent}28 0% 25%, transparent 0% 50%) 50% / 60px 60px"
    art_map = {
        "Punk Spray-Paint Graffiti": f'<text x="16" y="88" font-family="cursive" font-size="46" font-weight="900" fill="{accent}" fill-opacity="0.30" transform="rotate(-11 70 80)">{w}</text><path d="M20 145 Q110 120 230 155" stroke="{accent}" stroke-width="3" stroke-opacity="0.32" fill="none" stroke-dasharray="12 6"/>',
        "Y2K Stars & Sparkles": f'<polygon points="55,18 64,44 92,44 69,60 78,86 55,70 32,86 41,60 18,44 46,44" fill="none" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.36"/><path d="M185,115 L193,140 L218,148 L193,156 L185,181 L177,156 L152,148 Z" fill="{accent}" fill-opacity="0.28"/>',
        "Leopard Rosette Print": f'<circle cx="57" cy="54" r="20" fill="{accent}" fill-opacity="0.22" stroke="#FFF" stroke-opacity="0.26" stroke-width="4" stroke-dasharray="14 6"/><circle cx="177" cy="157" r="22" fill="{accent}" fill-opacity="0.24" stroke="#FFF" stroke-opacity="0.26" stroke-width="4" stroke-dasharray="16 6"/>',
        "Cherry Hearts & Kisses": f'<path d="M60,78 C60,78 26,54 26,35 C26,22 38,16 48,24 C54,28 60,36 60,36 C60,36 66,28 72,24 C82,16 94,22 94,35 C94,54 60,78 60,78 Z" fill="none" stroke="{accent}" stroke-width="2.5" stroke-opacity="0.38"/>',
        "Coquette Ribbon Bows": f'<path d="M65,55 L32,35 L38,75 Z M65,55 L98,35 L92,75 Z" fill="{accent}" fill-opacity="0.25" stroke="{accent}" stroke-width="2.2"/><circle cx="65" cy="55" r="6" fill="#FFF" fill-opacity="0.4"/>',
        "Butterfly Dreamscape": f'<path d="M65,60 C35,20 15,55 48,72 C22,85 42,110 65,80 C88,110 108,85 82,72 C115,55 95,20 65,60 Z" fill="{accent}" fill-opacity="0.24" stroke="{accent}" stroke-width="2"/>',
        "Skull & Crossbones Punk": f'<circle cx="65" cy="52" r="22" fill="none" stroke="#FFF" stroke-width="2.2" stroke-opacity="0.28"/><circle cx="57" cy="50" r="4" fill="{accent}"/><circle cx="73" cy="50" r="4" fill="{accent}"/>',
        "Lightning Bolts & Voltage": f'<polygon points="72,18 38,72 64,72 50,122 96,62 68,62" fill="{accent}" fill-opacity="0.26" stroke="{accent}" stroke-width="2"/>',
        "Gothic Bats & Moons": f'<path d="M175,35 A28,28 0 1,0 205,75 A22,22 0 1,1 175,35 Z" fill="{accent}" fill-opacity="0.30"/>',
        "Cyber Matrix Rain": f'<text x="18" y="45" font-family="monospace" font-size="16" font-weight="700" fill="{accent}" fill-opacity="0.36">010110 // {w}</text><text x="24" y="175" font-family="monospace" font-size="16" fill="#FFF" fill-opacity="0.20">SYS_OVERRIDE</text>',
        "Carbon Fiber Hex": f'<polygon points="60,18 96,38 96,78 60,98 24,78 24,38" fill="none" stroke="{accent}" stroke-opacity="0.34" stroke-width="2.2"/>',
        "Retro Cassette & Vinyl": f'<rect x="24" y="28" width="88" height="54" rx="6" fill="none" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.38"/><circle cx="180" cy="160" r="36" fill="none" stroke="{accent}" stroke-width="2"/>',
        "Flame & Hotrod Stripes": f'<path d="M55,105 C32,85 38,55 58,32 C55,52 68,56 72,42 C88,65 82,92 55,105 Z" fill="{accent}" fill-opacity="0.30" stroke="{accent}" stroke-width="2"/>',
        "Crown & Diamond Luxe": f'<polygon points="28,78 28,38 48,56 65,30 82,56 102,38 102,78" fill="none" stroke="{accent}" stroke-width="2.4" stroke-opacity="0.42"/>',
        "Rose Thorns & Petals": f'<circle cx="65" cy="55" r="22" fill="none" stroke="{accent}" stroke-width="2.5"/><line x1="65" y1="77" x2="65" y2="122" stroke="{accent}" stroke-width="2.4"/>',
        "8-Bit Arcade Invaders": f'<path d="M40,40 h10 v10 h20 v-10 h10 v20 h10 v20 h-10 v-10 h-40 v10 h-10 v-20 h10 z" fill="{accent}" fill-opacity="0.30"/>',
        "Tactical Urban Camo": f'<polygon points="18,28 68,18 92,46 64,74 22,62" fill="{accent}" fill-opacity="0.22"/><polygon points="125,85 188,72 225,108 192,142 138,125" fill="#FFF" fill-opacity="0.11"/>',
        "Cosmic Planets & Rings": f'<circle cx="68" cy="62" r="22" fill="{accent}" fill-opacity="0.26" stroke="{accent}" stroke-width="2"/><ellipse cx="68" cy="62" rx="44" ry="11" transform="rotate(-22 68 62)" fill="none" stroke="#FFF" stroke-width="2.2" stroke-opacity="0.34"/>',
    }
    body = art_map.get(style_name, art_map["Punk Spray-Paint Graffiti"])
    raw_svg = f'{SV_OPEN}xmlns="{SVG_NS}" width="260" height="220">{body}{SV_CLOSE}'
    return f'url("data:image/svg+xml,{urllib.parse.quote(raw_svg)}")'

def calc_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def encode_image_data_url(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    b64 = base64.b64encode(uploaded_file.getvalue()).decode("ascii")
    return f"data:{uploaded_file.type or 'image/png'};base64,{b64}"

def normalize_url(raw_url: str) -> str:
    clean = (raw_url or "").strip()
    if not clean:
        return ""
    return clean if (clean.startswith("http://") or clean.startswith("https://")) else ("https://" + clean)

def extract_yt_id(raw: str) -> str:
    s = (raw or "").strip()
    if len(s) == 11 and "/" not in s and "." not in s and re.match(r"^[A-Za-z0-9_-]{11}$", s):
        return s
    for sep in ["youtu.be/", "v=", "/embed/"]:
        if sep in s:
            _, _, tail = s.partition(sep)
            head, _, _ = tail.partition("?")
            head, _, _ = head.partition("&")
            cand = head.strip("/")[:11]
            if re.match(r"^[A-Za-z0-9_-]{11}$", cand):
                return cand
    return ""
def save_profile_to_cloud():
    sb = get_sb()
    u = st.session_state.get("lex_user")
    if not sb or not u or not u.get("user_id"):
        return
    try:
        theme_payload = st.session_state.lex_theme.copy()
        theme_payload["avatar"] = u.get("avatar", "")
        theme_payload["website"] = u.get("website", "")
        theme_payload["all_friends"] = st.session_state.lex_friends
        sb.table("lex_profiles").upsert({
            "user_id": u["user_id"], "handle": u["handle"], "display_name": u["name"],
            "bio": u.get("bio", ""), "who_to_meet": u.get("who_to_meet", ""),
            "mood": u.get("mood", "Online Now • Vibing ⚡"), "anthem": u.get("anthem", "Y2K Cobalt Synth"),
            "custom_song_url": u.get("custom_song_url", ""), "custom_song_title": u.get("custom_song_title", ""),
            "theme_json": theme_payload, "top8_json": st.session_state.lex_top8, "wall_json": st.session_state.lex_wall,
        }).execute()
    except Exception as e:
        st.warning(f"Cloud sync notice: {e}")

def toggle_follow_user(my_handle: str, target_handle: str):
    sb = get_sb()
    following = list(st.session_state.lex_theme.get("following") or [])
    adding = target_handle not in following
    following.append(target_handle) if adding else following.remove(target_handle)
    st.session_state.lex_theme["following"] = following
    save_profile_to_cloud()
    if sb:
        try:
            res = sb.table("lex_profiles").select("user_id, theme_json").eq("handle", target_handle).execute().data
            t_row = next(iter(res), None) if isinstance(res, list) else res
            if isinstance(t_row, dict):
                tj = t_row.get("theme_json") or {}
                f_list = list(tj.get("followers") or [])
                if adding and my_handle not in f_list:
                    f_list.append(my_handle)
                elif not adding and my_handle in f_list:
                    f_list.remove(my_handle)
                tj["followers"] = f_list
                sb.table("lex_profiles").update({"theme_json": tj}).eq("user_id", t_row["user_id"]).execute()
        except Exception:
            pass

def render_popular_song_embed(url: str) -> bool:
    clean = (url or "").strip()
    ok_u, _ = check_url_safety(clean)
    if not clean or not ok_u:
        return False
    sp_host = ".".join(["open", "spotify", "com"]) + "/track/"
    if sp_host in clean:
        _, _, tail = clean.partition(sp_host)
        track_id, _, _ = tail.partition("?")
        tid = re.sub(r"[^A-Za-z0-9]", "", track_id.strip("/"))
        if tid:
            components.iframe(f"{SPOTIFY_EMBED}{tid}?utm_source=generator&theme=0", height=152)
            return True
    if "youtube.com" in clean or "youtu.be/" in clean:
        yid = extract_yt_id(clean)
        if yid:
            st.video(f"https://youtube.com{yid}")
            return True
    ap_host = ".".join(["music", "apple", "com"])
    if ap_host in clean and ("embed." + ap_host) not in clean:
        components.iframe(clean.replace(ap_host, "embed." + ap_host), height=175)
        return True
    return False

def render_mini_yt_audio_bar(yt_id: str, track_label: str, accent: str):
    if not yt_id or not re.match(r"^[A-Za-z0-9_-]{11}$", yt_id):
        return
    src = f"{YT_EMBED_BASE}{yt_id}?autoplay=1&controls=1&rel=0"
    st.markdown(f'<div class="lex-card" style="padding:8px 10px;margin:8px 0;"><div style="font-size:12px;font-weight:800;color:{accent};margin-bottom:4px;">🎧 NOW SPINNING: {track_label}</div><div style="height:46px;overflow:hidden;border-radius:6px;"><iframe width="100%" height="140" src="{src}" frameborder="0" allow="autoplay; encrypted-media" style="margin-top:-92px;"></iframe></div></div>', unsafe_allow_html=True)
for k, v in [("lex_user", None), ("lex_theme", DEFAULT_THEME.copy()), ("lex_top8", [i.copy() for i in DEFAULT_TOP8]), ("lex_friends", [i.copy() for i in DEFAULT_TOP8]), ("viewing_handle", None)]:
    if k not in st.session_state:
        st.session_state[k] = v
if "lex_wall" not in st.session_state:
    st.session_state.lex_wall = [{"sender": "@LeX", "msg": "Welcome to LeX! Drop a wall note anytime ✦"}]

th = st.session_state.lex_theme
g_font_name, css_font_family = FONT_MAP.get(th.get("font", "Clean Studio Sans"), FONT_MAP["Clean Studio Sans"])
bg_pattern = build_backdrop_url(th.get("backdrop", "Architectural Grid"), th["accent"], th.get("spray_word", "LeX!"))
custom_wall = th.get("custom_wall", "")
bg_css_img = f'url("{custom_wall}")' if custom_wall else bg_pattern
bg_size = "cover" if custom_wall else ("56px 56px" if th.get("backdrop") == "Architectural Grid" else "260px 220px")
bg_repeat = "no-repeat" if custom_wall else "repeat"
glow_css = f"box-shadow: 0 0 18px {th['accent']}66, inset 0 0 10px {th['accent']}22;" if th.get("glow_borders", True) else ""
op_val = max(40, min(100, int(th.get("card_opacity", 92)))) / 100.0
rad_px = int(th.get("card_radius", 12))
extra_css = sanitize_custom_css(th.get("custom_css") or "")

css = (
    f'{LK_OPEN}rel="stylesheet" href="{GFONTS_BASE}{g_font_name.replace(" ", "+")}&display=swap" />' + ST_OPEN
    + f'[data-testid="stAppViewContainer"], .stApp {{ background-color: {th["bg"]} !important; background-image: {bg_css_img} !important; background-size: {bg_size} !important; background-repeat: {bg_repeat} !important; background-attachment: fixed !important; color: {th["text"]} !important; }}'
    + '[data-testid="stHeader"], [data-testid="stMain"] { background: transparent !important; }'
    + f".lex-banner {{ background: radial-gradient(circle at 15% 50%, rgba(236,72,153,0.18), {th['card']} 65%); border: 2px {th['border_style']} {th['accent']}; border-radius: {rad_px}px; padding: 18px 24px; margin-bottom: 16px; {glow_css} }}"
    + f".lex-wordmark {{ font-family: {css_font_family}; font-size: 38px; font-weight: 800; color: #FFFFFF; text-shadow: 0 0 22px {th['accent']}; }}"
    + f".lex-card {{ background: {th['card']}; opacity: {op_val}; border: 1.5px {th['border_style']} {th['accent']}; border-radius: {rad_px}px; padding: 16px 18px; margin-bottom: 12px; {glow_css} }}"
    + f".lex-friend-card {{ background: linear-gradient(145deg, {th['card']}, #000000); opacity: {op_val}; border: 1.5px {th['border_style']} {th['accent']}; border-radius: {rad_px}px; padding: 12px; margin-bottom: 10px; {glow_css} }}"
    + f".lex-avatar {{ width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2.5px solid {th['accent']}; box-shadow: 0 0 16px {th['accent']}; }}"
    + f".lex-avatar-fallback {{ width: 80px; height: 80px; border-radius: 50%; background: {th['accent']}; color: #000; font-weight: 900; font-size: 30px; display: flex; align-items: center; justify-content: center; }}"
    + extra_css + ST_CLOSE
)
st.markdown(css, unsafe_allow_html=True)

head_c1, head_c2 = st.columns([0.16, 0.84])
with head_c1:
    if os.path.exists("lex-logo.png"):
        st.image("lex-logo.png", width=145)
with head_c2:
    st.markdown('<div class="lex-banner"><div class="lex-wordmark">LeX</div><div style="color:#A1A1AA;font-family:monospace;font-size:12px;">NEXT-GEN SOCIAL ARCHITECTURE // LEXITECH STUDIO // 13+ ONLY // 🛡️ SAFETY ENGINE ACTIVE</div></div>', unsafe_allow_html=True)

sb = get_sb()
if st.session_state.lex_user is None:
    t_in, t_up = st.tabs(["🔐 Member Sign In", "✦ Create Account (13+ Required)"])
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
                        st.session_state.lex_user = {"user_id": uid, "name": r.get("display_name", "LeX Member"), "handle": r.get("handle", "@Member"), "bio": r.get("bio", ""), "who_to_meet": r.get("who_to_meet", ""), "mood": r.get("mood", "Online Now • Vibing ⚡"), "anthem": r.get("anthem", "Y2K Cobalt Synth"), "custom_song_url": r.get("custom_song_url", ""), "custom_song_title": r.get("custom_song_title", ""), "avatar": tj.get("avatar", ""), "website": tj.get("website", "")}
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
                        fname = (prefix or "Member").capitalize()
                        st.session_state.lex_user = {"user_id": uid, "name": fname, "handle": f"@{fname}", "avatar": "", "website": "", "mood": "Online Now • Vibing ⚡", "bio": "Back on LeX ✦", "who_to_meet": "Creators & music lovers.", "anthem": "Y2K Cobalt Synth", "custom_song_url": "", "custom_song_title": ""}
                        save_profile_to_cloud()
                    st.rerun()
                except Exception as e:
                    st.error(f"Sign in failed: {e}")
    with t_up:
        with st.form("lex_signup_form"):
            s_email, s_pass = st.text_input("Email"), st.text_input("Password (6+ chars)", type="password")
            d_name, r_handle = st.text_input("Display Name"), st.text_input("@handle")
            dob = st.date_input("Date of Birth (13+ Only)", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today())
            site_in = st.text_input("Profile Link / Website (Optional)", placeholder="heidiseckman.github.io/lexitech-hub")
            if st.form_submit_button("Create Permanent LeX Account ✦", use_container_width=True) and sb:
                ch = re.sub(r"[^A-Za-z0-9_]", "", r_handle.strip().lstrip("@"))
                ok_txt, err_txt = check_text_and_links(f"{d_name} {ch}", site_in)
                if calc_age(dob) < 13:
                    st.error("Must be 13+ to join LeX.")
                elif not ok_txt:
                    st.error(err_txt)
                elif s_email.strip() and len(s_pass) >= 6 and d_name.strip() and ch:
                    try:
                        ares = sb.auth.sign_up({"email": s_email.strip(), "password": s_pass})
                        st.session_state.lex_user = {"user_id": ares.user.id, "name": d_name.strip(), "handle": f"@{ch}", "avatar": "", "website": normalize_url(site_in), "mood": "Online Now • Vibing ⚡", "bio": "Zero algorithms. Custom vibes on LeX.", "who_to_meet": "Creators & music lovers.", "anthem": "Y2K Cobalt Synth", "custom_song_url": "", "custom_song_title": ""}
                        save_profile_to_cloud()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Signup error: {e}")
    st.stop()
user = st.session_state.lex_user
top_c1, top_c2 = st.columns([0.85, 0.15])
if st.session_state.viewing_handle and top_c1.button(f"← Back to My Profile ({user['handle']})"):
    st.session_state.viewing_handle = None
    st.rerun()
if top_c2.button("Sign Out"):
    st.session_state.lex_user = None
    st.session_state.viewing_handle = None
    st.rerun()

def friend_card_html(fr: dict, badge: str = "") -> str:
    ini = (fr.get("name", "L")[:1] or "L").upper()
    is_owner = (fr.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"})
    pill_lbl = "👑 FOUNDER" if is_owner else badge
    top_tag = f'<span style="background:{th["accent"]};color:#000;padding:2px 7px;border-radius:99px;font-size:10px;font-weight:900;">{pill_lbl}</span>' if pill_lbl else ""
    return f'<div class="lex-friend-card"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">{top_tag}<span style="color:#34D399;font-size:11px;font-weight:700;">● ONLINE</span></div><div style="display:flex;align-items:center;gap:10px;"><div style="width:42px;height:42px;border-radius:50%;background:radial-gradient(circle,{th["accent"]},#111);border:2px solid {th["accent"]};display:flex;align-items:center;justify-content:center;font-weight:900;color:#FFF;box-shadow:0 0 10px {th["accent"]};">{ini}</div><div><div style="font-weight:800;font-size:14px;color:{th["text"]};">{fr["name"]}</div><div style="color:{th["accent"]};font-size:12px;font-weight:700;">{fr["handle"]}</div></div></div><div style="font-size:11px;color:#D4D4D8;margin-top:8px;">{fr.get("mood", "Vibing ⚡")}</div><div style="margin-top:6px;padding:4px 8px;border-radius:6px;background:rgba(255,255,255,0.05);font-size:10px;color:{th["accent"]};">🎵 {fr.get("anthem", "Y2K Cobalt Synth")}</div></div>'

if st.session_state.viewing_handle and sb:
    v_res = sb.table("lex_profiles").select("*").eq("handle", st.session_state.viewing_handle).execute().data
    vp = next(iter(v_res), None) if isinstance(v_res, list) else v_res
    if isinstance(vp, dict):
        vp_handle = vp.get("handle", "")
        if vp_handle.lower() in get_blocked_set():
            st.warning(f"🚫 You have blocked {vp_handle}. Unblock them below to view their profile.")
            if st.button(f"Unblock {vp_handle}", key="unblk_pub_btn"):
                toggle_block_user(vp_handle)
                st.rerun()
            st.stop()
        vtj = vp.get("theme_json") or {}
        v_fol, v_fr = list(vtj.get("followers") or []), list(vtj.get("all_friends") or [])
        v_av = f'<img src="{vtj["avatar"]}" class="lex-avatar" />' if vtj.get("avatar") else f'<div class="lex-avatar-fallback">{(vp.get("display_name", "L")[:1] or "L").upper()}</div>'
        v_is_founder = vp_handle.strip().lower() in {"@heidi", "@heidiseckman"}
        v_site = founder_studio_link_html(vp_handle, th["accent"]) if v_is_founder else (f'<div style="margin-top:6px;"><a href="{vtj["website"]}" target="_blank" style="color:{th["accent"]};font-weight:700;">🔗 {vtj["website"]}</a></div>' if vtj.get("website") else "")
        st.markdown(f'<div class="lex-card"><div style="display:flex;align-items:center;gap:16px;">{v_av}<div><h2 style="margin:0;">{vp.get("display_name", "")} {founder_badge_html(vp_handle)}</h2><div style="color:{th["accent"]};font-weight:700;">{vp_handle}</div><div style="color:#34D399;font-size:13px;">● {vp.get("mood", "Online ⚡")}</div>{v_site}</div></div><div style="display:flex;gap:18px;margin-top:12px;font-weight:800;font-size:13px;"><span>⚡ {len(v_fol)} Followers (Unlimited)</span><span>👥 {len(v_fr)} / {MAX_FRIENDS} Friends</span></div><p style="margin-top:12px;"><strong>About Me:</strong> {vp.get("bio", "")}</p><p><strong>Who I\'d Like to Meet:</strong> {vp.get("who_to_meet", "")}</p></div>', unsafe_allow_html=True)
        ac1, ac2, ac3 = st.columns([0.4, 0.4, 0.2])
        is_fol = vp_handle in (th.get("following") or [])
        if ac1.button("✓ Following (Unfollow)" if is_fol else "⚡ Follow Creator (Unlimited)", use_container_width=True):
            toggle_follow_user(user["handle"], vp_handle)
            st.rerun()
        is_fr = any(f["handle"].lower() == vp_handle.lower() for f in st.session_state.lex_friends)
        if is_fr:
            ac2.button("✓ In Your Friends List", disabled=True, use_container_width=True)
        elif len(st.session_state.lex_friends) >= MAX_FRIENDS:
            ac2.button(f"Max {MAX_FRIENDS} Friends Reached", disabled=True, use_container_width=True)
        elif ac2.button(f"+ Add Friend ({len(st.session_state.lex_friends)}/{MAX_FRIENDS})", use_container_width=True):
            st.session_state.lex_friends.append({"handle": vp_handle, "name": vp["display_name"], "mood": vp.get("mood", "Online ⚡"), "anthem": vp.get("anthem", "Y2K Cobalt Synth")})
            save_profile_to_cloud()
            st.rerun()
        if not v_is_founder and ac3.button("🚫 Block", use_container_width=True, key="blk_pub_btn"):
            toggle_block_user(vp_handle)
            st.session_state.viewing_handle = None
            st.rerun()
        if not v_is_founder:
            with st.expander("🚩 Report Profile"):
                rep_reason = st.selectbox("Reason", ["Graphic / Explicit Content", "Harassment / Hate Speech", "Spam / Malicious Link", "Underage Account (<13)"], key="pub_rep_rsn")
                if st.button("Submit Profile Report", key="pub_rep_btn"):
                    submit_content_report(user["handle"], vp_handle, rep_reason, snippet=vp.get("bio", ""))
                    st.success("Report logged for LexiTech moderation review.")
        if vp.get("custom_song_url"):
            render_popular_song_embed(vp["custom_song_url"])
        v_albs = list(vtj.get("albums") or [])
        if v_albs:
            st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{th["accent"]};">📸 {vp.get("display_name", "")}\'s Featured Albums</strong></div>', unsafe_allow_html=True)
            va_pick = st.selectbox("View Album", [a["title"] for a in v_albs], key="pub_alb_sel")
            va_obj = next((a for a in v_albs if a["title"] == va_pick), {})
            va_cols = st.columns(3)
            for idx_p, ph in enumerate(va_obj.get("photos") or []):
                va_cols[idx_p % 3].markdown(f'<div class="lex-card" style="padding:6px;"><img src="{ph["img"]}" style="width:100%;height:150px;object-fit:cover;border-radius:8px;" /><div style="font-size:11px;margin-top:4px;">{ph.get("caption","")}</div></div>', unsafe_allow_html=True)
        st.stop()
def render_social_hub():
    t_feed, t_friends, t_dm, t_top8, t_studio, t_radar = st.tabs([
        "📰 Feed", "👥 All Friends", "✉ Messages", "✦ Top 8", "🎨 LeX Studio", "📡 Radar"
    ])
    with t_feed:
        with st.form("feed_post_form", clear_on_submit=True):
            new_post = st.text_area("Share a status update, photo, or link...", height=68)
            fc1, fc2 = st.columns(2)
            post_img = fc1.file_uploader("Attach Photo (Max 5MB)", type=["png", "jpg", "jpeg", "webp"], key="fp_img")
            post_link = fc2.text_input("Attach Link / URL", placeholder="https://...", key="fp_link")
            if st.form_submit_button("Publish Status ✦") and (new_post.strip() or post_img or post_link.strip()) and sb:
                ok_txt, msg_txt = check_text_and_links(new_post, post_link)
                ok_img, msg_img = validate_and_scan_media(post_img)
                if not ok_txt:
                    st.error(f"🛡️ Safety Filter: {msg_txt}")
                elif not ok_img:
                    st.error(f"🛡️ Media Safety Filter: {msg_img}")
                else:
                    packed = new_post.strip()
                    if post_link.strip():
                        packed += f"\n[LEX_LINK]{normalize_url(post_link)}"
                    if post_img is not None:
                        packed += f"\n[LEX_IMG]{encode_image_data_url(post_img)}"
                    sb.table("lex_posts").insert({"handle": user["handle"], "author": user["name"], "body": packed, "likes": 0}).execute()
                    st.rerun()

        blocked_now = get_blocked_set()
        reported_now = set(st.session_state.lex_theme.get("reported_items") or [])
        posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(30).execute().data or [] if sb else []
        for p in posts:
            p_handle = (p.get("handle") or "").strip()
            raw_body = p.get("body") or ""
            if p_handle.lower() in blocked_now or f"post:{p['id']}" in reported_now or raw_body == "[HIDDEN_BY_COMMUNITY_MODERATION]":
                continue
            clean_txt, img_src, lnk_src = raw_body, "", ""
            if "[LEX_IMG]" in clean_txt:
                clean_txt, img_src = clean_txt.split("[LEX_IMG]", 1)
            if "[LEX_LINK]" in clean_txt:
                clean_txt, lnk_src = clean_txt.split("[LEX_LINK]", 1)
            clean_txt, lnk_src, img_src = clean_txt.strip(), lnk_src.strip(), img_src.strip()
            ok_lnk, _ = check_url_safety(lnk_src)
            if lnk_src and not ok_lnk:
                lnk_src = ""
            img_tag = f'<img src="{img_src}" style="width:100%;max-height:360px;object-fit:cover;border-radius:10px;margin-top:10px;border:1px solid {th["accent"]};" />' if img_src else ""
            lnk_tag = f'<div style="margin-top:8px;"><a href="{lnk_src}" target="_blank" style="display:inline-block;padding:6px 12px;border-radius:8px;background:{th["accent"]}22;border:1px solid {th["accent"]};color:{th["accent"]};font-weight:700;text-decoration:none;">🔗 {lnk_src}</a></div>' if lnk_src else ""
            st.markdown(f'<div class="lex-card"><strong>{p["author"]}</strong> <span style="color:{th["accent"]};">{p_handle}</span>{founder_badge_html(p_handle)}<p style="margin-top:6px;">{clean_txt}</p>{lnk_tag}{img_tag}</div>', unsafe_allow_html=True)

            rx_key = f"rx_{p['id']}"
            if rx_key not in st.session_state:
                st.session_state[rx_key] = {"🔥": p.get("likes", 0), "💖": 0, "🎸": 0, "💀": 0}
            is_self_post = p_handle.lower() == user["handle"].lower()
            is_founder_post = p_handle.lower() in {"@heidi", "@heidiseckman"}
            rcols = st.columns([0.16, 0.16, 0.16, 0.16, 0.18, 0.18])
            for idx_e, emo in enumerate(["🔥", "💖", "🎸", "💀"]):
                if rcols[idx_e].button(f"{emo} {st.session_state[rx_key][emo]}", key=f"b_{p['id']}_{emo}"):
                    st.session_state[rx_key][emo] += 1
                    if emo == "🔥" and sb:
                        sb.table("lex_posts").update({"likes": st.session_state[rx_key]["🔥"]}).eq("id", p["id"]).execute()
                    st.rerun()
            if not is_self_post and not is_founder_post:
                if rcols[4].button("🚩 Report", key=f"rep_{p['id']}"):
                    st.session_state[f"show_rep_{p['id']}"] = not st.session_state.get(f"show_rep_{p['id']}", False)
                if rcols[5].button("🚫 Block", key=f"blk_{p['id']}"):
                    toggle_block_user(p_handle)
                    st.rerun()
            if st.session_state.get(f"show_rep_{p['id']}", False):
                rc1, rc2 = st.columns([0.7, 0.3])
                rsn = rc1.selectbox("Select violation", ["Graphic / Explicit Media", "Harassment / Hate", "Spam / Unsafe Link"], key=f"rsn_{p['id']}", label_visibility="collapsed")
                if rc2.button("Confirm Hide & Report", key=f"conf_rep_{p['id']}"):
                    submit_content_report(user["handle"], p_handle, rsn, post_id=p["id"], snippet=clean_txt)
                    st.session_state[f"show_rep_{p['id']}"] = False
                    st.rerun()
    return t_friends, t_dm, t_top8, t_studio, t_radar
def render_block(blk: str):
    if blk == "Profile Card":
        if th.get("marquee_on") and th.get("marquee_text"):
            st.markdown(f'<div class="lex-card" style="padding:6px 12px;"><marquee style="color:{th["accent"]};font-weight:800;letter-spacing:0.06em;">{th["marquee_text"]}</marquee></div>', unsafe_allow_html=True)
        if th.get("pinned_note"):
            st.markdown(f'<div class="lex-card" style="border-width:2.5px;"><span style="color:{th["accent"]};font-weight:900;font-size:11px;">📌 PINNED BULLETIN</span><div style="margin-top:4px;">{th["pinned_note"]}</div></div>', unsafe_allow_html=True)
        av_html = f'<img src="{user["avatar"]}" class="lex-avatar" />' if user.get("avatar") else f'<div class="lex-avatar-fallback">{(user["name"][:1] or "L").upper()}</div>'
        is_owner = user.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"}
        site_url = user.get("website", "")
        site_badge = founder_studio_link_html(user.get("handle", ""), th["accent"]) if is_owner else (f'<div style="margin-top:6px;"><a href="{site_url}" target="_blank" style="color:{th["accent"]};font-weight:700;text-decoration:none;">🔗 {site_url}</a></div>' if site_url else "")
        fol_cnt, ing_cnt, fr_cnt = len(th.get("followers") or []), len(th.get("following") or []), len(st.session_state.lex_friends)
        ints = [(lbl, th.get(k, "")) for lbl, k in [("General", "int_general"), ("Music", "int_music"), ("Movies", "int_movies"), ("TV", "int_tv"), ("Books & Heroes", "int_books")] if th.get(k)]
        int_html = "".join([f'<div style="font-size:12px;margin-top:4px;"><strong style="color:{th["accent"]};">{l}:</strong> {v}</div>' for l, v in ints])
        st.markdown(f'<div class="lex-card"><div style="display:flex;align-items:center;gap:14px;">{av_html}<div><h2 style="margin:0;color:{th["text"]};">{user["name"]} {founder_badge_html(user["handle"])}</h2><div style="color:{th["accent"]};font-weight:700;">{user["handle"]}</div><div style="color:#34D399;font-size:13px;">● {user["mood"]}</div>{site_badge}</div></div><div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.04);font-size:12px;font-weight:800;"><span>⚡ {fol_cnt} Followers</span><span>✦ {ing_cnt} Following</span><span>👥 {fr_cnt} / {MAX_FRIENDS} Friends</span></div><p style="margin-top:12px;"><strong>About Me:</strong> {user["bio"]}</p><p><strong>Who I\'d Like to Meet:</strong> {user["who_to_meet"]}</p>{int_html}</div>', unsafe_allow_html=True)
    elif blk == "Photo Albums":
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{th["accent"]};font-size:15px;">📸 {user["name"]}\'s Photo Albums</strong></div>', unsafe_allow_html=True)
        albums = list(th.get("albums") or [])
        if albums:
            pick_alb = st.selectbox("Select Album", [a["title"] for a in albums], key="alb_view_sel")
            cur_alb = next((a for a in albums if a["title"] == pick_alb), next(iter(albums), {}))
            photos = cur_alb.get("photos") or []
            if photos:
                p_cols = st.columns(2)
                for pi_idx, ph in enumerate(photos):
                    with p_cols[pi_idx % 2]:
                        cap_html = f'<div style="font-size:11px;color:#D4D4D8;margin-top:4px;">{ph["caption"]}</div>' if ph.get("caption") else ""
                        st.markdown(f'<div class="lex-card" style="padding:8px;"><img src="{ph["img"]}" style="width:100%;height:150px;object-fit:cover;border-radius:8px;" />{cap_html}</div>', unsafe_allow_html=True)
                        if st.button("Remove ✕", key=f"rm_ph_{pick_alb}_{pi_idx}"):
                            cur_alb["photos"].pop(pi_idx)
                            st.session_state.lex_theme["albums"] = albums
                            save_profile_to_cloud()
                            st.rerun()
        with st.expander("+ Manage / Add Featured Photo Album"):
            new_alb_name = st.text_input("New or Existing Album Name", placeholder="Vibe Dump 2026", key="alb_name_in")
            alb_up = st.file_uploader("Upload Photo (Max 5MB)", type=["png", "jpg", "jpeg", "webp"], key="alb_img_up")
            alb_cap = st.text_input("Photo Caption (Optional)", placeholder="Late night studio session ✦", key="alb_cap_in")
            if st.button("Add Photo to Album ✦", key="alb_save_btn"):
                t_clean = new_alb_name.strip()
                ok_c, msg_c = check_text_and_links(f"{t_clean} {alb_cap}")
                ok_m, msg_m = validate_and_scan_media(alb_up)
                if not ok_c:
                    st.error(f"🛡️ Safety Filter: {msg_c}")
                elif not ok_m:
                    st.error(f"🛡️ Media Safety Filter: {msg_m}")
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
    elif blk == "Top 8 Friends":
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{th["accent"]};font-size:15px;">✦ {user["name"]}\'s Top 8</strong></div>', unsafe_allow_html=True)
        g_cols = st.columns(2)
        for i_t, fr in enumerate(st.session_state.lex_top8[:8]):
            g_cols[i_t % 2].markdown(friend_card_html(fr, "👑 #1" if fr["rank"] == 1 else f"#{fr['rank']}"), unsafe_allow_html=True)
    elif blk == "Profile Anthem":
        st.markdown(f'<div class="lex-card" style="padding:12px 16px;margin-bottom:8px;"><strong style="color:{th["accent"]};font-size:15px;">🎵 Main Profile Anthem &amp; Playlist</strong><div style="font-size:11px;color:#A1A1AA;">Synced to your LeX Studio card theme</div></div>', unsafe_allow_html=True)
        mode = st.radio("Main Song Source", ["Popular Song Link", "Built-In LeX Synth"], horizontal=True, key="anthem_src")
        if mode.startswith("Popular"):
            s_url = st.text_input("Spotify / YouTube / Apple Link", value=user.get("custom_song_url", ""), key="s_url_in")
            if st.button("Save Main Anthem 🎵", key="save_s_btn"):
                ok_s, msg_s = check_url_safety(s_url)
                if not ok_s:
                    st.error(f"🛡️ Link Safety Filter: {msg_s}")
                else:
                    user["custom_song_url"] = s_url.strip()
                    save_profile_to_cloud()
                    st.rerun()
            if user.get("custom_song_url"):
                render_popular_song_embed(user["custom_song_url"])
        else:
            pick_synth = st.selectbox("Synth Track", list(ANTHEM_TRACKS.keys()), key="synth_pick")
            st.audio(generate_anthem_wav(pick_synth), format="audio/wav")
        plist = list(th.get("playlist") or [])
        active_idx = st.session_state.get("active_pl_idx", -1)
        if 0 <= active_idx < len(plist):
            cur_tr = next(iter(plist[active_idx:active_idx + 1]), {})
            render_mini_yt_audio_bar(cur_tr.get("yt_id", ""), f"{cur_tr.get('title', '')} — {cur_tr.get('artist', '')}", th["accent"])
        for pi, tr in enumerate(plist):
            st.markdown(f'<div class="lex-card" style="padding:8px 12px;margin-bottom:6px;"><strong style="color:{th["text"]};">{pi + 1}. {tr["title"]}</strong> <span style="color:{th["accent"]};font-size:12px;">· {tr["artist"]}</span></div>', unsafe_allow_html=True)
            pc1, pc2 = st.columns(2)
            if pc1.button("▶ Play Track", key=f"pl_play_{pi}", use_container_width=True):
                st.session_state["active_pl_idx"] = pi
                st.rerun()
            if pc2.button("✕ Remove", key=f"pl_del_{pi}", use_container_width=True):
                plist.pop(pi)
                st.session_state.lex_theme["playlist"] = plist
                st.session_state["active_pl_idx"] = -1
                save_profile_to_cloud()
                st.rerun()
        with st.expander("+ Add YouTube Song to Playlist"):
            p_title = st.text_input("Song Title", placeholder="Misery Business", key="pl_t")
            p_artist = st.text_input("Artist", placeholder="Paramore", key="pl_a")
            p_yt = st.text_input("YouTube Link or 11-Char Video Code", placeholder="aCyGvGEtOwc", key="pl_y")
            if st.button("Add to Playlist ✦", key="pl_add_btn"):
                yid = extract_yt_id(p_yt)
                ok_p, msg_p = check_text_and_links(f"{p_title} {p_artist}")
                if not ok_p:
                    st.error(f"🛡️ Safety Filter: {msg_p}")
                elif yid and p_title.strip():
                    plist.append({"title": p_title.strip(), "artist": p_artist.strip() or "Unknown Artist", "yt_id": yid})
                    st.session_state.lex_theme["playlist"] = plist
                    save_profile_to_cloud()
                    st.rerun()
                else:
                    st.warning("Enter a song title and valid YouTube URL or 11-character code.")
  elif blk == "Profile Wall":
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{th["accent"]};font-size:15px;">💬 Profile Wall</strong></div>', unsafe_allow_html=True)
        w_msg = st.text_input("Sign profile wall...", key="wall_in")
        if st.button("Post Wall Note", key="wall_btn") and w_msg.strip():
            ok_w, msg_w = check_text_and_links(w_msg)
            if not ok_w:
                st.error(f"🛡️ Safety Filter: {msg_w}")
            else:
                st.session_state.lex_wall.insert(0, {"sender": user["handle"], "msg": w_msg.strip()})
                save_profile_to_cloud()
                st.rerun()
        blocked_wall = get_blocked_set()
        for w in [x for x in st.session_state.lex_wall if x.get("sender", "").lower() not in blocked_wall][:6]:
            st.markdown(f'<div class="lex-card"><strong>{w["sender"]}:</strong> {w["msg"]}</div>', unsafe_allow_html=True)

left_blks = th.get("left_blocks") or DEFAULT_LEFT
right_blks = th.get("right_blocks") or DEFAULT_RIGHT
col_l, col_r = st.columns([1.15, 1.3], gap="large")
tabs_pack = None
for target_col, blk_seq in [(col_l, left_blks), (col_r, right_blks)]:
    with target_col:
        for b in blk_seq:
            if b == "Main Social Hub":
                tabs_pack = render_social_hub()
            else:
                render_block(b)
if tabs_pack is None:
    with col_r:
        tabs_pack = render_social_hub()
t_friends, t_dm, t_top8, t_studio, t_radar = tabs_pack

with t_friends:
    
    st.markdown("#### 🔍 Discover & Follow Creators on LeX")
    q_search = st.text_input("Search by @handle or name...", key="people_q").strip().lower()
    all_profiles = sb.table("lex_profiles").select("handle, display_name, mood, anthem, theme_json").execute().data or [] if sb else []
    my_handles = {f["handle"].lower() for f in st.session_state.lex_friends}
    following_set = set(th.get("following") or [])
    blocked_disc = get_blocked_set()
    matches = [r for r in all_profiles if r["handle"] != user["handle"] and r["handle"].lower() not in blocked_disc and (not q_search or q_search in r["handle"].lower() or q_search in r["display_name"].lower())]
    for m in matches[:15]:
        m_fol = len((m.get("theme_json") or {}).get("followers") or [])
        c1, c2, c3, c4 = st.columns([0.46, 0.18, 0.18, 0.18])
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
    st.markdown(f"#### 👥 All Friends ({len(st.session_state.lex_friends)} / {MAX_FRIENDS} Max)")
    f_cols = st.columns(2)
    for idx_f, fr in enumerate(st.session_state.lex_friends):
        with f_cols[idx_f % 2]:
            is_t8 = any(t["handle"] == fr["handle"] for t in st.session_state.lex_top8)
            st.markdown(friend_card_html(fr, "★ TOP 8" if is_t8 else "FRIEND"), unsafe_allow_html=True)
            fb1, fb2, fb3 = st.columns(3)
            if fb1.button("Profile", key=f"vfr_{idx_f}"):
                st.session_state.viewing_handle = fr["handle"]
                st.rerun()
            if not is_t8 and len(st.session_state.lex_top8) < 8 and fb2.button("+ Top 8", key=f"t8p_{idx_f}"):
                st.session_state.lex_top8.append({**fr, "rank": len(st.session_state.lex_top8) + 1})
                save_profile_to_cloud()
                st.rerun()
            if fb3.button("Delete ✕", key=f"delf_{idx_f}"):
                st.session_state.lex_friends.pop(idx_f)
                st.session_state.lex_top8 = [t for t in st.session_state.lex_top8 if t["handle"] != fr["handle"]]
                for r_i, item in enumerate(st.session_state.lex_top8):
                    item["rank"] = r_i + 1
                save_profile_to_cloud()
                st.rerun()
with t_dm:
    blocked_dm = get_blocked_set()
    all_m = sb.table("lex_messages").select("*").order("id", desc=False).limit(150).execute().data or [] if sb else []
    inbox_handles = {x["sender_handle"] for x in all_m if x["recipient_handle"] == user["handle"]} | {x["recipient_handle"] for x in all_m if x["sender_handle"] == user["handle"]}
    dm_targets = sorted({h for h in ({f["handle"] for f in st.session_state.lex_friends if f["handle"] != user["handle"]} | inbox_handles | {"@LeX"}) if h.lower() not in blocked_dm})
    dc1, dc2 = st.columns([0.55, 0.45])
    picked_chat = dc1.selectbox("Select Conversation", dm_targets or ["@LeX"])
    custom_dm = dc2.text_input("Or DM any @handle", placeholder="@Roxy")
    active_chat = ("@" + custom_dm.strip().lstrip("@")) if custom_dm.strip() else picked_chat
    if active_chat.lower() in blocked_dm:
        st.warning(f"🚫 {active_chat} is blocked. Unblock them in LeX Studio to message.")
    else:
        for m in [x for x in all_m if {x["sender_handle"], x["recipient_handle"]} == {user["handle"], active_chat}]:
            if m.get("body", "").startswith("[MOD_REPORT]") and user["handle"].lower() not in {"@heidi", "@heidiseckman"}:
                continue
            st.markdown(f"**{m['sender_handle']}:** {m['body']}")
        dm_txt = st.text_input(f"Message {active_chat}...", key="dm_in")
        dm_c1, dm_c2 = st.columns([0.75, 0.25])
        if dm_c1.button("Send DM ✉", use_container_width=True) and dm_txt.strip() and sb:
            ok_d, msg_d = check_text_and_links(dm_txt)
            if not ok_d:
                st.error(f"🛡️ Safety Filter: {msg_d}")
            else:
                sb.table("lex_messages").insert({"sender_handle": user["handle"], "recipient_handle": active_chat, "body": dm_txt.strip()}).execute()
                st.rerun()
        if active_chat.lower() not in {"@heidi", "@heidiseckman", "@lex"} and dm_c2.button("🚫 Block User", use_container_width=True, key="dm_blk_btn"):
            toggle_block_user(active_chat)
            st.rerun()

with t_top8:
    st.markdown("#### Ranked Top 8 Friends")
    t_cols = st.columns(2)
    for idx, friend in enumerate(st.session_state.lex_top8):
        with t_cols[idx % 2]:
            st.markdown(friend_card_html(friend, "👑 #1" if friend["rank"] == 1 else f"#{friend['rank']}"), unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if idx > 0 and b1.button("Move Up ↑", key=f"up_{idx}"):
                lst = st.session_state.lex_top8
                lst[idx], lst[idx - 1] = lst[idx - 1], lst[idx]
                for r_i, item in enumerate(lst):
                    item["rank"] = r_i + 1
                save_profile_to_cloud()
                st.rerun()
            if b2.button("Remove ✕", key=f"rm8_{idx}"):
                st.session_state.lex_top8.pop(idx)
                for r_i, item in enumerate(st.session_state.lex_top8):
                    item["rank"] = r_i + 1
                save_profile_to_cloud()
                st.rerun()
with t_studio:
    st.markdown("#### 🖱 Drag & Drop Profile Layout Board")
    l_items = "".join([f'<div class="d-item" draggable="true" data-b="{b}">⠿ {b}</div>' for b in left_blks])
    r_items = "".join([f'<div class="d-item" draggable="true" data-b="{b}">⠿ {b}</div>' for b in right_blks])
    board_html = (
        f'{ST_OPEN}.wrap{{display:flex;gap:12px;font-family:sans-serif;color:#fff}}.col{{flex:1;background:#0b0b10;border:1.5px dashed {th["accent"]};border-radius:10px;padding:10px;min-height:130px}}.d-item{{background:#161622;border:1px solid {th["accent"]};padding:7px 9px;margin:5px 0;border-radius:8px;cursor:grab;font-size:12px;font-weight:700}}{ST_CLOSE}'
        f'<div class="wrap"><div class="col" id="L"><b>LEFT</b>{l_items}</div><div class="col" id="R"><b>RIGHT</b>{r_items}</div></div>'
        f'<div id="out" style="margin-top:6px;font-family:monospace;font-size:11px;color:{th["accent"]};"></div>'
        f'{SC_OPEN}let drag=null;document.querySelectorAll(".d-item").forEach(el=>{{el.ondragstart=()=>drag=el;}});document.querySelectorAll(".col").forEach(c=>{{c.ondragover=e=>e.preventDefault();c.ondrop=()=>{{if(drag)c.appendChild(drag);document.getElementById("out").innerText="LEFT: "+[...document.querySelectorAll("#L .d-item")].map(x=>x.dataset.b).join(", ")+" | RIGHT: "+[...document.querySelectorAll("#R .d-item")].map(x=>x.dataset.b).join(", ");}};}});{SC_CLOSE}'
    )
    components.html(board_html, height=215)
    all_b = ["Profile Card", "Photo Albums", "Top 8 Friends", "Profile Anthem", "Profile Wall", "Main Social Hub"]
    cur_l = [b for b in left_blks if b in all_b]
    cur_r = [b for b in right_blks if b in all_b and b not in cur_l]
    pick_l = st.multiselect("Left Column Blocks", all_b, default=cur_l, key="ms_left")
    avail_r = [b for b in all_b if b not in pick_l]
    pick_r = st.multiselect("Right Column Blocks", avail_r, default=[b for b in cur_r if b in avail_r] or avail_r, key="ms_right")
    if st.button("Save & Move Blocks ✦", key="save_blk_btn"):
        st.session_state.lex_theme["left_blocks"] = pick_l
        st.session_state.lex_theme["right_blocks"] = pick_r + [b for b in avail_r if b not in pick_r]
        save_profile_to_cloud()
        st.rerun()

    st.markdown("#### 🎨 LeX Studio Visuals, Glow, Opacity & 20 Wall Arts")
    new_av = st.file_uploader("Update Profile Picture (Max 5MB)", type=["png", "jpg", "jpeg", "webp"], key="upd_av")
    if new_av is not None and st.button("Save Profile Picture"):
        ok_av, msg_av = validate_and_scan_media(new_av)
        if not ok_av:
            st.error(f"🛡️ Media Safety Filter: {msg_av}")
        else:
            user["avatar"] = encode_image_data_url(new_av)
            save_profile_to_cloud()
            st.rerun()
    wall_up = st.file_uploader("Upload Custom Wallpaper (Max 5MB)", type=["png", "jpg", "jpeg", "webp"], key="upd_wall")
    wc1, wc2 = st.columns(2)
    if wall_up is not None and wc1.button("Set Wallpaper 🖼"):
        ok_wl, msg_wl = validate_and_scan_media(wall_up)
        if not ok_wl:
            st.error(f"🛡️ Media Safety Filter: {msg_wl}")
        else:
            st.session_state.lex_theme["custom_wall"] = encode_image_data_url(wall_up)
            save_profile_to_cloud()
            st.rerun()
    if st.session_state.lex_theme.get("custom_wall") and wc2.button("Clear Wallpaper"):
        st.session_state.lex_theme["custom_wall"] = ""
        save_profile_to_cloud()
        st.rerun()

    c_a, c_b, c_c = st.columns(3)
    new_bg = c_a.color_picker("Background", th["bg"])
    new_card = c_b.color_picker("Card Surface", th["card"])
    new_acc = c_c.color_picker("Accent & Glow", th["accent"])
    s1, s2 = st.columns(2)
    new_op = s1.slider("Card Opacity %", 40, 100, int(th.get("card_opacity", 92)))
    new_rad = s2.slider("Corner Roundness (px)", 0, 24, int(th.get("card_radius", 12)))
    glow_on = st.toggle("✨ Neon Glowing Borders", value=th.get("glow_borders", True))
    mq_on = st.toggle("📢 Scrolling Marquee Ticker", value=th.get("marquee_on", True))
    mq_txt = st.text_input("Marquee Ticker Text", value=th.get("marquee_text", ""))
    font_keys = list(FONT_MAP.keys())
    new_font = st.selectbox("Profile Font", font_keys, index=font_keys.index(th["font"]) if th.get("font") in font_keys else 0)
    new_backdrop = st.selectbox("Wall Background Art (20 Crisp Vectors)", BACKDROP_OPTIONS, index=BACKDROP_OPTIONS.index(th["backdrop"]) if th.get("backdrop") in BACKDROP_OPTIONS else 0)
    new_spray = st.text_input("Custom Spray-Paint / Tag Word", value=th.get("spray_word", "LeX!"))
    borders = ["solid", "dashed", "double"]
    new_border = st.selectbox("Border Style", borders, index=borders.index(th["border_style"]) if th.get("border_style") in borders else 0)
    raw_css = st.text_area("Advanced Custom CSS (LeX Override)", value=th.get("custom_css", ""), height=68)
    if st.button("Apply Custom Look ✦"):
        ok_mq, msg_mq = check_text_and_links(f"{mq_txt} {new_spray}")
        if not ok_mq:
            st.error(f"🛡️ Safety Filter: {msg_mq}")
        else:
            st.session_state.lex_theme.update({"bg": new_bg, "card": new_card, "accent": new_acc, "card_opacity": new_op, "card_radius": new_rad, "glow_borders": glow_on, "marquee_on": mq_on, "marquee_text": mq_txt, "font": new_font, "backdrop": new_backdrop, "spray_word": new_spray, "border_style": new_border, "custom_css": sanitize_custom_css(raw_css), "custom_wall": ""})
            save_profile_to_cloud()
            st.rerun()

    st.markdown("#### 📝 Profile Bio, Pinned Bulletin & Classic Interests")
    pin_in = st.text_input("Pinned Bulletin (Top of Profile)", value=th.get("pinned_note", ""))
    new_site = st.text_input("Profile Website / Portfolio Link", value=user.get("website", ""))
    new_mood = st.text_input("Mood Badge", value=user["mood"])
    new_bio = st.text_area("About Me", value=user["bio"])
    new_meet = st.text_input("Who I'd Like to Meet", value=user.get("who_to_meet", ""))
    ig1, ig2 = st.columns(2)
    i_gen = ig1.text_input("General Interests", value=th.get("int_general", ""))
    i_mus = ig2.text_input("Favorite Music", value=th.get("int_music", ""))
    i_mov = ig1.text_input("Favorite Movies", value=th.get("int_movies", ""))
    i_tv = ig2.text_input("Favorite TV Shows", value=th.get("int_tv", ""))
    i_bk = st.text_input("Books & Heroes", value=th.get("int_books", ""))
    if st.button("Save All Profile Details ✦"):
        all_prof_txt = f"{pin_in} {new_mood} {new_bio} {new_meet} {i_gen} {i_mus} {i_mov} {i_tv} {i_bk}"
        ok_pr, msg_pr = check_text_and_links(all_prof_txt, new_site)
        if not ok_pr:
            st.error(f"🛡️ Safety Filter: {msg_pr}")
        else:
            user["website"] = normalize_url(new_site)
            user["mood"] = new_mood.strip()
            user["bio"] = new_bio.strip()
            user["who_to_meet"] = new_meet.strip()
            st.session_state.lex_theme.update({"pinned_note": pin_in.strip(), "int_general": i_gen.strip(), "int_music": i_mus.strip(), "int_movies": i_mov.strip(), "int_tv": i_tv.strip(), "int_books": i_bk.strip()})
            save_profile_to_cloud()
            st.rerun()

    st.markdown("#### 🛡️ Privacy & Blocked Users Manager")
    blocked_list = list(st.session_state.lex_theme.get("blocked_users") or [])
    if not blocked_list:
        st.caption("No blocked users. You can block any user from their profile, feed post, or DMs.")
    else:
        for b_idx, b_handle in enumerate(blocked_list):
            bc1, bc2 = st.columns([0.7, 0.3])
            bc1.markdown(f"🚫 **{b_handle}**")
            if bc2.button("Unblock", key=f"unblk_st_{b_idx}"):
                toggle_block_user(b_handle)
                st.rerun()

with t_radar:
    st.markdown("#### 📡 Inner Circle Radar")
    blocked_rad = get_blocked_set()
    for friend in [f for f in st.session_state.lex_top8 if f["handle"].lower() not in blocked_rad]:
        st.markdown(friend_card_html(friend, f"#{friend['rank']}"), unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only. Protected by LeX Safety Engine.")
