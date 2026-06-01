export default function ProviderBanner({status}) {
  if (!status) return null;
  const live = status.live_provider_connected;
  return (
    <div className={live ? "banner banner-ok" : "banner banner-warn"}>
      <strong>{status.message || (live ? "Live provider connected" : "No live provider connected")}</strong>
      <span> Racing form: {status.racing_form_configured ? "configured" : "missing"}</span>
      <span> Odds: {status.odds_configured ? "configured" : "missing"}</span>
    </div>
  );
}
