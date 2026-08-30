export default function MetricCard({ label, value, sub, tone = "" }) {
  return <div className={`metric-card ${tone}`}><span>{label}</span><strong>{value}</strong><small>{sub}</small></div>;
}