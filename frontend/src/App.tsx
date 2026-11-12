import { Activity, Bell, BookOpen, CandlestickChart, ChevronDown, LayoutDashboard, Search, Settings, ShieldCheck, SlidersHorizontal, Wallet } from "lucide-react";

const watchlist = [
  { symbol: "NIFTY 50", exchange: "NSE", price: "—", change: "Awaiting feed" },
  { symbol: "BANKNIFTY", exchange: "NSE", price: "—", change: "Awaiting feed" },
  { symbol: "RELIANCE", exchange: "NSE", price: "—", change: "Awaiting feed" },
  { symbol: "HDFCBANK", exchange: "NSE", price: "—", change: "Awaiting feed" },
];

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#"><span className="brand-mark">O</span><span>order<span className="brand-accent">block</span><small>MARKET INTELLIGENCE</small></span></a>
        <div className="nav-label">WORKSPACE</div>
        <a className="nav-item active" href="#"><LayoutDashboard size={17}/> Overview</a>
        <a className="nav-item" href="#"><CandlestickChart size={17}/> Chart workspace</a>
        <a className="nav-item" href="#"><Activity size={17}/> Market structure</a>
        <a className="nav-item" href="#"><Wallet size={17}/> Watchlists</a>
        <div className="nav-label nav-spaced">TOOLS</div>
        <a className="nav-item" href="#"><BookOpen size={17}/> Trading journal</a>
        <a className="nav-item" href="#"><SlidersHorizontal size={17}/> Strategy lab</a>
        <div className="sidebar-bottom"><a className="nav-item" href="#"><Settings size={17}/> Settings</a><div className="feed-status"><span/> Data feed not connected</div></div>
      </aside>

      <main className="main">
        <header className="topbar"><div className="crumb">Workspace <span>/</span> Overview</div><div className="top-actions"><button className="icon-button" aria-label="Search"><Search size={17}/></button><button className="icon-button" aria-label="Notifications"><Bell size={17}/></button><div className="profile">FT<span>Research</span><ChevronDown size={14}/></div></div></header>
        <section className="welcome"><div><div className="eyebrow">MONDAY • MARKET PREPARATION</div><h1>Market overview</h1><p>Your price-action workspace. Clear context, deliberate decisions.</p></div><div className="market-pill"><span/> MARKET DATA DISCONNECTED</div></section>

        <section className="metrics">
          <article className="metric-card"><div className="metric-head">MARKET BIAS <Activity size={16}/></div><div className="metric-value muted">—</div><div className="metric-foot">Waiting for verified market data</div></article>
          <article className="metric-card"><div className="metric-head">ACTIVE ORDER BLOCKS <CandlestickChart size={16}/></div><div className="metric-value">0</div><div className="metric-foot">No instrument selected</div></article>
          <article className="metric-card"><div className="metric-head">STRUCTURE EVENTS <Activity size={16}/></div><div className="metric-value">0</div><div className="metric-foot">BOS / CHoCH detected</div></article>
          <article className="metric-card"><div className="metric-head">SYSTEM STATUS <ShieldCheck size={16}/></div><div className="metric-value status-text">Research mode</div><div className="metric-foot">Paper analysis only</div></article>
        </section>

        <section className="content-grid">
          <article className="panel chart-panel"><div className="panel-head"><div><h2>Price action workspace</h2><p>Select an instrument to begin analysis</p></div><button className="select-button">Select market <ChevronDown size={15}/></button></div><div className="empty-chart"><div className="chart-icon"><CandlestickChart size={25}/></div><h3>Chart data will appear here</h3><p>Connect a licensed market-data provider to load candles, structure and liquidity overlays.</p><button className="primary-button">Configure data source</button></div><div className="chart-legend"><span><i className="dot teal"/> Bullish zone</span><span><i className="dot red"/> Bearish zone</span><span><i className="dot amber"/> Liquidity level</span></div></article>
          <article className="panel watch-panel"><div className="panel-head"><div><h2>Market watch</h2><p>India • NSE</p></div><button className="text-button">View all</button></div><div className="watch-list">{watchlist.map(item => <div className="watch-row" key={item.symbol}><div><strong>{item.symbol}</strong><small>{item.exchange}</small></div><div className="watch-price"><strong>{item.price}</strong><small>{item.change}</small></div></div>)}</div><div className="provider-note">No live or delayed quotes are being displayed.</div></article>
        </section>
        <section className="bottom-grid"><article className="panel"><div className="panel-head"><div><h2>Recent structure events</h2><p>Confirmed events from your selected instruments</p></div></div><div className="empty-inline">No structure events yet.</div></article><article className="panel"><div className="panel-head"><div><h2>Research checklist</h2><p>Before acting on a setup</p></div></div><div className="checklist"><div>01 <span>Confirm higher-timeframe context</span></div><div>02 <span>Identify liquidity and invalidation</span></div><div>03 <span>Validate risk and backtest assumptions</span></div></div></article></section>
        <footer>ORDERBLOCK <span>•</span> Market research workspace <span>•</span> Not investment advice</footer>
      </main>
    </div>
  );
}

export default App;
