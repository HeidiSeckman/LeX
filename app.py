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

DEFAULT_THEME = {
    "name": "LexiTech Obsidian (Official)",
    "bg": "#000000", "card": "#070709", "accent": "#EC4899", "text": "#F4F4F5",
    "font": "Clean Studio Sans", "backdrop": "Architectural Grid",
    "border_style": "solid", "spray_word": "LeX!", "custom_wall": "", "website": "",
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
    safe_word = (tag_word or "LeX!")[:14].replace("<", "").replace(">", "").replace("&", "")
    if style_name == "Punk Spray-Paint Graffiti":
        raw_svg = (
            f'{SV_OPEN}xmlns="{SVG_NS}" width="420" height="260">'
            f'<text x="24" y="95" font-family="cursive" font-size="54" font-weight="900" fill="{accent}" fill-opacity="0.26" transform="rotate(-11 80 80)">{safe_word}</text>'
            f'<text x="200" y="210" font-family="cursive" font-size="40" font-weight="900" fill="#FFFFFF" fill-opacity="0.14" transform="rotate(8 240 200)">PUNK // 2026</text>'
            f'<circle cx="150" cy="55" r="3" fill="{accent}" fill-opacity="0.45"/>'
            f'<circle cx="330" cy="145" r="4" fill="#FFFFFF" fill-opacity="0.25"/>'
            f'<path d="M30 165 Q120 140 210 175 T390 155" stroke="{accent}" stroke-width="3" stroke-opacity="0.28" fill="none" stroke-dasharray="10 6"/>'
            f'{SV_CLOSE}'
        )
        return f'url("data:image/svg+xml,{urllib.parse.quote(raw_svg)}")'
    if style_name == "Y2K Stars & Sparkles":
        raw_svg = (
            f'{SV_OPEN}xmlns="{SVG_NS}" width="220" height="220">'
            f'<text x="30" y="65" font-size="34" fill="{accent}" fill-opacity="0.28">✦</text>'
            f'<text x="145" y="155" font-size="28" fill="#FFFFFF" fill-opacity="0.18">★</text>'
            f'<text x="75" y="190" font-size="20" fill="{accent}" fill-opacity="0.25">⚡</text>'
            f'{SV_CLOSE}'
        )
        return f'url("data:image/svg+xml,{urllib.parse.quote(raw_svg)}")'
    return (
        "linear-gradient(to right, rgba(255,255,255,0.035) 1px, transparent 1px), "
        "linear-gradient(to bottom, rgba(255,255,255,0.035) 1px, transparent 1px)"
    )
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
    if clean.startswith("http://") or clean.startswith("https://"):
        return clean
    return "https://" + clean

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
            "user_id": u["user_id"],
            "handle": u["handle"],
            "display_name": u["name"],
            "bio": u.get("bio", ""),
            "who_to_meet": u.get("who_to_meet", ""),
            "mood": u.get("mood", "Online Now • Vibing ⚡"),
            "anthem": u.get("anthem", "Y2K Cobalt Synth"),
            "custom_song_url": u.get("custom_song_url", ""),
            "custom_song_title": u.get("custom_song_title", ""),
            "theme_json": theme_payload,
            "top8_json": st.session_state.lex_top8,
            "wall_json": st.session_state.lex_wall,
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
            "backdrop": "Punk Spray-Paint Graffiti", "border_style": "double", "spray_word": "NOCTURNE",
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
            "backdrop": "Architectural Grid", "border_style": "solid", "spray_word": "SYS_ONLINE",
        })
    return th
def render_popular_song_embed(url: str) -> bool:
    clean = (url or "").strip()
    if not clean:
        return False
    sp_host = ".".join(["open", "spotify", "com"]) + "/track/"
    if sp_host in clean:
        track_id = clean.split(sp_host)[1].split("?")[0].strip("/")
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
bg_size = "cover" if custom_wall else ("56px 56px" if th.get("backdrop") == "Architectural Grid" else "420px 260px")
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
                        r = prof[0]
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

left_col, right_col = st.columns([1.0, 1.45], gap="large")
with left_col:
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

    st.markdown("#### 💬 Profile Wall")
    w_msg = st.text_input("Sign profile wall...", key="wall_in")
    if st.button("Post Wall Note") and w_msg.strip():
        st.session_state.lex_wall.insert(0, {"sender": user["handle"], "msg": w_msg.strip()})
        save_profile_to_cloud()
        st.rerun()
    for w in st.session_state.lex_wall[:6]:
        st.markdown(f'<div class="lex-card"><strong>{w["sender"]}:</strong> {w["msg"]}</div>', unsafe_allow_html=True)

with right_col:
    t_feed, t_friends, t_dm, t_top8, t_studio = st.tabs([
        "📰 Feed & Reactions", "👥 All Friends & Search", "✉ Messages", "✦ Top 8", "🎨 Theme Studio"
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
        new_site = st.text_input("Profile Website / Portfolio Link", value=user.get("website", ""))
        new_mood = st.text_input("Mood Badge", value=user["mood"])
        new_bio = st.text_area("About Me", value=user["bio"])
        vibe_p = st.text_input("AI Vibe Prompt", placeholder="girl punk spray paint")
        if st.button("Remix Vibe ⚡") and vibe_p.strip():
            st.session_state.lex_theme = remix_theme_from_prompt(vibe_p)
            save_profile_to_cloud()
            st.rerun()
        new_av = st.file_uploader("New Profile Photo", type=["png", "jpg", "jpeg", "webp"])
        wall_up = st.file_uploader("Custom Background Wallpaper", type=["png", "jpg", "jpeg", "webp"])
        if st.button("Save All Profile & Theme Changes ✦"):
            user["website"] = normalize_url(new_site)
            user["mood"] = new_mood.strip()
            user["bio"] = new_bio.strip()
            if new_av is not None:
                user["avatar"] = encode_image_data_url(new_av)
            if wall_up is not None:
                st.session_state.lex_theme["custom_wall"] = encode_image_data_url(wall_up)
            save_profile_to_cloud()
            st.rerun()

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only.")
