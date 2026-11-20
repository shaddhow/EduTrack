import sys
import os
import time
import urllib.request
import argparse

MODELS = {
    "qwen": {
        "name": "Qwen 2.5 3B Instruct (Multilingual & Banglish Master, Recommended)",
        "url": "https://huggingface.co/Qwen/Qwen2.5-3B-Instruct-GGUF/resolve/main/qwen2.5-3b-instruct-q4_k_m.gguf",
        "dest": "d:/EduTrack/models/qwen2.5-3b-instruct-q4_k_m.gguf",
        "min_size_mb": 1800,
    },
    "llama": {
        "name": "Llama 3.2 1B Instruct (Lightweight English Model)",
        "url": "https://huggingface.co/bartowski/Llama-3.2-1B-Instruct-GGUF/resolve/main/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
        "dest": "d:/EduTrack/models/llama-3.2-1b-instruct-q4_k_m.gguf",
        "min_size_mb": 700,
    }
}

def download_model(model_key="qwen"):
    cfg = MODELS.get(model_key, MODELS["qwen"])
    dest_path = cfg["dest"]
    url = cfg["url"]
    min_size_bytes = cfg["min_size_mb"] * 1024 * 1024

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    if os.path.exists(dest_path) and os.path.getsize(dest_path) >= min_size_bytes:
        size_mb = os.path.getsize(dest_path) / (1024 * 1024)
        print(f"Model already downloaded: {cfg['name']}")
        print(f"Location: {dest_path} ({size_mb:.1f} MB)")
        return

    print("==================================================")
    print(f"EduTrack Offline Neural Engine Model Downloader")
    print(f"Target: {cfg['name']}")
    print(f"URL: {url}")
    print(f"Destination: {dest_path}")
    print("==================================================\n")

    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 EduTrack/2.0"})
    with urllib.request.urlopen(req) as resp, open(dest_path, "wb") as out_file:
        total_size = int(resp.headers.get("content-length", 0))
        downloaded = 0
        chunk_size = 1024 * 1024 * 4  # 4MB chunks
        t0 = time.time()
        last_print = t0

        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out_file.write(chunk)
            downloaded += len(chunk)
            now = time.time()
            if now - last_print >= 3 or downloaded == total_size:
                elapsed = now - t0
                speed_mb = (downloaded / (1024 * 1024)) / max(elapsed, 0.001)
                pct = (downloaded / total_size * 100) if total_size else 0
                dl_mb = downloaded / (1024 * 1024)
                tot_mb = total_size / (1024 * 1024)
                print(f"\rProgress: {dl_mb:.1f}/{tot_mb:.1f} MB ({pct:.1f}%) | Speed: {speed_mb:.2f} MB/s", end="", flush=True)
                last_print = now

    print(f"\n\nDownload finished successfully! Model active at {dest_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download EduTrack GGUF models")
    parser.add_argument("--model", choices=["qwen", "llama"], default="qwen", help="Model to download (default: qwen)")
    args = parser.parse_args()
    download_model(args.model)
