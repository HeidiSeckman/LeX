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
    "bg": "#06060A", "card": "#0E0E16", "accent": "#EC4899", "text": "#F4F4F5",
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
    last_ts = int((theme_data or {}).get("last_seen", 0))
    return (int(time.time()) - last_ts) < 600
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
                        st.rerun()
                    except Exception as e:
                        st.error(f"Signup error: {e}")
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
    top_tag = f'<span style="background:{ct["accent"]};color:#000;padding:2px 7px;border-radius:99px;font-size:10px;font-weight:900;">{pill_lbl}</span>' if pill_lbl else ""
    return f'<div class="lex-friend-card"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">{top_tag}<span style="color:#34D399;font-size:11px;font-weight:700;">● ONLINE</span></div><div style="display:flex;align-items:center;gap:10px;"><div style="width:42px;height:42px;border-radius:50%;background:radial-gradient(circle,{ct["accent"]},#111);border:2px solid {ct["accent"]};display:flex;align-items:center;justify-content:center;font-weight:900;color:#FFF;box-shadow:0 0 10px {ct["accent"]};">{ini}</div><div><div style="font-weight:800;font-size:14px;color:{ct["text"]};">{fr.get("name", fr.get("handle", "Member"))}</div><div style="color:{ct["accent"]};font-size:12px;font-weight:700;">{fr.get("handle", "@Member")}</div></div></div><div style="font-size:11px;color:#D4D4D8;margin-top:8px;">{fr.get("mood", "Vibing ⚡")}</div><div style="margin-top:6px;padding:4px 8px;border-radius:6px;background:rgba(255,255,255,0.05);font-size:10px;color:{ct["accent"]};">🎵 {fr.get("anthem", "Y2K Cobalt Synth")}</div></div>'

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
    v_av = render_avatar_html(vtj.get("avatar", ""), vp.get("display_name", "L"), v_th, 84)
    v_is_founder = vp.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"}
    v_site = founder_studio_link_html(vp.get("handle", ""), v_th["accent"]) if v_is_founder else (f'<div style="margin-top:6px;"><a href="{vtj["website"]}" target="_blank" style="color:{v_th["accent"]};font-weight:700;">🔗 {vtj["website"]}</a></div>' if vtj.get("website") else "")
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

    st.markdown(f'<div class="lex-card"><div style="display:flex;align-items:center;gap:16px;">{v_av}<div><h2 style="margin:0;">{vp.get("display_name", "")} {founder_badge_html(vp.get("handle", ""))}</h2><div style="color:{v_th["accent"]};font-weight:700;">{vp.get("handle", "")} <span style="font-size:11px;margin-left:6px;">{online_badge}</span></div><div style="color:#34D399;font-size:13px;">● {vp.get("mood", "Online ⚡")}</div>{v_site}</div></div><div style="display:flex;gap:18px;margin-top:12px;font-weight:800;font-size:13px;"><span>⚡ {len(v_fol)} Followers (Unlimited)</span><span>👥 {len(v_fr)} / {MAX_FRIENDS} Friends</span></div><p style="margin-top:12px;"><strong>About Me:</strong> {vp.get("bio", "")}</p><p><strong>Who I\'d Like to Meet:</strong> {vp.get("who_to_meet", "")}</p>{v_int_html}</div>', unsafe_allow_html=True)

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
        my_av = render_avatar_html(user.get("avatar", ""), user.get("name", "L"), th, 88)
        is_owner = user.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"}
        my_site = founder_studio_link_html(user.get("handle", ""), th["accent"]) if is_owner else (f'<div style="margin-top:6px;"><a href="{user["website"]}" target="_blank" style="color:{th["accent"]};font-weight:700;">🔗 {user["website"]}</a></div>' if user.get("website") else "")
        my_ints = [(lbl, th.get(k, "")) for lbl, k in [("General", "int_general"), ("Music", "int_music"), ("Movies", "int_movies"), ("TV", "int_tv"), ("Books & Heroes", "int_books")] if th.get(k)]
        my_int_html = "".join([f'<div style="font-size:12px;margin-top:4px;"><strong style="color:{th["accent"]};">{l}:</strong> {val}</div>' for l, val in my_ints])
        st.markdown(f'<div class="lex-card"><div style="display:flex;align-items:center;gap:14px;">{my_av}<div><h2 style="margin:0;">{user.get("name", "")} {founder_badge_html(user.get("handle", ""))}</h2><div style="color:{th["accent"]};font-weight:700;">{user.get("handle", "")}</div><div style="color:#34D399;font-size:13px;">● {user.get("mood", "Online ⚡")}</div>{my_site}</div></div><div style="display:flex;gap:16px;margin-top:12px;font-weight:800;font-size:13px;"><span>⚡ {len(my_fol)} Followers</span><span>👥 {len(st.session_state.lex_friends)} / {MAX_FRIENDS} Friends</span></div><p style="margin-top:12px;"><strong>About Me:</strong> {user.get("bio", "")}</p><p><strong>Who I\'d Like to Meet:</strong> {user.get("who_to_meet", "")}</p>{my_int_html}</div>', unsafe_allow_html=True)
        vis_list = th.get("visitors", [])
        vis_html = "".join([f'<span style="display:inline-block;padding:4px 10px;margin:3px;border-radius:99px;background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.16);font-size:11px;">👀 {v.get("handle") if isinstance(v, dict) else v}</span>' for v in vis_list]) or '<span style="opacity:0.6;font-size:12px;">No profile views yet — share your card below!</span>'
        st.markdown(f'<div class="lex-card"><strong>👀 Recent Profile Visitors</strong><div style="margin-top:8px;">{vis_html}</div></div>', unsafe_allow_html=True)
        with st.expander("🪪 Share My LeX Profile Card"):
            c_acc = th.get("accent", "#94A3B8")
            c_bg = th.get("card_bg", "rgba(15,23,42,0.92)")
            av_s = user.get("avatar", "")
            av_t = f'<img src="{av_s}" style="width:64px;height:64px;border-radius:50%;object-fit:cover;border:2px solid {c_acc};">' if av_s else '<div style="width:64px;height:64px;border-radius:50%;background:rgba(255,255,255,0.1);display:flex;align-items:center;justify-content:center;font-size:24px;">⚡</div>'
            st.markdown(
                f'<div style="padding:18px;border-radius:18px;background:linear-gradient(135deg,{c_bg},#090d16);border:1.5px solid {c_acc};box-shadow:0 10px 26px rgba(0,0,0,0.6);max-width:350px;margin:auto;">'
                f'<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;"><span style="font-weight:900;letter-spacing:2px;font-size:13px;color:#F8FAFC;">LeX SOCIAL</span><span style="font-size:9px;padding:3px 8px;border-radius:99px;border:1px solid {c_acc};color:{c_acc};font-weight:700;">FOUNDING MEMBER</span></div>'
                f'<div style="display:flex;align-items:center;gap:12px;">{av_t}<div><div style="font-size:17px;font-weight:800;color:#FFFFFF;">{user.get("name","Member")}</div><div style="font-size:12px;color:{c_acc};font-weight:600;">{user.get("handle","@member")}</div><div style="font-size:11px;color:#CBD5E1;margin-top:3px;">Mood: {user.get("mood","Online Now • Vibing ⚡")}</div></div></div>'
                f'<div style="margin-top:12px;padding-top:8px;border-top:1px solid rgba(255,255,255,0.12);display:flex;justify-content:space-between;font-size:10px;color:#94A3B8;"><span>Algorithm-Free Social</span><strong style="color:#F8FAFC;">lexsocial.space</strong></div></div>',
                unsafe_allow_html=True,
            )
            st.code(f"Come add me on LeX Social ({user.get('handle')}) — custom themes, profile songs & zero algorithms! 👉 https://lexsocial.space", language=None)

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
            st.markdown(f'<div class="lex-card" style="padding:10px;"><strong>{w_item.get("sender", "@LeX")}:</strong> {w_item.get("msg", "")}</div>', unsafe_allow_html=True)
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
    t_feed, t_friends, t_dm, t_top8, t_studio, t_radar = st.tabs([
        "📰 Feed", "👥 All Friends", "✉️ Messages", "✦ Top 8", "🎨 LeX Studio", "📡 Radar"
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
        posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(25).execute().data or [] if sb else []
        my_h_low = user["handle"].lower()
        for p in posts:
            p_author_h = (p.get("handle") or "").strip()
            if p_author_h.lower() in blocked_set:
                continue
            clean_txt, lnk_src, img_src, p_meta = parse_post_blob(p.get("body") or "", int(p.get("likes") or 0))
            img_tag = f'<img src="{img_src}" style="width:100%;max-height:360px;object-fit:cover;border-radius:10px;margin-top:10px;border:1px solid {th["accent"]};" />' if img_src else ""
            lnk_tag = f'<div style="margin-top:8px;"><a href="{lnk_src}" target="_blank" style="display:inline-block;padding:6px 12px;border-radius:8px;background:{th["accent"]}22;border:1px solid {th["accent"]};color:{th["accent"]};font-weight:700;text-decoration:none;">🔗 {lnk_src}</a></div>' if lnk_src else ""
            st.markdown(f'<div class="lex-card"><strong>{p["author"]}</strong> <span style="color:{th["accent"]};">{p_author_h}</span>{founder_badge_html(p_author_h)}<p style="margin-top:6px;">{clean_txt}</p>{lnk_tag}{img_tag}</div>', unsafe_allow_html=True)
            rx_map = p_meta["rx"]
            cm_list = p_meta["comments"]
            rcols = st.columns(7)
            for idx_e, emo in enumerate(["🔥", "💖", "🎸", "💀"]):
                emo_users = rx_map.get(emo) or {}
                cnt_e = sum(int(v) if isinstance(v, int) else 1 for v in emo_users.values())
                i_reacted = my_h_low in {str(k).lower() for k in emo_users.keys()}
                lbl_e = f"{emo} {cnt_e} ✓" if i_reacted else f"{emo} {cnt_e}"
                if rcols[idx_e].button(lbl_e, key=f"b_{p['id']}_{emo}") and sb:
                    existing_k = next((k for k in emo_users.keys() if str(k).lower() == my_h_low), None)
                    if existing_k:
                        emo_users.pop(existing_k, None)
                    else:
                        emo_users[user["handle"]] = 1
                        push_activity_notif(p_author_h, user["handle"], "react", emo, p["id"])
                    rx_map[emo] = emo_users
                    p_meta["rx"] = rx_map
                    fire_total = sum(int(v) if isinstance(v, int) else 1 for v in (rx_map.get("🔥") or {}).values())
                    sb.table("lex_posts").update({"body": pack_post_blob(clean_txt, lnk_src, img_src, p_meta), "likes": fire_total}).eq("id", p["id"]).execute()
                    st.rerun()
            c_open_key = f"open_cm_{p['id']}"
            if rcols[4].button(f"💬 {len(cm_list)}", key=f"cbtn_{p['id']}"):
                st.session_state[c_open_key] = not st.session_state.get(c_open_key, False)
                st.rerun()
            if p_author_h.lower() != my_h_low:
                if rcols[5].button("🚩 Report", key=f"rep_p_{p['id']}"):
                    block_or_report_member(p_author_h, "report", f"Reported post #{p['id']}")
                    st.toast("Reported post to LeX Safety")
            else:
                with rcols[5].popover("✏️"):
                    new_ed_txt = st.text_area("Edit post text", value=clean_txt, key=f"ed_ta_{p['id']}")
                    if st.button("💾 Save Edit", key=f"sv_ed_{p['id']}") and sb:
                        ok_e, msg_e = check_safety_and_dress_code(new_ed_txt)
                        if not ok_e:
                            st.error(msg_e)
                        else:
                            sb.table("lex_posts").update({"body": pack_post_blob(new_ed_txt, lnk_src, img_src, p_meta)}).eq("id", p["id"]).execute()
                            st.rerun()
                if rcols[6].button("🗑️", key=f"del_p_{p['id']}") and sb:
                    sb.table("lex_posts").delete().eq("id", p["id"]).execute()
                    st.rerun()

            if st.session_state.get(c_open_key, False) or cm_list:
                with st.expander(f"💬 Comments ({len(cm_list)})", expanded=st.session_state.get(c_open_key, False)):
                    for cm in cm_list[-20:]:
                        st.markdown(f'<div style="padding:6px 10px;border-left:2px solid {th["accent"]};margin-bottom:6px;background:rgba(255,255,255,0.03);border-radius:6px;"><strong style="color:{th["accent"]};">{cm.get("author", "@Member")}:</strong> {cm.get("text", "")}</div>', unsafe_allow_html=True)
                    with st.form(f"cm_form_{p['id']}", clear_on_submit=True):
                        c_in = st.text_input("Write a comment...", key=f"cin_{p['id']}")
                        if st.form_submit_button("Post Comment ✦") and c_in.strip() and sb:
                            ok_c, msg_c = check_safety_and_dress_code(c_in)
                            if not ok_c:
                                st.error(msg_c)
                            else:
                                cm_list.append({"author": user["handle"], "text": c_in.strip()[:280]})
                                p_meta["comments"] = cm_list
                                sb.table("lex_posts").update({"body": pack_post_blob(clean_txt, lnk_src, img_src, p_meta)}).eq("id", p["id"]).execute()
                                push_activity_notif(p_author_h, user["handle"], "comment", c_in.strip(), p["id"])
                                st.session_state[c_open_key] = True
                                st.rerun()
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
        all_rows = sb.table("lex_profiles").select("handle, display_name").limit(200).execute().data or [] if sb else []
        blocked_set = get_blocked_handles()
        member_opts = {}
        for mr in all_rows:
            mh = "@" + clean_handle_str(mr.get("handle", ""))
            if len(mh) > 1 and mh.lower() != user["handle"].lower() and mh.lower() not in blocked_set:
                member_opts[mh] = f"{mr.get('display_name', mh)} ({mh})"
        ov_raw = st.session_state.get("dm_target_override", "")
        ov_clean = "@" + clean_handle_str(ov_raw) if ov_raw else ""
        if ov_clean and len(ov_clean) > 1 and ov_clean not in member_opts and ov_clean.lower() != user["handle"].lower():
            member_opts[ov_clean] = ov_clean
        if not member_opts:
            st.info("No other members available to message yet.")
        else:
            handles_list = list(member_opts.keys())
            default_idx = handles_list.index(ov_clean) if ov_clean in handles_list else 0
            sel_h = st.selectbox("Select Member to Message", handles_list, index=default_idx, format_func=lambda h: member_opts.get(h, h), key="dm_member_pick")
            if ov_clean:
                st.session_state["dm_target_override"] = ""
            msgs = sb.table("lex_messages").select("*").order("id", desc=False).limit(300).execute().data or [] if sb else []
            my_l, tg_l = user["handle"].lower(), sel_h.lower()
            thread = [m for m in msgs if not (m.get("body") or "").startswith(("[LEX_F", "[LEX_NOTIF]")) and {str(m.get("sender_handle", "")).lower(), str(m.get("recipient_handle", "")).lower()} == {my_l, tg_l}]
            for m in thread[-30:]:
                is_me = str(m.get("sender_handle", "")).lower() == my_l
                st.markdown(f'<div class="lex-card" style="padding:8px 12px;margin-bottom:6px;text-align:{"right" if is_me else "left"};"><span style="color:{th["accent"]};font-size:11px;font-weight:800;">{"You" if is_me else sel_h}</span><div>{m.get("body", "")}</div></div>', unsafe_allow_html=True)
            with st.form("dm_send_form", clear_on_submit=True):
                dm_txt = st.text_input(f"Message {sel_h}...", key="dm_msg_in")
                if st.form_submit_button("Send Message ✦") and dm_txt.strip() and sb:
                    ok_d, msg_d = check_safety_and_dress_code(dm_txt)
                    if not ok_d:
                        st.error(msg_d)
                    else:
                        sb.table("lex_messages").insert({"sender_handle": user["handle"], "recipient_handle": sel_h, "body": dm_txt.strip()}).execute()
                        st.rerun()
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
                b_site = st.text_input("Profile Website / Link", value=user.get("website", ""))
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
                    blob_chk = f"{b_name} {b_mood} {b_site} {b_bio} {b_meet} {i_gen} {i_mus} {i_mov} {i_tv} {i_bok} {stk_url_in}"
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
                        user["website"] = normalize_url(b_site)
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
                x_css_in = st.text_area("Custom Profile CSS", value=th.get("custom_css", ""), height=68)
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
                        th.update({"bg": c_bg, "card": c_cd, "accent": c_ac, "text": c_tx, "font": sel_font, "backdrop": sel_bd, "spray_word": spray_in.strip() or "LeX!", "border_style": sel_bst, "card_radius": rad_val, "card_opacity": op_val, "cursor_style": sel_cur, "card_anim": sel_anim, "glow_borders": glow_b, "text_glow": glow_t, "banner_live": sel_bn, "marquee_on": mq_on, "marquee_text": mq_txt.strip(), "pinned_note": pin_txt.strip(), "custom_css": x_css_in})
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
        st.markdown(f'<div class="lex-card" style="padding:12px 16px;"><strong style="color:{th["accent"]};font-size:16px;">📡 Member Radar // Discover & Connect</strong></div>', unsafe_allow_html=True)
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
            filtered.append({"handle": mh, "name": m.get("display_name", mh.lstrip("@")), "mood": m.get("mood", "Online ⚡"), "anthem": m.get("anthem", "Y2K Cobalt Synth")})
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
