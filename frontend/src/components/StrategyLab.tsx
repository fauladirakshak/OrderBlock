import { useState } from "react";

type Candle = { timestamp: string; open: number; high: number; low: number; close: number; volume?: number };
type ImportedSeries = { provider: string; is_synthetic: boolean; symbol: string; market: string; timeframe: string; candle_count: number; candles: Candle[] };
type Trade = { direction: string; signal_timestamp: string; entry_timestamp: string; exit_timestamp: string; entry_price: number; exit_price: number; stop_price: number; target_price: number; quantity: number; gross_pnl: number; fees: number; net_pnl: number; r_multiple: number; exit_reason: string };
type Result = { metrics: { starting_equity: number; ending_equity: number; net_profit: number; total_return_pct: number; trade_count: number; winning_trades: number; losing_trades: number; win_rate_pct: number; profit_factor: number | null; expectancy: number; average_r: number; max_drawdown_pct: number }; trades: Trade[]; notes: string[]; execution_model: string };

type Props = { apiBase: string; market: string; symbol: string; timeframe: string };

export default function StrategyLab({ apiBase, market, symbol, timeframe }: Props) {
  const [series, setSeries] = useState<ImportedSeries | null>(null);
  const [timezone, setTimezone] = useState("UTC");
  const [startingEquity, setStartingEquity] = useState("10000");
  const [riskPct, setRiskPct] = useState("1");
  const [targetR, setTargetR] = useState("2");
  const [commission, setCommission] = useState("2");
  const [spread, setSpread] = useState("1");
  const [slippage, setSlippage] = useState("1");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("Import a historical OHLCV CSV to begin. Synthetic preview candles are not accepted as backtest data.");
  const [error, setError] = useState("");
  const [result, setResult] = useState<Result | null>(null);

  async function importFile(file?: File) {
    if (!file) return;
    setBusy(true); setError(""); setResult(null); setMessage("Validating and importing CSV…");
    try {
      const csvText = await file.text();
      const response = await fetch(apiBase + "/api/v1/market-data/import/csv", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ symbol, market, timeframe, timezone, csv_text: csvText }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "CSV import failed.");
      setSeries(payload as ImportedSeries);
      setMessage("Imported " + payload.candle_count + " candles from " + file.name + ". Source: user-supplied CSV.");
    } catch (failure) {
      setSeries(null);
      setError(failure instanceof Error ? failure.message : "CSV import failed.");
      setMessage("");
    } finally { setBusy(false); }
  }

  async function run() {
    if (!series) return;
    setBusy(true); setError(""); setResult(null); setMessage("Running prefix-replay backtest…");
    try {
      const response = await fetch(apiBase + "/api/v1/backtests/run", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          candles: series.candles,
          profile: { pivot: 2, sweep_lookback: 20, atr_period: 14, min_displacement_atr: 1.2, min_body_fraction: 0.6, require_fvg: true },
          starting_equity: Number(startingEquity), risk_per_trade_pct: Number(riskPct),
          target_r_multiple: Number(targetR), commission_bps: Number(commission),
          spread_bps: Number(spread), slippage_bps: Number(slippage),
        }),
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Backtest failed.");
      setResult(payload as Result);
      setMessage("Backtest complete. Results are historical simulation only.");
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "Backtest failed.");
      setMessage("");
    } finally { setBusy(false); }
  }

  function downloadTrades() {
    if (!result) return;
    const columns = ["direction","signal_timestamp","entry_timestamp","exit_timestamp","entry_price","exit_price","stop_price","target_price","quantity","gross_pnl","fees","net_pnl","r_multiple","exit_reason"];
    const csv = [columns.join(","), ...result.trades.map(t => columns.map(k => JSON.stringify((t as any)[k] ?? "")).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = "orderblock-trades.csv"; anchor.click(); URL.revokeObjectURL(url);
  }

  const m = result?.metrics;
  return <section className="strategy-lab">
    <div className="strategy-heading"><div><div className="eyebrow">PHASE 3 · HISTORICAL RESEARCH</div><h2>Strategy lab</h2><p>Import real historical OHLCV data, configure risk and evaluate the current ICT-inspired setup profile.</p></div><span className="lab-status">NO LIVE EXECUTION</span></div>
    <div className="lab-grid">
      <article className="panel lab-card">
        <h3>01 · Historical data</h3><p>Use a CSV with timestamp, open, high, low, close and optional volume. Naive timestamps use the timezone below.</p>
        <label className="lab-field">Source timezone (IANA)<input value={timezone} onChange={e=>setTimezone(e.target.value)} placeholder="Asia/Kolkata"/></label>
        <label className="lab-upload">Choose OHLCV CSV<input type="file" accept=".csv,text/csv" onChange={e=>void importFile(e.target.files?.[0])}/></label>
        {series && <div className="import-summary"><strong>{series.symbol} · {series.timeframe}</strong><span>{series.candle_count.toLocaleString()} candles · {series.provider}</span><span>UTC-normalized · user-supplied source</span></div>}
        <div className="lab-note">No Twelve Data, paid feed or broker account is required. Data ownership and usage rights remain your responsibility.</div>
      </article>
      <article className="panel lab-card">
        <h3>02 · Risk and execution costs</h3><p>These assumptions are applied consistently to each simulated trade.</p>
        <div className="lab-fields">
          <label className="lab-field">Starting equity<input type="number" min="1" value={startingEquity} onChange={e=>setStartingEquity(e.target.value)}/></label>
          <label className="lab-field">Risk per trade (%)<input type="number" min="0.01" max="10" step="0.1" value={riskPct} onChange={e=>setRiskPct(e.target.value)}/></label>
          <label className="lab-field">Target (R multiple)<input type="number" min="0.1" max="20" step="0.1" value={targetR} onChange={e=>setTargetR(e.target.value)}/></label>
          <label className="lab-field">Commission (bps)<input type="number" min="0" value={commission} onChange={e=>setCommission(e.target.value)}/></label>
          <label className="lab-field">Spread (bps)<input type="number" min="0" value={spread} onChange={e=>setSpread(e.target.value)}/></label>
          <label className="lab-field">Slippage (bps)<input type="number" min="0" value={slippage} onChange={e=>setSlippage(e.target.value)}/></label>
        </div>
        <button className="lab-run" disabled={!series || busy} onClick={()=>void run()}>{busy ? "Processing…" : "Run backtest"}</button>
      </article>
    </div>
    {message && <div className="lab-message">{message}</div>}
    {error && <div className="lab-error">{error}</div>}
    {m && <article className="panel results-panel">
      <div className="panel-head"><div><h3>Backtest results</h3><p>{series?.symbol} · {series?.timeframe} · {series?.candle_count} imported candles</p></div><button className="lab-export" onClick={downloadTrades}>Export trades CSV</button></div>
      <div className="result-metrics">
        <div><small>NET PROFIT</small><strong className={m.net_profit >= 0 ? "positive" : "negative"}>{m.net_profit.toFixed(2)}</strong></div>
        <div><small>RETURN</small><strong>{m.total_return_pct.toFixed(2)}%</strong></div>
        <div><small>TRADES</small><strong>{m.trade_count}</strong></div>
        <div><small>WIN RATE</small><strong>{m.win_rate_pct.toFixed(1)}%</strong></div>
        <div><small>PROFIT FACTOR</small><strong>{m.profit_factor === null ? "—" : m.profit_factor.toFixed(2)}</strong></div>
        <div><small>MAX DRAWDOWN</small><strong>{m.max_drawdown_pct.toFixed(2)}%</strong></div>
        <div><small>EXPECTANCY</small><strong>{m.expectancy.toFixed(2)}</strong></div>
        <div><small>AVERAGE R</small><strong>{m.average_r.toFixed(2)}R</strong></div>
      </div>
      <div className="lab-execution">{result?.execution_model}</div>
      <div className="trade-table-wrap"><table className="trade-table"><thead><tr><th>Side</th><th>Entry</th><th>Exit</th><th>Entry px</th><th>Exit px</th><th>Net PnL</th><th>R</th><th>Reason</th></tr></thead><tbody>
        {result?.trades.map((t,i)=><tr key={i}><td>{t.direction}</td><td>{new Date(t.entry_timestamp).toLocaleString()}</td><td>{new Date(t.exit_timestamp).toLocaleString()}</td><td>{t.entry_price.toFixed(5)}</td><td>{t.exit_price.toFixed(5)}</td><td className={t.net_pnl>=0?"positive":"negative"}>{t.net_pnl.toFixed(2)}</td><td>{t.r_multiple.toFixed(2)}</td><td>{t.exit_reason}</td></tr>)}
        {!result?.trades.length && <tr><td colSpan={8}>No qualifying setups found in this dataset.</td></tr>}
      </tbody></table></div>
      <ul className="lab-notes">{result?.notes.map((n,i)=><li key={i}>{n}</li>)}</ul>
    </article>}
  </section>;
}
