import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type UTCTimestamp,
  type SeriesMarker,
  type IChartApi,
  type ISeriesApi,
  type CandlestickSeries as CandlestickSeriesType,
} from "lightweight-charts";

export type TradingCandle = { time: number; open: number; high: number; low: number; close: number };
export type ChartOverlay = {
  structure_events: Array<{ kind: "BOS" | "CHoCH"; direction: "bullish" | "bearish"; level: number; candle_index: number; timestamp: string; explanation: string }>;
  order_blocks: Array<{ direction: "bullish" | "bearish"; candle_index: number; timestamp: string; top: number; bottom: number; break_kind: "BOS" | "CHoCH"; mitigated: boolean; invalidated: boolean; rule: string }>;
  fair_value_gaps: Array<{ direction: "bullish" | "bearish"; middle_candle_index: number; timestamp: string; top: number; bottom: number; mitigated: boolean; filled: boolean; rule: string }>;
  liquidity_sweeps: Array<{ direction: "bullish" | "bearish"; candle_index: number; timestamp: string; level: number; explanation: string }>;
};
type TradingChartProps = { candles: TradingCandle[]; overlays?: ChartOverlay | null; ariaLabel?: string };

export default function TradingChart({ candles, overlays, ariaLabel = "Interactive candlestick chart with price-action annotations" }: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    const canvas = canvasRef.current;
    if (!container || !canvas) return;
    const chart = createChart(container, {
      autoSize: true,
      layout: { background: { type: ColorType.Solid, color: "#0e151d" }, textColor: "#84919c", fontFamily: "DM Mono, monospace", fontSize: 10 },
      grid: { vertLines: { color: "#1c2832" }, horzLines: { color: "#1c2832" } },
      rightPriceScale: { borderColor: "#26333e", scaleMargins: { top: 0.12, bottom: 0.12 } },
      timeScale: { borderColor: "#26333e", timeVisible: true, secondsVisible: false },
      crosshair: { vertLine: { color: "#71838e", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#263a43" }, horzLine: { color: "#71838e", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#263a43" } },
      handleScroll: true, handleScale: true,
    });
    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#55bba5", downColor: "#ca7275", borderUpColor: "#55bba5", borderDownColor: "#ca7275", wickUpColor: "#62c4ae", wickDownColor: "#d77c7c",
    });
    const data: CandlestickData<UTCTimestamp>[] = candles.map(c => ({ time: c.time as UTCTimestamp, open: c.open, high: c.high, low: c.low, close: c.close }));
    series.setData(data);

    const markers: SeriesMarker<UTCTimestamp>[] = [];
    for (const event of overlays?.structure_events ?? []) {
      const candle = candles[event.candle_index]; if (!candle) continue;
      markers.push({ time: candle.time as UTCTimestamp, position: event.direction === "bullish" ? "belowBar" : "aboveBar", color: event.direction === "bullish" ? "#65c9b5" : "#df8585", shape: event.direction === "bullish" ? "arrowUp" : "arrowDown", text: event.kind, size: 1 });
    }
    for (const sweep of overlays?.liquidity_sweeps ?? []) {
      const candle = candles[sweep.candle_index]; if (!candle) continue;
      markers.push({ time: candle.time as UTCTimestamp, position: sweep.direction === "bullish" ? "belowBar" : "aboveBar", color: "#d5a45e", shape: "circle", text: sweep.direction === "bullish" ? "SSL sweep" : "BSL sweep", size: 1 });
    }
    markers.sort((a,b) => Number(a.time)-Number(b.time));
    createSeriesMarkers(series, markers);

    // Retain subtle boundary lines as a fallback if the canvas layer is unavailable.
    const visibleStart = Math.max(0, candles.length - 100);
    for (const zone of (overlays?.order_blocks ?? []).filter(z => z.candle_index >= visibleStart).slice(-8)) {
      const color = zone.direction === "bullish" ? "#4fae9a" : "#c96f75";
      series.createPriceLine({ price: zone.top, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: zone.invalidated ? "OB invalid" : zone.mitigated ? "OB mitigated" : "OB" });
      series.createPriceLine({ price: zone.bottom, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: false, title: "" });
    }
    for (const gap of (overlays?.fair_value_gaps ?? []).filter(g => g.middle_candle_index >= visibleStart).slice(-8)) {
      const color = gap.direction === "bullish" ? "#548fc4" : "#a58bd2";
      series.createPriceLine({ price: gap.top, color, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: gap.filled ? "FVG filled" : gap.mitigated ? "FVG touched" : "FVG" });
      series.createPriceLine({ price: gap.bottom, color, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: false, title: "" });
    }

    const ctx = canvas.getContext("2d");
    const drawZones = () => {
      if (!ctx) return;
      const rect = container.getBoundingClientRect();
      const dpr = window.devicePixelRatio || 1;
      canvas.width = Math.max(1, Math.floor(rect.width * dpr));
      canvas.height = Math.max(1, Math.floor(rect.height * dpr));
      canvas.style.width = rect.width + "px";
      canvas.style.height = rect.height + "px";
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, rect.width, rect.height);
      const right = chart.timeScale().width();
      const draw = (index: number, top: number, bottom: number, fill: string, stroke: string, label: string, status: string) => {
        const candle = candles[index];
        if (!candle) return;
        const x = chart.timeScale().timeToCoordinate(candle.time as UTCTimestamp);
        const yTop = series.priceToCoordinate(top);
        const yBottom = series.priceToCoordinate(bottom);
        if (x === null || yTop === null || yBottom === null) return;
        const left = Math.max(0, x);
        const width = Math.max(0, right - left);
        const y = Math.min(yTop, yBottom);
        const height = Math.max(1, Math.abs(yBottom-yTop));
        if (left >= right || y > rect.height || y + height < 0) return;
        ctx.fillStyle = fill; ctx.strokeStyle = stroke; ctx.lineWidth = 1;
        ctx.fillRect(left, y, width, height);
        ctx.strokeRect(left + .5, y + .5, Math.max(0,width-1), Math.max(0,height-1));
        ctx.save(); ctx.beginPath(); ctx.rect(left, Math.max(0,y), width, Math.min(rect.height,Math.max(14,height))); ctx.clip();
        ctx.font = "9px 'DM Mono', monospace"; ctx.fillStyle = stroke;
        ctx.fillText(label + (status ? " · " + status : ""), left + 5, Math.max(11,y+11));
        ctx.restore();
      };
      for (const z of (overlays?.order_blocks ?? []).filter(z => z.candle_index >= visibleStart).slice(-8)) {
        const bullish = z.direction === "bullish";
        draw(z.candle_index,z.top,z.bottom,z.invalidated?"rgba(130,130,130,.045)":bullish?"rgba(65,173,145,.13)":"rgba(199,103,112,.13)",z.invalidated?"#7d8991":bullish?"#55bba5":"#d17b82",bullish?"Bullish OB":"Bearish OB",z.invalidated?"invalid":z.mitigated?"mitigated":"active");
      }
      for (const z of (overlays?.fair_value_gaps ?? []).filter(z => z.middle_candle_index >= visibleStart).slice(-8)) {
        const bullish = z.direction === "bullish";
        draw(z.middle_candle_index,z.top,z.bottom,z.filled?"rgba(130,130,130,.035)":bullish?"rgba(75,137,194,.12)":"rgba(159,126,202,.12)",z.filled?"#77838c":bullish?"#649ed0":"#aa91d0",bullish?"Bullish FVG":"Bearish FVG",z.filled?"filled":z.mitigated?"touched":"open");
      }
    };
    chart.timeScale().fitContent();
    drawZones();
    const onVisibleRange = () => drawZones();
    chart.timeScale().subscribeVisibleTimeRangeChange(onVisibleRange);
    const observer = new ResizeObserver(drawZones);
    observer.observe(container);
    return () => { observer.disconnect(); chart.timeScale().unsubscribeVisibleTimeRangeChange(onVisibleRange); chart.remove(); };
  }, [candles, overlays]);

  return <div className="chart-stage" role="img" aria-label={ariaLabel}>
    <div ref={containerRef} className="chart-canvas" />
    <canvas ref={canvasRef} className="zone-overlay" aria-hidden="true" />
  </div>;
}
