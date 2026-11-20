import io
import wave
import numpy as np


ANTHEM_TRACKS = {
    "Y2K Cobalt Synth": {"bpm": 118, "notes": [261.63, 329.63, 392.00, 523.25], "wave": "saw"},
    "Midnight Tokyo Lo-Fi": {"bpm": 84, "notes": [220.00, 261.63, 329.63, 392.00], "wave": "sine"},
    "Velvet Chrome Rhodes": {"bpm": 96, "notes": [196.00, 246.94, 293.66, 369.99], "wave": "tri"},
    "Neon Arcade Pulse": {"bpm": 128, "notes": [293.66, 349.23, 440.00, 587.33], "wave": "saw"},
}


def generate_anthem_wav(track_name: str, duration_sec: int = 12) -> bytes:
    cfg = ANTHEM_TRACKS.get(track_name, ANTHEM_TRACKS["Y2K Cobalt Synth"])
    sr = 22050
    t = np.linspace(0, duration_sec, int(sr * duration_sec), endpoint=False)
    beat_len = 60.0 / cfg["bpm"]
    notes = cfg["notes"]
    step_idx = (t / beat_len).astype(int) % len(notes)
    freqs = np.array([notes[i] for i in step_idx])
    phase = 2.0 * np.pi * np.cumsum(freqs) / sr

    if cfg["wave"] == "saw":
        sig = 0.5 * np.sin(phase) + 0.25 * np.sin(2 * phase)
    elif cfg["wave"] == "tri":
        sig = (2.0 / np.pi) * np.arcsin(np.sin(phase))
    else:
        sig = np.sin(phase) + 0.3 * np.sin(0.5 * phase)

    local_t = t % beat_len
    env = np.exp(-2.6 * local_t) * np.minimum(1.0, local_t / 0.02)
    bass = 0.35 * np.sin(2.0 * np.pi * (freqs * 0.5) * t)
    mix = (sig * env * 0.65 + bass) * 0.45

    pcm = np.int16(np.clip(mix, -1.0, 1.0) * 32767)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    return buf.getvalue()
