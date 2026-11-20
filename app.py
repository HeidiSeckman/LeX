import os
from datetime import date
import streamlit as st
from audio_engine import ANTHEM_TRACKS, generate_anthem_wav

st.set_page_config(page_title="LeX // Social by LexiTech Studio", page_icon="✦", layout="wide")

ST_OPEN = "<" + "style>"
ST_CLOSE = "<" + "/style>"

PRESET_THEMES = {
    "LexiTech Obsidian (Official)": {"bg": "#000000", "card": "#070709", "accent": "#EC4899", "text": "#F4F4F5"},
    "Y2K Cyber Chrome": {"bg": "#06080D", "card": "#0F131E", "accent": "#E2E8F0", "text": "#F8FAFC"},
    "Velvet Rose Neon": {"bg": "#11050F", "card": "#1C0919", "accent": "#F472B6", "text": "#FDF2F8"},
    "Midnight Cobalt": {"bg": "#040914", "card": "#0A1429", "accent": "#3B82F6", "text": "#F1F5F9"},
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


if "lex_user" not in st.session_state:
    st.session_state.lex_user = None
if "lex_theme" not in st.session_state:
    st.session_state.lex_theme = PRESET_THEMES["LexiTech Obsidian (Official)"].copy()
if "lex_top8" not in st.session_state:
    st.session_state.lex_top8 = [item.copy() for item in DEFAULT_TOP8]
if "lex_room_chat" not in st.session_state:
    st.session_state.lex_room_chat = [
        {"sender": "@LeX", "msg": "Welcome to your live Vibe-Sync Room! Friends dropping in hear your anthem in real time."}
    ]

th = st.session_state.lex_theme
css = f"""
{ST_OPEN}
.stApp {{
  background-color: {th['bg']};
  background-image:
    linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px);
  background-size: 56px 56px;
  color: {th['text']};
}}
.lex-banner {{
  background: radial-gradient(circle at 15% 50%, rgba(236, 72, 153, 0.16), {th['card']} 62%);
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: 14px;
  padding: 22px 28px;
  margin-bottom: 20px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.85), inset 0 1px 0 rgba(255, 255, 255, 0.1);
}}
.lex-wordmark {{
  font-size: 40px; font-weight: 800; letter-spacing: 0.08em;
  color: #FFFFFF;
  text-shadow: 0 0 22px rgba(255, 255, 255, 0.45), 0 0 36px {th['accent']};
}}
.lex-card {{
  background: {th['card']};
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 12px;
  padding: 18px 20px;
  margin-bottom: 14px;
}}
{ST_CLOSE}
"""
st.markdown(css, unsafe_allow_html=True)

head_c1, head_c2 = st.columns([1, 5])
with head_c1:
    if os.path.exists("lex-logo.png"):
        st.image("lex-logo.png", width=115)
    elif os.path.exists("LEXItech.PNG"):
        st.image("LEXItech.PNG", width=115)
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
        with c2:
            dob = st.date_input(
                "Date of Birth (Must be 13 or older)",
                value=date(2000, 1, 1),
                min_value=date(1920, 1, 1),
                max_value=date.today(),
            )
            starting_anthem = st.selectbox("Choose Your Profile Anthem", list(ANTHEM_TRACKS.keys()))
        bio_text = st.text_area("About Me", value="Zero algorithms. Custom vibes. Building on LeX.")
        submitted = st.form_submit_button("Launch My LeX Profile ✦", use_container_width=True)

        if submitted:
            age = calc_age(dob)
            clean_handle = raw_handle.strip().lstrip("@").replace(" ", "")
            if age < 13:
                st.error("Access Denied: You must be at least 13 years old to create a LeX profile.")
            elif not display_name.strip() or not clean_handle:
                st.warning("Please enter both a Display Name and a Profile Name (@handle).")
            else:
                st.session_state.lex_user = {
                    "name": display_name.strip(),
                    "handle": f"@{clean_handle}",
                    "age": age,
                    "mood": "Online Now • Vibing ⚡",
                    "bio": bio_text.strip(),
                    "who_to_meet": "Creators, builders, music lovers, and night owls.",
                    "anthem": starting_anthem,
                }
                st.rerun()
    st.stop()

user = st.session_state.lex_user

left_col, right_col = st.columns([1.05, 1.35], gap="large")

with left_col:
    st.markdown(
        f'<div class="lex-card"><h2 style="margin:0;">{user["name"]} '
        f'<span style="color:#F472B6;font-size:18px;">{user["handle"]}</span></h2>'
        f'<p style="color:#34D399;font-size:13px;margin:6px 0;">● {user["mood"]}</p>'
        f'<p style="margin-top:10px;"><strong>About Me:</strong> {user["bio"]}</p>'
        f'<p style="margin-top:8px;"><strong>Who I\'d Like to Meet:</strong> {user["who_to_meet"]}</p></div>',
        unsafe_allow_html=True,
    )

    st.markdown("#### 🎵 Profile Anthem & Live Vibe-Sync")
    selected_track = st.selectbox(
        "Active Profile Track",
        list(ANTHEM_TRACKS.keys()),
        index=list(ANTHEM_TRACKS.keys()).index(user["anthem"]),
    )
    if selected_track != user["anthem"]:
        user["anthem"] = selected_track
        st.rerun()

    wav_bytes = generate_anthem_wav(user["anthem"])
    st.audio(wav_bytes, format="audio/wav")
    st.caption("🔴 LIVE VIBE-SYNC ACTIVE — Visitors on your page hear this track in real time.")

    with st.expander("💬 Ephemeral Vibe-Sync Room Chat", expanded=True):
        for entry in st.session_state.lex_room_chat[-5:]:
            st.markdown(f"**{entry['sender']}:** {entry['msg']}")
        room_msg = st.text_input("Drop a live note in the room...", key="room_input")
        if st.button("Send to Room"):
            if room_msg.strip():
                st.session_state.lex_room_chat.append({"sender": user["handle"], "msg": room_msg.strip()})
                st.rerun()
with right_col:
    tab_top8, tab_remix, tab_radar = st.tabs([
        "✦ Top 8 Friends",
        "🎨 Profile Studio & AI Vibe Remix",
        "📡 Inner Circle Radar",
    ])

    with tab_top8:
        st.markdown("#### Your Ranked Inner Circle (Zero Algorithms)")
        top_cols = st.columns(2)
        for idx, friend in enumerate(st.session_state.lex_top8):
            with top_cols[idx % 2]:
                st.markdown(
                    f'<div class="lex-card"><div style="display:flex;justify-content:space-between;">'
                    f'<strong>#{friend["rank"]} {friend["name"]}</strong>'
                    f'<span style="color:#F472B6;">{friend["handle"]}</span></div>'
                    f'<div style="font-size:12px;color:#A1A1AA;margin-top:6px;">{friend["mood"]}</div>'
                    f'<div style="font-size:11px;color:#E4E4E7;margin-top:4px;">🎵 {friend["anthem"]}</div></div>',
                    unsafe_allow_html=True,
                )
                if idx > 0 and st.button(f"Move {friend['handle']} Up ↑", key=f"up_{idx}"):
                    lst = st.session_state.lex_top8
                    lst[idx], lst[idx - 1] = lst[idx - 1], lst[idx]
                    for r_i, item in enumerate(lst):
                        item["rank"] = r_i + 1
                    st.rerun()

        with st.form("add_top_friend"):
            st.markdown("**Add Friend to Top 8**")
            fc1, fc2 = st.columns(2)
            with fc1:
                f_name = st.text_input("Friend Name", placeholder="Alex Rivera")
                f_handle = st.text_input("Friend @handle", placeholder="Alex")
            with fc2:
                f_mood = st.text_input("Status / Mood", value="Online • Chilling 🎧")
                f_anthem = st.selectbox("Their Anthem", list(ANTHEM_TRACKS.keys()), key="f_ant")
            if st.form_submit_button("Pin to Top 8") and len(st.session_state.lex_top8) < 8:
                clean_fh = f_handle.strip().lstrip("@").replace(" ", "")
                if f_name.strip() and clean_fh:
                    st.session_state.lex_top8.append({
                        "rank": len(st.session_state.lex_top8) + 1,
                        "handle": f"@{clean_fh}",
                        "name": f_name.strip(),
                        "mood": f_mood.strip(),
                        "anthem": f_anthem,
                    })
                    st.rerun()

    with tab_remix:
        st.markdown("#### ✨ AI Vibe Remix (Instant Profile Skin)")
        vibe_prompt = st.text_input(
            "Describe your aesthetic vibe",
            placeholder="e.g., LexiTech obsidian, velvet rose neon, cyber chrome, or midnight cobalt",
        )
        if st.button("Remix My Profile Skin ⚡"):
            vp = vibe_prompt.lower()
            if "rose" in vp or "pink" in vp or "velvet" in vp:
                st.session_state.lex_theme = PRESET_THEMES["Velvet Rose Neon"].copy()
                user["anthem"] = "Velvet Chrome Rhodes"
            elif "cobalt" in vp or "blue" in vp or "2006" in vp:
                st.session_state.lex_theme = PRESET_THEMES["Midnight Cobalt"].copy()
                user["anthem"] = "Y2K Cobalt Synth"
            elif "chrome" in vp or "silver" in vp or "cyber" in vp:
                st.session_state.lex_theme = PRESET_THEMES["Y2K Cyber Chrome"].copy()
                user["anthem"] = "Neon Arcade Pulse"
            else:
                st.session_state.lex_theme = PRESET_THEMES["LexiTech Obsidian (Official)"].copy()
                user["anthem"] = "Y2K Cobalt Synth"
            st.rerun()

        preset_choice = st.selectbox("Or Pick a Classic Theme Preset", list(PRESET_THEMES.keys()))
        if st.button("Apply Preset"):
            st.session_state.lex_theme = PRESET_THEMES[preset_choice].copy()
            st.rerun()

        new_mood = st.text_input("Update Mood Badge", value=user["mood"])
        new_bio = st.text_area("Update About Me", value=user["bio"])
        new_meet = st.text_input("Update Who I'd Like to Meet", value=user["who_to_meet"])
        if st.button("Save Profile Details"):
            user["mood"] = new_mood.strip()
            user["bio"] = new_bio.strip()
            user["who_to_meet"] = new_meet.strip()
            st.rerun()

    with tab_radar:
        st.markdown("#### 📡 Zero-Algorithm Inner Circle Radar")
        st.caption("No public follower counts. No ads. Just live status & anthems from your Top 8.")
        for friend in st.session_state.lex_top8:
            st.markdown(
                f"- **{friend['name']}** (`{friend['handle']}`) — {friend['mood']} | Playing: *{friend['anthem']}*"
            )

st.markdown("---")
st.caption("© 2026 LeX Social // Built & Engineered by Heidi Seckman at LexiTech Studio. Ages 13+ Only.")
