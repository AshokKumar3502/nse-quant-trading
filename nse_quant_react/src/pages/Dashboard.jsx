import { useEffect, useState } from "react";
import { ArrowUpRight, LockKeyhole } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { REPORTS } from "../components/Layout";
import MetricCard from "../components/MetricCard";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Dashboard() {
  const [reports,setReports]=useState({}); const [error,setError]=useState("");
  const { session } = useAuth();
  const navigate=useNavigate();
  useEffect(()=>{
    if (!session?.access_token) return;
    setError("");
    api.reports(session.access_token)
      .then(data=>setReports(normalize(data)))
      .catch(e=>setError(e.message));
  },[session?.access_token]);
  const normalize = (data) => {
    const list = Array.isArray(data) ? data : (Array.isArray(data?.reports) ? data.reports : []);
    return Object.fromEntries(list.map(x => [
      x.name || x.report || x.key,
      x.rows || x.data || []
    ]));
  };
  const count = key => Array.isArray(reports[key]) ? reports[key].length : (reports[key]?.count ?? 0);
  return <div className="page">
    <section className="hero"><div><span>MARKET RESEARCH TERMINAL</span><h1>Smart Data. Smarter Trades.</h1><p>Quantitative signals, stock research and evidence-driven market analysis.</p></div><div className="live">● ENGINE ACTIVE</div></section>
    {error && <div className="alert error">{error}<br/><small>Make sure your FastAPI backend exposes the report endpoints.</small></div>}
    <div className="metric-grid">
      <MetricCard label="All Scores" value={count("All Scores")} sub="Complete scoring" tone="blue"/>
      <MetricCard label="Swing" value={count("Swing Candidates")} sub="Opportunities" tone="green"/>
      <MetricCard label="Position" value={count("Position Selection")} sub="Position setups" tone="gold"/>
      <MetricCard label="Historical" value={count("Historical Setup Stats")} sub="Setup evidence" tone="cyan"/>
      <MetricCard label="Next-Day" value={count("Next-Day Candidates") || "PRO"} sub="Premium research" tone="purple"/>
      <MetricCard label="Overlap" value={count("High-Priority Overlap") || "PRO"} sub="Premium research" tone="red"/>
    </div>
    <div className="section-title"><div><span>RESEARCH WORKSPACE</span><h2>Reports</h2></div></div>
    <div className="report-grid">{REPORTS.map(r=><button className="report-card" key={r.key} onClick={()=>navigate(`/reports/${encodeURIComponent(r.key)}`)}>
      <div className="report-top"><b>{r.free?"▣":"✦"}</b>{r.free?null:<span className="pro">PRO</span>}</div><h3>{r.label}</h3><p>{r.free?"Available in core research":"Premium research feature"}</p><strong>{count(r.key) || "—"} <ArrowUpRight size={15}/></strong>
    </button>)}</div>
    <div className="mobile-note">Tip: double-click any stock row to open its complete analysis.</div>
  </div>;
}