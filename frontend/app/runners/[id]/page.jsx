"use client";

import {useEffect, useState} from "react";
import {useParams} from "next/navigation";
import ProviderBanner from "../../../components/ProviderBanner";
import {apiFetch} from "../../../lib/api";

export default function RunnerDetailPage() {
  const params = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  useEffect(() => {
    apiFetch(`/racing/runners/${params.id}`).then(setData).catch((err) => setError(err.message));
  }, [params.id]);
  const runner = data?.runner;
  return (
    <section>
      <h1>Runner Detail</h1>
      {error && <div className="error">{error}</div>}
      <ProviderBanner status={data?.provider_status} />
      {runner && (
        <div className="grid">
          <div className="card">
            <h2>{runner.horse_name}</h2>
            <p className="muted">{data.meeting.track_name} | {data.race.name}</p>
            <p>Barrier: {runner.barrier ?? "-"}</p>
            <p>Weight: {runner.weight_kg ?? "-"}</p>
            <p>Jockey: {runner.jockey || "-"}</p>
            <p>Trainer: {runner.trainer || "-"}</p>
            <p>Status: {runner.data_quality_status}</p>
          </div>
          <div className="card">
            <h2>Rating</h2>
            <p>Market odds: {runner.latest_odds ?? "-"}</p>
            <p>Fair odds: {runner.model_rating?.fair_odds ?? "-"}</p>
            <p>Expected value: {runner.model_rating?.expected_value ?? "-"}</p>
            <p>Confidence: {runner.model_rating?.confidence_label || "insufficient data"}</p>
            <p className="muted">Missing: {(runner.model_rating?.missing_data_fields || runner.missing_data_fields || []).join(", ") || "none"}</p>
          </div>
          <div className="card">
            <h2>Past Form</h2>
            <pre>{JSON.stringify(data.past_form || [], null, 2)}</pre>
          </div>
          <div className="card">
            <h2>Result</h2>
            {data.result ? <pre>{JSON.stringify(data.result, null, 2)}</pre> : <p className="muted">No result loaded yet.</p>}
          </div>
        </div>
      )}
    </section>
  );
}
