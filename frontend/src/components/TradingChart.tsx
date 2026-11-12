import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  LineStyle,
  createChart,
  createSeriesMarkers,
  type CandlestickData,
  type IChartApi,
  type UTCTimestamp,
  type SeriesMarker,
} from "lightweight-charts";

export type TradingCandle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
};

export type ChartOverlay = {
  structure_events: Array<{ kind: "BOS" | "CHoCH"; direction: "bullish" | "bearish"; level: number; candle_index: number; timestamp: string; explanation: string }>;
  order_blocks: Array<{ direction: "bullish" | "bearish"; candle_index: number; timestamp: string; top: number; bottom: number; break_kind: "BOS" | "CHoCH"; mitigated: boolean; invalidated: boolean; rule: string }>;
  fair_value_gaps: Array<{ direction: "bullish" | "bearish"; middle_candle_index: number; timestamp: string; top: number; bottom: number; mitigated: boolean; filled: boolean; rule: string }>;
  liquidity_sweeps: Array<{ direction: "bullish" | "bearish"; candle_index: number; timestamp: string; level: number; explanation: string }>;
};

type TradingChartProps = {
  candles: TradingCandle[];
  overlays?: ChartOverlay | null;
  ariaLabel?: string;
};

export default function TradingChart({
  candles,
  overlays,
  ariaLabel = "Interactive candlestick chart with price-action annotations",
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "#0e151d" },
        textColor: "#84919c",
        fontFamily: "DM Mono, monospace",
        fontSize: 10,
      },
      grid: {
        vertLines: { color: "#1c2832" },
        horzLines: { color: "#1c2832" },
      },
      rightPriceScale: {
        borderColor: "#26333e",
        scaleMargins: { top: 0.12, bottom: 0.12 },
      },
      timeScale: {
        borderColor: "#26333e",
        timeVisible: true,
        secondsVisible: false,
      },
      crosshair: {
        vertLine: { color: "#71838e", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#263a43" },
        horzLine: { color: "#71838e", width: 1, style: LineStyle.Dashed, labelBackgroundColor: "#263a43" },
      },
      handleScroll: true,
      handleScale: true,
    });

    const series = chart.addSeries(CandlestickSeries, {
      upColor: "#55bba5",
      downColor: "#ca7275",
      borderUpColor: "#55bba5",
      borderDownColor: "#ca7275",
      wickUpColor: "#62c4ae",
      wickDownColor: "#d77c7c",
    });

    const data: CandlestickData<UTCTimestamp>[] = candles.map((candle) => ({
      time: candle.time as UTCTimestamp,
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    }));
    series.setData(data);

    const markerItems: SeriesMarker<UTCTimestamp>[] = [];
    for (const event of overlays?.structure_events ?? []) {
      const candle = candles[event.candle_index];
      if (!candle) continue;
      markerItems.push({
        time: candle.time as UTCTimestamp,
        position: event.direction === "bullish" ? "belowBar" : "aboveBar",
        color: event.direction === "bullish" ? "#65c9b5" : "#df8585",
        shape: event.direction === "bullish" ? "arrowUp" : "arrowDown",
        text: event.kind,
        size: 1,
      });
    }
    for (const sweep of overlays?.liquidity_sweeps ?? []) {
      const candle = candles[sweep.candle_index];
      if (!candle) continue;
      markerItems.push({
        time: candle.time as UTCTimestamp,
        position: sweep.direction === "bullish" ? "belowBar" : "aboveBar",
        color: "#d5a45e",
        shape: "circle",
        text: sweep.direction === "bullish" ? "SSL sweep" : "BSL sweep",
        size: 1,
      });
    }
    markerItems.sort((a, b) => Number(a.time) - Number(b.time));
    createSeriesMarkers(series, markerItems);

    const visibleStart = Math.max(0, candles.length - 100);
    for (const zone of (overlays?.order_blocks ?? []).filter(z => z.candle_index >= visibleStart).slice(-8)) {
      const color = zone.direction === "bullish" ? "#4fae9a" : "#c96f75";
      const label = zone.invalidated ? "OB invalid" : zone.mitigated ? "OB mitigated" : "OB";
      series.createPriceLine({ price: zone.top, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: label + " top" });
      series.createPriceLine({ price: zone.bottom, color, lineWidth: 1, lineStyle: LineStyle.Dashed, axisLabelVisible: true, title: label + " bottom" });
    }
    for (const gap of (overlays?.fair_value_gaps ?? []).filter(g => g.middle_candle_index >= visibleStart).slice(-8)) {
      const color = gap.direction === "bullish" ? "#548fc4" : "#a58bd2";
      const label = gap.filled ? "FVG filled" : gap.mitigated ? "FVG touched" : "FVG";
      series.createPriceLine({ price: gap.top, color, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: label + " top" });
      series.createPriceLine({ price: gap.bottom, color, lineWidth: 1, lineStyle: LineStyle.Dotted, axisLabelVisible: true, title: label + " bottom" });
    }

    chart.timeScale().fitContent();
    return () => chart.remove();
  }, [candles, overlays]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      style={{ width: "100%", height: "360px", minHeight: "300px" }}
    />
  );
}
