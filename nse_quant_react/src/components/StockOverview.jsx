export default function StockOverview({ data }) {
  const fields = data?.overview || {};
  const entries = Object.entries(fields);
  if (!entries.length) return <div className="empty">No summary fields found for this stock.</div>;
  return <div className="overview-grid">{entries.map(([k,v]) =>
    <div className="data-card" key={k}><span>{k.replaceAll("_"," ")}</span><strong>{v == null ? "—" : String(v)}</strong></div>
  )}</div>;
}