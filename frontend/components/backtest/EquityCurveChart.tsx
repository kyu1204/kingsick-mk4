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

export interface EquityCurveChartProps {
  dailyEquity: number[];
  startDate: string;
}

export function EquityCurveChart({ dailyEquity, startDate }: EquityCurveChartProps) {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const seriesRef = useRef<ISeriesApi<'Line'> | null>(null);
  const { resolvedTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!chartContainerRef.current || !mounted) return;

    const isDark = resolvedTheme === 'dark';

    const chartOptions = {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: isDark ? '#D1D5DB' : '#374151',
      },
      grid: {
        vertLines: { color: isDark ? '#374151' : '#E5E7EB' },
        horzLines: { color: isDark ? '#374151' : '#E5E7EB' },
      },
      rightPriceScale: {
        borderColor: isDark ? '#374151' : '#E5E7EB',
      },
      timeScale: {
        borderColor: isDark ? '#374151' : '#E5E7EB',
      },
      handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
      },
      handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
      },
    };

    if (!chartRef.current) {
      chartRef.current = createChart(chartContainerRef.current, {
        ...chartOptions,
        width: chartContainerRef.current.clientWidth,
        height: 300,
      });

      seriesRef.current = chartRef.current.addLineSeries({
        color: '#3B82F6',
        lineWidth: 2,
      });
    } else {
      chartRef.current.applyOptions(chartOptions);
    }

    if (seriesRef.current && dailyEquity.length > 0) {
      const start = new Date(startDate);
      const data: LineData[] = dailyEquity.map((value, index) => {
        const date = new Date(start);
        date.setDate(date.getDate() + index);
        return {
          time: date.toISOString().split('T')[0] as Time,
          value: value,
        };
      });

      seriesRef.current.setData(data);
      chartRef.current?.timeScale().fitContent();
    }

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
  }, [dailyEquity, startDate, resolvedTheme, mounted]);

  useEffect(() => {
    return () => {
      if (chartRef.current) {
        chartRef.current.remove();
        chartRef.current = null;
        seriesRef.current = null;
      }
    };
  }, []);

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
}
