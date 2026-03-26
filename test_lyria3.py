"""
Lyria 3 測試腳本 - 迪威智能 x Master Concept
=============================================
對應會議 Action Items：
1. 測試 BPM 與樂理 Prompt 的遵循精準度
2. 測試批次生成是否重複（Lyria 3 無 seed 參數）
3. 測試圖片轉音樂 + Safety Filter（含兒童圖片）

使用方式：
  uv run test_lyria3.py              # 執行全部測試
  uv run test_lyria3.py --test bpm   # 只跑 BPM 測試
  uv run test_lyria3.py --test dup   # 只跑重複性測試
  uv run test_lyria3.py --test img   # 只跑圖片測試
"""

import argparse
import base64
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google import genai

load_dotenv()

PROJECT_ID = os.environ.get("PROJECT_ID")
LOCATION = os.environ.get("LOCATION", "global")

if not PROJECT_ID or PROJECT_ID == "your-project-id":
    print("ERROR: 請先在 .env 設定 PROJECT_ID")
    sys.exit(1)

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

MODEL_CLIP = "lyria-3-clip-preview"  # 30 秒 clip
MODEL_PRO = "lyria-3-pro-preview"  # 最長 ~184 秒

OUTPUT_DIR = Path("outputs")
OUTPUT_DIR.mkdir(exist_ok=True)

# Rate limit: 10 QPM → 每次呼叫後等 7 秒保守避免觸發
RATE_LIMIT_DELAY = 7


def save_interaction(interaction, test_name: str) -> list[str]:
    """儲存 interaction 的音檔與文字輸出，回傳儲存的檔案路徑列表。"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    saved_files = []

    for i, output in enumerate(interaction.outputs):
        if output.type == "text":
            text = output.text
            # 清除 section tags
            text = re.sub(r"\[.*?\]", "", text)
            text_file = OUTPUT_DIR / f"{test_name}_{timestamp}_lyrics.txt"
            text_file.write_text(text.strip(), encoding="utf-8")
            saved_files.append(str(text_file))
            print(f"  [TEXT] {text_file}")
            # 顯示前 200 字
            preview = text.strip()[:200]
            if preview:
                print(f"         {preview}...")

        elif output.type == "audio":
            audio_data = base64.b64decode(output.data)
            audio_file = OUTPUT_DIR / f"{test_name}_{timestamp}_{i}.mp3"
            audio_file.write_bytes(audio_data)
            saved_files.append(str(audio_file))
            size_kb = len(audio_data) / 1024
            print(f"  [AUDIO] {audio_file} ({size_kb:.1f} KB)")

    return saved_files


def test_bpm_accuracy():
    """測試 1：BPM 與樂理 Prompt 遵循精準度。"""
    print("\n" + "=" * 60)
    print("測試 1：BPM 與樂理 Prompt 遵循精準度")
    print("=" * 60)

    bpm_prompts = [
        {
            "bpm": 120,
            "prompt": (
                "120 BPM upbeat electronic dance music, energetic synth lead, "
                "punchy four-on-the-floor kicks, festival energy, no vocals, "
                "bright arpeggiated synth patterns"
            ),
        },
        {
            "bpm": 85,
            "prompt": (
                "85 BPM chill lo-fi hip hop beat, jazzy Rhodes piano chords, "
                "vinyl crackle texture, mellow boom-bap drums, relaxing "
                "rainy day atmosphere, no vocals"
            ),
        },
        {
            "bpm": 140,
            "prompt": (
                "140 BPM aggressive trap beat, heavy 808 sub bass, dark "
                "menacing synth pads, rapid hi-hat rolls, cinematic tension "
                "building, no vocals"
            ),
        },
        {
            "bpm": 100,
            "prompt": (
                "100 BPM acoustic folk pop, warm fingerpicking guitar, "
                "soft brushed drums, gentle bass line, heartfelt and "
                "intimate atmosphere, no vocals"
            ),
        },
    ]

    results = []
    for i, item in enumerate(bpm_prompts, 1):
        print(f"\n--- BPM 測試 {i}/4 | 目標 BPM: {item['bpm']} ---")
        print(f"  Prompt: {item['prompt'][:80]}...")

        try:
            interaction = client.interactions.create(
                model=MODEL_PRO,
                input=item["prompt"],
            )
            files = save_interaction(interaction, f"bpm_{item['bpm']}")
            results.append({"bpm": item["bpm"], "status": "OK", "files": files})
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({"bpm": item["bpm"], "status": f"FAIL: {e}", "files": []})

        if i < len(bpm_prompts):
            print(f"  (等待 {RATE_LIMIT_DELAY} 秒避免 rate limit...)")
            time.sleep(RATE_LIMIT_DELAY)

    print("\n--- BPM 測試結果摘要 ---")
    for r in results:
        print(f"  BPM {r['bpm']}: {r['status']}")
    print("  提醒：請人工聽音檔驗證實際 BPM 是否接近目標值")

    return results


def test_duplicate_generation():
    """測試 2：同一 prompt 連續生成 4 次，檢查是否重複。"""
    print("\n" + "=" * 60)
    print("測試 2：批次生成重複性測試（同一 Prompt x4）")
    print("=" * 60)

    prompt = (
        "Sophisticated, rhythmic, and aspirational track with crisp 808 "
        "percussion, digital plucks, and muted electric guitar rhythmic "
        "strums. Include breathy, airy alto female vocal textures with "
        "melodic, minimalist oohs and aahs with heavy reverb and "
        "rhythmic delay."
    )

    print(f"  固定 Prompt: {prompt[:100]}...")
    results = []

    for i in range(1, 5):
        print(f"\n--- 第 {i}/4 次生成 ---")
        try:
            interaction = client.interactions.create(
                model=MODEL_PRO,
                input=prompt,
            )
            files = save_interaction(interaction, f"dup_test_{i}")
            results.append({"run": i, "status": "OK", "files": files})
        except Exception as e:
            print(f"  [ERROR] {e}")
            results.append({"run": i, "status": f"FAIL: {e}", "files": []})

        if i < 4:
            print(f"  (等待 {RATE_LIMIT_DELAY} 秒避免 rate limit...)")
            time.sleep(RATE_LIMIT_DELAY)

    print("\n--- 重複性測試結果摘要 ---")
    audio_sizes = []
    for r in results:
        print(f"  第 {r['run']} 次: {r['status']}")
        for f in r["files"]:
            if f.endswith(".mp3"):
                size = os.path.getsize(f)
                audio_sizes.append(size)
                print(f"    音檔大小: {size} bytes")

    if len(audio_sizes) >= 2:
        all_same = len(set(audio_sizes)) == 1
        if all_same:
            print("  WARNING: 所有音檔大小完全相同，可能仍有重複問題")
        else:
            print("  OK: 音檔大小不同，初步判斷非完全重複")
    print("  提醒：請人工聽音檔確認旋律/編曲是否明顯不同")

    return results


def test_image_to_music():
    """測試 3：圖片轉音樂 + Safety Filter 測試。"""
    print("\n" + "=" * 60)
    print("測試 3：圖片轉音樂 & Safety Filter")
    print("=" * 60)

    test_images_dir = Path("test_images")

    # 檢查 test_images 資料夾內有沒有圖片
    image_extensions = {".png", ".jpg", ".jpeg", ".webp"}
    images = [
        f
        for f in test_images_dir.iterdir()
        if f.suffix.lower() in image_extensions
    ]

    if not images:
        print("  WARNING: test_images/ 資料夾內沒有圖片")
        print("  請放入測試圖片後重新執行，建議：")
        print("    - 一般風景/花朵圖片（預期成功）")
        print("    - 動物圖片（預期成功）")
        print("    - 兒童相關圖片（測試 Safety Filter）")
        return []

    prompt_text = (
        "Generate an instrumental music clip based on this image. "
        "Start slowly and build in intensity. Professional cinematic quality."
    )

    results = []
    for i, img_path in enumerate(sorted(images), 1):
        print(f"\n--- 圖片測試 {i}/{len(images)} | {img_path.name} ---")

        # 讀取圖片並轉 base64
        img_bytes = img_path.read_bytes()
        base64_image = base64.b64encode(img_bytes).decode("utf-8")

        # 判斷 MIME type
        suffix = img_path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
        }
        mime_type = mime_map.get(suffix, "image/png")

        try:
            interaction = client.interactions.create(
                model=MODEL_CLIP,
                input=[
                    {"type": "text", "text": prompt_text},
                    {"type": "image", "mime_type": mime_type, "data": base64_image},
                ],
            )
            files = save_interaction(interaction, f"img_{img_path.stem}")
            results.append({
                "image": img_path.name,
                "status": "OK",
                "files": files,
            })
        except Exception as e:
            error_msg = str(e)
            print(f"  [ERROR] {error_msg}")
            results.append({
                "image": img_path.name,
                "status": f"BLOCKED/FAIL: {error_msg[:200]}",
                "files": [],
            })

        if i < len(images):
            print(f"  (等待 {RATE_LIMIT_DELAY} 秒避免 rate limit...)")
            time.sleep(RATE_LIMIT_DELAY)

    print("\n--- 圖片轉音樂測試結果摘要 ---")
    for r in results:
        status_icon = "OK" if r["status"] == "OK" else "BLOCKED"
        print(f"  {r['image']}: {status_icon}")
        if r["status"] != "OK":
            print(f"    Error: {r['status']}")

    return results


def test_nursery_rhyme():
    """測試 4：兒童圖片 + 兒歌歌詞組合，驗證 Safety Filter。"""
    print("\n" + "=" * 60)
    print("測試 4：兒童圖片 + 兒歌歌詞 Safety Filter 測試")
    print("=" * 60)

    baby_image = Path("test_images/image-test.jpg")
    if not baby_image.exists():
        print("  ERROR: test_images/image-test.jpg 不存在，跳過此測試")
        return []

    img_bytes = baby_image.read_bytes()
    base64_image = base64.b64encode(img_bytes).decode("utf-8")

    nursery_cases = [
        {
            "name": "英文兒歌_Twinkle",
            "prompt": (
                "Genre: Gentle, soothing lullaby with soft music box and "
                "acoustic guitar.\n\n"
                "Lyrics:\n"
                "Twinkle, twinkle, little star,\n"
                "How I wonder what you are.\n"
                "Up above the world so high,\n"
                "Like a diamond in the sky.\n"
                "Twinkle, twinkle, little star,\n"
                "How I wonder what you are."
            ),
        },
        {
            "name": "中文兒歌_兩隻老虎",
            "prompt": (
                "Genre: Playful, cheerful children's song with xylophone, "
                "ukulele, and hand claps.\n\n"
                "Lyrics:\n"
                "兩隻老虎，兩隻老虎，\n"
                "跑得快，跑得快，\n"
                "一隻沒有眼睛，\n"
                "一隻沒有尾巴，\n"
                "真奇怪，真奇怪。"
            ),
        },
        {
            "name": "中文兒歌_小星星",
            "prompt": (
                "Genre: Warm, tender lullaby with piano and soft strings.\n\n"
                "Lyrics:\n"
                "一閃一閃亮晶晶，\n"
                "滿天都是小星星，\n"
                "掛在天空放光明，\n"
                "好像許多小眼睛。\n"
                "一閃一閃亮晶晶，\n"
                "滿天都是小星星。"
            ),
        },
    ]

    results = []
    for i, case in enumerate(nursery_cases, 1):
        print(f"\n--- 兒歌測試 {i}/{len(nursery_cases)} | {case['name']} ---")
        print(f"  圖片: {baby_image.name}")
        print(f"  歌詞: {case['prompt'][:80]}...")

        try:
            interaction = client.interactions.create(
                model=MODEL_CLIP,
                input=[
                    {"type": "text", "text": case["prompt"]},
                    {"type": "image", "mime_type": "image/jpeg", "data": base64_image},
                ],
            )
            files = save_interaction(interaction, f"nursery_{case['name']}")
            results.append({
                "name": case["name"],
                "status": "OK",
                "files": files,
            })
        except Exception as e:
            error_msg = str(e)
            print(f"  [ERROR] {error_msg}")
            results.append({
                "name": case["name"],
                "status": f"BLOCKED/FAIL: {error_msg[:200]}",
                "files": [],
            })

        if i < len(nursery_cases):
            print(f"  (等待 {RATE_LIMIT_DELAY} 秒避免 rate limit...)")
            time.sleep(RATE_LIMIT_DELAY)

    print("\n--- 兒歌測試結果摘要 ---")
    for r in results:
        status_icon = "OK" if r["status"] == "OK" else "BLOCKED"
        print(f"  {r['name']}: {status_icon}")
        if r["status"] != "OK":
            print(f"    Error: {r['status']}")

    return results


def main():
    parser = argparse.ArgumentParser(description="Lyria 3 測試腳本")
    parser.add_argument(
        "--test",
        choices=["bpm", "dup", "img", "nursery", "all"],
        default="all",
        help="選擇要執行的測試 (預設: all)",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("Lyria 3 測試腳本 - 迪威智能 x Master Concept")
    print(f"時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Project: {PROJECT_ID}")
    print(f"Location: {LOCATION}")
    print(f"Models: {MODEL_PRO} / {MODEL_CLIP}")
    print("=" * 60)

    all_results = {}

    if args.test in ("bpm", "all"):
        all_results["bpm"] = test_bpm_accuracy()

    if args.test in ("dup", "all"):
        if all_results:
            print(f"\n(測試間等待 {RATE_LIMIT_DELAY} 秒...)")
            time.sleep(RATE_LIMIT_DELAY)
        all_results["duplicate"] = test_duplicate_generation()

    if args.test in ("img", "all"):
        if all_results:
            print(f"\n(測試間等待 {RATE_LIMIT_DELAY} 秒...)")
            time.sleep(RATE_LIMIT_DELAY)
        all_results["image"] = test_image_to_music()

    if args.test in ("nursery", "all"):
        if all_results:
            print(f"\n(測試間等待 {RATE_LIMIT_DELAY} 秒...)")
            time.sleep(RATE_LIMIT_DELAY)
        all_results["nursery"] = test_nursery_rhyme()

    # 最終報告
    print("\n" + "=" * 60)
    print("全部測試完成！")
    print("=" * 60)
    print(f"輸出資料夾: {OUTPUT_DIR.resolve()}")

    output_files = list(OUTPUT_DIR.iterdir())
    mp3_count = sum(1 for f in output_files if f.suffix == ".mp3")
    txt_count = sum(1 for f in output_files if f.suffix == ".txt")
    print(f"生成音檔: {mp3_count} 個 MP3")
    print(f"歌詞/描述: {txt_count} 個 TXT")

    print("\n後續驗證項目：")
    print("  1. 人工聽 BPM 測試音檔，確認是否接近指定 BPM")
    print("  2. 比較 4 次重複生成的音檔，確認旋律/編曲是否不同")
    print("  3. 檢查圖片 Safety Filter 結果（哪些被阻擋）")


if __name__ == "__main__":
    main()
