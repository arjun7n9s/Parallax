"""Final compression: MP4 with better text quality (CRF 23) and GIF fallback.

CRF 28 is too aggressive for text — characters become hard to read. CRF 23
keeps text crisp. 720p, 12fps, CRF 23 → expect ~500KB-1MB.
"""
import subprocess
from pathlib import Path

SRC = Path(r"C:/Users/arjun/Downloads/Arjun's video 🍨.gif")
DOCS = Path(r"C:/Users/arjun/Desktop/PSBs/GenAI-Cybersec-hackathon/docs/assets")
DOCS.mkdir(parents=True, exist_ok=True)

MP4 = DOCS / "agents_debate.mp4"
GIF = DOCS / "agents_debate.gif"

# Trial different MP4 settings - find the smallest that keeps text crisp
trials = [
    # (width, fps, crf, label)
    (720, 12, 23, "720-12-23"),
    (720, 12, 26, "720-12-26"),
    (720, 10, 23, "720-10-23"),
    (640, 12, 23, "640-12-23"),
    (640, 10, 23, "640-10-23"),
    (640, 12, 26, "640-12-26"),
    (800, 12, 25, "800-12-25"),
    (800, 10, 25, "800-10-25"),
]

best_size = float("inf")
best_label = None
best_path = None

WORK = Path(r"C:/Users/arjun/Desktop/PSBs/GenAI-Cybersec-hackathon/tmp-live/gif_work")
WORK.mkdir(parents=True, exist_ok=True)

print("MP4 trials:")
for width, fps, crf, label in trials:
    out = WORK / f"mp4_{label}.mp4"
    r = subprocess.run([
        "ffmpeg", "-y", "-i", str(SRC),
        "-vf", f"trim=start=3:duration=18,setpts=PTS-STARTPTS,fps={fps},scale={width}:-2:flags=lanczos",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", str(crf),
        "-preset", "slow", "-movflags", "+faststart", "-an",
        str(out),
    ], capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  [{label}] FAILED")
        continue
    size = out.stat().st_size
    print(f"  [{label:14s}] {width}px, {fps}fps, CRF {crf} → {size/1024:.0f} KB")
    if size < best_size:
        best_size = size
        best_label = label
        best_path = out

print(f"\nBest MP4: {best_label} at {best_size/1024:.0f} KB")

if best_path:
    shutil_copy = subprocess.run(["cp", str(best_path), str(MP4)], capture_output=True, text=True)
    if shutil_copy.returncode != 0:
        # Try Python copy
        import shutil
        shutil.copy(best_path, MP4)
    print(f"Saved: {MP4} ({MP4.stat().st_size/1024:.0f} KB)")

# 2) GIF fallback - 480px, 8fps, 64 colors (smaller for README inline)
print("\nGIF fallback (480px, 8fps, 64 colors)…")
filter_str = (
    "trim=start=3:duration=18,setpts=PTS-STARTPTS,"
    "fps=8,"
    "scale=480:-2:flags=lanczos,"
    "split [a][b];"
    "[a] palettegen=stats_mode=full:max_colors=64 [p];"
    "[b][p] paletteuse=dither=sierra2_4a:diff_mode=rectangle:new=1"
)
subprocess.run([
    "ffmpeg", "-y", "-i", str(SRC),
    "-lavfi", filter_str,
    "-loop", "0", "-an",
    str(GIF),
], check=True, capture_output=True)
print(f"  GIF: {GIF.stat().st_size/1024:.0f} KB")
