"use client";

import Link from "next/link";
import {useEffect, useState} from "react";
import ProviderBanner from "../../components/ProviderBanner";
import {apiFetch} from "../../lib/api";

export default function DailyPage() {
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  async function load() {
    setError("");
    try {
      setData(await apiFetch(`/racing/dashboard/daily?race_date=${date}`));
    } catch (err) {
      setError(err.message);
    }
  }
  useEffect(() => { load(); }, []);
  const meetings = data?.meetings || [];
  return (
    <section>
      <div className="hero">
        <h1>Daily Race Dashboard</h1>
        <p>Racecards, runners, barriers, weights, jockeys, trainers, market odds, confidence and model data for the selected date.</p>
        <div className="actions">
          <input className="input" style={{maxWidth: 220}} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
          <button className="button" onClick={load}>Load races</button>
        </div>
      </div>
      {error && <div className="error">{error}</div>}
      <ProviderBanner status={data?.provider_status} />
      {!meetings.length && <div className="locked">No racecards loaded for this date. If providers are not configured, the app will not show fake results.</div>}
      <div className="grid">
        {meetings.map((meeting) => (
          <div className="card" key={meeting.id}>
            <h2>{meeting.track_name}</h2>
            <p className="muted">{meeting.track_condition || "Track condition unavailable"}</p>
            {meeting.races.map((race) => (
              <div className="card" key={race.id}>
                <h3>R{race.race_number || "?"}: {race.name}</h3>
                <p className="muted">{new Date(race.start_time).toLocaleString()} | {race.distance_meters || "?"}m | {race.data_quality_status}</p>
                <div className="table-wrap">
                  <table>
                    <thead><tr><th>Runner</th><th>Barrier</th><th>Weight</th><th>Jockey</th><th>Odds</th><th>Fair</th><th>EV</th><th>Confidence</th><th>Source</th><th>Stake</th></tr></thead>
                    <tbody>
                      {race.runners.map((runner) => (
                        <tr key={runner.id}>
                          <td><Link href={`/runners/${runner.id}`}>{runner.horse_name}</Link></td>
                          <td>{runner.barrier ?? "-"}</td>
                          <td>{runner.weight_kg ?? "-"}</td>
                          <td>{runner.jockey || "-"}</td>
                          <td>{runner.latest_odds ?? "-"}</td>
                          <td>{runner.model_rating?.fair_odds ?? "-"}</td>
                          <td>{runner.model_rating?.expected_value ?? "-"}</td>
                          <td>{runner.model_rating?.confidence_label || runner.data_quality_status}</td>
                          <td>{runner.source_label || "-"}</td>
                          <td>{runner.model_rating?.suggested_staking_unit ?? "-"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}
