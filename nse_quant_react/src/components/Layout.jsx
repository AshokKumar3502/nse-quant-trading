import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { BarChart3, ChevronDown, LogOut, Menu, Search, ShieldCheck, X } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export const REPORTS = [
  { key: "All Scores", label: "All Scores", free: true },
  { key: "Swing Candidates", label: "Swing Candidates", free: true },
  { key: "Historical Setup Stats", label: "Historical Setup Stats", free: true },
  { key: "Position Selection", label: "Position Selection", free: true },
  { key: "Next-Day Candidates", label: "Next-Day Candidates", free: false },
  { key: "High-Priority Overlap", label: "High-Priority Overlap", free: false },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [symbol, setSymbol] = useState("");

  const goStock = (e) => {
    e.preventDefault();
    const value = symbol.trim().toUpperCase();
    if (value) { navigate(`/stock/${encodeURIComponent(value)}`); setSymbol(""); setMobileOpen(false); }
  };

  const links = REPORTS.map(r => ({ ...r, path: `/reports/${encodeURIComponent(r.key)}` }));

  return (
    <div className="app-shell">
      <aside className={`sidebar ${mobileOpen ? "open" : ""}`}>
        <div className="brand">
          <div className="brand-mark">↗</div>
          <div><strong>NSE QUANT</strong><span>Smart Data. Smarter Trades.</span></div>
          <button className="mobile-close" onClick={() => setMobileOpen(false)}><X size={18}/></button>
        </div>

        <nav className="side-nav">
          <div className="nav-caption">WORKSPACE</div>
          <NavLink to="/" end onClick={() => setMobileOpen(false)}>⌂ <span>Dashboard</span></NavLink>
          <div className="nav-caption">RESEARCH REPORTS</div>
          {links.map(r => (
            <NavLink key={r.key} to={r.path} onClick={() => setMobileOpen(false)}>
              <span>{r.free ? "▣" : "✦"}</span><span>{r.label}</span>{!r.free && <small>PRO</small>}
            </NavLink>
          ))}
        </nav>

        <div className="side-bottom">
          <div className="user-mini"><div className="avatar">{(user?.email || "U")[0].toUpperCase()}</div><div><b>{user?.email}</b><span>Authenticated</span></div></div>
          <button className="logout-btn" onClick={async () => { await logout(); navigate("/login"); }}><LogOut size={16}/> Logout</button>
        </div>
      </aside>

      {mobileOpen && <div className="mobile-overlay" onClick={() => setMobileOpen(false)} />}

      <main className="main">
        <header className="topbar">
          <button className="menu-btn" onClick={() => setMobileOpen(true)}><Menu size={21}/></button>
          <form className="global-search" onSubmit={goStock}>
            <Search size={17}/>
            <input value={symbol} onChange={e => setSymbol(e.target.value)} placeholder="Search stock symbol, e.g. RELIANCE" />
            <button type="submit">Analyze</button>
          </form>
          <div className="top-status"><ShieldCheck size={16}/> Secure Research</div>
        </header>
        <Outlet />
      </main>
    </div>
  );
}