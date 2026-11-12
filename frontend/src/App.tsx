import { useEffect, useState } from "react";
import { Activity, Bell, BookOpen, CandlestickChart, ChevronDown, LayoutDashboard, Search, Settings, ShieldCheck, SlidersHorizontal, Wallet } from "lucide-react";
import TradingChart from "./components/TradingChart";

type Market = "Forex" | "Crypto" | "Stocks";
type CandlePoint = { time: number; open: number; high: number; low: number; close: number };
type CandleResponse = { provider: string; is_synthetic: boolean; candles: Array<{ timestamp: string; open: number; high: number; low: number; close: number }> };
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const apiMarkets: Record<Market, string> = { Forex: "forex", Crypto: "crypto", Stocks: "stocks" };

const instruments: Record<Market, string[]> = {
  Forex: ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF"],
  Crypto: ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
  Stocks: ["NIFTY 50", "BANKNIFTY", "RELIANCE", "HDFCBANK", "INFY"],
};
const timeframes = ["5m", "15m", "1H", "4H", "1D", "1W"];

function App() {
  const [market, setMarket] = useState<Market>("Forex");
  const [instrument, setInstrument] = useState(instruments.Forex[0]);
  const [timeframe, setTimeframe] = useState("1H");
  const [activeTab, setActiveTab] = useState("Overview");
  const [candles, setCandles] = useState<CandlePoint[]>([]);
  const [provider, setProvider] = useState("loading");
  const [loading, setLoading] = useState(true);
  const [dataError, setDataError] = useState("");
  useEffect(() => {
    const controller = new AbortController();
    async function loadCandles() {
      setLoading(true);
      setDataError("");
      try {
        const params = new URLSearchParams({ market: apiMarkets[market], symbol: instrument, timeframe, limit: "200" });
        const requestUrl = API_BASE + "/api/v1/market-data/candles?" + params.toString();
        const response = await fetch(requestUrl, { signal: controller.signal });
        if (!response.ok) throw new Error(\`Market data API returned HTTP \${response.status}\`);
        const payload = await response.json() as CandleResponse;
        const parsed = payload.candles.map(c => ({ time: Math.floor(Date.parse(c.timestamp) / 1000), open: c.open, high: c.high, low: c.low, close: c.close }));
        if (parsed.some(c => !Number.isFinite(c.time))) throw new Error("Invalid candle timestamp returned by API.");
        setCandles(parsed);
        setProvider(payload.provider);
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        setCandles([]);
        setProvider("unavailable");
        setDataError(error instanceof Error ? error.message : "Unable to load market data.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void loadCandles();
    return () => controller.abort();
  }, [market, instrument, timeframe]);
  const last = candles.length ? candles[candles.length - 1].close : 0;
  const previous = candles.length > 1 ? candles[candles.length - 2].close : 0;
  const move = previous ? ((last - previous) / previous) * 100 : 0;

  const changeMarket = (next: Market) => { setMarket(next); setInstrument(instruments[next][0]); };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#"><span className="brand-mark">O</span><span>order<span className="brand-accent">block</span><small>MARKET INTELLIGENCE</small></span></a>
        <div className="nav-label">WORKSPACE</div>
        {[[LayoutDashboard,"Overview"],[CandlestickChart,"Chart workspace"],[Activity,"Market structure"],[Wallet,"Watchlists"]].map(([Icon,label]: any) => <button key={label} className={`nav-item ${activeTab===label?"active":""}`} onClick={()=>setActiveTab(label)}><Icon size={17}/>{label}</button>)}
        <div className="nav-label nav-spaced">TOOLS</div>
        {[[BookOpen,"Trading journal"],[SlidersHorizontal,"Strategy lab"]].map(([Icon,label]: any) => <button key={label} className={`nav-item ${activeTab===label?"active":""}`} onClick={()=>setActiveTab(label)}><Icon size={17}/>{label}</button>)}
        <div className="sidebar-bottom"><button className="nav-item" onClick={()=>setActiveTab("Settings")}><Settings size={17}/> Settings</button><div className="feed-status"><span/> {provider === "synthetic-demo" ? "Demo provider • synthetic" : "Market data • disconnected"}</div></div>
      </aside>
      <main className="main">
        <header className="topbar"><div className="crumb">Workspace <span>/</span> {activeTab}</div><div className="top-actions"><button className="icon-button" aria-label="Search"><Search size={17}/></button><button className="icon-button" aria-label="Notifications"><Bell size={17}/></button><div className="profile">OB<span>Research</span><ChevronDown size={14}/></div></div></header>
        <section className="welcome"><div><div className="eyebrow">MULTI-MARKET RESEARCH TERMINAL</div><h1>{activeTab === "Overview" ? "Market overview" : activeTab}</h1><p>One price-action workspace for Forex, Crypto and global markets.</p></div><div className="market-pill"><span/> DEMO MODE · NOT LIVE</div></section>
        <section className="market-switcher"><div className="switcher-label">MARKET</div>{(["Forex","Crypto","Stocks"] as Market[]).map(m=><button key={m} className={market===m?"market-tab selected":"market-tab"} onClick={()=>changeMarket(m)}>{m}</button>)}<div className="market-hint">{market==="Forex"?"FX spot · session-aware":market==="Crypto"?"Spot & perpetuals · 24/7":"NSE/BSE · exchange sessions"}</div></section>
        <section className="metrics">
          <article className="metric-card"><div className="metric-head">SELECTED INSTRUMENT <Activity size={16}/></div><div className="metric-value metric-symbol">{instrument}</div><div className="metric-foot">{market} · {provider} series</div></article>
          <article className="metric-card"><div className="metric-head">SAMPLE LAST CLOSE <CandlestickChart size={16}/></div><div className="metric-value">{loading ? "…" : candles.length ? last.toFixed(5) : "—"}</div><div className="metric-foot">Demo value · not a quote</div></article>
          <article className="metric-card"><div className="metric-head">LAST CANDLE CHANGE <Activity size={16}/></div><div className={`metric-value ${move>=0?"positive":"negative"}`}>{candles.length > 1 ? `${move>=0?"+":""}${move.toFixed(2)}%` : "—"}</div><div className="metric-foot">Illustrative only</div></article>
          <article className="metric-card"><div className="metric-head">SYSTEM STATUS <ShieldCheck size={16}/></div><div className="metric-value status-text">Research mode</div><div className="metric-foot">No broker connection</div></article>
        </section>
        <section className="content-grid">
          <article className="panel chart-panel">
            <div className="panel-head chart-title"><div><h2>{instrument} <span className="demo-tag">SAMPLE</span></h2><p>{market} · {timeframe} · backend-provided OHLC</p></div><label className="instrument-select"><span>INSTRUMENT</span><select value={instrument} onChange={e=>setInstrument(e.target.value)}>{instruments[market].map(s=><option key={s}>{s}</option>)}</select></label></div>
            <div className="timeframes">{timeframes.map(t=><button key={t} className={timeframe===t?"timeframe active":"timeframe"} onClick={()=>setTimeframe(t)}>{t}</button>)}</div>
            <div className="chart-wrap">{loading ? <div className="data-state">Loading candle series…</div> : candles.length ? <TradingChart candles={candles}/> : <div className="data-state error">{dataError || "No candle data available."}<small>Start the FastAPI backend and refresh this workspace.</small></div>}</div>
            <div className="chart-legend"><span><i className="dot teal"/> Bullish candle</span><span><i className="dot red"/> Bearish candle</span><span className="chart-disclaimer">Synthetic demo data — not tradable prices</span></div>
          </article>
          <article className="panel watch-panel"><div className="panel-head"><div><h2>Market watch</h2><p>{market} instruments</p></div></div><div className="watch-list">{instruments[market].map((symbol,i)=><button className={`watch-row ${instrument===symbol?"watch-active":""}`} key={symbol} onClick={()=>setInstrument(symbol)}><div><strong>{symbol}</strong><small>{market==="Forex"?"FX":market==="Crypto"?(i===0||i===1?"Spot / Perpetual":"Spot"):"NSE sample list"}</small></div><div className="watch-price"><strong>{instrument===symbol?"Selected":"Open chart"}</strong><small>Demo only</small></div></button>)}</div><div className="provider-note">Provider: {provider}. Live data is not connected. Real market prices require a licensed source.</div></article>
        </section>
        <section className="bottom-grid"><article className="panel"><div className="panel-head"><div><h2>Analysis layers</h2><p>Next engine modules to be connected to real candles</p></div></div><div className="layer-list"><div><i className="dot teal"/> Market structure <span>Planned</span></div><div><i className="dot red"/> Order blocks <span>Planned</span></div><div><i className="dot amber"/> Fair Value Gaps <span>Planned</span></div><div><i className="dot violet"/> Liquidity sweeps <span>Planned</span></div></div></article><article className="panel"><div className="panel-head"><div><h2>Market-specific context</h2><p>{market} configuration</p></div></div><div className="context-copy">{market==="Forex"?"Session-aware analysis will account for Asia, London and New York sessions, pip precision and spread.":market==="Crypto"?"Crypto instruments will retain exchange and contract identity, with optional funding, open interest and liquidation overlays.":"Equity analysis will respect exchange calendars, trading sessions, gaps and corporate actions."}</div><div className="checklist"><div>01 <span>Confirm higher-timeframe context</span></div><div>02 <span>Identify liquidity and invalidation</span></div><div>03 <span>Validate risk and costs</span></div></div></article></section>
        <footer>ORDERBLOCK <span>•</span> Multi-market research workspace <span>•</span> Demo data only · Not investment advice</footer>
      </main>
    </div>
  );
}
export default App;
