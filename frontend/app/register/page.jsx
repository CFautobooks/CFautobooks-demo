"use client";

import Link from "next/link";
import {useState} from "react";
import {apiFetch, setSession} from "../../lib/api";

export default function RegisterPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  async function submit(event) {
    event.preventDefault();
    setError("");
    try {
      const payload = await apiFetch("/auth/register", {method: "POST", body: JSON.stringify({email, password})});
      setSession(payload);
      window.location.href = "/pricing";
    } catch (err) {
      setError(err.message);
    }
  }
  return (
    <div className="card">
      <h1>Register</h1>
      <p className="muted">Registration creates a free inactive account. Paid access is granted only after Stripe subscription confirmation.</p>
      <form className="form" onSubmit={submit}>
        {error && <div className="error">{error}</div>}
        <input className="input" type="email" placeholder="you@example.com" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <input className="input" type="password" placeholder="Minimum 8 characters" minLength="8" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <button className="button" type="submit">Create account</button>
      </form>
      <p className="muted">Already registered? <Link href="/login">Login</Link></p>
    </div>
  );
}
