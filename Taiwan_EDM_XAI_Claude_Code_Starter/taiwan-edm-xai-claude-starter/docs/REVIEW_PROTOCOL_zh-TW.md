# Code Review 嚴謹性規範（中文）

> 目的：讓你**不用相信任何人（包括 Claude）說「沒問題」**，而是靠可重現的證據判斷程式是否正確。
> 搭配：`docs/GUIDE_zh-TW.md`（流程）、`docs/PROMPTS_zh-TW.md`（提示詞）、`docs/CODE_WALKTHROUGH_zh-TW.md`（程式碼）。

---

## 0. 核心原則

1. **審查員也會錯。** AI 審查員和寫程式的 AI 是同一類模型，會用同樣的方式誤解；而且它說錯的時候語氣跟說對的時候一樣篤定。
2. **嚴謹 = 證據，不是信心。** 每個「有問題」或「沒問題」都要附上可重跑的東西：失敗的測試、具體反例、`file:line`、數值比對。
3. **測試綠燈 ≠ 正確。** 綠燈只代表「沒有違反你寫下的檢查」。檢查寫得鬆，bug 一樣過得去（見第 2 節實測）。
4. **要測「測試本身」。** 故意把程式改壞，看測試抓不抓得到。抓不到 = 測試有洞。
5. **寫的人不審，審的人不改。** 寫和審要分開，審查員一律唯讀。

---

## 1. 五層防線

```
第 1 層  自動測試（pytest）           每次改動都跑；抓「已知」錯誤
第 2 層  突變測試（mutation check）   故意埋 bug，檢查第 1 層夠不夠強
第 3 層  參考實作交叉比對             用 scipy / 手算 / 原推論程式比對數值
第 4 層  獨立 AI 審查員（唯讀）        scientific-reviewer + qa-reviewer，各自獨立
第 5 層  你的人工最後關卡             /diff + 第 6 節的檢查清單 + 自己重跑測試
```

只靠任何一層都不夠。第 4 層最容易讓人「感覺」嚴謹，但沒有第 1–3 層撐著，它只是意見。

---

## 2. 實測：這個專案現在的測試有多強？

我（Claude）在暫存區複製了一份專案，對 `backend/app/metrics.py` 故意埋了 8 個**典型的科學錯誤**，然後跑現有的 9 個測試（**沒有動到你的專案檔**）。

| # | 故意埋的 bug | 科學上的後果 | 現有測試 |
|---|---|---|---|
| M1 | SD 用 `ddof=0` 而不是 `ddof=1` | spread 系統性偏小，違反 spec | ❌ **沒抓到** |
| M2 | W1 用配對相減，沒有先排序 | 把「分佈距離」算成「member 反應」 | ❌ **沒抓到** |
| M3 | ROI 平均忽略遮罩，整張圖平均 | 選什麼 Output ROI 結果都一樣 | ❌ **沒抓到** |
| M4 | tail 機率 `>` 改成 `>=` | 剛好等於門檻的值被算進去 | ❌ **沒抓到** |
| M5 | cohort 中位數改成平均數 | 一個極端 case 會拖垮整個 cohort | ✅ 抓到 |
| M6 | `delta_sd` 回傳的是變異數變化 | 單位變 (mm/day)²，數值完全不同 | ❌ **沒抓到** |
| M7 | layer 距離沒除以 √D | 不同維度的 layer 無法比較 | ❌ **沒抓到** |
| M8 | step W1 用配對相減 | 同 M2 | ❌ **沒抓到** |

**結果：8 個 bug 只抓到 1 個（1/8）。全部 9 個測試仍然綠燈。**

這不代表現在的程式是錯的：現在的程式是對的。它代表的是：**如果 Claude 之後改程式時不小心犯了這些錯，現有測試不會告訴你。** 這正是「review 不嚴謹」最常見的來源。

### 補強後

我寫了 8 個補強測試（附錄 B），在暫存區驗證過：
- 正確的程式：**17 passed**（原 9 + 新 8）
- 8 個 bug：**8/8 全部抓到**

這些測試也順便補上 `ACCEPTANCE.md` P0 缺的「affine scale > 1」那一條。
要放進專案，可以貼第 8 節的提示詞，或叫我直接加。

---

## 3. 第 2 層：突變測試怎麼用

附錄 A 是一支 `scripts/mutation_check.py`（我已經在暫存區實際跑過）：
- 把 `backend/` 和 `data/` 複製到暫存資料夾，**不會改到真正的原始碼**
- 逐一套用 8 個突變 → 跑 pytest → 回報 `killed`（抓到）或 `SURVIVED`（漏掉）
- 有任何突變存活就回傳 exit code 1

```powershell
python scripts/mutation_check.py
```

**什麼時候跑**：每次 `metrics.py` 或測試有改動後。
**怎麼擴充**：每發現一種新的錯誤類型（例如審查時抓到的真 bug），就在 `MUTANTS` 加一筆，確保以後同樣的錯不會再溜過。
**規則**：`SURVIVED` 一律視為 **P1**，要補測試。

---

## 4. 第 3 層：參考實作交叉比對

自己寫的公式要和「別人寫好、被廣泛驗證過」的實作比對：

| 本專案的值 | 參考 |
|---|---|
| `w1` | `scipy.stats.wasserstein_distance(b, p)`（你的環境有 scipy 1.16.3；正式加入時要寫進 `requirements.txt`） |
| `baseline_sd` | `np.std(x, ddof=1)` / `statistics.stdev(x)` |
| 變異數分解 | 程式內已有 `np.isclose` 自檢；測試再用隨機資料驗證 |
| ROI 平均 | 小陣列**手算**，寫死期望值 |
| 真 EDM（Phase 3+） | **你原本的推論程式**的輸出 = golden reference |

選用的進階做法：**property-based testing**（套件 `hypothesis`，你的環境目前沒裝）。它會自動產生上千組隨機輸入，檢查「恆等式永遠成立」「B=P 時所有效果 = 0」「平移不改變 SD」等性質。

---

## 5. 第 4 層：讓 AI 審查員真的嚴謹

### 5.1 獨立性：最重要
| 做法 | 原因 |
|---|---|
| 審查員用 **subagent**（`scientific-reviewer`、`qa-reviewer`），或在 `/clear` 後的新對話裡審 | 寫程式那個對話已經「相信」自己的設計，會替它辯護 |
| **只給它 diff 和 spec，不給作者的結論** | 「我確認變異數分解是對的，請幫我看一下」等於叫它附和你 |
| 兩個審查員**分別**跑，不互相看結果 | 避免第二個人只是同意第一個人 |
| 審查員**不准改檔**（現有 agent 已設定只有 Read/Grep/Glob） | 自己審自己改，錯誤會被悄悄蓋掉 |

### 5.2 要求證據格式
每一個 finding 必須包含：
```
嚴重度：P0 / P1 / P2
位置：file:line
問題：一句話
反例：具體輸入 → 錯誤輸出（或違反哪一條 spec）
證明方式：一個會失敗的測試，或可重跑的數值比對
```
**沒有反例或測試的 finding 一律視為「待驗證」，不能直接修。**

### 5.3 嚴重度定義（本專案）
| 等級 | 定義 | 例子 |
|---|---|---|
| **P0** | 科學結果錯誤，或違反 CLAUDE.md 不變式 | 像素×member 攤平、seed 不配對、backend 匯入 torch、假資料標成 actual |
| **P1** | 可能導致錯誤但目前沒觸發；測試有洞；安全問題 | 突變存活、cache 路徑沒白名單、缺錯誤處理 |
| **P2** | 可讀性、效能、風格 | 每個請求重讀 manifest |

規則：**P0 不修完不能 merge；P1 要修或記錄在 PLAN.md 並說明原因；P2 自行決定。**

### 5.4 對抗式審查：叫它「試著弄壞」
與其問「這段程式有沒有問題？」，不如問：
> 「請找出一組輸入，讓 `compare_ensemble` 回傳科學上錯誤的值。」

找得到 → 就是 bug；找不到又說明了理由 → 可信度才比較高。

### 5.5 處理 finding：先重現，再修
```
審查員回報 finding
   ↓
寫一個「會失敗」的測試重現它  ── 測試沒失敗？→ finding 是誤報，記下來，不修
   ↓ 確認失敗
修正程式
   ↓
該測試通過 + 全部 pytest 通過
   ↓
跑 mutation_check.py（把這類錯誤加進 MUTANTS）
   ↓
記錄到 review log
```
這樣做兩件事：不會被誤報騙去亂改，而且真 bug 修好後永遠有測試守著。

---

## 6. 第 5 層：你的人工檢查清單

`/diff` 看完改動後，依改動類型逐項打勾。

### 改到 `metrics.py`（科學公式）
- [ ] 每個 member 是先在 ROI 內空間平均，再算 ensemble 統計？
- [ ] 所有 SD / var / cov 都是 `ddof=1`？
- [ ] W1 是兩邊**各自排序**後相減？
- [ ] `delta_m = P_m − B_m` 有依 seed 對齊？
- [ ] spread 變化（SD 差）和變異數變化分開報告、單位正確？
- [ ] cohort 是「case 效果」的中位數 / IQR，不是 member 混在一起？
- [ ] 有沒有偷偷 clip、正規化、改單位？
- [ ] spec 有對應更新嗎？有沒有經過你同意？
- [ ] `mutation_check.py` 全部 killed？

### 改到 `store.py` / `main.py`（API、cache）
- [ ] cache miss 回 4xx 且列出可用選項，沒有內插或替代值？
- [ ] 檔案路徑只來自 manifest 白名單？
- [ ] 每個回應都有 `data_status`、單位、樣本數？
- [ ] 沒有 import torch / cuda / 模型模組（`test_cpu_boundary.py` 有過）？
- [ ] API 形狀改變前有先改 spec？

### 改到 `frontend/`
- [ ] SYNTHETIC 警告還在，且依 `data_status` 正確顯示？
- [ ] 有 loading / error / cache miss 狀態？
- [ ] 單位有標示？沒有「因果」「重要性」這類誇大用語？
- [ ] `npm run build` 成功？

### 改到 `offline/`（Phase 3+）
- [ ] 沒有改到模型權重或原推論演算法？
- [ ] baseline / perturbed 共用**每一個**隨機抽樣（含 churn）？
- [ ] no-op 擾動與原推論完全一致（golden test）？
- [ ] metadata 有 checkpoint SHA256、seed、sampler、40 個 sigma、單位？

### 每次都要
- [ ] **自己**重跑一次 `python -m pytest backend/tests -q`，不要只看 Claude 貼的輸出
- [ ] 改動範圍和你要求的一致，沒有順手重構
- [ ] `docs/PLAN.md` 有更新

---

## 7. Review 紀錄模板

建議放在 `docs/reviews/YYYY-MM-DD-<功能>.md`，或附在 `docs/PLAN.md`：

```markdown
## Review：<功能名稱>（YYYY-MM-DD）
- 改動檔案：
- 對應 spec / 驗收條件：
- pytest：__ passed（我本人重跑：是/否）
- mutation_check：__/__ killed
- 參考實作比對：
- scientific-reviewer findings：P0 _ / P1 _ / P2 _
- qa-reviewer findings：P0 _ / P1 _ / P2 _
- 已重現並修正：
- 判定為誤報（附理由）：
- 延後處理（附理由）：
- 結論：可 merge / 不可 merge
```

---

## 8. 可直接貼的提示詞

**把補強測試和突變檢查加進專案**
```
/implement-spec 依照 docs/REVIEW_PROTOCOL_zh-TW.md 附錄 A 新增 scripts/mutation_check.py，依照附錄 B 把 8 個補強測試加到 backend/tests/test_metrics.py，並把 scipy 加進 backend/requirements.txt。不要修改 backend/app/ 的任何程式。完成後回報 pytest 輸出和 mutation_check.py 輸出（預期 17 passed、8/8 killed）。
```

**獨立科學審查（不給結論）**
```
請使用 scientific-reviewer，唯讀審查 `git diff` 中的改動，對照 specs/CACHE_CONTRACT.md 和 specs/PHYSICAL_MAPPING.md。每個 finding 必須包含：嚴重度(P0/P1/P2)、file:line、具體反例（輸入→錯誤輸出）、可以證明它的測試。沒有反例的不要列。也請明確列出你「檢查過且認為正確」的項目以及理由。
```

**對抗式審查**
```
請使用 qa-reviewer，唯讀。目標是「弄壞」這次的改動：找出能讓 API 回傳錯誤數值、錯誤 data_status、或讀到白名單外檔案的輸入。每找到一個就給出具體請求 URL 和預期 vs 實際結果。
```

**驗證 finding（先重現再修）**
```
針對 finding <編號>：先寫一個會失敗的測試重現它，跑給我看失敗輸出。如果測試沒有失敗，就告訴我這是誤報，不要修改程式。確認失敗後再修，並把這類錯誤加進 scripts/mutation_check.py 的 MUTANTS。
```

---

## 9. Review 做不到的事（誠實的限制）

- **物理意義是否合理**（q700 擾動 0.5σ 是否現實、cohort 定義是否恰當）：只有你和領域專家能判斷，程式審查無法證明。
- **真實模型的正確性**：在拿到你的 EDM 程式碼之前，一切只在假資料上驗證過。Phase 3 的 golden test 才是真正的門檻。
- **突變測試只檢查列出來的錯誤類型**：8/8 killed 不代表沒有其他 bug，只代表這 8 種不會再溜過。
- **Hook 不是安全邊界**：`guard_commands.py` 是盡力而為的正規表達式，權限提示仍要自己看。
- **AI 審查員可能漏看，也可能誤報**：所以才需要第 5.5 節的「先重現再修」。

---

## 附錄 A：`scripts/mutation_check.py`（已在暫存區實測）

```python
"""Mutation check: inject known scientific bugs into a temp copy and see if pytest catches them.

Usage (from project root): python scripts/mutation_check.py
Never modifies the real source tree.
"""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = "backend/app/metrics.py"
MUTANTS = [
    ("M1 SD ddof=1 -> ddof=0",
     "b_sd = float(np.std(b, ddof=1))\n    p_sd = float(np.std(p, ddof=1))",
     "b_sd = float(np.std(b))\n    p_sd = float(np.std(p))"),
    ("M2 W1 paired instead of sorted",
     "np.mean(np.abs(np.sort(b) - np.sort(p)))", "np.mean(np.abs(b - p))"),
    ("M3 ROI mean ignores mask",
     "samples = maps[:, mask].mean(axis=1)", "samples = maps.mean(axis=(1, 2))"),
    ("M4 tail '>' -> '>='",
     "np.mean(b > threshold)),", "np.mean(b >= threshold)),"),
    ("M5 cohort median -> mean",
     '"median": float(np.median(vals)),', '"median": float(np.mean(vals)),'),
    ("M6 delta_sd reports variance change",
     '"delta_sd": p_sd - b_sd,', '"delta_sd": dvar,'),
    ("M7 layer distance without /sqrt(D)",
     "/ np.sqrt(b.shape[-1])", ""),
    ("M8 step W1 paired instead of sorted",
     "np.mean(np.abs(np.sort(roi_member_values(a[k], mask)) - np.sort(roi_member_values(b[k], mask))))",
     "np.mean(np.abs(roi_member_values(a[k], mask) - roi_member_values(b[k], mask)))"),
]


def pytest_passes(workdir: Path) -> bool:
    cmd = [sys.executable, "-m", "pytest", "backend/tests", "-q", "-x", "-p", "no:cacheprovider"]
    return subprocess.run(cmd, cwd=workdir, capture_output=True).returncode == 0


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for sub in ("backend", "data"):
            shutil.copytree(ROOT / sub, work / sub, ignore=shutil.ignore_patterns("__pycache__"))
        target = work / TARGET
        original = target.read_text(encoding="utf8")
        if not pytest_passes(work):
            print("Baseline tests fail; fix them before mutation testing.")
            return 2
        survived = 0
        for name, old, new in MUTANTS:
            if old not in original:
                print(f"SKIP     {name} (pattern not found; code changed?)")
                continue
            target.write_text(original.replace(old, new), encoding="utf8")
            if pytest_passes(work):
                survived += 1
                print(f"SURVIVED {name}  <- tests did NOT catch this bug")
            else:
                print(f"killed   {name}")
        target.write_text(original, encoding="utf8")
        print(f"\n{len(MUTANTS) - survived}/{len(MUTANTS)} mutants killed")
        return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
```

> 注意：突變是「字串取代」，`metrics.py` 的寫法改變後某些突變會顯示 `SKIP`。看到 `SKIP` 要更新該突變的字串，不能當作通過。

## 附錄 B：8 個補強測試（已驗證：正確程式全過、8 個突變全抓到）

加在 `backend/tests/test_metrics.py` 最後（需要 `scipy`）：

```python
from scipy.stats import wasserstein_distance
from app.metrics import layer_step_distance, step_w1_curve


def test_sd_uses_sample_ddof1():  # 抓 M1
    r = compare_ensemble(np.array([1.0, 2, 3, 4]), np.array([1.0, 2, 3, 4]) * 3)
    assert r["baseline_sd"] == pytest.approx(np.std([1, 2, 3, 4], ddof=1))
    assert r["perturbed_sd"] == pytest.approx(3 * np.std([1, 2, 3, 4], ddof=1))


def test_affine_scale_increases_sd_and_variance():  # ACCEPTANCE P0 缺的那條；抓 M6
    b = np.linspace(1, 30, 30)
    r = compare_ensemble(b, 2 * b)
    sd = np.std(b, ddof=1)
    assert r["delta_sd"] == pytest.approx(sd)            # sd(2B) - sd(B) = sd(B)
    assert r["delta_variance"] == pytest.approx(3 * sd**2)  # 4var - var


def test_w1_is_distributional_not_paired():  # 抓 M2
    b = np.linspace(0, 29, 30)
    r = compare_ensemble(b, b[::-1].copy())  # 同一組值、順序打亂
    assert r["w1"] == pytest.approx(0.0)
    assert r["delta_mean"] == pytest.approx(0.0)


def test_w1_matches_scipy_reference():  # 抓 M2（交叉比對參考實作）
    rng = np.random.default_rng(0)
    b, p = rng.gamma(2, 5, 30), rng.gamma(3, 5, 30)
    assert compare_ensemble(b, p)["w1"] == pytest.approx(wasserstein_distance(b, p))


def test_roi_mean_uses_only_masked_pixels():  # 抓 M3
    maps = np.zeros((3, 2, 2))
    maps[:, 0, 0] = [1, 2, 3]
    maps[:, 1, 1] = 100  # ROI 外的大值不可混入
    mask = np.array([[True, False], [False, False]])
    assert roi_member_values(maps, mask).tolist() == [1, 2, 3]


def test_tail_is_strictly_greater_than_threshold():  # 抓 M4
    r = compare_ensemble(np.array([40.0, 10.0]), np.array([40.0, 50.0]), threshold=40)
    assert r["baseline_tail_probability"] == 0.0
    assert r["perturbed_tail_probability"] == 0.5


def test_layer_distance_normalized_by_sqrt_dim():  # 抓 M7
    b = np.zeros((1, 1, 2, 4))
    assert layer_step_distance(b, b + 1.0) == [[1.0]]  # ||1||/sqrt(4) = 1


def test_step_w1_is_distributional():  # 抓 M8
    base = np.arange(6, dtype=float).reshape(1, 6, 1, 1)
    pert = base[:, ::-1].copy()
    assert step_w1_curve(base, pert, np.ones((1, 1), bool)) == [0.0]
```
