'use client';

import { useEffect, useRef, useState } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  CandlestickData,
  LineData,
  Time,
  ColorType,
} from 'lightweight-charts';
import { useTheme } from 'next-themes';

/**
 * OHLCV data point for chart.
 */
export interface OHLCVData {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

/**
 * Chart type options.
 */
export type ChartType = 'candlestick' | 'line' | 'area';

/**
 * StockChart component props.
 */
export interface StockChartProps {
  /** OHLCV data to display */
  data: OHLCVData[];
  /** Chart type: candlestick, line, or area */
  type?: ChartType;
  /** Chart height in pixels */
  height?: number;
  /** Show volume bars */
  showVolume?: boolean;
  /** Loading state */
  loading?: boolean;
  /** Error message */
  error?: string | null;
}

/**
 * Convert date string to chart time format.
 */
function toChartTime(dateStr: string): Time {
  return dateStr as Time;
}

/**
 * StockChart component using Lightweight Charts.
 *
 * Displays stock price data as candlestick, line, or area chart.
 */
export function StockChart({
  data,
  type = 'candlestick',
  height = 300,
  showVolume = false,
  loading = false,
  error = null,
}: StockChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Candlestick' | 'Line' | 'Area'> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<'Histogram'> | null>(null);
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  // Handle hydration
  useEffect(() => {
    setMounted(true);
  }, []);

  // Create and update chart
  useEffect(() => {
    if (!chartContainerRef.current || !mounted) return;

    const isDark = resolvedTheme === 'dark';

    // Chart options
    const chartOptions = {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: isDark ? '#D1D5DB' : '#374151',
      },
      grid: {
        vertLines: { color: isDark ? '#374151' : '#E5E7EB' },
        horzLines: { color: isDark ? '#374151' : '#E5E7EB' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderColor: isDark ? '#374151' : '#E5E7EB',
      },
      timeScale: {
        borderColor: isDark ? '#374151' : '#E5E7EB',
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    };

    // Create chart if not exists
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        ...chartOptions,
        width: chartContainerRef.current.clientWidth,
        height: height,
      });

      // Create price series based on type
      if (type === 'candlestick') {
        seriesRef.current = chartRef.current.addCandlestickSeries({
          upColor: '#10B981',
          downColor: '#EF4444',
          borderUpColor: '#10B981',
          borderDownColor: '#EF4444',
          wickUpColor: '#10B981',
          wickDownColor: '#EF4444',
        });
      } else if (type === 'line') {
        seriesRef.current = chartRef.current.addLineSeries({
          color: '#3B82F6',
          lineWidth: 2,
        });
      } else {
        seriesRef.current = chartRef.current.addAreaSeries({
          lineColor: '#3B82F6',
          topColor: 'rgba(59, 130, 246, 0.4)',
          bottomColor: 'rgba(59, 130, 246, 0.0)',
          lineWidth: 2,
        });
      }

      // Create volume series if enabled
      if (showVolume) {
        volumeSeriesRef.current = chartRef.current.addHistogramSeries({
          color: '#6B7280',
          priceFormat: {
            type: 'volume',
          },
          priceScaleId: '',
        });
        volumeSeriesRef.current.priceScale().applyOptions({
          scaleMargins: {
            top: 0.8,
            bottom: 0,
          },
        });
      }
    } else {
      // Update chart options
      chartRef.current.applyOptions(chartOptions);
    }

    // Update data
    if (seriesRef.current && data.length > 0) {
      if (type === 'candlestick') {
        const candlestickData: CandlestickData[] = data.map((d) => ({
          time: toChartTime(d.date),
          open: d.open,
          high: d.high,
          low: d.low,
          close: d.close,
        }));
        seriesRef.current.setData(candlestickData as CandlestickData<Time>[]);
      } else {
        const lineData: LineData[] = data.map((d) => ({
          time: toChartTime(d.date),
          value: d.close,
        }));
        seriesRef.current.setData(lineData as LineData<Time>[]);
      }

      // Update volume data
      if (showVolume && volumeSeriesRef.current) {
        const volumeData = data.map((d, i) => ({
          time: toChartTime(d.date),
          value: d.volume,
          color: i > 0 && d.close >= data[i - 1].close ? '#10B98180' : '#EF444480',
        }));
        volumeSeriesRef.current.setData(volumeData);
      }

      // Fit content
      chartRef.current?.timeScale().fitContent();
    }

    // Handle resize
    const handleResize = () => {
      if (chartRef.current && chartContainerRef.current) {
        chartRef.current.applyOptions({
          width: chartContainerRef.current.clientWidth,
        });
      }
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [data, type, height, showVolume, resolvedTheme, mounted]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
        volumeSeriesRef.current = null;
      }
    };
  }, []);

  // Loading state
  if (loading) {
    return (
      <div
        className="flex items-center justify-center bg-muted/20 rounded-lg animate-pulse"
        style={{ height }}
      >
        <span className="text-muted-foreground">Loading chart...</span>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div
        className="flex items-center justify-center bg-destructive/10 rounded-lg"
        style={{ height }}
      >
        <span className="text-destructive">{error}</span>
      </div>
    );
  }

  // No data state
  if (!data || data.length === 0) {
    return (
      <div
        className="flex items-center justify-center border-2 border-dashed border-muted rounded-lg"
        style={{ height }}
      >
        <span className="text-muted-foreground">No data available</span>
      </div>
    );
  }

  return <div ref={chartContainerRef} style={{ height }} />;
}
