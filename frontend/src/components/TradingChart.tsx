import { useEffect, useRef } from "react";
import {
  CandlestickSeries,
  ColorType,
  LineStyle,
  createChart,
  type CandlestickData,
  type IChartApi,
  type UTCTimestamp,
} from "lightweight-charts";

export type TradingCandle = {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
};

type TradingChartProps = {
  candles: TradingCandle[];
  ariaLabel?: string;
};

export default function TradingChart({
  candles,
  ariaLabel = "Interactive candlestick chart",
}: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

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
        horzLine: { color: "#71838e", width: 1, style: 2, labelBackgroundColor: "#263a43" },
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
    chart.timeScale().fitContent();
    chartRef.current = chart;

    return () => {
      chart.remove();
      chartRef.current = null;
    };
  }, [candles]);

  return (
    <div
      ref={containerRef}
      role="img"
      aria-label={ariaLabel}
      style={{ width: "100%", height: "320px", minHeight: "260px" }}
    />
  );
}
