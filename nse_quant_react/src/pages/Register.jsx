import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthShell } from "./Login";
import { useAuth } from "../context/AuthContext";

export default function Register() {
  const { register, supabase } = useAuth(); const navigate=useNavigate();
  const [email,setEmail]=useState(""); const [password,setPassword]=useState(""); const [confirm,setConfirm]=useState(""); const [message,setMessage]=useState(""); const [error,setError]=useState(""); const [busy,setBusy]=useState(false);
  async function submit(e) { e.preventDefault(); setError(""); setMessage(""); if(password.length<8){setError("Password must be at least 8 characters.");return;} if(password!==confirm){setError("Passwords do not match.");return;} setBusy(true); try { const data=await register(email.trim(),password); setMessage(data.session ? "Account created." : "Account created. Check your email to confirm your account."); if(data.session) navigate("/"); } catch(err){setError(err.message)} finally{setBusy(false)} }
  return <AuthShell title="Create your account" subtitle="Start exploring quantitative stock research.">
    {!supabase && <div className="alert error">Add VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY to .env.</div>}
    <form onSubmit={submit} className="auth-form">
      <label>Email<input type="email" value={email} onChange={e=>setEmail(e.target.value)} required placeholder="you@example.com"/></label>
      <label>Password<input type="password" value={password} onChange={e=>setPassword(e.target.value)} required placeholder="Minimum 8 characters"/></label>
      <label>Confirm password<input type="password" value={confirm} onChange={e=>setConfirm(e.target.value)} required placeholder="Repeat password"/></label>
      {error&&<div className="alert error">{error}</div>}{message&&<div className="alert success">{message}</div>}
      <button className="primary-btn" disabled={busy||!supabase}>{busy?"Creating...":"Create account →"}</button>
    </form>
    <p className="auth-switch">Already registered? <Link to="/login">Sign in</Link></p>
  </AuthShell>;
}