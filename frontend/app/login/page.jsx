"use client";

import Link from "next/link";
import {useState} from "react";
import {apiFetch, setSession} from "../../lib/api";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const payload = await apiFetch("/auth/login", {method: "POST", body: JSON.stringify({email, password})});
      setSession(payload);
      window.location.href = "/daily";
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <div className="card">
      <h1>Login</h1>
      <p className="muted">Access your racing dashboards and subscription-gated Best Bets.</p>
      <form className="form" onSubmit={submit}>
        {error && <div className="error">{error}</div>}
        <input className="input" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="input" type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="button" type="submit">Login</button>
      </form>
      <p className="muted">No account? <Link href="/register">Register</Link></p>
    </div>
  );
}
