"""
Lyria 2 Seed 對照測試腳本
=========================
驗證 Lyria 2 的 seed 參數是否能：
1. 不同 seed → 產生不同結果（解決客戶重複問題）
2. 相同 seed → 可重現相同結果

使用方式：
  uv run test_lyria2_seed.py
"""

import base64
import os
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

PROJECT_ID = os.environ.get("PROJECT_ID")

if not PROJECT_ID or PROJECT_ID == "your-project-id":
    print("ERROR: 請先在 .env 設定 PROJECT_ID")
    sys.exit(1)

# Lyria 2 使用 us-central1（不是 global）
client = genai.Client(vertexai=True, project=PROJECT_ID, location="us-central1")

MODEL = "lyria-002"
OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

RATE_LIMIT_DELAY = 7

PROMPT = (
    "Sophisticated, rhythmic, and aspirational track with crisp 808 "
    "percussion, digital plucks, and muted electric guitar rhythmic strums."
)


def save_audio(predictions, test_name: str) -> list[str]:
    """從 predict response 儲存音檔。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved = []

    for i, pred in enumerate(predictions):
        audio_content = pred.get("audioContent") or pred.get("audio_content")
        if not audio_content:
            print(f"  [WARN] prediction {i} 無音檔內容")
            continue

        audio_data = base64.b64decode(audio_content)
        filename = OUTPUT_DIR / f"{test_name}_{timestamp}_{i}.wav"
        filename.write_bytes(audio_data)
        saved.append(str(filename))
        size_kb = len(audio_data) / 1024
        print(f"  [AUDIO] {filename} ({size_kb:.1f} KB)")

    return saved


def main():
    print("=" * 60)
    print("Lyria 2 Seed 對照測試")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: {PROJECT_ID}")
    print(f"Model: {MODEL}")
    print("=" * 60)

    # --- 測試 A：不同 seed 應產生不同結果 ---
    print("\n--- 測試 A：不同 seed → 應產生不同結果 ---")
    print(f"  Prompt: {PROMPT[:80]}...")

    seeds = [111, 222, 333, 444]
    results_a = []

    for i, seed in enumerate(seeds):
        print(f"\n  Seed={seed} (第 {i + 1}/4 次)")
        try:
            response = client.models.predict(
                model=MODEL,
                instances=[{"prompt": PROMPT, "seed": seed}],
            )
            files = save_audio(response.predictions, f"lyria2_seed_{seed}")
            results_a.append({"seed": seed, "status": "OK", "files": files})
        except Exception as e:
            print(f"  [ERROR] {e}")
            results_a.append({"seed": seed, "status": f"FAIL: {e}", "files": []})

        if i < len(seeds) - 1:
            print(f"  (等待 {RATE_LIMIT_DELAY} 秒...)")
            time.sleep(RATE_LIMIT_DELAY)

    # --- 測試 B：相同 seed 應可重現 ---
    print("\n\n--- 測試 B：相同 seed → 應可重現相同結果 ---")
    fixed_seed = 12345

    results_b = []
    for i in range(1, 3):
        print(f"\n  Seed={fixed_seed} (第 {i}/2 次)")
        try:
            response = client.models.predict(
                model=MODEL,
                instances=[{"prompt": PROMPT, "seed": fixed_seed}],
            )
            files = save_audio(response.predictions, f"lyria2_repro_{i}")
            results_b.append({"run": i, "status": "OK", "files": files})
        except Exception as e:
            print(f"  [ERROR] {e}")
            results_b.append({"run": i, "status": f"FAIL: {e}", "files": []})

        if i < 2:
            print(f"  (等待 {RATE_LIMIT_DELAY} 秒...)")
            time.sleep(RATE_LIMIT_DELAY)

    # --- 結果摘要 ---
    print("\n" + "=" * 60)
    print("測試結果摘要")
    print("=" * 60)

    print("\n測試 A（不同 seed）：")
    sizes_a = []
    for r in results_a:
        print(f"  Seed {r['seed']}: {r['status']}")
        for f in r["files"]:
            if f.endswith(".wav"):
                size = os.path.getsize(f)
                sizes_a.append(size)

    if len(sizes_a) >= 2:
        if len(set(sizes_a)) == 1:
            print("  WARNING: 檔案大小完全相同，需人工聽確認")
        else:
            print("  OK: 檔案大小不同，初步判斷有差異")

    print("\n測試 B（相同 seed 重現性）：")
    sizes_b = []
    for r in results_b:
        print(f"  第 {r['run']} 次: {r['status']}")
        for f in r["files"]:
            if f.endswith(".wav"):
                size = os.path.getsize(f)
                sizes_b.append(size)

    if len(sizes_b) == 2:
        if sizes_b[0] == sizes_b[1]:
            print("  OK: 相同 seed 產生相同大小檔案（可能可重現）")
        else:
            print("  INFO: 檔案大小不同，即使相同 seed 也非完全重現")

    print(f"\n輸出資料夾: {OUTPUT_DIR.resolve()}")


if __name__ == "__main__":
    main()
