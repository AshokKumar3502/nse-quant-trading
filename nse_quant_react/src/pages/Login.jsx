import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { TrendingUp } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function Login() {
  const { login, supabase } = useAuth();
  const navigate = useNavigate();
  const [email,setEmail]=useState(""); const [password,setPassword]=useState(""); const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  async function submit(e) { e.preventDefault(); setError(""); setBusy(true); try { await login(email.trim(), password); navigate("/"); } catch(err) { setError(err.message); } finally { setBusy(false); } }
  return <AuthShell title="Welcome back" subtitle="Sign in to your quantitative research terminal.">
    {!supabase && <div className="alert error">Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to .env.</div>}
    <form onSubmit={submit} className="auth-form">
      <label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com"/></label>
      <label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required placeholder="••••••••"/></label>
      {error && <div className="alert error">{error}</div>}
      <button className="primary-btn" disabled={busy || !supabase}>{busy ? "Signing in..." : "Sign in →"}</button>
    </form>
    <p className="auth-switch">New here? <Link to="/register">Create an account</Link></p>
  </AuthShell>;
}

export function AuthShell({ title, subtitle, children }) {
  return <div className="auth-page"><div className="auth-panel"><div className="auth-brand"><div className="brand-mark"><TrendingUp/></div><div><b>NSE QUANT</b><span>Smart Data. Smarter Trades.</span></div></div><div className="auth-kicker">NSE QUANTITATIVE RESEARCH</div><h1>{title}</h1><p>{subtitle}</p>{children}</div></div>;
}