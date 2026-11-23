import os
import json
import base64
import urllib.parse
from datetime import date
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client
from audio_engine import ANTHEM_TRACKS, generate_anthem_wav
import time
st.set_page_config(page_title="LeX // Social by LexiTech Studio", page_icon="✦", layout="wide")
ST_OPEN = "<" + "style>"
ST_CLOSE = "<" + "/style>"
st.markdown(
    f"{ST_OPEN}@media (max-width: 768px) {{"
    + ".block-container { padding-left: 0.65rem !important; padding-right: 0.65rem !important; padding-top: 1.2rem !important; max-width: 100vw !important; overflow-x: hidden !important; }"
    + ".lex-card { padding: 12px !important; margin-bottom: 10px !important; }"
    + ".lex-card h2 { font-size: 1.25rem !important; }"
    + "div[data-testid='stHorizontalBlock'] { flex-wrap: wrap !important; gap: 0.4rem !important; }"
    + "div[data-testid='stHorizontalBlock'] > div[data-testid='column'] { min-width: 46% !important; flex: 1 1 46% !important; }"
    + ".stTabs [data-baseweb='tab-list'] { flex-wrap: wrap !important; gap: 4px !important; }"
    + ".stTabs [data-baseweb='tab'] { font-size: 12px !important; padding: 6px 10px !important; }"
    + f"}}{ST_CLOSE}",
    unsafe_allow_html=True,
)

LK_OPEN = "<" + "link "
SV_OPEN = "<" + "svg "
SV_CLOSE = "<" + "/svg>"
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
    "bestiality", "necrophilia"
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
    return "".join(c for c in s if c.isalnum() or c in ("_", "."))[:24]

def is_handle_taken(sb_client, raw_handle: str, exclude_uid: str = "") -> bool:
    ch = clean_handle_str(raw_handle)
    if not ch or not sb_client:
        return True
    rows = sb_client.table("lex_profiles").select("user_id, handle").ilike("handle", f"@{ch}").execute().data or []
    for row in rows:
        if exclude_uid and str(row.get("user_id", "")) == str(exclude_uid):
            continue
        return True
    return False
def check_safety_and_dress_code(text_val: str, extra_name: str = ""):
    blob = " ".join(f"{text_val or ''} {extra_name or ''}".lower().split())
    for term in SEVERE_BLOCKED_TERMS | NSFW_DRESS_CODE_TERMS:
        if term in blob:
            return False, "Blocked by LeX Safety & Dress Code Shield: nudity, adult links, and severe violence are prohibited."
    return True, ""

def scan_image_safely(uploaded_file, caption_text: str = ""):
    if uploaded_file is None:
        return True, ""
    fname = getattr(uploaded_file, "name", "")
    if not str(getattr(uploaded_file, "type", "")).startswith("image/"):
        return False, "Only valid image files are allowed."
    ok_txt, msg_txt = check_safety_and_dress_code(caption_text, fname)
    if not ok_txt:
        return False, msg_txt
    api_u = st.secrets.get("SIGHTENGINE_USER", "")
    api_s = st.secrets.get("SIGHTENGINE_SECRET", "")
    if api_u and api_s:
        try:
            se_ep = "https://" + ".".join(["api", "sightengine", "com"]) + "/1.0/check.json"
            r = requests.post(se_ep, files={"media": (fname, uploaded_file.getvalue())}, data={"models": "nudity-2.1,gore-2.0", "api_user": api_u, "api_secret": api_s}, timeout=12)
            jd = r.json() if r.status_code == 200 else {}
            nud, gor = jd.get("nudity") or {}, jd.get("gore") or {}
            scores = [nud.get("sexual_activity", 0), nud.get("sexual_display", 0), nud.get("erotica", 0), nud.get("very_suggestive", 0), nud.get("mildly_suggestive", 0), gor.get("prob", 0)]
            if any(float(sc or 0) > 0.25 for sc in scores):
                return False, "Upload rejected: Everyone on LeX must be fully dressed."
        except Exception:
            pass
    return True, ""

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

CURSOR_OPTIONS = {
    "Default System Pointer": "auto",
    "Crosshair Precision": "crosshair",
    "Pointer Hand": "pointer",
    "Cell Grid": "cell",
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

LIVE_BANNERS = [
    "None", "Falling Shooting Stars", "Rising Cyber Flames", "Orbiting Planets & Space",
    "Neon Cyberpunk Rain", "Live Glowing Waterfall", "Electric Lightning Storm",
    "Floating Cyber Hearts", "Live Audio Equalizer",
]

CARD_ANIMATIONS = ["None (Static)", "Pulse Neon Glow", "Floating Levitate", "Cyber Glitch Flicker"]
AVATAR_SHAPES = {
    "Classic Circle": ("50%", "none"),
    "Rounded Studio Square": ("18px", "none"),
    "Sharp Edge Square": ("0px", "none"),
    "Apple Squircle": ("28%", "none"),
    "Vertical Pill Capsule": ("999px", "inset(0 12% 0 12% round 999px)"),
    "Cyber Cut-Corner": ("0px", "polygon(18% 0%, 82% 0%, 100% 18%, 100% 82%, 82% 100%, 18% 100%, 0% 82%, 0% 18%)"),
    "Hexagon": ("0px", "polygon(50% 0%, 95% 25%, 95% 75%, 50% 100%, 5% 75%, 5% 25%)"),
    "Octagon": ("0px", "polygon(30% 0%, 70% 0%, 100% 30%, 100% 70%, 70% 100%, 30% 100%, 0% 70%, 0% 30%)"),
    "Diamond": ("0px", "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)"),
    "5-Point Star": ("0px", "polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%)"),
    "12-Point Starburst": ("0px", "polygon(50% 0%, 60% 18%, 80% 10%, 78% 32%, 98% 38%, 84% 54%, 96% 74%, 75% 76%, 76% 96%, 56% 85%, 44% 98%, 35% 79%, 14% 86%, 22% 66%, 4% 55%, 20% 42%, 12% 22%, 34% 25%, 40% 4%)"),
    "Y2K Heart": ("0px", "polygon(50% 92%, 10% 52%, 4% 32%, 16% 14%, 34% 12%, 50% 28%, 66% 12%, 84% 14%, 96% 32%, 90% 52%)"),
    "Gothic Shield": ("0px", "polygon(12% 0%, 88% 0%, 96% 45%, 50% 100%, 4% 45%)"),
    "Cathedral Arch": ("50% 50% 8px 8px", "none"),
    "Pentagon": ("0px", "polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)"),
    "4-Leaf Clover": ("38%", "none"),
}
ALL_PROFILE_MODULES = [
    "Profile Card", "Vibe Sticker", "Profile Song / Playlist",
    "Photo Albums", "Guestbook Wall", "Pinned Bulletin", "Top 8", "Social Hub"
]

DEFAULT_THEME = {
    "bg": "#06060A", "card": "#0E0E16", "accent": "#FFFFFF", "text": "#F4F4F5",
    "font": "Clean Studio Sans", "backdrop": "Y2K Stars & Sparkles", "spray_word": "LeX!",
    "border_style": "solid", "card_radius": 14, "card_opacity": 94,
    "glow_borders": True, "text_glow": True, "cursor_style": "Default System Pointer",
    "card_anim": "None (Static)", "avatar_shape": "Classic Circle",
    "banner_live": "None", "banner_img": "", "custom_wall": "", "custom_css": "",
    "marquee_on": False, "marquee_text": "✦ WELCOME TO MY LEX PROFILE ✦",
    "pinned_note": "", "vibe_sticker": "", "yt_playlist": [],
    "int_general": "", "int_music": "", "int_movies": "", "int_tv": "", "int_books": "",
    "albums": [], "following": [], "followers": [],
    "incoming_requests": [], "sent_requests": [], "blocked_users": [], "reports_log": [],
    "left_blocks": ["Profile Card", "Vibe Sticker", "Profile Song / Playlist", "Photo Albums", "Guestbook Wall"],
    "right_blocks": ["Pinned Bulletin", "Top 8", "Social Hub"],
    "notif_read_id": 0,
}
def founder_badge_html(handle: str) -> str:
    if (handle or "").strip().lower() in {"@heidi", "@heidiseckman"}:
        return '<span style="background:linear-gradient(90deg,#F59E0B,#EC4899);color:#000;padding:2px 8px;border-radius:99px;font-size:10px;font-weight:900;margin-left:6px;">👑 CREATOR & FOUNDER</span>'
    return ""

def founder_studio_link_html(handle: str, accent: str) -> str:
    if (handle or "").strip().lower() in {"@heidi", "@heidiseckman"}:
        return f'<div style="margin-top:6px;"><a href="{LEXITECH_HUB_URL}" target="_blank" style="display:inline-block;padding:3px 10px;border-radius:99px;background:{accent}22;border:1px solid {accent};color:{accent};font-size:11px;font-weight:800;text-decoration:none;">✦ LexiTech Studio ↗</a></div>'
    return ""
def build_profile_link_html(raw_url: str, raw_label: str, accent: str) -> str:
    clean = normalize_url(raw_url)
    if not clean:
        return ""
    lbl = (raw_label or "").strip() or "My Website ↗"
    safe_u = clean.replace('"', "&quot;").replace("<", "").replace(">", "")
    safe_l = lbl.replace("<", "&lt;").replace(">", "&gt;")
    return f'<div style="margin-top:6px;"><a href="{safe_u}" target="_blank" rel="noopener noreferrer" style="display:inline-block;padding:3px 11px;border-radius:99px;background:{accent}22;border:1px solid {accent};color:{accent};font-size:11px;font-weight:800;text-decoration:none;">🔗 {safe_l} ↗</a></div>'

def earned_badges_html(t_cfg: dict, friends_cnt: int, top8_cnt: int, handle_str: str) -> str:
    badges = []
    h_low = (handle_str or "").strip().lower()
    if h_low in {"@heidi", "@heidiseckman"} or int(t_cfg.get("is_og", 0)) == 1 or len(t_cfg.get("followers") or []) >= 1:
        badges.append(("✨ OG EARLY ADOPTER", "#38BDF8,#818CF8"))
    if len((t_cfg.get("custom_css") or "").strip()) >= 25:
        badges.append(("🎨 CSS ARCHITECT", "#EC4899,#A855F7"))
    if friends_cnt >= 8 or top8_cnt >= 8:
        badges.append(("👑 TOP 8 ROYALTY", "#F59E0B,#FDE047"))
    last_ts = int(float(t_cfg.get("last_seen") or 0))
    if last_ts > 0 and ((last_ts // 3600) % 24) in {0, 1, 2, 3, 4, 5, 6, 7}:
        badges.append(("🦉 NIGHT OWL", "#6366F1,#14B8A6"))
    if not badges:
        return ""
    pills = "".join([f'<span style="display:inline-block;margin:4px 6px 0 0;padding:2px 9px;border-radius:99px;background:linear-gradient(90deg,{grad});color:#05050A;font-size:10px;font-weight:900;letter-spacing:0.5px;box-shadow:0 0 10px rgba(255,255,255,0.35);">{lbl}</span>' for lbl, grad in badges])
    return f'<div style="margin-top:6px;">{pills}</div>'
    def build_profile_link_html(raw_url: str, raw_label: str, accent: str) -> str:
        clean = normalize_url(raw_url)
    if not clean:
        return ""
    lbl = (raw_label or "").strip() or "My Website ↗"
    safe_u = clean.replace('"', "&quot;").replace("<", "").replace(">", "")
    safe_l = lbl.replace("<", "&lt;").replace(">", "&gt;")
    return f'<div style="margin-top:6px;"><a href="{safe_u}" target="_blank" rel="noopener noreferrer" style="display:inline-block;padding:3px 11px;border-radius:99px;background:{accent}22;border:1px solid {accent};color:{accent};font-size:11px;font-weight:800;text-decoration:none;">🔗 {safe_l} ↗</a></div>'

def earned_badges_html(t_cfg: dict, friends_cnt: int, top8_cnt: int, handle_str: str) -> str:
    badges = []
    h_low = (handle_str or "").strip().lower()
    if h_low in {"@heidi", "@heidiseckman"} or int(t_cfg.get("is_og", 0)) == 1 or len(t_cfg.get("followers") or []) >= 1:
        badges.append(("✨ OG EARLY ADOPTER", "#38BDF8,#818CF8"))
    if len((t_cfg.get("custom_css") or "").strip()) >= 25:
        badges.append(("🎨 CSS ARCHITECT", "#EC4899,#A855F7"))
    if friends_cnt >= 8 or top8_cnt >= 8:
        badges.append(("👑 TOP 8 ROYALTY", "#F59E0B,#FDE047"))
    last_ts = int(float(t_cfg.get("last_seen") or 0))
    if last_ts > 0 and ((last_ts // 3600) % 24) in {0, 1, 2, 3, 4, 5, 6, 7}:
        badges.append(("🦉 NIGHT OWL", "#6366F1,#14B8A6"))
    if not badges:
        return ""
    pills = "".join([f'<span style="display:inline-block;margin:4px 6px 0 0;padding:2px 9px;border-radius:99px;background:linear-gradient(90deg,{grad});color:#05050A;font-size:10px;font-weight:900;letter-spacing:0.5px;box-shadow:0 0 10px rgba(255,255,255,0.35);">{lbl}</span>' for lbl, grad in badges])
    return f'<div style="margin-top:6px;">{pills}</div>'
def build_backdrop_url(style_name: str, accent: str, spray_word: str = "LeX!") -> str:
    w = (spray_word or "LeX!").replace("<", "").replace(">", "")[:14]
    if style_name == "Architectural Grid":
        raw = f'{SV_OPEN}xmlns="{SVG_NS}" width="56" height="56"><path d="M56 0H0V56" fill="none" stroke="{accent}" stroke-opacity="0.18" stroke-width="1"/>{SV_CLOSE}'
        return f'url("data:image/svg+xml,{urllib.parse.quote(raw)}")'
    art_map = {
        "Punk Spray-Paint Graffiti": f'<text x="16" y="88" font-family="cursive" font-size="46" font-weight="900" fill="{accent}" fill-opacity="0.30" transform="rotate(-11 70 80)">{w}</text><path d="M20 145 Q110 120 230 155" stroke="{accent}" stroke-width="3" stroke-opacity="0.32" fill="none" stroke-dasharray="12 6"/>',
        "Y2K Stars & Sparkles": f'<polygon points="55,18 64,44 92,44 69,60 78,86 55,70 32,86 41,60 18,44 46,44" fill="none" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.36"/><path d="M185,115 L193,140 L218,148 L193,156 L185,181 L177,156 L152,148 Z" fill="{accent}" fill-opacity="0.28"/>',
        "Leopard Rosette Print": f'<circle cx="57" cy="54" r="20" fill="{accent}" fill-opacity="0.22" stroke="#FFF" stroke-opacity="0.26" stroke-width="4" stroke-dasharray="14 6"/><circle cx="177" cy="157" r="22" fill="{accent}" fill-opacity="0.24" stroke="#FFF" stroke-opacity="0.26" stroke-width="4" stroke-dasharray="16 6"/>',
        "Cherry Hearts & Kisses": f'<path d="M60,78 C60,78 26,54 26,35 C26,22 38,16 48,24 C54,28 60,36 60,36 C60,36 66,28 72,24 C82,16 94,22 94,35 C94,54 60,78 60,78 Z" fill="none" stroke="{accent}" stroke-width="2.5" stroke-opacity="0.38"/>',
        "Coquette Ribbon Bows": f'<path d="M65,55 L32,35 L38,75 Z M65,55 L98,35 L92,75 Z" fill="{accent}" fill-opacity="0.25" stroke="{accent}" stroke-width="2.2"/><circle cx="65" cy="55" r="6" fill="#FFF" fill-opacity="0.4"/>',
        "Butterfly Dreamscape": f'<path d="M65,60 C35,20 15,55 48,72 C22,85 42,110 65,80 C88,110 108,85 82,72 C115,55 95,20 65,60 Z" fill="{accent}" fill-opacity="0.24" stroke="{accent}" stroke-width="2"/>',
        "Checkered Ska / Vans": f'<rect x="0" y="0" width="65" height="55" fill="{accent}" fill-opacity="0.16"/><rect x="65" y="55" width="65" height="55" fill="{accent}" fill-opacity="0.16"/>',
        "Skull & Crossbones Punk": f'<circle cx="65" cy="52" r="22" fill="none" stroke="#FFF" stroke-width="2.2" stroke-opacity="0.28"/><circle cx="57" cy="50" r="4" fill="{accent}"/><circle cx="73" cy="50" r="4" fill="{accent}"/>',
        "Lightning Bolts & Voltage": f'<polygon points="72,18 38,72 64,72 50,122 96,62 68,62" fill="{accent}" fill-opacity="0.26" stroke="{accent}" stroke-width="2"/>',
        "Gothic Bats & Moons": f'<path d="M175,35 A28,28 0 1,0 205,75 A22,22 0 1,1 175,35 Z" fill="{accent}" fill-opacity="0.30"/>',
    }
    art_map.update({
        "Cyber Matrix Rain": f'<text x="18" y="45" font-family="monospace" font-size="16" font-weight="700" fill="{accent}" fill-opacity="0.36">010110 // {w}</text>',
        "Carbon Fiber Hex": f'<polygon points="60,18 96,38 96,78 60,98 24,78 24,38" fill="none" stroke="{accent}" stroke-opacity="0.34" stroke-width="2.2"/>',
        "Retro Cassette & Vinyl": f'<rect x="24" y="28" width="88" height="54" rx="6" fill="none" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.38"/><circle cx="180" cy="160" r="36" fill="none" stroke="{accent}" stroke-width="2"/>',
        "Flame & Hotrod Stripes": f'<path d="M55,105 C32,85 38,55 58,32 C55,52 68,56 72,42 C88,65 82,92 55,105 Z" fill="{accent}" fill-opacity="0.30" stroke="{accent}" stroke-width="2"/>',
        "Crown & Diamond Luxe": f'<polygon points="28,78 28,38 48,56 65,30 82,56 102,38 102,78" fill="none" stroke="{accent}" stroke-width="2.4" stroke-opacity="0.42"/>',
        "Rose Thorns & Petals": f'<circle cx="65" cy="55" r="22" fill="none" stroke="{accent}" stroke-width="2.5"/><line x1="65" y1="77" x2="65" y2="122" stroke="{accent}" stroke-width="2.4"/>',
        "8-Bit Arcade Invaders": f'<path d="M40,40 h10 v10 h20 v-10 h10 v20 h10 v20 h-10 v-10 h-40 v10 h-10 v-20 h10 z" fill="{accent}" fill-opacity="0.30"/>',
        "Tactical Urban Camo": f'<polygon points="18,28 68,18 92,46 64,74 22,62" fill="{accent}" fill-opacity="0.22"/>',
        "Cosmic Planets & Rings": f'<circle cx="68" cy="62" r="22" fill="{accent}" fill-opacity="0.26" stroke="{accent}" stroke-width="2"/><ellipse cx="68" cy="62" rx="44" ry="11" transform="rotate(-22 68 62)" fill="none" stroke="#FFF" stroke-width="2.2" stroke-opacity="0.34"/>',
    })
    body = art_map.get(style_name, art_map["Y2K Stars & Sparkles"])
    raw_svg = f'{SV_OPEN}xmlns="{SVG_NS}" width="260" height="220">{body}{SV_CLOSE}'
    return f'url("data:image/svg+xml,{urllib.parse.quote(raw_svg)}")'
def build_live_banner_html(mode: str, custom_img: str, accent: str, rad_px: int) -> str:
    if custom_img:
        return f'<div style="width:100%;height:155px;border-radius:{rad_px}px;overflow:hidden;margin-bottom:12px;border:1.5px solid {accent};box-shadow:0 0 16px {accent}55;"><img src="{custom_img}" style="width:100%;height:100%;object-fit:cover;" /></div>'
    if not mode or mode == "None":
        return ""
    kf = "@keyframes lexFall{0%{transform:translate(0,-30px);opacity:1}100%{transform:translate(-140px,170px);opacity:0}}@keyframes lexRise{0%,100%{transform:translateY(0) scaleY(1)}50%{transform:translateY(-14px) scaleY(1.18)}}@keyframes lexOrbit{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}@keyframes lexRain{0%{transform:translateY(-140px)}100%{transform:translateY(160px)}}@keyframes lexPulse{0%,100%{opacity:.25}50%{opacity:1}}"
    if mode == "Falling Shooting Stars":
        inner = f'<circle cx="15%" cy="25%" r="2" fill="#fff" style="animation:lexPulse 1.5s infinite"/><line x1="85%" y1="10" x2="72%" y2="45" stroke="{accent}" stroke-width="3" style="animation:lexFall 1.8s linear infinite"/>'
    elif mode == "Rising Cyber Flames":
        inner = f'<path d="M0,140 Q60,70 120,130 T240,120 T360,135 T480,115 T600,130 T720,120 T840,140 L840,150 L0,150 Z" fill="{accent}" fill-opacity="0.55" style="animation:lexRise 1.4s ease-in-out infinite"/>'
    elif mode == "Orbiting Planets & Space":
        inner = f'<circle cx="50%" cy="72" r="24" fill="{accent}" fill-opacity="0.45" stroke="{accent}" stroke-width="2"/><g style="transform-origin:50% 72px;animation:lexOrbit 5s linear infinite"><circle cx="50%" cy="22" r="7" fill="#fff"/></g>'
    elif mode == "Neon Cyberpunk Rain":
        inner = "".join([f'<line x1="{x}%" y1="0" x2="{x-4}%" y2="45" stroke="{accent}" stroke-width="2" style="animation:lexRain 0.9s linear infinite"/>' for x in range(8, 96, 10)])
    elif mode == "Live Glowing Waterfall":
        inner = "".join([f'<rect x="{x}%" y="0" width="6%" height="145" fill="{accent}" fill-opacity="0.32" style="animation:lexRain 1.1s linear infinite"/>' for x in range(28, 72, 9)])
    elif mode == "Electric Lightning Storm":
        inner = f'<polyline points="220,0 195,55 230,55 185,140" fill="none" stroke="{accent}" stroke-width="4" style="animation:lexPulse 0.9s infinite"/>'
    elif mode == "Floating Cyber Hearts":
        inner = "".join([f'<text x="{x}%" y="120" font-size="24" fill="{accent}" style="animation:lexRise 1.8s ease-in-out infinite">♥</text>' for x in range(14, 90, 18)])
    else:
        inner = "".join([f'<rect x="{x}%" y="45" width="4%" height="95" rx="4" fill="{accent}" style="transform-origin:bottom;animation:lexRise 0.7s ease-in-out infinite"/>' for x in range(10, 92, 8)])
    return f'{ST_OPEN}{kf}{ST_CLOSE}<div style="width:100%;height:135px;border-radius:{rad_px}px;overflow:hidden;margin-bottom:12px;background:radial-gradient(circle at 50% 40%, {accent}22, #050508 85%);border:1.5px solid {accent};">{SV_OPEN}xmlns="{SVG_NS}" width="100%" height="135">{inner}{SV_CLOSE}</div>'
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

def normalize_gif_url(raw_url: str) -> str:
    clean = normalize_url(raw_url)
    if not clean:
        return ""
    if "://giphy.com" in clean and not clean.lower().endswith(".gif"):
        slug = clean.rstrip("/").split("/")[-1]
        gif_id = slug.split("-")[-1]
        if gif_id:
            return "https://" + ".".join(["media", "giphy", "com"]) + f"/media/{gif_id}/giphy.gif"
    return clean
def extract_yt_id(raw: str) -> str:
    s = (raw or "").strip()
    if len(s) == 11 and "/" not in s and "." not in s:
        return s
    for sep in ["youtu.be/", "v=", "/embed/"]:
        if sep in s:
            _, _, tail = s.partition(sep)
            head, _, _ = tail.partition("?")
            head, _, _ = head.partition("&")
            return head.strip("/")[:11]
    return ""

def render_avatar_html(avatar_url: str, display_name: str, t_cfg: dict, size_px: int = 80) -> str:
    acc = t_cfg.get("accent", "#EC4899")
    rad, clip = AVATAR_SHAPES.get(t_cfg.get("avatar_shape", "Classic Circle"), ("50%", "none"))
    clip_css = f"clip-path:{clip};-webkit-clip-path:{clip};" if clip != "none" else ""
    wrap_st = f"width:{size_px}px;height:{size_px}px;padding:3px;background:{acc};border-radius:{rad};{clip_css}box-shadow:0 0 16px {acc};display:flex;align-items:center;justify-content:center;flex-shrink:0;"
    if avatar_url:
        return f'<div style="{wrap_st}"><img src="{avatar_url}" style="width:100%;height:100%;object-fit:cover;border-radius:{rad};{clip_css}" /></div>'
    ini = ((display_name or "L")[:1] or "L").upper()
    return f'<div style="{wrap_st}"><div style="width:100%;height:100%;background:#09090d;color:{acc};font-weight:900;font-size:{int(size_px*0.38)}px;border-radius:{rad};{clip_css}display:flex;align-items:center;justify-content:center;">{ini}</div></div>'
def is_member_online(theme_data: dict) -> bool:
    try:
        last_ts = int(float((theme_data or {}).get("last_seen") or 0))
    except Exception:
        last_ts = 0
    if last_ts <= 0:
        return False
    return 0 <= (int(time.time()) - last_ts) < 180

def ping_member_heartbeat():
    u = st.session_state.get("lex_user")
    if not u or not u.get("user_id"):
        return
    now_ts = int(time.time())
    if now_ts - int(st.session_state.get("_lex_hb_ts", 0)) < 90:
        return
    st.session_state["_lex_hb_ts"] = now_ts
    st.session_state.lex_theme["last_seen"] = now_ts
    sb = get_sb()
    if sb:
        try:
            th_copy = st.session_state.lex_theme.copy()
            th_copy["last_seen"] = now_ts
            sb.table("lex_profiles").update({"theme_json": th_copy}).eq("user_id", u["user_id"]).execute()
        except Exception:
            pass

def parse_post_blob(raw_body: str, fallback_likes: int = 0):
    txt = raw_body or ""
    meta = {"rx": {"🔥": {}, "💖": {}, "🎸": {}, "💀": {}}, "comments": []}
    if "[LEX_META]" in txt:
        txt, _, m_str = txt.partition("[LEX_META]")
        try:
            loaded = json.loads(m_str.strip())
            if isinstance(loaded, dict):
                meta.update(loaded)
        except Exception:
            pass
    img_src, lnk_src = "", ""
    if "[LEX_IMG]" in txt:
        txt, _, img_src = txt.partition("[LEX_IMG]")
    if "[LEX_LINK]" in txt:
        txt, _, lnk_src = txt.partition("[LEX_LINK]")
    rx_map = meta.get("rx") or {}
    for emo in ("🔥", "💖", "🎸", "💀"):
        if not isinstance(rx_map.get(emo), dict):
            rx_map[emo] = {}
    if fallback_likes and not rx_map.get("🔥"):
        rx_map["🔥"]["@legacy"] = int(fallback_likes)
    meta["rx"] = rx_map
    if not isinstance(meta.get("comments"), list):
        meta["comments"] = []
    return txt.strip(), lnk_src.strip(), img_src.strip(), meta
def pack_post_blob(clean_txt: str, lnk_src: str, img_src: str, meta: dict) -> str:
    out = (clean_txt or "").strip()
    if lnk_src:
        out += f"\n[LEX_LINK]{lnk_src}"
    if img_src:
        out += f"\n[LEX_IMG]{img_src}"
    out += f"\n[LEX_META]{json.dumps(meta, separators=(',', ':'))}"
    return out

def push_activity_notif(target_handle: str, actor_handle: str, kind: str, detail: str, post_id):
    if not sb or not target_handle or target_handle.lower() == actor_handle.lower():
        return
    try:
        sb.table("lex_messages").insert({
            "sender_handle": actor_handle,
            "recipient_handle": target_handle,
            "body": f"[LEX_NOTIF]{kind}|{post_id}|{(detail or '')[:90]}"
        }).execute()
    except Exception:
        pass
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
        theme_payload["last_seen"] = int(time.time())
        payload = {
            "handle": u["handle"], "display_name": u["name"],
            "bio": u.get("bio", ""), "who_to_meet": u.get("who_to_meet", ""),
            "mood": u.get("mood", "Online Now • Vibing ⚡"), "anthem": u.get("anthem", "Y2K Cobalt Synth"),
            "custom_song_url": u.get("custom_song_url", ""), "custom_song_title": u.get("custom_song_title", ""),
            "theme_json": theme_payload, "top8_json": st.session_state.lex_top8, "wall_json": st.session_state.lex_wall,
        }
        exists = sb.table("lex_profiles").select("user_id").eq("user_id", u["user_id"]).execute().data
        if exists:
            sb.table("lex_profiles").update(payload).eq("user_id", u["user_id"]).execute()
        else:
            payload["user_id"] = u["user_id"]
            sb.table("lex_profiles").insert(payload).execute()
    except Exception as e:
        st.warning(f"Cloud sync notice: {e}")
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
        st.session_state.lex_friends = [f for f in st.session_state.lex_friends if isinstance(f, dict) and f.get("handle", "").lower() != tgt.lower()]
        st.session_state.lex_top8 = [t for t in st.session_state.lex_top8 if isinstance(t, dict) and t.get("handle", "").lower() != tgt.lower()]
        for r_i, item in enumerate(st.session_state.lex_top8):
            item["rank"] = r_i + 1
        th_ref["following"] = [x for x in (th_ref.get("following") or []) if str(x).lower() != tgt.lower()]
        th_ref["incoming_requests"] = [x for x in (th_ref.get("incoming_requests") or []) if isinstance(x, dict) and x.get("handle", "").lower() != tgt.lower()]
        th_ref["sent_requests"] = [x for x in (th_ref.get("sent_requests") or []) if str(x).lower() != tgt.lower()]
    elif mode == "report":
        reps = list(th_ref.get("reports_log") or [])
        reps.append({"target": tgt, "reason": (reason or "Reported by member")[:240], "date": str(date.today())})
        th_ref["reports_log"] = reps
    save_profile_to_cloud()
def send_friend_request(target_handle: str):
    sb = get_sb()
    u = st.session_state.get("lex_user")
    if not sb or not u:
        return False
    tgt = "@" + clean_handle_str(target_handle)
    sb.table("lex_messages").insert({
        "sender_handle": u["handle"], "recipient_handle": tgt,
        "body": f"[LEX_FREQ]{u['name']}|{u.get('mood', 'Online ⚡')}|{u.get('anthem', 'Y2K Cobalt Synth')}"
    }).execute()
    sent = list(st.session_state.lex_theme.get("sent_requests") or [])
    if tgt.lower() not in {str(x).lower() for x in sent}:
        sent.append(tgt)
        st.session_state.lex_theme["sent_requests"] = sent
        save_profile_to_cloud()
    return True

def cancel_friend_request(target_handle: str):
    sb = get_sb()
    u = st.session_state.get("lex_user")
    tgt = "@" + clean_handle_str(target_handle)
    st.session_state.lex_theme["sent_requests"] = [x for x in (st.session_state.lex_theme.get("sent_requests") or []) if str(x).lower() != tgt.lower()]
    save_profile_to_cloud()
    if sb and u:
        sb.table("lex_messages").insert({"sender_handle": u["handle"], "recipient_handle": tgt, "body": "[LEX_FCAN]"}).execute()
def accept_friend_request(req_obj):
    sb = get_sb()
    u = st.session_state.get("lex_user")
    if not u:
        return
    if isinstance(req_obj, str):
        req_obj = {"handle": req_obj, "name": req_obj.lstrip("@")}
    r_h = "@" + clean_handle_str(req_obj.get("handle", ""))
    st.session_state.lex_theme["incoming_requests"] = [x for x in (st.session_state.lex_theme.get("incoming_requests") or []) if isinstance(x, dict) and x.get("handle", "").lower() != r_h.lower()]
    if len(st.session_state.lex_friends) < MAX_FRIENDS and not any(isinstance(f, dict) and f.get("handle", "").lower() == r_h.lower() for f in st.session_state.lex_friends):
        st.session_state.lex_friends.append({"handle": r_h, "name": req_obj.get("name", r_h.lstrip("@")), "mood": req_obj.get("mood", "Online ⚡"), "anthem": req_obj.get("anthem", "Y2K Cobalt Synth")})
    save_profile_to_cloud()
    if sb and len(r_h) > 1:
        sb.table("lex_messages").insert({
            "sender_handle": u["handle"], "recipient_handle": r_h,
            "body": f"[LEX_FACC]{u['name']}|{u.get('mood', 'Online ⚡')}|{u.get('anthem', 'Y2K Cobalt Synth')}"
        }).execute()

def decline_friend_request(req_handle: str):
    sb = get_sb()
    u = st.session_state.get("lex_user")
    r_h = "@" + clean_handle_str(req_handle)
    st.session_state.lex_theme["incoming_requests"] = [x for x in (st.session_state.lex_theme.get("incoming_requests") or []) if isinstance(x, dict) and x.get("handle", "").lower() != r_h.lower()]
    save_profile_to_cloud()
    if sb and u and len(r_h) > 1:
        sb.table("lex_messages").insert({"sender_handle": u["handle"], "recipient_handle": r_h, "body": "[LEX_FDEC]"}).execute()

def toggle_follow_user(my_handle: str, target_handle: str):
    sb = get_sb()
    my_clean = "@" + clean_handle_str(my_handle)
    tgt_clean = "@" + clean_handle_str(target_handle)
    following = list(st.session_state.lex_theme.get("following") or [])
    existing_idx = next((i for i, x in enumerate(following) if str(x).lower() == tgt_clean.lower()), None)
    adding = existing_idx is None
    if adding:
        following.append(tgt_clean)
    else:
        following.pop(existing_idx)
    st.session_state.lex_theme["following"] = following
    save_profile_to_cloud()
    if sb:
        try:
            res = sb.table("lex_profiles").select("user_id, handle, theme_json").ilike("handle", tgt_clean).execute().data or []
            t_row = next(iter(res), None)
            if isinstance(t_row, dict):
                tj = dict(t_row.get("theme_json") or {})
                f_list = list(tj.get("followers") or [])
                f_list = [x for x in f_list if str(x).lower() != my_clean.lower()]
                if adding:
                    f_list.append(my_clean)
                tj["followers"] = f_list
                sb.table("lex_profiles").update({"theme_json": tj}).eq("user_id", t_row["user_id"]).execute()
        except Exception as e:
            st.warning(f"Follow sync notice: {e}")

def render_popular_song_embed(url: str) -> bool:
    clean = (url or "").strip()
    if not clean:
        return False
    sp_host = ".".join(["open", "spotify", "com"]) + "/track/"
    if sp_host in clean:
        _, _, tail = clean.partition(sp_host)
        track_id, _, _ = tail.partition("?")
        components.iframe(f"{SPOTIFY_EMBED}{track_id.strip('/')}?utm_source=generator&theme=0", height=152)
        return True
    if "youtube.com" in clean or "youtu.be/" in clean:
        st.video(clean)
        return True
    ap_host = ".".join(["music", "apple", "com"])
    if ap_host in clean and ("embed." + ap_host) not in clean:
        components.iframe(clean.replace(ap_host, "embed." + ap_host), height=175)
        return True
    return False

def render_mini_yt_audio_bar(yt_id: str, track_label: str, accent: str, playlist_ref: list = None):
    if not yt_id:
        return
    import random
    loop_on = bool(st.session_state.get("yt_loop_on", False))
    loop_q = f"&loop=1&playlist={yt_id}" if loop_on else ""
    src = f"{YT_EMBED_BASE}{yt_id}?autoplay=1&controls=1&rel=0{loop_q}"
    st.markdown(f'<div class="lex-card" style="padding:8px 10px;margin:8px 0;"><div style="font-size:12px;font-weight:800;color:{accent};margin-bottom:4px;">🎧 NOW SPINNING: {track_label} {"🔁" if loop_on else ""}</div><div style="height:46px;overflow:hidden;border-radius:6px;"><iframe width="100%" height="140" src="{src}" frameborder="0" allow="autoplay; encrypted-media" style="margin-top:-92px;"></iframe></div></div>', unsafe_allow_html=True)
    mc1, mc2, mc3 = st.columns(3)
    if mc1.button("⏹️ Stop", key="yt_stop_btn", use_container_width=True):
        st.session_state.active_yt_track = None
        st.rerun()
    if mc2.button("🔁 Loop: ON" if loop_on else "🔁 Loop: OFF", key="yt_loop_btn", use_container_width=True):
        st.session_state.yt_loop_on = not loop_on
        st.rerun()
    if mc3.button("🔀 Shuffle", key="yt_shuf_btn", use_container_width=True) and playlist_ref:
        st.session_state.active_yt_track = random.choice(playlist_ref)
        st.rerun()

for k, v in [("lex_user", None), ("lex_theme", DEFAULT_THEME.copy()), ("lex_top8", []), ("lex_friends", []), ("viewing_handle", None), ("dm_target_override", ""), ("active_yt_track", None), ("show_notifs", False)]:
    if k not in st.session_state:
        st.session_state[k] = v
if "lex_wall" not in st.session_state:
    st.session_state.lex_wall = [{"sender": "@LeX", "msg": "Welcome to LeX! Drop a wall note anytime ✦"}]
def build_theme_css(t_cfg: dict) -> str:
    gf_name, css_ff = FONT_MAP.get(t_cfg.get("font", "Clean Studio Sans"), FONT_MAP["Clean Studio Sans"])
    bg_pat = build_backdrop_url(t_cfg.get("backdrop", "Architectural Grid"), t_cfg["accent"], t_cfg.get("spray_word", "LeX!"))
    c_wall = t_cfg.get("custom_wall", "")
    bg_img = f'url("{c_wall}")' if c_wall else bg_pat
    bg_sz = "cover" if c_wall else ("56px 56px" if t_cfg.get("backdrop") == "Architectural Grid" else "260px 220px")
    bg_rep = "no-repeat" if c_wall else "repeat"
    if not st.session_state.get("lex_user"):
        bg_img, bg_sz, bg_rep = "radial-gradient(circle at 20% 15%, #1e293b 0%, #0f172a 48%, #07090f 100%)", "cover", "no-repeat"
    glw = f"box-shadow: 0 0 18px {t_cfg['accent']}66, inset 0 0 10px {t_cfg['accent']}22;" if t_cfg.get("glow_borders", True) else ""
    tglw = f"text-shadow: 0 0 14px {t_cfg['accent']};" if t_cfg.get("text_glow", True) else ""
    opv = max(40, min(100, int(t_cfg.get("card_opacity", 92)))) / 100.0
    rpx = int(t_cfg.get("card_radius", 12))
    cur_css = CURSOR_OPTIONS.get(t_cfg.get("cursor_style", "Default System Pointer"), "auto")
    anim_mode = t_cfg.get("card_anim", "None (Static)")
    anim_kf = "@keyframes lexCardPulse{0%,100%{box-shadow:0 0 14px " + t_cfg["accent"] + "55}50%{box-shadow:0 0 28px " + t_cfg["accent"] + "cc}}@keyframes lexFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}@keyframes lexGlitch{0%,94%,100%{transform:translate(0)}96%{transform:translate(-2px,1px)}98%{transform:translate(2px,-1px)}}"
    anim_rule = "animation: lexCardPulse 2.4s ease-in-out infinite;" if anim_mode == "Pulse Neon Glow" else ("animation: lexFloat 3s ease-in-out infinite;" if anim_mode == "Floating Levitate" else ("animation: lexGlitch 3.5s infinite;" if anim_mode == "Cyber Glitch Flicker" else ""))
    x_css = (t_cfg.get("custom_css") or "").replace("<", "").replace(">", "")
    if os.path.exists("lex-logo.png"):
        _ic_b64 = base64.b64encode(open("lex-logo.png", "rb").read()).decode("ascii")
        components.html(f'<script>["apple-touch-icon","icon"].forEach(r=>{{let l=document.createElement("link");l.rel=r;l.href="data:image/png;base64,{_ic_b64}";window.parent.document.head.appendChild(l);}});</script>', height=0)

    return (
        f'{LK_OPEN}rel="stylesheet" href="{GFONTS_BASE}{gf_name.replace(" ", "+")}&display=swap" />' + ST_OPEN + anim_kf
        + f'[data-testid="stAppViewContainer"], .stApp {{ background-color: {t_cfg["bg"]} !important; background-image: {bg_img} !important; background-size: {bg_sz} !important; background-repeat: {bg_rep} !important; background-attachment: fixed !important; color: {t_cfg["text"]} !important; cursor: {cur_css}; }}'
        + '[data-testid="stHeader"], [data-testid="stMain"] { background: transparent !important; }'
        + f"@keyframes lexBannerRoll {{ 0% {{ opacity:0; transform:translateX(-48px) scaleX(0.96); }} 100% {{ opacity:1; transform:translateX(0) scaleX(1); }} }}"
        + f"@keyframes lexSilverGlint {{ 0%, 15% {{ left:-45%; opacity:0; }} 30% {{ opacity:0.95; }} 55% {{ left:115%; opacity:0; }} 100% {{ left:115%; opacity:0; }} }}"
        + f".lex-banner {{ position:relative; overflow:hidden; padding:22px 26px; border-radius:18px; margin-bottom:14px; background:linear-gradient(125deg, rgba(12,14,22,0.94) 0%, rgba(26,30,44,0.92) 55%, rgba(14,16,24,0.96) 100%); border:1px solid rgba(226,232,240,0.38); box-shadow:0 12px 36px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.28); animation:lexBannerRoll 0.9s cubic-bezier(0.22, 1, 0.36, 1) both; }}"
        + f".lex-banner::after {{ content:''; position:absolute; top:-40%; left:-45%; width:28%; height:180%; background:linear-gradient(105deg, transparent 20%, rgba(255,255,255,0.12) 42%, rgba(255,255,255,0.85) 50%, rgba(203,213,225,0.18) 58%, transparent 80%); transform:rotate(18deg); pointer-events:none; animation:lexSilverGlint 4.2s ease-in-out 0.55s infinite; }}"
        + f".lex-wordmark {{ position:relative; display:inline-block; font-family:'Cinzel','Playfair Display',Georgia,serif; font-size:44px; font-weight:900; letter-spacing:3px; line-height:1.05; background:linear-gradient(180deg, #FFFFFF 0%, #E2E8F0 38%, #94A3B8 68%, #F8FAFC 100%); -webkit-background-clip:text; -webkit-text-fill-color:transparent; filter:drop-shadow(0 0 14px rgba(226,232,240,0.55)) drop-shadow(0 2px 4px rgba(0,0,0,0.85)); }}"
        + f".lex-card {{ background: {t_cfg['card']}; opacity: {opv}; border: 1.5px {t_cfg['border_style']} {t_cfg['accent']}; border-radius: {rpx}px; padding: 16px 18px; margin-bottom: 12px; {glw} {anim_rule} }}"
        + f".lex-card h1, .lex-card h2, .lex-card h3 {{ font-family: {css_ff}; {tglw} }}"
        + f".lex-friend-card {{ background: linear-gradient(145deg, {t_cfg['card']}, #000000); opacity: {opv}; border: 1.5px {t_cfg['border_style']} {t_cfg['accent']}; border-radius: {rpx}px; padding: 12px; margin-bottom: 10px; {glw} }}"
        + x_css + ST_CLOSE
    )
th = st.session_state.lex_theme
rad_px = int(th.get("card_radius", 12))
st.markdown(build_theme_css(th), unsafe_allow_html=True)
head_c1, head_c2 = st.columns([0.16, 0.84])
with head_c1:
    if os.path.exists("lex-logo.png"):
        st.image("lex-logo.png", width=145)
with head_c2:
    st.markdown('<div class="lex-banner"><div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px;"><div><div class="lex-wordmark">LeX</div><div style="height:2px;width:54px;margin:6px 0 8px 0;background:linear-gradient(90deg,#FFFFFF,#94A3B8,transparent);border-radius:99px;"></div><div style="color:#CBD5E1;font-family:\'Inter\',sans-serif;font-size:11px;font-weight:600;letter-spacing:2.4px;text-transform:uppercase;">Engineered by LexiTech Studio &bull; Algorithm-Free Social</div></div><div style="padding:5px 12px;border-radius:99px;border:1px solid rgba(226,232,240,0.32);background:rgba(255,255,255,0.06);color:#E2E8F0;font-size:10px;font-weight:700;letter-spacing:1.6px;">PUBLIC BETA // 13+</div></div></div>', unsafe_allow_html=True)

sb = get_sb()
if st.session_state.get("show_confirm_email_popup"):
    _pop_c1, _pop_c2 = st.columns([0.92, 0.08])
    with _pop_c1:
        st.markdown(
            '<div style="background:linear-gradient(135deg,#120724,#2E1065);border:2px solid #A855F7;border-radius:16px;padding:16px 18px;box-shadow:0 0 28px rgba(168,85,247,0.65);margin:10px 0;">'
            '<div style="font-size:16px;font-weight:900;color:#F3E8FF;margin-bottom:6px;">📩 Please Confirm Your Email Address</div>'
            '<div style="font-size:13.5px;color:#E9D5FF;line-height:1.45;">We just sent a confirmation link to your inbox. Tap the link inside that email to verify your <b>LeX Social</b> account!</div>'
            '<div style="margin-top:10px;padding:8px 10px;border-radius:10px;background:rgba(255,255,255,0.08);font-size:11.5px;color:#FDE68A;line-height:1.4;">'
            '⚠️ <b>Heads up:</b> When you click the confirmation link in your email, the page it opens may act broken or show an error—<b>don’t worry!</b> Clicking it still confirms your email automatically. Just come back here and sign in!'
            '</div></div>',
            unsafe_allow_html=True,
        )
    with _pop_c2:
        if st.button("✕", key="close_confirm_email_popup", help="Close notice"):
            st.session_state["show_confirm_email_popup"] = False
            st.rerun()
if st.session_state.lex_user is None:
    t_in, t_up = st.tabs(["🔐 Member Sign In", "+ Create Account"])
    with t_in:
        with st.form("lex_login_form"):
            l_email, l_pass = st.text_input("Email"), st.text_input("Password", type="password")
            if st.form_submit_button("Sign In to My LeX Profile +", use_container_width=True):
                try:
                    res = sb.auth.sign_in_with_password({"email": l_email.strip(), "password": l_pass})
                    uid = res.user.id
                    prof = sb.table("lex_profiles").select("*").eq("user_id", uid).execute().data
                    r = next(iter(prof), None) if isinstance(prof, list) else prof
                    if isinstance(r, dict):
                        tj = r.get("theme_json") or {}
                        if isinstance(tj, str): tj = json.loads(tj or "{}")
                        st.session_state.lex_user = {
                            "user_id": uid, "name": r.get("display_name", "Member"), "handle": r.get("handle", "@Member"),
                            "avatar": tj.get("avatar", ""), "website": tj.get("website", ""),
                            "bio": r.get("bio", ""), "who_to_meet": r.get("who_to_meet", ""),
                            "mood": r.get("mood", "Online Now • Vibing ⚡"), "anthem": r.get("anthem", "Y2K Cobalt Synth"),
                            "custom_song_url": r.get("custom_song_url", ""), "custom_song_title": r.get("custom_song_title", ""),
                        }
                        st.session_state.lex_theme.update(tj)
                        st.session_state.lex_top8 = [x if isinstance(x, dict) else {"handle": str(x)} for x in (r.get("top8_json") or [])]
                        raw_fr = tj.get("all_friends") or r.get("friends_json") or []
                        st.session_state.lex_friends = [x if isinstance(x, dict) else {"handle": str(x)} for x in raw_fr]
                        if r.get("wall_json"):
                            st.session_state.lex_wall = r["wall_json"]
                    else:

                        prefix, _, _ = l_email.strip().partition("@")
                        base_h = clean_handle_str(prefix) or "Member"
                        cand, sfx = base_h, 1
                        while is_handle_taken(sb, cand, uid):
                            cand = f"{base_h}{sfx}"
                            sfx += 1
                        st.session_state.lex_user = {"user_id": uid, "name": cand, "handle": f"@{cand}"}
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
                    st.error("Enter a valid @handle using letters, numbers, or underscores.")
                elif is_handle_taken(sb, ch):
                    st.error(f"@{ch} is already taken! Every handle on LeX must be unique.")
                elif s_email.strip() and len(s_pass) >= 6 and d_name.strip():
                    try:
                        ares = sb.auth.sign_up({"email": s_email.strip(), "password": s_pass})
                        st.session_state.lex_user = {"user_id": ares.user.id, "name": d_name.strip(), "handle": f"@{ch}", "avatar": "", "website": normalize_url(site_in), "mood": "Online Now • Vibing ⚡", "bio": "Zero algorithms. Custom vibes on LeX.", "who_to_meet": "Creators & music lovers.", "anthem": "Y2K Cobalt Synth", "custom_song_url": "", "custom_song_title": ""}
                        save_profile_to_cloud()
                        st.session_state["show_confirm_email_popup"] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Signup error: {e}")
    st.markdown(
        f"{ST_OPEN}"
        + ".lex-app-dock { margin-top: 18px; padding: 16px 14px; border-radius: 14px; "
        + "background: linear-gradient(180deg, #23252B 0%, #16181D 100%); "
        + "border: 1px solid #8E94A0; text-align: center; }"
        + ".lex-app-title { font-size: 11px; font-weight: 800; letter-spacing: 0.16em; "
        + "color: #E2E5EC; text-transform: uppercase; margin-bottom: 4px; }"
        + ".lex-app-sub { font-size: 11.5px; color: #9DA3B0; margin-bottom: 12px; }"
        + ".lex-app-row { display: flex; justify-content: center; gap: 10px; flex-wrap: wrap; }"
        + ".lex-app-btn { display: inline-flex; align-items: center; gap: 8px; padding: 9px 14px; "
        + "border-radius: 10px; background: linear-gradient(180deg, #D8DCE3 0%, #AEB4C0 100%); "
        + "border: 1px solid #F2F4F8; color: #111318 !important; text-decoration: none !important; "
        + "font-size: 12px; font-weight: 700; letter-spacing: 0.02em; }"
        + ".lex-app-btn:hover { background: linear-gradient(180deg, #E8EBF0 0%, #C2C7D2 100%); }"
        + ".lex-steps-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr)); "
        + "gap: 10px; margin-top: 14px; text-align: left; }"
        + ".lex-step-card { padding: 10px 11px; border-radius: 10px; background: #121418; "
        + "border: 1px solid #2E333E; color: #B8BECB; font-size: 11px; line-height: 1.45; }"
        + ".lex-step-head { font-weight: 800; color: #E2E5EC; font-size: 11px; "
        + "letter-spacing: 0.04em; text-transform: uppercase; margin-bottom: 4px; }"
        + ".lex-app-note { font-size: 10.5px; color: #888F9E; margin-top: 10px; }"
        + f"{ST_CLOSE}",
        unsafe_allow_html=True,
    )
    rel_base = "https://" + ".".join(["github", "com"]) + "/HeidiSeckman/LeX/releases/download/v1.0/"
    ic_and = f"{SV_OPEN}width='16' height='16' viewBox='0 0 24 24' fill='#111318' xmlns='{SVG_NS}'><path d='M6 18c0 .55.45 1 1 1h1v3.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5V19h2v3.5c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5V19h1c.55 0 1-.45 1-1V8H6v10zM3.5 8C2.67 8 2 8.67 2 9.5v7c0 .83.67 1.5 1.5 1.5S5 17.33 5 16.5v-7C5 8.67 4.33 8 3.5 8zm17 0c-.83 0-1.5.67-1.5 1.5v7c0 .83.67 1.5 1.5 1.5s1.5-.67 1.5-1.5v-7c0-.83-.67-1.5-1.5-1.5zm-4.97-5.84l1.3-1.3c.2-.2.2-.51 0-.71-.2-.2-.51-.2-.71 0l-1.48 1.48C13.85 1.23 12.95 1 12 1c-.96 0-1.86.23-2.66.63L7.85.15c-.2-.2-.51-.2-.71 0-.2.2-.2.51 0 .71l1.31 1.31C6.97 3.26 6 5.01 6 7h12c0-1.99-.97-3.75-2.47-4.84zM10 5H9V4h1v1zm5 0h-1V4h1v1z'/>{SV_CLOSE}"
    ic_win = f"{SV_OPEN}width='15' height='15' viewBox='0 0 24 24' fill='#111318' xmlns='{SVG_NS}'><path d='M3 5.5L10.5 4.4V11.5H3V5.5ZM11.5 4.3L21 3V11.5H11.5V4.3ZM3 12.5H10.5V19.6L3 18.5V12.5ZM11.5 12.5H21V21L11.5 19.7V12.5Z'/>{SV_CLOSE}"
    a_and = "<" + f"a class='lex-app-btn' href='{rel_base}LeXSocial.apk' download>{ic_and}<span>Android (.APK)</span><" + "/a>"
    a_win = "<" + f"a class='lex-app-btn' href='{rel_base}LeXSocial.msi' download>{ic_win}<span>Windows (.MSI)</span><" + "/a>"
    st.markdown(
        "<div class='lex-app-dock'>"
        + "<div class='lex-app-title'>Get the Official LeX Social App</div>"
        + "<div class='lex-app-sub'>One-tap install for Android &amp; Windows &bull; Zero algorithms</div>"
        + f"<div class='lex-app-row'>{a_and}{a_win}</div>"
        + "<div class='lex-steps-grid'>"
        + "<div class='lex-step-card'><div class='lex-step-head'>Android / Samsung</div>1. Tap <strong>Android (.APK)</strong> above.<br/>2. Open the downloaded file.<br/>3. Tap <strong>Install</strong> (allow unknown apps if asked).</div>"
        + "<div class='lex-step-card'><div class='lex-step-head'>Windows PC</div>1. Click <strong>Windows (.MSI)</strong> above.<br/>2. Double-click <strong>LeXSocial.msi</strong>.<br/>3. Click <strong>More info &rarr; Run anyway</strong> to finish.</div>"
        + "</div>"
        + "<div class='lex-app-note'>iPhone &amp; iPad: App Store release coming soon &bull; Full experience live right here in Safari.</div>"
        + "</div>",
        unsafe_allow_html=True,
    )
    st.stop()


user = st.session_state.lex_user
st.session_state.lex_friends = [x if isinstance(x, dict) else {"handle": str(x), "name": str(x).lstrip("@")} for x in (st.session_state.lex_friends or [])]
st.session_state.lex_top8 = [x if isinstance(x, dict) else {"handle": str(x), "name": str(x).lstrip("@")} for x in (st.session_state.lex_top8 or [])]

if sb and user.get("handle"):
    try:
        my_low = user["handle"].lower()
        all_sys = sb.table("lex_messages").select("*").order("id", desc=False).limit(500).execute().data or []
        my_f_low = {f["handle"].lower() for f in st.session_state.lex_friends}
        inc_dict, sent_dict, dirty_sync = {}, {}, False
        for sr in all_sys:
            b_txt = sr.get("body") or ""
            if not b_txt.startswith("[LEX_F"):
                continue
            s_h = "@" + clean_handle_str(sr.get("sender_handle", ""))
            r_h = "@" + clean_handle_str(sr.get("recipient_handle", ""))
            s_low, r_low = s_h.lower(), r_h.lower()
            if r_low == my_low and len(s_h) > 1:
                if b_txt.startswith("[LEX_FREQ]"):
                    p_name, _, p_rest = b_txt[10:].partition("|")
                    p_mood, _, p_anth = p_rest.partition("|")
                    if s_low not in my_f_low:
                        inc_dict[s_low] = {"handle": s_h, "name": p_name or s_h.lstrip("@"), "mood": p_mood or "Online ⚡", "anthem": p_anth or "Y2K Cobalt Synth"}
                elif b_txt.startswith("[LEX_FCAN]"):
                    inc_dict.pop(s_low, None)
                elif b_txt.startswith("[LEX_FACC]"):
                    p_name, _, p_rest = b_txt[10:].partition("|")
                    p_mood, _, p_anth = p_rest.partition("|")
                    sent_dict.pop(s_low, None)
                    inc_dict.pop(s_low, None)
                    if s_low not in my_f_low and len(st.session_state.lex_friends) < MAX_FRIENDS:
                        st.session_state.lex_friends.append({"handle": s_h, "name": p_name or s_h.lstrip("@"), "mood": p_mood or "Online ⚡", "anthem": p_anth or "Y2K Cobalt Synth"})
                        my_f_low.add(s_low)
                        dirty_sync = True
                elif b_txt.startswith("[LEX_FDEC]"):
                    sent_dict.pop(s_low, None)
            elif s_low == my_low and len(r_h) > 1:
                if b_txt.startswith("[LEX_FREQ]") and r_low not in my_f_low:
                    sent_dict[r_low] = r_h
                elif b_txt.startswith("[LEX_FCAN]"):
                    sent_dict.pop(r_low, None)
                elif b_txt.startswith("[LEX_FACC]") or b_txt.startswith("[LEX_FDEC]"):
                    inc_dict.pop(r_low, None)
        st.session_state.lex_theme["incoming_requests"] = list(inc_dict.values())
        st.session_state.lex_theme["sent_requests"] = list(sent_dict.values())
        if dirty_sync:
            save_profile_to_cloud()
    except Exception:
        pass
my_notifs = []
if sb and user.get("handle"):
    try:
        n_rows = sb.table("lex_messages").select("*").ilike("recipient_handle", user["handle"]).order("id", desc=True).limit(150).execute().data or []
        for nr in n_rows:
            nb = nr.get("body") or ""
            if nb.startswith("[LEX_NOTIF]"):
                kind, _, rest = nb[11:].partition("|")
                pid_s, _, det_s = rest.partition("|")
                my_notifs.append({"id": int(nr.get("id") or 0), "actor": nr.get("sender_handle", "@Member"), "kind": kind, "pid": pid_s, "detail": det_s})
    except Exception:
        pass

last_seen_nid = int(th.get("notif_read_id") or 0)
unread_n = sum(1 for x in my_notifs if x["id"] > last_seen_nid)
n_lbl = f"🔔 Notifications ({unread_n})" if unread_n else "🔔 Notifications"
unread_dms = []
if sb and user.get("handle"):
    try:
        dm_rows = sb.table("lex_messages").select("*").ilike("recipient_handle", user["handle"]).order("id", desc=True).limit(60).execute().data or []
        last_dm_id = int(th.get("dm_read_id") or 0)
        for dr in dm_rows:
            db_txt = dr.get("body") or ""
            if not db_txt.startswith(("[LEX_F", "[LEX_NOTIF]")) and int(dr.get("id") or 0) > last_dm_id:
                unread_dms.append(dr)
    except Exception:
        pass
if unread_dms:
    latest_dm = unread_dms[0]
    st.info(f"✉️ **{len(unread_dms)} New Message(s)** — Latest from **{latest_dm.get('sender_handle')}**: “{(latest_dm.get('body') or '')[:60]}” (Open **✉️ Messages** tab to reply!)")
    if st.button("✓ Dismiss Message Alert", key="dismiss_dm_alert"):
        th["dm_read_id"] = max(int(x.get("id") or 0) for x in unread_dms)
        save_profile_to_cloud()
        st.rerun()

top_c1, top_c2, top_c3 = st.columns([0.62, 0.23, 0.15])
if st.session_state.viewing_handle and top_c1.button(f"← Back to My Profile ({user['handle']})"):
    st.session_state.viewing_handle = None
    st.rerun()
if top_c2.button(n_lbl, use_container_width=True, key="top_notif_btn"):
    st.session_state.show_notifs = not st.session_state.show_notifs
    st.rerun()
if top_c3.button("Sign Out", use_container_width=True):
    st.session_state.lex_user = None
    st.session_state.viewing_handle = None
    st.rerun()

if st.session_state.show_notifs:
    nh1, nh2 = st.columns([0.75, 0.25])
    nh1.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:6px;"><strong style="color:{th["accent"]};">🔔 Post Reactions &amp; Comments Activity</strong></div>', unsafe_allow_html=True)
    if my_notifs and nh2.button("✓ Mark All Read", use_container_width=True, key="mark_notifs_read"):
        th["notif_read_id"] = max(x["id"] for x in my_notifs)
        save_profile_to_cloud()
        st.rerun()
    if not my_notifs:
        st.caption("No post reactions or comments yet—when members react or comment on your posts, they appear right here!")
    for nf in my_notifs[:20]:
        is_new = nf["id"] > last_seen_nid
        tag_new = f'<span style="background:{th["accent"]};color:#000;padding:1px 6px;border-radius:99px;font-size:10px;font-weight:900;margin-right:6px;">NEW</span>' if is_new else ""
        act_txt = f"reacted {nf['detail']} to your post" if nf["kind"] == "react" else f"commented on your post: “{nf['detail']}”"
        st.markdown(f'<div class="lex-card" style="padding:8px 12px;margin-bottom:6px;">{tag_new}<strong>{nf["actor"]}</strong> {act_txt}</div>', unsafe_allow_html=True)
def friend_card_html(fr, badge: str = "", card_theme: dict = None) -> str:
    if isinstance(fr, str):
        fr = {"handle": fr, "name": fr.lstrip("@") or "Member"}
    elif not isinstance(fr, dict):
        fr = {"handle": "@Member", "name": "Member"}
    ct = card_theme or th
    ini = (str(fr.get("name") or fr.get("handle") or "L").lstrip("@")[:1] or "L").upper()
    is_owner = (str(fr.get("handle", "")).strip().lower() in {"@heidi", "@heidiseckman"})
    pill_lbl = "👑 FOUNDER" if is_owner else badge
    top_tag = f'<span style="background:{ct["accent"]};color:#000;padding:2px 7px;border-radius:99px;font-size:10px;font-weight:900;">{pill_lbl}</span>' if pill_lbl else '<span></span>'
    is_on = is_member_online(fr) if ("last_seen" in fr) else False
    on_tag = '<span style="color:#34D399;font-size:11px;font-weight:700;">&#9679; ONLINE</span>' if is_on else '<span style="color:#94A3B8;font-size:11px;font-weight:700;">&#9679; OFFLINE</span>'
    _av_cache = st.session_state.setdefault("_lex_av_cache", {})
    _fh_key = "@" + clean_handle_str(fr.get("handle", "")).lower()
    _av_src = fr.get("avatar") or _av_cache.get(_fh_key, "")
    if not _av_src and _fh_key not in _av_cache and len(_fh_key) > 1 and sb:
        try:
            _r_av = sb.table("lex_profiles").select("theme_json").ilike("handle", _fh_key).limit(1).execute().data or []
            _av_src = (_r_av[0].get("theme_json") or {}).get("avatar", "") if _r_av else ""
        except Exception:
            _av_src = ""
        _av_cache[_fh_key] = _av_src
    _av_box = f'<img src="{_av_src}" style="width:42px;height:42px;border-radius:50%;object-fit:cover;border:2px solid {ct["accent"]};box-shadow:0 0 10px {ct["accent"]};" />' if _av_src else f'<div style="width:42px;height:42px;border-radius:50%;background:radial-gradient(circle,{ct["accent"]},#111);border:2px solid {ct["accent"]};display:flex;align-items:center;justify-content:center;font-weight:900;color:#FFF;box-shadow:0 0 10px {ct["accent"]};">{ini}</div>'
    return f'<div class="lex-friend-card"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">{top_tag}{on_tag}</div><div style="display:flex;align-items:center;gap:10px;">{_av_box}<div><div style="font-weight:800;font-size:14px;color:{ct["text"]};">{fr.get("name", fr.get("handle", "Member"))}</div><div style="color:{ct["accent"]};font-size:12px;font-weight:700;">{fr.get("handle", "@Member")}</div></div></div><div style="font-size:11px;color:#D4D4D8;margin-top:8px;">{fr.get("mood", "Vibing ⚡")}</div><div style="margin-top:6px;padding:4px 8px;border-radius:6px;background:rgba(255,255,255,0.05);font-size:10px;color:{ct["accent"]};">🎵 {fr.get("anthem", "Y2K Cobalt Synth")}</div></div>'

def render_member_action_buttons(target_handle: str, key_prefix: str = "m"):
    tgt = "@" + clean_handle_str(target_handle)
    if len(tgt) <= 1 or tgt.lower() == user["handle"].lower():
        return
    is_fr = any(isinstance(f, dict) and f.get("handle", "").lower() == tgt.lower() for f in st.session_state.lex_friends)
    is_sent = tgt.lower() in {str(x).lower() for x in (th.get("sent_requests") or [])}
    inc_match = next((x for x in (th.get("incoming_requests") or []) if isinstance(x, dict) and x.get("handle", "").lower() == tgt.lower()), None)
    b1, b2, b3 = st.columns(3)
    if b1.button("👁️ Profile", key=f"{key_prefix}_vp_{tgt}", use_container_width=True):
        st.session_state.viewing_handle = tgt
        st.rerun()
    if is_fr:
        b2.button("✓ Friends", key=f"{key_prefix}_fr_{tgt}", disabled=True, use_container_width=True)
    elif inc_match:
        if b2.button("✓ Accept", key=f"{key_prefix}_ac_{tgt}", use_container_width=True):
            accept_friend_request(inc_match)
            st.rerun()
    elif is_sent:
        if b2.button("✕ Cancel", key=f"{key_prefix}_cn_{tgt}", use_container_width=True):
            cancel_friend_request(tgt)
            st.rerun()
    elif b2.button("+ Add Friend", key=f"{key_prefix}_ad_{tgt}", use_container_width=True):
        send_friend_request(tgt)
        st.toast(f"Friend request sent to {tgt}!")
        st.rerun()
    if b3.button("✉️ Message", key=f"{key_prefix}_dm_{tgt}", use_container_width=True):
        st.session_state.dm_target_override = tgt
        st.session_state.viewing_handle = None
        st.toast(f"Opened chat with {tgt} in Messages tab!")
        st.rerun()
if st.session_state.viewing_handle and sb:
    vh_clean = "@" + clean_handle_str(st.session_state.viewing_handle)
    v_res = sb.table("lex_profiles").select("*").ilike("handle", vh_clean).execute().data
    vp = next(iter(v_res), None) if isinstance(v_res, list) else v_res
    if not isinstance(vp, dict):
        st.warning(f"Could not load profile for {vh_clean}.")
        st.stop()
    vtj = vp.get("theme_json") or {}
    if isinstance(vtj, str): vtj = json.loads(vtj or "{}")
    v_th = DEFAULT_THEME.copy()
    v_th.update(vtj)
    if isinstance(st.session_state.get("lex_theme"), str):
        st.session_state.lex_theme = json.loads(st.session_state.lex_theme or "{}")
    v_h_str = (vp.get("handle") or "").strip()
    v_rad = int(v_th.get("card_radius", 12))
    st.markdown(build_theme_css(v_th), unsafe_allow_html=True)
    vb_html = build_live_banner_html(v_th.get("banner_live", "None"), v_th.get("banner_img", ""), v_th["accent"], v_rad)
    if vb_html:
        st.markdown(vb_html, unsafe_allow_html=True)
    if v_th.get("marquee_on") and v_th.get("marquee_text"):
        st.markdown(f'<div class="lex-card" style="padding:6px 12px;"><marquee style="color:{v_th["accent"]};font-weight:800;letter-spacing:0.06em;">{v_th["marquee_text"]}</marquee></div>', unsafe_allow_html=True)
    if v_th.get("pinned_note"):
        st.markdown(f'<div class="lex-card" style="border-width:2.5px;"><span style="color:{v_th["accent"]};font-weight:900;font-size:11px;">📌 PINNED BULLETIN</span><div style="margin-top:4px;">{v_th["pinned_note"]}</div></div>', unsafe_allow_html=True)
    v_fol, v_fr = list(vtj.get("followers") or []), list(vtj.get("all_friends") or [])
    v_av = render_avatar_html(vtj.get("avatar", ""), vp.get("display_name", "M"), v_th, 84)
    v_is_founder = vp.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"}
    v_site = founder_studio_link_html(vp.get("handle", ""), v_th["accent"]) if v_is_founder else build_profile_link_html(vtj.get("website", ""), vtj.get("website_label", ""), v_th["accent"])
    v_badges = earned_badges_html(v_th, len(v_fr), len(vp.get("top8_json") or []), vp.get("handle", ""))
    v_ints = [(lbl, v_th.get(k, "")) for lbl, k in [("General", "int_general"), ("Music", "int_music"), ("Movies", "int_movies"), ("TV", "int_tv"), ("Books & Heroes", "int_books")] if v_th.get(k)]
    v_int_html = "".join([f'<div style="font-size:12px;margin-top:4px;"><strong style="color:{v_th["accent"]};">{l}:</strong> {val}</div>' for l, val in v_ints])
    online_badge = "🟢 ONLINE" if is_member_online(v_th) else "⚫ OFFLINE"
    visit_key = f"logged_visit_{v_h_str.lower()}"
    if v_h_str and v_h_str.lstrip("@").lower() != user["handle"].lstrip("@").lower() and not st.session_state.get(visit_key):
        try:
            t_vis = [v for v in vtj.get("visitors", []) if (str(v.get("handle", "") if isinstance(v, dict) else v)).lstrip("@").lower() != user["handle"].lstrip("@").lower()]
            t_vis.insert(0, {"handle": user["handle"], "name": user.get("name", user["handle"]), "ts": int(time.time())})
            vtj["visitors"] = t_vis[:10]
            sb.table("lex_profiles").update({"theme_json": vtj}).eq("handle", v_h_str).execute()
            st.session_state[visit_key] = True
        except Exception:
            pass

    st.markdown(f'<div class="lex-card"><div style="display:flex;align-items:center;gap:16px;">{v_av}<div><h2 style="margin:0;">{vp.get("display_name", "")} {founder_badge_html(vp.get("handle", ""))}</h2><div style="color:{v_th["accent"]};font-weight:700;">{vp.get("handle", "")} <span style="font-size:11px;margin-left:6px;">{online_badge}</span></div><div style="color:#34D399;font-size:13px;">● {vp.get("mood", "Online ⚡")}</div>{v_badges}{v_site}</div></div><div style="display:flex;gap:18px;margin-top:12px;font-weight:800;font-size:13px;"><span>⚡ {len(v_fol)} Followers (Unlimited)</span><span>👥 {len(v_fr)} / {MAX_FRIENDS} Friends</span></div><p style="margin-top:12px;"><strong>About Me:</strong> {vp.get("bio", "")}</p><p><strong>Who I\'d Like to Meet:</strong> {vp.get("who_to_meet", "")}</p>{v_int_html}</div>', unsafe_allow_html=True)
    if v_th.get("allow_css_remix") and (v_th.get("custom_css") or "").strip():
        if st.button(f"✨ Steal This Look (Remix {vp.get('handle', '')}'s Theme)", key="steal_look_btn"):
            credit_tag = f'html body .lex-banner::after{{content:"Theme inspired by {vp.get("handle", "@Member")}";position:absolute;bottom:6px;right:12px;font-size:10px;opacity:0.85;font-weight:800;}}'
            th.update({
                "bg": v_th.get("bg", th["bg"]), "card": v_th.get("card", th["card"]),
                "accent": v_th.get("accent", th["accent"]), "text": v_th.get("text", th["text"]),
                "font": v_th.get("font", th["font"]), "backdrop": v_th.get("backdrop", th["backdrop"]),
                "custom_css": (v_th.get("custom_css", "") + "\n" + credit_tag).strip(),
            })
            st.session_state.lex_theme = th
            save_profile_to_cloud()
            st.toast(f"Remixed {vp.get('handle', '')}'s layout with credit badge!")
            st.rerun()

    if v_th.get("vibe_sticker"):
        v_stk = v_th["vibe_sticker"] if v_th["vibe_sticker"].startswith("data:") else normalize_gif_url(v_th["vibe_sticker"])
        st.markdown(f'<div class="lex-card" style="text-align:center;"><img src="{v_stk}" style="max-width:100%;max-height:220px;border-radius:10px;" /></div>', unsafe_allow_html=True)
    ac1, ac2, ac3, ac4, ac5 = st.columns([0.22, 0.30, 0.20, 0.14, 0.14])
    is_fol = vp.get("handle") in (th.get("following") or [])
    if ac1.button("✓ Following" if is_fol else "⚡ Follow", use_container_width=True):
        toggle_follow_user(user["handle"], vp["handle"])
        st.rerun()
    is_fr = any(f["handle"].lower() == vp.get("handle", "").lower() for f in st.session_state.lex_friends)
    is_sent = vp.get("handle", "").lower() in {str(x).lower() for x in (th.get("sent_requests") or [])}
    inc_match = next((x for x in (th.get("incoming_requests") or []) if isinstance(x, dict) and x.get("handle", "").lower() == vp.get("handle", "").lower()), None)
    if is_fr:
        ac2.button("✓ Friends", disabled=True, use_container_width=True)
    elif inc_match:
        sub1, sub2 = ac2.columns(2)
        if sub1.button("✓ Accept", key="pub_acc_req", use_container_width=True):
            accept_friend_request(inc_match)
            st.rerun()
        if sub2.button("✕ Decline", key="pub_dec_req", use_container_width=True):
            decline_friend_request(vp["handle"])
            st.rerun()
    elif is_sent:
        if ac2.button("✕ Cancel Request", key="pub_can_req", use_container_width=True):
            cancel_friend_request(vp["handle"])
            st.rerun()
        if bool(v_th.get("is_private", False)) and not is_fr and not is_founder:
            st.markdown('<div class="lex-card" style="text-align:center;padding:24px;"><div style="font-size:28px;">🔒</div><div style="font-weight:800;font-size:16px;margin-top:6px;">This Profile is Private</div><div style="font-size:13px;opacity:0.8;margin-top:4px;">Send a friend request above to view their bio, Top 8, and guestbook wall.</div></div>', unsafe_allow_html=True)
            st.stop()
    elif len(st.session_state.lex_friends) >= MAX_FRIENDS:
        ac2.button(f"Max {MAX_FRIENDS}", disabled=True, use_container_width=True)
    elif ac2.button("+ Add Friend", key="pub_add_fr", use_container_width=True):
        send_friend_request(vp["handle"])
        st.toast(f"Friend request sent to {vp['handle']}!")
        st.rerun()
    if ac3.button("✉️ Message", key=f"pub_msg_{vp['handle']}", use_container_width=True):
        st.session_state.dm_target_override = vp["handle"]
        st.session_state.viewing_handle = None
        st.rerun()
    if ac4.button("🚫 Block", key=f"pub_blk_{vp['handle']}", use_container_width=True):
        block_or_report_member(vp["handle"], "block")
        st.session_state.viewing_handle = None
        st.rerun()
    if ac5.button("🚩 Report", key=f"pub_rep_{vp['handle']}", use_container_width=True):
        block_or_report_member(vp["handle"], "report", "Reported from Public Profile")
        st.toast(f"Reported {vp['handle']}")
    if vp.get("custom_song_url"):
        render_popular_song_embed(vp["custom_song_url"])
    v_pl = list(v_th.get("yt_playlist") or [])
    if v_pl:
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{v_th["accent"]};">🎧 {vp.get("display_name", "")}\'s Audio Playlist</strong></div>', unsafe_allow_html=True)
        for idx_vp, vtr in enumerate(v_pl):
            if st.button(f"▶ {vtr.get('title', 'Track')}", key=f"vpl_btn_{idx_vp}"):
                st.session_state.active_yt_track = vtr
        if st.session_state.active_yt_track:
            render_mini_yt_audio_bar(st.session_state.active_yt_track.get("yt_id", ""), st.session_state.active_yt_track.get("title", ""), v_th["accent"])
    v_top8 = vp.get("top8_json") or []
    if v_top8:
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{v_th["accent"]};">✦ {vp.get("display_name", "")}\'s Top 8</strong></div>', unsafe_allow_html=True)
        vt_cols = st.columns(4)
        for i_vt, vfr in enumerate(v_top8[:8]):
            vt_cols[i_vt % 4].markdown(friend_card_html(vfr, "👑 #1" if i_vt == 0 else f"#{i_vt + 1}", v_th), unsafe_allow_html=True)
    v_albs = list(vtj.get("albums") or [])
    if v_albs:
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{v_th["accent"]};">📸 {vp.get("display_name", "")}\'s Featured Albums</strong></div>', unsafe_allow_html=True)
        va_pick = st.selectbox("View Album", [a["title"] for a in v_albs], key="pub_alb_sel")
        va_obj = next((a for a in v_albs if a["title"] == va_pick), {})
        va_cols = st.columns(3)
        for idx_p, ph in enumerate(va_obj.get("photos") or []):
            va_cols[idx_p % 3].markdown(f'<div class="lex-card" style="padding:6px;"><img src="{ph["img"]}" style="width:100%;height:150px;object-fit:cover;border-radius:8px;" /><div style="font-size:11px;margin-top:4px;">{ph.get("caption","")}</div></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{v_th["accent"]};">💬 Sign {vp.get("display_name", "")}\'s Wall</strong></div>', unsafe_allow_html=True)
    vw_msg = st.text_input("Leave a guestbook note...", key="pub_wall_in")
    if st.button("Post to Wall ✦", key="pub_wall_btn") and vw_msg.strip():
        ok_vw, msg_vw = check_safety_and_dress_code(vw_msg)
        if not ok_vw:
            st.error(msg_vw)
        else:
            cur_vw = list(vp.get("wall_json") or [])
            cur_vw.insert(0, {"sender": user["handle"], "msg": vw_msg.strip()})
            sb.table("lex_profiles").update({"wall_json": cur_vw}).eq("user_id", vp["user_id"]).execute()
            st.rerun()
    for vw in (vp.get("wall_json") or [])[:8]:
        st.markdown(f'<div class="lex-card"><strong>{vw["sender"]}:</strong> {vw["msg"]}</div>', unsafe_allow_html=True)
    st.stop()
b_html = build_live_banner_html(th.get("banner_live", "None"), th.get("banner_img", ""), th["accent"], rad_px)
if b_html:
    st.markdown(b_html, unsafe_allow_html=True)
if th.get("marquee_on") and th.get("marquee_text"):
    st.markdown(f'<div class="lex-card" style="padding:6px 12px;"><marquee style="color:{th["accent"]};font-weight:800;letter-spacing:0.06em;">{th["marquee_text"]}</marquee></div>', unsafe_allow_html=True)

def render_profile_module(mod_name: str):
    if mod_name == "Profile Card":
        my_fol = list(th.get("followers") or [])
        my_av = render_avatar_html(user.get("avatar", ""), user.get("name", "M"), th, 76)
        is_owner = user.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"}
        my_site = founder_studio_link_html(user.get("handle", ""), th["accent"])
        my_ints = [(lbl, th.get(k, "")) for lbl, k in [("General", "int_general"), ("Music", "int_music"), ("Movies", "int_movies"), ("Books", "int_books")] if th.get(k, "")]
        my_int_html = "".join([f'<div style="font-size:12px;margin-top:4px;"><strong>{lbl}:</strong> {val}</div>' for lbl, val in my_ints])
        home_h = f'<div style="margin-top:4px;font-size:12px;opacity:0.85;">&#128205; From <strong>{th.get("hometown")}</strong></div>' if th.get("hometown") else ""
        bio_h = f'{home_h}<div style="margin-top:10px;font-size:13px;">{user.get("bio")}</div>' if user.get("bio") else home_h


        st.markdown(f'<div class="lex-card"><div style="display:flex;align-items:center;gap:14px;">{my_av}<div><div style="font-size:20px;font-weight:900;">{user.get("name","Member")}</div><div style="color:{th["accent"]};font-weight:700;">{user.get("handle","@Member")}</div>{founder_badge_html(user.get("handle",""))}{my_site}<div style="font-size:12px;opacity:0.75;margin-top:4px;">{user.get("mood","Online Now")} • {len(my_fol)} Followers</div></div></div>{bio_h}{my_int_html}</div>', unsafe_allow_html=True)

        vis_list = th.get("visitors", [])
        vis_html = "".join([f'<span style="display:inline-block;padding:4px 10px;margin:3px;border-radius:99px;background:rgba(255,255,255,0.08);font-size:12px;">{v}</span>' for v in vis_list[-12:]]) or '<span style="opacity:0.6;font-size:12px;">No recent profile visitors yet.</span>'
        st.markdown(f'<div class="lex-card"><strong>👀 Recent Profile Visitors</strong><div style="margin-top:8px;">{vis_html}</div></div>', unsafe_allow_html=True)
        c_acc = th.get("accent", "#94A3B8")
        c_bg = th.get("card_bg", "rgba(15,23,42,0.92)")
        av_s = user.get("avatar", "")
        av_t = f'<img src="{av_s}" style="width:64px;height:64px;border-radius:14px;object-fit:cover;border:2px solid {c_acc};">' if av_s else f'<div style="width:64px;height:64px;border-radius:14px;background:rgba(255,255,255,0.08);border:2px solid {c_acc};display:flex;align-items:center;justify-content:center;font-weight:900;font-size:24px;color:{c_acc};">{user.get("name","M")[:1].upper()}</div>'
        card_tier = "FOUNDER" if is_owner else "MEMBER"
        if not is_owner and sb:
            try:
                first_100 = sb.table("lex_profiles").select("handle").order("created_at", desc=False).limit(100).execute().data or []
                handles_100 = ["@" + clean_handle_str(r.get("handle", "")).lower() for r in first_100]
                cur_h_l = "@" + clean_handle_str(user.get("handle", "")).lower()
                if cur_h_l in handles_100:
                    card_tier = f"FOUNDING MEMBER #{handles_100.index(cur_h_l) + 1}/100"
            except Exception:
                pass
        _sc_open = st.session_state.get("lex_share_card_open", True)
        _sc_lbl = "▲ Collapse Share Card" if _sc_open else "🪪 Show Share Card"
        if st.button(_sc_lbl, key="toggle_share_card_btn"):
            st.session_state["lex_share_card_open"] = not _sc_open
            st.rerun()
        if _sc_open:
            _sc_bg = th.get("bg") or th.get("bg_color") or "#0F172A"
            _sc_ac = th.get("accent") or th.get("accent_color") or "#38BDF8"
            st.markdown(
                f'<div style="padding:18px;border-radius:18px;background:linear-gradient(135deg,#0B0F1A,{_sc_bg});border:2px solid {_sc_ac};box-shadow:0 0 24px {_sc_ac}44;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;"><span style="font-weight:900;font-size:15px;color:{_sc_ac};">LeX // SOCIAL</span><span style="font-size:10px;padding:3px 8px;border-radius:99px;background:{_sc_ac}22;color:{_sc_ac};font-weight:800;">{card_tier}</span></div>'
                f'<div style="display:flex;align-items:center;gap:12px;">{av_t}<div><div style="font-weight:900;font-size:18px;color:#FFF;">{user.get("name")}</div><div style="color:{_sc_ac};font-weight:700;font-size:13px;">{user.get("handle")}</div></div></div>'
                f'<div style="margin-top:12px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.1);display:flex;justify-content:space-between;font-size:11px;color:#A1A1AA;"><span>lexsocial.streamlit.app</span><span>{user.get("mood")}</span></div></div>',
                unsafe_allow_html=True,
            )
            st.code(f"Add me on LeX Social ({user.get('handle')}) — https://lexsocial.streamlit.app", language=None)

    elif mod_name == "Vibe Sticker" and th.get("vibe_sticker"):
        my_stk = th["vibe_sticker"] if th["vibe_sticker"].startswith("data:") else normalize_gif_url(th["vibe_sticker"])
        st.markdown(f'<div class="lex-card" style="text-align:center;"><img src="{my_stk}" style="max-width:100%;max-height:220px;border-radius:10px;" /></div>', unsafe_allow_html=True)
    elif mod_name == "Profile Song / Playlist":
        if user.get("custom_song_url"):
            render_popular_song_embed(user["custom_song_url"])
        elif user.get("anthem"):
            wav_bytes = generate_anthem_wav(user["anthem"])
            if wav_bytes:
                st.audio(wav_bytes, format="audio/wav")
        my_pl = list(th.get("yt_playlist") or [])
        if my_pl:
            st.markdown(f'<div class="lex-card" style="padding:10px 14px;"><strong style="color:{th["accent"]};">🎧 My Audio-Only Playlist</strong></div>', unsafe_allow_html=True)
            for idx_mp, mtr in enumerate(my_pl):
                if st.button(f"▶ {mtr.get('title', 'Track')}", key=f"mpl_btn_{idx_mp}"):
                    st.session_state.active_yt_track = mtr
            if st.session_state.active_yt_track:
                render_mini_yt_audio_bar(st.session_state.active_yt_track.get("yt_id", ""), st.session_state.active_yt_track.get("title", ""), th["accent"])
    elif mod_name == "Photo Albums" and th.get("albums"):
        my_albs = list(th.get("albums") or [])
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;"><strong style="color:{th["accent"]};">📸 My Featured Albums</strong></div>', unsafe_allow_html=True)
        ma_pick = st.selectbox("Select Album", [a["title"] for a in my_albs], key="own_alb_sel")
        ma_obj = next((a for a in my_albs if a["title"] == ma_pick), {})
        ma_cols = st.columns(2)
        for idx_ap, aph in enumerate(ma_obj.get("photos") or []):
            ma_cols[idx_ap % 2].markdown(f'<div class="lex-card" style="padding:6px;"><img src="{aph["img"]}" style="width:100%;height:120px;object-fit:cover;border-radius:8px;" /><div style="font-size:11px;margin-top:4px;">{aph.get("caption","")}</div></div>', unsafe_allow_html=True)
    elif mod_name == "Guestbook Wall":
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;"><strong style="color:{th["accent"]};">💬 My Guestbook Wall</strong></div>', unsafe_allow_html=True)
        w_in = st.text_input("Post a note on your wall...", key="own_wall_in")
        if st.button("Post Wall Note ✦", key="own_wall_btn") and w_in.strip():
            ok_w, msg_w = check_safety_and_dress_code(w_in)
            if not ok_w:
                st.error(msg_w)
            else:
                st.session_state.lex_wall.insert(0, {"sender": user["handle"], "msg": w_in.strip()})
                save_profile_to_cloud()
                st.rerun()
        for w_item in (st.session_state.lex_wall or [])[:8]:
            my_aux = list(th.get("guest_queue") or [])
        if my_aux:
            st.markdown(f'<div class="lex-card" style="padding:10px 14px;"><strong style="color:{th["accent"]};">🎶 Friends\' Pass-the-Aux Queue ({len(my_aux)})</strong></div>', unsafe_allow_html=True)
            for idx_ma, max_tr in enumerate(my_aux[-8:]):
                if st.button(f"▶ {max_tr.get('title', 'Track')} (from {max_tr.get('by', '@Friend')})", key=f"myax_btn_{idx_ma}"):
                    st.session_state.active_yt_track = max_tr
        all_my_sp = list(th.get("scrapbook_photos") or [])
        approved_sp = [s for s in all_my_sp if s.get("approved", True)]
        pending_sp = [s for s in all_my_sp if not s.get("approved", True)]
        if approved_sp or pending_sp:
            st.markdown(f'<div class="lex-card" style="padding:10px 14px;"><strong style="color:{th["accent"]};">🎞️ My Collaborative Scrapbook ({len(approved_sp)} Live • {len(pending_sp)} Pending)</strong></div>', unsafe_allow_html=True)
            if approved_sp:
                msc_cols = st.columns(2)
                for idx_ms, msp in enumerate(approved_sp[-12:]):
                    msc_cols[idx_ms % 2].markdown(f'<div class="lex-card" style="padding:6px;"><img src="{msp["img"]}" style="width:100%;height:120px;object-fit:cover;border-radius:8px;" /><div style="font-size:11px;margin-top:4px;"><strong>{msp.get("by","@Friend")}:</strong> {msp.get("caption","")}</div></div>', unsafe_allow_html=True)
            for idx_pd, psp in enumerate(pending_sp):
                st.image(psp["img"], caption=f"Pending from {psp.get('by','@Friend')}: {psp.get('caption','')}", width=180)
                ap_c1, ap_c2 = st.columns(2)
                if ap_c1.button("✓ Approve Photo", key=f"app_sp_{idx_pd}"):
                    psp["approved"] = True
                    th["scrapbook_photos"] = all_my_sp
                    save_profile_to_cloud()
                    st.rerun()
                if ap_c2.button("✕ Reject", key=f"rej_sp_{idx_pd}"):
                    all_my_sp.remove(psp)
                    th["scrapbook_photos"] = all_my_sp
                    save_profile_to_cloud()
                    st.rerun()
    elif mod_name == "Pinned Bulletin" and th.get("pinned_note"):
        st.markdown(f'<div class="lex-card" style="border-width:2.5px;"><span style="color:{th["accent"]};font-weight:900;font-size:11px;">📌 PINNED BULLETIN</span><div style="margin-top:4px;">{th["pinned_note"]}</div></div>', unsafe_allow_html=True)
    elif mod_name == "Top 8" and st.session_state.lex_top8:
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{th["accent"]};">✦ {user.get("name", "")}\'s Top 8</strong></div>', unsafe_allow_html=True)
        t8_top_cols = st.columns(4)
        for i_t8, fr8 in enumerate(st.session_state.lex_top8[:8]):
            t8_top_cols[i_t8 % 4].markdown(friend_card_html(fr8, "👑 #1" if i_t8 == 0 else f"#{i_t8 + 1}", th), unsafe_allow_html=True)

active_left = list(th.get("left_blocks") or ["Profile Card", "Vibe Sticker", "Profile Song / Playlist", "Photo Albums", "Guestbook Wall"])
active_right = list(th.get("right_blocks") or ["Pinned Bulletin", "Top 8", "Social Hub"])
if "Social Hub" not in active_left and "Social Hub" not in active_right:
    active_right.append("Social Hub")

col_left, col_right = st.columns([1.05, 1.95], gap="large")
with col_left:
    for m_name in active_left:
        if m_name != "Social Hub":
            render_profile_module(m_name)
with col_right:
    for m_name in active_right:
        if m_name != "Social Hub":
            render_profile_module(m_name)

hub_col = col_left if "Social Hub" in active_left else col_right
with hub_col:
    t_feed, t_ffeed, t_friends, t_dm, t_top8, t_studio, t_radar = st.tabs([
        "📝 My Feed", "👯 Friends Feed", "👥 All Friends", "✉️ Messages", "✦ Top 8", "🎨 LeX Studio", "📡 Radar"
    ])
    with t_feed:
        with st.form("feed_post_form", clear_on_submit=True):
            new_post = st.text_area("Share a status update, photo, or link... (Fully clothed & respectful only)", height=68)
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
                    init_meta = {"rx": {"🔥": {}, "💖": {}, "🎸": {}, "💀": {}}, "comments": []}
                    packed = pack_post_blob(new_post, normalize_url(post_link) if post_link.strip() else "", encode_image_data_url(post_img) if post_img is not None else "", init_meta)
                    sb.table("lex_posts").insert({"handle": user["handle"], "author": user["name"], "body": packed, "likes": 0}).execute()
                    st.rerun()
                blocked_set = get_blocked_handles()
        posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(80).execute().data or [] if sb else []
        my_h_low = "@" + clean_handle_str(user["handle"]).lower()
        friend_handles = set()
        for _fr in (st.session_state.lex_friends or []) + (st.session_state.lex_top8 or []):
            _fh = _fr if isinstance(_fr, str) else (_fr.get("handle") or _fr.get("friend_handle") or "" if isinstance(_fr, dict) else "")
            if _fh.strip():
                friend_handles.add("@" + clean_handle_str(_fh).lower())
        friend_handles.discard(my_h_low)
        if sb and not friend_handles:
            try:
                _db_fr = sb.table("lex_friends").select("*").or_(f"user_handle.ilike.{my_h_low},friend_handle.ilike.{my_h_low}").execute().data or []
                for _row in _db_fr:
                    for _col in ("user_handle", "friend_handle", "handle"):
                        if _row.get(_col):
                            _cand = "@" + clean_handle_str(_row[_col]).lower()
                            if _cand != my_h_low:
                                friend_handles.add(_cand)
            except Exception:
                pass
                
        def render_feed_post(p: dict, k_pfx: str):
            p_author_h = (p.get("handle") or "").strip()
            clean_txt, lnk_src, img_src, p_meta = parse_post_blob(p.get("body"))
            img_tag = f'<img src="{img_src}" style="width:100%;max-height:360px;object-fit:cover;border-radius:10px;margin-top:8px;" />' if img_src else ""
            lnk_tag = f'<div style="margin-top:8px;"><a href="{lnk_src}" target="_blank" style="color:{th["accent"]};font-weight:800;">🔗 {lnk_src}</a></div>' if lnk_src else ""
            st.markdown(f'<div class="lex-card"><strong>{p["author"]}</strong> <span style="color:{th["accent"]};font-size:12px;">{p_author_h}</span><div style="margin-top:6px;">{clean_txt}</div>{img_tag}{lnk_tag}</div>', unsafe_allow_html=True)
            rx_map = p_meta["rx"]
            cm_list = p_meta["comments"]
            rcols = st.columns(7)
            for idx_e, emo in enumerate(["🔥", "💖", "🎸", "💀"]):
                emo_users = rx_map.get(emo) or {}
                cnt_e = sum(int(v) if isinstance(v, int) else 1 for v in emo_users.values())
                i_reacted = my_h_low in {str(k).lower() for k in emo_users.keys()}
                lbl_e = f"{emo} {cnt_e} ✓" if i_reacted else f"{emo} {cnt_e}"
                if rcols[idx_e].button(lbl_e, key=f"{k_pfx}_b_{p['id']}_{emo}") and sb:
                    existing_k = next((k for k in emo_users.keys() if str(k).lower() == my_h_low), None)
                    if existing_k:
                        emo_users.pop(existing_k, None)
                    else:
                        emo_users[user["handle"]] = 1
                        push_activity_notif(p_author_h, user["handle"], "react", emo)
                    rx_map[emo] = emo_users
                    p_meta["rx"] = rx_map
                    fire_total = sum(int(v) if isinstance(v, int) else 1 for v in (rx_map.get("🔥") or {}).values())
                    sb.table("lex_posts").update({"body": pack_post_blob(clean_txt, lnk_src, img_src, p_meta), "fires": fire_total}).eq("id", p["id"]).execute()
                    st.rerun()
            c_open_key = f"{k_pfx}_open_cm_{p['id']}"
            if rcols[4].button(f"💬 {len(cm_list)}", key=f"{k_pfx}_cbtn_{p['id']}"):
                st.session_state[c_open_key] = not st.session_state.get(c_open_key, False)
                st.rerun()
            if ("@" + clean_handle_str(p_author_h).lower()) != my_h_low:
                if rcols[5].button("🚩 Report", key=f"{k_pfx}_rep_p_{p['id']}"):
                    block_or_report_member(p_author_h, "report", f"Reported post #{p['id']}")
                    st.toast("Reported post to LeX Safety")
            else:
                with rcols[5].popover("✏️"):
                    new_ed_txt = st.text_area("Edit post text", value=clean_txt, key=f"{k_pfx}_ed_{p['id']}")
                    if st.button("💾 Save Edit", key=f"{k_pfx}_sv_ed_{p['id']}"):
                        ok_e, msg_e = check_safety_and_dress_code(new_ed_txt)
                        if not ok_e:
                            st.error(msg_e)
                        else:
                            sb.table("lex_posts").update({"body": pack_post_blob(new_ed_txt, lnk_src, img_src, p_meta)}).eq("id", p["id"]).execute()
                            st.rerun()
            if rcols[6].button("🗑️", key=f"{k_pfx}_del_p_{p['id']}") and sb:
                sb.table("lex_posts").delete().eq("id", p["id"]).execute()
                st.rerun()
            if st.session_state.get(c_open_key, False) or cm_list:
                with st.expander(f"💬 Comments ({len(cm_list)})", expanded=st.session_state.get(c_open_key, False)):
                    for cm in cm_list[-20:]:
                        st.markdown(f'<div style="padding:6px 10px;border-left:2px solid {th["accent"]};margin-bottom:4px;"><strong>{cm.get("author","Member")}:</strong> {cm.get("text","")}</div>', unsafe_allow_html=True)
                    with st.form(f"{k_pfx}_cm_form_{p['id']}", clear_on_submit=True):
                        c_in = st.text_input("Write a comment...", key=f"{k_pfx}_cin_{p['id']}")
                        if st.form_submit_button("Post Comment +") and c_in.strip() and sb:
                            ok_c, msg_c = check_safety_and_dress_code(c_in)
                            if not ok_c:
                                st.error(msg_c)
                            else:
                                cm_list.append({"author": user["handle"], "text": c_in.strip()[:280]})
                                p_meta["comments"] = cm_list
                                sb.table("lex_posts").update({"body": pack_post_blob(clean_txt, lnk_src, img_src, p_meta)}).eq("id", p["id"]).execute()
                                push_activity_notif(p_author_h, user["handle"], "comment", c_in.strip()[:80])
                                st.session_state[c_open_key] = True
                                st.rerun()

        my_posts = [p for p in posts if ("@" + clean_handle_str(p.get("handle") or "").lower()) == my_h_low]
        if not my_posts:
            st.caption("No status updates from you yet — post your first one above!")
        for p in my_posts:
            render_feed_post(p, "my")

    with t_ffeed:
        _ff_blocked = get_blocked_handles()
        _ff_my_h = "@" + clean_handle_str(user.get("handle") or "").lower()
        _ff_handles = set()
        for _fr in (st.session_state.get("lex_friends") or []) + (st.session_state.get("lex_top8") or []):
            _fh = _fr if isinstance(_fr, str) else (_fr.get("handle") or _fr.get("friend_handle") or "" if isinstance(_fr, dict) else "")
            if _fh.strip():
                _ff_handles.add("@" + clean_handle_str(_fh).lower())
        _ff_handles.discard(_ff_my_h)
        _ff_posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(80).execute().data or [] if sb else []
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{th["accent"]};">👯 Friends-Only Feed</strong><div style="font-size:12px;opacity:0.8;">Showing posts exclusively from your {len(_ff_handles)} accepted friends.</div></div>', unsafe_allow_html=True)
        fr_posts = [p for p in _ff_posts if ("@" + clean_handle_str(p.get("handle") or "").lower()) in _ff_handles and ("@" + clean_handle_str(p.get("handle") or "").lower()) not in _ff_blocked]
        if not fr_posts:
            st.info("No posts from your accepted friends yet! Add friends in Radar or All Friends to see their updates here.")
        for p in fr_posts:
            render_feed_post(p, "fr")

    with t_friends:
        inc_reqs = list(th.get("incoming_requests") or [])
        sent_reqs = list(th.get("sent_requests") or [])
        blk_users = list(th.get("blocked_users") or [])
        with st.expander(f"⚙️ Requests & Blocked Manager ({len(inc_reqs)} Incoming • {len(sent_reqs)} Sent • {len(blk_users)} Blocked)", expanded=bool(inc_reqs)):
            mgr_pick = st.selectbox("Select Manager View", ["📩 Pending Friend Requests", "⏳ Sent Friend Requests", "🚫 Blocked Users List"], key="fr_mgr_sel")
            if mgr_pick == "📩 Pending Friend Requests":
                if not inc_reqs:
                    st.caption("No incoming friend requests right now.")
                for rq in inc_reqs:
                    rq_h = rq.get("handle", "")
                    rc1, rc2, rc3, rc4 = st.columns([2.4, 1, 1, 1])
                    rc1.markdown(f"**{rq.get('name', rq_h)}** `{rq_h}`")
                    if rc2.button("✓ Accept", key=f"acc_{rq_h}"):
                        accept_friend_request(rq)
                        st.rerun()
                    if rc3.button("✕ Decline", key=f"dec_{rq_h}"):
                        decline_friend_request(rq_h)
                        st.rerun()
                    if rc4.button("👁️ View", key=f"vw_inc_{rq_h}"):
                        st.session_state.viewing_handle = rq_h
                        st.rerun()
            elif mgr_pick == "⏳ Sent Friend Requests":
                if not sent_reqs:
                    st.caption("No pending sent friend requests.")
                for sq_h in sent_reqs:
                    sc1, sc2, sc3 = st.columns([2.8, 1.2, 1])
                    sc1.markdown(f"⏳ `{sq_h}`")
                    if sc2.button("✕ Cancel", key=f"can_{sq_h}"):
                        cancel_friend_request(sq_h)
                        st.rerun()
                    if sc3.button("👁️ View", key=f"vw_snt_{sq_h}"):
                        st.session_state.viewing_handle = sq_h
                        st.rerun()
            else:
                if not blk_users:
                    st.caption("Your blocked users list is empty.")
                for bh in blk_users:
                    bc1, bc2 = st.columns([3.4, 1.6])
                    bc1.markdown(f"🚫 `{bh}`")
                    if bc2.button("🔓 Unblock", key=f"unblk_{bh}"):
                        th["blocked_users"] = [x for x in blk_users if str(x).lower() != str(bh).lower()]
                        save_profile_to_cloud()
                        st.rerun()
        st.markdown(f"**👥 All Friends ({len(st.session_state.lex_friends)} / {MAX_FRIENDS})**")
        fcols = st.columns(3)
        for idx_f, fr in enumerate(st.session_state.lex_friends):
            fh = fr.get("handle", "")
            with fcols[idx_f % 3]:
                st.markdown(friend_card_html(fr, "✓ Friend", th), unsafe_allow_html=True)
                fb1, fb2 = st.columns(2)
                if fb1.button("👁️ Profile", key=f"fp_{fh}_{idx_f}"):
                    st.session_state.viewing_handle = fh
                    st.rerun()
                if fb2.button("✉️ Message", key=f"fdm_{fh}_{idx_f}"):
                    st.session_state.dm_target_override = fh
                    st.toast(f"Selected {fh} in Messages tab!")
    with t_dm:
        if sb and user and user.get("handle"):
            try:
                im_rows = sb.table("lex_profiles").select("handle, display_name, theme_json").limit(150).execute().data or []
                im_blk = get_blocked_handles()
                im_peers, im_avs = {}, {}
                for mr in im_rows:
                    mh = "@" + clean_handle_str(mr.get("handle", ""))
                    if len(mh) > 1 and mh.lower() != user["handle"].lower() and mh.lower() not in im_blk:
                        im_peers[mh] = f"{mr.get('display_name', mh)} ({mh})"
                        mtj = mr.get("theme_json") or {}
                        if isinstance(mtj, str):
                            try: mtj = json.loads(mtj or "{}")
                            except Exception: mtj = {}
                        im_avs[mh] = mtj.get("avatar", "") if isinstance(mtj, dict) else ""
                if im_peers:
                    im_list = list(im_peers.keys())
                    im_act = st.session_state.get("lex_im_peer")
                    if im_act not in im_peers:
                        im_act = im_list[0]
                        st.session_state["lex_im_peer"] = im_act
                    im_msgs = sb.table("lex_messages").select("*").order("id", desc=False).limit(300).execute().data or []
                    my_l, tg_l = user["handle"].lower(), im_act.lower()
                    im_thread = [
                        m for m in im_msgs
                        if not (m.get("body") or "").startswith(("[LEX_F", "[LEX_NOTIF]"))
                        and {str(m.get("sender_handle", "")).lower(), str(m.get("recipient_handle", "")).lower()} == {my_l, tg_l}
                    ]
                    av_u = im_avs.get(im_act, "")
                    av_h = f'<img src="{av_u}" style="width:36px;height:36px;border-radius:6px;object-fit:cover;border:1.5px solid {th["accent"]};">' if av_u else f'<div style="width:36px;height:36px;border-radius:6px;background:rgba(255,255,255,0.12);display:flex;align-items:center;justify-content:center;font-weight:900;">{im_act.lstrip("@")[:1].upper()}</div>'
                    rows_h = "".join([
                        f'<div style="margin-bottom:4px;font-size:12px;line-height:1.35;"><strong style="color:{th["accent"] if str(m.get("sender_handle","")).lower()==my_l else "#34D399"};">{user["handle"] if str(m.get("sender_handle","")).lower()==my_l else im_act}:</strong> <span>{m.get("body","")}</span></div>'
                        for m in im_thread[-30:]
                    ]) or '<div style="opacity:0.55;font-size:12px;padding:38px 8px;text-align:center;">No messages yet — say hey below! ⚡</div>'
                    win_html = (
                        f'<div id="lex-im-win" style="position:fixed;bottom:16px;right:16px;width:310px;z-index:99999;border-radius:10px;overflow:hidden;border:1.5px solid {th["accent"]};background:#0B0F1A;color:#F8FAFC;box-shadow:0 12px 32px rgba(0,0,0,0.75);font-family:sans-serif;">'
                        f'<div id="lex-im-bar" style="cursor:move;padding:6px 10px;background:linear-gradient(90deg,{th["accent"]},#1E293B);color:#06060A;font-weight:900;font-size:12px;display:flex;justify-content:space-between;align-items:center;user-select:none;">'
                        f'<span>⚡ {im_act} — LeX Instant</span>'
                        f'<span id="lex-im-min" style="cursor:pointer;padding:0 6px;font-size:14px;font-weight:900;">_</span></div>'
                        f'<div id="lex-im-body">'
                        f'<div style="padding:8px 10px;background:rgba(255,255,255,0.04);border-bottom:1px solid rgba(255,255,255,0.1);display:flex;align-items:center;gap:8px;">{av_h}<div><div style="font-weight:800;font-size:13px;">{im_peers.get(im_act, im_act)}</div><div style="font-size:10px;color:#34D399;">● Online • LeX Instant</div></div></div>'
                        f'<div id="lex-im-log" style="height:175px;overflow-y:auto;padding:8px 10px;background:#070A12;">{rows_h}</div>'
                        f'</div></div>'
                    )
                    st.markdown(win_html, unsafe_allow_html=True)
                    st.components.v1.html(
                        "<" + "script>"
                        + "const p=window.parent.document,w=p.getElementById('lex-im-win'),b=p.getElementById('lex-im-bar'),m=p.getElementById('lex-im-min'),bd=p.getElementById('lex-im-body'),lg=p.getElementById('lex-im-log');"
                        + "if(lg){lg.scrollTop=lg.scrollHeight;}"
                        + "if(m&&bd){m.onclick=()=>{bd.style.display=bd.style.display==='none'?'block':'none';};}"
                        + "if(w&&b){let dx=0,dy=0,drag=false;b.onmousedown=(e)=>{drag=true;dx=e.clientX-w.offsetLeft;dy=e.clientY-w.offsetTop;};p.onmousemove=(e)=>{if(!drag)return;w.style.left=(e.clientX-dx)+'px';w.style.top=(e.clientY-dy)+'px';w.style.right='auto';w.style.bottom='auto';};p.onmouseup=()=>{drag=false;};}"
                        + "</" + "script>",
                        height=0,
                    )
                    with st.expander("⚡ LeX Instant Quick Send / Switch Friend", expanded=True):
                        c_p, c_m, c_s = st.columns([1.4, 2.4, 0.8])
                        pk = c_p.selectbox("Friend", im_list, index=im_list.index(im_act), format_func=lambda x: im_peers.get(x, x), label_visibility="collapsed", key="lex_im_sel")
                        if pk != im_act:
                            st.session_state["lex_im_peer"] = pk
                            st.rerun()
                        im_in = c_m.text_input("IM", placeholder=f"IM {im_act}...", label_visibility="collapsed", key="lex_im_txt")
                        if c_s.button("SEND", key="lex_im_go", use_container_width=True) and im_in.strip():
                            ok_i, msg_i = check_safety_and_dress_code(im_in)
                            if ok_i:
                                sb.table("lex_messages").insert({"sender_handle": user["handle"], "recipient_handle": im_act, "body": im_in.strip()}).execute()
                                st.rerun()
                            else:
                                st.error(msg_i)
            except Exception as e:
                st.warning(f"LeX Instant notice: {e}")

    with t_top8:
        st.markdown(f'<div class="lex-card" style="padding:12px 16px;"><strong style="color:{th["accent"]};font-size:16px;">✦ Manage Your Top 8 Friends ({len(st.session_state.lex_top8)} / 8)</strong></div>', unsafe_allow_html=True)
        top8_handles = {str(x.get("handle", "")).lower() for x in st.session_state.lex_top8}
        eligible = [f for f in st.session_state.lex_friends if f["handle"].lower() not in top8_handles]
        if len(st.session_state.lex_top8) < 8 and eligible:
            ac_1, ac_2 = st.columns([0.72, 0.28])
            pick_lbl = ac_1.selectbox("Choose a friend to spotlight", [f"{f.get('name', f['handle'])} ({f['handle']})" for f in eligible], key="top8_add_pick")
            if ac_2.button("+ Add to Top 8 ✦", use_container_width=True, key="top8_add_btn"):
                chosen = next((f for f in eligible if f"{f.get('name', f['handle'])} ({f['handle']})" == pick_lbl), None)
                if chosen:
                    entry = chosen.copy()
                    entry["rank"] = len(st.session_state.lex_top8) + 1
                    st.session_state.lex_top8.append(entry)
                    save_profile_to_cloud()
                    st.rerun()
        elif not eligible and len(st.session_state.lex_top8) < 8:
            st.caption("All of your current friends are already in your Top 8—or find new friends in 📡 Radar!")
        t8_cols = st.columns(4)
        for idx_8, t_fr in enumerate(list(st.session_state.lex_top8)[:8]):
            th_handle = t_fr.get("handle", "")
            with t8_cols[idx_8 % 4]:
                st.markdown(friend_card_html(t_fr, "👑 #1" if idx_8 == 0 else f"#{idx_8 + 1}", th), unsafe_allow_html=True)
                b_up, b_rm = st.columns(2)
                if idx_8 > 0 and b_up.button("👑 #1", key=f"t8_top_{th_handle}_{idx_8}", use_container_width=True):
                    cur_list = list(st.session_state.lex_top8)
                    moved = cur_list.pop(idx_8)
                    cur_list.insert(0, moved)
                    for r_i, item in enumerate(cur_list):
                        item["rank"] = r_i + 1
                    st.session_state.lex_top8 = cur_list
                    save_profile_to_cloud()
                    st.rerun()
                if b_rm.button("✕ Drop", key=f"t8_rm_{th_handle}_{idx_8}", use_container_width=True):
                    cur_list = [x for i, x in enumerate(st.session_state.lex_top8) if i != idx_8]
                    for r_i, item in enumerate(cur_list):
                        item["rank"] = r_i + 1
                    st.session_state.lex_top8 = cur_list
                    save_profile_to_cloud()
                    st.rerun()
    with t_studio:
        with st.expander("👤 Bio, Personal Info, Avatar Shape & Vibe Sticker / GIF", expanded=True):
            with st.form("studio_bio_form"):
                b_name = st.text_input("Display Name", value=user.get("name", ""))
                b_mood = st.text_input("Current Mood", value=user.get("mood", "Online Now • Vibing ⚡"))
                b_home = st.text_input("Where are you from?", value=th.get("hometown", ""), placeholder="e.g., Portsmouth, OH")
                b_priv = st.checkbox("🔒 Private Profile (Only approved friends can see your bio, Top 8 & wall)", value=bool(th.get("is_private", False)))
                ws1, ws2 = st.columns(2)
                b_site_lbl = ws1.text_input("Link Display Name (Shown on Profile)", value=th.get("website_label", ""), placeholder="e.g., My Portfolio / YouTube")
                b_site = ws2.text_input("Profile Website / Link URL", value=user.get("website") or th.get("website", ""), placeholder="https://...")
                b_bio = st.text_area("About Me (Bio)", value=user.get("bio", ""), height=90)

                b_meet = st.text_area("Who I'd Like to Meet", value=user.get("who_to_meet", ""), height=68)
                ic1, ic2 = st.columns(2)
                i_gen = ic1.text_input("General Interests", value=th.get("int_general", ""))
                i_mus = ic2.text_input("Music", value=th.get("int_music", ""))
                i_mov = ic1.text_input("Movies", value=th.get("int_movies", ""))
                i_tv = ic2.text_input("Television", value=th.get("int_tv", ""))
                i_bok = st.text_input("Books & Heroes", value=th.get("int_books", ""))
                av_c1, av_c2 = st.columns(2)
                shape_keys = list(AVATAR_SHAPES.keys())
                cur_shape = th.get("avatar_shape", "Classic Circle")
                pick_shape = av_c1.selectbox("Profile Picture Border Shape (16 Shapes)", shape_keys, index=shape_keys.index(cur_shape) if cur_shape in shape_keys else 0)
                upd_av = av_c2.file_uploader("Upload New Profile Photo", type=["png", "jpg", "jpeg", "webp"], key="upd_av_file")
                st.markdown("**✨ Vibe Box Sticker / Animated GIF (Paste URL OR Upload .gif/.png)**")
                sk1, sk2 = st.columns(2)
                cur_stk = th.get("vibe_sticker", "")
                stk_url_in = sk1.text_input("Sticker / GIF URL (Giphy link or direct .gif)", value="" if cur_stk.startswith("data:") else cur_stk)
                upd_stk = sk2.file_uploader("Or Upload Sticker / GIF File", type=["gif", "png", "jpg", "jpeg", "webp"], key="upd_stk_file")
                clr_stk = st.checkbox("Remove current Vibe Sticker / GIF")
                if st.form_submit_button("Save Profile, Bio & Sticker ✦", use_container_width=True):
                    blob_chk = f"{b_name} {b_mood} {b_home} {b_site} {b_bio} {b_meet} {i_gen} {i_mus} {i_mov} {i_tv} {i_bok} {stk_url_in}"
                    ok_b, msg_b = check_safety_and_dress_code(blob_chk)
                    ok_av, msg_av = scan_image_safely(upd_av, b_name)
                    ok_sk, msg_sk = scan_image_safely(upd_stk, "sticker")
                    if not ok_b:
                        st.error(msg_b)
                    elif not ok_av:
                        st.error(msg_av)
                    elif not ok_sk:
                        st.error(msg_sk)
                    else:
                        user["name"] = b_name.strip() or user["name"]
                        user["mood"] = b_mood.strip()
                        th["hometown"] = b_home.strip()
                        th["is_private"] = bool(b_priv)                        
                        user["website"] = normalize_url(b_site)
                        th["website"] = user["website"]
                        th["website_label"] = b_site_lbl.strip()
                        user["bio"] = b_bio.strip()
                        user["who_to_meet"] = b_meet.strip()
                        th["int_general"], th["int_music"], th["int_movies"], th["int_tv"], th["int_books"] = i_gen.strip(), i_mus.strip(), i_mov.strip(), i_tv.strip(), i_bok.strip()
                        th["avatar_shape"] = pick_shape
                        if upd_av is not None:
                            user["avatar"] = encode_image_data_url(upd_av)
                        if clr_stk:
                            th["vibe_sticker"] = ""
                        elif upd_stk is not None:
                            th["vibe_sticker"] = encode_image_data_url(upd_stk)
                        elif stk_url_in.strip():
                            th["vibe_sticker"] = normalize_gif_url(stk_url_in.strip())
                        st.session_state.lex_user = user
                        st.session_state.lex_theme = th
                        save_profile_to_cloud()
                        st.toast("Saved Profile, Bio & Sticker to Cloud ✦")
                        st.rerun()
        with st.expander("🎨 Premade Themes, Colors, Card FX, Custom Wallpapers & CSS", expanded=True):
            PRESET_THEMES = {
                "Custom (Keep Current)": None,
                "💖 2000s Scene Pink": {"bg": "#06060A", "card": "#0E0E16", "accent": "#EC4899", "text": "#F4F4F5", "font": "Girl Punk / Spray Marker", "backdrop": "Y2K Stars & Sparkles"},
                "⚡ Cyber Cobalt Matrix": {"bg": "#030712", "card": "#0B1120", "accent": "#38BDF8", "text": "#F0F9FF", "font": "Futuristic Orbitron", "backdrop": "Cyber Matrix Rain"},
                "🦇 Gothic Cathedral": {"bg": "#09050D", "card": "#140B1C", "accent": "#A855F7", "text": "#FAF5FF", "font": "Gothic Editorial", "backdrop": "Gothic Bats & Moons"},
                "🎀 Coquette Cherry Ribbon": {"bg": "#14080E", "card": "#1F0D16", "accent": "#FB7185", "text": "#FFF1F2", "font": "Clean Studio Sans", "backdrop": "Coquette Ribbon Bows"},
                "👾 Y2K Arcade Lime": {"bg": "#050A06", "card": "#0B170E", "accent": "#4ADE80", "text": "#F0FDF4", "font": "Y2K Arcade Pixel", "backdrop": "8-Bit Arcade Invaders"},
                "🔥 Hotrod Flame Gold": {"bg": "#0D0704", "card": "#1A0E08", "accent": "#F59E0B", "text": "#FFFBEB", "font": "Girl Punk / Spray Marker", "backdrop": "Flame & Hotrod Stripes"},
                "🐆 Leopard Luxe Gold": {"bg": "#0F0B07", "card": "#1C150E", "accent": "#EAB308", "text": "#FEFCE8", "font": "Gothic Editorial", "backdrop": "Leopard Rosette Print"},
                "🦋 Twilight Butterfly": {"bg": "#070914", "card": "#101429", "accent": "#818CF8", "text": "#EEF2FF", "font": "Clean Studio Sans", "backdrop": "Butterfly Dreamscape"},
                "🏁 Checkered Ska Voltage": {"bg": "#080808", "card": "#141414", "accent": "#F43F5E", "text": "#FFFFFF", "font": "Cyber Glitch", "backdrop": "Checkered Ska / Vans"},
                "💎 Crown Diamond Ice": {"bg": "#060B10", "card": "#0E1721", "accent": "#22D3EE", "text": "#ECFEFF", "font": "Futuristic Orbitron", "backdrop": "Crown & Diamond Luxe"},
                "🌹 Rose Thorn Crimson": {"bg": "#0E0507", "card": "#1A090D", "accent": "#E11D48", "text": "#FFF1F2", "font": "Gothic Editorial", "backdrop": "Rose Thorns & Petals"},
            }
            p_c1, p_c2 = st.columns([0.72, 0.28])
            picked_preset = p_c1.selectbox("⚡ Quick-Apply a Premade Vibe Theme", list(PRESET_THEMES.keys()), key="preset_th_pick")
            if p_c2.button("Apply Preset ✦", use_container_width=True, key="apply_preset_btn") and PRESET_THEMES[picked_preset]:
                th.update(PRESET_THEMES[picked_preset])
                st.session_state.lex_theme = th
                save_profile_to_cloud()
                st.toast(f"Applied {picked_preset}!")
                st.rerun()

            with st.form("studio_full_theme_form"):
                tc1, tc2, tc3, tc4 = st.columns(4)
                c_bg = tc1.color_picker("Background", th.get("bg", "#06060A"))
                c_cd = tc2.color_picker("Card Surface", th.get("card", "#0E0E16"))
                c_ac = tc3.color_picker("Neon Accent", th.get("accent", "#EC4899"))
                c_tx = tc4.color_picker("Text Color", th.get("text", "#F4F4F5"))
                f_keys = list(FONT_MAP.keys())
                s1, s2, s3 = st.columns(3)
                sel_font = s1.selectbox("Typography Font", f_keys, index=f_keys.index(th.get("font")) if th.get("font") in f_keys else 0)
                sel_bd = s2.selectbox("SVG Backdrop Pattern", BACKDROP_OPTIONS, index=BACKDROP_OPTIONS.index(th.get("backdrop")) if th.get("backdrop") in BACKDROP_OPTIONS else 0)
                spray_in = s3.text_input("Graffiti Spray Word", value=th.get("spray_word", "LeX!"))
                fx1, fx2, fx3 = st.columns(3)
                b_styles = ["solid", "dashed", "dotted", "double"]
                sel_bst = fx1.selectbox("Card Border Style", b_styles, index=b_styles.index(th.get("border_style")) if th.get("border_style") in b_styles else 0)
                rad_val = fx2.slider("Card Corner Radius (px)", 0, 32, int(th.get("card_radius", 14)))
                op_val = fx3.slider("Card Opacity (%)", 40, 100, int(th.get("card_opacity", 94)))
                an1, an2, an3, an4 = st.columns(4)
                c_keys = list(CURSOR_OPTIONS.keys())
                sel_cur = an1.selectbox("Custom Cursor", c_keys, index=c_keys.index(th.get("cursor_style")) if th.get("cursor_style") in c_keys else 0)
                sel_anim = an2.selectbox("Card Animation", CARD_ANIMATIONS, index=CARD_ANIMATIONS.index(th.get("card_anim")) if th.get("card_anim") in CARD_ANIMATIONS else 0)
                glow_b = an3.checkbox("Neon Border Glow", value=bool(th.get("glow_borders", True)))
                glow_t = an4.checkbox("Neon Text Glow", value=bool(th.get("text_glow", True)))
                up1, up2 = st.columns(2)
                wall_up = up1.file_uploader("Upload Custom Background Wallpaper", type=["png", "jpg", "jpeg", "webp", "gif"], key="th_wall_up")
                clr_wall = up1.checkbox("Remove Custom Wallpaper")
                sel_bn = up2.selectbox("Animated Live Banner", LIVE_BANNERS, index=LIVE_BANNERS.index(th.get("banner_live")) if th.get("banner_live") in LIVE_BANNERS else 0)
                ban_up = up2.file_uploader("Or Upload Custom Banner Image", type=["png", "jpg", "jpeg", "webp", "gif"], key="th_ban_up")
                clr_ban = up2.checkbox("Remove Custom Banner Image")
                mq_on = st.checkbox("Enable Scrolling Marquee Ticker", value=bool(th.get("marquee_on", False)))
                mq_txt = st.text_input("Marquee Ticker Text", value=th.get("marquee_text", ""))
                pin_txt = st.text_input("Pinned Bulletin Note", value=th.get("pinned_note", ""))
                rmx_c1, rmx_c2 = st.columns(2)
                allow_rmx = rmx_c1.checkbox("✨ Allow CSS Remix ('Steal This Look' button)", value=bool(th.get("allow_css_remix", True)))
                scrap_app = rmx_c2.checkbox("🎞️ Require Approval for Friend Scrapbook Photos", value=bool(th.get("scrapbook_require_approval", True)))
                x_css_in = st.text_area("Custom Profile CSS", value=th.get("custom_css", ""), height=68)
                with st.expander("🎨 10 Total Package CSS Themes & Color Cheat Sheet"):
                    st.caption("Pick a full-page animated layout below, tap the copy icon in the top-right corner of the box, paste it into Custom Profile CSS above, and tweak any #HEX colors to make it yours!")
                    _css_packs = {
                        "1. Liquid Mercury & Chrome Y2K (Floating Squares + Chrome Wave)": (
                            '@keyframes lexSqFloat{0%{background-position:0 0,70px 40px}100%{background-position:0 -400px,70px -580px}}\n'
                            '@keyframes lexChromeWave{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexMercuryPulse{0%,100%{border-color:#94A3B8;box-shadow:0 0 18px #94A3B877}50%{border-color:#F8FAFC;box-shadow:0 0 34px #E2E8F0dd}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#040507!important;background-image:linear-gradient(45deg,#1E293B33 25%,transparent 25%),linear-gradient(-45deg,#1E293B33 25%,transparent 25%),linear-gradient(180deg,#020305,#0D1117,#020305)!important;background-size:48px 48px,48px 48px,100% 100%!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(135deg,#F8FAFCaa 0 10px,transparent 10px),linear-gradient(135deg,#94A3B899 0 14px,transparent 14px);background-size:160px 230px,240px 320px;animation:lexSqFloat 6.5s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Trebuchet MS","Avenir Next",sans-serif!important;text-transform:uppercase!important;color:#F8FAFC!important;text-shadow:0 0 14px #E2E8F0cc!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#090B10,#334155,#94A3B8,#E2E8F0,#090B10)!important;background-size:300% 300%!important;border:2px solid #F8FAFC!important;animation:lexChromeWave 6s ease-in-out infinite,lexMercuryPulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ LIQUID MERCURY EDITION ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(15,23,42,.75)!important;border:1px solid #F8FAFC!important;color:#F8FAFC!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#06080D,#1E293B,#475569,#06080D)!important;background-size:300% 300%!important;border:2px solid #CBD5E1!important;animation:lexChromeWave 7s ease-in-out infinite,lexMercuryPulse 3.8s ease-in-out infinite!important}'
                        ),
                        "2. Inferno Ember & Molten Gold (Sunburst Beams + Gold Lava)": (
                            '@keyframes lexSunSpin{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}\n'
                            '@keyframes lexLavaFlow{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexGoldPulse{0%,100%{border-color:#F59E0B;box-shadow:0 0 18px #F59E0B88}50%{border-color:#FDE68A;box-shadow:0 0 36px #FBBF24ee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#060302!important;background-image:radial-gradient(circle at 50% 95%,#991B1B55,transparent 55%),linear-gradient(180deg,#040201,#140804,#040201)!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:-50%;pointer-events:none;z-index:0;background:repeating-conic-gradient(from 0deg,#F59E0B1A 0deg 8deg,transparent 8deg 24deg);animation:lexSunSpin 35s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Palatino Linotype",Georgia,serif!important;color:#FEF3C7!important;text-shadow:0 0 14px #F59E0Bee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#090402,#7F1D1D,#D97706,#FBBF24,#090402)!important;background-size:300% 300%!important;border:2px solid #FDE68A!important;animation:lexLavaFlow 6s ease-in-out infinite,lexGoldPulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ MOLTEN GOLD EDITION ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(120,53,15,.55)!important;border:1px solid #FDE68A!important;color:#FEF3C7!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#080402,#451A03,#B45309,#080402)!important;background-size:300% 300%!important;border:2px solid #F59E0B!important;animation:lexLavaFlow 6.5s ease-in-out infinite,lexGoldPulse 3.5s ease-in-out infinite!important}'
                        ),
                        "3. Bioluminescent Abyss & Neon Teal (Hollow Rings + Teal Tide)": (
                            '@keyframes lexRingRise{0%{background-position:0 0,80px 40px}100%{background-position:0 -400px,80px -580px}}\n'
                            '@keyframes lexTideWave{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexTealPulse{0%,100%{border-color:#14B8A6;box-shadow:0 0 18px #14B8A688}50%{border-color:#99F6E4;box-shadow:0 0 34px #2DD4BFee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#020608!important;background-image:radial-gradient(circle at 25% 20%,#0F766E44,transparent 48%),linear-gradient(180deg,#010406,#041318,#010406)!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:radial-gradient(circle,transparent 8px,#2DD4BFaa 9px,#2DD4BFaa 11px,transparent 12px),radial-gradient(circle,transparent 13px,#38BDF888 14px,#38BDF888 16px,transparent 17px);background-size:160px 230px,240px 320px;animation:lexRingRise 6.5s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Snell Roundhand","Palatino Linotype",Georgia,serif!important;color:#CCFBF1!important;text-shadow:0 0 14px #2DD4BFee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#02080A,#115E59,#0D9488,#2DD4BF,#02080A)!important;background-size:300% 300%!important;border:2px solid #99F6E4!important;animation:lexTideWave 6s ease-in-out infinite,lexTealPulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ BIOLUMINESCENT TIDE ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(13,148,136,.35)!important;border:1px solid #99F6E4!important;color:#CCFBF1!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#020709,#062B2E,#0F766E,#020709)!important;background-size:300% 300%!important;border:2px solid #14B8A6!important;animation:lexTideWave 6s ease-in-out infinite,lexTealPulse 3.5s ease-in-out infinite!important}'
                        ),
                        "4. Electric Cyan Cyber Grid (Blueprint Grid + Floating Orbs)": (
                            '@keyframes orbFloat{0%,100%{transform:translateY(0) scale(1)}50%{transform:translateY(-28px) scale(1.08)}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#020617!important;background-image:linear-gradient(#00F0FF26 2px,transparent 2px),linear-gradient(90deg,#00F0FF26 2px,transparent 2px),linear-gradient(#38BDF814 1px,transparent 1px),linear-gradient(90deg,#38BDF814 1px,transparent 1px)!important;background-size:80px 80px,80px 80px,16px 16px,16px 16px!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:radial-gradient(circle at 18% 25%,#00F0FFcc 0 6px,transparent 28px),radial-gradient(circle at 82% 20%,#3B82F6cc 0 7px,transparent 32px),radial-gradient(circle at 75% 75%,#38BDF8cc 0 6px,transparent 28px);animation:orbFloat 5s ease-in-out infinite}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(90deg,#020617,#0369A1,#00F0FF,#020617)!important;border:2px solid #7DD3FC!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:rgba(6,12,26,.86)!important;backdrop-filter:blur(14px)!important;border:1.5px solid #00F0FF!important;box-shadow:0 0 20px #00F0FF44!important}'
                        ),
                        "5. Rose Gold Champagne Shimmer (Diamond Confetti + Velvet Wave)": (
                            '@keyframes lexDiamondRise{0%{background-position:0 0,70px 50px}100%{background-position:0 -400px,70px -580px}}\n'
                            '@keyframes lexRoseWave{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexRosePulse{0%,100%{border-color:#FB7185;box-shadow:0 0 18px #FB718588}50%{border-color:#FECDD3;box-shadow:0 0 34px #FDA4AFee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#090406!important;background-image:radial-gradient(circle at 25% 20%,#BE123C44,transparent 48%),linear-gradient(180deg,#070305,#1C0910,#070305)!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(45deg,transparent 43%,#FECDD3cc 44%,#FECDD3cc 56%,transparent 57%),linear-gradient(-45deg,transparent 43%,#FB7185bb 44%,#FB7185bb 56%,transparent 57%);background-size:145px 210px,215px 300px;animation:lexDiamondRise 6s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Snell Roundhand","Palatino Linotype",Georgia,serif!important;color:#FFE4E6!important;text-shadow:0 0 14px #FB7185ee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#090406,#881337,#E11D48,#FDA4AF,#090406)!important;background-size:300% 300%!important;border:2px solid #FECDD3!important;animation:lexRoseWave 6s ease-in-out infinite,lexRosePulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ ROSE GOLD CHAMPAGNE ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(136,19,55,.45)!important;border:1px solid #FECDD3!important;color:#FFE4E6!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#0A0406,#3B0D1B,#881337,#0A0406)!important;background-size:300% 300%!important;border:2px solid #FB7185!important;animation:lexRoseWave 6s ease-in-out infinite,lexRosePulse 3.5s ease-in-out infinite!important}'
                        ),
                        "6. Emerald Toxic Matrix (Shooting Laser Rain + CRT Lines)": (
                            '@keyframes lexLaserRain{0%{background-position:0 0,60px -120px,130px -60px}100%{background-position:0 500px,60px 580px,130px 440px}}\n'
                            '@keyframes lexGreenPulse{0%,100%{border-color:#22C55E;box-shadow:0 0 18px #22C55E88}50%{border-color:#86EFAC;box-shadow:0 0 34px #4ADE80ee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#020704!important;background-image:repeating-linear-gradient(0deg,rgba(34,197,94,.07) 0 1px,transparent 1px 4px),linear-gradient(#22C55E22 1px,transparent 1px),linear-gradient(90deg,#22C55E22 1px,transparent 1px)!important;background-size:100% 4px,38px 38px,38px 38px!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(180deg,transparent,#22C55Ecc 50%,transparent),linear-gradient(180deg,transparent,#86EFAC99 50%,transparent),linear-gradient(180deg,transparent,#10B981bb 50%,transparent);background-size:2px 75px,1.5px 110px,3px 55px;background-repeat:repeat;animation:lexLaserRain 3.5s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Courier New",monospace!important;color:#DCFCE7!important;text-shadow:0 0 14px #22C55Eee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(90deg,#020704,#14532D,#16A34A,#020704)!important;border:2px solid #86EFAC!important;animation:lexGreenPulse 3.5s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ TOXIC MATRIX PROTOCOL ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(20,83,45,.65)!important;border:1px solid #86EFAC!important;color:#DCFCE7!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:rgba(3,14,8,.90)!important;border:2px solid #22C55E!important;animation:lexGreenPulse 3.5s ease-in-out infinite!important}'
                        ),
                        "7. Gothic Blood Crimson & Velvet (Drifting Ruby Squares + Obsidian Wave)": (
                            '@keyframes lexRubySq{0%{background-position:0 0,65px 35px}100%{background-position:0 380px,65px 560px}}\n'
                            '@keyframes lexCrimsonWave{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexRedPulse{0%,100%{border-color:#DC2626;box-shadow:0 0 18px #DC262688}50%{border-color:#FCA5A5;box-shadow:0 0 34px #EF4444ee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#060203!important;background-image:radial-gradient(circle at 20% 20%,#991B1B44,transparent 48%),linear-gradient(180deg,#040102,#170508,#040102)!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(135deg,#EF4444aa 0 9px,transparent 9px),linear-gradient(135deg,#991B1Bcc 0 14px,transparent 14px);background-size:150px 215px,225px 310px;animation:lexRubySq 6s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Palatino Linotype",Georgia,serif!important;color:#FEE2E2!important;text-shadow:0 0 14px #EF4444ee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#060203,#7F1D1D,#DC2626,#450A0A,#060203)!important;background-size:300% 300%!important;border:2px solid #FCA5A5!important;animation:lexCrimsonWave 6s ease-in-out infinite,lexRedPulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ CRIMSON VELVET EDITION ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(127,29,29,.55)!important;border:1px solid #FCA5A5!important;color:#FEE2E2!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#070203,#3B070B,#7F1D1D,#070203)!important;background-size:300% 300%!important;border:2px solid #DC2626!important;animation:lexCrimsonWave 6s ease-in-out infinite,lexRedPulse 3.5s ease-in-out infinite!important}'
                        ),
                        "8. Midnight Cobalt & Tactical Carbon (Diagonal Speed Bars + Steel Wave)": (
                            '@keyframes lexSlashSlide{0%{background-position:0 0}100%{background-position:280px -280px}}\n'
                            '@keyframes lexSteelWave{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexBluePulse{0%,100%{border-color:#2563EB;box-shadow:0 0 18px #2563EB88}50%{border-color:#93C5FD;box-shadow:0 0 34px #3B82F6ee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#02040A!important;background-image:repeating-linear-gradient(45deg,rgba(37,99,235,.06) 0 2px,transparent 2px 12px),linear-gradient(180deg,#02040A,#0A1530,#02040A)!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:repeating-linear-gradient(135deg,transparent 0 42px,#3B82F626 42px 46px,transparent 46px 95px,#60A5FA1F 95px 98px);background-size:280px 280px;animation:lexSlashSlide 8s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Trebuchet MS",sans-serif!important;text-transform:uppercase!important;color:#DBEAFE!important;text-shadow:0 0 14px #3B82F6ee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#02040A,#1E3A8A,#2563EB,#60A5FA,#02040A)!important;background-size:300% 300%!important;border:2px solid #93C5FD!important;animation:lexSteelWave 6s ease-in-out infinite,lexBluePulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ MIDNIGHT COBALT CARBON ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(30,58,138,.55)!important;border:1px solid #93C5FD!important;color:#DBEAFE!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#03060E,#0F2147,#1D4ED8,#03060E)!important;background-size:300% 300%!important;border:2px solid #2563EB!important;animation:lexSteelWave 6s ease-in-out infinite,lexBluePulse 3.5s ease-in-out infinite!important}'
                        ),
                        "9. Peach Sunset & Golden Hour Glow (Rising Halo Rings + Sunset Wave)": (
                            '@keyframes lexHaloRise{0%{background-position:0 0,75px 45px}100%{background-position:0 -380px,75px -560px}}\n'
                            '@keyframes lexSunsetWave{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexPeachPulse{0%,100%{border-color:#F97316;box-shadow:0 0 18px #F9731688}50%{border-color:#FED7AA;box-shadow:0 0 34px #FB923Cee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#080403!important;background-image:radial-gradient(circle at 80% 15%,#EA580C44,transparent 50%),linear-gradient(180deg,#070302,#1C0C07,#070302)!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:radial-gradient(circle,transparent 9px,#FED7AA99 10px,#FED7AA99 12px,transparent 13px),radial-gradient(circle,transparent 15px,#FB923C77 16px,#FB923C77 18px,transparent 19px);background-size:165px 235px,245px 325px;animation:lexHaloRise 6.5s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Snell Roundhand","Palatino Linotype",Georgia,serif!important;color:#FFEDD5!important;text-shadow:0 0 14px #FB923Cee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#080403,#9A3412,#EA580C,#FDBA74,#080403)!important;background-size:300% 300%!important;border:2px solid #FED7AA!important;animation:lexSunsetWave 6s ease-in-out infinite,lexPeachPulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ GOLDEN HOUR SUNSET ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(154,52,18,.55)!important;border:1px solid #FED7AA!important;color:#FFEDD5!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#090403,#431407,#9A3412,#090403)!important;background-size:300% 300%!important;border:2px solid #F97316!important;animation:lexSunsetWave 6s ease-in-out infinite,lexPeachPulse 3.5s ease-in-out infinite!important}'
                        ),
                        "10. Arctic Glacier & Diamond Ice (Falling Ice Diamonds + Frost Wave)": (
                            '@keyframes lexIceFall{0%{background-position:0 0,60px 30px}100%{background-position:0 390px,60px 570px}}\n'
                            '@keyframes lexIceWave{0%{background-position:0% 50%}50%{background-position:100% 50%}100%{background-position:0% 50%}}\n'
                            '@keyframes lexIcePulse{0%,100%{border-color:#38BDF8;box-shadow:0 0 18px #38BDF888}50%{border-color:#E0F2FE;box-shadow:0 0 34px #7DD3FCee}}\n'
                            'html body [data-testid="stAppViewContainer"]{background-color:#02060A!important;background-image:radial-gradient(circle at 20% 20%,#0284C744,transparent 50%),linear-gradient(180deg,#020508,#071926,#020508)!important}\n'
                            'html body [data-testid="stAppViewContainer"]::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(45deg,transparent 43%,#E0F2FEcc 44%,#E0F2FEcc 56%,transparent 57%),linear-gradient(-45deg,transparent 43%,#7DD3FCbb 44%,#7DD3FCbb 56%,transparent 57%);background-size:140px 205px,210px 295px;animation:lexIceFall 5.8s linear infinite}\n'
                            'html body .lex-card h1,html body .lex-card h2,html body .lex-card h3,html body h1,html body h2,html body h3{font-family:"Trebuchet MS",sans-serif!important;color:#F0F9FF!important;text-shadow:0 0 14px #7DD3FCee!important}\n'
                            'html body [data-testid="stIconMaterial"],html body .material-symbols-rounded{font-family:"Material Symbols Rounded",sans-serif!important}\n'
                            'html body .lex-banner{background:linear-gradient(115deg,#02060A,#075985,#0284C7,#BAE6FD,#02060A)!important;background-size:300% 300%!important;border:2px solid #E0F2FE!important;animation:lexIceWave 6s ease-in-out infinite,lexIcePulse 4s ease-in-out infinite!important}\n'
                            'html body .lex-banner::before{content:"✦ ARCTIC GLACIER EDITION ✦"!important;display:inline-block!important;margin-bottom:6px!important;padding:3px 12px!important;border-radius:999px!important;background:rgba(7,89,133,.55)!important;border:1px solid #E0F2FE!important;color:#F0F9FF!important;font-size:11px!important;font-weight:800!important}\n'
                            'html body .lex-card,html body .lex-friend-card{background:linear-gradient(125deg,#03070C,#082F49,#0369A1,#03070C)!important;background-size:300% 300%!important;border:2px solid #38BDF8!important;animation:lexIceWave 6s ease-in-out infinite,lexIcePulse 3.5s ease-in-out infinite!important}'
                        ),
                    }
                    _pick_pack = st.selectbox("Select a Total Package CSS Theme", list(_css_packs.keys()), key="lex_css_pack_picker")
                    st.code(_css_packs[_pick_pack], language="css")

                if st.form_submit_button("Save All Visual Customizations ✦", use_container_width=True):
                    ok_w, msg_w = scan_image_safely(wall_up, "wallpaper")
                    ok_bn, msg_bn = scan_image_safely(ban_up, "banner")
                    ok_tx, msg_tx = check_safety_and_dress_code(f"{spray_in} {mq_txt} {pin_txt}")
                    if not ok_w:
                        st.error(msg_w)
                    elif not ok_bn:
                        st.error(msg_bn)
                    elif not ok_tx:
                        st.error(msg_tx)
                    else:
                        th.update({"bg": c_bg, "card": c_cd, "accent": c_ac, "text": c_tx, "font": sel_font, "backdrop": sel_bd, "spray_word": spray_in.strip() or "LeX!", "border_style": sel_bst, "card_radius": rad_val, "card_opacity": op_val, "cursor_style": sel_cur, "card_anim": sel_anim, "glow_borders": glow_b, "text_glow": glow_t, "banner_live": sel_bn, "marquee_on": mq_on, "marquee_text": mq_txt.strip(), "pinned_note": pin_txt.strip(), "allow_css_remix": allow_rmx, "scrapbook_require_approval": scrap_app, "custom_css": x_css_in})
                        if clr_wall:
                            th["custom_wall"] = ""
                        elif wall_up is not None:
                            th["custom_wall"] = encode_image_data_url(wall_up)
                        if clr_ban:
                            th["banner_img"] = ""
                        elif ban_up is not None:
                            th["banner_img"] = encode_image_data_url(ban_up)
                        st.session_state.lex_theme = th
                        save_profile_to_cloud()
                        st.toast("All visual customizations saved ✦")
                        st.rerun()
        with st.expander("🎵 Profile Anthem & 🧩 Move / Rearrange ALL Page Modules", expanded=True):
            with st.form("studio_song_form"):
                song_in = st.text_input("Profile Song Link (Spotify / YouTube / Apple Music)", value=user.get("custom_song_url", ""))
                song_lbl = st.text_input("Custom Song Title (Optional)", value=user.get("custom_song_title", ""))
                anth_keys = list(ANTHEM_TRACKS.keys())
                sel_anth = st.selectbox("Or Built-In LeX Synth Anthem", anth_keys, index=anth_keys.index(user.get("anthem")) if user.get("anthem") in anth_keys else 0)
                if st.form_submit_button("Save Profile Song & Anthem ✦", use_container_width=True):
                    user["custom_song_url"] = song_in.strip()
                    user["custom_song_title"] = song_lbl.strip()
                    user["anthem"] = sel_anth
                    st.session_state.lex_user = user
                    save_profile_to_cloud()
                    st.toast("Saved Profile Song ✦")
                    st.rerun()

            st.markdown("**🧩 Move & Rearrange ALL Your Profile Modules (Up, Down, or Swap Columns)**")
            lb = [m for m in (th.get("left_blocks") or ["Profile Card", "Vibe Sticker", "Profile Song / Playlist", "Photo Albums", "Guestbook Wall"]) if m in ALL_PROFILE_MODULES]
            rb = [m for m in (th.get("right_blocks") or ["Pinned Bulletin", "Top 8", "Social Hub"]) if m in ALL_PROFILE_MODULES and m not in lb]
            for missing_m in ALL_PROFILE_MODULES:
                if missing_m not in lb and missing_m not in rb:
                    rb.append(missing_m)
            mc1, mc2 = st.columns(2)
            with mc1:
                st.caption("⬅️ Left Column Order")
                for idx_l, blk in enumerate(lb):
                    r1, r2, r3, r4 = st.columns([2.2, 0.6, 0.6, 0.8])
                    r1.markdown(f"**{idx_l + 1}. {blk}**")
                    if idx_l > 0 and r2.button("↑", key=f"lu_{idx_l}"):
                        lb[idx_l], lb[idx_l - 1] = lb[idx_l - 1], lb[idx_l]
                        th["left_blocks"], th["right_blocks"] = lb, rb
                        save_profile_to_cloud()
                        st.rerun()
                    if idx_l < len(lb) - 1 and r3.button("↓", key=f"ld_{idx_l}"):
                        lb[idx_l], lb[idx_l + 1] = lb[idx_l + 1], lb[idx_l]
                        th["left_blocks"], th["right_blocks"] = lb, rb
                        save_profile_to_cloud()
                        st.rerun()
                    if r4.button("⇄ Right", key=f"lr_{idx_l}"):
                        rb.append(lb.pop(idx_l))
                        th["left_blocks"], th["right_blocks"] = lb, rb
                        save_profile_to_cloud()
                        st.rerun()
            with mc2:
                st.caption("➡️ Right Column Order")
                for idx_r, blk in enumerate(rb):
                    r1, r2, r3, r4 = st.columns([2.2, 0.6, 0.6, 0.8])
                    r1.markdown(f"**{idx_r + 1}. {blk}**")
                    if idx_r > 0 and r2.button("↑", key=f"ru_{idx_r}"):
                        rb[idx_r], rb[idx_r - 1] = rb[idx_r - 1], rb[idx_r]
                        th["left_blocks"], th["right_blocks"] = lb, rb
                        save_profile_to_cloud()
                        st.rerun()
                    if idx_r < len(rb) - 1 and r3.button("↓", key=f"rd_{idx_r}"):
                        rb[idx_r], rb[idx_r + 1] = rb[idx_r + 1], rb[idx_r]
                        th["left_blocks"], th["right_blocks"] = lb, rb
                        save_profile_to_cloud()
                        st.rerun()
                    if r4.button("⇄ Left", key=f"rl_{idx_r}"):
                        lb.append(rb.pop(idx_r))
                        th["left_blocks"], th["right_blocks"] = lb, rb
                        save_profile_to_cloud()
                        st.rerun()
        with st.expander("📸 Featured Photo Albums & 🎧 Audio-Only Playlist"):
            with st.form("studio_album_form", clear_on_submit=True):
                alb_title = st.text_input("Album Title", placeholder="Studio Nights 2026")
                alb_cap = st.text_input("Photo Caption", placeholder="Late night coding & synth vibes")
                alb_file = st.file_uploader("Upload Album Photo", type=["png", "jpg", "jpeg", "webp"], key="alb_up_file")
                if st.form_submit_button("Add Photo to Album ✦") and alb_title.strip() and alb_file is not None:
                    ok_ap, msg_ap = scan_image_safely(alb_file, f"{alb_title} {alb_cap}")
                    if not ok_ap:
                        st.error(msg_ap)
                    else:
                        albs = list(th.get("albums") or [])
                        target_alb = next((a for a in albs if a["title"].lower() == alb_title.strip().lower()), None)
                        if target_alb is None:
                            target_alb = {"title": alb_title.strip(), "photos": []}
                            albs.append(target_alb)
                        target_alb["photos"].append({"img": encode_image_data_url(alb_file), "caption": alb_cap.strip()})
                        th["albums"] = albs
                        st.session_state.lex_theme = th
                        save_profile_to_cloud()
                        st.toast("Added photo to album ✦")
                        st.rerun()

            with st.form("studio_yt_pl_form", clear_on_submit=True):
                yt_title = st.text_input("Playlist Track Name", placeholder="Midnight Synthwave Mix")
                yt_url = st.text_input("YouTube Link or 11-char Video ID")
                if st.form_submit_button("Add Track to Audio Playlist 🎧") and yt_title.strip() and yt_url.strip():
                    yid = extract_yt_id(yt_url)
                    ok_yt, msg_yt = check_safety_and_dress_code(yt_title)
                    if not ok_yt:
                        st.error(msg_yt)
                    elif not yid:
                        st.error("Enter a valid YouTube link or 11-character video ID.")
                    else:
                        pl = list(th.get("yt_playlist") or [])
                        pl.append({"title": yt_title.strip(), "yt_id": yid})
                        th["yt_playlist"] = pl
                        st.session_state.lex_theme = th
                        save_profile_to_cloud()
                        st.toast("Added track to playlist ✦")
                        st.rerun()
    with t_radar:
        all_mem = sb.table("lex_profiles").select("handle, display_name, mood, anthem, theme_json").limit(100).execute().data or [] if sb else []
        q_search = st.text_input("Search by @handle or Display Name...", placeholder="Type @handle or name...", key="radar_search_q")
        all_mem = sb.table("lex_profiles").select("handle, display_name, mood, anthem").limit(100).execute().data or [] if sb else []
        blocked_set = get_blocked_handles()
        filtered = []
        for m in all_mem:
            mh = "@" + clean_handle_str(m.get("handle", ""))
            if len(mh) <= 1 or mh.lower() == user["handle"].lower() or mh.lower() in blocked_set:
                continue
            if q_search.strip() and q_search.strip().lower() not in f"{mh} {m.get('display_name', '')}".lower():
                continue
            m_th = m.get("theme_json") if isinstance(m.get("theme_json"), dict) else {}
            filtered.append({"handle": mh, "name": m.get("display_name", mh.lstrip("@")), "mood": m.get("mood", "Online ⚡"), "anthem": m.get("anthem", "Y2K Cobalt Synth"), "last_seen": m_th.get("last_seen", 0)})
        if not filtered:
            st.info("No matching members found.")
        r_cols = st.columns(3)
        for idx_m, m_obj in enumerate(filtered):
            with r_cols[idx_m % 3]:
                st.markdown(friend_card_html(m_obj, "", th), unsafe_allow_html=True)
                render_member_action_buttons(m_obj["handle"], key_prefix=f"rad_{idx_m}")
with st.expander("⚠️ Account Safety & Permanent Deletion"):
    st.caption("Permanently deletes your LeX profile, posts, messages, and account data.")
    del_confirm = st.checkbox("I understand this action is permanent and cannot be undone.", key="del_acc_chk")
    if st.button("🗑️ Permanently Delete My Account", type="primary", disabled=not del_confirm, key="del_acc_btn") and sb:
        uid_del = str(user.get("user_id") or "")
        h_del = user.get("handle", "")
        try:
            if h_del:
                sb.table("lex_posts").delete().ilike("handle", h_del).execute()
                sb.table("lex_messages").delete().ilike("sender_handle", h_del).execute()
                sb.table("lex_messages").delete().ilike("recipient_handle", h_del).execute()
            if uid_del:
                sb.table("lex_profiles").delete().eq("user_id", uid_del).execute()
            sb.auth.sign_out()
        except Exception as e:
            st.error(f"Deletion notice: {e}")
        st.session_state.lex_user = None
        st.session_state.viewing_handle = None
        st.toast("Your LeX account and profile data have been deleted.")
        st.rerun()

st.markdown(f'<div style="text-align:center;opacity:0.55;font-size:11px;font-family:monospace;margin-top:24px;">LeX Social // Engineered by LexiTech Studio • 13+ Community</div>', unsafe_allow_html=True)
