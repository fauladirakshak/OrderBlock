import { useEffect, useState } from "react";
import { Activity, Bell, BookOpen, CandlestickChart, ChevronDown, LayoutDashboard, Search, Settings, ShieldCheck, SlidersHorizontal, Wallet } from "lucide-react";
import TradingChart, { type ChartOverlay } from "./components/TradingChart";

type Market = "Forex" | "Crypto" | "Stocks";
type CandlePoint = { time: number; open: number; high: number; low: number; close: number };
type InstrumentMetadata = { symbol: string; venue: string; venue_id: string; contract_type: string; timezone: string; session: string; price_precision: number; tick_size: number; quote_currency: string; session_open?: string | null; session_close?: string | null };
type MarketCatalogue = { instruments: InstrumentMetadata[] };
type CandleResponse = { provider: string; is_synthetic: boolean; venue?: string; venue_id?: string; contract_type?: string; timezone?: string; session?: string; price_precision?: number; tick_size?: number; candles: Array<{ timestamp: string; open: number; high: number; low: number; close: number }> };
type MtfContext = { timeframe: string; candle_count: number; bias: "bullish" | "bearish" | "neutral"; latest_event: { kind: string; direction: string } | null; explanation: string };
type MtfAnalysis = { primary_timeframe: string; primary_bias: "bullish" | "bearish" | "neutral"; higher_timeframe_context: MtfContext[]; alignment: "bullish" | "bearish" | "mixed" | "neutral"; summary: string; notes: string[] };
const timeframeRank: Record<string, number> = { "5m": 1, "15m": 2, "1H": 3, "4H": 4, "1D": 5, "1W": 6 };
const API_BASE = (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");
const apiMarkets: Record<Market, string> = { Forex: "forex", Crypto: "crypto", Stocks: "stocks" };

const instruments: Record<Market, string[]> = {
  Forex: ["EUR/USD", "GBP/USD", "USD/JPY", "AUD/USD", "USD/CHF"],
  Crypto: ["BTC/USDT", "ETH/USDT", "SOL/USDT", "BNB/USDT", "XRP/USDT"],
  Stocks: ["NIFTY 50", "BANKNIFTY", "RELIANCE", "HDFCBANK", "INFY"],
};
const timeframes = ["5m", "15m", "1H", "4H", "1D", "1W"];
const timeframeSeconds: Record<string, number> = { "5m": 300, "15m": 900, "1H": 3600, "4H": 14400, "1D": 86400, "1W": 604800 };
function makePreviewCandles(market: Market, symbol: string, timeframe: string) {
  const interval = timeframeSeconds[timeframe] || 3600;
  const seed = Array.from((market + symbol).toLowerCase()).reduce((sum, char) => sum + char.charCodeAt(0), 0);
  const base = market === "Forex" ? 1.08 : market === "Crypto" ? 42000 : 24000;
  const scale = market === "Forex" ? 0.0007 : market === "Crypto" ? 55 : 12;
  let previous = base + (seed % 97) * scale;
  const end = Date.UTC(2026, 0, 1) / 1000;
  return Array.from({ length: 140 }, (_, index) => {
    const wave = Math.sin((index + seed) * 1.71) * scale * 1.7 + Math.cos((index + seed) * 0.39) * scale * 0.7;
    const open = previous;
    const close = Math.max(0.00001, open + wave);
    const wick = scale * (0.6 + (Math.sin(index * 2.1 + seed) + 1) * 0.4);
    const time = end - interval * (139 - index);
    previous = close;
    return { timestamp: new Date(time * 1000).toISOString(), open, high: Math.max(open, close) + wick, low: Math.max(0.000001, Math.min(open, close) - wick), close };
  });
}

function App() {
  const [market, setMarket] = useState<Market>("Forex");
  const [instrument, setInstrument] = useState(instruments.Forex[0]);
  const [timeframe, setTimeframe] = useState("1H");
  const [activeTab, setActiveTab] = useState("Overview");
  const [candles, setCandles] = useState<CandlePoint[]>([]);
  const [provider, setProvider] = useState("loading");
  const [loading, setLoading] = useState(true);
  const [dataError, setDataError] = useState("");
  const [overlays, setOverlays] = useState<ChartOverlay | null>(null);
  const [analysisError, setAnalysisError] = useState("");
  const [mtf, setMtf] = useState<MtfAnalysis | null>(null);
  const [mtfError, setMtfError] = useState("");
  const [selectedZoneKey, setSelectedZoneKey] = useState("");
  const [instrumentMetadata, setInstrumentMetadata] = useState<InstrumentMetadata | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    async function loadCandles() {
      setLoading(true);
      setDataError("");
      try {
        let selectedMetadata: InstrumentMetadata | null = null;
        try {
          const catalogueResponse = await fetch(API_BASE + "/api/v1/markets", { signal: controller.signal });
          if (catalogueResponse.ok) {
            const catalogue = await catalogueResponse.json() as MarketCatalogue;
            selectedMetadata = catalogue.instruments.find(item => item.symbol === instrument) ?? null;
          }
        } catch (catalogueError) {
          if (catalogueError instanceof Error && catalogueError.name === "AbortError") return;
        }
        setInstrumentMetadata(selectedMetadata);
        const params = new URLSearchParams({ market: apiMarkets[market], symbol: instrument, timeframe, limit: "200" });
        if (selectedMetadata) {
          params.set("venue_id", selectedMetadata.venue_id);
          params.set("contract_type", selectedMetadata.contract_type);
        }
        const requestUrl = API_BASE + "/api/v1/market-data/candles?" + params.toString();
        let payload: CandleResponse;
        try {
          const response = await fetch(requestUrl, { signal: controller.signal });
          if (!response.ok) throw new Error("Market data API returned HTTP " + response.status);
          payload = await response.json() as CandleResponse;
        } catch (fetchFailure) {
          if (controller.signal.aborted) return;
          if (import.meta.env.VITE_PREVIEW_MODE !== "true") throw fetchFailure;
          payload = { provider: "preview-synthetic", is_synthetic: true, candles: makePreviewCandles(market, instrument, timeframe) };
        }
        const parsed = payload.candles.map(c => ({ time: Math.floor(Date.parse(c.timestamp) / 1000), open: c.open, high: c.high, low: c.low, close: c.close }));
        if (parsed.some(c => !Number.isFinite(c.time))) throw new Error("Invalid candle timestamp returned by API.");
        setCandles(parsed);
        setProvider(payload.provider);
        if (payload.provider === "preview-synthetic") {
          setMtf(null);
          setMtfError("Static preview mode: higher-timeframe analysis appears when the FastAPI service is connected.");
          setOverlays(null);
          setAnalysisError("Static preview mode: backend overlays appear when the FastAPI service is connected.");
          return;
        }
        try {
          const analysisResponse = await fetch(API_BASE + "/api/v1/analysis/workspace", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candles: payload.candles, pivot: 2 }),
            signal: controller.signal,
          });
          if (!analysisResponse.ok) throw new Error("Analysis API returned HTTP " + analysisResponse.status);
          setOverlays(await analysisResponse.json() as ChartOverlay);
          setAnalysisError("");
          try {
            const higherTimeframes = timeframes.filter(tf => timeframeRank[tf] > timeframeRank[timeframe]);
            const contextSeries = await Promise.all(higherTimeframes.map(async tf => {
              const contextParams = new URLSearchParams({ market: apiMarkets[market], symbol: instrument, timeframe: tf, limit: "200" });
              if (selectedMetadata) { contextParams.set("venue_id", selectedMetadata.venue_id); contextParams.set("contract_type", selectedMetadata.contract_type); }
              const contextResponse = await fetch(API_BASE + "/api/v1/market-data/candles?" + contextParams.toString(), { signal: controller.signal });
              if (!contextResponse.ok) throw new Error("Unable to load " + tf + " context candles.");
              return [tf, (await contextResponse.json() as CandleResponse).candles] as const;
            }));
            if (higherTimeframes.length) {
              const contextPayload = Object.fromEntries([[timeframe, payload.candles], ...contextSeries]);
              const mtfResponse = await fetch(API_BASE + "/api/v1/analysis/multi-timeframe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ primary_timeframe: timeframe, candles_by_timeframe: contextPayload, pivot: 2 }),
                signal: controller.signal,
              });
              if (!mtfResponse.ok) throw new Error("Multi-timeframe API returned HTTP " + mtfResponse.status);
              setMtf(await mtfResponse.json() as MtfAnalysis);
              setMtfError("");
            } else {
              setMtf(null);
              setMtfError("No higher timeframe is available above 1W.");
            }
          } catch (contextFailure) {
            if (contextFailure instanceof Error && contextFailure.name === "AbortError") return;
            setMtf(null);
            setMtfError(contextFailure instanceof Error ? contextFailure.message : "Higher-timeframe context unavailable.");
          }
        } catch (analysisFailure) {
          if (analysisFailure instanceof Error && analysisFailure.name === "AbortError") return;
          setOverlays(null);
          setAnalysisError(analysisFailure instanceof Error ? analysisFailure.message : "Analysis overlays unavailable.");
        }
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        setCandles([]);
        setOverlays(null);
        setProvider("unavailable");
        setDataError(error instanceof Error ? error.message : "Unable to load market data.");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    void loadCandles();
    return () => controller.abort();
  }, [market, instrument, timeframe]);
  const zoneItems = [
    ...(overlays?.order_blocks ?? []).slice(-8).map((z, i) => ({ key: "ob-" + z.candle_index + "-" + i, kind: "Order Block", direction: z.direction, top: z.top, bottom: z.bottom, status: z.invalidated ? "Invalidated" : z.mitigated ? "Mitigated" : "Active", rule: z.rule, index: z.candle_index })),
    ...(overlays?.fair_value_gaps ?? []).slice(-8).map((z, i) => ({ key: "fvg-" + z.middle_candle_index + "-" + i, kind: "Fair Value Gap", direction: z.direction, top: z.top, bottom: z.bottom, status: z.filled ? "Filled" : z.mitigated ? "Touched" : "Open", rule: z.rule, index: z.middle_candle_index })),
  ].sort((x,y) => y.index - x.index);
  const selectedZone = zoneItems.find(z => z.key === selectedZoneKey) ?? zoneItems[0];
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
            <div className="chart-wrap">{loading ? <div className="data-state">Loading candle series…</div> : candles.length ? <TradingChart candles={candles} overlays={overlays}/> : <div className="data-state error">{dataError || "No candle data available."}<small>Start the FastAPI backend and refresh this workspace.</small></div>}</div>
            <div className="chart-legend"><span><i className="dot teal"/> Bullish candle</span><span><i className="dot red"/> Bearish candle</span><span className="chart-disclaimer">Synthetic demo data — not tradable prices</span></div>
          </article>
          <article className="panel watch-panel"><div className="panel-head"><div><h2>Market watch</h2><p>{market} instruments</p></div></div><div className="watch-list">{instruments[market].map((symbol,i)=><button className={`watch-row ${instrument===symbol?"watch-active":""}`} key={symbol} onClick={()=>setInstrument(symbol)}><div><strong>{symbol}</strong><small>{market==="Forex"?"FX":market==="Crypto"?(i===0||i===1?"Spot / Perpetual":"Spot"):"NSE sample list"}</small></div><div className="watch-price"><strong>{instrument===symbol?"Selected":"Open chart"}</strong><small>Demo only</small></div></button>)}</div><div className="provider-note">Provider: {provider}. Live data is not connected. Real market prices require a licensed source.</div></article>
        </section>
        <section className="bottom-grid"><article className="panel"><div className="panel-head"><div><h2>Higher-timeframe context</h2><p>Independent structure read across larger intervals</p></div><span className={`bias-pill ${mtf?.alignment || "neutral"}`}>{mtf?.alignment?.toUpperCase() || "PENDING"}</span></div><div className="mtf-list">{mtf?.higher_timeframe_context.map(item=><div className="mtf-row" key={item.timeframe}><strong>{item.timeframe}</strong><span className={`bias-text ${item.bias}`}>{item.bias.toUpperCase()}</span><small>{item.explanation}</small></div>)}</div><div className="overlay-note">{mtf?.summary || mtfError || "Waiting for higher-timeframe analysis…"}</div><div className="context-copy">{mtf?.notes[2] || "Directional context is descriptive research, not a trade signal."}</div></article><article className="panel"><div className="panel-head"><div><h2>Live analysis overlays</h2><p>Rule-based annotations calculated from the displayed candles</p></div></div><div className="layer-list"><div><i className="dot teal"/> BOS / CHoCH <span>{overlays?.structure_events.length ?? "—"}</span></div><div><i className="dot red"/> Order blocks <span>{overlays?.order_blocks.length ?? "—"}</span></div><div><i className="dot amber"/> Fair Value Gaps <span>{overlays?.fair_value_gaps.length ?? "—"}</span></div><div><i className="dot violet"/> Liquidity sweeps <span>{overlays?.liquidity_sweeps.length ?? "—"}</span></div></div><div className="overlay-note">{analysisError || (overlays ? "Historical pattern observations only — not trade instructions." : "Waiting for analysis response…")}</div></article><article className="panel"><div className="panel-head"><div><h2>Zone inspection</h2><p>Review detected zones and their rule notes</p></div><span className="zone-count">{zoneItems.length} zones</span></div><div className="zone-inspector-list">{zoneItems.length ? zoneItems.slice(0,10).map(z=><button key={z.key} className={"zone-inspector-row " + (selectedZone?.key===z.key?"selected":"")} onClick={()=>setSelectedZoneKey(z.key)}><span className={"zone-swatch " + z.direction}/><span className="zone-row-main"><strong>{z.direction} {z.kind}</strong><small>{z.status} · {z.bottom.toFixed(5)} – {z.top.toFixed(5)}</small></span><span className="zone-row-arrow">›</span></button>) : <div className="empty-zones">No zones returned by the analysis engine.</div>}</div>{selectedZone && <div className="zone-detail"><div className="zone-detail-title">{selectedZone.kind} · {selectedZone.status}</div><div className="zone-detail-range">{selectedZone.bottom.toFixed(5)} — {selectedZone.top.toFixed(5)}</div><p>{selectedZone.rule}</p><small>Zone annotations are rule-based historical observations, not entry or exit instructions.</small></div>}</article><article className="panel"><div className="panel-head"><div><h2>Market-specific context</h2><p>{market} configuration</p></div></div><div className="instrument-meta-grid">{instrumentMetadata ? <><div><small>VENUE / CONTRACT</small><strong>{instrumentMetadata.venue_id} · {instrumentMetadata.contract_type}</strong></div><div><small>SESSION / TIMEZONE</small><strong>{instrumentMetadata.session} · {instrumentMetadata.timezone}</strong></div><div><small>PRICE PRECISION / TICK</small><strong>{instrumentMetadata.price_precision} decimals · {instrumentMetadata.tick_size}</strong></div></> : <div className="context-copy">Instrument metadata is loaded from the API catalogue when the backend is connected.</div>}</div><div className="context-copy">{market==="Forex"?"Session-aware analysis will account for Asia, London and New York sessions, pip precision and spread.":market==="Crypto"?"Crypto instruments will retain exchange and contract identity, with optional funding, open interest and liquidation overlays.":"Equity analysis will respect exchange calendars, trading sessions, gaps and corporate actions."}</div><div className="checklist"><div>01 <span>Confirm higher-timeframe context</span></div><div>02 <span>Identify liquidity and invalidation</span></div><div>03 <span>Validate risk and costs</span></div></div></article></section>
        <footer>ORDERBLOCK <span>•</span> Multi-market research workspace <span>•</span> Demo data only · Not investment advice</footer>
      </main>
    </div>
  );
}
export default App;
