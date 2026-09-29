# LaTeX 原始碼

以下內容可直接複製成 `.tex` 檔，並使用 pdfLaTeX 編譯。

```latex
\documentclass[11pt,a4paper]{article}

% =========================================================
% Traditional Chinese / pdfLaTeX
% =========================================================
\usepackage{CJKutf8}
\usepackage[margin=1.7cm]{geometry}
\usepackage{amsmath,amssymb,mathtools}
\usepackage{booktabs,longtable,array}
\usepackage{xcolor}
\usepackage{enumitem}
\usepackage{hyperref}
\usepackage{fancyhdr}
\usepackage{tcolorbox}
\tcbuselibrary{breakable}
\usepackage{listings}

\hypersetup{
  colorlinks=true,
  linkcolor=blue,
  urlcolor=blue,
  citecolor=blue
}

\pagestyle{fancy}
\setlength{\headheight}{14pt}
\fancyhf{}
\lhead{NTNU Data Visualization with Python}
\rhead{Homework Analysis Guide}
\cfoot{\thepage}

\setlength{\parindent}{2em}
\setlength{\parskip}{0.38em}
\renewcommand{\arraystretch}{1.18}
\setlength{\tabcolsep}{5pt}
\emergencystretch=3em
\sloppy

\definecolor{myblue}{RGB}{35,80,160}
\definecolor{mygreen}{RGB}{35,120,75}
\definecolor{myorange}{RGB}{190,110,20}
\definecolor{myred}{RGB}{160,55,55}
\definecolor{mygray}{RGB}{245,245,245}

\newtcolorbox{plainbox}[1]{
  colback=blue!3,
  colframe=myblue,
  title=\textbf{#1},
  fonttitle=\bfseries,
  breakable
}
\newtcolorbox{keybox}[1]{
  colback=green!4,
  colframe=mygreen,
  title=\textbf{#1},
  fonttitle=\bfseries,
  breakable
}
\newtcolorbox{warnbox}[1]{
  colback=orange!5,
  colframe=myorange,
  title=\textbf{#1},
  fonttitle=\bfseries,
  breakable
}
\newtcolorbox{resultbox}[1]{
  colback=red!3,
  colframe=myred,
  title=\textbf{#1},
  fonttitle=\bfseries,
  breakable
}

\newcommand{\E}{\mathbb{E}}
\newcommand{\R}{\mathbb{R}}
\newcommand{\MAE}{\operatorname{MAE}}
\newcommand{\CRPS}{\operatorname{CRPS}}

\lstset{
  language=Python,
  basicstyle=\ttfamily\small,
  backgroundcolor=\color{mygray},
  frame=single,
  breaklines=true,
  columns=fullflexible,
  keepspaces=true,
  showstringspaces=false,
  keywordstyle=\color{myblue},
  commentstyle=\color{mygreen},
  stringstyle=\color{myred}
}

\begin{document}
\begin{CJK*}{UTF8}{bkai}

\begin{center}
{\LARGE \textbf{NTNU Data Visualization with Python}}\\[0.45em]
{\Large \textbf{氣候降尺度資料十題分析方法與結果詳解}}\\[0.35em]
{\large Student ID：61547029S}
\end{center}

\vspace{0.6em}

\begin{keybox}{這份作業的核心問題}
這份作業不是只要求把圖畫出來，而是要從四個方向評估氣候降尺度模型：
\[
\boxed{
\begin{gathered}
\text{數值分布是否正確}
\quad\longrightarrow\quad
\text{預測誤差有多大}\\
\text{ensemble 是否有幫助}
\quad\longrightarrow\quad
\text{時間、空間與不確定性是否合理}
\end{gathered}
}
\]
Q1--Q4 比較數值分布；Q5--Q7 分析預測誤差；Q8 檢查不確定性；Q9--Q10 分析降雨誤差的空間分布。
\end{keybox}

\begin{plainbox}{十題之間的邏輯關係}
\[
\boxed{
\begin{gathered}
\text{Q1--Q4：Prediction/Input 與 Truth 的分布是否相似}\\
\Downarrow\\
\text{Q5：每天的 MAE 通常是多少}\\
\Downarrow\\
\text{Q6：增加 ensemble members 是否能降低 MAE}\\
\Downarrow\\
\text{Q7：MAE 與 CRPS 是否有月份或季節性}\\
\Downarrow\\
\text{Q8：ensemble spread 能否涵蓋 Ground Truth}\\
\Downarrow\\
\text{Q9--Q10：誤差在空間上出現在哪裡}
\end{gathered}
}
\]
\end{plainbox}

\tableofcontents
\newpage

% =========================================================
\section{資料結構、符號與共同前處理}
% =========================================================

\subsection{三組資料代表什麼？}

主 NetCDF 檔案包含三個群組：

\begin{center}
\begin{tabular}{p{0.18\textwidth}p{0.70\textwidth}}
\toprule
群組 & 意義\\
\midrule
\texttt{truth} & 高解析度 Ground Truth，是評估模型時使用的真實參考答案。\\
\texttt{prediction} & 深度學習降尺度模型的輸出；每一天有 64 個 ensemble members。\\
\texttt{input} & 輸入模型的低品質資料。雖然已被內插成 $208\times208$，但細節與極端值仍可能不足。\\
\bottomrule
\end{tabular}
\end{center}

四個主要模型輸出變數為：
\begin{itemize}[leftmargin=2em]
\item precipitation：降雨量，單位為 mm/day；
\item temperature at 2m：2 公尺溫度，單位為 K；
\item eastward wind at 10m：10 公尺東向風，單位為 m/s；
\item northward wind at 10m：10 公尺北向風，單位為 m/s。
\end{itemize}

\subsection{資料維度}

Ground Truth 與 Input 可概念化為：
\[
y\in\R^{365\times208\times208}.
\]
第一個維度是日期，後兩個維度是空間位置。

Prediction 則包含 64 個 ensemble members：
\[
x\in\R^{64\times365\times208\times208}.
\]
其維度順序為：
\[
\boxed{
\text{ensemble}\times\text{time}\times\text{latitude grid}\times\text{longitude grid}
}.
\]

\subsection{為什麼所有題目都只分析陸地？}

Land mask 中：
\[
L_i=
\begin{cases}
1, & \text{格點 }i\text{ 是陸地},\\
0, & \text{格點 }i\text{ 是海洋}.
\end{cases}
\]

程式使用：
\begin{lstlisting}
land_mask = mask_dataset.variables['LANDMASK'][:]
land_only = land_mask == 1
\end{lstlisting}

之後所有統計量都只在 $L_i=1$ 的位置計算。這是因為題目明確要求只使用 land area；若把海洋一起納入，樣本組成與誤差大小都可能改變。

\subsection{整份 Notebook 的共同資料流}

\begin{lstlisting}
Open NetCDF files
       |
       v
Read truth / prediction / input
       |
       v
Apply LANDMASK == 1
       |
       +-----------------------------+
       |                             |
       v                             v
Distribution analysis          Error analysis
Q1--Q4                        Q5--Q10
       |                             |
       v                             v
Histogram                  Histogram / line / map
       |                             |
       +--------------+--------------+
                      v
             Scientific conclusion
\end{lstlisting}

% =========================================================
\section{Q1：模型輸出降雨的分布是否接近真實降雨？}
% =========================================================

\subsection{這題想知道什麼？}

這題比較模型輸出的 precipitation 與 Ground Truth precipitation，目的是判斷模型是否能重現全年陸地降雨的整體數值分布。

這裡問的是\textbf{邊際分布是否相似}，不是問某一天、某個位置是否預測正確。即使兩組 histogram 很像，仍可能存在位置錯置或日期錯置。

\subsection{資料如何整理？}

Ground Truth 的形狀為：
\[
(365,208,208),
\]
Prediction 的形狀為：
\[
(64,365,208,208).
\]

套用 land mask 後，程式將日期、空間及 ensemble 維度攤平成一維：

\begin{lstlisting}
truth_land_only = truth_precip[..., land_only].flatten()
pred_land_only = pred_precip[..., land_only].flatten()
\end{lstlisting}

若陸地格點數為 $N_L$，則 Ground Truth 約有 $365N_L$ 筆樣本，Prediction 約有 $64\times365N_L$ 筆樣本。

\subsection{為什麼使用 normalized histogram？}

因為 Prediction 的樣本數是 Ground Truth 的 64 倍，不能直接比較每個 bin 的筆數。程式使用：

\begin{lstlisting}
plt.hist(..., density=True)
\end{lstlisting}

使 histogram 的總面積為 1，因而比較的是機率密度而不是原始筆數。

若第 $b$ 個 bin 的寬度為 $\Delta_b$、樣本比例為 $p_b$，其 density 可理解為：
\[
h_b=\frac{p_b}{\Delta_b}.
\]

\subsection{為什麼 Y 軸使用 log scale？}

降雨分布高度右偏：無雨或弱降雨非常多，極端降雨非常少。如果使用一般線性 Y 軸，高降雨尾端會被大量低降雨樣本掩蓋。

\begin{lstlisting}
plt.yscale('log')
\end{lstlisting}

log scale 能同時顯示高密度的弱降雨區間與低密度的極端降雨尾端。

\begin{resultbox}{Q1 圖表證據與結論}
Prediction 與 Ground Truth 在低至中等降雨量區間有高度重疊，表示模型大致掌握一般降雨的整體分布。

但是 Ground Truth 的右尾延伸得更遠，而 Prediction 在高降雨量區間下降得較快，代表模型低估部分極端降雨。此外，Prediction 出現少量小於 0 的降雨值；負降雨在物理上不合理，顯示輸出仍可能需要非負約束或後處理。
\end{resultbox}

\begin{warnbox}{Q1 能回答與不能回答的事}
這張圖能回答「全年所有陸地值的整體分布是否相似」，但不能證明模型在正確日期、正確位置預測出正確降雨。位置與時間配對誤差要由後面的 MAE、月份分析與空間圖判斷。
\end{warnbox}

% =========================================================
\section{Q2：模型輸入降雨的分布是否接近真實降雨？}
% =========================================================

\subsection{這題與 Q1 有什麼不同？}

Q1 比較模型 Prediction 與 Truth；Q2 比較模型 Input 與 Truth。其目的在於檢查低品質內插輸入本身與高解析 Ground Truth 有多大差異，也可與 Q1 對照，判斷模型輸出是否比原始輸入更接近真實資料。

\subsection{資料處理}

\begin{lstlisting}
truth_precip = dataset.groups['truth'].variables['precipitation'][:]
input_precip = dataset.groups['input'].variables['precipitation'][:]

truth_land_only = truth_precip[..., land_mask == 1].flatten()
input_land_only = input_precip[..., land_mask == 1].flatten()
\end{lstlisting}

Input 沒有 64 個 ensemble members，因此兩組資料都只包含日期與空間維度。後續同樣使用共同 bins、\texttt{density=True} 與 log Y 軸。

\subsection{為什麼必須使用共同 bins？}

如果兩個 histogram 各自使用不同範圍與切分方式，即使視覺上重疊，也不能公平比較。程式先找出共同最小值與最大值：

\begin{lstlisting}
hist_min = min(np.min(truth_land_only), np.min(input_land_only))
hist_max = max(np.max(truth_land_only), np.max(input_land_only))
shared_bins = np.linspace(hist_min, hist_max, 51)
\end{lstlisting}

因此每一個柱子都代表相同的降雨量區間。

\begin{resultbox}{Q2 圖表證據與結論}
Input 與 Ground Truth 在低降雨量區間大致相近，但 Input 的高降雨右尾明顯較短，在中高降雨量區間的密度也較低。

這代表低解析資料經過一般內插後，雖然尺寸已變成 $208\times208$，仍無法恢復真正高解析資料中的強降雨與極端值。內插會讓資料變得平滑，但不會自動創造缺失的小尺度強降雨結構。
\end{resultbox}

\begin{keybox}{Q1 與 Q2 合併解讀}
Q2 顯示 Input 對高降雨的表示不足；Q1 顯示 Prediction 雖仍低估最極端尾端，但通常比 Input 更能延伸到中高降雨區間。因此模型確實學到了一部分原始輸入沒有的降雨結構。
\end{keybox}

% =========================================================
\section{Q3：模型輸出溫度的分布是否接近真實溫度？}
% =========================================================

\subsection{分析目的}

這題將模型輸出的 2m temperature 與 Ground Truth 2m temperature 比較，檢查模型能否重現全年陸地溫度的整體數值範圍與分布形狀。

\subsection{資料處理}

\begin{lstlisting}
truth_temp = dataset.groups['truth'].variables['temperature_2m'][:]
pred_temp = dataset.groups['prediction'].variables['temperature_2m'][:]

truth_land_only = truth_temp[..., land_mask == 1].flatten()
pred_land_only = pred_temp[..., land_mask == 1].flatten()
\end{lstlisting}

和 Q1 一樣，Prediction 的 64 個 members 全部納入分布分析。使用 \texttt{density=True} 後，樣本數差異不會主導圖形。

\subsection{為什麼溫度圖不需要 log Y 軸？}

降雨通常有大量接近 0 的資料以及很長的右尾；溫度則集中在較連續的範圍內，分布沒有降雨那麼極端偏斜。因此一般線性 Y 軸已能清楚比較兩組密度。

\begin{resultbox}{Q3 圖表證據與結論}
Prediction 與 Ground Truth 的 histogram 在大部分溫度區間幾乎重疊，兩者的主要溫度範圍、峰值位置與分布形狀都非常接近。

因此模型能良好重現全年溫度的整體統計特性。相較於降雨，溫度是較平滑、較連續的物理變數，所以通常也較容易被模型預測。
\end{resultbox}

\begin{warnbox}{分布相似不等於逐點準確}
假設模型把北部與南部的溫度互換，整體 histogram 仍可能相同。因此 Q3 只能說明全域分布相似，不能單獨證明空間與時間上的預測完全正確。逐點準確度需要用 MAE 等指標檢查。
\end{warnbox}

% =========================================================
\section{Q4：模型輸入溫度的分布是否接近真實溫度？}
% =========================================================

\subsection{分析目的}

這題比較 Input temperature 與 Ground Truth temperature，檢查低品質內插輸入是否保留真實資料的高低溫變化。

\subsection{資料處理}

\begin{lstlisting}
truth_temp = dataset.groups['truth'].variables['temperature_2m'][:]
input_temp = dataset.groups['input'].variables['temperature_2m'][:]

truth_land_only = truth_temp[..., land_mask == 1].flatten()
input_land_only = input_temp[..., land_mask == 1].flatten()
\end{lstlisting}

兩組資料使用相同 bins 與 normalized histogram，比較的是全年所有陸地格點的溫度分布。

\begin{resultbox}{Q4 圖表證據與結論}
Input 與 Ground Truth 的主要溫度範圍有重疊，但 Input 分布較窄，資料較集中在中間溫度區間；Ground Truth 則具有較完整的低溫與高溫尾端。

這代表內插輸入具有平滑效應：極低溫與極高溫容易被削弱，中間溫度的相對比例則提高。與 Q3 對照後，可以看出 Prediction 的分布明顯比 Input 更接近 Ground Truth。
\end{resultbox}

\begin{keybox}{Q3 與 Q4 合併解讀}
Q4 說明原始 Input 對溫度極端值的表現不足；Q3 則顯示模型輸出幾乎重現 Ground Truth 的整體溫度分布。因此模型不只是複製 Input，而是修正了一部分內插造成的分布壓縮。
\end{keybox}

% =========================================================
\section{Q5：溫度與降雨的每日 MAE 分布為何？}
% =========================================================

\subsection{MAE 的意義}

Absolute Error 是預測值與真實值差距的絕對值：
\[
e_{d,i}=|\hat y_{d,i}-y_{d,i}|,
\]
其中 $d$ 表示日期，$i$ 表示陸地格點。

MAE 對所有誤差給相同線性權重，單位與原變數相同，因此容易解釋：溫度 MAE 的單位是 K，降雨 MAE 的單位是 mm/day。

\subsection{第一步：計算 ensemble mean}

每一天有 $M=64$ 個 prediction members。程式先計算 ensemble mean：
\[
\bar x_{d,i}=\frac{1}{M}\sum_{m=1}^{M}x_{m,d,i}.
\]

\begin{lstlisting}
pred_temp_mean = np.ma.mean(pred_temp, axis=0)
pred_precip_mean = np.ma.mean(pred_precip, axis=0)
\end{lstlisting}

資料形狀由 $(64,365,208,208)$ 變成 $(365,208,208)$。

\subsection{第二步：計算每個格點的 absolute error}

\begin{lstlisting}
temp_absolute_error = np.abs(pred_temp_mean - truth_temp)
precip_absolute_error = np.abs(pred_precip_mean - truth_precip)
\end{lstlisting}

只保留陸地後，每一天仍保有所有陸地格點的誤差。

\subsection{第三步：得到 365 個 Daily MAE}

若陸地格點集合為 $\mathcal L$、格點數為 $N_L$，則第 $d$ 天的 MAE 為：
\[
\MAE_d=\frac{1}{N_L}\sum_{i\in\mathcal L}|\bar x_{d,i}-y_{d,i}|.
\]

\begin{lstlisting}
temp_daily_mae = np.ma.mean(temp_error_land, axis=1)
precip_daily_mae = np.ma.mean(precip_error_land, axis=1)
\end{lstlisting}

因此每個變數有 365 個數字。Histogram 中的一筆樣本代表一天，而不是一個格點。

\subsection{如何解讀 histogram？}

Histogram 回答的是：
\begin{quote}
一年之中，有多少天的平均陸地誤差落在某個範圍？誤差是否集中？是否有少數極端錯誤日期？
\end{quote}

\begin{resultbox}{Q5 溫度結果}
溫度 Daily MAE 大多集中在約 0.3--0.6 K，表示多數日期的平均溫度誤差相對穩定。只有少數日期超過 1 K，並有極少數日期接近約 2.15 K。

因此溫度 MAE 分布雖然略向右偏，但整體集中度高，模型在大部分日期的溫度表現較穩定。
\end{resultbox}

\begin{resultbox}{Q5 降雨結果}
降雨 Daily MAE 呈現明顯右偏：大量日期集中在低 MAE 區間，但少數日期的 MAE 非常高，最大可接近約 70 mm/day。

這表示模型平常的降雨誤差可能不大，但在少數強降雨或極端天氣日期會出現很大的預測錯誤。只看全年平均值可能會掩蓋這種長右尾風險，因此畫出完整分布是必要的。
\end{resultbox}

\begin{warnbox}{不同變數的 MAE 數字不能直接比較}
溫度與降雨的單位不同，不能因為降雨 MAE 數字較大，就直接說模型對降雨一定差多少倍。合理的比較方式包括各自變數內部比較、標準化誤差，或與該變數自然變異幅度相比。
\end{warnbox}

% =========================================================
\section{Q6：增加 ensemble members 是否能改善平均準確度？}
% =========================================================

\subsection{分析問題}

這題要判斷當 ensemble members 從 1 個逐漸增加至 64 個時，ensemble mean 的 MAE 是否降低，以及四個輸出變數是否具有相同趨勢。

\subsection{前 $N$ 個 members 的 ensemble mean}

當使用前 $N$ 個 members 時：
\[
\bar x^{(N)}_{d,i}
=
\frac{1}{N}\sum_{m=1}^{N}x_{m,d,i},
\qquad N=1,2,\ldots,64.
\]

對應的整體陸地 MAE 為：
\[
\MAE_v(N)
=
\frac{1}{365N_L}
\sum_{d=1}^{365}
\sum_{i\in\mathcal L}
\left|
\bar x^{(N)}_{d,i}-y_{d,i}
\right|,
\]
其中 $v$ 代表 precipitation、temperature 或 wind variable。

\subsection{為什麼使用 cumulative sum？}

若每個 $N$ 都重新計算前 $N$ 個 members 的平均，會重複大量加法。程式先做：

\begin{lstlisting}
pred_cumsum = np.ma.cumsum(pred_data, axis=0)
\end{lstlisting}

則前 $N$ 個 members 的總和已存在：

\begin{lstlisting}
pred_n_mean = pred_cumsum[n - 1] / n
\end{lstlisting}

這能降低不必要的重複運算。

\subsection{四個子圖為什麼分開畫？}

四個變數的單位與自然尺度不同：

\begin{center}
\begin{tabular}{ll}
\toprule
變數 & MAE 單位\\
\midrule
Precipitation & mm/day\\
Temperature 2m & K\\
Eastward Wind 10m & m/s\\
Northward Wind 10m & m/s\\
\bottomrule
\end{tabular}
\end{center}

因此分成四張圖，觀察每個變數本身隨 $N$ 改變的趨勢，而不是直接比較不同單位的絕對高度。

\begin{resultbox}{Q6 圖表證據與結論}
四個變數的 MAE 都隨 ensemble members 增加而下降。從 1 個增加至數個 members 時改善最明顯；約在 10--20 個 members 後，曲線逐漸變平；接近 64 個 members 時，繼續增加 members 的改善已很小。

這表示 ensemble averaging 能抵消個別 member 的隨機偏差或雜訊，但存在邊際效益遞減。四個變數方向一致，兩個風速變數的相對降幅較明顯，降雨的相對改善則較小。
\end{resultbox}

\begin{warnbox}{方法上的一個重要限制}
目前程式使用「前 $N$ 個 members」，因此曲線會受到 ensemble 排列順序影響。若要估計一般化的 ensemble-size 效果，可對每個 $N$ 多次隨機抽取 members，再報告平均 MAE 與信賴範圍。不過目前方法仍能回答這組固定 ensemble 順序下的累積平均效果。
\end{warnbox}

% =========================================================
\section{Q7：誤差是否具有月份或季節性？MAE 與 CRPS 是否不同？}
% =========================================================

\subsection{第一步：把時間轉成月份}

NetCDF 的時間通常不是直接儲存成日期文字，而是「從某個基準時間開始經過多少小時或天」。程式使用：

\begin{lstlisting}
dates = nc.num2date(
    time_var[:],
    units=time_var.units,
    calendar=time_var.calendar
)
months = np.array([date.month for date in dates])
\end{lstlisting}

得到每一天所屬的月份 $m(d)\in\{1,\ldots,12\}$。

\subsection{每日 MAE}

MAE 使用 ensemble mean：
\[
\bar x_{d,i}=\frac{1}{M}\sum_{m=1}^{M}x_{m,d,i},
\]
\[
\MAE_d
=
\frac{1}{N_L}
\sum_{i\in\mathcal L}
|\bar x_{d,i}-y_{d,i}|.
\]

因此 MAE 評估的是 ensemble mean 作為一個 deterministic prediction 時的準確度。

\subsection{CRPS 是什麼？}

CRPS，全名 Continuous Ranked Probability Score，用來評估整個 ensemble predictive distribution，而不是只看 ensemble mean。

對某一天、某個格點，若 ensemble predictions 為 $x_1,\ldots,x_M$，Ground Truth 為 $y$，則 ensemble CRPS 為：
\[
\CRPS
=
\frac{1}{M}\sum_{m=1}^{M}|x_m-y|
-
\frac{1}{2M^2}
\sum_{m=1}^{M}\sum_{j=1}^{M}|x_m-x_j|.
\]

第一項測量所有 members 與 Ground Truth 的距離；第二項反映 ensemble members 彼此之間的 spread。

\begin{plainbox}{MAE 與 CRPS 的差別}
\textbf{MAE} 只問：「64 個 members 的平均預測準不準？」

\textbf{CRPS} 則問：「整個 ensemble distribution 是否同時具有正確位置與合理 spread？」

兩個指標都是越低越好，但 CRPS 對 probabilistic forecast 提供更完整的評估。
\end{plainbox}

\subsection{程式為什麼先排序？}

直接計算第二項需要建立 $M\times M$ 的兩兩差異。程式將 predictions 排序後，使用等價快速公式：
\[
\frac{1}{M^2}
\sum_{m=1}^{M}
(2m-M-1)x_{(m)},
\]
其中 $x_{(m)}$ 是由小到大排序後的第 $m$ 個 member。

此公式與完整兩兩差異公式數學上等價，但更節省記憶體與計算量。

\subsection{如何得到月平均？}

先算每日 MAE 與每日 CRPS，再將同月份的日期平均：
\[
\overline{\MAE}_k
=
\frac{1}{D_k}
\sum_{d:m(d)=k}\MAE_d,
\]
\[
\overline{\CRPS}_k
=
\frac{1}{D_k}
\sum_{d:m(d)=k}\CRPS_d,
\]
其中 $D_k$ 為第 $k$ 個月份的天數。

\begin{resultbox}{Q7 降雨結果}
降雨呈現最明顯的季節性。1--3 月誤差較低，4 月開始上升，6--9 月明顯較高，並在 8 月達到最高；之後於秋季下降，11 月降至低值。

MAE 與 CRPS 的月份趨勢高度相似，表示夏季的高誤差不只是 ensemble spread 的問題，ensemble mean 本身也在這些月份較難準確預測。
\end{resultbox}

\begin{resultbox}{Q7 溫度與風速結果}
溫度和兩個風速變數也會隨月份波動，但變化不像降雨那麼平滑。兩種指標的高低月份大致相互對應，例如部分變數在 5 月或 8 月較高、11 月較低。

CRPS 通常低於 MAE 的數值，但不能只依兩條線的高度判斷優劣，因為它們衡量的對象不同；更重要的是比較兩者的月份趨勢是否一致。
\end{resultbox}

% =========================================================
\section{Q8：3-sigma uncertainty range 能否涵蓋 Ground Truth？}
% =========================================================

\subsection{這題在檢查什麼？}

64 個 ensemble members 不只可以取平均，也可用其 spread 表示模型的不確定性。若模型在某個格點的 members 非常分散，表示模型對該位置較不確定；若 members 很集中，表示模型聲稱自己較有把握。

這題要檢查模型所提供的不確定性是否足以涵蓋真實答案。

\subsection{計算 ensemble mean 與 standard deviation}

對每一天、每個格點：
\[
\mu_{d,i}=\frac{1}{M}\sum_{m=1}^{M}x_{m,d,i},
\]
\[
\sigma_{d,i}
=
\sqrt{
\frac{1}{M}
\sum_{m=1}^{M}
(x_{m,d,i}-\mu_{d,i})^2
}.
\]

目前程式使用 NumPy 預設的 population standard deviation，即 \texttt{ddof=0}。

\subsection{建立 3-sigma interval}

\[
I_{d,i}
=
[\mu_{d,i}-3\sigma_{d,i},\ \mu_{d,i}+3\sigma_{d,i}].
\]

若 Ground Truth 滿足：
\[
\mu_{d,i}-3\sigma_{d,i}
\le y_{d,i}\le
\mu_{d,i}+3\sigma_{d,i},
\]
則該樣本被視為 covered。

\subsection{Coverage rate}

\[
\operatorname{Coverage}
=
\frac{
\sum_{d=1}^{365}
\sum_{i\in\mathcal L}
\mathbf 1(y_{d,i}\in I_{d,i})
}{365N_L}
\times100\%.
\]

若 predictive distribution 近似常態而且校準良好，$\mu\pm3\sigma$ 理論上約涵蓋 99.7\% 的結果。這個 99.7\% 是參考基準，不代表所有非高斯變數都必須精確達到該數值。

\begin{center}
\begin{tabular}{lc}
\toprule
變數 & 3-sigma Coverage\\
\midrule
Precipitation & 約 83.01\%\\
Temperature 2m & 約 80.90\%\\
Eastward Wind 10m & 約 85.65\%\\
Northward Wind 10m & 約 89.04\%\\
\bottomrule
\end{tabular}
\end{center}

\begin{resultbox}{Q8 結論}
四個變數的 coverage 都低於 90\%，與常態分布下 3-sigma 約 99.7\% 的參考值有明顯差距。因此 ensemble uncertainty range 無法充分涵蓋 Ground Truth。

這表示 ensemble spread 相對於實際預測誤差偏窄，模型可能有 overconfidence。四個變數的方向一致，但程度不同：Northward Wind coverage 最高，Temperature coverage 最低。
\end{resultbox}

\begin{warnbox}{Coverage 的正確解讀}
Coverage 低不一定只代表平均預測差，也可能代表 ensemble members 太集中。相反地，單純把 spread 放得非常寬雖可提高 coverage，卻不代表預測有用。因此完整的不確定性評估應同時考慮 coverage、interval width、CRPS、rank histogram 與 spread-skill relation。
\end{warnbox}

% =========================================================
\section{Q9：不同月份的高降雨誤差空間分布是否不同？}
% =========================================================

\subsection{為什麼前面的指標還不夠？}

Q5 與 Q7 將所有陸地格點平均成一個數字，因此能描述整體誤差大小，卻無法回答誤差主要發生在哪裡。

Q9 保留 $208\times208$ 空間結構，對每個格點分別計算 monthly spatial MAE。

\subsection{計算每日空間 absolute error}

先對 64 個 members 取平均：
\[
\bar x_{d,i}=\frac{1}{64}\sum_{m=1}^{64}x_{m,d,i}.
\]

再計算每個位置的誤差：
\[
e_{d,i}=|\bar x_{d,i}-y_{d,i}|.
\]

這一步沒有對空間格點取平均，因此每天仍保留一張 $208\times208$ 的 error map。

\subsection{計算每個月份的 spatial MAE map}

對第 $k$ 個月份：
\[
E_{k,i}
=
\frac{1}{D_k}
\sum_{d:m(d)=k}
e_{d,i}.
\]

$E_{k,i}$ 表示格點 $i$ 在第 $k$ 個月份的平均降雨絕對誤差。最後得到 12 張地圖：
\[
E\in\R^{12\times208\times208}.
\]

海洋位置被設為 \texttt{NaN}，因此不顯示：

\begin{lstlisting}
monthly_mae = np.full((208, 208), np.nan)
monthly_mae[land_only] = (
    error_sum[land_only] / len(day_indices)
)
\end{lstlisting}

\subsection{為什麼 12 張圖必須共用色階？}

如果每張圖各自設定最大值，一個低誤差月份也可能看起來和高誤差月份一樣亮。因此程式使用共同的：

\begin{lstlisting}
vmin = 0
vmax = np.nanpercentile(all_land_errors, 99)
\end{lstlisting}

共同色階讓相同顏色在所有月份代表相同誤差大小。使用第 99 百分位作為上限，可避免極少數極端值壓縮其餘地圖的色彩差異；代價是高於該值的區域都會呈現最亮顏色。

\begin{resultbox}{Q9 圖表證據與結論}
降雨誤差的空間分布會隨月份明顯改變。1--3 月整體較暗，高誤差區域較少；4--5 月開始增加；6--9 月大範圍區域變亮，8 月尤其明顯；10 月後逐漸下降，11--12 月再次較低。

因此模型降雨誤差同時具有季節性與空間性。不同地區可能因地形、季風、對流降雨或資料解析度等因素，在不同月份呈現不同的預測難度。
\end{resultbox}

\begin{keybox}{Q7 與 Q9 的關係}
Q7 告訴我們「哪個月份整體誤差較大」；Q9 進一步告訴我們「該月份的誤差主要出現在哪些位置」。Q7 是時間摘要，Q9 是保留地理位置的空間診斷。
\end{keybox}

% =========================================================
\section{Q10：只看 Top 10\% 強降雨事件時，空間誤差是否不同？}
% =========================================================

\subsection{Q10 與 Q9 的核心差別}

Q9 使用所有日期與所有降雨強度，因此包含無雨、弱降雨與強降雨。Q10 只保留 Ground Truth 中最高的 10\% 降雨值，專門檢查模型在高降雨事件下的空間誤差。

\subsection{如何定義 Top 10\%？}

程式先收集全年所有陸地日期--格點的 Ground Truth precipitation：
\[
\mathcal Y_L
=
\{y_{d,i}:d=1,\ldots,365,\ i\in\mathcal L\}.
\]

再計算第 90 百分位門檻：
\[
q_{0.9}=\operatorname{Percentile}_{90}(\mathcal Y_L).
\]

Notebook 的執行結果為：
\[
\boxed{q_{0.9}\approx12.9302\ \text{mm/day}}.
\]

事件指示變數為：
\[
I_{d,i}
=
\mathbf 1(i\in\mathcal L)
\mathbf 1(y_{d,i}\ge q_{0.9}).
\]

因此這裡的「事件」是某一天、某個陸地格點的 Ground Truth precipitation 達到全年陸地資料的最高 10\%，不是將整個日期視為單一事件。

\subsection{為什麼需要 event count？}

不同格點在不同月份發生強降雨的次數不同。程式分別累積：

\begin{lstlisting}
error_sum[extreme_event] += abs_error[extreme_event]
event_count[extreme_event] += 1
\end{lstlisting}

對月份 $k$、格點 $i$，Top 10\% 條件下的平均誤差為：
\[
E^{\mathrm{extreme}}_{k,i}
=
\frac{
\sum_{d:m(d)=k}I_{d,i}|\bar x_{d,i}-y_{d,i}|
}{
\sum_{d:m(d)=k}I_{d,i}
}.
\]

只有分母大於 0，也就是該格點在該月真的發生過強降雨時，才會計算平均值。

\subsection{圖上的白色區域代表什麼？}

沒有事件的格點被設為 \texttt{NaN}：

\begin{lstlisting}
has_event = event_count > 0
monthly_extreme_mae[has_event] = (
    error_sum[has_event] / event_count[has_event]
)
\end{lstlisting}

因此白色可能代表：
\begin{itemize}[leftmargin=2em]
\item 海洋格點；或
\item 該陸地格點在該月份沒有發生 Top 10\% 強降雨。
\end{itemize}

白色不代表誤差為 0。若誤把白色解讀成完美預測，會得到錯誤結論。

\begin{resultbox}{Q10 圖表證據與結論}
只考慮 Top 10\% 強降雨時，不同月份的高誤差區域仍明顯不同。冬季強降雨事件較少，有效區域較零散；5--10 月強降雨事件增加，高誤差區域更廣且更集中。

相較於 Q9，Q10 的色階上限與實際誤差幅度明顯較高，表示模型在極端降雨條件下比一般天氣更容易產生大誤差。這也說明只看所有事件的平均誤差，可能低估模型在重要極端事件中的風險。
\end{resultbox}

\begin{warnbox}{Top 10\% 定義的限制}
目前使用全年所有陸地日期--格點的統一第 90 百分位門檻。若改成「每個月份各自的 Top 10\%」、「每個格點各自的 Top 10\%」或「全年降雨量最高的 10\% 日期」，事件集合與結論都會不同。報告時應明確說明本題採用的是全年、全陸地、grid--day level 的統一門檻。
\end{warnbox}

% =========================================================
\section{十題的分析尺度總整理}
% =========================================================

\begin{center}
\begin{longtable}{p{0.07\textwidth}p{0.22\textwidth}p{0.24\textwidth}p{0.36\textwidth}}
\toprule
題目 & 主要比較 & 被平均或攤平的維度 & 最後圖表回答的問題\\
\midrule
Q1 & Prediction precip vs Truth & ensemble、time、space 攤平 & 模型輸出降雨的整體分布是否相似？\\
Q2 & Input precip vs Truth & time、space 攤平 & 原始輸入降雨是否缺少強降雨？\\
Q3 & Prediction temp vs Truth & ensemble、time、space 攤平 & 模型輸出溫度的整體分布是否相似？\\
Q4 & Input temp vs Truth & time、space 攤平 & 輸入溫度是否因內插而過度平滑？\\
Q5 & Ensemble mean vs Truth & 每天對 land space 平均 & 一年中每日 MAE 的分布與極端值如何？\\
Q6 & 不同 ensemble size & 對 time 與 land space 平均 & members 增加是否降低整體 MAE？\\
Q7 & 月份 MAE/CRPS & 每天對 land space 平均，再按月平均 & 誤差是否有月份或季節性？\\
Q8 & $\mu\pm3\sigma$ vs Truth & 對全年所有 land samples 計數 & ensemble uncertainty 是否充分涵蓋真值？\\
Q9 & Monthly precip error & 保留 space，對該月日期平均 & 一般降雨誤差主要出現在哪裡？\\
Q10 & Top 10\% precip error & 保留 space，只平均 extreme events & 強降雨條件下的高誤差區域在哪裡？\\
\bottomrule
\end{longtable}
\end{center}

% =========================================================
\section{整體科學結論}
% =========================================================

\begin{plainbox}{結論一：模型對溫度分布的重建優於降雨極端值}
模型輸出溫度與 Ground Truth 的分布幾乎重疊，表示模型能有效重現溫度的整體統計特性。降雨的一般範圍也有相似性，但模型對高降雨尾端仍有低估，並出現少量負降雨預測。
\end{plainbox}

\begin{plainbox}{結論二：模型輸出相較於 Input 有改善}
Input precipitation 缺少高降雨尾端，Input temperature 則呈現較窄、較平滑的分布。Prediction 對兩者都有改善，代表模型不是單純複製內插輸入，而是學到部分高解析結構。
\end{plainbox}

\begin{plainbox}{結論三：降雨比溫度更難預測}
溫度 Daily MAE 較集中；降雨 Daily MAE 呈長右尾，少數日期可能出現非常大的誤差。這反映強降雨具有局部性、非線性與高度不均勻等特性。
\end{plainbox}

\begin{plainbox}{結論四：增加 ensemble members 有幫助，但效益遞減}
四個變數的 ensemble-mean MAE 都隨 members 增加而下降，前幾個 members 的改善最大，約 10--20 個 members 後逐漸趨平。因此 ensemble averaging 有效，但不是 members 越多就能等比例改善。
\end{plainbox}

\begin{plainbox}{結論五：降雨誤差具有明顯季節與空間模式}
降雨 MAE 與 CRPS 在夏季升高，8 月最高。空間圖也顯示 6--9 月高誤差區域明顯擴大。模型困難並非均勻分布，而是與月份、地理位置及強降雨事件有關。
\end{plainbox}

\begin{plainbox}{結論六：ensemble uncertainty 偏窄}
四個變數的 3-sigma coverage 約為 81--89\%，遠低於常態分布參考值 99.7\%。這代表 ensemble spread 無法充分反映實際誤差，模型存在不確定性低估或 overconfidence 的可能。
\end{plainbox}

\begin{resultbox}{最終總結}
此降尺度模型對一般氣候狀態，尤其是溫度，具有良好的整體分布重建能力；ensemble averaging 也能改善平均預測準確度。然而，極端降雨仍是主要弱點：模型低估高降雨尾端、極端日期的 MAE 很大，而且高誤差具有明顯季節與空間差異。此外，ensemble spread 對真實誤差的涵蓋不足，因此未來除了提升平均預測，也應改善極端事件表現與 probabilistic calibration。
\end{resultbox}

% =========================================================
\section{報告或口頭詢問時的重點回答}
% =========================================================

\subsection*{為什麼 precipitation histogram 使用 log Y 軸？}
因為弱降雨樣本很多、極端降雨樣本很少。使用 log scale 才能同時看到主要分布與低密度右尾。

\subsection*{為什麼 Prediction 有 64 倍樣本仍能和 Truth 比？}
因為 histogram 使用 \texttt{density=True}，比較的是正規化後的機率密度，而不是原始樣本筆數。

\subsection*{為什麼 Q5 使用 ensemble mean？}
因為 MAE 是 deterministic prediction metric。先將 64 個 members 平均，可以把 ensemble 轉成單一代表預測，再和 Ground Truth 比較。

\subsection*{CRPS 為什麼比 MAE 更適合 ensemble？}
MAE 只評估 ensemble mean；CRPS 使用所有 members，能同時考慮真值距離與 ensemble spread，因此更適合 probabilistic forecast。

\subsection*{Coverage 低代表什麼？}
代表 Ground Truth 經常落在 ensemble mean $\pm3\sigma$ 之外。可能原因是 ensemble spread 太小、平均預測有偏差，或 predictive distribution 並非理想常態分布。

\subsection*{Q9 與 Q10 有何不同？}
Q9 是所有天氣條件的 monthly spatial MAE；Q10 是 Ground Truth 達到全年 Top 10\% 時的 conditional spatial MAE。Q10 更聚焦於高影響的強降雨事件。

\subsection*{Q10 的白色區域是不是零誤差？}
不是。白色可能是海洋，也可能是該格點當月沒有 Top 10\% 強降雨事件，因此沒有可計算的 conditional MAE。

% =========================================================
\section{重現分析時需要的檔案與注意事項}
% =========================================================

Notebook 使用相對路徑，因此執行時必須將下列檔案放在同一資料夾：
\begin{itemize}[leftmargin=2em]
\item \texttt{61547029s.ipynb}
\item \texttt{output\_0\_all.nc}
\item \texttt{wrf\_208x208\_grid\_coords.nc}
\end{itemize}

執行前需安裝：
\begin{lstlisting}
numpy
matplotlib
netCDF4
\end{lstlisting}

由於主資料約 15 GB，部分題目一次讀取全年 64-member prediction 時會使用大量記憶體。Q7--Q10 採逐日讀取，可降低記憶體需求；若電腦記憶體不足，Q1、Q3、Q5、Q6 也可改成逐日或分批處理。

\begin{keybox}{最後應牢記的八句話}
\begin{enumerate}[leftmargin=2em]
\item Q1--Q4 比較的是整體分布，不是逐點正確性。
\item Histogram 使用共同 bins 才能公平比較。
\item 降雨使用 log Y 軸是為了看見稀少的極端尾端。
\item Q5 的一筆 histogram 樣本代表一天的 land-average MAE。
\item Q6 顯示 ensemble averaging 有效，但具有邊際效益遞減。
\item MAE 評估 ensemble mean；CRPS 評估整個 ensemble distribution。
\item 3-sigma coverage 低表示模型的不確定性範圍不夠寬或預測存在偏差。
\item Q9 看所有降雨，Q10 只看 Ground Truth Top 10\% 強降雨。
\end{enumerate}
\end{keybox}

\end{CJK*}
\end{document}
```
