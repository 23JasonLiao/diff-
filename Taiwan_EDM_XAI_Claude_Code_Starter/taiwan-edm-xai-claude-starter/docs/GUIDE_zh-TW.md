# 使用指南：如何用這些 md 檔 + Claude Code 完成 Taiwan EDM XAI 專案

> 給專案負責人（你）看的操作手冊。Claude Code 不需要讀這份；它讀的是 `CLAUDE.md` 和 `specs/`。

---

## 0. 一句話看懂這個專案

做一個**只用 CPU** 的互動式視覺分析／XAI 系統：
在 GPU 上**事先算好**「同一組 seed 的 baseline vs. 擾動後」兩組 30-member 降雨 ensemble，
CPU 端（FastAPI + React）只負責**讀 cache、算統計、畫圖**，回答：

> 「把某個輸入物理量（例如北部 q700 +0.5σ）調一下，輸出區域（例如東北部）的降雨分佈，尤其是 **spread（離散度）**，怎麼變？這個效果在整個 cohort（例如冬季個案）裡穩不穩定？」

### 目前進度（2026-10 實測）

| 項目 | 狀態 |
|---|---|
| Phase 0–2：規格、CPU 指標、FastAPI、React demo | ✅ 完成，`pytest` 9/9 通過 |
| 資料 | ⚠️ 全是 `scripts/generate_demo_cache.py` 產生的**合成假資料**（12×10 網格、5 步、3 層） |
| Phase 3+：接上你真正的 EDM 模型、GPU 預算 cache | ❌ 尚未開始，**需要你提供**模型原始碼、checkpoint、資料前處理、正規化統計 |

---

## 1. 專案地圖

```
taiwan-edm-xai-claude-starter/
├── CLAUDE.md                 ← Claude 每次啟動自動讀：專案「憲法」（不可違反的規則）
├── README.md                 ← 人類看的快速開始
├── specs/                    ← 科學與工程「規格書」，唯一真相來源 (source of truth)
│   ├── PRD.md                  要解決什麼科學問題、名詞定義、非目標
│   ├── CACHE_CONTRACT.md       tensor 維度、cache key、公式定義
│   ├── ARCHITECTURE.md         GPU 離線 / CPU 線上 的邊界
│   ├── PHYSICAL_MAPPING.md     q700/u/v/t2m/msl/tp 的物理意義、cohort 選法
│   └── ACCEPTANCE.md           P0/P1/P2 驗收測試清單
├── docs/
│   ├── PLAN.md                 里程碑勾選清單（Claude 做完要更新）
│   ├── PROMPTS.md              ★ 每個階段可直接貼給 Claude 的提示詞
│   ├── CLI_CHEATSHEET.md       Claude Code 指令速查
│   ├── GUIDE_zh-TW.md          本檔
│   ├── PROMPTS_zh-TW.md        PROMPTS.md 中文版（附檢查重點）
│   ├── CODE_WALKTHROUGH_zh-TW.md  逐檔程式碼導讀
│   └── REVIEW_PROTOCOL_zh-TW.md   如何確保 code review 嚴謹
├── .claude/
│   ├── settings.json           權限 + hooks 設定
│   ├── agents/*.md             5 個 subagent（角色）
│   ├── skills/*/SKILL.md       3 個 slash command 技能
│   └── hooks/*.py              自動防呆腳本
├── backend/app/              ← CPU 端：metrics.py(數學) store.py(讀 cache) main.py(API)
├── backend/tests/            ← pytest
├── frontend/                 ← React + Vite 單頁
├── scripts/generate_demo_cache.py  ← 產生假資料
├── data/demo/                ← 假資料（manifest.json + .npz）
└── offline/README.md         ← 未來 GPU adapter 的施工說明（目前沒有程式碼）
```

---

## 2. 每個 md 檔是給誰、什麼時候用

這是最重要的一節。這個專案的設計是：**md 檔 = 你給 coding agent 的「規格 + 規則 + 角色 + 流程」**，agent 照著寫程式。

| 檔案 | 誰讀 | 何時被讀 | 你要做什麼 |
|---|---|---|---|
| `CLAUDE.md` | Claude（自動） | 每次啟動 session 都會載入 | 很少改。只有「新增不可違反的規則」時才改。它告訴 Claude：先讀 specs、絕不在 backend 跑 GPU、不可把假資料說成真的… |
| `specs/*.md` | Claude（CLAUDE.md 要求它讀）+ 你 | 每次改程式前 | **你的主要控制桿**。要改功能／公式／API → **先改 spec，再叫 Claude 照 spec 改 code**。 |
| `specs/ACCEPTANCE.md` | Claude + 你 | 寫測試時 | 新功能要先在這裡加一條驗收條件，Claude 會把它變成 pytest。 |
| `docs/PLAN.md` | Claude + 你 | 每個里程碑結束 | 看進度；Claude 完成後會勾選並記錄決策。 |
| `docs/PROMPTS.md` | **你** | 每開始一個階段 | 複製對應段落貼進 Claude Code。 |
| `docs/CLI_CHEATSHEET.md` | 你 | 忘記指令時 | 查指令。 |
| `offline/README.md` | Claude + 你 | Phase 3–4 | 接真模型時的施工順序。 |
| `.claude/agents/*.md` | Claude | 被指派時 | 定義「角色」。多數是**唯讀審查員**，不會改檔。 |
| `.claude/skills/*/SKILL.md` | Claude | 你打 `/技能名` 時 | 定義「固定流程」。 |

### 2.1 五個 Agent（角色）

| Agent | 可否改檔 | 用途 | 怎麼叫 |
|---|---|---|---|
| `architect` | ❌ 唯讀 | 大改動前出設計、檔案層級計畫 | 「請用 architect agent 規劃 …」 |
| `edm-integrator` | ❌ 唯讀 | 讀你的真 EDM 程式碼，整理 shape / seed / sigma / hook 位置 | Phase 3 第一步 |
| `scientific-reviewer` | ❌ 唯讀 | 審數學：ddof、W1、變異數分解、cohort 不可攤平 | 改到 `metrics.py` 後必叫 |
| `qa-reviewer` | ❌ 唯讀 | 審工程：CPU 邊界、cache 路徑安全、錯誤處理 | 改 API / cache 後必叫 |
| `frontend-developer` | ✅ 只能改 `frontend/` | 做 UI | 「請用 frontend-developer agent 做 …」 |

> 設計理念：**一個人寫、多個人獨立審**。審查員是唯讀的，所以不會「自己審自己改」而掩蓋錯誤。

### 2.2 三個 Skill（slash command）

| 指令 | 做什麼 |
|---|---|
| `/implement-spec <功能描述>` | 標準開發流程：讀 spec → 找驗收測試 → 寫計畫 → **先寫會失敗的測試** → 實作一個垂直切片 → 跑 pytest/build → 叫 reviewer → 更新 PLAN.md |
| `/scientific-review` | 對目前的數學實作做一次科學審查清單 |
| `/edm-cache-audit` | 接真模型 / 驗證 GPU cache 時使用；沒有真檔案時它會列出缺什麼而不是亂猜 |

### 2.3 Hooks（自動防呆，你不用手動觸發）

- `guard_commands.py`：Claude 執行指令前，擋掉 `rm -rf`、`git reset --hard`、`git push --force`、`git clean -f`、`--dangerously-skip-permissions`。
- `check_edited_python.py`：Claude 改完 `.py` 後自動檢查語法。
- `settings.json` 也禁止 Claude 讀 `.env`。

---

## 3. 你必須懂的 6 個科學觀念（用來「審」Agent）

Agent 最容易在這裡出錯；你要能一眼看出來。

1. **Member = 一張完整降雨圖**（一個 seed 跑出來的）。Ensemble = 30 張。
2. **先空間平均、再算 spread**：每個 member 在 Output ROI 內取平均 → 得到 30 個數字 → 再算 SD。
   ❌ 錯誤：把「像素 × member」全部攤平算變異數，說那是 ensemble spread。
3. **Paired seed**：baseline 和 perturbed 必須用**同樣的 30 個 seed、同樣的雜訊**，`delta_m = P_m − B_m` 才有意義。
4. **W1（Wasserstein-1）**：兩組各自**排序**後逐一相減取絕對值平均——不是用 seed 配對相減。
5. **變異數分解（恆等式）**：`Var(P) − Var(B) = Var(delta) + 2·Cov(B, delta)`（全部 ddof=1）。它說明 spread 怎麼「數值上」變了，**不代表**物理因果。
6. **Cohort 統計取「每個 case 的效果」的中位數 / IQR**，不可以把 case × member 全部混在一起。

另外：q700、u/v 等擾動結果只能叫「模型對輸入的敏感度 / 物理假說」，**不能說是大氣因果**。

這些都已經寫在 `backend/app/metrics.py` 和 `backend/tests/test_metrics.py`，可以對照看。

---

## 4. 第一次啟動（Windows PowerShell）

```powershell
cd "C:\Users\user\Downloads\新增資料夾 (20)\Taiwan_EDM_XAI_Claude_Code_Starter\taiwan-edm-xai-claude-starter"

# 後端（你的環境已有 Python 3.13 + 套件，可略過 venv；建議仍用 venv 隔離）
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r backend/requirements.txt
python scripts/generate_demo_cache.py
python -m pytest backend/tests -q            # 應看到 9 passed
python -m uvicorn app.main:app --app-dir backend --reload --host 127.0.0.1 --port 8000
```

另開一個終端機：

```powershell
cd frontend
npm install
npm run dev        # 開 http://localhost:5173
```

API 文件：`http://127.0.0.1:8000/docs`。看到紅色 SYNTHETIC 警告是正常的。

---

## 5. 啟動 Claude Code 的正確方式

```powershell
cd "...\taiwan-edm-xai-claude-starter"   # ★ 一定要在這一層，不是外層資料夾
claude
```

為什麼：`CLAUDE.md`、`.claude/agents`、`.claude/skills`、hooks 都放在這一層。若在外層啟動，Claude 看不到這些設定，等於沒有規則。

進去後先確認：
- `/agents` → 應看到 5 個 agent
- `/skills`（或打 `/` 看清單）→ 應看到 `implement-spec`、`scientific-review`、`edm-cache-audit`
- `/hooks` → 應看到 PreToolUse / PostToolUse

---

## 6. 標準工作循環（每個里程碑都照這個做）

```
① /clear                          開新對話，避免舊上下文干擾
② 進入 Plan mode（Shift+Tab 切換，或 /plan）
   貼 docs/PROMPTS.md 對應段落 → Claude 只讀不改，給你計畫
③ 你審計畫：有沒有違反 §3 的觀念？範圍會不會太大？
   不對就直接回覆修正，例如「只做 case 模式，cohort 下一輪」
④ 離開 Plan mode → /implement-spec <功能>
⑤ Claude 寫測試 → 實作 → 跑 pytest
⑥ 要求：「請 scientific-reviewer 和 qa-reviewer 各自獨立、唯讀審查，回報 P0/P1 問題」
⑦ 只修「確認為真」的問題
⑧ /diff 自己看一次改動 → 自己再跑一次 pytest
⑨ 確認 docs/PLAN.md 有更新 → git commit
```

### 寫 prompt 的 5 個原則

1. **一次一個垂直切片**（spec → 測試 → backend → frontend），不要「幫我把整個系統做完」。
2. **指出依據**：「依照 `specs/CACHE_CONTRACT.md` 的 Calculation contracts …」
3. **寫出禁止事項**：「不要改 metrics.py 的公式」「不要碰 frontend」。
4. **要求證據**：「回報 pytest 完整輸出」「列出改了哪些檔案」。
5. **要改定義 → 先改 spec**：「先更新 `specs/ACCEPTANCE.md` 加一條 …，給我看，我同意後再寫 code」。

---

## 7. 路線圖：從現在到完成

### 階段 A — 還沒有真模型時（現在就能做，用來練習流程）

| 任務 | 貼給 Claude 的 prompt |
|---|---|
| A1 全專案審視 | `docs/PROMPTS.md` →「Initial no-edit architecture pass」 |
| A2 補缺的 P0 測試 | `/implement-spec 補上 specs/ACCEPTANCE.md P0 中「affine scale >1 會增加 SD 與 variance」的測試；只改 backend/tests，不改公式` |
| A3 member-response 散佈圖 | `docs/PROMPTS.md` →「Expand CPU XAI」 |
| A4 前端選單接 API | `/implement-spec 讓 frontend 的 variable/input_roi/magnitude/cohort 選單改從 /api/options 讀取並對參數做 URL encode；cache miss 要顯示 API 回傳的 detail` |
| A5 物理概念選擇器與 cohort 子群 | `docs/PROMPTS.md` →「Physical mapping and cohort」 |

每個任務結束都跑 §6 的 ⑥–⑨。

### 階段 B — Phase 3：接上你的真實 EDM（需要你準備檔案）

**你要先準備**（放在專案外或 `data/actual/`、`checkpoints/`，這兩個已被 `.gitignore` 排除）：
- `Network.py`、訓練腳本、推論腳本、資料前處理程式
- checkpoint（只要路徑與 metadata，**不要**把 .pt 給 Claude 讀或 commit）
- 正規化統計（mean/std）、channel 順序、sampler 設定（Heun/Euler、40 levels、churn 設定）

**步驟：**
1. **B1 唯讀稽核**：`docs/PROMPTS.md` →「Actual model audit」。產出一份有 `file:line` 引用的 shape / normalization / seed / step 報告。**請它把報告寫進 `specs/EDM_AUDIT.md`**，之後當 spec 用。
2. **你審報告**：channel 順序、`[B,7,112,72]`、residual、log1p 反轉、40 個 sigma 的位置是否正確——這只有你（或指導教授）能確認。
3. **B2 Golden tests**：`docs/PROMPTS.md` →「Frozen numerical golden tests」。1 個 case、2 個 seed、no-op 擾動必須和原推論**完全相同**。
4. 依結果更新 `specs/CACHE_CONTRACT.md`「For actual 8-km Taiwan EDM」一節。

### 階段 C — Phase 4：GPU 離線 cache

1. **C1**：`docs/PROMPTS.md` →「GPU offline adapter」。只做 1 case × q700 × north × +0.5σ。路徑一律用 CLI 參數。
2. 在 H200 上自己跑（Claude 不會也不該在本機跑 GPU）。
3. **C2**：`/edm-cache-audit`（「Cache validation」段落）。全部通過才把 `data_status` 標成 `actual_edm`。
4. 用 `XAI_CACHE_ROOT` 環境變數讓 backend 改讀真 cache：
   ```powershell
   $env:XAI_CACHE_ROOT = "D:\path\to\actual_cache"
   python -m uvicorn app.main:app --app-dir backend --port 8000
   ```
   （`store.py` 目前讀 `.npz`；若改 Zarr，用 `/implement-spec` 換實作但保留 API 形狀與驗證。）
5. 擴到 `offline/README.md` 的 pilot：12 cases × 2 變數 × 2 幅度 × 3 區域 = 144 組。**先估算儲存量**（ARCHITECTURE.md 有公式）。

### 階段 D — Phase 5–6
- 真實 step sigma / 真實 layer hook（`edm-integrator` 先規劃 → `/implement-spec`）。
- 正式地圖（真實經緯度）、cohort 子群、使用性評估。
- 每次合併前：`docs/PROMPTS.md` →「Read-only gate before each merge」。

---

## 8. 如何擴充這套 md 系統

- **新功能**：先在 `specs/PRD.md`（要什麼）＋`specs/ACCEPTANCE.md`（怎麼算完成）加條目，再 `/implement-spec`。
- **新規則**（Claude 一直犯同一個錯）：加到 `CLAUDE.md` 的 Invariants，一行一條，用 MUST / Never。
- **新角色**：在 `.claude/agents/` 新增 md，格式照抄現有的（frontmatter：`name`、`description`、`tools`、`model`）。審查類一律只給 `Read, Grep, Glob`。
- **新流程**：在 `.claude/skills/<名稱>/SKILL.md` 新增，用 `$ARGUMENTS` 接參數，之後可用 `/<名稱>` 呼叫。
- 改完 md 後 `/clear` 重開，讓新規則生效。

---

## 9. 我讀完專案後發現的注意事項

| # | 問題 | 建議 |
|---|---|---|
| 1 | Git 根目錄是 `C:\Users\user\Downloads\新增資料夾 (20)`（外面兩層），不是本專案資料夾 | 建議在 `taiwan-edm-xai-claude-starter` 內重新 `git init`，避免把 Downloads 其他檔案納入版控 |
| 2 | `ACCEPTANCE.md` P0 的「affine scale >1」測試尚未實作 | 階段 A2 |
| 3 | `guard_commands.py` 只擋 bash 寫法；PowerShell 的 `Remove-Item -Recurse -Force` 不會被擋 | 在 patterns 加 `(r"Remove-Item\b.*-Recurse.*-Force\|Remove-Item\b.*-Force.*-Recurse", ...)`；且它本來就不是安全邊界，權限提示仍要自己看 |
| 4 | 前端把 `q700 / north / 0.5 / winter` 寫死，query string 沒 URL encode | 階段 A4 |
| 5 | pytest 有 Starlette 的 httpx deprecation warning | 無害，可忽略 |
| 6 | hooks 用 `python` 指令 | 確保 Claude Code 啟動時 `python` 在 PATH（你的 Anaconda 目前可用） |
| 7 | 所有數字都是假資料 | 寫論文 / 報告前務必確認 `data_status == actual_edm` |

---

## 10. 常見問題

**Q：Claude 說「我幫你寫好 EDM adapter 了」，但我還沒給它模型檔？**
A：這違反 `offline/README.md`。拒絕並 `/clear`。它不能憑空捏造模型。

**Q：Claude 想改 `metrics.py` 的公式？**
A：先問它「這個改動在哪個 spec 有依據？」，並要求 `scientific-reviewer` 審。沒有你同意不准改科學定義。

**Q：對話太長、Claude 開始忘記規則？**
A：`/compact` 或直接 `/clear` 開新對話；規則在 `CLAUDE.md` 會自動重新載入。

**Q：可以開 `--dangerously-skip-permissions` 讓它跑快一點嗎？**
A：不行。資料和 checkpoint 很貴，hook 也會擋。

**Q：可以同時開多個 Claude 一起寫？**
A：可以，但**同一組檔案只能有一個在寫**（例如一個寫 backend、一個寫 frontend），其他只做唯讀審查。
