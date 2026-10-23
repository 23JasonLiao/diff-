# 可直接貼上的 Claude Code 提示詞（中文版）

> 這是 `docs/PROMPTS.md` 的中文版。Claude 看得懂中文，可以直接複製貼上。
> 每段都附上「什麼時候用」「你要準備什麼」「做完要檢查什麼」。
> **一次只做一個里程碑**，做完一段先 `/clear` 開新對話，再做下一段。

---

## 1. 初次全專案審視（不改任何檔案）

**時機**：第一次進專案，或隔一段時間回來時。
**模式**：先按 `Shift+Tab` 切到 Plan mode（或用 `/plan`）。

```
/plan 請閱讀 CLAUDE.md、specs/PRD.md、specs/ARCHITECTURE.md、specs/CACHE_CONTRACT.md、specs/PHYSICAL_MAPPING.md 和 specs/ACCEPTANCE.md。檢查目前的測試和 data/demo。請提出一條從這個合成資料的 CPU demo 走到真實 Taiwan EDM cache 的「最小且安全」路線圖。不要修改任何檔案，不要產生任何科學結論，也不要重新實作我的 EDM。
```

**做完檢查**：
- 它有沒有把假資料說成真結果？
- 路線圖是不是「一次一小步」？有沒有跳過 golden test 直接要跑大量 GPU？

---

## 2. 真實模型稽核（唯讀）

**時機**：Phase 3 開始，你已經把模型「原始碼」放進一個安全的工作區（**只放程式碼和 checkpoint 的說明文字，不要放 .pt 二進位檔**）。
**你要準備**：`Network.py`、訓練腳本、推論腳本、資料前處理程式、checkpoint 的 metadata（路徑、SHA256、訓練設定）。

```
請使用 edm-integrator 作為唯讀、獨立的 agent。檢查我真實的 Network、TrainDiffusion、Inference、資料前處理程式和 checkpoint metadata。產出一份以原始碼為依據的報告，內容包含：tensor shape、正規化方式、seed 設定、取樣步驟（sampling steps），每一項都要附上 file:line 引用。如果缺少必要的檔案，請明確寫出缺的是哪一個。不要修改模型。請把報告寫進 specs/EDM_AUDIT.md。
```

**做完檢查**（只有你或指導教授能確認）：
- condition channel 順序、`[B,7,112,72]`、residual `[B,1,112,72]` 是否正確
- residual 的 z-score 和 log1p 反轉流程
- 40 個 sigma levels 對應的是哪些 denoiser 呼叫（Heun 的 predictor/corrector 怎麼算）
- 每個 member 的 seed 怎麼產生、有沒有 stochastic churn（每步額外的雜訊）

---

## 3. 凍結數值的 Golden tests

**時機**：稽核報告你確認無誤之後。

```
/implement-spec 撰寫測試：一個 no-op 擾動（擾動量為 0）必須完全重現 baseline 的 seed、降雨的數值單位轉換（mm/day）、樣本排列 [M,H,W]，以及每個 step 的 denoised estimate。先只用 1 個真實 case、2 個 seed，並與現有推論程式的輸出比對。請 scientific-reviewer 審查；不要開始整批預先計算。
```

**做完檢查**：
- no-op 結果與原推論「完全相同」或在明確寫出的容許誤差內
- 測試真的有呼叫你原本的推論程式，而不是 Claude 自己寫的仿製版

---

## 4. GPU 離線 adapter

**時機**：golden tests 通過、審查完成之後。

```
/implement-spec 只有在 golden tests 和審查都完成後，才實作離線 GPU adapter。保留訓練好的權重和既有的推論演算法。只支援 1 個 case、1 組 q700 / north / +0.5σ 擾動，baseline 與擾動使用成對（相同）的 seed；輸出帶版本的 metadata 和小型 cache。為 H200 提供執行用的 CLI，checkpoint 和資料路徑一律用命令列參數傳入，不要寫死成常數。不要修改 backend/ 和 frontend/。完成後跑測試並回報。
```

**做完檢查**：
- 程式放在 `offline/`，沒有碰 `backend/`、`frontend/`
- 路徑全部是參數
- 輸出的 metadata 有 checkpoint SHA256、seed 清單、sampler 設定、單位、`data_status`

> 這一步的程式由 **你** 拿到 H200 上跑，Claude 不會也不應該在本機跑 GPU。

---

## 5. Cache 驗證

**時機**：GPU 跑完、產出 cache 之後。

```
/edm-cache-audit 驗證真實 checkpoint 的 SHA256、資料日期、正規化統計值、每一組成對的 seed 與雜訊序列、solver/sigma 的呼叫語意、30 個 member 的數量，以及物理單位。只有在所有來源資訊（provenance）和驗收檢查都通過時，才把 cache 標記為 actual（data_status = actual_edm）。
```

**做完檢查**：每一項都有「通過／不通過」和證據，不是只寫「看起來沒問題」。

---

## 6. 擴充 CPU 端 XAI（現在就能做）

**時機**：任何時候都可以，用假資料練習。

```
/implement-spec 建立 member-response 散佈圖與變異數分解的 UI，以及對應的測試。先閱讀科學指標相關的 spec；backend 不准使用 torch。使用 2018-01-12 的 demo 資料，但每一個結果都要標示為 synthetic（合成資料）。要包含 cache 缺漏時的錯誤畫面。
```

**做完檢查**：
- 散佈圖的 x 軸是 baseline 的 member 值 `B_m`、y 軸是 response `delta_m`（或 `P_m`），而且是「同一個 seed」配對
- 畫面上仍有 SYNTHETIC 警告

---

## 7. 物理概念與 cohort

**時機**：第 6 段完成之後。

```
/implement-spec 新增「物理概念選擇器」，並寫明每個概念的物理假設；cohort 子群必須依據「擾動前」的 metadata 來決定；提供每個 case 的效果統計、IQR 和方向一致性。cache 中沒有的輸入擾動一律拒絕，不要宣稱任何因果機制。
```

**做完檢查**：
- cohort 不是用「擾動後」的結果來挑選的（避免 post-treatment leakage）
- cohort 統計是「每個 case 的效果」取中位數／IQR，不是把所有 member 混在一起

---

## 8. 每次合併前的唯讀把關

**時機**：每個功能完成、準備 commit / merge 前。

```
請 scientific-reviewer 和 qa-reviewer 各自獨立、以唯讀方式審查，回報 P0 和 P1 等級的問題。只修正「經過確認為真」的問題；跑 backend 的 pytest、前端 build，以及一次端到端的 API demo。請總結確切的通過／失敗證據。不要做大型、無關的重構。
```

---

## 附錄：本指南額外建議的練習題（非原檔內容）

這些對應 `docs/GUIDE_zh-TW.md` 第 7 節「階段 A」，適合在還沒有真模型時練習流程。

**A2 補上缺少的 P0 測試**
```
/implement-spec 補上 specs/ACCEPTANCE.md P0 中「affine scale > 1 會使 SD 與 sample variance 依預期增加」的測試。只修改 backend/tests，不要改 metrics.py 的公式。
```

**A4 前端選單改由 API 提供**
```
/implement-spec 讓 frontend 的 variable、input_roi、magnitude、cohort 選單改從 /api/options 讀取，並對 query 參數做 URL encode；cache miss 時要顯示 API 回傳的 detail 訊息。只修改 frontend/。
```

**修補 hook 對 PowerShell 的防護**
```
請在 .claude/hooks/guard_commands.py 加一條規則，擋下 PowerShell 的 Remove-Item 同時帶 -Recurse 和 -Force 的指令（參數順序不限）。附上一個小測試或手動驗證方式，不要改其他規則。
```

---

## 寫自己的 prompt 時的模板

```
/implement-spec <一句話描述功能>
依據：specs/<檔名>.md 的 <章節>
範圍：只改 <目錄或檔案>
禁止：<不准碰的東西，例如 metrics.py 公式、frontend>
驗收：<哪條 ACCEPTANCE 或你新增的條件>
回報：改了哪些檔案、pytest 完整輸出、已知限制
```
