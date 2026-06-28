import { useEffect, useMemo, useState } from "react";
import {
  ArrowRight, Brain, ChartLineUp, CheckCircle, Clock, Database,
  GlobeHemisphereEast, House, ListChecks, MagnifyingGlass, MetaLogo,
  Scales, ShieldCheck, SlidersHorizontal, UserFocus, WarningCircle, X,
} from "@phosphor-icons/react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

const API = window.location.port === "5173" ? "http://127.0.0.1:8000/api" : "/api";
const COLORS = ["#cf4249", "#e89429", "#258e87", "#3478c8", "#8394aa", "#b5c0ce"];

const nav = [
  ["overview", "Command Center", House],
  ["queue", "Review Queue", ListChecks],
  ["policy", "Policy Reasoning", Scales],
  ["metrics", "Metric Diagnosis", ChartLineUp],
  ["feedback", "Feedback", UserFocus],
  ["mandarin", "Mandarin Lab", GlobeHemisphereEast],
];

async function get(path, options) {
  const response = await fetch(`${API}${path}`, options);
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

const fmt = new Intl.NumberFormat("en-US");
const pct = (value) => `${Math.round((value || 0) * 100)}%`;
const short = (value, length = 120) => value?.length > length ? `${value.slice(0, length)}…` : value || "—";

function Pill({ children, tone = "neutral" }) {
  return <span className={`pill ${tone}`}>{children}</span>;
}

function Empty({ title, detail }) {
  return <div className="empty"><Database size={24}/><strong>{title}</strong><span>{detail}</span></div>;
}

function SourceStrip({ sources = [] }) {
  const icons = { ftc: Scales, cfpb: Database, meta: MetaLogo };
  return <section className="surface provenance">
    <div className="section-title">Source provenance <span>Every metric traces to public records.</span></div>
    <div className="source-grid">
      {sources.map((source) => {
        const Icon = icons[source.key] || Database;
        return <div className="source" key={source.key}>
          <div className={`source-icon ${source.key}`}><Icon size={25} weight="duotone"/></div>
          <div><strong>{source.name}</strong><small><i className={source.status}/>{source.status === "optional" ? "Optional enrichment" : `${fmt.format(source.records)} records`}</small></div>
          <span>{source.detail}</span>
        </div>;
      })}
    </div>
  </section>;
}

function Kpis({ overview }) {
  const data = [
    ["Total real records", overview.total_real_records, "FTC + CFPB + Meta"],
    ["Cases analyzed", overview.cases_analyzed, "Deterministic workflow"],
    ["High-risk detections", overview.high_risk_cases, pct(overview.high_risk_rate)],
    ["Under review", overview.review_queue_size, "Human judgment retained"],
    ["Review time saved", overview.estimated_minutes_saved, "Estimated minutes"],
  ];
  return <section className="surface kpis">{data.map(([label, value, note]) => <div className="kpi" key={label}><span>{label}</span><strong>{fmt.format(value || 0)}</strong><small>{note}</small></div>)}</section>;
}

function RiskTable({ cases, onSelect, compact = false }) {
  if (!cases.length) return <Empty title="No cases in this view" detail="Adjust filters or run the ingestion pipeline."/>;
  return <div className="table-wrap"><table className="risk-table">
    <thead><tr><th>Source</th><th>Case</th><th>Risk category</th><th>Severity</th>{!compact && <th>Suggested action</th>}<th/></tr></thead>
    <tbody>{cases.map((item) => <tr key={item.case_id} onClick={() => onSelect(item.case_id)} tabIndex={0} onKeyDown={(event) => event.key === "Enter" && onSelect(item.case_id)}>
      <td><Pill tone={item.source.toLowerCase()}>{item.source}</Pill></td>
      <td><strong>{item.case_id}</strong><span>{short(item.case_text, compact ? 58 : 100)}</span></td>
      <td>{item.risk_category}</td>
      <td><Pill tone={item.severity}>{item.severity}</Pill></td>
      {!compact && <td>{item.recommended_action}</td>}
      <td><ArrowRight size={16}/></td>
    </tr>)}</tbody>
  </table></div>;
}

function CaseDrawer({ caseId, onClose, onFeedback }) {
  const [detail, setDetail] = useState(null);
  const [decision, setDecision] = useState("escalate");
  const [notes, setNotes] = useState("");
  const [saved, setSaved] = useState(false);
  useEffect(() => { setDetail(null); get(`/cases/${caseId}`).then(setDetail); }, [caseId]);
  const submit = async () => {
    await get("/feedback", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ case_id: caseId, decision, notes }) });
    setSaved(true); onFeedback?.();
  };
  return <div className="drawer-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
    <aside className="drawer" aria-label="Case review detail">
      <header><div><span>Investigation Desk</span><h2>{caseId}</h2></div><button className="icon-button" onClick={onClose}><X size={20}/></button></header>
      {!detail ? <Empty title="Loading case evidence" detail="Reading the local risk mart."/> : <>
        <div className="case-hero"><div><Pill tone={detail.source.toLowerCase()}>{detail.source}</Pill><Pill tone={detail.severity}>{detail.severity}</Pill></div><div className="score"><span>Risk score</span><strong>{Math.round(detail.risk_score * 100)}</strong><small>/ 100</small></div></div>
        <section className="drawer-section"><h3>Original public-source text</h3><p className="case-copy">{detail.case_text}</p><div className="privacy-line"><ShieldCheck size={16}/> CFPB-published text is scrubbed; company and ZIP fields are excluded from this view.</div></section>
        <section className="drawer-section"><h3>AI evidence extraction</h3>{detail.evidence.length ? <div className="evidence-list">{detail.evidence.map((item, index) => <div key={`${item.term}-${index}`}><Pill tone="evidence">{item.type.replaceAll("_", " ")}</Pill><strong>{item.term}</strong><span>{item.category || "Operational signal"}</span></div>)}</div> : <Empty title="No explicit phrase match" detail="The current score is driven by source/product priors and remains reviewable."/>}</section>
        <section className="drawer-section"><h3>Policy reasoning</h3><p>{detail.policy_rationale}</p><div className="policy-list">{detail.policies.map((policy) => <a key={policy.rule_id} href={policy.source_url} target="_blank" rel="noreferrer"><Scales size={18}/><span><strong>{policy.rule_id} · {policy.title}</strong><small>{policy.source_name}</small></span><ArrowRight size={16}/></a>)}</div></section>
        <section className="decision"><div><span>Recommended action</span><strong>{detail.recommended_action}</strong><small>Confidence {pct(detail.confidence)} · {detail.needs_human_review ? "Human review required" : "Eligible for automated routing"}</small></div></section>
        <section className="drawer-section"><h3>Human reviewer feedback</h3><div className="decision-grid">{["approve", "reject", "escalate", "wrong category", "false positive", "false negative"].map(value => <button className={decision === value ? "selected" : ""} onClick={() => setDecision(value)} key={value}>{value}</button>)}</div><textarea placeholder="Review note (optional)" value={notes} onChange={(e) => setNotes(e.target.value)}/><button className="primary" onClick={submit}>{saved ? "Decision saved" : "Save reviewer decision"}</button></section>
      </>}
    </aside>
  </div>;
}

function Overview({ overview, metrics, cases, mandarin, onSelect, navigate }) {
  return <>
    <PageHeader title="Command Center" subtitle="Executive overview of commercial ads risk exposure and operations." updated={overview.last_updated}/>
    <SourceStrip sources={overview.sources}/><Kpis overview={overview}/>
    <div className="two-col">
      <section className="surface chart"><div className="section-title">Risk category distribution <span>Share of scored cases</span></div>
        <ResponsiveContainer width="100%" height={245}><PieChart><Pie data={metrics.category_distribution} dataKey="cases" nameKey="risk_category" innerRadius={57} outerRadius={84} paddingAngle={1}>{metrics.category_distribution.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]}/>)}</Pie><Tooltip/><Legend layout="vertical" align="right" verticalAlign="middle" formatter={(value) => <span className="legend-label">{value}</span>}/></PieChart></ResponsiveContainer>
      </section>
      <section className="surface chart"><div className="section-title">Anomaly trend <span>Public cases by received date</span></div>
        {metrics.anomalies.length ? <ResponsiveContainer width="100%" height={245}><AreaChart data={metrics.anomalies}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date" tick={{fontSize: 11}} minTickGap={28}/><YAxis tick={{fontSize: 11}}/><Tooltip/><Area type="monotone" dataKey="cases" stroke="#356da7" fill="#dce8f5" strokeWidth={2}/></AreaChart></ResponsiveContainer> : <Empty title="No timeline available" detail="Dated cases appear after ingestion."/>}
      </section>
    </div>
    <div className="bottom-grid">
      <section className="surface queue-preview"><div className="section-title">Review queue <button onClick={() => navigate("queue")}>Open full queue <ArrowRight size={15}/></button></div><RiskTable cases={cases.slice(0, 6)} compact onSelect={onSelect}/></section>
      <section className="surface mandarin-preview"><div className="section-title">Mandarin Risk Lab <span>Bilingual detection layer</span></div><div className="term-head"><span>术语</span><span>Pinyin</span><span>English gloss</span></div>{mandarin.terms.slice(0, 6).map(term => <div className="term-row" key={term.term}><strong>{term.term}</strong><span>{term.pinyin}</span><span>{term.gloss}</span></div>)}<button className="text-link" onClick={() => navigate("mandarin")}>Open Mandarin Lab <ArrowRight size={15}/></button></section>
    </div>
  </>;
}

function PageHeader({ title, subtitle, updated }) {
  return <div className="page-header"><div><h1>{title}</h1><p>{subtitle}</p></div>{updated && <div className="updated"><Clock size={21}/><span>Data updates after ingestion<small>Last scored {new Date(updated).toLocaleString()}</small></span></div>}</div>;
}

function QueuePage({ cases, onSelect, refresh }) {
  const [search, setSearch] = useState("");
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [language, setLanguage] = useState("");
  const [source, setSource] = useState("");
  const [action, setAction] = useState("");
  const categories = [...new Set(cases.map(item => item.risk_category))].sort();
  const filtered = cases.filter(item => (!search || `${item.case_text} ${item.case_id}`.toLowerCase().includes(search.toLowerCase())) && (!severity || item.severity === severity) && (!category || item.risk_category === category) && (!language || item.language === language) && (!source || item.source === source) && (!action || item.recommended_action === action));
  return <><PageHeader title="Case Review Queue" subtitle="Search, triage, and document decisions on public-source cases."/><section className="surface filters"><label><MagnifyingGlass size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search case text or ID"/></label><select value={category} onChange={e => setCategory(e.target.value)}><option value="">All categories</option>{categories.map(value => <option key={value}>{value}</option>)}</select><select value={severity} onChange={e => setSeverity(e.target.value)}><option value="">All severities</option>{["critical","high","medium","low"].map(value => <option key={value}>{value}</option>)}</select><select value={language} onChange={e => setLanguage(e.target.value)}><option value="">All languages</option>{["en","zh","mixed"].map(value => <option key={value}>{value}</option>)}</select><select value={source} onChange={e => setSource(e.target.value)}><option value="">All sources</option>{["CFPB","Meta"].map(value => <option key={value}>{value}</option>)}</select><select value={action} onChange={e => setAction(e.target.value)}><option value="">All actions</option>{["approve","soft reject","hard reject","escalate to human review"].map(value => <option key={value}>{value}</option>)}</select><button onClick={refresh}><SlidersHorizontal size={17}/> Refresh</button></section><section className="surface full-table"><div className="section-title">Prioritized cases <span>{fmt.format(filtered.length)} visible</span></div><RiskTable cases={filtered} onSelect={onSelect}/></section></>;
}

function LlmComparison({ comparison = {} }) {
  const cases = comparison.cases || [];
  const available = comparison.llm_available;
  return <section className="surface llm-compare">
    <div className="section-title">Rule engine vs. LLM <span>{available ? `${comparison.llm_model} second opinion on ${cases.length} sampled cases` : "Deterministic scoring is the default"}</span></div>
    <div className={`llm-banner ${available ? "on" : "off"}`}><Brain size={20}/><div><strong>{available ? "Optional LLM comparison active" : "LLM comparison is optional and currently off"}</strong><p>{comparison.note}</p></div>{available && comparison.category_agreement_rate != null && <span className="agree-pill">{pct(comparison.category_agreement_rate)} category agreement</span>}</div>
    {!cases.length ? <Empty title="No sampled cases yet" detail="Build the data mart with make ingest && make transform to populate the comparison sample."/> :
      <div className="table-wrap"><table className="risk-table compare-table">
        <thead><tr><th>Case</th><th>Rule category → action</th><th>LLM category → action</th><th>Match</th></tr></thead>
        <tbody>{cases.map((row) => {
          const det = row.deterministic || {};
          const llm = row.llm;
          const match = row.category_agreement;
          return <tr key={row.case_id}>
            <td><strong>{row.case_id}</strong><span>{short(row.excerpt, 64)}</span></td>
            <td>{det.risk_category}<small> → {det.recommended_action}</small></td>
            <td>{llm ? <>{llm.risk_category}<small> → {llm.recommended_action}</small></> : <em>not run (no key)</em>}</td>
            <td>{match == null ? "—" : <Pill tone={match ? "approve" : "high"}>{match ? "agree" : "differs"}</Pill>}</td>
          </tr>;
        })}</tbody>
      </table></div>}
  </section>;
}

function MetricsPage({ metrics, llmComparison }) {
  const evaluation = metrics.evaluation || {};
  return <><PageHeader title="Risk Metric Diagnosis" subtitle="Diagnose category mix, risk-driving features, market differences, spikes, and decision coverage."/>
    <div className="metric-grid">
      <section className="surface wide-chart"><div className="section-title">Risk spikes <span>Z-score flags on dated case volume</span></div><ResponsiveContainer width="100%" height={270}><AreaChart data={metrics.anomalies}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="date"/><YAxis/><Tooltip/><Area type="monotone" dataKey="cases" stroke="#2d679e" fill="#dfeaf5"/><Area type="monotone" dataKey="z_score" stroke="#cf4249" fill="transparent"/></AreaChart></ResponsiveContainer></section>
      <section className="surface"><div className="section-title">Feature lift <span>High-risk vs all scored cases</span></div><div className="feature-table">{metrics.feature_lift.map((row, i) => <div key={row.term}><b>{i + 1}</b><strong>{row.term}</strong><span>{row.high_risk_cases} high-risk</span><Pill tone={row.lift >= 1.5 ? "high" : "neutral"}>{row.lift}×</Pill></div>)}</div></section>
      <section className="surface"><div className="section-title">Language comparison <span>Risk rate by detected language</span></div><ResponsiveContainer width="100%" height={240}><BarChart data={metrics.language_comparison}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="language"/><YAxis tickFormatter={pct}/><Tooltip formatter={pct}/><Bar dataKey="high_risk_rate" fill="#3478c8" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></section>
      <section className="surface"><div className="section-title">Market comparison <span>Top CFPB states by case volume</span></div><ResponsiveContainer width="100%" height={240}><BarChart data={metrics.market_comparison}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="state"/><YAxis/><Tooltip/><Bar dataKey="cases" fill="#258e87" radius={[4,4,0,0]}/></BarChart></ResponsiveContainer></section>
      <section className="surface"><div className="section-title">AI evaluation <span>Labels never fabricated</span></div><div className="eval-grid"><div><span>Auto-decision coverage</span><strong>{pct(evaluation.auto_decision_coverage)}</strong></div><div><span>Escalation rate</span><strong>{pct(evaluation.escalation_rate)}</strong></div><div><span>Evidence completeness</span><strong>{pct(evaluation.evidence_extraction_completeness)}</strong></div><div><span>Review minutes saved</span><strong>{fmt.format(evaluation.estimated_review_minutes_saved || 0)}</strong></div><div><span>Precision / Recall / F1</span><strong>{evaluation.f1 == null ? "Awaiting labels" : `${pct(evaluation.precision)} / ${pct(evaluation.recall)} / ${pct(evaluation.f1)}`}</strong></div></div></section>
    </div>
    <LlmComparison comparison={llmComparison}/>
  </>;
}

function PolicyPage({ policies }) {
  return <><PageHeader title="Policy Reasoning" subtitle="Short local summaries with source links and retrieval metadata—not copied policy text."/><section className="surface policy-catalog">{policies.map(policy => <a href={policy.source_url} target="_blank" rel="noreferrer" key={policy.rule_id}><div><Pill tone="policy">{policy.rule_id}</Pill><h3>{policy.title}</h3><p>{policy.summary}</p><small>{policy.category} · Checked {policy.last_checked}</small></div><ArrowRight size={20}/></a>)}</section></>;
}

function MandarinPage({ mandarin }) {
  return <><PageHeader title="Mandarin Risk Lab" subtitle="Context-aware bilingual signals for euphemisms, pinyin, homophones, and off-platform diversion."/><section className="surface callout"><Brain size={24}/><div><strong>Why literal matching is not enough</strong><p>{mandarin.note}</p></div></section><section className="surface full-table"><div className="section-title">Bilingual signal taxonomy <span>{mandarin.terms.length} curated terms</span></div><div className="mandarin-table"><div><b>Term</b><b>Pinyin</b><b>English gloss</b><b>Risk mapping</b></div>{mandarin.terms.map(term => <div key={term.term}><strong>{term.term}</strong><span>{term.pinyin}</span><span>{term.gloss}</span><span>{term.category}</span></div>)}</div></section><section className="surface examples"><div className="section-title">Examples in current real records</div>{mandarin.real_record_examples.length ? mandarin.real_record_examples.map(row => <p key={row.case_id}>{row.case_id}: {row.excerpt}</p>) : <Empty title="No Mandarin records in the current public ingestion" detail="The taxonomy remains visible, but the app does not invent examples."/>}</section></>;
}

function FeedbackPage({ evaluation }) {
  return <><PageHeader title="Human Feedback" subtitle="Reviewer decisions are stored locally and unlock quality metrics without manufacturing labels."/><section className="surface callout"><CheckCircle size={26}/><div><strong>{evaluation.labeled_cases || 0} cases labeled</strong><p>{evaluation.label_note}</p></div></section><section className="surface"><div className="section-title">Evaluation status</div><div className="eval-grid"><div><span>Precision</span><strong>{evaluation.precision == null ? "—" : pct(evaluation.precision)}</strong></div><div><span>Recall</span><strong>{evaluation.recall == null ? "—" : pct(evaluation.recall)}</strong></div><div><span>F1</span><strong>{evaluation.f1 == null ? "—" : pct(evaluation.f1)}</strong></div><div><span>Label coverage</span><strong>{evaluation.scored_cases ? pct((evaluation.labeled_cases || 0) / evaluation.scored_cases) : "—"}</strong></div></div></section></>;
}

export function App() {
  const [page, setPage] = useState("overview");
  const [data, setData] = useState({ overview: null, metrics: null, cases: [], policies: [], mandarin: { terms: [], real_record_examples: [] }, llmComparison: { llm_available: false, cases: [] } });
  const [selectedCase, setSelectedCase] = useState(null);
  const [error, setError] = useState("");
  const load = async () => {
    try {
      const [overview, metrics, cases, policies, mandarin, llmComparison] = await Promise.all([get("/overview"), get("/metrics"), get("/cases?limit=500"), get("/policies"), get("/mandarin"), get("/llm-comparison")]);
      setData({ overview, metrics, cases, policies, mandarin, llmComparison }); setError("");
    } catch (err) { setError(err.message); }
  };
  useEffect(() => { load(); }, []);
  useEffect(() => { window.scrollTo({ top: 0, behavior: "instant" }); }, [page]);
  const currentLabel = useMemo(() => nav.find(([key]) => key === page)?.[1], [page]);
  if (error) return <main className="boot-error"><WarningCircle size={34}/><h1>Command Center needs its data mart</h1><p>{error}</p><code>make ingest && make transform && make app</code></main>;
  if (!data.overview) return <main className="boot-error"><ShieldCheck size={36}/><h1>Loading AdShield AI</h1><p>Connecting to the local public-data risk mart.</p></main>;
  let content;
  if (page === "overview") content = <Overview {...data} onSelect={setSelectedCase} navigate={setPage}/>;
  else if (page === "queue") content = <QueuePage cases={data.cases} onSelect={setSelectedCase} refresh={load}/>;
  else if (page === "metrics") content = <MetricsPage metrics={data.metrics} llmComparison={data.llmComparison}/>;
  else if (page === "policy") content = <PolicyPage policies={data.policies}/>;
  else if (page === "mandarin") content = <MandarinPage mandarin={data.mandarin}/>;
  else content = <FeedbackPage evaluation={data.metrics.evaluation || {}}/>;
  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark"><ShieldCheck size={31} weight="duotone"/></div><div><strong>AdShield AI</strong><span>Commercial Ads<br/>Risk Governance Copilot</span></div></div><div className="real-only"><i/>Real public data only</div><nav>{nav.map(([key, label, Icon]) => <button key={key} className={page === key ? "active" : ""} onClick={() => setPage(key)}><Icon size={20}/><span>{label}</span></button>)}</nav><div className="sidebar-foot"><ShieldCheck size={18}/><span>Deterministic fallback<br/><small>LLM optional</small></span></div></aside>
    <main className="content" aria-label={currentLabel}>{content}</main>
    {selectedCase && <CaseDrawer caseId={selectedCase} onClose={() => setSelectedCase(null)} onFeedback={load}/>}
  </div>;
}
