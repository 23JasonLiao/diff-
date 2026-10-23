# 程式碼導讀（中文）

> 逐檔說明這個專案「現在」的程式碼在做什麼、資料怎麼流動、每個函式的數學意義。
> 搭配 `docs/GUIDE_zh-TW.md`（怎麼用）和 `docs/PROMPTS_zh-TW.md`（要貼什麼）一起看。

---

## 1. 全貌：資料怎麼流動

```
scripts/generate_demo_cache.py        （一次性，產生假資料）
        │ 寫出
        ▼
data/demo/manifest.json               ← 有哪些 case、cohort、擾動組合、metadata
data/demo/roi_masks.npz               ← Output ROI 遮罩（northeast / north / all）
data/demo/cases/<日期>.npz             ← 每個 case 的 baseline / perturbed 陣列
        │ 讀取
        ▼
backend/app/store.py   CacheStore     ← 安全讀檔 + 檢查請求的組合是否存在
        │
        ▼
backend/app/metrics.py                ← 純 NumPy 統計：ROI 平均、spread、W1、變異數分解、cohort
        │
        ▼
backend/app/main.py    FastAPI        ← /health  /api/options  /api/case  /api/cohort
        │ HTTP JSON（Vite 代理 /api → 127.0.0.1:8000）
        ▼
frontend/src/main.jsx  React          ← 下拉選單、數字卡片、折線圖、熱圖、表格
```

重點：整條線**沒有任何模型推論**。未來真模型只會在最上面換掉「產生 cache 的那一步」（`offline/`），下面三層不變。

---

## 2. 假資料產生器：`scripts/generate_demo_cache.py`

目的：讓整套 UI/API 能端到端跑起來。**不是台灣地理、不是大氣資料、不是 EDM 輸出。**

| 內容 | 說明 |
|---|---|
| 網格 `H, W = 12, 10` | 真實模型是 112×72，這裡縮小 |
| ROI 遮罩（第 17–23 行） | `northeast` = 上半部右半、`north` = 上半部、`all` = 全部 |
| 4 個 case | `20171220, 20180103, 20180112, 20180204`，全歸入 cohort `winter` |
| `step_sigma` | 假的 5 個 sigma 標籤（真實應為 40 個） |

### 每個 case 怎麼造（第 27–43 行）

```python
shared   = rng.normal(0, 1, (30, 1, 1))       # 每個 member 一個「整體偏濕/偏乾」因子
baseline = 14 + 6*idx + 8*shared + 空間圖樣 + 雜訊  → clip(0)
response = 1.5 + (1.2 + 0.2*idx)*shared + 小雜訊   # 每個 member 的反應量
perturbed = baseline + response + 0.7*mask_ne     → clip(0)
```

這樣設計的效果（你可以用來驗證 UI 數字合理）：
- `response` 和 `shared` **正相關** → baseline 越濕的 member 反應越大 → `Cov(B, delta) > 0` → **spread 會變大**。
- 平均多 1.5，northeast 區再多 0.7 → **mean 會上升**，而且選 `northeast` ROI 時上升較多。
- `idx` 越大反應係數越大 → 4 個 case 效果不同，cohort 才有 IQR 可看。
- `bsteps / psteps`：把最終圖按比例縮放成 5 張「假中間步驟」，差異隨步驟增加。
- `bvec / pvec`：3 層 × 5 步 × 30 member × 16 維的隨機向量，擾動量隨步驟從 0.02 增到 0.5。

### 輸出檔案格式

| 陣列名 | shape | 意義 |
|---|---|---|
| `baseline_final` / `perturbed_final` | `[30, 12, 10]` | 30 個 member 的最終降雨圖 |
| `baseline_steps` / `perturbed_steps` | `[5, 30, 12, 10]` | 每個步驟的 denoised 降雨估計 |
| `baseline_vectors` / `perturbed_vectors` | `[3, 5, 30, 16]` | [layer, step, member, 特徵維度] |

`manifest.json` 記錄 `data_status: "synthetic_demo"`、警告文字、case 清單、cohort、**唯一可用的擾動組合** `q700 / north / 0.5`，以及 metadata（seeds 0–29、單位、layer 名稱、step sigma）。

---

## 3. 讀 cache：`backend/app/store.py`

### `class CacheMiss(LookupError)`（第 17 行）
自訂例外。代表「你要的組合沒有預先算過」。API 會把它轉成 **HTTP 404**。

### `class CacheStore`（第 21 行）

**`__init__(root=None)`**（第 22 行）
- cache 位置優先順序：參數 `root` → 環境變數 `XAI_CACHE_ROOT` → 預設 `data/demo/`。
  → 未來接真 cache 只要設 `XAI_CACHE_ROOT`，不用改程式。
- 找不到 `manifest.json` 就丟 `FileNotFoundError`（API 會回 503，提示你先跑產生器）。
- 讀入 manifest 和所有 ROI 遮罩（轉成 bool）。
- `np.load(..., allow_pickle=False)`：**安全措施**，避免載入惡意 pickle。

**`validate(case_id, roi, variable, input_roi, magnitude)`**（第 33 行）
依序檢查：case 存在？Output ROI 存在？擾動組合等於 manifest 中的那一組？任何一項不符就丟 `CacheMiss`，並附上「可用選項」。
→ 這就是 spec 規定的「cache miss 必須明確報錯、絕不內插」。

**`case_arrays(case_id)`**（第 43 行）
**只接受 manifest 白名單內的 case_id** 才組出檔名。所以 `case_id=../secret` 這種路徑穿越攻擊會被擋（`test_api.py` 有測）。

> 小提醒：目前 demo 只支援「一組」擾動（`self.combo`）。接真資料、有多組擾動時，`validate` 需要改成查表（cache key：case × variable × input_roi × magnitude × model_version × seed_set × sampler_spec，見 `CACHE_CONTRACT.md`）。

---

## 4. 科學核心：`backend/app/metrics.py`

這是整個專案最重要的檔案。所有輸入都是 **物理單位（mm/day）**。

### `roi_member_values(maps, roi_mask)`（第 11 行）
```
maps [M, H, W]  +  mask [H, W]   →   [M]
```
對每個 member，只取 ROI 內的像素做**空間平均**，得到 30 個數字。
- 檢查：維度、遮罩不可全空（`Empty Output ROI`）、結果必須是有限數。
- **為什麼重要**：先平均再算 spread。若把像素和 member 全攤平，空間上的高低差會被誤當成 ensemble 的不確定性。

### `compare_ensemble(baseline, perturbed, threshold=40)`（第 25 行）
輸入兩組各 30 個 ROI 平均值（**依 seed 對齊**），輸出：

| 欄位 | 公式 | 意義 |
|---|---|---|
| `baseline_mean` / `perturbed_mean` | 平均 | |
| `delta_mean` | `mean(P − B)` | 平均降雨變化 |
| `baseline_sd` / `perturbed_sd` | `std(ddof=1)` | 樣本標準差 = spread |
| `delta_sd` | `sd(P) − sd(B)` | **spread 變化（主要研究指標）** |
| `w1` | `mean(|sort(B) − sort(P)|)` | 1D Wasserstein 距離：兩個「分佈」差多遠（**各自排序**，不是配對相減） |
| `*_tail_probability` | `mean(x > threshold)` | ROI 平均 > 40 mm/day 的比例 |
| `delta_variance` | `var(P) − var(B)` | 變異數變化 |
| `response_variance` | `var(delta)` | member 反應量本身的離散 |
| `baseline_response_cov2` | `2·cov(B, delta)` | baseline 與反應量的共變 |
| `member_responses` 等 | 原始 30 個值 | 給前端畫散佈圖 |

**內建自我檢查**：程式會驗證
`var(P) − var(B) == var(delta) + 2·cov(B, delta)`，不成立直接丟 `AssertionError`。
這是數學恆等式，不成立代表程式有 bug（例如 ddof 不一致）。

**怎麼解讀**：
- `delta_variance` 主要來自 `2cov` 項 → 「原本越濕的 member 反應越大」造成 spread 變大。
- 主要來自 `response_variance` → member 之間反應不一致造成 spread 變大。
- 這只是**數值上的拆解**，不是物理因果。

### `step_w1_curve(base_steps, pert_steps, mask)`（第 65 行）
```
[K, M, H, W] × 2   →   [K]
```
每一個步驟 k：各自做 ROI 平均 → 算 W1。得到「差異在生成過程的哪一步開始出現」的曲線。（輔助證據）

### `layer_step_distance(base_features, pert_features)`（第 77 行）
```
[L, K, M, D] × 2   →   [L, K]
```
每個 member 算 `‖P − B‖₂ / √D`，再對 member 取平均。
**注意**：這是「表徵差異」，**不是**重要性或因果，不同 layer 之間也未經校準、不能直接比大小。

### `cohort_aggregate(case_results)`（第 90 行）
輸入：每個 case 的 `analyze_case` 結果。輸出：
- `delta_mean`、`delta_sd`、`w1`、`delta_tail_probability` 各自的 **median / q25 / q75**（跨 case）
- `share_mean_increased` / `share_spread_increased`：有幾成 case 是增加的（方向一致性）
- `step_w1_median / q25 / q75`：每一步的跨 case 分位數

**關鍵**：統計單位是「case 的效果」，不是把 4×30 個 member 混在一起。

---

## 5. API：`backend/app/main.py`

- 建立 FastAPI app，CORS 只允許 `localhost:5173`（Vite 開發伺服器），只允許 GET。
- `store()`（第 14 行）：**每個請求重新建一次 `CacheStore`**（每次重讀 manifest 和遮罩）。demo 夠用；資料大了之後可改成啟動時載入一次。

| 端點 | 位置 | 做什麼 |
|---|---|---|
| `GET /health` | 第 21 行 | 回傳 `runtime: cpu-only, edm_inference: false` |
| `GET /api/options` | 第 26 行 | 回傳可選的 cases、cohorts、Output ROI、擾動組合、metadata、`data_status` |
| `GET /api/case` | 第 59 行 | 參數：`case_id, variable=q700, input_roi=north, magnitude=0.5, output_roi=northeast, threshold=40`；先 `validate`，再 `analyze_case` |
| `GET /api/cohort` | 第 76 行 | 參數同上但用 `cohort=winter`；先驗證 cohort 內**所有** case 都有 cache，才逐一分析並 `cohort_aggregate` |

### `analyze_case(s, case_id, output_roi, threshold)`（第 40 行）
把上面的函式串起來：
```
讀 npz → roi_member_values(baseline_final), roi_member_values(perturbed_final)
       → compare_ensemble         → metrics
       → step_w1_curve            → step_w1
       → layer_step_distance      → layer_step_distance
       + step_metadata、layer_ids、interpretation_note
```
`/api/case` 和 `/api/cohort` 共用這個函式，避免公式在兩處各寫一份。

錯誤碼：`CacheMiss` → 404；cache 不存在 → 503；`threshold < 0` → 422（FastAPI 自動驗證）。

---

## 6. 前端：`frontend/`

| 檔案 | 說明 |
|---|---|
| `package.json` | React 19 + Vite 7；`npm run dev / build / preview` |
| `vite.config.js` | 把 `/api`、`/health` 代理到 `127.0.0.1:8000` |
| `index.html` | 掛載點 `#root` |
| `src/style.css` | 單行壓縮的樣式 |
| `src/main.jsx` | 全部 UI 邏輯 |

### `src/main.jsx`
- `fmt`（第 5 行）：數字格式化，非數字顯示「—」。
- `MiniLine`（第 7 行）：手寫 SVG 折線圖，畫 step W1 曲線。
- `App`（第 14 行）：
  1. 啟動時打 `/api/options`，填入 case 和 Output ROI 下拉選單。
  2. 使用者選「Case / Cohort」模式、case、Output ROI，按按鈕 → `query()` 打 `/api/case` 或 `/api/cohort`。
  3. **Case 結果**：4 張卡片（ΔMean、ΔSpread、W1、tail 機率變化）、變異數分解那一行、step W1 折線、layer × step 熱圖（顏色深淺 = 距離）。
  4. **Cohort 結果**：4 張卡片（median ΔMean、median ΔSpread、mean/spread 增加的比例）、ΔSpread IQR、cohort step W1 中位數曲線、每個 case 的表格。
  5. 錯誤時顯示紅框（例如 cache miss 的 detail）。
  6. 頂端固定顯示 **SYNTHETIC DEMONSTRATION** 警告。

**目前限制**（可當練習題）：
- `variable=q700&input_roi=north&magnitude=0.5` 和 `cohort=winter` 寫死在程式中，下拉選單是 disabled。
- query string 沒有 `encodeURIComponent`。
- 還沒有 member 散佈圖、沒有地圖。
- 警告文字是寫死的，沒有依 API 回傳的 `data_status` 切換。

---

## 7. 測試：`backend/tests/`

`conftest.py`：把 `backend/` 加到 `sys.path`，讓測試能 `import app`。

### `test_metrics.py`（對應 ACCEPTANCE P0）
| 測試 | 驗證什麼 |
|---|---|
| `test_zero_perturbation_all_effects_zero` | B = P 時所有效果都是 0 |
| `test_constant_shift_preserves_spread_and_w1` | 每個 member 都 +7 → ΔMean=7、ΔSD=0、W1=7 |
| `test_variance_decomposition_with_heterogeneous_responses` | 變異數恆等式成立 |
| `test_spatial_heterogeneity_does_not_fake_member_spread` | 空間上有高低但每個 member 一樣 → spread = 0（證明沒有攤平像素） |
| `test_roi_empty_is_error` | 空 ROI 必須報錯 |
| `test_cohort_aggregates_case_effects_not_member_pooling` | cohort 用的是 case 效果的中位數，極端 case（−100）不會拖垮結果 |

**缺少**：ACCEPTANCE 中「affine scale > 1 會增加 SD 與 variance」的測試。

### `test_api.py`（對應 ACCEPTANCE P1）
- 所有回應都帶 `data_status = synthetic_demo`；case 有 30 member、5 步；cohort 有 4 個 case。
- cache miss：錯的 variable（`t2m`）→ 404 且訊息含 `not precomputed`；`../secret` → 404；錯的 ROI → 404。

### `test_cpu_boundary.py`
用 AST 掃描 `backend/app/*.py` 的所有 import，**不准出現** `torch`、`cupy`、`tensorflow`、`Network`、`TrainDiffusion`。這是「CPU-only」規則的自動化執行，不只是口頭約定。

跑法：
```powershell
python -m pytest backend/tests -q     # 目前 9 passed
```

---

## 8. Claude Code 設定也是「程式」：`.claude/`

| 檔案 | 作用 |
|---|---|
| `settings.json` | 禁止讀 `.env`；設定兩個 hook |
| `hooks/guard_commands.py` | 執行 Bash/PowerShell 前，用正規表達式擋危險指令，回傳 `permissionDecision: deny` |
| `hooks/check_edited_python.py` | 編輯 `.py` 後 `py_compile` 檢查語法，有錯就印警告（不會自動修改） |
| `agents/*.md` | 5 個 subagent，frontmatter 決定可用工具（審查員只有 Read/Grep/Glob） |
| `skills/*/SKILL.md` | 3 個 slash command 的步驟清單 |

詳細用法見 `docs/GUIDE_zh-TW.md` 第 2 節。

---

## 9. 未來會新增 / 修改的地方（對照路線圖）

| 階段 | 會動到的檔案 |
|---|---|
| Phase 3 稽核 | 新增 `specs/EDM_AUDIT.md`；`offline/` 開始有 golden test |
| Phase 4 GPU cache | 新增 `offline/adapters/*`；可能改 `store.py`（多組擾動查表、Zarr 讀取）；`manifest` 改為 `data_status: actual_edm` |
| Phase 5 真實 step/layer | 更新 `CACHE_CONTRACT.md`（40 步、真實 sigma、hook ID）；`step_metadata` 換成真值 |
| Phase 6 正式 UI | `frontend/` 加地圖、散佈圖、物理概念選擇器；`main.py` 可能加新端點（先改 spec） |

不應該變的：`metrics.py` 的數學定義（除非先改 spec 並經科學審查）、CPU-only 邊界、cache miss 必須報錯的原則。
