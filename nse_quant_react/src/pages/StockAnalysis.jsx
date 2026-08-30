import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { ArrowLeft, ChevronDown, ChevronUp, LockKeyhole } from "lucide-react";
import { api } from "../services/api";
import StockOverview from "../components/StockOverview";
import { useAuth } from "../context/AuthContext";

function value(v) {
  if (v === null || v === undefined || v === "") return "—";
  return typeof v === "object" ? JSON.stringify(v) : String(v);
}

function RecordTable({ rows }) {
  if (!rows?.length) return <div className="empty">No records returned for this section.</div>;
  const columns = Array.from(new Set(rows.flatMap(row => Object.keys(row))));
  return (
    <div className="table-wrap detail-table">
      <table>
        <thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {columns.map(c => <td key={c}>{value(row[c])}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function StockAnalysis() {
  const { symbol } = useParams();
  const navigate = useNavigate();
  const { session } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [expanded, setExpanded] = useState(false);
  const [openReports, setOpenReports] = useState({});

  useEffect(() => {
    if (!session?.access_token) return;
    setLoading(true);
    setError("");
    api.stock(symbol, session.access_token)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, [symbol, session?.access_token]);

  if (loading) return <div className="page"><div className="loading-line">Loading {symbol} analysis…</div></div>;

  if (error) return (
    <div className="page">
      <button className="back-btn" onClick={() => navigate(-1)}><ArrowLeft size={16}/> Back</button>
      <div className="alert error">{error}</div>
    </div>
  );

  const reports = data?.reports || [];
  const allRows = reports.flatMap(r => r.rows || []);
  const overview = data?.overview || {};

  const toggleReport = (name) => {
    setOpenReports(prev => ({ ...prev, [name]: !prev[name] }));
  };

  return (
    <div className="page">
      <button className="back-btn" onClick={() => navigate(-1)}>
        <ArrowLeft size={16}/> Back to report
      </button>

      <section className="stock-head">
        <div>
          <span>STOCK ANALYSIS</span>
          <h1>{String(symbol).toUpperCase()}</h1>
          <p>Complete research data collected from every available report.</p>
        </div>
        <div className="stock-signal">
          {data?.signal || overview?.SIGNAL || overview?.BIAS || "RESEARCH"}
        </div>
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <span>QUICK OVERVIEW</span>
            <h2>Key market data</h2>
          </div>
        </div>
        <StockOverview data={{ overview }} />
      </section>

      <section className="panel">
        <div className="panel-head">
          <div>
            <span>COMPLETE RESEARCH DATA</span>
            <h2>{allRows.length.toLocaleString()} stock records</h2>
          </div>
          <button className="expand-btn" onClick={() => setExpanded(v => !v)}>
            {expanded ? <><ChevronUp size={15}/> Collapse all</> : <><ChevronDown size={15}/> View more details</>}
          </button>
        </div>

        {!reports.length && (
          <div className="empty">
            No stock records were returned by the backend.
          </div>
        )}

        {reports.map(report => {
          const locked = report.locked;
          const rows = report.rows || [];
          const isOpen = expanded || openReports[report.report];

          return (
            <div className="stock-report-section" key={report.report}>
              <button
                className="stock-report-title"
                onClick={() => !locked && toggleReport(report.report)}
              >
                <span>
                  {report.premium ? "✦" : "▣"} {report.report}
                  {report.premium && <em>PRO</em>}
                </span>
                <span className={locked ? "locked-label" : ""}>
                  {locked ? <><LockKeyhole size={14}/> Premium</> : `${rows.length} row${rows.length === 1 ? "" : "s"} ${isOpen ? "▲" : "▼"}`}
                </span>
              </button>

              {locked ? (
                <div className="locked-panel">
                  <LockKeyhole size={18}/>
                  <div><b>Premium report</b><span>Subscribe to view this stock's complete premium data.</span></div>
                </div>
              ) : isOpen ? (
                <RecordTable rows={rows}/>
              ) : (
                <div className="section-preview">
                  {rows.length ? `Click to view all ${rows.length} record${rows.length === 1 ? "" : "s"} and every available column.` : "No matching records."}
                </div>
              )}
            </div>
          );
        })}
      </section>
    </div>
  );
}
