"use client";

import {useEffect, useState} from "react";
import ProviderBanner from "../../../components/ProviderBanner";
import {API_BASE_URL} from "../../../lib/api";

async function adminFetch(path, token, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {"Content-Type": "application/json", "X-Admin-Token": token, ...(options.headers || {})}
  });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || `Request failed with ${response.status}`);
  return body;
}

export default function AdminSyncPage() {
  const [adminToken, setAdminToken] = useState("");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  useEffect(() => setAdminToken(window.localStorage.getItem("admin_token") || ""), []);
  async function load() {
    setError(""); setSuccess("");
    try {
      window.localStorage.setItem("admin_token", adminToken);
      setData(await adminFetch("/racing/admin/sync-status", adminToken));
    } catch (err) { setError(err.message); }
  }
  async function trigger(syncType) {
    setError(""); setSuccess("");
    try {
      const result = await adminFetch(`/racing/admin/sync?sync_type=${syncType}&race_date=${date}`, adminToken, {method: "POST"});
      setSuccess(`${syncType} sync requested: ${JSON.stringify(result)}`);
      await load();
    } catch (err) { setError(err.message); }
  }
  return (
    <section>
      <h1>Admin Sync Dashboard</h1>
      <p className="muted">Enter the admin token from your backend .env. It is stored only in this browser, not baked into the app bundle.</p>
      <div className="actions">
        <input className="input" style={{maxWidth: 360}} type="password" placeholder="ADMIN_API_TOKEN" value={adminToken} onChange={(e) => setAdminToken(e.target.value)} />
        <input className="input" style={{maxWidth: 220}} type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        <button className="button" onClick={load}>Load status</button>
      </div>
      <div className="actions" style={{marginTop: 12}}>
        <button className="button secondary" onClick={() => trigger("racecards")}>Sync racecards</button>
        <button className="button secondary" onClick={() => trigger("odds")}>Sync odds</button>
        <button className="button secondary" onClick={() => trigger("results")}>Sync results</button>
        <button className="button" onClick={() => trigger("all")}>Sync all</button>
      </div>
      {error && <div className="error">{error}</div>}
      {success && <div className="success">{success}</div>}
      <ProviderBanner status={data?.provider_status} />
      <div className="grid">
        <div className="card">
          <h2>Latest syncs</h2>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Provider</th><th>Type</th><th>Status</th><th>Records</th><th>Error</th></tr></thead>
              <tbody>
                {(data?.latest || []).map((run, index) => (
                  <tr key={index}><td>{run.provider}</td><td>{run.sync_type}</td><td>{run.status}</td><td>{run.records_processed}</td><td>{run.error_message || "-"}</td></tr>
                ))}
                {data && !data.latest?.length && <tr><td colSpan="5">No sync runs yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div className="card">
          <h2>Missing data fields</h2>
          <pre>{JSON.stringify(data?.missing_field_counts || {}, null, 2)}</pre>
        </div>
      </div>
    </section>
  );
}
