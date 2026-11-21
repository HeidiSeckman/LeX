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
            r = requests.post(
                "https://sightengine.com",
                files={"media": (fname, uploaded_file.getvalue())},
                data={"models": "nudity-2.1,gore-2.0", "api_user": api_u, "api_secret": api_s},
                timeout=12,
            )
            jd = r.json() if r.status_code == 200 else {}
            nud, gor = jd.get("nudity") or {}, jd.get("gore") or {}
            scores = [nud.get("sexual_activity", 0), nud.get("sexual_display", 0), nud.get("erotica", 0), nud.get("very_suggestive", 0), nud.get("mildly_suggestive", 0), gor.get("prob", 0)]
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
        for r_i, item in enumerate(st.session_state.lex_top8):
            item["rank"] = r_i + 1
        th_ref["following"] = [x for x in (th_ref.get("following") or []) if x.lower() != tgt.lower()]
        th_ref["incoming_requests"] = [x for x in (th_ref.get("incoming_requests") or []) if x.get("handle", "").lower() != tgt.lower()]
        th_ref["sent_requests"] = [x for x in (th_ref.get("sent_requests") or []) if x.lower() != tgt.lower()]
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
    "12-Point Starburst": ("0px", "polygon(50% 0%, 60% 18%, 80% 10%, 78% 32%, 98% 38%, 84% 54%, 96% 74%, 75% 76%, 76% 96%, 56% 85%, 44% 98%, 35% 79%, 14% 86%, 22% 66%, 4% 55%, 20% 42%, 12% 22%, 33% 25%, 40% 5%)"),
    "Y2K Heart": ("0px", "path('M 42 78 C 10 56 0 38 0 23 C 0 10 10 0 23 0 C 31 0 38 4 42 11 C 46 4 53 0 61 0 C 74 0 84 10 84 23 C 84 38 74 56 42 78 Z')"),
    "Gothic Shield": ("0px", "polygon(50% 0%, 95% 15%, 90% 62%, 50% 100%, 10% 62%, 5% 15%)"),
    "Cathedral Arch": ("42px 42px 6px 6px", "none"),
    "Pentagon": ("0px", "polygon(50% 0%, 100% 38%, 82% 100%, 18% 100%, 0% 38%)"),
    "4-Leaf Clover": ("35%", "polygon(25% 0%, 50% 15%, 75% 0%, 100% 25%, 85% 50%, 100% 75%, 75% 100%, 50% 85%, 25% 100%, 0% 75%, 15% 50%, 0% 25%)"),
}

CURSOR_OPTIONS = {
    "Default System Pointer": "auto",
    "Neon Crosshair": "crosshair",
    "Cyber Grab Hand": "grab",
    "Retro Cell Plus": "cell",
    "Sparkle Star SVG": "url(\"data:image/svg+xml,%3Csvg xmlns='http://w3.org' width='24' height='24'%3E%3Ctext y='18' font-size='18'%3E✦%3C/text%3E%3C/svg%3E\"), auto",
    "Pink Heart SVG": "url(\"data:image/svg+xml,%3Csvg xmlns='http://w3.org' width='24' height='24'%3E%3Ctext y='18' font-size='18'%3E💖%3C/text%3E%3C/svg%3E\"), auto",
    "Cyber Skull SVG": "url(\"data:image/svg+xml,%3Csvg xmlns='http://w3.org' width='24' height='24'%3E%3Ctext y='18' font-size='18'%3E💀%3C/text%3E%3C/svg%3E\"), auto",
}

THEME_PRESETS = {
    "LexiTech Obsidian (Official)": {"bg": "#000000", "card": "#070709", "accent": "#EC4899", "font": "Clean Studio Sans", "backdrop": "Architectural Grid", "banner_live": "Falling Shooting Stars", "card_anim": "None (Static)"},
    "2006 Emo Scene Kid": {"bg": "#09040c", "card": "#14091c", "accent": "#D946EF", "font": "Girl Punk / Spray Marker", "backdrop": "Checkered Ska / Vans", "banner_live": "Rising Cyber Flames", "card_anim": "Pulse Neon Glow"},
    "Y2K Cyber Bratz Glam": {"bg": "#120318", "card": "#1f0729", "accent": "#FF2A85", "font": "Futuristic Orbitron", "backdrop": "Y2K Stars & Sparkles", "banner_live": "Floating Cyber Hearts", "card_anim": "Floating Levitate"},
    "Matrix Hacker Terminal": {"bg": "#000802", "card": "#031407", "accent": "#00FF66", "font": "Y2K Arcade Pixel", "backdrop": "Cyber Matrix Rain", "banner_live": "Neon Cyberpunk Rain", "card_anim": "Cyber Glitch Flicker"},
    "Cosmic Space Odyssey": {"bg": "#030514", "card": "#080d29", "accent": "#38BDF8", "font": "Futuristic Orbitron", "backdrop": "Cosmic Planets & Rings", "banner_live": "Orbiting Planets & Space", "card_anim": "Floating Levitate"},
    "Gothic Velvet Vampire": {"bg": "#0a0204", "card": "#170509", "accent": "#EF4444", "font": "Gothic Editorial", "backdrop": "Gothic Bats & Moons", "banner_live": "Electric Lightning Storm", "card_anim": "Pulse Neon Glow"},
}

DEFAULT_LEFT = ["Profile Card", "Photo Albums", "Profile Anthem", "Profile Wall"]
DEFAULT_RIGHT = ["Top 8 Friends", "Main Social Hub"]
DEFAULT_THEME = {
    "name": "LexiTech Obsidian (Official)", "bg": "#000000", "card": "#070709",
    "accent": "#EC4899", "text": "#F4F4F5", "font": "Clean Studio Sans",
    "backdrop": "Architectural Grid", "border_style": "solid", "glow_borders": True,
    "text_glow": True, "card_opacity": 92, "card_radius": 12,
    "marquee_text": "✦ WELCOME TO MY LeX PROFILE // ZERO ALGORITHMS ✦",
    "marquee_on": True, "pinned_note": "", "custom_css": "",
    "int_general": "", "int_music": "", "int_movies": "", "int_tv": "", "int_books": "",
    "spray_word": "LeX!", "custom_wall": "", "website": "",
    "banner_live": "None", "banner_img": "", "cursor_style": "Default System Pointer",
    "card_anim": "None (Static)", "vibe_sticker": "", "avatar_shape": "Classic Circle",
    "left_blocks": DEFAULT_LEFT.copy(), "right_blocks": DEFAULT_RIGHT.copy(),
    "followers": [], "following": [], "playlist": [], "albums": [],
    "incoming_requests": [], "sent_requests": [], "declined_requests": [],
    "blocked_users": [], "reports_log": [],
}
DEFAULT_TOP8 = []
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
def build_live_banner_html(mode: str, custom_img: str, accent: str, rad_px: int) -> str:
    if custom_img:
        return f'<div style="width:100%;height:155px;border-radius:{rad_px}px;overflow:hidden;margin-bottom:12px;border:1.5px solid {accent};box-shadow:0 0 16px {accent}55;"><img src="{custom_img}" style="width:100%;height:100%;object-fit:cover;" /></div>'
    if not mode or mode == "None":
        return ""
    kf = "@keyframes lexFall{0%{transform:translate(0,-30px);opacity:1}100%{transform:translate(-140px,170px);opacity:0}}@keyframes lexRise{0%,100%{transform:translateY(0) scaleY(1)}50%{transform:translateY(-14px) scaleY(1.18)}}@keyframes lexOrbit{0%{transform:rotate(0deg)}100%{transform:rotate(360deg)}}@keyframes lexRain{0%{transform:translateY(-140px)}100%{transform:translateY(160px)}}@keyframes lexPulse{0%,100%{opacity:.25}50%{opacity:1}}"
    if mode == "Falling Shooting Stars":
        inner = f'<circle cx="15%" cy="25%" r="2" fill="#fff" style="animation:lexPulse 1.5s infinite"/><circle cx="75%" cy="35%" r="2.5" fill="{accent}" style="animation:lexPulse 2s infinite"/><line x1="85%" y1="10" x2="72%" y2="45" stroke="{accent}" stroke-width="3" style="animation:lexFall 1.8s linear infinite"/><line x1="45%" y1="5" x2="32%" y2="40" stroke="#fff" stroke-width="2.5" style="animation:lexFall 2.4s linear infinite 0.7s"/>'
    elif mode == "Rising Cyber Flames":
        inner = f'<path d="M0,140 Q60,70 120,130 T240,120 T360,135 T480,115 T600,130 T720,120 T840,140 L840,150 L0,150 Z" fill="{accent}" fill-opacity="0.55" style="animation:lexRise 1.4s ease-in-out infinite"/><path d="M0,145 Q90,90 180,135 T360,125 T540,140 T720,120 T840,145 L840,150 L0,150 Z" fill="#F59E0B" fill-opacity="0.45" style="animation:lexRise 1.1s ease-in-out infinite 0.3s"/>'
    elif mode == "Orbiting Planets & Space":
        inner = f'<circle cx="50%" cy="72" r="24" fill="{accent}" fill-opacity="0.45" stroke="{accent}" stroke-width="2"/><ellipse cx="50%" cy="72" rx="68" ry="16" fill="none" stroke="#fff" stroke-opacity="0.4" stroke-width="2"/><g style="transform-origin:50% 72px;animation:lexOrbit 5s linear infinite"><circle cx="50%" cy="22" r="7" fill="#fff"/></g>'
    elif mode == "Neon Cyberpunk Rain":
        inner = "".join([f'<line x1="{x}%" y1="0" x2="{x-4}%" y2="45" stroke="{accent}" stroke-width="2" style="animation:lexRain {0.7+(x%3)*0.25}s linear infinite {(x%5)*0.2}s"/>' for x in range(6, 98, 8)])
    elif mode == "Live Glowing Waterfall":
        inner = "".join([f'<rect x="{x}%" y="0" width="6%" height="145" fill="{accent}" fill-opacity="0.32" style="animation:lexRain {0.9+(x%2)*0.3}s linear infinite"/>' for x in range(28, 72, 9)]) + '<ellipse cx="50%" cy="138" rx="34%" ry="12" fill="#fff" fill-opacity="0.35" style="animation:lexPulse 1s infinite"/>'
    elif mode == "Electric Lightning Storm":
        inner = f'<polyline points="220,0 195,55 230,55 185,140" fill="none" stroke="{accent}" stroke-width="4" style="animation:lexPulse 0.9s infinite"/><polyline points="560,0 590,60 555,60 605,140" fill="none" stroke="#fff" stroke-width="3" style="animation:lexPulse 1.3s infinite 0.4s"/>'
    elif mode == "Floating Cyber Hearts":
        inner = "".join([f'<text x="{x}%" y="120" font-size="24" fill="{accent}" style="animation:lexRise {1.6+(x%3)*0.4}s ease-in-out infinite {(x%4)*0.3}s">♥</text>' for x in range(12, 92, 16)])
    else:
        inner = "".join([f'<rect x="{x}%" y="45" width="4%" height="95" rx="4" fill="{accent}" style="transform-origin:bottom;animation:lexRise {0.5+(x%4)*0.15}s ease-in-out infinite {(x%3)*0.1}s"/>' for x in range(10, 92, 8)])
    return f'{ST_OPEN}{kf}{ST_CLOSE}<div style="width:100%;height:140px;border-radius:{rad_px}px;overflow:hidden;margin-bottom:12px;background:radial-gradient(circle at 50% 40%, {accent}22, #050508 85%);border:1.5px solid {accent};">{SV_OPEN}xmlns="{SVG_NS}" width="100%" height="140">{inner}{SV_CLOSE}</div>'

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
    if len(s) == 11 and "/" not in s and "." not in s:
        return s
    for sep in ["youtu.be/", "v=", "/embed/"]:
        if sep in s:
            _, _, tail = s.partition(sep)
            head, _, _ = tail.partition("?")
            head, _, _ = head.partition("&")
            return head.strip("/")[:11]
    return ""
def render_avatar_html(avatar_url: str, display_name: str, t_cfg: dict, size_px: int = 84) -> str:
    acc = t_cfg.get("accent", "#EC4899")
    rad, clip = AVATAR_SHAPES.get(t_cfg.get("avatar_shape", "Classic Circle"), ("50%", "none"))
    clip_css = f"clip-path:{clip};-webkit-clip-path:{clip};" if clip != "none" else ""
    wrap_st = f"width:{size_px}px;height:{size_px}px;padding:3px;background:{acc};border-radius:{rad};{clip_css}box-shadow:0 0 16px {acc};display:flex;align-items:center;justify-content:center;flex-shrink:0;"
    if avatar_url:
        return f'<div style="{wrap_st}"><img src="{avatar_url}" style="width:100%;height:100%;object-fit:cover;border-radius:{rad};{clip_css}" /></div>'
    ini = ((display_name or "L")[:1] or "L").upper()
    return f'<div style="{wrap_st}"><div style="width:100%;height:100%;background:#09090d;color:{acc};font-weight:900;font-size:{int(size_px*0.38)}px;border-radius:{rad};{clip_css}display:flex;align-items:center;justify-content:center;">{ini}</div></div>'

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
    if tgt.lower() not in {x.lower() for x in sent}:
        sent.append(tgt)
        st.session_state.lex_theme["sent_requests"] = sent
        save_profile_to_cloud()
    return True

def accept_friend_request(req_obj: dict):
    sb = get_sb()
    u = st.session_state.get("lex_user")
    if not u:
        return
    r_h = "@" + clean_handle_str(req_obj.get("handle", ""))
    st.session_state.lex_theme["incoming_requests"] = [x for x in (st.session_state.lex_theme.get("incoming_requests") or []) if x.get("handle", "").lower() != r_h.lower()]
    if len(st.session_state.lex_friends) < MAX_FRIENDS and not any(f.get("handle", "").lower() == r_h.lower() for f in st.session_state.lex_friends):
        st.session_state.lex_friends.append({"handle": r_h, "name": req_obj.get("name", r_h), "mood": req_obj.get("mood", "Online ⚡"), "anthem": req_obj.get("anthem", "Y2K Cobalt Synth")})
    save_profile_to_cloud()
    if sb and len(r_h) > 1:
        sb.table("lex_messages").insert({
            "sender_handle": u["handle"], "recipient_handle": r_h,
            "body": f"[LEX_FACC]{u['name']}|{u.get('mood', 'Online ⚡')}|{u.get('anthem', 'Y2K Cobalt Synth')}"
        }).execute()

def decline_friend_request(req_handle: str):
    r_h = "@" + clean_handle_str(req_handle)
    st.session_state.lex_theme["incoming_requests"] = [x for x in (st.session_state.lex_theme.get("incoming_requests") or []) if x.get("handle", "").lower() != r_h.lower()]
    dec = list(st.session_state.lex_theme.get("declined_requests") or [])
    if r_h.lower() not in {x.lower() for x in dec}:
        dec.append(r_h)
        st.session_state.lex_theme["declined_requests"] = dec
    save_profile_to_cloud()
def toggle_follow_user(my_handle: str, target_handle: str):
    sb = get_sb()
    following = list(st.session_state.lex_theme.get("following") or [])
    adding = target_handle not in following
    following.append(target_handle) if adding else following.remove(target_handle)
    st.session_state.lex_theme["following"] = following
    save_profile_to_cloud()
    if sb:
        try:
            res = sb.table("lex_profiles").select("user_id, theme_json").ilike("handle", target_handle).execute().data
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

def render_mini_yt_audio_bar(yt_id: str, track_label: str, accent: str):
    if not yt_id:
        return
    src = f"{YT_EMBED_BASE}{yt_id}?autoplay=1&controls=1&rel=0"
    st.markdown(f'<div class="lex-card" style="padding:8px 10px;margin:8px 0;"><div style="font-size:12px;font-weight:800;color:{accent};margin-bottom:4px;">🎧 NOW SPINNING: {track_label}</div><div style="height:46px;overflow:hidden;border-radius:6px;"><iframe width="100%" height="140" src="{src}" frameborder="0" allow="autoplay; encrypted-media" style="margin-top:-92px;"></iframe></div></div>', unsafe_allow_html=True)

for k, v in [("lex_user", None), ("lex_theme", DEFAULT_THEME.copy()), ("lex_top8", []), ("lex_friends", []), ("viewing_handle", None), ("dm_target_override", "")]:
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
    glw = f"box-shadow: 0 0 18px {t_cfg['accent']}66, inset 0 0 10px {t_cfg['accent']}22;" if t_cfg.get("glow_borders", True) else ""
    tglw = f"text-shadow: 0 0 14px {t_cfg['accent']};" if t_cfg.get("text_glow", True) else ""
    opv = max(40, min(100, int(t_cfg.get("card_opacity", 92)))) / 100.0
    rpx = int(t_cfg.get("card_radius", 12))
    cur_css = CURSOR_OPTIONS.get(t_cfg.get("cursor_style", "Default System Pointer"), "auto")
    anim_mode = t_cfg.get("card_anim", "None (Static)")
    anim_kf = "@keyframes lexCardPulse{0%,100%{box-shadow:0 0 14px " + t_cfg["accent"] + "55}50%{box-shadow:0 0 28px " + t_cfg["accent"] + "cc}}@keyframes lexFloat{0%,100%{transform:translateY(0)}50%{transform:translateY(-4px)}}@keyframes lexGlitch{0%,94%,100%{transform:translate(0)}96%{transform:translate(-2px,1px)}98%{transform:translate(2px,-1px)}}"
    anim_rule = "animation: lexCardPulse 2.4s ease-in-out infinite;" if anim_mode == "Pulse Neon Glow" else ("animation: lexFloat 3s ease-in-out infinite;" if anim_mode == "Floating Levitate" else ("animation: lexGlitch 3.5s infinite;" if anim_mode == "Cyber Glitch Flicker" else ""))
    x_css = (t_cfg.get("custom_css") or "").replace("<", "").replace(">", "")
    return (
        f'{LK_OPEN}rel="stylesheet" href="{GFONTS_BASE}{gf_name.replace(" ", "+")}&display=swap" />' + ST_OPEN + anim_kf
        + f'[data-testid="stAppViewContainer"], .stApp {{ background-color: {t_cfg["bg"]} !important; background-image: {bg_img} !important; background-size: {bg_sz} !important; background-repeat: {bg_rep} !important; background-attachment: fixed !important; color: {t_cfg["text"]} !important; cursor: {cur_css}; }}'
        + '[data-testid="stHeader"], [data-testid="stMain"] { background: transparent !important; }'
        + f".lex-banner {{ background: radial-gradient(circle at 15% 50%, rgba(236,72,153,0.18), {t_cfg['card']} 65%); border: 2px {t_cfg['border_style']} {t_cfg['accent']}; border-radius: {rpx}px; padding: 18px 24px; margin-bottom: 16px; {glw} }}"
        + f".lex-wordmark {{ font-family: {css_ff}; font-size: 38px; font-weight: 800; color: #FFFFFF; text-shadow: 0 0 22px {t_cfg['accent']}; }}"
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
    st.markdown('<div class="lex-banner"><div class="lex-wordmark">LeX</div><div style="color:#A1A1AA;font-family:monospace;font-size:12px;">NEXT-GEN SOCIAL ARCHITECTURE // LEXITECH STUDIO // 13+ ONLY</div></div>', unsafe_allow_html=True)
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
                        st.session_state.lex_top8 = r.get("top8_json") or []
                        st.session_state.lex_friends = tj.get("all_friends") or []
                        if r.get("wall_json"):
                            st.session_state.lex_wall = r["wall_json"]
                    else:
                        prefix, _, _ = l_email.strip().partition("@")
                        base_h = clean_handle_str(prefix) or "Member"
                        cand, sfx = base_h, 1
                        while is_handle_taken(sb, cand, uid):
                            cand = f"{base_h}{sfx}"
                            sfx += 1
                        st.session_state.lex_user = {"user_id": uid, "name": cand.capitalize(), "handle": f"@{cand}", "avatar": "", "website": "", "mood": "Online Now • Vibing ⚡", "bio": "Back on LeX ✦", "who_to_meet": "Creators & music lovers.", "anthem": "Y2K Cobalt Synth", "custom_song_url": "", "custom_song_title": ""}
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
                    st.error(f"@{ch} is already taken! Every handle on LeX must be unique—please pick another.")
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
if sb and user.get("handle"):
    try:
        sys_rows = sb.table("lex_messages").select("*").ilike("recipient_handle", user["handle"]).order("id", desc=False).limit(200).execute().data or []
        my_f_low = {f["handle"].lower() for f in st.session_state.lex_friends}
        inc_list = list(st.session_state.lex_theme.get("incoming_requests") or [])
        inc_low = {x["handle"].lower() for x in inc_list if x.get("handle")}
        dec_low = {x.lower() for x in (st.session_state.lex_theme.get("declined_requests") or [])}
        sent_list = list(st.session_state.lex_theme.get("sent_requests") or [])
        dirty_sync = False
        for sr in sys_rows:
            b_txt = sr.get("body") or ""
            s_h = "@" + clean_handle_str(sr.get("sender_handle", ""))
            if len(s_h) <= 1 or s_h.lower() == user["handle"].lower():
                continue
            if b_txt.startswith("[LEX_FACC]"):
                parts = b_txt[10:].split("|")
                if s_h.lower() not in my_f_low and len(st.session_state.lex_friends) < MAX_FRIENDS:
                    st.session_state.lex_friends.append({"handle": s_h, "name": parts if parts else s_h, "mood": parts if len(parts) > 1 else "Online ⚡", "anthem": parts if len(parts) > 2 else "Y2K Cobalt Synth"})
                    my_f_low.add(s_h.lower())
                    dirty_sync = True
                if s_h.lower() in {x.lower() for x in sent_list}:
                    sent_list = [x for x in sent_list if x.lower() != s_h.lower()]
                    st.session_state.lex_theme["sent_requests"] = sent_list
                    dirty_sync = True
            elif b_txt.startswith("[LEX_FREQ]"):
                parts = b_txt[10:].split("|")
                if s_h.lower() not in my_f_low and s_h.lower() not in inc_low and s_h.lower() not in dec_low:
                    inc_list.append({"handle": s_h, "name": parts if parts else s_h, "mood": parts if len(parts) > 1 else "Online ⚡", "anthem": parts if len(parts) > 2 else "Y2K Cobalt Synth"})
                    inc_low.add(s_h.lower())
                    st.session_state.lex_theme["incoming_requests"] = inc_list
                    dirty_sync = True
        if dirty_sync:
            save_profile_to_cloud()
    except Exception:
        pass

top_c1, top_c2 = st.columns([0.85, 0.15])
if st.session_state.viewing_handle and top_c1.button(f"← Back to My Profile ({user['handle']})"):
    st.session_state.viewing_handle = None
    st.rerun()
if top_c2.button("Sign Out"):
    st.session_state.lex_user = None
    st.session_state.viewing_handle = None
    st.rerun()

def friend_card_html(fr: dict, badge: str = "", card_theme: dict = None) -> str:
    ct = card_theme or th
    ini = (fr.get("name", "L")[:1] or "L").upper()
    is_owner = (fr.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"})
    pill_lbl = "👑 FOUNDER" if is_owner else badge
    top_tag = f'<span style="background:{ct["accent"]};color:#000;padding:2px 7px;border-radius:99px;font-size:10px;font-weight:900;">{pill_lbl}</span>' if pill_lbl else ""
    return (
        f'<div class="lex-friend-card"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">{top_tag}'
        f'<span style="color:#34D399;font-size:11px;font-weight:700;">● ONLINE</span></div>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<div style="width:42px;height:42px;border-radius:50%;background:radial-gradient(circle,{ct["accent"]},#111);border:2px solid {ct["accent"]};display:flex;align-items:center;justify-content:center;font-weight:900;color:#FFF;box-shadow:0 0 10px {ct["accent"]};">{ini}</div>'
        f'<div><div style="font-weight:800;font-size:14px;color:{ct["text"]};">{fr["name"]}</div>'
        f'<div style="color:{ct["accent"]};font-size:12px;font-weight:700;">{fr["handle"]}</div></div></div>'
        f'<div style="font-size:11px;color:#D4D4D8;margin-top:8px;">{fr.get("mood", "Vibing ⚡")}</div>'
        f'<div style="margin-top:6px;padding:4px 8px;border-radius:6px;background:rgba(255,255,255,0.05);font-size:10px;color:{ct["accent"]};">🎵 {fr.get("anthem", "Y2K Cobalt Synth")}</div></div>'
    )
if st.session_state.viewing_handle and sb:
    vh_clean = "@" + clean_handle_str(st.session_state.viewing_handle)
    v_res = sb.table("lex_profiles").select("*").ilike("handle", vh_clean).execute().data
    vp = next(iter(v_res), None) if isinstance(v_res, list) else v_res
    if not isinstance(vp, dict):
        st.warning(f"Could not load profile for {vh_clean}. Make sure Supabase public read policy is enabled.")
        st.stop()
    vtj = vp.get("theme_json") or {}
    v_th = DEFAULT_THEME.copy()
    v_th.update(vtj)
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
    st.markdown(
        f'<div class="lex-card"><div style="display:flex;align-items:center;gap:16px;">{v_av}'
        f'<div><h2 style="margin:0;">{vp.get("display_name", "")} {founder_badge_html(vp.get("handle", ""))}</h2>'
        f'<div style="color:{v_th["accent"]};font-weight:700;">{vp.get("handle", "")}</div>'
        f'<div style="color:#34D399;font-size:13px;">● {vp.get("mood", "Online ⚡")}</div>{v_site}</div></div>'
        f'<div style="display:flex;gap:18px;margin-top:12px;font-weight:800;font-size:13px;">'
        f'<span>⚡ {len(v_fol)} Followers (Unlimited)</span><span>👥 {len(v_fr)} / {MAX_FRIENDS} Friends</span></div>'
        f'<p style="margin-top:12px;"><strong>About Me:</strong> {vp.get("bio", "")}</p>'
        f'<p><strong>Who I\'d Like to Meet:</strong> {vp.get("who_to_meet", "")}</p>{v_int_html}</div>',
        unsafe_allow_html=True,
    )
    if v_th.get("vibe_sticker"):
        st.markdown(f'<div class="lex-card" style="text-align:center;"><img src="{v_th["vibe_sticker"]}" style="max-width:100%;max-height:220px;border-radius:10px;" /></div>', unsafe_allow_html=True)
    ac1, ac2, ac3, ac4, ac5 = st.columns([0.24, 0.28, 0.20, 0.14, 0.14])
    is_fol = vp.get("handle") in (th.get("following") or [])
    if ac1.button("✓ Following" if is_fol else "⚡ Follow", use_container_width=True):
        toggle_follow_user(user["handle"], vp["handle"])
        st.rerun()
    is_fr = any(f["handle"].lower() == vp.get("handle", "").lower() for f in st.session_state.lex_friends)
    is_sent = vp.get("handle", "").lower() in {x.lower() for x in (th.get("sent_requests") or [])}
    inc_match = next((x for x in (th.get("incoming_requests") or []) if x.get("handle", "").lower() == vp.get("handle", "").lower()), None)
    if is_fr:
        ac2.button("✓ Friends", disabled=True, use_container_width=True)
    elif inc_match:
        if ac2.button("✓ Accept Request", use_container_width=True):
            accept_friend_request(inc_match)
            st.rerun()
    elif is_sent:
        ac2.button("⏳ Request Sent", disabled=True, use_container_width=True)
    elif len(st.session_state.lex_friends) >= MAX_FRIENDS:
        ac2.button(f"Max {MAX_FRIENDS}", disabled=True, use_container_width=True)
    elif ac2.button("+ Add Friend", use_container_width=True):
        send_friend_request(vp["handle"])
        st.toast(f"Friend request sent to {vp['handle']}!")
        st.rerun()
    if ac3.button("✉️ Message", key=f"pub_msg_{vp['handle']}", use_container_width=True):
        st.session_state["dm_target_override"] = vp["handle"]
        st.session_state["viewing_handle"] = None
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
    v_top8 = vp.get("top8_json") or []
    if v_top8:
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{v_th["accent"]};">✦ {vp.get("display_name", "")}\'s Top 8</strong></div>', unsafe_allow_html=True)
        vt_cols = st.columns(4)
        for i_vt, vfr in enumerate(v_top8[:8]):
            vt_cols[i_vt % 4].markdown(friend_card_html(vfr, "👑 #1" if vfr.get("rank", i_vt + 1) == 1 else f"#{vfr.get('rank', i_vt + 1)}", v_th), unsafe_allow_html=True)
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
def render_social_hub():
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
                    packed = new_post.strip()
                    if post_link.strip():
                        packed += f"\n[LEX_LINK]{normalize_url(post_link)}"
                    if post_img is not None:
                        packed += f"\n[LEX_IMG]{encode_image_data_url(post_img)}"
                    sb.table("lex_posts").insert({"handle": user["handle"], "author": user["name"], "body": packed, "likes": 0}).execute()
                    st.rerun()
        blocked_set = get_blocked_handles()
        posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(25).execute().data or [] if sb else []
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
            if (p.get("handle") or "").lower() != user["handle"].lower():
                if rcols[4].button("🚩 Report", key=f"rep_p_{p['id']}"):
                    block_or_report_member(p.get("handle", ""), "report", f"Reported post #{p['id']}")
                    st.toast("Reported post to LeX Safety")
    return t_friends, t_dm, t_top8, t_studio, t_radar
def render_block(blk: str):
    if blk == "Profile Card":
        b_html = build_live_banner_html(th.get("banner_live", "None"), th.get("banner_img", ""), th["accent"], rad_px)
        if b_html:
            st.markdown(b_html, unsafe_allow_html=True)
        if th.get("marquee_on") and th.get("marquee_text"):
            st.markdown(f'<div class="lex-card" style="padding:6px 12px;"><marquee style="color:{th["accent"]};font-weight:800;letter-spacing:0.06em;">{th["marquee_text"]}</marquee></div>', unsafe_allow_html=True)
        if th.get("pinned_note"):
            st.markdown(f'<div class="lex-card" style="border-width:2.5px;"><span style="color:{th["accent"]};font-weight:900;font-size:11px;">📌 PINNED BULLETIN</span><div style="margin-top:4px;">{th["pinned_note"]}</div></div>', unsafe_allow_html=True)
        av_html = render_avatar_html(user.get("avatar", ""), user.get("name", "L"), th, 84)
        is_owner = user.get("handle", "").strip().lower() in {"@heidi", "@heidiseckman"}
        site_url = user.get("website", "")
        site_badge = founder_studio_link_html(user.get("handle", ""), th["accent"]) if is_owner else (
            f'<div style="margin-top:6px;"><a href="{site_url}" target="_blank" style="color:{th["accent"]};font-weight:700;text-decoration:none;">🔗 {site_url}</a></div>' if site_url else ""
        )
        fol_cnt, ing_cnt, fr_cnt = len(th.get("followers") or []), len(th.get("following") or []), len(st.session_state.lex_friends)
        ints = [(lbl, th.get(k, "")) for lbl, k in [("General", "int_general"), ("Music", "int_music"), ("Movies", "int_movies"), ("TV", "int_tv"), ("Books & Heroes", "int_books")] if th.get(k)]
        int_html = "".join([f'<div style="font-size:12px;margin-top:4px;"><strong style="color:{th["accent"]};">{l}:</strong> {val}</div>' for l, val in ints])
        st.markdown(
            f'<div class="lex-card"><div style="display:flex;align-items:center;gap:14px;">{av_html}'
            f'<div><h2 style="margin:0;color:{th["text"]};">{user["name"]} {founder_badge_html(user["handle"])}</h2>'
            f'<div style="color:{th["accent"]};font-weight:700;">{user["handle"]}</div>'
            f'<div style="color:#34D399;font-size:13px;">● {user["mood"]}</div>{site_badge}</div></div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.04);font-size:12px;font-weight:800;">'
            f'<span>⚡ {fol_cnt} Followers</span><span>✦ {ing_cnt} Following</span><span>👥 {fr_cnt} / {MAX_FRIENDS} Friends</span></div>'
            f'<p style="margin-top:12px;"><strong>About Me:</strong> {user["bio"]}</p>'
            f'<p><strong>Who I\'d Like to Meet:</strong> {user["who_to_meet"]}</p>{int_html}</div>',
            unsafe_allow_html=True,
        )
        if th.get("vibe_sticker"):
            st.markdown(f'<div class="lex-card" style="text-align:center;"><img src="{th["vibe_sticker"]}" style="max-width:100%;max-height:220px;border-radius:10px;" /></div>', unsafe_allow_html=True)
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
            alb_up = st.file_uploader("Upload Photo (Fully clothed only)", type=["png", "jpg", "jpeg", "webp"], key="alb_img_up")
            alb_cap = st.text_input("Photo Caption (Optional)", placeholder="Late night studio session ✦", key="alb_cap_in")
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
    elif blk == "Top 8 Friends":
        st.markdown(f'<div class="lex-card" style="padding:10px 14px;margin-bottom:8px;"><strong style="color:{th["accent"]};font-size:15px;">✦ {user["name"]}\'s Top 8</strong></div>', unsafe_allow_html=True)
        if not st.session_state.lex_top8:
            st.markdown('<div class="lex-card" style="font-size:13px;">No Top 8 friends yet — search real members in <strong>👥 All Friends</strong>, add them, and click <strong>+ Top 8</strong>!</div>', unsafe_allow_html=True)
        else:
            g_cols = st.columns(2)
            for i_t, fr in enumerate(st.session_state.lex_top8[:8]):
                g_cols[i_t % 2].markdown(friend_card_html(fr, "👑 #1" if fr.get("rank", i_t + 1) == 1 else f"#{fr.get('rank', i_t + 1)}"), unsafe_allow_html=True)
    elif blk == "Profile Anthem":
        st.markdown(f'<div class="lex-card" style="padding:12px 16px;margin-bottom:8px;"><strong style="color:{th["accent"]};font-size:15px;">🎵 Main Profile Anthem &amp; Playlist</strong><div style="font-size:11px;color:#A1A1AA;">Synced to your LeX Studio card theme</div></div>', unsafe_allow_html=True)
        mode = st.radio("Main Song Source", ["Popular Song Link", "Built-In LeX Synth"], horizontal=True, key="anthem_src")
        if mode.startswith("Popular"):
            s_url = st.text_input("Spotify / YouTube / Apple Link", value=user.get("custom_song_url", ""), key="s_url_in")
            if st.button("Save Main Anthem 🎵", key="save_s_btn"):
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
            st.markdown(f'<div class="lex-card" style="padding:8px 12px;margin-bottom:6px;"><strong style="color:{th["text"]};">{pi + 1}. {tr["title"]}</strong> <span style="color:{th["accent"]};font-size:12px;">• {tr["artist"]}</span></div>', unsafe_allow_html=True)
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
                if yid and p_title.strip():
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
            ok_w, msg_w = check_safety_and_dress_code(w_msg)
            if not ok_w:
                st.error(msg_w)
            else:
                st.session_state.lex_wall.insert(0, {"sender": user["handle"], "msg": w_msg.strip()})
                save_profile_to_cloud()
                st.rerun()
        for w in st.session_state.lex_wall[:6]:
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
    inc_reqs = list(st.session_state.lex_theme.get("incoming_requests") or [])
    if inc_reqs:
        st.markdown(f"#### 📩 Incoming Friend Requests ({len(inc_reqs)})")
        for r_idx, rq in enumerate(inc_reqs):
            rc1, rc2, rc3, rc4 = st.columns([0.46, 0.18, 0.18, 0.18])
            rc1.markdown(f"**{rq.get('name', rq.get('handle'))}** (`{rq.get('handle')}`)")
            if rc2.button("View", key=f"rq_vw_{r_idx}"):
                st.session_state.viewing_handle = rq["handle"]
                st.rerun()
            if rc3.button("✓ Accept", key=f"rq_acc_{r_idx}"):
                accept_friend_request(rq)
                st.toast(f"You and {rq['handle']} are now friends!")
                st.rerun()
            if rc4.button("✕ Decline", key=f"rq_dec_{r_idx}"):
                decline_friend_request(rq["handle"])
                st.rerun()
    st.markdown("#### 🔍 Search & Discover Everyone on LeX")
    with st.form("global_platform_search_form", clear_on_submit=False):
        sc1, sc2 = st.columns([0.72, 0.28])
        q_in = sc1.text_input("Search entire platform by @handle or name...", placeholder="Type @handle or name (or click Search Platform to browse all)", label_visibility="collapsed")
        do_search = sc2.form_submit_button("🔍 Search Platform", use_container_width=True)
        if do_search:
            st.session_state["lex_global_q"] = clean_handle_str(q_in).lower() if q_in.strip().startswith("@") else q_in.strip().lower()
    q_search = st.session_state.get("lex_global_q", "")
    blocked_set = get_blocked_handles()
    all_profiles = sb.table("lex_profiles").select("handle, display_name, mood, anthem, theme_json").execute().data or [] if sb else []
    my_handles = {f["handle"].lower() for f in st.session_state.lex_friends}
    sent_set = {x.lower() for x in (st.session_state.lex_theme.get("sent_requests") or [])}
    inc_map = {x["handle"].lower(): x for x in inc_reqs if x.get("handle")}
    following_set = set(th.get("following") or [])
    matches = [
        r for r in all_profiles
        if r.get("handle") and r["handle"].lower() != user["handle"].lower() and r["handle"].lower() not in blocked_set
        and (not q_search or q_search in r["handle"].lower() or q_search in (r.get("display_name") or "").lower())
    ]
    st.caption(f"Showing {len(matches)} member(s) on LeX Social")
    if not matches:
        st.info("No matching members found yet. Make sure Supabase public SELECT policy is enabled on lex_profiles!")
    for m in matches[:25]:
        m_fol = len((m.get("theme_json") or {}).get("followers") or [])
        c1, c2, c3, c4, c5, c6, c7 = st.columns([0.28, 0.11, 0.12, 0.14, 0.11, 0.12, 0.12])
        c1.markdown(f"**{m['display_name']}** (`{m['handle']}`) • ⚡ {m_fol}")
        if c2.button("View", key=f"vw_{m['handle']}"):
            st.session_state.viewing_handle = m["handle"]
            st.rerun()
        is_f = m["handle"] in following_set
        if c3.button("✓ Following" if is_f else "⚡ Follow", key=f"fol_{m['handle']}"):
            toggle_follow_user(user["handle"], m["handle"])
            st.rerun()
        mh_low = m["handle"].lower()
        if mh_low in my_handles:
            c4.caption("✓ Friend")
        elif mh_low in inc_map:
            if c4.button("✓ Accept", key=f"acc_s_{m['handle']}"):
                accept_friend_request(inc_map[mh_low])
                st.rerun()
        elif mh_low in sent_set:
            c4.caption("⏳ Sent")
        elif len(st.session_state.lex_friends) >= MAX_FRIENDS:
            c4.caption("Max 1k")
        elif c4.button("+ Request", key=f"addf_{m['handle']}"):
            send_friend_request(m["handle"])
            st.toast(f"Friend request sent to {m['handle']}!")
            st.rerun()
        if c5.button("✉️ Msg", key=f"msg_s_{m['handle']}"):
            st.session_state["dm_target_override"] = m["handle"]
            st.toast(f"Open the ✉️ Messages tab to chat with {m['handle']}!")
        if c6.button("🚫 Block", key=f"blk_{m['handle']}"):
            block_or_report_member(m["handle"], "block")
            st.toast(f"Blocked {m['handle']}")
            st.rerun()
        if c7.button("🚩 Report", key=f"rep_{m['handle']}"):
            block_or_report_member(m["handle"], "report", "Reported from Global Search")
            st.toast(f"Reported {m['handle']}")
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
    blocked_set = get_blocked_handles()
    all_m = sb.table("lex_messages").select("*").order("id", desc=False).limit(200).execute().data or [] if sb else []
    chat_m = [x for x in all_m if not (x.get("body") or "").startswith("[LEX_F")]
    inbox_handles = {x["sender_handle"] for x in chat_m if x["recipient_handle"].lower() == user["handle"].lower()} | {x["recipient_handle"] for x in chat_m if x["sender_handle"].lower() == user["handle"].lower()}
    all_user_handles = {r["handle"] for r in (sb.table("lex_profiles").select("handle").execute().data or []) if r.get("handle") and r["handle"].lower() != user["handle"].lower()} if sb else set()
    dm_targets = sorted({h for h in (all_user_handles | inbox_handles) if h.lower() not in blocked_set})
    ovr = st.session_state.get("dm_target_override", "")
    if ovr and ovr not in dm_targets:
        dm_targets = [ovr] + dm_targets
    def_idx = dm_targets.index(ovr) if (ovr and ovr in dm_targets) else 0
    dc1, dc2 = st.columns([0.55, 0.45])
    picked_chat = dc1.selectbox("Select Any Member to Message", dm_targets, index=def_idx) if dm_targets else ""
    custom_dm = dc2.text_input("Or type any @handle", value="", placeholder="@Roxy")
    active_chat = ("@" + clean_handle_str(custom_dm)) if clean_handle_str(custom_dm) else picked_chat
    if active_chat:
        if active_chat.lower() in blocked_set:
            st.warning("You have blocked this user.")
        else:
            st.caption(f"Direct Message Thread with **{active_chat}** (Open to all members)")
            for m in [x for x in chat_m if {x["sender_handle"].lower(), x["recipient_handle"].lower()} == {user["handle"].lower(), active_chat.lower()}]:
                st.markdown(f"**{m['sender_handle']}:** {m['body']}")
            dm_txt = st.text_input(f"Message {active_chat}...", key="dm_in")
            if st.button("Send DM ✉️") and dm_txt.strip() and sb:
                ok_d, msg_d = check_safety_and_dress_code(dm_txt)
                if not ok_d:
                    st.error(msg_d)
                else:
                    sb.table("lex_messages").insert({"sender_handle": user["handle"], "recipient_handle": active_chat, "body": dm_txt.strip()}).execute()
                    st.session_state["dm_target_override"] = active_chat
                    st.rerun()

with t_top8:
    st.markdown("#### Ranked Top 8 Friends")
    if not st.session_state.lex_top8:
        st.info("Your Top 8 is empty! Add real friends in 👥 All Friends and click + Top 8 on their card.")
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
    l_items = "".join([f'<div class="d-item" draggable="true" data-b="{b}">:: {b}</div>' for b in left_blks])
    r_items = "".join([f'<div class="d-item" draggable="true" data-b="{b}">:: {b}</div>' for b in right_blks])
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
    st.markdown("#### 🎨 LeX Studio x75 // Banners, Presets, Cursors, Animations & Visuals")
    preset_pick = st.selectbox("⚡ One-Click Aesthetic Preset", ["(Keep Current)"] + list(THEME_PRESETS.keys()), key="pr_pick")
    if preset_pick != "(Keep Current)" and st.button("Load Aesthetic Preset ✦", key="load_pr_btn"):
        st.session_state.lex_theme.update(THEME_PRESETS[preset_pick])
        save_profile_to_cloud()
        st.rerun()
    ban_up = st.file_uploader("Upload Custom Top Profile Banner (PNG/JPG/WEBP/GIF — Fully clothed only)", type=["png", "jpg", "jpeg", "webp", "gif"], key="upd_ban")
    bc_a, bc_b = st.columns(2)
    if ban_up is not None and bc_a.button("Set Custom Banner 🖼", key="set_ban_btn"):
        ok_b, msg_b = scan_image_safely(ban_up, "profile banner")
        if not ok_b:
            st.error(msg_b)
        else:
            st.session_state.lex_theme["banner_img"] = encode_image_data_url(ban_up)
            save_profile_to_cloud()
            st.rerun()
    if st.session_state.lex_theme.get("banner_img") and bc_b.button("Clear Custom Banner", key="clr_ban_btn"):
        st.session_state.lex_theme["banner_img"] = ""
        save_profile_to_cloud()
        st.rerun()
    new_av = st.file_uploader("Update Profile Picture (Fully clothed only)", type=["png", "jpg", "jpeg", "webp"], key="upd_av")
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
    tg1, tg2, tg3 = st.columns(3)
    glow_on = tg1.toggle("✨ Neon Borders", value=th.get("glow_borders", True))
    tglow_on = tg2.toggle("🌟 Neon Text Glow", value=th.get("text_glow", True))
    mq_on = tg3.toggle("📢 Marquee Ticker", value=th.get("marquee_on", True))
    mq_txt = st.text_input("Marquee Ticker Text", value=th.get("marquee_text", ""))
    x1, x2, x3 = st.columns(3)
    new_ban_live = x1.selectbox("🌠 Premade Live Banner", LIVE_BANNERS, index=LIVE_BANNERS.index(th["banner_live"]) if th.get("banner_live") in LIVE_BANNERS else 0)
    cur_keys = list(CURSOR_OPTIONS.keys())
    new_cursor = x2.selectbox("🖱 Custom Cursor", cur_keys, index=cur_keys.index(th["cursor_style"]) if th.get("cursor_style") in cur_keys else 0)
    new_anim = x3.selectbox("⚡ Card Animation", CARD_ANIMATIONS, index=CARD_ANIMATIONS.index(th["card_anim"]) if th.get("card_anim") in CARD_ANIMATIONS else 0)
    font_keys = list(FONT_MAP.keys())
    shape_keys = list(AVATAR_SHAPES.keys())
    f_col1, f_col2 = st.columns(2)
    new_font = f_col1.selectbox("Profile Font", font_keys, index=font_keys.index(th["font"]) if th.get("font") in font_keys else 0)
    new_av_shape = f_col2.selectbox("🖼 Profile Pic Shape (16 Shapes)", shape_keys, index=shape_keys.index(th.get("avatar_shape")) if th.get("avatar_shape") in shape_keys else 0)
    new_backdrop = st.selectbox("Wall Background Art (20 Crisp Vectors)", BACKDROP_OPTIONS, index=BACKDROP_OPTIONS.index(th["backdrop"]) if th.get("backdrop") in BACKDROP_OPTIONS else 0)
    new_spray = st.text_input("Custom Spray-Paint / Tag Word", value=th.get("spray_word", "LeX!"))
    borders = ["solid", "dashed", "double"]
    new_border = st.selectbox("Border Style", borders, index=borders.index(th["border_style"]) if th.get("border_style") in borders else 0)
    new_sticker = st.text_input("Vibe Box Sticker / GIF URL (Optional)", value=th.get("vibe_sticker", ""), placeholder="https://...")
    raw_css = st.text_area("Advanced Custom CSS (LeX Override)", value=th.get("custom_css", ""), height=68)
    if st.button("Apply Custom Look ✦"):
        ok_v, msg_v = check_safety_and_dress_code(f"{new_spray} {mq_txt} {new_sticker}")
        if not ok_v:
            st.error(msg_v)
        else:
            st.session_state.lex_theme.update({"bg": new_bg, "card": new_card, "accent": new_acc, "card_opacity": new_op, "card_radius": new_rad, "glow_borders": glow_on, "text_glow": tglow_on, "marquee_on": mq_on, "marquee_text": mq_txt, "font": new_font, "avatar_shape": new_av_shape, "backdrop": new_backdrop, "spray_word": new_spray, "border_style": new_border, "banner_live": new_ban_live, "cursor_style": new_cursor, "card_anim": new_anim, "vibe_sticker": normalize_url(new_sticker), "custom_css": raw_css})
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

with t_radar:
    st.markdown("#### 📡 Inner Circle Radar")
    for friend in st.session_state.lex_top8:
        st.markdown(friend_card_html(friend, f"#{friend['rank']}"), unsafe_allow_html=True)

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only.")
