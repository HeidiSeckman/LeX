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
    "border_style": "solid", "spray_word": "LeX!", "custom_wall": "",
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
            f'{SV_OPEN}xmlns="http://w3.org" width="420" height="260">'
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
            f'{SV_OPEN}xmlns="http://w3.org" width="220" height="220">'
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


def save_profile_to_cloud():
    sb = get_sb()
    u = st.session_state.get("lex_user")
    if not sb or not u or not u.get("user_id"):
        return
    try:
        theme_payload = st.session_state.lex_theme.copy()
        theme_payload["avatar"] = u.get("avatar", "")
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
    th = DEFAULT_THEME.copy()
    if any(k in p for k in ["punk", "spray", "graffiti", "grunge", "rock", "riot"]):
        th.update({
            "name": "Girl Punk Spray-Paint",
            "bg": "#0A040A", "card": "#170917", "accent": "#FF1E8A", "text": "#FFF0F7",
            "font": "Girl Punk / Spray Marker", "backdrop": "Punk Spray-Paint Graffiti",
            "border_style": "dashed", "spray_word": "RIOT // LeX",
        })
    elif any(k in p for k in ["goth", "emo", "dark", "vampire", "bat"]):
        th.update({
            "name": "2004 Mall Goth",
            "bg": "#050307", "card": "#110B14", "accent": "#C084FC", "text": "#F3E8FF",
            "font": "Gothic Editorial", "backdrop": "Punk Spray-Paint Graffiti",
            "border_style": "double", "spray_word": "NOCTURNE",
        })
    elif any(k in p for k in ["y2k", "star", "glitter", "sparkle", "2006", "pop"]):
        th.update({
            "name": "Y2K Starlight Chrome",
            "bg": "#050A18", "card": "#0D1730", "accent": "#38BDF8", "text": "#F0F9FF",
            "font": "Y2K Arcade Pixel", "backdrop": "Y2K Stars & Sparkles",
            "border_style": "solid", "spray_word": "2006 ★",
        })
    elif any(k in p for k in ["cyber", "matrix", "hacker", "glitch", "neon"]):
        th.update({
            "name": "Cyber Glitch Matrix",
            "bg": "#020A06", "card": "#071910", "accent": "#10B981", "text": "#ECFDF5",
            "font": "Cyber Glitch", "backdrop": "Architectural Grid",
            "border_style": "solid", "spray_word": "SYS_ONLINE",
        })
    if "pink" in p or "magenta" in p or "rose" in p:
        th["accent"] = "#FF1E8A"
    elif "purple" in p or "violet" in p:
        th["accent"] = "#A855F7"
    elif "blue" in p or "cobalt" in p:
        th["accent"] = "#3B82F6"
    elif "red" in p or "crimson" in p:
        th["accent"] = "#EF4444"
    elif "green" in p or "lime" in p:
        th["accent"] = "#22C55E"
    return th


def render_popular_song_embed(url: str) -> bool:
    clean = (url or "").strip()
    if not clean:
        return False
    if "://spotify.com" in clean:
        after_track = clean.split("://spotify.com").__getitem__(1)
        track_id = after_track.split("?").__getitem__(0).strip("/")
        embed_src = f"https://spotify.com{track_id}?utm_source=generator&theme=0"
        components.iframe(embed_src, height=152)
        return True
    if "://youtube.com" in clean or "youtu.be/" in clean:
        st.video(clean)
        return True
    if "://apple.com" in clean and "://apple.com" not in clean:
        embed_src = clean.replace("https://://apple.com", "https://embed.://apple.com")
        components.iframe(embed_src, height=175)
        return True
    return False


if "lex_user" not in st.session_state:
    st.session_state.lex_user = None
if "lex_theme" not in st.session_state:
    st.session_state.lex_theme = DEFAULT_THEME.copy()
if "lex_top8" not in st.session_state:
    st.session_state.lex_top8 = [item.copy() for item in DEFAULT_TOP8]
if "lex_wall" not in st.session_state:
    st.session_state.lex_wall = [
        {"sender": "@LeX", "msg": "Thanks for joining LeX! Leave a comment on the profile wall anytime ✦"},
        {"sender": "@Nova", "msg": "Love the profile anthem + custom theme!"},
    ]
th = st.session_state.lex_theme
g_font_name, css_font_family = FONT_MAP.get(th.get("font", "Clean Studio Sans"), FONT_MAP["Clean Studio Sans"])
font_query = g_font_name.replace(" ", "+")
bg_pattern = build_backdrop_url(th.get("backdrop", "Architectural Grid"), th["accent"], th.get("spray_word", "LeX!"))

custom_wall = th.get("custom_wall", "")
if custom_wall:
    bg_css_img = f'url("{custom_wall}")'
    bg_size = "cover"
    bg_repeat = "no-repeat"
else:
    bg_css_img = bg_pattern
    bg_size = "56px 56px" if th.get("backdrop") == "Architectural Grid" else "420px 260px"
    bg_repeat = "repeat"

css = (
    f'{LK_OPEN}rel="stylesheet" href="https://googleapis.com{font_query}&display=swap" />'
    + ST_OPEN
    + f'[data-testid="stAppViewContainer"], .stApp {{ background-color: {th["bg"]} !important; background-image: {bg_css_img} !important; background-size: {bg_size} !important; background-repeat: {bg_repeat} !important; background-attachment: fixed !important; color: {th["text"]} !important; }}'
    + '[data-testid="stHeader"], [data-testid="stMain"] { background: transparent !important; }'
    + f".lex-banner {{ background: radial-gradient(circle at 15% 50%, rgba(236,72,153,0.18), {th['card']} 65%); border: 2px {th['border_style']} {th['accent']}; border-radius: 14px; padding: 20px 26px; margin-bottom: 18px; }}"
    + f".lex-wordmark {{ font-family: {css_font_family}; font-size: 40px; font-weight: 800; letter-spacing: 0.06em; color: #FFFFFF; text-shadow: 0 0 22px {th['accent']}; }}"
    + f".lex-card {{ background: {th['card']}; border: 1.5px {th['border_style']} {th['accent']}; border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; }}"
    + f".lex-title {{ font-family: {css_font_family}; color: {th['text']}; }}"
    + f".lex-avatar {{ width: 84px; height: 84px; border-radius: 50%; object-fit: cover; border: 2.5px solid {th['accent']}; box-shadow: 0 0 18px {th['accent']}; }}"
    + f".lex-avatar-fallback {{ width: 84px; height: 84px; border-radius: 50%; background: {th['accent']}; color: #000000; font-weight: 900; font-size: 32px; display: flex; align-items: center; justify-content: center; }}"
    + ST_CLOSE
)
st.markdown(css, unsafe_allow_html=True)

head_c1, head_c2 = st.columns([0.18, 0.82])
with head_c1:
    if os.path.exists("lex-logo.png"):
        st.image("lex-logo.png", width=155)
    elif os.path.exists("LEXItech.PNG"):
        st.image("LEXItech.PNG", width=155)
with head_c2:
    st.markdown(
        '<div class="lex-banner"><div class="lex-wordmark">LeX</div>'
        '<div style="color:#A1A1AA;font-family:monospace;font-size:12px;letter-spacing:0.14em;">'
        'NEXT-GEN SOCIAL ARCHITECTURE // POWERED BY LEXITECH STUDIO // AGES 13+ ONLY</div></div>',
        unsafe_allow_html=True,
    )

sb = get_sb()

if st.session_state.lex_user is None:
    tab_login, tab_join = st.tabs(["🔐 Member Sign In", "✦ Create Account (13+ Required)"])

    with tab_login:
        with st.form("lex_login_form"):
            l_email = st.text_input("Email")
            l_pass = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In to My LeX Profile ✦", use_container_width=True):
                if not sb:
                    st.error("Supabase Secrets missing. Add SUPABASE_URL and SUPABASE_KEY in App Settings.")
                else:
                    try:
                        res = sb.auth.sign_in_with_password({"email": l_email.strip(), "password": l_pass})
                        uid = res.user.id
                        prof = sb.table("lex_profiles").select("*").eq("user_id", uid).execute().data
                        if prof:
                            row = prof[0]
                            st.session_state.lex_user = {
                                "user_id": uid, "name": row["display_name"], "handle": row["handle"],
                                "bio": row.get("bio", ""), "who_to_meet": row.get("who_to_meet", ""),
                                "mood": row.get("mood", "Online Now • Vibing ⚡"),
                                "anthem": row.get("anthem", "Y2K Cobalt Synth"),
                                "custom_song_url": row.get("custom_song_url", ""),
                                "custom_song_title": row.get("custom_song_title", ""),
                                "avatar": row.get("theme_json", {}).get("avatar", ""),
                            }
                            if row.get("theme_json"):
                                st.session_state.lex_theme.update(row["theme_json"])
                            if row.get("top8_json"):
                                st.session_state.lex_top8 = row["top8_json"]
                            if row.get("wall_json"):
                                st.session_state.lex_wall = row["wall_json"]
                            st.rerun()
                        else:
                            st.error("Profile record not found for this login.")
                    except Exception as e:
                        st.error(f"Sign in failed: {e}")

    with tab_join:
        with st.form("lex_signup_form"):
            c1, c2 = st.columns(2)
            with c1:
                s_email = st.text_input("Email Address")
                s_pass = st.text_input("Create Password (6+ characters)", type="password")
                display_name = st.text_input("Display Name", placeholder="Heidi Seckman")
                raw_handle = st.text_input("Create Profile Name (@handle)", placeholder="Heidi")
            with c2:
                dob = st.date_input("Date of Birth (13+ Only)", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today())
                starting_anthem = st.selectbox("Starting Synth Vibe", list(ANTHEM_TRACKS.keys()))
                avatar_up = st.file_uploader("Upload Profile Picture (Optional)", type=["png", "jpg", "jpeg", "webp"])
            bio_text = st.text_area("About Me", value="Zero algorithms. Custom spray-paint vibes. Building on LeX.")
            if st.form_submit_button("Create Permanent LeX Account ✦", use_container_width=True):
                age = calc_age(dob)
                clean_handle = raw_handle.strip().lstrip("@").replace(" ", "")
                if age < 13:
                    st.error("Access Denied: You must be at least 13 years old to create a LeX profile.")
                elif not s_email.strip() or len(s_pass) < 6 or not display_name.strip() or not clean_handle:
                    st.warning("Fill in Email, 6+ char Password, Display Name, and @handle.")
                elif not sb:
                    st.error("Supabase Secrets missing.")
                else:
                    try:
                        auth_res = sb.auth.sign_up({"email": s_email.strip(), "password": s_pass})
                        uid = auth_res.user.id
                        av_data = encode_image_data_url(avatar_up)
                        st.session_state.lex_theme["avatar"] = av_data
                        st.session_state.lex_user = {
                            "user_id": uid, "name": display_name.strip(), "handle": f"@{clean_handle}",
                            "avatar": av_data, "mood": "Online Now • Vibing ⚡", "bio": bio_text.strip(),
                            "who_to_meet": "Creators, builders, music lovers, and night owls.",
                            "anthem": starting_anthem, "custom_song_url": "", "custom_song_title": "",
                        }
                        save_profile_to_cloud()
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not create account: {e}")
    st.stop()

user = st.session_state.lex_user
top_bar1, top_bar2 = st.columns([0.85, 0.15])
with top_bar2:
    if st.button("Sign Out"):
        st.session_state.lex_user = None
        st.rerun()

left_col, right_col = st.columns([1.05, 1.4], gap="large")

with left_col:
    if user.get("avatar"):
        av_html = f'<img src="{user["avatar"]}" class="lex-avatar" alt="Avatar" />'
    else:
        initial = (user["name"][:1] or "L").upper()
        av_html = f'<div class="lex-avatar-fallback">{initial}</div>'

    st.markdown(
        f'<div class="lex-card"><div style="display:flex;align-items:center;gap:16px;">{av_html}'
        f'<div><h2 class="lex-title" style="margin:0;">{user["name"]}</h2>'
        f'<div style="color:{th["accent"]};font-size:17px;font-weight:700;">{user["handle"]}</div>'
        f'<div style="color:#34D399;font-size:13px;margin-top:4px;">● {user["mood"]}</div></div></div>'
        f'<p style="margin-top:14px;"><strong>About Me:</strong> {user["bio"]}</p>'
        f'<p style="margin-top:8px;"><strong>Who I\'d Like to Meet:</strong> {user["who_to_meet"]}</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### 🎵 Profile Anthem & Live Vibe-Sync")
    anthem_mode = st.radio("Source", ["Popular Song Link (Spotify / YouTube / Apple)", "Built-In LeX Synth"], horizontal=True)
    if anthem_mode.startswith("Popular"):
        song_url = st.text_input("Paste Spotify, Apple Music, or YouTube link", value=user.get("custom_song_url", ""))
        song_title = st.text_input("Now Playing Label", value=user.get("custom_song_title", "Hot New Track 🔥"))
        if st.button("Set Profile Song 🎵"):
            user["custom_song_url"] = song_url.strip()
            user["custom_song_title"] = song_title.strip() or "Hot New Track 🔥"
            user["anthem"] = user["custom_song_title"]
            save_profile_to_cloud()
            st.rerun()
        if user.get("custom_song_url") and not render_popular_song_embed(user["custom_song_url"]):
            st.warning("Paste a valid Spotify track, Apple Music song, or YouTube link.")
    else:
        idx = list(ANTHEM_TRACKS.keys()).index(user["anthem"]) if user["anthem"] in ANTHEM_TRACKS else 0
with right_col:
    tab_feed, tab_dm, tab_top8, tab_studio, tab_radar = st.tabs([
        "📰 Friends Feed", "✉️ Messages", "✦ Top 8", "🎨 Theme Studio", "📡 Radar"
    ])

    with tab_feed:
        st.markdown("#### Chronological Friends Feed (Zero Algorithms)")
        with st.form("feed_post_form", clear_on_submit=True):
            new_post = st.text_area("Share a status update, lyric, or mood...", height=70)
            if st.form_submit_button("Publish to Feed ✦") and new_post.strip():
                if sb:
                    try:
                        sb.table("lex_posts").insert({
                            "handle": user["handle"], "author": user["name"], "body": new_post.strip(), "likes": 1
                        }).execute()
                    except Exception as e:
                        st.warning(f"Post error: {e}")
                st.rerun()

        posts_list = []
        if sb:
            try:
                posts_list = sb.table("lex_posts").select("*").order("id", desc=True).limit(30).execute().data or []
            except Exception:
                posts_list = []

        if not posts_list:
            st.info("No posts yet—be the first to publish on the LeX feed!")
        for post in posts_list:
            st.markdown(
                f'<div class="lex-card"><strong>{post["author"]}</strong> '
                f'<span style="color:{th["accent"]};">{post["handle"]}</span>'
                f'<p style="margin-top:8px;">{post["body"]}</p></div>',
                unsafe_allow_html=True,
            )
            if st.button(f"⚡ Vibe ({post.get('likes', 1)})", key=f"like_{post['id']}"):
                if sb:
                    sb.table("lex_posts").update({"likes": (post.get("likes", 1) + 1)}).eq("id", post["id"]).execute()
                st.rerun()

    with tab_dm:
        st.markdown("#### ✉️ Direct Messages")
        dm_targets = [f["handle"] for f in st.session_state.lex_top8 if f["handle"] != user["handle"]]
        active_chat = st.selectbox("Select Friend", dm_targets or ["@LeX"])
        msgs = []
        if sb:
            try:
                all_m = sb.table("lex_messages").select("*").order("id", desc=False).limit(100).execute().data or []
                msgs = [
                    m for m in all_m
                    if (m["sender_handle"] == user["handle"] and m["recipient_handle"] == active_chat)
                    or (m["sender_handle"] == active_chat and m["recipient_handle"] == user["handle"])
                ]
            except Exception:
                msgs = []
        for m in msgs:
            st.markdown(f"**{m['sender_handle']}:** {m['body']}")
        dm_text = st.text_input(f"Message {active_chat}...", key="dm_box")
        if st.button("Send DM") and dm_text.strip():
            if sb:
                sb.table("lex_messages").insert({
                    "sender_handle": user["handle"], "recipient_handle": active_chat, "body": dm_text.strip()
                }).execute()
                if active_chat == "@LeX":
                    sb.table("lex_messages").insert({
                        "sender_handle": "@LeX", "recipient_handle": user["handle"],
                        "body": "Got it! Your profile and Top 8 are synced live to the cloud ✦"
                    }).execute()
            st.rerun()
    with tab_top8:
        st.markdown("#### Ranked Top 8 Friends (Full 8-Slot Editor)")
        t_cols = st.columns(2)
        for idx, friend in enumerate(st.session_state.lex_top8):
            with t_cols[idx % 2]:
                st.markdown(
                    f'<div class="lex-card"><strong>#{friend["rank"]} {friend["name"]}</strong> '
                    f'<span style="color:{th["accent"]};">{friend["handle"]}</span>'
                    f'<div style="font-size:12px;color:#A1A1AA;margin-top:4px;">{friend["mood"]}</div>'
                    f'<div style="font-size:11px;margin-top:4px;">🎵 {friend["anthem"]}</div></div>',
                    unsafe_allow_html=True,
                )
                b1, b2 = st.columns(2)
                with b1:
                    if idx > 0 and st.button("Move Up ↑", key=f"up_{idx}"):
                        lst = st.session_state.lex_top8
                        lst[idx], lst[idx - 1] = lst[idx - 1], lst[idx]
                        for r_i, item in enumerate(lst):
                            item["rank"] = r_i + 1
                        save_profile_to_cloud()
                        st.rerun()
                with b2:
                    if st.button("Remove ✕", key=f"rm_{idx}"):
                        st.session_state.lex_top8.pop(idx)
                        for r_i, item in enumerate(st.session_state.lex_top8):
                            item["rank"] = r_i + 1
                        save_profile_to_cloud()
                        st.rerun()

        st.markdown("---")
        if len(st.session_state.lex_top8) < 8:
            with st.form("add_top_friend_form", clear_on_submit=True):
                st.markdown(f"**Add New Friend ({8 - len(st.session_state.lex_top8)} slots open)**")
                fc1, fc2 = st.columns(2)
                with fc1:
                    f_name = st.text_input("Friend Name", placeholder="Taylor")
                    f_handle = st.text_input("Friend @handle", placeholder="Taylor")
                with fc2:
                    f_mood = st.text_input("Status / Mood", value="Online • Listening 🎧")
                    f_anthem = st.text_input("Their Current Song", value="Hot New Track 🔥")
                if st.form_submit_button("Add to Top 8 ✦"):
                    clean_fh = f_handle.strip().lstrip("@").replace(" ", "")
                    if f_name.strip() and clean_fh:
                        st.session_state.lex_top8.append({
                            "rank": len(st.session_state.lex_top8) + 1,
                            "handle": f"@{clean_fh}", "name": f_name.strip(),
                            "mood": f_mood.strip(), "anthem": f_anthem.strip() or "Y2K Cobalt Synth",
                        })
                        save_profile_to_cloud()
                        st.rerun()
        else:
            st.caption("All 8 slots are full! Click **Remove ✕** on any friend above to swap in someone new.")

        if st.session_state.lex_top8:
            with st.expander("✏️ Edit an Existing Top 8 Friend"):
                slot_labels = [f"#{f['rank']} {f['name']} ({f['handle']})" for f in st.session_state.lex_top8]
                pick_idx = st.selectbox("Choose Slot to Edit", range(len(slot_labels)), format_func=lambda i: slot_labels[i])
                target_f = st.session_state.lex_top8[pick_idx]
                ed_name = st.text_input("Edit Name", value=target_f["name"], key="ed_fn")
                ed_handle = st.text_input("Edit @handle", value=target_f["handle"], key="ed_fh")
                ed_mood = st.text_input("Edit Mood", value=target_f["mood"], key="ed_fm")
                ed_anthem = st.text_input("Edit Song", value=target_f["anthem"], key="ed_fa")
                if st.button("Save Friend Changes"):
                    clean_eh = ed_handle.strip().lstrip("@").replace(" ", "")
                    if ed_name.strip() and clean_eh:
                        target_f["name"] = ed_name.strip()
                        target_f["handle"] = f"@{clean_eh}"
                        target_f["mood"] = ed_mood.strip()
                        target_f["anthem"] = ed_anthem.strip()
                        save_profile_to_cloud()
                        st.rerun()

    with tab_studio:
        st.markdown("#### 🎨 Profile Photo, Wallpaper & Full Theme Customizer")
        new_av = st.file_uploader("Update Profile Picture", type=["png", "jpg", "jpeg", "webp"], key="upd_av")
        if new_av is not None and st.button("Save New Profile Picture"):
            user["avatar"] = encode_image_data_url(new_av)
            save_profile_to_cloud()
            st.rerun()

        wall_up = st.file_uploader("Upload Custom Profile Background Wallpaper", type=["png", "jpg", "jpeg", "webp"], key="upd_wall")
        w_c1, w_c2 = st.columns(2)
        with w_c1:
            if wall_up is not None and st.button("Set Background Wallpaper 🖼️"):
                st.session_state.lex_theme["custom_wall"] = encode_image_data_url(wall_up)
                save_profile_to_cloud()
                st.rerun()
        with w_c2:
            if st.session_state.lex_theme.get("custom_wall") and st.button("Clear Wallpaper"):
                st.session_state.lex_theme["custom_wall"] = ""
                save_profile_to_cloud()
                st.rerun()

        vibe_prompt = st.text_input("AI Vibe Prompt", placeholder="e.g., girl punk theme with spray paint writing in the back")
        if st.button("Generate Custom Theme ⚡"):
            st.session_state.lex_theme = remix_theme_from_prompt(vibe_prompt)
            save_profile_to_cloud()
            st.rerun()

        c_a, c_b, c_c = st.columns(3)
        with c_a:
            new_bg = st.color_picker("Background Color", th["bg"])
        with c_b:
            new_card = st.color_picker("Card Surface", th["card"])
        with c_c:
            new_acc = st.color_picker("Accent & Spray Color", th["accent"])
        new_font = st.selectbox("Profile Font", list(FONT_MAP.keys()), index=list(FONT_MAP.keys()).index(th["font"]))
        new_backdrop = st.selectbox("Wall Background Art", ["Architectural Grid", "Punk Spray-Paint Graffiti", "Y2K Stars & Sparkles"])
        new_spray = st.text_input("Custom Spray-Paint / Wall Tag Text", value=th.get("spray_word", "LeX!"))
        new_border = st.selectbox("Border Style", ["solid", "dashed", "double"], index=["solid", "dashed", "double"].index(th["border_style"]))
        if st.button("Apply Custom Look ✦"):
            st.session_state.lex_theme.update({
                "bg": new_bg, "card": new_card, "accent": new_acc,
                "font": new_font, "backdrop": new_backdrop,
                "spray_word": new_spray, "border_style": new_border,
                "custom_wall": "",
            })
            save_profile_to_cloud()
            st.rerun()

        new_mood = st.text_input("Update Mood Badge", value=user["mood"])
        new_bio = st.text_area("Update About Me", value=user["bio"])
        new_meet = st.text_input("Update Who I'd Like to Meet", value=user["who_to_meet"])
        if st.button("Save Profile Text"):
            user["mood"] = new_mood.strip()
            user["bio"] = new_bio.strip()
            user["who_to_meet"] = new_meet.strip()
            save_profile_to_cloud()
            st.rerun()

    with tab_radar:
        st.markdown("#### 📡 Inner Circle Radar")
        for friend in st.session_state.lex_top8:
            st.markdown(f"- **{friend['name']}** (`{friend['handle']}`) — {friend['mood']} | 🎵 *{friend['anthem']}*")

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only.")
