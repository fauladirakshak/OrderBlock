import { useEffect, useState } from "react";
import { Activity, Bell, BookOpen, CandlestickChart, ChevronDown, LayoutDashboard, Search, Settings, ShieldCheck, SlidersHorizontal, Wallet } from "lucide-react";
import TradingChart, { type ChartOverlay } from "./components/TradingChart";
import StrategyLab from "./components/StrategyLab";

type Market = "Forex" | "Crypto" | "Stocks";
type CandlePoint = { time: number; open: number; high: number; low: number; close: number };
type InstrumentMetadata = { symbol: string; venue: string; venue_id: string; contract_type: string; timezone: string; session: string; price_precision: number; tick_size: number; quote_currency: string; session_open?: string | null; session_close?: string | null };
type MarketCatalogue = { instruments: InstrumentMetadata[] };
type CandleResponse = { provider: string; is_synthetic: boolean; venue?: string; venue_id?: string; contract_type?: string; timezone?: string; session?: string; price_precision?: number; tick_size?: number; candles: Array<{ timestamp: string; open: number; high: number; low: number; close: number }> };
type MtfContext = { timeframe: string; candle_count: number; bias: "bullish" | "bearish" | "neutral"; latest_event: { kind: string; direction: string } | null; explanation: string };
type MtfAnalysis = { primary_timeframe: string; primary_bias: "bullish" | "bearish" | "neutral"; higher_timeframe_context: MtfContext[]; alignment: "bullish" | "bearish" | "mixed" | "neutral"; summary: string; notes: string[] };
type SessionSummary = { name: string; session_date: string; timezone: string; open: number; high: number; low: number; close: number; range_points: number; range_pct: number; volume: number; candle_count: number };
type SessionAnalysis = { session_model: string; latest_candle_sessions: string[]; sessions: SessionSummary[]; notes: string[] };
type LiquidityLevel = { kind: string; label: string; price: number; source_period: string; touch_count: number; swept: boolean; sweep_timestamp: string | null; sweep_index: number | null };
type LiquidityReferences = { timezone: string; levels: LiquidityLevel[]; notes: string[] };
type DealingRangeData = { high: number; low: number; equilibrium: number; current_price: number; position_pct: number; location: string; high_swing_timestamp: string; low_swing_timestamp: string };
type DealingRangeResponse = { available: boolean; range: DealingRangeData | null; notes: string[] };
type HtfRangeContext = { timeframe: string; latest_candle_timestamp: string; analysis: DealingRangeResponse };
type HtfRangeResponse = { primary_timeframe: string; primary_latest_timestamp: string; contexts: HtfRangeContext[]; notes: string[] };
type HtfZoneItem = { direction: "bullish" | "bearish"; timestamp: string; top: number; bottom: number; mitigated: boolean; invalidated?: boolean; filled?: boolean; break_kind?: string; rule: string };
type HtfZoneContext = { timeframe: string; latest_candle_timestamp: string; order_blocks: HtfZoneItem[]; fair_value_gaps: HtfZoneItem[]; notes: string[] };
type HtfZonesResponse = { primary_timeframe: string; primary_latest_timestamp: string; contexts: HtfZoneContext[]; notes: string[] };
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
  const [sessionContext, setSessionContext] = useState<SessionAnalysis | null>(null);
  const [sessionError, setSessionError] = useState("");
  const [liquidityReferences, setLiquidityReferences] = useState<LiquidityReferences | null>(null);
  const [liquidityError, setLiquidityError] = useState("");
  const [dealingRange, setDealingRange] = useState<DealingRangeData | null>(null);
  const [dealingRangeError, setDealingRangeError] = useState("");
  const [higherTimeframeRanges, setHigherTimeframeRanges] = useState<HtfRangeResponse | null>(null);
  const [higherTimeframeRangeError, setHigherTimeframeRangeError] = useState("");
  const [higherTimeframeZones, setHigherTimeframeZones] = useState<HtfZonesResponse | null>(null);
  const [higherTimeframeZonesError, setHigherTimeframeZonesError] = useState("");
  const [customSessionWindow, setCustomSessionWindow] = useState({ name: "London Open Study", timezone: "Europe/London", start: "08:00", end: "10:00" });
  const [customSessionStatus, setCustomSessionStatus] = useState("");
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
          setSessionContext(null);
          setSessionError("Session summaries appear when the FastAPI service is connected.");
          setLiquidityReferences(null);
          setLiquidityError("Liquidity reference levels appear when the FastAPI service is connected.");
          setDealingRange(null);
          setDealingRangeError("Premium/discount context appears when the FastAPI service is connected.");
          setHigherTimeframeRanges(null);
          setHigherTimeframeRangeError("Higher-timeframe dealing ranges appear when the FastAPI service is connected.");
          setHigherTimeframeZones(null);
          setHigherTimeframeZonesError("Higher-timeframe order blocks and FVGs appear when the FastAPI service is connected.");
          setOverlays(null);
          setAnalysisError("Static preview mode: backend overlays appear when the FastAPI service is connected.");
          return;
        }
        try {
          const workspaceResponse = await fetch(API_BASE + "/api/v1/analysis/workspace", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candles: payload.candles, pivot: 2 }),
            signal: controller.signal,
          });
          if (!workspaceResponse.ok) throw new Error("Analysis API returned HTTP " + workspaceResponse.status);
          const baseOverlay = await workspaceResponse.json() as ChartOverlay;
          setOverlays(baseOverlay);
          setAnalysisError("");
        } catch (failure) {
          if (failure instanceof Error && failure.name === "AbortError") return;
          setOverlays(null);
          setAnalysisError(failure instanceof Error ? failure.message : "Analysis overlays unavailable.");
        }
        try {
          const liquidityResponse = await fetch(API_BASE + "/api/v1/analysis/liquidity-references", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              candles: payload.candles,
              timezone: selectedMetadata?.timezone || "Etc/UTC",
              pivot: 2,
              tick_size: selectedMetadata?.tick_size || 0.00001,
              tolerance_ticks: 2,
            }),
            signal: controller.signal,
          });
          if (!liquidityResponse.ok) throw new Error("Liquidity reference API returned HTTP " + liquidityResponse.status);
          const references = await liquidityResponse.json() as LiquidityReferences;
          setLiquidityReferences(references);
          setLiquidityError("");
          setOverlays(current => current ? { ...current, reference_levels: references.levels } : current);
        } catch (failure) {
          if (failure instanceof Error && failure.name === "AbortError") return;
          setLiquidityReferences(null);
          setLiquidityError(failure instanceof Error ? failure.message : "Liquidity references unavailable.");
        }
        try {
          const rangeResponse = await fetch(API_BASE + "/api/v1/analysis/dealing-range", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ candles: payload.candles, pivot: 2, equilibrium_band_pct: 5 }),
            signal: controller.signal,
          });
          if (!rangeResponse.ok) throw new Error("Dealing range API returned HTTP " + rangeResponse.status);
          const rangePayload = await rangeResponse.json() as DealingRangeResponse;
          setDealingRange(rangePayload.range);
          setDealingRangeError(rangePayload.available ? "" : "Waiting for enough confirmed swing points to establish a dealing range.");
          setOverlays(current => current ? { ...current, dealing_range: rangePayload.range } : current);
        } catch (failure) {
          if (failure instanceof Error && failure.name === "AbortError") return;
          setDealingRange(null);
          setDealingRangeError(failure instanceof Error ? failure.message : "Premium/discount context unavailable.");
        }
        try {
          const sessionResponse = await fetch(API_BASE + "/api/v1/analysis/sessions", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ market: apiMarkets[market], symbol: instrument, candles: payload.candles }),
            signal: controller.signal,
          });
          if (!sessionResponse.ok) throw new Error("Session analysis API returned HTTP " + sessionResponse.status);
          setSessionContext(await sessionResponse.json() as SessionAnalysis);
          setSessionError("");
        } catch (failure) {
          if (failure instanceof Error && failure.name === "AbortError") return;
          setSessionContext(null);
          setSessionError(failure instanceof Error ? failure.message : "Session context unavailable.");
        }
        try {
          const higherTimeframes = timeframes.filter(tf => timeframeRank[tf] > timeframeRank[timeframe]);
            const contextSeries = await Promise.all(higherTimeframes.map(async tf => {
              const contextParams = new URLSearchParams({ market: apiMarkets[market], symbol: instrument, timeframe: tf, limit: "200" });
              if (selectedMetadata) { contextParams.set("venue_id", selectedMetadata.venue_id); contextParams.set("contract_type", selectedMetadata.contract_type); }
              const contextResponse = await fetch(API_BASE + "/api/v1/market-data/candles?" + contextParams.toString(), { signal: controller.signal });
              if (!contextResponse.ok) throw new Error("Unable to load " + tf + " context candles.");
              return [tf, (await contextResponse.json() as CandleResponse).candles] as const;
            }));
            // Exclude still-forming higher-timeframe candles before every context engine.
            // Provider timestamps identify candle opens; only bars whose full interval
            // ends no later than the latest primary candle open are considered closed.
            const closedContextSeries = contextSeries
              .map(([tf, series]) => [tf, series.filter(candle =>
                Date.parse(candle.timestamp) + (timeframeSeconds[tf] || 0) * 1000
                <= Date.parse(payload.candles[payload.candles.length - 1].timestamp)
              )] as const)
              .filter(([, series]) => series.length >= 5);
            if (closedContextSeries.length) {
              const contextPayload = Object.fromEntries([[timeframe, payload.candles], ...closedContextSeries]);
              const mtfResponse = await fetch(API_BASE + "/api/v1/analysis/multi-timeframe", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ primary_timeframe: timeframe, candles_by_timeframe: contextPayload, pivot: 2 }),
                signal: controller.signal,
              });
              if (!mtfResponse.ok) throw new Error("Multi-timeframe API returned HTTP " + mtfResponse.status);
              setMtf(await mtfResponse.json() as MtfAnalysis);
              setMtfError("");
              const rangeResponse = await fetch(API_BASE + "/api/v1/analysis/higher-timeframe-ranges", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  primary_timeframe: timeframe,
                  primary_candles: payload.candles,
                  higher_timeframes: contextSeries.map(([tf, series]) => ({
                    timeframe: tf,
                    candles: series.filter(candle =>
                      Date.parse(candle.timestamp) + (timeframeSeconds[tf] || 0) * 1000
                      <= Date.parse(payload.candles[payload.candles.length - 1].timestamp)
                    ),
                  })),
                  pivot: 2,
                  equilibrium_band_pct: 5,
                }),
                signal: controller.signal,
              });
              if (!rangeResponse.ok) throw new Error("Higher-timeframe dealing-range API returned HTTP " + rangeResponse.status);
              const rangePayload = await rangeResponse.json() as HtfRangeResponse;
              setHigherTimeframeRanges(rangePayload);
              setHigherTimeframeRangeError("");
              const zonesResponse = await fetch(API_BASE + "/api/v1/analysis/higher-timeframe-zones", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({
                  primary_timeframe: timeframe,
                  primary_candles: payload.candles,
                  higher_timeframes: closedContextSeries.map(([tf, series]) => ({ timeframe: tf, candles: series })),
                  pivot: 2,
                  max_zones_per_type: 8,
                }),
                signal: controller.signal,
              });
              if (!zonesResponse.ok) throw new Error("Higher-timeframe zone API returned HTTP " + zonesResponse.status);
              const zonesPayload = await zonesResponse.json() as HtfZonesResponse;
              setHigherTimeframeZones(zonesPayload);
              setHigherTimeframeZonesError("");
              setOverlays(current => current ? {
                ...current,
                higher_timeframe_zones: zonesPayload.contexts.flatMap(context => [
                  ...context.order_blocks.slice(-2).map(zone => ({
                    timeframe: context.timeframe, direction: zone.direction, kind: "OB" as const,
                    top: zone.top, bottom: zone.bottom,
                    status: zone.invalidated ? "invalidated" : zone.mitigated ? "mitigated" : "active",
                  })),
                  ...context.fair_value_gaps.slice(-2).map(zone => ({
                    timeframe: context.timeframe, direction: zone.direction, kind: "FVG" as const,
                    top: zone.top, bottom: zone.bottom,
                    status: zone.filled ? "filled" : zone.mitigated ? "mitigated" : "open",
                  })),
                ]).slice(0, 8),
              } : current);

              setOverlays(current => current ? {
                ...current,
                higher_timeframe_ranges: rangePayload.contexts
                  .filter(item => item.analysis.available && item.analysis.range)
                  .map(item => ({
                    timeframe: item.timeframe,
                    high: item.analysis.range!.high,
                    low: item.analysis.range!.low,
                    equilibrium: item.analysis.range!.equilibrium,
                    location: item.analysis.range!.location,
                  })),
              } : current);
            } else {
              setMtf(null);
              setMtfError("No completed higher-timeframe history is available for this chart yet.");
              setHigherTimeframeRanges(null);
              setHigherTimeframeZones(null);
            }
        } catch (contextFailure) {
          if (contextFailure instanceof Error && contextFailure.name === "AbortError") return;
          setMtf(null);
          setMtfError(contextFailure instanceof Error ? contextFailure.message : "Higher-timeframe context unavailable.");
          setHigherTimeframeRanges(null);
          setHigherTimeframeRangeError(contextFailure instanceof Error ? contextFailure.message : "Higher-timeframe dealing ranges unavailable.");
          setHigherTimeframeZones(null);
          setHigherTimeframeZonesError(contextFailure instanceof Error ? contextFailure.message : "Higher-timeframe zones unavailable.");
        }
      } catch (error) {
        if (error instanceof Error && error.name === "AbortError") return;
        setCandles([]);
        setSessionContext(null);
        setLiquidityReferences(null);
        setDealingRange(null);
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
  const applyCustomSessionWindow = async () => {
    if (!candles.length) return;
    setCustomSessionStatus("Calculating custom window…");
    try {
      const requestCandles = candles.map(c => ({
        timestamp: new Date(c.time * 1000).toISOString(),
        open: c.open, high: c.high, low: c.low, close: c.close,
      }));
      const response = await fetch(API_BASE + "/api/v1/analysis/sessions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          market: apiMarkets[market], symbol: instrument, candles: requestCandles,
          custom_windows: [customSessionWindow],
        }),
      });
      if (!response.ok) throw new Error("Session analysis API returned HTTP " + response.status);
      setSessionContext(await response.json() as SessionAnalysis);
      setSessionError("");
      setCustomSessionStatus("Custom window applied to the current candle history.");
    } catch (error) {
      setCustomSessionStatus(error instanceof Error ? error.message : "Unable to calculate custom window.");
    }
  };

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
        <section className="bottom-grid"><article className="panel"><div className="panel-head"><div><h2>Higher-timeframe context</h2><p>Independent structure read across larger intervals</p></div><span className={`bias-pill ${mtf?.alignment || "neutral"}`}>{mtf?.alignment?.toUpperCase() || "PENDING"}</span></div><div className="mtf-list">{mtf?.higher_timeframe_context.map(item=><div className="mtf-row" key={item.timeframe}><strong>{item.timeframe}</strong><span className={`bias-text ${item.bias}`}>{item.bias.toUpperCase()}</span><small>{item.explanation}</small></div>)}</div><div className="overlay-note">{mtf?.summary || mtfError || "Waiting for higher-timeframe analysis…"}</div><div className="context-copy">{mtf?.notes[2] || "Directional context is descriptive research, not a trade signal."}</div></article><article className="panel"><div className="panel-head"><div><h2>Live analysis overlays</h2><p>Rule-based annotations calculated from the displayed candles</p></div></div><div className="layer-list"><div><i className="dot teal"/> BOS / CHoCH <span>{overlays?.structure_events.length ?? "—"}</span></div><div><i className="dot red"/> Order blocks <span>{overlays?.order_blocks.length ?? "—"}</span></div><div><i className="dot amber"/> Fair Value Gaps <span>{overlays?.fair_value_gaps.length ?? "—"}</span></div><div><i className="dot violet"/> Liquidity sweeps <span>{overlays?.liquidity_sweeps.length ?? "—"}</span></div></div><div className="overlay-note">{analysisError || (overlays ? "Historical pattern observations only — not trade instructions." : "Waiting for analysis response…")}</div></article><article className="panel"><div className="panel-head"><div><h2>Zone inspection</h2><p>Review detected zones and their rule notes</p></div><span className="zone-count">{zoneItems.length} zones</span></div><div className="zone-inspector-list">{zoneItems.length ? zoneItems.slice(0,10).map(z=><button key={z.key} className={"zone-inspector-row " + (selectedZone?.key===z.key?"selected":"")} onClick={()=>setSelectedZoneKey(z.key)}><span className={"zone-swatch " + z.direction}/><span className="zone-row-main"><strong>{z.direction} {z.kind}</strong><small>{z.status} · {z.bottom.toFixed(5)} – {z.top.toFixed(5)}</small></span><span className="zone-row-arrow">›</span></button>) : <div className="empty-zones">No zones returned by the analysis engine.</div>}</div>{selectedZone && <div className="zone-detail"><div className="zone-detail-title">{selectedZone.kind} · {selectedZone.status}</div><div className="zone-detail-range">{selectedZone.bottom.toFixed(5)} — {selectedZone.top.toFixed(5)}</div><p>{selectedZone.rule}</p><small>Zone annotations are rule-based historical observations, not entry or exit instructions.</small></div>}</article><article className="panel"><div className="panel-head"><div><h2>Premium / discount</h2><p>Latest eligible confirmed swing range</p></div><span className={"bias-pill " + (dealingRange?.location || "neutral")}>{dealingRange?.location?.replace("_"," ").toUpperCase() || "PENDING"}</span></div>{dealingRange ? <div className="instrument-meta-grid"><div><small>RANGE HIGH</small><strong>{dealingRange.high.toFixed(instrumentMetadata?.price_precision ?? 5)}</strong></div><div><small>EQUILIBRIUM · 50%</small><strong>{dealingRange.equilibrium.toFixed(instrumentMetadata?.price_precision ?? 5)}</strong></div><div><small>RANGE LOW</small><strong>{dealingRange.low.toFixed(instrumentMetadata?.price_precision ?? 5)}</strong></div><div><small>PRICE POSITION</small><strong>{dealingRange.position_pct.toFixed(1)}% of range</strong></div></div> : <div className="overlay-note">{dealingRangeError || "Waiting for confirmed swing range…"}</div>}<div className="overlay-note">Premium/discount is geometric context, not a directional prediction or entry instruction.</div></article><article className="panel"><div className="panel-head"><div><h2>Higher-timeframe dealing ranges</h2><p>Independent confirmed swing ranges · {higherTimeframeRanges?.primary_timeframe || timeframe} chart</p></div><span className="zone-count">{higherTimeframeRanges?.contexts.length ?? "—"} contexts</span></div><div className="session-context-list">{higherTimeframeRanges?.contexts.map(item=><div className="session-context-row" key={item.timeframe}><div><strong>{item.timeframe} · {item.analysis.range?.location?.replace("_"," ").toUpperCase() || "UNAVAILABLE"}</strong><small>Latest supplied candle · {new Date(item.latest_candle_timestamp).toLocaleString()}</small></div><div className="session-range">{item.analysis.range ? <><strong>{item.analysis.range.equilibrium.toFixed(instrumentMetadata?.price_precision ?? 5)}</strong><small>{item.analysis.range.low.toFixed(instrumentMetadata?.price_precision ?? 5)} – {item.analysis.range.high.toFixed(instrumentMetadata?.price_precision ?? 5)}</small></> : <small>Waiting for confirmed swing pair</small>}</div></div>)}</div><div className="overlay-note">{higherTimeframeRangeError || (higherTimeframeRanges?.notes[0] ?? "Waiting for higher-timeframe dealing ranges…")}</div><div className="context-copy">Completed higher-timeframe candles only. These ranges are geometric context, not trade signals.</div></article><article className="panel"><div className="panel-head"><div><h2>Higher-timeframe order blocks & FVGs</h2><p>Independent HTF zones · {higherTimeframeZones?.primary_timeframe || timeframe} chart</p></div><span className="zone-count">{higherTimeframeZones?.contexts.length ?? "—"} timeframes</span></div>{higherTimeframeZones?.contexts.map(context=><div className="htf-zone-group" key={context.timeframe}><div className="lab-divider-title">{context.timeframe} CONTEXT</div>{[...context.order_blocks.slice(-4).map(zone=>({...zone,kind:"ORDER BLOCK",status:zone.invalidated?"INVALIDATED":zone.mitigated?"MITIGATED":"ACTIVE"})),...context.fair_value_gaps.slice(-4).map(zone=>({...zone,kind:"FAIR VALUE GAP",status:zone.filled?"FILLED":zone.mitigated?"TOUCHED":"OPEN"}))].slice(-6).map((zone,index)=><div className="session-context-row" key={zone.kind+"-"+zone.timestamp+"-"+index}><div><strong>{zone.direction.toUpperCase()} · {zone.kind}</strong><small>{zone.status} · {new Date(zone.timestamp).toLocaleString()}</small></div><div className="session-range"><strong>{zone.bottom.toFixed(instrumentMetadata?.price_precision ?? 5)} – {zone.top.toFixed(instrumentMetadata?.price_precision ?? 5)}</strong><small>{zone.rule}</small></div></div>)}{!context.order_blocks.length && !context.fair_value_gaps.length && <div className="overlay-note">No qualifying zones in this supplied history.</div>}</div>)}<div className="overlay-note">{higherTimeframeZonesError || (higherTimeframeZones?.notes[0] ?? "Waiting for higher-timeframe zone analysis…")}</div><div className="context-copy">Mitigation and fill are evaluated within each source timeframe. These are rule-based observations, not trade instructions.</div></article><article className="panel"><div className="panel-head"><div><h2>Liquidity reference levels</h2><p>Previous periods and confirmed equal swings · {liquidityReferences?.timezone || "instrument timezone"}</p></div><span className="zone-count">{liquidityReferences?.levels.length ?? "—"} levels</span></div><div className="session-context-list">{liquidityReferences?.levels.slice(0,8).map((level,i)=><div className="session-context-row" key={level.kind+"-"+level.source_period+"-"+i}><div><strong>{level.label} {level.swept ? "· Swept" : "· Untouched"}</strong><small>{level.source_period} · {level.touch_count} touch{level.touch_count===1?"":"es"}</small></div><div className="session-range"><strong>{level.price.toFixed(instrumentMetadata?.price_precision ?? 5)}</strong><small>{level.sweep_timestamp ? new Date(level.sweep_timestamp).toLocaleString() : "Reference price"}</small></div></div>)}</div><div className="overlay-note">{liquidityError || (liquidityReferences?.notes[0] ?? "Waiting for liquidity reference analysis…")}</div></article><article className="panel"><div className="panel-head"><div><h2>Session context</h2><p>{sessionContext?.session_model || "Timezone-aware trading windows"}</p></div><span className="zone-count">{sessionContext?.latest_candle_sessions.length ? sessionContext.latest_candle_sessions.join(" / ") : "—"}</span></div><div className="session-context-list">{sessionContext?.sessions.slice(-6).reverse().map((item,i)=><div className="session-context-row" key={item.name+"-"+item.session_date}><div><strong>{item.name}</strong><small>{item.session_date} · {item.timezone}</small></div><div className="session-range"><strong>{item.range_pct.toFixed(2)}%</strong><small>{item.low.toFixed(instrumentMetadata?.price_precision ?? 5)} – {item.high.toFixed(instrumentMetadata?.price_precision ?? 5)}</small></div></div>)}</div><div className="overlay-note">{sessionError || (sessionContext?.notes[0] ?? "Waiting for session analysis…")}</div><div className="lab-divider-title">CUSTOM SESSION WINDOW</div><div className="lab-fields"><label className="lab-field">Window name<input value={customSessionWindow.name} onChange={e=>setCustomSessionWindow(v=>({...v,name:e.target.value}))}/></label><label className="lab-field">IANA timezone<input value={customSessionWindow.timezone} onChange={e=>setCustomSessionWindow(v=>({...v,timezone:e.target.value}))} placeholder="Europe/London"/></label><label className="lab-field">Local start<input value={customSessionWindow.start} onChange={e=>setCustomSessionWindow(v=>({...v,start:e.target.value}))} placeholder="08:00"/></label><label className="lab-field">Local end<input value={customSessionWindow.end} onChange={e=>setCustomSessionWindow(v=>({...v,end:e.target.value}))} placeholder="10:00"/></label></div><button className="lab-run lab-run-secondary" onClick={()=>void applyCustomSessionWindow()} disabled={!candles.length || !customSessionWindow.name || !customSessionWindow.timezone}>Apply to current chart</button>{customSessionStatus && <div className="lab-message">{customSessionStatus}</div>}</article><article className="panel"><div className="panel-head"><div><h2>Market-specific context</h2><p>{market} configuration</p></div></div><div className="instrument-meta-grid">{instrumentMetadata ? <><div><small>VENUE / CONTRACT</small><strong>{instrumentMetadata.venue_id} · {instrumentMetadata.contract_type}</strong></div><div><small>SESSION / TIMEZONE</small><strong>{instrumentMetadata.session} · {instrumentMetadata.timezone}</strong></div><div><small>PRICE PRECISION / TICK</small><strong>{instrumentMetadata.price_precision} decimals · {instrumentMetadata.tick_size}</strong></div></> : <div className="context-copy">Instrument metadata is loaded from the API catalogue when the backend is connected.</div>}</div><div className="context-copy">{market==="Forex"?"Session-aware analysis will account for Asia, London and New York sessions, pip precision and spread.":market==="Crypto"?"Crypto instruments will retain exchange and contract identity, with optional funding, open interest and liquidation overlays.":"Equity analysis will respect exchange calendars, trading sessions, gaps and corporate actions."}</div><div className="checklist"><div>01 <span>Confirm higher-timeframe context</span></div><div>02 <span>Identify liquidity and invalidation</span></div><div>03 <span>Validate risk and costs</span></div></div></article></section>
        {activeTab === "Strategy lab" && <StrategyLab apiBase={API_BASE} market={apiMarkets[market]} symbol={instrument} timeframe={timeframe}/>}
        <footer>ORDERBLOCK <span>•</span> Multi-market research workspace <span>•</span> Demo data only · Not investment advice</footer>
      </main>
    </div>
  );
}
export default App;
