import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, Search } from "lucide-react";
import ReportTable from "../components/ReportTable";
import { api } from "../services/api";
import { useAuth } from "../context/AuthContext";

export default function Reports() {
  const { report }=useParams(); const name=decodeURIComponent(report||""); const navigate=useNavigate();
  const { session } = useAuth();
  const [rows,setRows]=useState([]); const [loading,setLoading]=useState(true); const [error,setError]=useState("");
  useEffect(()=>{
    if (!session?.access_token) return;
    setLoading(true);
    setError("");
    api.report(name, session.access_token)
      .then(data=>setRows(Array.isArray(data)?data:(data?.rows||data?.data||[])))
      .catch(e=>setError(e.message))
      .finally(()=>setLoading(false));
  },[name, session?.access_token]);
  return <div className="page"><button className="back-btn" onClick={()=>navigate("/")}><ArrowLeft size={16}/> Dashboard</button>
    <section className="report-head"><div><span>RESEARCH REPORT</span><h1>{name}</h1><p>Double-click a stock row for complete analysis.</p></div><div className="report-count">{rows.length.toLocaleString()} rows</div></section>
    {error&&<div className="alert error">{error}</div>}{loading?<div className="loading-line">Loading report…</div>:<ReportTable rows={rows}/>}
  </div>;
}