import React, { useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import './style.css'

const fmt = (x, n=2) => typeof x === 'number' ? x.toFixed(n) : '—'

function MiniLine({values, label}) {
  if (!values?.length) return null
  const w=550, h=130, max=Math.max(1e-6,...values), min=0
  const points=values.map((v,i)=>`${20+(i/(values.length-1||1))*(w-38)},${h-20-(v-min)/(max-min)*(h-35)}`).join(' ')
  return <figure><figcaption>{label}</figcaption><svg viewBox={`0 0 ${w} ${h}`} role="img" aria-label={label}><line x1="20" y1="110" x2="530" y2="110" stroke="#64748b"/><polyline points={points} fill="none" stroke="#0d9488" strokeWidth="3"/>{values.map((v,i)=><circle key={i} cx={20+i/(values.length-1||1)*(w-38)} cy={h-20-(v-min)/(max-min)*(h-35)} r="3" fill="#0f766e"/>)}</svg><small>Step index 0–{values.length-1}；toy demo 不代表真實 EDM denoising steps</small></figure>
}

function App(){
  const [options,setOptions]=useState(null), [error,setError]=useState(''), [mode,setMode]=useState('case'), [caseId,setCaseId]=useState('20180112'), [roi,setRoi]=useState('northeast'), [result,setResult]=useState(null), [busy,setBusy]=useState(false)
  useEffect(()=>{fetch('/api/options').then(r=>{if(!r.ok)throw new Error(`HTTP ${r.status}`);return r.json()}).then(o=>{setOptions(o);setCaseId(o.cases.includes('20180112')?'20180112':o.cases[0]);setRoi(o.output_rois[0])}).catch(e=>setError(String(e)))},[])
  const query = async (newMode=mode) => {
    setBusy(true);setError('');setResult(null)
    const common=`variable=q700&input_roi=north&magnitude=0.5&output_roi=${roi}`
    const url=newMode==='case'?`/api/case?case_id=${caseId}&${common}`:`/api/cohort?cohort=winter&${common}`
    try{const r=await fetch(url);const data=await r.json();if(!r.ok)throw new Error(data.detail||`HTTP ${r.status}`);setResult(data)}catch(e){setError(String(e))}finally{setBusy(false)}
  }
  const metric = result?.metrics
  const cohort=result?.summary
  return <main><header><h1>Taiwan EDM XAI</h1><p>Input physical hypothesis → Rainfall ensemble distribution → Cohort / Step / Layer</p></header>
    <div className="warning">SYNTHETIC DEMONSTRATION — 所有地圖、降雨量與 feature 數值都不是你的 Taiwan EDM 實測結果。</div>
    <section className="controls"><h2>CPU-only XAI：分析條件</h2><div className="fields"><label>分析模式<select value={mode} onChange={e=>{setMode(e.target.value);setResult(null)}}><option value="case">Case</option><option value="cohort">Cohort</option></select></label><label>Cohort<select disabled value="winter"><option value="winter">Winter (toy cohort)</option></select></label><label>Case<select value={caseId} disabled={mode!=='case'} onChange={e=>setCaseId(e.target.value)}>{options?.cases.map(v=><option key={v} value={v}>{v}</option>)}</select></label><label>Output ROI<select value={roi} onChange={e=>setRoi(e.target.value)}>{options?.output_rois.map(v=><option key={v} value={v}>{v}</option>)}</select></label><label>輸入擾動<select disabled><option>q700 | north | +0.5σ (cached)</option></select></label></div><button onClick={()=>query()} disabled={!options||busy}>{busy?'讀取中…':'讀取 Cache 並分析'}</button><p className="hint">不執行任何 EDM forward；若 cache 缺少組合，API 應明確拒絕。</p></section>
    {error&&<section className="error" role="alert">{error}</section>}
    {metric&&<section><h2>Case：{result.case_id} / ROI：{result.output_roi}</h2><div className="cards"><article><span>Mean shift (mm/day)</span><strong>{fmt(metric.delta_mean)}</strong></article><article><span>Spread shift (sample SD)</span><strong>{fmt(metric.delta_sd)}</strong></article><article><span>1D Wasserstein W1</span><strong>{fmt(metric.w1)}</strong></article><article><span>Tail probability shift</span><strong>{fmt(metric.delta_tail_probability*100,1)} pp</strong></article></div><p><b>Variance identity：</b> ΔVariance={fmt(metric.delta_variance)} = Var(member response) {fmt(metric.response_variance)} + 2Cov(base,response) {fmt(metric.baseline_response_cov2)} (mm/day)²</p><MiniLine values={result.step_w1} label="Step-wise distribution shift (W1)"/><h3>Layer × Step — toy compact feature distance</h3><div className="heatmap">{result.layer_step_distance.map((row,l)=><div className="hrow" key={l} style={{gridTemplateColumns:`110px repeat(${row.length},minmax(20px,1fr))`}}><span>{result.layer_ids[l]}</span>{row.map((v,k)=><div key={k} title={`layer=${l}, step=${k}, distance=${v.toFixed(3)}`} style={{background:`rgba(13,148,136,${Math.max(.1,Math.min(1,v))})`}}/>)}</div>)}</div><p className="hint">Layer distance 是 representation difference，不能當作因果性重要程度。</p></section>}
    {cohort&&<section><h2>Cohort：{result.cohort}（{cohort.n_cases} 個 cases）</h2><div className="cards"><article><span>Median ΔMean</span><strong>{fmt(cohort.delta_mean.median)}</strong></article><article><span>Median ΔSpread</span><strong>{fmt(cohort.delta_sd.median)}</strong></article><article><span>Mean 增加案例比例</span><strong>{fmt(cohort.share_mean_increased*100,0)}%</strong></article><article><span>Spread 增加案例比例</span><strong>{fmt(cohort.share_spread_increased*100,0)}%</strong></article></div><p>ΔSpread Q25–Q75: {fmt(cohort.delta_sd.q25)} ～ {fmt(cohort.delta_sd.q75)} mm/day</p><MiniLine values={cohort.step_w1_median} label="Cohort per-case median Step W1"/><table><thead><tr><th>Case</th><th>ΔMean</th><th>ΔSpread</th></tr></thead><tbody>{result.cases.map(c=><tr key={c.case_id}><td>{c.case_id}</td><td>{fmt(c.delta_mean)}</td><td>{fmt(c.delta_sd)}</td></tr>)}</tbody></table></section>}
    <footer>Prototype scientific contracts and synthetic data. True GPU adapter still requires your trained model, dataset and inference scripts.</footer>
  </main>
}

createRoot(document.getElementById('root')).render(<App />)
