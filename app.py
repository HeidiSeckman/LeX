import os
import base64
import urllib.parse
from datetime import date
import streamlit as st
import streamlit.components.v1 as components
from audio_engine import ANTHEM_TRACKS, generate_anthem_wav

st.set_page_config(page_title="LeX // Social by LexiTech Studio", page_icon="✦", layout="wide")

ST_OPEN = "<" + "style>"
ST_CLOSE = "<" + "/style>"
LK_OPEN = "<" + "link "
SV_OPEN = "<" + "svg "
SV_CLOSE = "<" + "/svg>"

FONT_MAP = {
    "Clean Studio Sans": ("Inter", "'Inter', sans-serif"),
    "Girl Punk / Spray Marker": ("Permanent Marker", "'Permanent Marker', cursive"),
    "Cyber Glitch": ("Rubik Glitch", "'Rubik Glitch', system-ui"),
    "Y2K Arcade Pixel": ("Press Start 2P", "'Press Start 2P', monospace"),
    "Gothic Editorial": ("Cinzel", "'Cinzel', serif"),
    "Futuristic Orbitron": ("Orbitron", "'Orbitron', sans-serif"),
}


def build_backdrop_url(style_name: str, accent: str, tag_word: str = "LeX!") -> str:
    safe_word = (tag_word or "LeX!")[:14].replace("<", "").replace(">", "").replace("&", "")
    if style_name == "Punk Spray-Paint Graffiti":
        raw_svg = (
            f'{SV_OPEN}xmlns="http://w3.org" width="420" height="260">'
            f'<text x="24" y="95" font-family="cursive" font-size="54" font-weight="900" fill="{accent}" fill-opacity="0.22" transform="rotate(-11 80 80)">{safe_word}</text>'
            f'<text x="200" y="210" font-family="cursive" font-size="40" font-weight="900" fill="#FFFFFF" fill-opacity="0.12" transform="rotate(8 240 200)">PUNK // 2026</text>'
            f'<circle cx="150" cy="55" r="3" fill="{accent}" fill-opacity="0.4"/>'
            f'<circle cx="162" cy="64" r="2" fill="{accent}" fill-opacity="0.32"/>'
            f'<circle cx="330" cy="145" r="4" fill="#FFFFFF" fill-opacity="0.22"/>'
            f'<path d="M30 165 Q120 140 210 175 T390 155" stroke="{accent}" stroke-width="3" stroke-opacity="0.24" fill="none" stroke-dasharray="10 6"/>'
            f'{SV_CLOSE}'
        )
        return f'url("data:image/svg+xml,{urllib.parse.quote(raw_svg)}")'
    if style_name == "Y2K Stars & Sparkles":
        raw_svg = (
            f'{SV_OPEN}xmlns="http://w3.org" width="220" height="220">'
            f'<text x="30" y="65" font-size="34" fill="{accent}" fill-opacity="0.25">✦</text>'
            f'<text x="145" y="155" font-size="28" fill="#FFFFFF" fill-opacity="0.16">★</text>'
            f'<text x="75" y="190" font-size="20" fill="{accent}" fill-opacity="0.22">⚡</text>'
            f'{SV_CLOSE}'
        )
        return f'url("data:image/svg+xml,{urllib.parse.quote(raw_svg)}")'
    return (
        "linear-gradient(to right, rgba(255,255,255,0.035) 1px, transparent 1px), "
        "linear-gradient(to bottom, rgba(255,255,255,0.035) 1px, transparent 1px)"
    )


DEFAULT_THEME = {
    "name": "LexiTech Obsidian (Official)",
    "bg": "#000000",
    "card": "#070709",
    "accent": "#EC4899",
    "text": "#F4F4F5",
    "font": "Clean Studio Sans",
    "backdrop": "Architectural Grid",
    "border_style": "solid",
    "spray_word": "LeX!",
}

DEFAULT_TOP8 = [
    {"rank": 1, "handle": "@LeX", "name": "LeX (Studio Co-Pilot)", "mood": "Online • Remixing Vibes ⚡", "anthem": "Y2K Cobalt Synth"},
    {"rank": 2, "handle": "@Heidi", "name": "Heidi Seckman", "mood": "Founder @ LexiTech Studio ✦", "anthem": "Velvet Chrome Rhodes"},
    {"rank": 3, "handle": "@Nova", "name": "Nova Chen", "mood": "Late-night synth session 🎧", "anthem": "Midnight Tokyo Lo-Fi"},
    {"rank": 4, "handle": "@Kai", "name": "Kai Mercer", "mood": "Zero algorithms, pure vibes ✦", "anthem": "Neon Arcade Pulse"},
]
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


def remix_theme_from_prompt(prompt: str) -> dict:
    p = (prompt or "").lower()
    th = DEFAULT_THEME.copy()
    if any(k in p for k in ["punk", "spray", "graffiti", "grunge", "rock", "riot"]):
        th.update({
            "name": "Girl Punk Spray-Paint",
            "bg": "#0A040A",
            "card": "#170917",
            "accent": "#FF1E8A",
            "text": "#FFF0F7",
            "font": "Girl Punk / Spray Marker",
            "backdrop": "Punk Spray-Paint Graffiti",
            "border_style": "dashed",
            "spray_word": "RIOT // LeX",
        })
    elif any(k in p for k in ["goth", "emo", "dark", "vampire", "bat"]):
        th.update({
            "name": "2004 Mall Goth",
            "bg": "#050307",
            "card": "#110B14",
            "accent": "#C084FC",
            "text": "#F3E8FF",
            "font": "Gothic Editorial",
            "backdrop": "Punk Spray-Paint Graffiti",
            "border_style": "double",
            "spray_word": "NOCTURNE",
        })
    elif any(k in p for k in ["y2k", "star", "glitter", "sparkle", "2006", "pop"]):
        th.update({
            "name": "Y2K Starlight Chrome",
            "bg": "#050A18",
            "card": "#0D1730",
            "accent": "#38BDF8",
            "text": "#F0F9FF",
            "font": "Y2K Arcade Pixel",
            "backdrop": "Y2K Stars & Sparkles",
            "border_style": "solid",
            "spray_word": "2006 ★",
        })
    elif any(k in p for k in ["cyber", "matrix", "hacker", "glitch", "neon"]):
        th.update({
            "name": "Cyber Glitch Matrix",
            "bg": "#020A06",
            "card": "#071910",
            "accent": "#10B981",
            "text": "#ECFDF5",
            "font": "Cyber Glitch",
            "backdrop": "Architectural Grid",
            "border_style": "solid",
            "spray_word": "SYS_ONLINE",
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
if "lex_feed" not in st.session_state:
    st.session_state.lex_feed = [
        {"author": "Heidi Seckman", "handle": "@Heidi", "time": "Just now", "text": "Officially building on LeX — zero algorithms, custom spray-paint punk themes, and real music profiles! ✦", "image": "", "likes": 12},
        {"author": "Nova Chen", "handle": "@Nova", "time": "14m ago", "text": "Finally a social network where my profile looks like my actual bedroom wall in 2006 🎧", "image": "", "likes": 8},
        {"author": "LeX (Studio Co-Pilot)", "handle": "@LeX", "time": "1h ago", "text": "Tip: Open Theme Studio to spray-paint your background, upload a profile photo, or embed any Spotify/YouTube track.", "image": "", "likes": 24},
    ]
if "lex_dms" not in st.session_state:
    st.session_state.lex_dms = {
        "@LeX": [{"from": "@LeX", "text": "Hey! Welcome to LeX Social. Need help remixing your profile skin or adding friends?"}],
        "@Nova": [{"from": "@Nova", "text": "Yo! Just saw your profile theme—obsessed with the vibe 🔥"}],
        "@Kai": [{"from": "@Kai", "text": "What song are you putting on your profile today?"}],
    }
if "lex_wall" not in st.session_state:
    st.session_state.lex_wall = [
        {"sender": "@LeX", "msg": "Thanks for joining LeX! Leave a comment on the profile wall anytime ✦"},
        {"sender": "@Nova", "msg": "Love the profile anthem + custom theme!"},
    ]
th = st.session_state.lex_theme
g_font_name, css_font_family = FONT_MAP.get(th.get("font", "Clean Studio Sans"), FONT_MAP["Clean Studio Sans"])
font_query = g_font_name.replace(" ", "+")
bg_pattern = build_backdrop_url(th.get("backdrop", "Architectural Grid"), th["accent"], th.get("spray_word", "LeX!"))
bg_size = "56px 56px" if th.get("backdrop") == "Architectural Grid" else "420px 260px"

css = (
    f'{LK_OPEN}rel="stylesheet" href="https://googleapis.com{font_query}&display=swap" />'
    + ST_OPEN
    + f".stApp {{ background-color: {th['bg']}; background-image: {bg_pattern}; background-size: {bg_size}; color: {th['text']}; }}"
    + f".lex-banner {{ background: radial-gradient(circle at 15% 50%, rgba(236,72,153,0.18), {th['card']} 65%); border: 2px {th['border_style']} {th['accent']}; border-radius: 14px; padding: 20px 26px; margin-bottom: 18px; }}"
    + f".lex-wordmark {{ font-family: {css_font_family}; font-size: 40px; font-weight: 800; letter-spacing: 0.06em; color: #FFFFFF; text-shadow: 0 0 22px {th['accent']}; }}"
    + f".lex-card {{ background: {th['card']}; border: 1.5px {th['border_style']} {th['accent']}; border-radius: 12px; padding: 18px 20px; margin-bottom: 14px; }}"
    + f".lex-title {{ font-family: {css_font_family}; color: {th['text']}; }}"
    + f".lex-avatar {{ width: 84px; height: 84px; border-radius: 50%; object-fit: cover; border: 2.5px solid {th['accent']}; box-shadow: 0 0 18px {th['accent']}; }}"
    + f".lex-avatar-fallback {{ width: 84px; height: 84px; border-radius: 50%; background: {th['accent']}; color: #000000; font-weight: 900; font-size: 32px; display: flex; align-items: center; justify-content: center; }}"
    + f".lex-post-img {{ width: 100%; max-height: 360px; object-fit: cover; border-radius: 10px; margin-top: 12px; border: 1px solid rgba(255,255,255,0.14); }}"
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

if st.session_state.lex_user is None:
    st.subheader("Create Your LeX Profile (13+ Required)")
    with st.form("lex_signup_form"):
        c1, c2 = st.columns(2)
        with c1:
            display_name = st.text_input("Display Name", placeholder="Heidi Seckman")
            raw_handle = st.text_input("Create Profile Name (@handle)", placeholder="Heidi")
            avatar_up = st.file_uploader("Upload Profile Picture (Optional)", type=["png", "jpg", "jpeg", "webp"])
        with c2:
            dob = st.date_input("Date of Birth (13+ Only)", value=date(2000, 1, 1), min_value=date(1920, 1, 1), max_value=date.today())
            starting_anthem = st.selectbox("Starting Synth Vibe", list(ANTHEM_TRACKS.keys()))
        bio_text = st.text_area("About Me", value="Zero algorithms. Custom spray-paint vibes. Building on LeX.")
        if st.form_submit_button("Launch My LeX Profile ✦", use_container_width=True):
            age = calc_age(dob)
            clean_handle = raw_handle.strip().lstrip("@").replace(" ", "")
            if age < 13:
                st.error("Access Denied: You must be at least 13 years old to create a LeX profile.")
            elif not display_name.strip() or not clean_handle:
                st.warning("Please enter both a Display Name and a Profile Name (@handle).")
            else:
                st.session_state.lex_user = {
                    "name": display_name.strip(), "handle": f"@{clean_handle}", "age": age,
                    "avatar": encode_image_data_url(avatar_up),
                    "mood": "Online Now • Vibing ⚡", "bio": bio_text.strip(),
                    "who_to_meet": "Creators, builders, music lovers, and night owls.",
                    "anthem": starting_anthem, "custom_song_url": "", "custom_song_title": "",
                }
                st.rerun()
    st.stop()

user = st.session_state.lex_user
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
            st.rerun()
        if user.get("custom_song_url") and not render_popular_song_embed(user["custom_song_url"]):
            st.warning("Paste a valid Spotify track, Apple Music song, or YouTube link.")
    else:
        idx = list(ANTHEM_TRACKS.keys()).index(user["anthem"]) if user["anthem"] in ANTHEM_TRACKS else 0
        sel = st.selectbox("Studio Synth Track", list(ANTHEM_TRACKS.keys()), index=idx)
        if sel != user["anthem"]:
            user["anthem"] = sel
            st.rerun()
        st.audio(generate_anthem_wav(user["anthem"]), format="audio/wav")

    st.caption(f"🔴 LIVE VIBE-SYNC ACTIVE — Playing: {user['anthem']}")

    with st.expander("🧱 Profile Wall / Guestbook", expanded=True):
        for w in st.session_state.lex_wall[-5:]:
            st.markdown(f"**{w['sender']}:** {w['msg']}")
        wall_note = st.text_input("Sign the profile wall...", key="wall_in")
        if st.button("Post on Wall") and wall_note.strip():
            st.session_state.lex_wall.append({"sender": user["handle"], "msg": wall_note.strip()})
            st.rerun()
with right_col:
    tab_feed, tab_dm, tab_top8, tab_studio, tab_radar = st.tabs([
        "📰 Friends Feed", "✉️ Messages", "✦ Top 8", "🎨 Theme Studio", "📡 Radar"
    ])

    with tab_feed:
        st.markdown("#### Chronological Friends Feed (Zero Algorithms)")
        with st.form("feed_post_form", clear_on_submit=True):
            new_post = st.text_area("Share a status update, lyric, or mood...", height=70)
            post_photo = st.file_uploader("Attach a Photo (Optional)", type=["png", "jpg", "jpeg", "webp"], key="feed_img")
            if st.form_submit_button("Publish to Feed ✦") and (new_post.strip() or post_photo is not None):
                st.session_state.lex_feed.insert(0, {
                    "author": user["name"], "handle": user["handle"], "time": "Just now",
                    "text": new_post.strip(), "image": encode_image_data_url(post_photo), "likes": 1,
                })
                st.rerun()
        for p_idx, post in enumerate(st.session_state.lex_feed):
            img_tag = f'<img src="{post["image"]}" class="lex-post-img" alt="Post photo" />' if post.get("image") else ""
            st.markdown(
                f'<div class="lex-card"><strong>{post["author"]}</strong> '
                f'<span style="color:{th["accent"]};">{post["handle"]}</span> '
                f'<span style="color:#71717A;font-size:12px;">• {post["time"]}</span>'
                f'<p style="margin-top:8px;">{post["text"]}</p>{img_tag}</div>',
                unsafe_allow_html=True,
            )
            if st.button(f"⚡ Vibe ({post['likes']})", key=f"like_{p_idx}"):
                post["likes"] += 1
                st.rerun()

    with tab_dm:
        st.markdown("#### ✉️ Direct Messages")
        dm_targets = [f["handle"] for f in st.session_state.lex_top8 if f["handle"] != user["handle"]]
        active_chat = st.selectbox("Select Friend", dm_targets or ["@LeX"])
        thread = st.session_state.lex_dms.setdefault(active_chat, [])
        for m in thread:
            st.markdown(f"**{m['from']}:** {m['text']}")
        dm_text = st.text_input(f"Message {active_chat}...", key="dm_box")
        if st.button("Send DM") and dm_text.strip():
            thread.append({"from": user["handle"], "text": dm_text.strip()})
            if active_chat == "@LeX":
                thread.append({"from": "@LeX", "text": "Got it! Let me know if you want to remix your profile skin or pin new Top 8 friends."})
            st.rerun()

    with tab_top8:
        st.markdown("#### Ranked Top 8 Friends")
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
                if idx > 0 and st.button(f"Move {friend['handle']} Up ↑", key=f"up_{idx}"):
                    lst = st.session_state.lex_top8
                    lst[idx], lst[idx - 1] = lst[idx - 1], lst[idx]
                    for r_i, item in enumerate(lst):
                        item["rank"] = r_i + 1
                    st.rerun()

    with tab_studio:
        st.markdown("#### 🎨 Profile Photo, Bio & Full Theme Customizer")
        new_av = st.file_uploader("Update Profile Picture", type=["png", "jpg", "jpeg", "webp"], key="upd_av")
        if new_av is not None and st.button("Save New Profile Picture"):
            user["avatar"] = encode_image_data_url(new_av)
            st.rerun()

        vibe_prompt = st.text_input("AI Vibe Prompt", placeholder="e.g., girl punk theme with spray paint writing in the back")
        if st.button("Generate Custom Theme ⚡"):
            st.session_state.lex_theme = remix_theme_from_prompt(vibe_prompt)
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
            })
            st.rerun()

        new_mood = st.text_input("Update Mood Badge", value=user["mood"])
        new_bio = st.text_area("Update About Me", value=user["bio"])
        new_meet = st.text_input("Update Who I'd Like to Meet", value=user["who_to_meet"])
        if st.button("Save Profile Text"):
            user["mood"] = new_mood.strip()
            user["bio"] = new_bio.strip()
            user["who_to_meet"] = new_meet.strip()
            st.rerun()

    with tab_radar:
        st.markdown("#### 📡 Inner Circle Radar")
        for friend in st.session_state.lex_top8:
            st.markdown(f"- **{friend['name']}** (`{friend['handle']}`) — {friend['mood']} | 🎵 *{friend['anthem']}*")

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only.")
