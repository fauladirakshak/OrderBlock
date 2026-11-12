import { useMemo, useState } from "react";
import { Activity, Bell, BookOpen, CandlestickChart, ChevronDown, LayoutDashboard, Search, Settings, ShieldCheck, SlidersHorizontal, Wallet } from "lucide-react";
import TradingChart from "./components/TradingChart";

type Market = "Forex" | "Crypto" | "Stocks";
type CandlePoint = { time: number; open: number; high: number; low: number; close: number };

const instruments: Record<Market, string[]> = {
  Forex: ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF"],
  Crypto: ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
  Stocks: ["NIFTY 50", "BANKNIFTY", "RELIANCE", "HDFCBANK", "INFY"],
};
const timeframes = ["5m", "15m", "1H", "4H", "1D", "1W"];

function makeSampleCandles(seed: number, count = 56, timeframe = "1H"): CandlePoint[] {
  const intervalSeconds: Record<string, number> = {
    "5m": 300, "15m": 900, "1H": 3600, "4H": 14400, "1D": 86400, "1W": 604800,
  };
  const startTime = Math.floor(Date.UTC(2026, 0, 1, 0, 0, 0) / 1000);
  const interval = intervalSeconds[timeframe] ?? 3600;
  let previous = 100 + seed * 7;
  return Array.from({ length: count }, (_, i) => {
    const wave = Math.sin((i + seed) * 0.53) * 2.3 + Math.cos((i + seed) * 0.19) * 1.4;
    const open = previous;
    const close = open + wave + Math.sin(i * 1.7 + seed) * 0.9;
    const high = Math.max(open, close) + 0.7 + (i % 4) * 0.18;
    const low = Math.min(open, close) - 0.65 - (i % 3) * 0.2;
    previous = close;
    return { time: startTime + i * interval, open, high, low, close };
  });
}

function App() {
  const [market, setMarket] = useState<Market>("Forex");
  const [instrument, setInstrument] = useState(instruments.Forex[0]);
  const [timeframe, setTimeframe] = useState("1H");
  const [activeTab, setActiveTab] = useState("Overview");
  const marketSeed = ["Forex", "Crypto", "Stocks"].indexOf(market) + instruments[market].indexOf(instrument) + timeframes.indexOf(timeframe);
  const candles = useMemo(() => makeSampleCandles(marketSeed, 56, timeframe), [marketSeed, timeframe]);
  const last = candles[candles.length - 1].close;
  const previous = candles[candles.length - 2].close;
  const move = ((last - previous) / previous) * 100;

  const changeMarket = (next: Market) => { setMarket(next); setInstrument(instruments[next][0]); };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#"><span className="brand-mark">O</span><span>order<span className="brand-accent">block</span><small>MARKET INTELLIGENCE</small></span></a>
        <div className="nav-label">WORKSPACE</div>
        {[[LayoutDashboard,"Overview"],[CandlestickChart,"Chart workspace"],[Activity,"Market structure"],[Wallet,"Watchlists"]].map(([Icon,label]: any) => <button key={label} className={`nav-item ${activeTab===label?"active":""}`} onClick={()=>setActiveTab(label)}><Icon size={17}/>{label}</button>)}
        <div className="nav-label nav-spaced">TOOLS</div>
        {[[BookOpen,"Trading journal"],[SlidersHorizontal,"Strategy lab"]].map(([Icon,label]: any) => <button key={label} className={`nav-item ${activeTab===label?"active":""}`} onClick={()=>setActiveTab(label)}><Icon size={17}/>{label}</button>)}
        <div className="sidebar-bottom"><button className="nav-item" onClick={()=>setActiveTab("Settings")}><Settings size={17}/> Settings</button><div className="feed-status"><span/> Demo data • no live feed</div></div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="crumb">Workspace <span>/</span> {activeTab}</div><div className="top-actions"><button className="icon-button" aria-label="Search"><Search size={17}/></button><button className="icon-button" aria-label="Notifications"><Bell size={17}/></button><div className="profile">OB<span>Research</span><ChevronDown size={14}/></div></div></header>
        <section className="welcome"><div><div className="eyebrow">MULTI-MARKET RESEARCH TERMINAL</div><h1>{activeTab === "Overview" ? "Market overview" : activeTab}</h1><p>One price-action workspace for Forex, Crypto and global markets.</p></div><div className="market-pill"><span/> DEMO MODE · NOT LIVE</div></section>
        <section className="market-switcher"><div className="switcher-label">MARKET</div>{(["Forex","Crypto","Stocks"] as Market[]).map(m=><button key={m} className={market===m?"market-tab selected":"market-tab"} onClick={()=>changeMarket(m)}>{m}</button>)}<div className="market-hint">{market==="Forex"?"FX spot · session-aware":market==="Crypto"?"Spot & perpetuals · 24/7":"NSE/BSE · exchange sessions"}</div></section>
        <section className="metrics">
          <article className="metric-card"><div className="metric-head">SELECTED INSTRUMENT <Activity size={16}/></div><div className="metric-value metric-symbol">{instrument}</div><div className="metric-foot">{market} · illustrative sample series</div></article>
          <article className="metric-card"><div className="metric-head">SAMPLE LAST CLOSE <CandlestickChart size={16}/></div><div className="metric-value">{last.toFixed(2)}</div><div className="metric-foot">Synthetic demo value · not a quote</div></article>
          <article className="metric-card"><div className="metric-head">LAST CANDLE CHANGE <Activity size={16}/></div><div className={`metric-value ${move>=0?"positive":"negative"}`}>{move>=0?"+":""}{move.toFixed(2)}%</div><div className="metric-foot">Illustrative only</div></article>
          <article className="metric-card"><div className="metric-head">SYSTEM STATUS <ShieldCheck size={16}/></div><div className="metric-value status-text">Research mode</div><div className="metric-foot">No broker connection</div></article>
        </section>
        <section className="content-grid">
          <article className="panel chart-panel">
            <div className="panel-head chart-title"><div><h2>{instrument} <span className="demo-tag">SAMPLE</span></h2><p>{market} · {timeframe} · synthetic OHLC candles</p></div><label className="instrument-select"><span>INSTRUMENT</span><select value={instrument} onChange={e=>setInstrument(e.target.value)}>{instruments[market].map(s=><option key={s}>{s}</option>)}</select></label></div>
            <div className="timeframes">{timeframes.map(t=><button key={t} className={timeframe===t?"timeframe active":"timeframe"} onClick={()=>setTimeframe(t)}>{t}</button>)}</div>
            <div className="chart-wrap"><TradingChart candles={candles}/></div>
            <div className="chart-legend"><span><i className="dot teal"/> Bullish candle</span><span><i className="dot red"/> Bearish candle</span><span className="chart-disclaimer">Synthetic demo data — not tradable prices</span></div>
          </article>
          <article className="panel watch-panel"><div className="panel-head"><div><h2>Market watch</h2><p>{market} instruments</p></div></div><div className="watch-list">{instruments[market].map((symbol,i)=><button className={`watch-row ${instrument===symbol?"watch-active":""}`} key={symbol} onClick={()=>setInstrument(symbol)}><div><strong>{symbol}</strong><small>{market==="Forex"?"FX":market==="Crypto"?(i===0||i===1?"Spot / Perpetual":"Spot"):"NSE sample list"}</small></div><div className="watch-price"><strong>{instrument===symbol?"Selected":"Open chart"}</strong><small>Demo only</small></div></button>)}</div><div className="provider-note">Live data is not connected. Select a licensed provider before using real market prices.</div></article>
        </section>
        <section className="bottom-grid"><article className="panel"><div className="panel-head"><div><h2>Analysis layers</h2><p>Next engine modules to be connected to real candles</p></div></div><div className="layer-list"><div><i className="dot teal"/> Market structure <span>Planned</span></div><div><i className="dot red"/> Order blocks <span>Planned</span></div><div><i className="dot amber"/> Fair Value Gaps <span>Planned</span></div><div><i className="dot violet"/> Liquidity sweeps <span>Planned</span></div></div></article><article className="panel"><div className="panel-head"><div><h2>Market-specific context</h2><p>{market} configuration</p></div></div><div className="context-copy">{market==="Forex"?"Session-aware analysis will account for Asia, London and New York sessions, pip precision and spread.":market==="Crypto"?"Crypto instruments will retain exchange and contract identity, with optional funding, open interest and liquidation overlays.":"Equity analysis will respect exchange calendars, trading sessions, gaps and corporate actions."}</div><div className="checklist"><div>01 <span>Confirm higher-timeframe context</span></div><div>02 <span>Identify liquidity and invalidation</span></div><div>03 <span>Validate risk and costs</span></div></div></article></section>
        <footer>ORDERBLOCK <span>•</span> Multi-market research workspace <span>•</span> Demo data only · Not investment advice</footer>
      </main>
    </div>
  );
}
export default App;
