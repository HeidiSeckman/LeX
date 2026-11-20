import os
import base64
import urllib.parse
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
MAX_FRIENDS = 1000

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
    "card_opacity": 92, "card_radius": 12, "marquee_text": "✦ WELCOME TO MY LeX PROFILE // ZERO ALGORITHMS ✦",
    "marquee_on": True, "pinned_note": "", "custom_css": "",
    "int_general": "", "int_music": "", "int_movies": "", "int_tv": "", "int_books": "",
    "spray_word": "LeX!", "custom_wall": "", "website": "",
    "left_blocks": DEFAULT_LEFT.copy(), "right_blocks": DEFAULT_RIGHT.copy(),
    "followers": [], "following": [], "playlist": [], "albums": [],
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
    return (
        '<span style="display:inline-block;margin-left:8px;padding:3px 10px;border-radius:99px;'
        'background:linear-gradient(90deg,#F59E0B,#EC4899);color:#000000;font-size:11px;'
        'font-weight:900;letter-spacing:0.06em;box-shadow:0 0 12px #EC4899;">'
        '👑 CREATOR &amp; FOUNDER</span>'
    )

def build_backdrop_url(style_name: str, accent: str, tag_word: str = "LeX!") -> str:
    w = (tag_word or "LeX!")[:14].replace("<", "").replace(">", "").replace("&", "")
    if style_name == "Architectural Grid":
        return "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)"
    if style_name == "Checkered Ska / Vans":
        return f"repeating-conic-gradient({accent}28 0% 25%, transparent 0% 50%) 50% / 60px 60px"
    art_map = {
        "Punk Spray-Paint Graffiti": f'<text x="16" y="88" font-family="cursive" font-size="46" font-weight="900" fill="{accent}" fill-opacity="0.30" transform="rotate(-11 70 80)">{w}</text><text x="145" y="190" font-family="cursive" font-size="28" font-weight="900" fill="#FFF" fill-opacity="0.16" transform="rotate(8 190 190)">RIOT // 2026</text><path d="M20 145 Q110 120 230 155" stroke="{accent}" stroke-width="3" stroke-opacity="0.32" fill="none" stroke-dasharray="12 6"/>',
        "Y2K Stars & Sparkles": f'<polygon points="55,18 64,44 92,44 69,60 78,86 55,70 32,86 41,60 18,44 46,44" fill="none" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.36"/><path d="M185,115 L193,140 L218,148 L193,156 L185,181 L177,156 L152,148 L177,140 Z" fill="{accent}" fill-opacity="0.28"/><circle cx="115" cy="195" r="3" fill="#FFF" fill-opacity="0.35"/>',
        "Leopard Rosette Print": f'<path d="M45,35 C65,25 85,42 78,62 C70,80 42,78 36,60 C31,46 35,40 45,35 Z" fill="{accent}" fill-opacity="0.22" stroke="#FFF" stroke-opacity="0.26" stroke-width="4" stroke-dasharray="18 7 12 6"/><circle cx="57" cy="54" r="7" fill="{accent}" fill-opacity="0.34"/><path d="M165,135 C188,125 210,145 200,168 C190,188 158,185 152,165 C146,148 152,140 165,135 Z" fill="{accent}" fill-opacity="0.24" stroke="#FFF" stroke-opacity="0.26" stroke-width="4" stroke-dasharray="20 8 10 6"/><circle cx="177" cy="157" r="8" fill="{accent}" fill-opacity="0.36"/>',
        "Cherry Hearts & Kisses": f'<path d="M60,78 C60,78 26,54 26,35 C26,22 38,16 48,24 C54,28 60,36 60,36 C60,36 66,28 72,24 C82,16 94,22 94,35 C94,54 60,78 60,78 Z" fill="none" stroke="{accent}" stroke-width="2.5" stroke-opacity="0.38"/><path d="M180,178 C180,178 152,158 152,142 C152,131 162,126 170,133 C175,137 180,143 180,143 C180,143 185,137 190,133 C198,126 208,131 208,142 C208,158 180,178 180,178 Z" fill="{accent}" fill-opacity="0.25"/>',
        "Coquette Ribbon Bows": f'<path d="M65,55 L32,35 L38,75 Z M65,55 L98,35 L92,75 Z M65,55 L52,92 M65,55 L78,92" fill="{accent}" fill-opacity="0.25" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.42"/><circle cx="65" cy="55" r="6" fill="#FFF" fill-opacity="0.4"/><path d="M185,155 L155,138 L160,172 Z M185,155 L215,138 L210,172 Z" fill="none" stroke="#FFF" stroke-width="2" stroke-opacity="0.26"/>',
        "Butterfly Dreamscape": f'<path d="M65,60 C35,20 15,55 48,72 C22,85 42,110 65,80 C88,110 108,85 82,72 C115,55 95,20 65,60 Z" fill="{accent}" fill-opacity="0.24" stroke="{accent}" stroke-width="2" stroke-opacity="0.42"/><line x1="65" y1="45" x2="65" y2="92" stroke="#FFF" stroke-width="2" stroke-opacity="0.35"/><path d="M185,155 C160,122 142,152 170,166 C148,177 165,198 185,172 C205,198 222,177 200,166 C228,152 210,122 185,155 Z" fill="none" stroke="#FFF" stroke-width="2" stroke-opacity="0.26"/>',
        "Skull & Crossbones Punk": f'<circle cx="65" cy="52" r="22" fill="none" stroke="#FFF" stroke-width="2.2" stroke-opacity="0.28"/><rect x="53" y="68" width="24" height="14" rx="4" fill="none" stroke="#FFF" stroke-width="2" stroke-opacity="0.28"/><circle cx="57" cy="50" r="4" fill="{accent}" fill-opacity="0.55"/><circle cx="73" cy="50" r="4" fill="{accent}" fill-opacity="0.55"/><line x1="35" y1="95" x2="95" y2="115" stroke="{accent}" stroke-width="2.5" stroke-opacity="0.35"/><line x1="95" y1="95" x2="35" y2="115" stroke="{accent}" stroke-width="2.5" stroke-opacity="0.35"/>',
        "Lightning Bolts & Voltage": f'<polygon points="72,18 38,72 64,72 50,122 96,62 68,62" fill="{accent}" fill-opacity="0.26" stroke="{accent}" stroke-width="2" stroke-opacity="0.45"/><polygon points="192,115 162,162 184,162 172,208 212,154 188,154" fill="none" stroke="#FFF" stroke-width="2" stroke-opacity="0.25"/>',
        "Gothic Bats & Moons": f'<path d="M175,35 A28,28 0 1,0 205,75 A22,22 0 1,1 175,35 Z" fill="{accent}" fill-opacity="0.30"/><path d="M65,145 Q45,125 20,142 Q35,150 42,162 Q55,152 65,166 Q75,152 88,162 Q95,150 110,142 Q85,125 65,145 Z" fill="#FFF" fill-opacity="0.20" stroke="{accent}" stroke-width="1.8" stroke-opacity="0.38"/>',
        "Cyber Matrix Rain": f'<text x="18" y="45" font-family="monospace" font-size="16" font-weight="700" fill="{accent}" fill-opacity="0.36">010110 // {w}</text><text x="85" y="110" font-family="monospace" font-size="16" fill="{accent}" fill-opacity="0.26">1010011101</text><text x="24" y="175" font-family="monospace" font-size="16" fill="#FFF" fill-opacity="0.20">SYS_OVERRIDE</text><line x1="15" y1="55" x2="235" y2="55" stroke="{accent}" stroke-opacity="0.18" stroke-dasharray="4 4"/>',
        "Carbon Fiber Hex": f'<polygon points="60,18 96,38 96,78 60,98 24,78 24,38" fill="none" stroke="{accent}" stroke-opacity="0.34" stroke-width="2.2"/><polygon points="168,112 204,132 204,172 168,192 132,172 132,132" fill="none" stroke="#FFF" stroke-opacity="0.20" stroke-width="2"/>',
        "Retro Cassette & Vinyl": f'<rect x="24" y="28" width="88" height="54" rx="6" fill="none" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.38"/><circle cx="48" cy="55" r="10" fill="none" stroke="#FFF" stroke-width="2" stroke-opacity="0.3"/><circle cx="88" cy="55" r="10" fill="none" stroke="#FFF" stroke-width="2" stroke-opacity="0.3"/><circle cx="180" cy="160" r="36" fill="none" stroke="{accent}" stroke-width="2.2" stroke-opacity="0.32"/><circle cx="180" cy="160" r="10" fill="{accent}" fill-opacity="0.35"/>',
        "Flame & Hotrod Stripes": f'<path d="M55,105 C32,85 38,55 58,32 C55,52 68,56 72,42 C88,65 82,92 55,105 Z" fill="{accent}" fill-opacity="0.30" stroke="{accent}" stroke-width="2" stroke-opacity="0.45"/><line x1="0" y1="135" x2="260" y2="135" stroke="{accent}" stroke-width="3" stroke-opacity="0.25"/><line x1="0" y1="145" x2="260" y2="145" stroke="#FFF" stroke-width="1.5" stroke-opacity="0.18"/>',
        "Crown & Diamond Luxe": f'<polygon points="28,78 28,38 48,56 65,30 82,56 102,38 102,78" fill="none" stroke="{accent}" stroke-width="2.4" stroke-opacity="0.42"/><polygon points="180,125 206,150 180,188 154,150" fill="{accent}" fill-opacity="0.22" stroke="#FFF" stroke-width="2" stroke-opacity="0.3"/>',
        "Rose Thorns & Petals": f'<circle cx="65" cy="55" r="22" fill="none" stroke="{accent}" stroke-width="2.5" stroke-opacity="0.4"/><path d="M52,55 A13,13 0 1,1 78,55 A9,9 0 1,1 58,55" fill="none" stroke="#FFF" stroke-width="2" stroke-opacity="0.3"/><line x1="65" y1="77" x2="65" y2="122" stroke="{accent}" stroke-width="2.4" stroke-opacity="0.4"/><polygon points="65,92 78,86 65,100" fill="{accent}" fill-opacity="0.4"/>',
        "8-Bit Arcade Invaders": f'<path d="M40,40 h10 v10 h20 v-10 h10 v20 h10 v20 h-10 v-10 h-40 v10 h-10 v-20 h10 z" fill="{accent}" fill-opacity="0.30"/><rect x="155" y="135" width="44" height="32" fill="none" stroke="#FFF" stroke-width="2.5" stroke-opacity="0.25"/>',
        "Tactical Urban Camo": f'<polygon points="18,28 68,18 92,46 64,74 22,62" fill="{accent}" fill-opacity="0.22"/><polygon points="125,85 188,72 225,108 192,142 138,125" fill="#FFF" fill-opacity="0.11"/><polygon points="35,148 95,138 118,178 72,208 24,186" fill="{accent}" fill-opacity="0.18"/>',
        "Cosmic Planets & Rings": f'<circle cx="68" cy="62" r="22" fill="{accent}" fill-opacity="0.26" stroke="{accent}" stroke-width="2" stroke-opacity="0.42"/><ellipse cx="68" cy="62" rx="44" ry="11" transform="rotate(-22 68 62)" fill="none" stroke="#FFF" stroke-width="2.2" stroke-opacity="0.34"/><circle cx="185" cy="160" r="14" fill="none" stroke="{accent}" stroke-width="2" stroke-opacity="0.35"/>',
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
    if len(s) == 11 and "/" not in s and "." not in s:
        return s
    for sep in ["youtu.be/", "v=", "/embed/"]:
        if sep in s:
            _, _, tail = s.partition(sep)
            head, _, _ = tail.partition("?")
            head, _, _ = head.partition("&")
            return head.strip("/")[:11]
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
    st.markdown(
        f'<div style="border:1.5px solid {accent};border-radius:10px;padding:8px 10px;background:#08080c;margin:8px 0;">'
        f'<div style="font-size:12px;font-weight:800;color:{accent};margin-bottom:4px;">🎧 NOW SPINNING: {track_label}</div>'
        f'<div style="height:46px;overflow:hidden;border-radius:6px;">'
        f'<iframe width="100%" height="140" src="{src}" frameborder="0" allow="autoplay; encrypted-media" style="margin-top:-92px;"></iframe>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

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
extra_css = (th.get("custom_css") or "").replace("<", "").replace(">", "")

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
                        st.session_state.lex_user = {
                            "user_id": uid, "name": r.get("display_name", "LeX Member"), "handle": r.get("handle", "@Member"),
                            "bio": r.get("bio", ""), "who_to_meet": r.get("who_to_meet", ""),
                            "mood": r.get("mood", "Online Now • Vibing ⚡"), "anthem": r.get("anthem", "Y2K Cobalt Synth"),
                            "custom_song_url": r.get("custom_song_url", ""), "custom_song_title": r.get("custom_song_title", ""),
                            "avatar": tj.get("avatar", ""), "website": tj.get("website", ""),
                        }
                        st.session_state.lex_theme.update(tj)
                        if r.get("top8_json"):
                            st.session_state.lex_top8 = r["top8_json"]
                        st.session_state.lex_friends = tj.get("all_friends") or [i.copy() for i in st.session_state.lex_top8]
                        if r.get("wall_json"):
                            st.session_state.lex_wall = r["wall_json"]
                    else:
                        prefix, _, _ = l_email.strip().partition("@")
                        fname = (prefix or "Member").capitalize()
                        st.session_state.lex_user = {
                            "user_id": uid, "name": fname, "handle": f"@{fname}", "avatar": "", "website": "",
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
            d_name, r_handle = st.text_input("Display Name"), st.text_input("@handle")
            dob = st.date_input("Date of Birth (13+ Only)", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today())
            site_in = st.text_input("Profile Link / Website (Optional)", placeholder="heidiseckman.github.io/lexitech-hub")
            if st.form_submit_button("Create Permanent LeX Account ✦", use_container_width=True) and sb:
                ch = r_handle.strip().lstrip("@").replace(" ", "")
                if calc_age(dob) < 13:
                    st.error("Must be 13+ to join LeX.")
                elif s_email.strip() and len(s_pass) >= 6 and d_name.strip() and ch:
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
    return (
        f'<div class="lex-friend-card"><div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px;">{top_tag}'
        f'<span style="color:#34D399;font-size:11px;font-weight:700;">● ONLINE</span></div>'
        f'<div style="display:flex;align-items:center;gap:10px;">'
        f'<div style="width:42px;height:42px;border-radius:50%;background:radial-gradient(circle,{th["accent"]},#111);border:2px solid {th["accent"]};display:flex;align-items:center;justify-content:center;font-weight:900;color:#FFF;box-shadow:0 0 10px {th["accent"]};">{ini}</div>'
        f'<div><div style="font-weight:800;font-size:14px;color:{th["text"]};">{fr["name"]}</div>'
        f'<div style="color:{th["accent"]};font-size:12px;font-weight:700;">{fr["handle"]}</div></div></div>'
        f'<div style="font-size:11px;color:#D4D4D8;margin-top:8px;">{fr.get("mood", "Vibing ⚡")}</div>'
        f'<div style="margin-top:6px;padding:4px 8px;border-radius:6px;background:rgba(255,255,255,0.05);font-size:10px;color:{th["accent"]};">🎵 {fr.get("anthem", "Y2K Cobalt Synth")}</div></div>'
    )

if st.session_state.viewing_handle and sb:
    v_res = sb.table("lex_profiles").select("*").eq("handle", st.session_state.viewing_handle).execute().data
    vp = next(iter(v_res), None) if isinstance(v_res, list) else v_res
    if isinstance(vp, dict):
        vtj = vp.get("theme_json") or {}
        v_fol, v_fr = list(vtj.get("followers") or []), list(vtj.get("all_friends") or [])
        v_av = f'<img src="{vtj["avatar"]}" class="lex-avatar" />' if vtj.get("avatar") else f'<div class="lex-avatar-fallback">{(vp.get("display_name", "L")[:1] or "L").upper()}</div>'
        v_site = f'<div style="margin-top:6px;"><a href="{vtj["website"]}" target="_blank" style="color:{th["accent"]};font-weight:700;">🔗 {vtj["website"]}</a></div>' if vtj.get("website") else ""
        st.markdown(
            f'<div class="lex-card"><div style="display:flex;align-items:center;gap:16px;">{v_av}'
            f'<div><h2 style="margin:0;">{vp.get("display_name", "")}{founder_badge_html(vp.get("handle", ""))}</h2>'
            f'<div style="color:{th["accent"]};font-weight:700;">{vp.get("handle", "")}</div>'
            f'<div style="color:#34D399;font-size:13px;">● {vp.get("mood", "Online ⚡")}</div>{v_site}</div></div>'
            f'<div style="display:flex;gap:18px;margin-top:12px;font-weight:800;font-size:13px;">'
            f'<span>⚡ {len(v_fol)} Followers (Unlimited)</span><span>👥 {len(v_fr)} / {MAX_FRIENDS} Friends</span></div>'
            f'<p style="margin-top:12px;"><strong>About Me:</strong> {vp.get("bio", "")}</p></div>',
            unsafe_allow_html=True,
        )
        ac1, ac2 = st.columns(2)
        is_fol = vp.get("handle") in (th.get("following") or [])
        if ac1.button("✓ Following (Unfollow)" if is_fol else "⚡ Follow Creator (Unlimited)", use_container_width=True):
            toggle_follow_user(user["handle"], vp["handle"])
            st.rerun()
        is_fr = any(f["handle"].lower() == vp.get("handle", "").lower() for f in st.session_state.lex_friends)
        if is_fr:
            ac2.button("✓ In Your Friends List", disabled=True, use_container_width=True)
        elif len(st.session_state.lex_friends) >= MAX_FRIENDS:
            ac2.button(f"Max {MAX_FRIENDS} Friends Reached", disabled=True, use_container_width=True)
        elif ac2.button(f"+ Add Friend ({len(st.session_state.lex_friends)}/{MAX_FRIENDS})", use_container_width=True):
            st.session_state.lex_friends.append({"handle": vp["handle"], "name": vp["display_name"], "mood": vp.get("mood", "Online ⚡"), "anthem": vp.get("anthem", "Y2K Cobalt Synth")})
            save_profile_to_cloud()
            st.rerun()
        if vp.get("custom_song_url"):
            render_popular_song_embed(vp["custom_song_url"])
        v_albs = list(vtj.get("albums") or [])
        if v_albs:
            st.markdown(f"#### 📸 {vp.get('display_name', '')}'s Featured Albums")
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
            post_img = fc1.file_uploader("Attach Photo", type=["png", "jpg", "jpeg", "webp"], key="fp_img")
            post_link = fc2.text_input("Attach Link / URL", placeholder="https://...", key="fp_link")
            if st.form_submit_button("Publish Status ✦") and (new_post.strip() or post_img or post_link.strip()) and sb:
                packed = new_post.strip()
                if post_link.strip():
                    packed += f"\n[LEX_LINK]{normalize_url(post_link)}"
                if post_img is not None:
                    packed += f"\n[LEX_IMG]{encode_image_data_url(post_img)}"
                sb.table("lex_posts").insert({"handle": user["handle"], "author": user["name"], "body": packed, "likes": 0}).execute()
                st.rerun()

        posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(25).execute().data or [] if sb else []
        for p in posts:
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
            rcols = st.columns(4)
            for idx_e, emo in enumerate(["🔥", "💖", "🎸", "💀"]):
                if rcols[idx_e].button(f"{emo} {st.session_state[rx_key][emo]}", key=f"b_{p['id']}_{emo}"):
                    st.session_state[rx_key][emo] += 1
                    if emo == "🔥" and sb:
                        sb.table("lex_posts").update({"likes": st.session_state[rx_key]["🔥"]}).eq("id", p["id"]).execute()
                    st.rerun()
    return t_friends, t_dm, t_top8, t_studio, t_radar

def render_block(blk: str):
    if blk == "Profile Card":
        if th.get("marquee_on") and th.get("marquee_text"):
            st.markdown(f'<div class="lex-card" style="padding:6px 12px;"><marquee style="color:{th["accent"]};font-weight:800;letter-spacing:0.06em;">{th["marquee_text"]}</marquee></div>', unsafe_allow_html=True)
        if th.get("pinned_note"):
            st.markdown(f'<div class="lex-card" style="border-width:2.5px;"><span style="color:{th["accent"]};font-weight:900;font-size:11px;">📌 PINNED BULLETIN</span><div style="margin-top:4px;">{th["pinned_note"]}</div></div>', unsafe_allow_html=True)
        av_html = f'<img src="{user["avatar"]}" class="lex-avatar" />' if user.get("avatar") else f'<div class="lex-avatar-fallback">{(user["name"][:1] or "L").upper()}</div>'
        site_url = user.get("website", "")
        site_badge = f'<div style="margin-top:6px;"><a href="{site_url}" target="_blank" style="color:{th["accent"]};font-weight:700;text-decoration:none;">🔗 {site_url}</a></div>' if site_url else ""
        fol_cnt, ing_cnt, fr_cnt = len(th.get("followers") or []), len(th.get("following") or []), len(st.session_state.lex_friends)
        ints = [(lbl, th.get(k, "")) for lbl, k in [("General", "int_general"), ("Music", "int_music"), ("Movies", "int_movies"), ("TV", "int_tv"), ("Books & Heroes", "int_books")] if th.get(k)]
        int_html = "".join([f'<div style="font-size:12px;margin-top:4px;"><strong style="color:{th["accent"]};">{l}:</strong> {v}</div>' for l, v in ints])
        st.markdown(
            f'<div class="lex-card"><div style="display:flex;align-items:center;gap:14px;">{av_html}'
            f'<div><h2 style="margin:0;color:{th["text"]};">{user["name"]}{founder_badge_html(user["handle"])}</h2>'
            f'<div style="color:{th["accent"]};font-weight:700;">{user["handle"]}</div>'
            f'<div style="color:#34D399;font-size:13px;">● {user["mood"]}</div>{site_badge}</div></div>'
            f'<div style="display:flex;flex-wrap:wrap;gap:14px;margin-top:12px;padding:8px 10px;border-radius:8px;background:rgba(255,255,255,0.04);font-size:12px;font-weight:800;">'
            f'<span>⚡ {fol_cnt} Followers</span><span>✦ {ing_cnt} Following</span><span>👥 {fr_cnt} / {MAX_FRIENDS} Friends</span></div>'
            f'<p style="margin-top:12px;"><strong>About Me:</strong> {user["bio"]}</p>'
            f'<p><strong>Who I\'d Like to Meet:</strong> {user["who_to_meet"]}</p>{int_html}</div>',
            unsafe_allow_html=True,
        )
    elif blk == "Photo Albums":
        st.markdown(f"#### 📸 {user['name']}'s Photo Albums")
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
            alb_up = st.file_uploader("Upload Photo", type=["png", "jpg", "jpeg", "webp"], key="alb_img_up")
            alb_cap = st.text_input("Photo Caption (Optional)", placeholder="Late night studio session ✦", key="alb_cap_in")
            if st.button("Add Photo to Album ✦", key="alb_save_btn"):
                t_clean = new_alb_name.strip()
                if t_clean and alb_up is not None:
                    img_data = encode_image_data_url(alb_up)
                    found = next((a for a in albums if a["title"].lower() == t_clean.lower()), None)
                    if found:
                        found["photos"].append({"img": img_data, "caption": alb_cap.strip()})
                    else:
                        albums.append({"title": t_clean, "photos": [{"img": img_data, "caption": alb_cap.strip()}]})
                    st.session_state.lex_theme["albums"] = albums
                    save_profile_to_cloud()
                    st.rerun()
