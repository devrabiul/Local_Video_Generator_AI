import urllib.request
from pathlib import Path
import subprocess

MUSIC_DIR = Path(__file__).resolve().parent.parent / "music"
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

TRACKS = {
    "epic_battle.ogg": "https://upload.wikimedia.org/wikipedia/commons/4/47/Alexander_Nakarada_-_The_Return_%28cc-by%29_%28filmmusic%29.ogg",
    "dramatic_history.ogg": "https://upload.wikimedia.org/wikipedia/commons/6/6f/Dramatic_Trailer_by_Rafael_Krux.ogg",
    "blockbuster_suspense.ogg": "https://upload.wikimedia.org/wikipedia/commons/1/12/Cinema_Blockbuster_Trailer_3_by_Sascha_Ende.ogg"
}

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) VidForge/1.0'}

for name, url in TRACKS.items():
    ogg_path = MUSIC_DIR / name
    mp3_name = name.replace(".ogg", ".mp3")
    mp3_path = MUSIC_DIR / mp3_name
    print(f"Fetching {name}...")
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req) as resp, open(ogg_path, "wb") as out:
            out.write(resp.read())
        # Convert to mp3
        subprocess.run(["ffmpeg", "-y", "-i", str(ogg_path), "-q:a", "2", str(mp3_path)], check=True, capture_output=True)
        ogg_path.unlink(missing_ok=True)
        print(f"Successfully prepared: {mp3_path.name} ({mp3_path.stat().st_size / (1024*1024):.2f} MB)")
    except Exception as e:
        print(f"Failed to fetch {name}: {e}")
