# Lyria 3 API 測試報告

**測試日期：** 2026-03-26
**測試專案：** tw-maxchens-sandbox
**測試目的：** 驗證 Lyria 3 是否解決迪威團隊在 Lyria 2 遇到的痛點
**對應會議：** 迪威智能 x Master Concept 線上合作會議（2026-03-26）

---

## 測試環境

| 項目 | 值 |
|------|-----|
| SDK | google-genai 1.68.0 |
| 模型（長曲） | lyria-3-pro-preview（最長 184 秒） |
| 模型（短 clip） | lyria-3-clip-preview（30 秒） |
| Location | global |
| 輸出格式 | MP3（44.1kHz / 192kbps） |

---

## 測試結果總覽

| 測試項目 | 結果 | 客戶痛點是否解決 |
|----------|------|-----------------|
| BPM 精準度 | 4/4 全部命中 | 是 |
| 批次生成重複性 | 4 次皆不同 | 是 |
| 圖片轉音樂（一般圖片） | 通過 | - |
| 圖片轉音樂（專輯封面含藝人名） | 被阻擋（版權過濾） | 需注意 |
| 兒童圖片 + 兒歌歌詞 | 2/3 通過 | 大致可用 |

---

## 測試 1：BPM 與樂理 Prompt 精準度

使用 `lyria-3-pro-preview` 生成，指定不同 BPM 與風格。

| 目標 BPM | 模型回報 BPM | 時長 | 品質分數 | 風格 |
|----------|-------------|------|---------|------|
| 120 | 120.0 | 160.0s | 4.5 | Progressive House / Big Room EDM |
| 85 | 85.0 | 158.2s | 4.5 | Lo-Fi Hip Hop |
| 140 | 140.0 | 150.8s | 4.5 | Dark Trap |
| 100 | 100.0 | 156.0s | 4.5 | Acoustic Folk Pop |

**結論：** Lyria 3 對 BPM 的遵循度極高，4 組全部精準命中目標值。風格描述也與 Prompt 高度吻合。

---

## 測試 2：批次生成重複性

使用同一 Prompt 連續呼叫 4 次（Lyria 3 無 seed 參數）。

| 次數 | 模型自選 BPM | 時長 | 檔案大小 |
|------|-------------|------|---------|
| 第 1 次 | 120 | 160.0s | 3,562,265 bytes |
| 第 2 次 | 100 | 156.0s | 3,600,508 bytes |
| 第 3 次 | 100 | 153.6s | 3,520,887 bytes |
| 第 4 次 | 120 | 160.0s | 3,658,813 bytes |

**結論：** 客戶最大痛點已解決。4 次生成的檔案大小皆不同、BPM 與時長也有變化、歌詞結構各異。不再出現 Lyria 2「4 首一模一樣」的問題，無需 seed 參數即可確保隨機性。

---

## 測試 3：圖片轉音樂 + Safety Filter

使用 `lyria-3-clip-preview` 測試不同類型圖片。

| 圖片 | 內容描述 | 結果 | 說明 |
|------|---------|------|------|
| image-test.jpg | 嬰兒照片 | OK | 兒童圖片本身不會觸發 Safety Filter |
| image1.jpg | 一般風景 | OK | 正常生成 |
| image2.jpeg | 專輯封面（含歌手名 Joker242 / JACKSON） | BLOCKED | 觸發版權過濾（藝人名稱），非兒童安全過濾 |

**結論：** Safety Filter 主要針對版權（藝人名稱、特定歌手風格）進行阻擋，兒童圖片本身不受影響。含有藝人名稱的圖片會被視為版權侵權而直接阻擋。

---

## 測試 4：兒童圖片 + 兒歌歌詞組合

使用嬰兒照片（image-test.jpg）搭配中英文兒歌歌詞。

| 兒歌 | 語言 | 結果 | 說明 |
|------|------|------|------|
| Twinkle Twinkle Little Star | 英文 | FAIL (500) | Internal server error，可能為版權偵測誤判或暫時性錯誤 |
| 兩隻老虎 | 中文 | OK | 成功生成，歌詞完整還原 |
| 小星星 | 中文 | OK | 成功生成，鋼琴搖籃曲風格 |

**結論：** 中文兒歌 + 嬰兒圖片組合完全沒有問題。英文 Twinkle Twinkle Little Star 回傳 500 錯誤，不確定是版權偵測（該曲旋律雖已公版但歌詞可能觸發 recitation check）還是暫時性 API 錯誤，建議重試確認。

---

## 重要 API 差異：Lyria 3 vs Lyria 2

| 功能 | Lyria 3 | Lyria 2 |
|------|---------|---------|
| API 端點 | Interactions API（v1beta1） | Predict API（v1） |
| 最長時長 | 184 秒（Pro）/ 30 秒（Clip） | 30 秒 |
| 輸出格式 | MP3 | WAV |
| seed 參數 | 不支援 | 支援 |
| negative_prompt | 不支援 | 支援 |
| sample_count | 不支援 | 支援 |
| safety_settings | 不可調整（固定） | 不可調整（固定） |
| 圖片輸入 | 支援 | 不支援 |
| 人聲/歌詞 | 支援 | 不支援 |
| Location | 必須為 global | us-central1 等 |
| Rate Limit | 10 QPM per model | 依專案 quota |

---

## 客戶痛點回應摘要

### 1. 生成重複問題
**已解決。** Lyria 3 預設隨機性足夠，同一 Prompt 連續 4 次都產出不同音樂。雖然 Lyria 3 移除了 seed 參數（無法做可重現生成），但重複問題不再發生。

### 2. Safety Filter 過嚴
**部分改善。** 兒童圖片和中文兒歌歌詞不會被阻擋。但版權過濾仍然嚴格——圖片中出現藝人名稱會被直接阻擋，且 Safety Filter 強度無法透過 API 調整。建議客戶在產品端做前置過濾，避免使用者上傳含版權資訊的圖片。

### 3. BPM 控制精準度
**完美。** 4 組不同 BPM 全部精準命中，可放心用於商業生產。

---

## 後續建議

1. **重試 Twinkle Twinkle Little Star** — 確認 500 錯誤是暫時性還是版權偵測
2. **測試更多版權邊界案例** — 如公版古典樂曲名（Fur Elise、Canon in D）是否被阻擋
3. **申請 Vertex AI Quota 提升** — 目前 10 QPM 對批次生產可能不足
4. **確認 WAV 格式支援時程** — 目前僅 MP3，專業後製可能需要無損格式
5. **評估 Lyria 2 seed 參數的替代方案** — 若客戶需要可重現生成，目前 Lyria 3 無法做到

---

## 執行方式

```bash
# 安裝環境
uv sync

# 設定環境變數
cp .env.example .env
# 編輯 .env 填入 PROJECT_ID

# 執行全部測試
uv run test_lyria3.py

# 單獨執行特定測試
uv run test_lyria3.py --test bpm      # BPM 精準度
uv run test_lyria3.py --test dup      # 重複性
uv run test_lyria3.py --test img      # 圖片轉音樂
uv run test_lyria3.py --test nursery  # 兒歌 + 兒童圖片

# Lyria 2 seed 對照測試
uv run test_lyria2_seed.py
```
