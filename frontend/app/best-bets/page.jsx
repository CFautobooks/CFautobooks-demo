"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import ProviderBanner from "../../components/ProviderBanner";
import {apiFetch} from "../../lib/api";

export default function BestBetsPage() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [locked, setLocked] = useState(false);
  async function load() {
    setError("");
    setLocked(false);
    try {
      setData(await apiFetch(`/racing/dashboard/best-bets?race_date=${date}`));
    } catch (err) {
      if (err.status === 401 || err.status === 402) setLocked(true);
      setError(err.message);
    }
  }
  useEffect(() => { load(); }, []);
  return (
    <section>
      <div className="hero">
        <h1>Best Bets</h1>
        <p>Paid dashboard ranked by expected value after the model has calculated win probability and fair odds. No random selections.</p>
        <div className="actions">
          <input className="input" style={{maxWidth: 220}} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <button className="button" onClick={load}>Load best bets</button>
        </div>
      </div>
      {locked && <div className="locked">Best Bets requires an active subscription. <Link href="/pricing">Go to pricing</Link> or login with a paid account.</div>}
      {error && !locked && <div className="error">{error}</div>}
      <ProviderBanner status={data?.provider_status} />
      <div className="table-wrap">
        <table>
          <thead><tr><th>Track</th><th>Race</th><th>Runner</th><th>Win %</th><th>Fair Odds</th><th>Market Odds</th><th>EV</th><th>Confidence</th></tr></thead>
          <tbody>
            {(data?.bets || []).map((bet) => (
              <tr key={`${bet.race_id}-${bet.runner_id}`}>
                <td>{bet.track}</td><td>{bet.race}</td>
                <td><Link href={`/runners/${bet.runner_id}`}>{bet.horse_name}</Link></td>
                <td>{bet.win_probability ?? "-"}</td><td>{bet.fair_odds ?? "-"}</td><td>{bet.bookmaker_odds ?? "-"}</td><td>{bet.expected_value ?? "-"}</td><td>{bet.confidence_label}</td>
              </tr>
            ))}
            {data && !data.bets?.length && <tr><td colSpan="8">No calculated positive-value bets. Live provider data is required.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
