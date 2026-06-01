import Link from "next/link";

export default function Home() {
  return (
    <section className="hero">
      <span className="badge">Live-data first racing analytics MVP</span>
      <h1>Transparent horse racing ratings, odds value, and results tracking.</h1>
      <p>HorseEdge connects to racing form and odds APIs, stores normalized race data, calculates fair odds and expected value, and refuses to fabricate tips when live providers are not connected.</p>
      <div className="actions">
        <Link className="button" href="/daily">Open Daily Race Dashboard</Link>
        <Link className="button secondary" href="/pricing">View Subscription</Link>
      </div>
      <div className="grid">
        <div className="card"><div className="kpi">0 fake tips</div><p className="muted">Selections only come from model ratings calculated from stored race and odds data.</p></div>
        <div className="card"><div className="kpi">EV first</div><p className="muted">Best Bets are ranked by expected value, fair odds, market odds, and confidence.</p></div>
        <div className="card"><div className="kpi">Provider ready</div><p className="muted">Generic provider adapters are in place for real racing and odds APIs.</p></div>
      </div>
    </section>
  );
}
