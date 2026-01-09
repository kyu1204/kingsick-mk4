'use client';

import { useEffect, useRef, useState } from 'react';
import {
  createChart,
  IChartApi,
  ISeriesApi,
  LineData,
  Time,
  ColorType,
} from 'lightweight-charts';
import { useTheme } from 'next-themes';

/**
 * Portfolio data point.
 */
export interface PortfolioDataPoint {
  date: string;
  value: number;
}

/**
 * PortfolioChart component props.
 */
export interface PortfolioChartProps {
  /** Portfolio value data over time */
  data: PortfolioDataPoint[];
  /** Chart height in pixels */
  height?: number;
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
 * PortfolioChart component using Lightweight Charts.
 *
 * Displays portfolio value over time as an area chart.
 */
export function PortfolioChart({
  data,
  height = 300,
  loading = false,
  error = null,
}: PortfolioChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Area'> | null>(null);
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

    // Calculate if overall trend is positive or negative
    const isPositive =
      data.length >= 2 ? data[data.length - 1].value >= data[0].value : true;

    // Chart options
    const chartOptions = {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: isDark ? '#D1D5DB' : '#374151',
      },
      grid: {
        vertLines: { visible: false },
        horzLines: { color: isDark ? '#374151' : '#E5E7EB' },
      },
      crosshair: {
        mode: 1,
      },
      rightPriceScale: {
        borderVisible: false,
      },
      timeScale: {
        borderVisible: false,
        timeVisible: true,
        secondsVisible: false,
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
        horzTouchDrag: true,
        vertTouchDrag: false,
      },
      handleScale: {
        axisPressedMouseMove: false,
        mouseWheel: false,
        pinch: false,
      },
    };

    // Colors based on trend
    const lineColor = isPositive ? '#10B981' : '#EF4444';
    const topColor = isPositive ? 'rgba(16, 185, 129, 0.4)' : 'rgba(239, 68, 68, 0.4)';
    const bottomColor = isPositive ? 'rgba(16, 185, 129, 0.0)' : 'rgba(239, 68, 68, 0.0)';

    // Create chart if not exists
    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        ...chartOptions,
        width: chartContainerRef.current.clientWidth,
        height: height,
      });

      seriesRef.current = chartRef.current.addAreaSeries({
        lineColor,
        topColor,
        bottomColor,
        lineWidth: 2,
      });
    } else {
      // Update chart options
      chartRef.current.applyOptions(chartOptions);

      // Update series colors
      if (seriesRef.current) {
        seriesRef.current.applyOptions({
          lineColor,
          topColor,
          bottomColor,
        });
      }
    }

    // Update data
    if (seriesRef.current && data.length > 0) {
      const chartData: LineData[] = data.map((d) => ({
        time: toChartTime(d.date),
        value: d.value,
      }));
      seriesRef.current.setData(chartData as LineData<Time>[]);

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
  }, [data, height, resolvedTheme, mounted]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
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
        <span className="text-muted-foreground">No portfolio data available</span>
      </div>
    );
  }

  return <div ref={chartContainerRef} style={{ height }} />;
}
