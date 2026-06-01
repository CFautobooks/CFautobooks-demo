"use client";

import {useEffect, useState} from "react";
import ProviderBanner from "../../components/ProviderBanner";
import {apiFetch} from "../../lib/api";

export default function ResultsPage() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  async function load() {
    setError("");
    try { setData(await apiFetch(`/racing/results/tracker?race_date=${date}`)); }
    catch (err) { setError(err.message); }
  }
  useEffect(() => { load(); }, []);
  return (
    <section>
      <h1>Results Tracker</h1>
      <div className="actions">
        <input className="input" style={{maxWidth: 220}} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <button className="button" onClick={load}>Load results</button>
      </div>
      {error && <div className="error">{error}</div>}
      <ProviderBanner status={data?.provider_status} />
      <div className="table-wrap">
        <table>
          <thead><tr><th>Track</th><th>Race</th><th>Runner</th><th>Position</th><th>Margin</th><th>SP</th><th>Status</th></tr></thead>
          <tbody>
            {(data?.results || []).map((result, index) => (
              <tr key={index}><td>{result.track}</td><td>{result.race}</td><td>{result.horse_name}</td><td>{result.position ?? "-"}</td><td>{result.margin ?? "-"}</td><td>{result.starting_price ?? "-"}</td><td>{result.result_status}</td></tr>
            ))}
            {data && !data.results?.length && <tr><td colSpan="7">No results loaded for this date.</td></tr>}
          </tbody>
        </table>
      </div>
    </section>
  );
}
