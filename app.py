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
SVG_NS = "http://" + ".".join(["www", "w3", "org"]) + "/2000/svg"
GFONTS_BASE = "https://" + ".".join(["fonts", "googleapis", "com"]) + "/css2?family="
SPOTIFY_EMBED = "https://" + ".".join(["open", "spotify", "com"]) + "/embed/track/"

@st.cache_resource
def get_sb():
    url = st.secrets.get("SUPABASE_URL", "")
    key = st.secrets.get("SUPABASE_KEY", "")
    if not url or not key:
        return None
    return create_client(url, key)

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
    "Hot Pink Leopard Print", "Cherry Hearts & Kisses", "Coquette Ribbon Bows",
    "Butterfly Dreamscape", "Checkered Ska / Vans", "Skull & Crossbones Punk",
    "Lightning Bolts & Voltage", "Gothic Bats & Crescent Moons", "Cyber Matrix Rain",
    "Carbon Fiber Hex", "Retro Cassette & Vinyl", "Flame & Hotrod Stripes",
    "Crown & Diamond Luxe", "Rose Thorns & Petals", "8-Bit Arcade Invaders",
    "Camo Streetwear", "Cosmic Planets & Rings",
]

DEFAULT_BLOCKS = ["Profile Card", "Top 8 Friends", "Profile Anthem", "Profile Wall"]

DEFAULT_THEME = {
    "name": "LexiTech Obsidian (Official)", "bg": "#000000", "card": "#070709",
    "accent": "#EC4899", "text": "#F4F4F5", "font": "Clean Studio Sans",
    "backdrop": "Architectural Grid", "border_style": "solid", "spray_word": "LeX!",
    "custom_wall": "", "website": "", "layout_side": "Left (Classic)", "block_order": DEFAULT_BLOCKS.copy(),
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
def build_backdrop_url(style_name: str, accent: str, tag_word: str = "LeX!") -> str:
    w = (tag_word or "LeX!")[:14].replace("<", "").replace(">", "").replace("&", "")
    if style_name == "Architectural Grid":
        return "linear-gradient(to right, rgba(255,255,255,0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.035) 1px, transparent 1px)"
    if style_name == "Checkered Ska / Vans":
        return f"repeating-conic-gradient({accent}26 0% 25%, transparent 0% 50%) 50% / 64px 64px"
    art_map = {
        "Punk Spray-Paint Graffiti": f'<text x="20" y="90" font-family="cursive" font-size="48" font-weight="900" fill="{accent}" fill-opacity="0.28" transform="rotate(-10 80 80)">{w}</text><text x="170" y="195" font-family="cursive" font-size="32" font-weight="900" fill="#FFF" fill-opacity="0.14" transform="rotate(8 210 190)">RIOT // 2026</text><circle cx="140" cy="50" r="4" fill="{accent}" fill-opacity="0.45"/>',
        "Y2K Stars & Sparkles": f'<text x="25" y="65" font-size="36" fill="{accent}" fill-opacity="0.32">✦</text><text x="165" y="145" font-size="30" fill="#FFF" fill-opacity="0.20">★</text><text x="80" y="205" font-size="24" fill="{accent}" fill-opacity="0.28">✧</text>',
        "Hot Pink Leopard Print": f'<ellipse cx="60" cy="60" rx="22" ry="16" fill="{accent}" fill-opacity="0.22" stroke="#FFF" stroke-opacity="0.18" stroke-width="4" stroke-dasharray="14 6"/><ellipse cx="195" cy="165" rx="26" ry="18" fill="{accent}" fill-opacity="0.25" stroke="#FFF" stroke-opacity="0.18" stroke-width="4" stroke-dasharray="16 7"/>',
        "Cherry Hearts & Kisses": f'<text x="28" y="70" font-size="34" fill="{accent}" fill-opacity="0.32">💖</text><text x="160" y="150" font-size="32" fill="{accent}" fill-opacity="0.28">💋</text><text x="75" y="210" font-size="28" fill="#FFF" fill-opacity="0.20">🍒</text>',
        "Coquette Ribbon Bows": f'<text x="30" y="72" font-size="36" fill="{accent}" fill-opacity="0.32">🎀</text><text x="165" y="165" font-size="30" fill="{accent}" fill-opacity="0.26">🎀</text><circle cx="115" cy="115" r="4" fill="#FFF" fill-opacity="0.25"/>',
        "Butterfly Dreamscape": f'<text x="30" y="75" font-size="36" fill="{accent}" fill-opacity="0.32">🦋</text><text x="165" y="160" font-size="32" fill="#FFF" fill-opacity="0.22">🦋</text><text x="85" y="215" font-size="22" fill="{accent}" fill-opacity="0.26">✨</text>',
        "Skull & Crossbones Punk": f'<text x="28" y="75" font-size="36" fill="#FFF" fill-opacity="0.22">💀</text><text x="160" y="165" font-size="34" fill="{accent}" fill-opacity="0.30">☠️</text><text x="85" y="210" font-size="22" fill="{accent}" fill-opacity="0.28">✖</text>',
        "Lightning Bolts & Voltage": f'<text x="30" y="75" font-size="38" fill="{accent}" fill-opacity="0.34">⚡</text><text x="165" y="170" font-size="34" fill="#FFF" fill-opacity="0.20">⚡</text>',
        "Gothic Bats & Crescent Moons": f'<text x="28" y="72" font-size="34" fill="#FFF" fill-opacity="0.22">🦇</text><text x="160" y="160" font-size="34" fill="{accent}" fill-opacity="0.30">🌙</text><text x="80" y="210" font-size="24" fill="{accent}" fill-opacity="0.25">🕸️</text>',
        "Cyber Matrix Rain": f'<text x="20" y="60" font-family="monospace" font-size="18" fill="{accent}" fill-opacity="0.32">010110 // {w}</text><text x="90" y="140" font-family="monospace" font-size="18" fill="{accent}" fill-opacity="0.24">1010011101</text><text x="30" y="210" font-family="monospace" font-size="18" fill="#FFF" fill-opacity="0.16">SYS_ONLINE</text>',
        "Carbon Fiber Hex": f'<polygon points="60,20 95,40 95,80 60,100 25,80 25,40" fill="none" stroke="{accent}" stroke-opacity="0.28" stroke-width="2"/><polygon points="165,110 200,130 200,170 165,190 130,170 130,130" fill="none" stroke="#FFF" stroke-opacity="0.16" stroke-width="2"/>',
        "Retro Cassette & Vinyl": f'<text x="28" y="75" font-size="36" fill="{accent}" fill-opacity="0.30">📼</text><text x="160" y="165" font-size="36" fill="#FFF" fill-opacity="0.22">💿</text><text x="80" y="215" font-size="24" fill="{accent}" fill-opacity="0.28">🎧</text>',
        "Flame & Hotrod Stripes": f'<text x="28" y="78" font-size="38" fill="{accent}" fill-opacity="0.34">🔥</text><text x="160" y="170" font-size="36" fill="{accent}" fill-opacity="0.28">🔥</text><line x1="0" y1="120" x2="260" y2="120" stroke="{accent}" stroke-opacity="0.22" stroke-width="3"/>',
        "Crown & Diamond Luxe": f'<text x="30" y="74" font-size="34" fill="{accent}" fill-opacity="0.32">👑</text><text x="162" y="165" font-size="32" fill="#FFF" fill-opacity="0.24">💎</text>',
        "Rose Thorns & Petals": f'<text x="30" y="75" font-size="36" fill="{accent}" fill-opacity="0.32">🥀</text><text x="162" y="165" font-size="34" fill="{accent}" fill-opacity="0.28">🌹</text>',
        "8-Bit Arcade Invaders": f'<text x="28" y="75" font-size="34" fill="{accent}" fill-opacity="0.32">👾</text><text x="160" y="165" font-size="34" fill="#FFF" fill-opacity="0.22">🕹️</text>',
        "Camo Streetwear": f'<ellipse cx="65" cy="65" rx="42" ry="22" fill="{accent}" fill-opacity="0.20"/><ellipse cx="175" cy="155" rx="48" ry="25" fill="#FFF" fill-opacity="0.10"/><ellipse cx="105" cy="195" rx="35" ry="18" fill="{accent}" fill-opacity="0.16"/>',
        "Cosmic Planets & Rings": f'<text x="28" y="75" font-size="36" fill="{accent}" fill-opacity="0.32">🪐</text><text x="162" y="165" font-size="30" fill="#FFF" fill-opacity="0.22">🚀</text><text x="85" y="212" font-size="22" fill="{accent}" fill-opacity="0.28">✨</text>',
    }
    body = art_map.get(style_name, art_map["Punk Spray-Paint Graffiti"])
    raw_svg = f'{SV_OPEN}xmlns="{SVG_NS}" width="260" height="240">{body}{SV_CLOSE}'
    return f'url("data:image/svg+xml,{urllib.parse.quote(raw_svg)}")'

def calc_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def encode_image_data_url(uploaded_file) -> str:
    if uploaded_file is None:
        return ""
    raw = uploaded_file.getvalue()
    b64 = base64.b64encode(raw).decode("ascii")
    mime = uploaded_file.type or "image/png"
    return f"data:{mime};base64,{b64}"

def normalize_url(raw_url: str) -> str:
    clean = (raw_url or "").strip()
    if not clean:
        return ""
    return clean if (clean.startswith("http://") or clean.startswith("https://")) else ("https://" + clean)

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
def remix_theme_from_prompt(prompt: str) -> dict:
    p = (prompt or "").lower()
    th = st.session_state.lex_theme.copy()
    if any(k in p for k in ["punk", "spray", "graffiti", "grunge", "rock", "riot"]):
        th.update({
            "name": "Girl Punk Spray-Paint", "bg": "#0A040A", "card": "#170917",
            "accent": "#FF1E8A", "text": "#FFF0F7", "font": "Girl Punk / Spray Marker",
            "backdrop": "Punk Spray-Paint Graffiti", "border_style": "dashed", "spray_word": "RIOT // LeX",
        })
    elif any(k in p for k in ["goth", "emo", "dark", "vampire", "bat"]):
        th.update({
            "name": "2004 Mall Goth", "bg": "#050307", "card": "#110B14",
            "accent": "#C084FC", "text": "#F3E8FF", "font": "Gothic Editorial",
            "backdrop": "Gothic Bats & Crescent Moons", "border_style": "double", "spray_word": "NOCTURNE",
        })
    elif any(k in p for k in ["y2k", "star", "glitter", "sparkle", "2006", "pop"]):
        th.update({
            "name": "Y2K Starlight Chrome", "bg": "#050A18", "card": "#0D1730",
            "accent": "#38BDF8", "text": "#F0F9FF", "font": "Y2K Arcade Pixel",
            "backdrop": "Y2K Stars & Sparkles", "border_style": "solid", "spray_word": "2006 ★",
        })
    elif any(k in p for k in ["cyber", "matrix", "hacker", "glitch", "neon"]):
        th.update({
            "name": "Cyber Glitch Matrix", "bg": "#020A06", "card": "#071910",
            "accent": "#10B981", "text": "#ECFDF5", "font": "Cyber Glitch",
            "backdrop": "Cyber Matrix Rain", "border_style": "solid", "spray_word": "SYS_ONLINE",
        })
    return th

def render_popular_song_embed(url: str) -> bool:
    clean = (url or "").strip()
    if not clean:
        return False
    sp_host = ".".join(["open", "spotify", "com"]) + "/track/"
    if sp_host in clean:
        track_id = clean.split(sp_host).split("?").strip("/")
        components.iframe(f"{SPOTIFY_EMBED}{track_id}?utm_source=generator&theme=0", height=152)
        return True
    if "youtube.com" in clean or "youtu.be/" in clean:
        st.video(clean)
        return True
    ap_host = ".".join(["music", "apple", "com"])
    if ap_host in clean and ("embed." + ap_host) not in clean:
        components.iframe(clean.replace(ap_host, "embed." + ap_host), height=175)
        return True
    return False

for k, v in [("lex_user", None), ("lex_theme", DEFAULT_THEME.copy()), ("lex_top8", [i.copy() for i in DEFAULT_TOP8]), ("lex_friends", [i.copy() for i in DEFAULT_TOP8])]:
    if k not in st.session_state:
        st.session_state[k] = v
if "lex_wall" not in st.session_state:
    st.session_state.lex_wall = [{"sender": "@LeX", "msg": "Welcome to LeX! Drop a wall note anytime ✦"}]

th = st.session_state.lex_theme
g_font_name, css_font_family = FONT_MAP.get(th.get("font", "Clean Studio Sans"), FONT_MAP["Clean Studio Sans"])
bg_pattern = build_backdrop_url(th.get("backdrop", "Architectural Grid"), th["accent"], th.get("spray_word", "LeX!"))
custom_wall = th.get("custom_wall", "")
bg_css_img = f'url("{custom_wall}")' if custom_wall else bg_pattern
bg_size = "cover" if custom_wall else ("56px 56px" if th.get("backdrop") == "Architectural Grid" else "260px 240px")
bg_repeat = "no-repeat" if custom_wall else "repeat"

css = (
    f'{LK_OPEN}rel="stylesheet" href="{GFONTS_BASE}{g_font_name.replace(" ", "+")}&display=swap" />' + ST_OPEN
    + f'[data-testid="stAppViewContainer"], .stApp {{ background-color: {th["bg"]} !important; background-image: {bg_css_img} !important; background-size: {bg_size} !important; background-repeat: {bg_repeat} !important; background-attachment: fixed !important; color: {th["text"]} !important; }}'
    + '[data-testid="stHeader"], [data-testid="stMain"] { background: transparent !important; }'
    + f".lex-banner {{ background: radial-gradient(circle at 15% 50%, rgba(236,72,153,0.18), {th['card']} 65%); border: 2px {th['border_style']} {th['accent']}; border-radius: 14px; padding: 18px 24px; margin-bottom: 16px; }}"
    + f".lex-wordmark {{ font-family: {css_font_family}; font-size: 38px; font-weight: 800; color: #FFFFFF; text-shadow: 0 0 22px {th['accent']}; }}"
    + f".lex-card {{ background: {th['card']}; border: 1.5px {th['border_style']} {th['accent']}; border-radius: 12px; padding: 16px 18px; margin-bottom: 12px; }}"
    + f".lex-avatar {{ width: 80px; height: 80px; border-radius: 50%; object-fit: cover; border: 2.5px solid {th['accent']}; box-shadow: 0 0 16px {th['accent']}; }}"
    + f".lex-avatar-fallback {{ width: 80px; height: 80px; border-radius: 50%; background: {th['accent']}; color: #000; font-weight: 900; font-size: 30px; display: flex; align-items: center; justify-content: center; }}"
    + ST_CLOSE
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
                    prof = sb.table("lex_profiles").select("*").eq("user_id", res.user.id).execute().data
                    if prof:
                        r = prof
                        tj = r.get("theme_json") or {}
                        st.session_state.lex_user = {
                            "user_id": res.user.id, "name": r["display_name"], "handle": r["handle"],
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
if st.button("Sign Out"):
    st.session_state.lex_user = None
    st.rerun()

def render_profile_blocks():
    order = th.get("block_order") or DEFAULT_BLOCKS
    for blk in order:
        if blk == "Profile Card":
            av_html = f'<img src="{user["avatar"]}" class="lex-avatar" />' if user.get("avatar") else f'<div class="lex-avatar-fallback">{(user["name"][:1] or "L").upper()}</div>'
            site_url = user.get("website", "")
            site_badge = f'<div style="margin-top:6px;"><a href="{site_url}" target="_blank" style="color:{th["accent"]};font-weight:700;text-decoration:none;">🔗 {site_url}</a></div>' if site_url else ""
            st.markdown(
                f'<div class="lex-card"><div style="display:flex;align-items:center;gap:14px;">{av_html}'
                f'<div><h2 style="margin:0;color:{th["text"]};">{user["name"]}</h2>'
                f'<div style="color:{th["accent"]};font-weight:700;">{user["handle"]}</div>'
                f'<div style="color:#34D399;font-size:13px;">● {user["mood"]}</div>{site_badge}</div></div>'
                f'<p style="margin-top:12px;"><strong>About Me:</strong> {user["bio"]}</p>'
                f'<p><strong>Who I\'d Like to Meet:</strong> {user["who_to_meet"]}</p></div>',
                unsafe_allow_html=True,
            )
        elif blk == "Top 8 Friends":
            st.markdown(f"#### ✦ {user['name']}'s Top 8")
            g_cols = st.columns(4)
            for i_t, fr in enumerate(st.session_state.lex_top8[:8]):
                g_cols[i_t % 4].markdown(
                    f'<div class="lex-card" style="padding:8px;text-align:center;">'
                    f'<div style="font-size:11px;color:{th["accent"]};font-weight:700;">#{fr["rank"]}</div>'
                    f'<div style="font-size:12px;font-weight:700;">{fr["name"][:10]}</div>'
                    f'<div style="font-size:10px;color:#A1A1AA;">{fr["handle"]}</div></div>',
                    unsafe_allow_html=True,
                )
        elif blk == "Profile Anthem":
            st.markdown("#### 🎵 Profile Anthem")
            mode = st.radio("Audio Source", ["Popular Song Link", "Built-In LeX Synth"], horizontal=True)
            if mode.startswith("Popular"):
                s_url = st.text_input("Spotify / YouTube / Apple Link", value=user.get("custom_song_url", ""))
                if st.button("Save Song 🎵"):
                    user["custom_song_url"] = s_url.strip()
                    save_profile_to_cloud()
                    st.rerun()
                if user.get("custom_song_url"):
                    render_popular_song_embed(user["custom_song_url"])
            else:
                pick_synth = st.selectbox("Synth Track", list(ANTHEM_TRACKS.keys()))
                st.audio(generate_anthem_wav(pick_synth), format="audio/wav")
        elif blk == "Profile Wall":
            st.markdown("#### 💬 Profile Wall")
            w_msg = st.text_input("Sign profile wall...", key="wall_in")
            if st.button("Post Wall Note") and w_msg.strip():
                st.session_state.lex_wall.insert(0, {"sender": user["handle"], "msg": w_msg.strip()})
                save_profile_to_cloud()
                st.rerun()
            for w in st.session_state.lex_wall[:6]:
                st.markdown(f'<div class="lex-card"><strong>{w["sender"]}:</strong> {w["msg"]}</div>', unsafe_allow_html=True)

is_flipped = th.get("layout_side") == "Right (Flipped)"
if is_flipped:
    main_col, prof_col = st.columns([1.45, 1.0], gap="large")
else:
    prof_col, main_col = st.columns([1.0, 1.45], gap="large")

with prof_col:
    render_profile_blocks()
with main_col:
    t_feed, t_friends, t_dm, t_top8, t_studio, t_radar = st.tabs([
        "📰 Feed", "👥 All Friends", "✉ Messages", "✦ Top 8", "🎨 Theme & Layout", "📡 Radar"
    ])
    with t_feed:
        with st.form("feed_post_form", clear_on_submit=True):
            new_post = st.text_area("Share a status update or lyric...", height=68)
            if st.form_submit_button("Publish ✦") and new_post.strip() and sb:
                sb.table("lex_posts").insert({"handle": user["handle"], "author": user["name"], "body": new_post.strip(), "likes": 0}).execute()
                st.rerun()
        posts = sb.table("lex_posts").select("*").order("id", desc=True).limit(25).execute().data or [] if sb else []
        for p in posts:
            st.markdown(f'<div class="lex-card"><strong>{p["author"]}</strong> <span style="color:{th["accent"]};">{p["handle"]}</span><p style="margin-top:6px;">{p["body"]}</p></div>', unsafe_allow_html=True)
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

    with t_friends:
        st.markdown("#### 🔍 Search People on LeX")
        q_search = st.text_input("Search by @handle or name...", key="people_q").strip().lower()
        all_profiles = sb.table("lex_profiles").select("handle, display_name, mood, anthem").execute().data or [] if sb else []
        my_handles = {f["handle"].lower() for f in st.session_state.lex_friends}
        matches = [r for r in all_profiles if r["handle"] != user["handle"] and (not q_search or q_search in r["handle"].lower() or q_search in r["display_name"].lower())]
        for m in matches[:12]:
            c_info, c_btn = st.columns([0.72, 0.28])
            c_info.markdown(f"**{m['display_name']}** (`{m['handle']}`) — {m.get('mood', '')}")
            if m["handle"].lower() not in my_handles:
                if c_btn.button("+ Add Friend", key=f"addf_{m['handle']}"):
                    st.session_state.lex_friends.append({"handle": m["handle"], "name": m["display_name"], "mood": m.get("mood", "Online ⚡"), "anthem": m.get("anthem", "Y2K Cobalt Synth")})
                    save_profile_to_cloud()
                    st.rerun()
            else:
                c_btn.caption("✓ Friends")
        st.markdown(f"#### 👥 All Friends ({len(st.session_state.lex_friends)})")
        for idx_f, fr in enumerate(st.session_state.lex_friends):
            fc1, fc2, fc3 = st.columns([0.56, 0.22, 0.22])
            fc1.markdown(f"**{fr['name']}** (`{fr['handle']}`) • {fr.get('mood', '')}")
            if fc2.button("★ Top 8", key=f"t8p_{idx_f}") and len(st.session_state.lex_top8) < 8:
                if not any(t["handle"] == fr["handle"] for t in st.session_state.lex_top8):
                    st.session_state.lex_top8.append({**fr, "rank": len(st.session_state.lex_top8) + 1})
                    save_profile_to_cloud()
                    st.rerun()
            if fc3.button("Delete ✕", key=f"delf_{idx_f}"):
                st.session_state.lex_friends.pop(idx_f)
                st.session_state.lex_top8 = [t for t in st.session_state.lex_top8 if t["handle"] != fr["handle"]]
                for r_i, item in enumerate(st.session_state.lex_top8):
                    item["rank"] = r_i + 1
                save_profile_to_cloud()
                st.rerun()

    with t_dm:
        dm_targets = [f["handle"] for f in st.session_state.lex_friends if f["handle"] != user["handle"]]
        active_chat = st.selectbox("Message Friend", dm_targets or ["@LeX"])
        all_m = sb.table("lex_messages").select("*").order("id", desc=False).limit(100).execute().data or [] if sb else []
        for m in [x for x in all_m if {x["sender_handle"], x["recipient_handle"]} == {user["handle"], active_chat}]:
            st.markdown(f"**{m['sender_handle']}:** {m['body']}")
        dm_txt = st.text_input(f"Message {active_chat}...", key="dm_in")
        if st.button("Send DM") and dm_txt.strip() and sb:
            sb.table("lex_messages").insert({"sender_handle": user["handle"], "recipient_handle": active_chat, "body": dm_txt.strip()}).execute()
            st.rerun()

    with t_top8:
        st.markdown("#### Ranked Top 8 Friends")
        for idx, friend in enumerate(st.session_state.lex_top8):
            st.markdown(f'<div class="lex-card"><strong>#{friend["rank"]} {friend["name"]}</strong> <span style="color:{th["accent"]};">{friend["handle"]}</span> — {friend["mood"]}</div>', unsafe_allow_html=True)
            b1, b2 = st.columns(2)
            if idx > 0 and b1.button("Move Up ↑", key=f"up_{idx}"):
                lst = st.session_state.lex_top8
                lst[idx], lst[idx - 1] = lst[idx - 1], lst[idx]
                for r_i, item in enumerate(lst):
                    item["rank"] = r_i + 1
                save_profile_to_cloud()
                st.rerun()
            if b2.button("Remove from Top 8", key=f"rm8_{idx}"):
                st.session_state.lex_top8.pop(idx)
                for r_i, item in enumerate(st.session_state.lex_top8):
                    item["rank"] = r_i + 1
                save_profile_to_cloud()
                st.rerun()
    with t_studio:
        st.markdown("#### 📐 Page Layout & Movable Profile Blocks")
        cur_side = th.get("layout_side", "Left (Classic)")
        side_pick = st.radio("Profile Column Side", ["Left (Classic)", "Right (Flipped)"], index=1 if cur_side == "Right (Flipped)" else 0, horizontal=True)
        if side_pick != cur_side:
            st.session_state.lex_theme["layout_side"] = side_pick
            save_profile_to_cloud()
            st.rerun()

        blk_list = list(th.get("block_order") or DEFAULT_BLOCKS)
        for bi, bname in enumerate(blk_list):
            bc1, bc2, bc3 = st.columns([0.64, 0.18, 0.18])
            bc1.markdown(f"**{bi + 1}. {bname}**")
            if bi > 0 and bc2.button("↑", key=f"bup_{bi}"):
                blk_list[bi], blk_list[bi - 1] = blk_list[bi - 1], blk_list[bi]
                st.session_state.lex_theme["block_order"] = blk_list
                save_profile_to_cloud()
                st.rerun()
            if bi < len(blk_list) - 1 and bc3.button("↓", key=f"bdn_{bi}"):
                blk_list[bi], blk_list[bi + 1] = blk_list[bi + 1], blk_list[bi]
                st.session_state.lex_theme["block_order"] = blk_list
                save_profile_to_cloud()
                st.rerun()

        st.markdown("#### 🎨 Colors, Fonts & 20 Wall Backgrounds")
        new_av = st.file_uploader("Update Profile Picture", type=["png", "jpg", "jpeg", "webp"], key="upd_av")
        if new_av is not None and st.button("Save New Profile Picture"):
            user["avatar"] = encode_image_data_url(new_av)
            save_profile_to_cloud()
            st.rerun()

        wall_up = st.file_uploader("Upload Custom Wallpaper", type=["png", "jpg", "jpeg", "webp"], key="upd_wall")
        w_c1, w_c2 = st.columns(2)
        with w_c1:
            if wall_up is not None and st.button("Set Background Wallpaper 🖼"):
                st.session_state.lex_theme["custom_wall"] = encode_image_data_url(wall_up)
                save_profile_to_cloud()
                st.rerun()
        with w_c2:
            if st.session_state.lex_theme.get("custom_wall") and st.button("Clear Wallpaper"):
                st.session_state.lex_theme["custom_wall"] = ""
                save_profile_to_cloud()
                st.rerun()

        vibe_prompt = st.text_input("AI Vibe Prompt", placeholder="e.g., girl punk spray paint or goth bats")
        if st.button("Generate Custom Theme ⚡"):
            st.session_state.lex_theme = remix_theme_from_prompt(vibe_prompt)
            save_profile_to_cloud()
            st.rerun()

        c_a, c_b, c_c = st.columns(3)
        new_bg = c_a.color_picker("Background Color", th["bg"])
        new_card = c_b.color_picker("Card Surface", th["card"])
        new_acc = c_c.color_picker("Accent & Art Color", th["accent"])

        font_keys = list(FONT_MAP.keys())
        new_font = st.selectbox("Profile Font", font_keys, index=font_keys.index(th["font"]) if th.get("font") in font_keys else 0)
        new_backdrop = st.selectbox("Wall Background Art (20 Styles)", BACKDROP_OPTIONS, index=BACKDROP_OPTIONS.index(th["backdrop"]) if th.get("backdrop") in BACKDROP_OPTIONS else 0)
        new_spray = st.text_input("Custom Spray-Paint / Tag Word", value=th.get("spray_word", "LeX!"))
        borders = ["solid", "dashed", "double"]
        new_border = st.selectbox("Border Style", borders, index=borders.index(th["border_style"]) if th.get("border_style") in borders else 0)

        if st.button("Apply Custom Look ✦"):
            st.session_state.lex_theme.update({
                "bg": new_bg, "card": new_card, "accent": new_acc, "font": new_font,
                "backdrop": new_backdrop, "spray_word": new_spray, "border_style": new_border, "custom_wall": "",
            })
            save_profile_to_cloud()
            st.rerun()

        new_site = st.text_input("Profile Website / Portfolio Link", value=user.get("website", ""))
        new_mood = st.text_input("Update Mood Badge", value=user["mood"])
        new_bio = st.text_area("Update About Me", value=user["bio"])
        new_meet = st.text_input("Update Who I'd Like to Meet", value=user.get("who_to_meet", ""))
        if st.button("Save Profile Text & Link"):
            user["website"] = normalize_url(new_site)
            user["mood"] = new_mood.strip()
            user["bio"] = new_bio.strip()
            user["who_to_meet"] = new_meet.strip()
            save_profile_to_cloud()
            st.rerun()

    with t_radar:
        st.markdown("#### 📡 Inner Circle Radar")
        for friend in st.session_state.lex_top8:
            st.markdown(f"- **{friend['name']}** (`{friend['handle']}`) — {friend['mood']} | 🎵 *{friend['anthem']}*")

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only.")
