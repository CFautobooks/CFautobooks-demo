"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import {apiFetch, getToken} from "../../lib/api";

export default function PricingPage() {
  const [subscription, setSubscription] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    if (getToken()) apiFetch("/billing/subscription").then(setSubscription).catch(() => {});
  }, []);
  async function checkout() {
    setError(""); setLoading(true);
    try {
      const payload = await apiFetch("/billing/create-checkout-session", {method: "POST"});
      window.location.href = payload.checkout_url;
    } catch (err) {
      setError(err.message);
    } finally { setLoading(false); }
  }
  return (
    <section className="hero">
      <h1>Subscription</h1>
      <p>Best Bets are locked behind an active Stripe subscription. Daily racecards and results stay visible so users can inspect available data before upgrading.</p>
      {subscription && <div className="success">Current status: {subscription.subscription_status}. Stripe configured: {String(subscription.stripe_configured)}</div>}
      {error && <div className="error">{error}</div>}
      <div className="grid">
        <div className="card">
          <h2>Racing Pro</h2>
          <div className="kpi">Paid</div>
          <p className="muted">Unlock Best Bets, expected value rankings, confidence scores, fair odds and odds comparison.</p>
          <button className="button" disabled={loading} onClick={checkout}>{loading ? "Opening Stripe..." : "Subscribe with Stripe"}</button>
          <p className="muted">If Stripe env vars are missing, checkout will show a configuration error instead of pretending payment worked.</p>
        </div>
        <div className="card">
          <h2>Free</h2>
          <p>Daily race dashboard, provider status, runner detail pages and results tracker.</p>
          <Link className="button secondary" href="/daily">Continue free</Link>
        </div>
      </div>
    </section>
  );
}
