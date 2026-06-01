"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {clearSession, currentUser} from "../lib/api";

export default function Nav() {
  const [user, setUser] = useState(null);
  useEffect(() => setUser(currentUser()), []);
  function logout() {
    clearSession();
    window.location.href = "/login";
  }
  return (
    <nav className="nav">
      <Link href="/" className="brand">HorseEdge Analytics</Link>
      <div className="nav-links">
        <Link href="/daily">Daily Races</Link>
        <Link href="/best-bets">Best Bets</Link>
        <Link href="/results">Results</Link>
        <Link href="/admin/sync">Admin Sync</Link>
        <Link href="/pricing">Pricing</Link>
        {user ? <button onClick={logout}>Logout</button> : <Link href="/login">Login</Link>}
      </div>
    </nav>
  );
}
