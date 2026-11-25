"""Sound for a reel with no narrator (the chat story, the pause challenge): a library track under effects at given times.
  python3 fxmix.py <silent.mp4> <events.json> <track title> <out.mp4> [music_db]
events.json: [[t, "pop"|"whoosh"|"thud"|"ding"|"rise"|"boom"|"tick"], ...]; the result is -14.5 LUFS like the story reels."""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.dirname(HERE))
import numpy as np, soundfile as sf, sounds as SD
os.environ.setdefault("EXPLAINER_TRACK", "")


def main(silent, events, title, out, music_db=-6.0):
    import make as M
    os.environ["EXPLAINER_TRACK"] = title; tr = M.track(title); f = os.path.join(M.MUSIC_DIR, tr["file"])
    T = float(subprocess.run([M.FFMPEG.replace("ffmpeg", "ffprobe") if "ffmpeg" in M.FFMPEG else "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", silent], capture_output=True, text=True).stdout)
    raw = np.frombuffer(subprocess.run([M.FFMPEG, "-v", "error", "-i", f, "-ac", "2", "-ar", str(SD.SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32).reshape(-1, 2)
    b = int(SD.SR); lv = np.sqrt((raw[: len(raw) // b * b].mean(1).reshape(-1, b) ** 2).mean(1)); go = int(np.argmax(lv >= .8 * np.median(lv))); raw = raw[go * b:]
    n = int(T * SD.SR); m = np.concatenate([raw] * (n // len(raw) + 1))[:n].copy(); k = int(1.2 * SD.SR); m[-k:] *= np.linspace(1, 0, k)[:, None]
    m *= 10 ** (music_db / 20) * .25 / (np.sqrt((m ** 2).mean()) + 1e-9)
    hits = np.zeros((n + SD.SR, 2), np.float32)
    for t, kind in json.load(open(events)):
        x = SD.whoosh(.3) if kind == "whoosh" else SD.pop() if kind == "tick" else getattr(SD, kind)(); x = np.asarray(x, np.float32); a = int(t * SD.SR); x = x[: len(hits) - a]
        hits[a:a + len(x)] += (x * ((.35 if kind == "tick" else .7) / (np.abs(x).max() + 1e-9)))[:, None]
    mix = m + hits[:n]; pre = out + ".wav"; sf.write(pre, mix, SD.SR)
    heard = re.findall(r"I:\s+(-?[\d.]+) LUFS", subprocess.run([M.FFMPEG, "-hide_banner", "-nostats", "-i", pre, "-af", "ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr)
    gain = -14.5 - float(heard[-1]) if heard else 0
    subprocess.run([M.FFMPEG, "-v", "error", "-y", "-i", silent, "-i", pre, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-af", f"volume={gain:.2f}dB,alimiter=limit=0.84:level=false",
                    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", "-t", f"{T:.3f}", out], check=True)
    os.remove(pre); return tr


if __name__ == "__main__":
    tr = main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], float(sys.argv[5]) if len(sys.argv) > 5 else -6.0); print(sys.argv[4], tr.get("credit"))
