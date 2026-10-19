import os
import sys
import time
from pathlib import Path
import httpx

MODEL_URL = "https://huggingface.co/SWivid/F5-TTS/resolve/main/F5TTS_v1_Base/model_1250000.safetensors"
TARGET_DIR = Path(__file__).resolve().parent / "models" / "F5-TTS"
TARGET_FILE = TARGET_DIR / "model_1250000.safetensors"
TEMP_FILE = TARGET_DIR / "model_1250000.safetensors.download"

def main():
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    if TARGET_FILE.exists() and TARGET_FILE.stat().st_size > 1000000000:
        print(f"Model already downloaded: {TARGET_FILE} ({TARGET_FILE.stat().st_size} bytes)")
        return

    print(f"Downloading F5-TTS Base model from: {MODEL_URL}")
    print(f"Target path: {TARGET_FILE}")

    downloaded = 0
    if TEMP_FILE.exists():
        downloaded = TEMP_FILE.stat().st_size
        print(f"Resuming download from byte: {downloaded}")

    headers = {}
    if downloaded > 0:
        headers["Range"] = f"bytes={downloaded}-"

    with httpx.stream("GET", MODEL_URL, headers=headers, follow_redirects=True, timeout=120.0) as response:
        if response.status_code not in (200, 206):
            print(f"Failed to download: HTTP {response.status_code}", file=sys.stderr)
            sys.exit(1)

        total = int(response.headers.get("content-length", 0))
        if response.status_code == 206:
            total += downloaded

        mode = "ab" if downloaded > 0 and response.status_code == 206 else "wb"
        if mode == "wb":
            downloaded = 0

        last_print = time.time()
        with open(TEMP_FILE, mode) as f:
            for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_print >= 2.0:
                        pct = (downloaded / total * 100) if total else 0
                        mb = downloaded / (1024 * 1024)
                        tot_mb = total / (1024 * 1024) if total else 0
                        print(f"Progress: {mb:.1f} MB / {tot_mb:.1f} MB ({pct:.1f}%)")
                        last_print = now

    TEMP_FILE.rename(TARGET_FILE)
    print(f"Download complete: {TARGET_FILE} ({TARGET_FILE.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
