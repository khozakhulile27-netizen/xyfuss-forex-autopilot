import "./styles.css";

type Page = "Overview" | "Markets" | "Strategies" | "Risk & Safety" | "Activity" | "Settings";

const navigation: { page: Page; icon: string }[] = [
  { page: "Overview", icon: "⌂" },
  { page: "Markets", icon: "⌁" },
  { page: "Strategies", icon: "◈" },
  { page: "Risk & Safety", icon: "⬡" },
  { page: "Activity", icon: "≋" },
  { page: "Settings", icon: "⚙" },
];

const app = document.querySelector<HTMLDivElement>("#app");
if (!app) throw new Error("Dashboard root element #app was not found");

let currentPage: Page = "Overview";

function pageContent(page: Page): string {
  if (page === "Overview") return overview();
  if (page === "Markets") return markets();
  if (page === "Strategies") return strategies();
  if (page === "Risk & Safety") return risk();
  if (page === "Activity") return activity();
  return settings();
}

function overview(): string {
  return `
    <div class="banner"><div class="banner-icon">⚠</div><div><strong>PREVIEW MODE — ROBOT NOT CONNECTED</strong><p>This dashboard interface is being built. It is not receiving live prices, connected to a broker, or controlling a trading robot. All account and market values are intentionally unavailable.</p></div></div>
    <div class="section-head"><h2>System overview</h2><span>Connection status</span></div>
    <div class="grid">
      <article class="card"><div class="metric-label">ROBOT STATUS</div><div class="metric-value warn">OFFLINE</div><div class="metric-note">No engine connection</div></article>
      <article class="card"><div class="metric-label">TRADING MODE</div><div class="metric-value">PAPER</div><div class="metric-note">Live trading disabled</div></article>
      <article class="card"><div class="metric-label">BROKER CONNECTION</div><div class="metric-value warn">NONE</div><div class="metric-note">No account connected</div></article>
      <article class="card"><div class="metric-label">OPEN POSITIONS</div><div class="metric-value">—</div><div class="metric-note">No broker data available</div></article>
    </div>
    <div class="section-head"><h2>Robot activity</h2><span>Awaiting backend connection</span></div>
    <div class="two-col">
      <article class="card"><div class="metric-label">MARKET PERFORMANCE</div><div class="empty-chart">No verified market feed connected.<br/>Performance charts will appear after backend integration.</div></article>
      <article class="card"><div class="metric-label">SYSTEM CHECKS</div><div class="status-list">
        <div class="status-row"><span>Eligibility engine</span><strong class="blocked">NOT CONNECTED</strong></div>
        <div class="status-row"><span>Risk engine</span><strong class="blocked">NOT CONNECTED</strong></div>
        <div class="status-row"><span>Market data</span><strong class="blocked">NOT CONNECTED</strong></div>
        <div class="status-row"><span>Broker adapter</span><strong class="blocked">NOT CONNECTED</strong></div>
        <div class="status-row"><span>Live trading</span><strong class="safe">DISABLED</strong></div>
      </div></article>
    </div>
    <div class="section-head"><h2>Latest decisions</h2><span>Real decisions will appear here</span></div>
    <article class="card"><div class="empty-chart">No decisions recorded yet.<br/>The dashboard will show evidence, eligibility results and NO_TRADE reasons when the engine API is connected.</div></article>
    <p class="footer-note">No simulated profits, balances, trades or market signals are displayed as real account information.</p>`;
}

function markets(): string {
  return `<div class="banner"><div class="banner-icon">ⓘ</div><div><strong>MARKET FEED NOT CONNECTED</strong><p>Instrument watchlists, bid/ask prices, spreads, volatility and data freshness will populate only from a verified backend feed.</p></div></div>
  <div class="section-head"><h2>Market watchlist</h2><span>Live values unavailable</span></div>
  <article class="card table-wrap"><table class="table"><thead><tr><th>Instrument</th><th>Bid / Ask</th><th>Spread</th><th>Data age</th><th>Eligibility</th></tr></thead><tbody><tr><td colspan="5">No market instruments loaded. No prices are being invented.</td></tr></tbody></table></article>
  <p class="footer-note">A market candidate must pass data-integrity, freshness, instrument allowlist, session and evidence checks before risk assessment.</p>`;
}

function strategies(): string {
  return `<div class="banner"><div class="banner-icon">ⓘ</div><div><strong>STRATEGY ENGINE NOT CONNECTED</strong><p>No strategy is currently approved for trading. Strategies must pass out-of-sample and forward demo testing before being eligible.</p></div></div>
  <div class="section-head"><h2>Strategy registry</h2><span>Validation required</span></div>
  <article class="card table-wrap"><table class="table"><thead><tr><th>Strategy</th><th>Market</th><th>Backtest</th><th>Forward test</th><th>Status</th></tr></thead><tbody><tr><td colspan="5">No validated strategies registered.</td></tr></tbody></table></article>
  <div class="section-head"><h2>Required validation</h2></div><div class="feature-list"><div class="feature"><strong>Out-of-sample testing</strong><p>Keep unseen data separate from strategy development to reduce overfitting.</p></div><div class="feature"><strong>Trading costs</strong><p>Include spreads, commissions, swaps, slippage and realistic execution assumptions.</p></div><div class="feature"><strong>Walk-forward evaluation</strong><p>Test performance across multiple changing market periods.</p></div><div class="feature"><strong>Demo forward testing</strong><p>Verify behavior in live market conditions without risking capital.</p></div></div>`;
}

function risk(): string {
  return `<div class="banner"><div class="banner-icon">⬡</div><div><strong>CAPITAL PROTECTION — NOT YET CONNECTED</strong><p>The controls below describe required safeguards. Their operational status cannot be confirmed until the Rust engine and persistent state are connected and tested.</p></div></div>
  <div class="section-head"><h2>Required protection controls</h2><span>Design checklist</span></div>
  <div class="content-panel">
    <article class="card"><div class="status-list">
      <div class="status-row"><span>Trade eligibility gate</span><strong class="blocked">IMPLEMENTED — NOT INTEGRATED</strong></div>
      <div class="status-row"><span>Pre-trade risk gate</span><strong class="blocked">IMPLEMENTED — NOT INTEGRATED</strong></div>
      <div class="status-row"><span>Stop-loss / take-profit verification</span><strong class="blocked">NOT VERIFIED</strong></div>
      <div class="status-row"><span>Position sizing and exposure</span><strong class="blocked">NOT COMPLETE</strong></div>
      <div class="status-row"><span>Daily loss / drawdown lockout</span><strong class="blocked">NOT INTEGRATED</strong></div>
      <div class="status-row"><span>Correlation and portfolio limits</span><strong class="blocked">NOT COMPLETE</strong></div>
      <div class="status-row"><span>Emergency stop and recovery</span><strong class="blocked">NOT VERIFIED</strong></div>
      <div class="status-row"><span>Live order permission</span><strong class="safe">DISABLED</strong></div>
    </div></article>
    <div class="feature-list"><div class="feature"><strong>Fail closed</strong><p>Missing, stale, malformed or contradictory data must produce NO_TRADE.</p></div><div class="feature"><strong>Broker-side protection</strong><p>Never assume a stop-loss exists until the broker confirms its accepted order state.</p></div></div>
  </div>`;
}

function activity(): string {
  return `<div class="banner"><div class="banner-icon">ⓘ</div><div><strong>AUDIT STREAM NOT CONNECTED</strong><p>This page will show timestamped engine events, evidence references, eligibility decisions, risk verdicts and broker acknowledgements.</p></div></div>
  <div class="section-head"><h2>System event history</h2><span>Awaiting persistent audit API</span></div>
  <article class="card table-wrap"><table class="table"><thead><tr><th>Time</th><th>Event</th><th>Decision</th><th>Evidence ID</th></tr></thead><tbody><tr><td colspan="4">No audit events available.</td></tr></tbody></table></article>`;
}

function settings(): string {
  return `<div class="section-head"><h2>Connection settings</h2><span>Not configured</span></div>
  <div class="content-panel">
    <article class="card"><div class="status-list">
      <div class="status-row"><span>Robot API</span><strong class="blocked">NOT CONFIGURED</strong></div>
      <div class="status-row"><span>Broker</span><strong class="blocked">NOT CONNECTED</strong></div>
      <div class="status-row"><span>Authentication</span><strong class="blocked">NOT CONFIGURED</strong></div>
      <div class="status-row"><span>Trading mode</span><strong class="safe">PAPER / DEMO ONLY</strong></div>
    </div></article>
    <div class="banner"><div class="banner-icon">🔒</div><div><strong>SECURITY FIRST</strong><p>Broker passwords, API secrets and account tokens must never be entered into this static dashboard or committed to GitHub. The future backend must store secrets securely and enforce authenticated access.</p></div></div>
    <p class="footer-note">The dashboard is currently a frontend preview. A secure API, authentication, server deployment, broker adapter and operator audit trail are still required before it can control the robot.</p>
  </div>`;
}

function render(): void {
  const nav = navigation.map(({ page, icon }) =>
    `<button type="button" data-page="${page}" class="${page === currentPage ? "active" : ""}"><span class="nav-icon">${icon}</span>${page}</button>`
  ).join("");
  app.innerHTML = `
    <div class="shell">
      <aside class="sidebar">
        <div class="brand"><div class="brand-mark">X</div><div><div class="brand-name">XYFUSS</div><div class="brand-sub">FOREX AUTOPILOT</div></div></div>
        <div><div class="nav-label">CONTROL CENTER</div><nav class="nav">${nav}</nav></div>
        <div class="sidebar-bottom"><div class="safety-mini"><strong>● LIVE TRADING LOCKED</strong><p>Live order capability is disabled during development and testing.</p></div></div>
      </aside>
      <main class="main">
        <div class="mobile-brand"><div class="brand-mark">X</div><div><div class="brand-name">XYFUSS</div><div class="brand-sub">FOREX AUTOPILOT</div></div></div>
        <header class="topbar"><div><div class="eyebrow">OPERATOR CONSOLE / ${currentPage.toUpperCase()}</div><h1 class="page-title">${currentPage}</h1></div><div class="top-actions"><span class="pill"><i class="dot"></i> ROBOT OFFLINE</span><span class="pill">PAPER PREVIEW</span><button class="button" disabled title="Backend connection is not implemented">Connect robot</button></div></header>
        ${pageContent(currentPage)}
      </main>
    </div>
    <nav class="bottom-nav" aria-label="Main navigation">${navigation.map(({page,icon})=>`<button type="button" data-page="${page}" class="${page===currentPage?"active":""}"><span>${icon}</span>${page==="Risk & Safety"?"Safety":page}</button>`).join("")}</nav>
  `;
  app.querySelectorAll<HTMLButtonElement>("[data-page]").forEach((button) => {
    button.addEventListener("click", () => {
      const page = button.dataset.page as Page | undefined;
      if (page && navigation.some((item) => item.page === page)) {
        currentPage = page;
        render();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    });
  });
}

render();
