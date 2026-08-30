import { useNavigate } from "react-router-dom";

function findSymbol(row) {
  const key = Object.keys(row).find(k => ["symbol","ticker","stock","security"].includes(k.toLowerCase()) || k.toLowerCase().includes("symbol"));
  return key ? String(row[key]) : "";
}

export default function ReportTable({ rows = [] }) {
  const navigate = useNavigate();
  if (!rows.length) return <div className="empty">No data available for this report.</div>;
  const columns = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead><tr>{columns.map(c => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{rows.slice(0, 1000).map((row, i) => {
          const symbol = findSymbol(row);
          return <tr key={i} onDoubleClick={() => symbol && navigate(`/stock/${encodeURIComponent(symbol)}`)} title={symbol ? "Double-click to open full stock analysis" : ""}>
            {columns.map(c => <td key={c}>{row[c] == null ? "—" : String(row[c])}</td>)}
          </tr>;
        })}</tbody>
      </table>
    </div>
  );
}