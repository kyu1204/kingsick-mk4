import * as React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui';
import { BacktestResult } from '@/lib/api/backtest';
import { cn, formatKRW, formatPercent } from '@/lib/utils';
import { ArrowDownIcon, ArrowUpIcon, MinusIcon } from 'lucide-react';

interface MetricsCardsProps {
  result: BacktestResult;
}

interface MetricItemProps {
  title: string;
  value: string;
  subValue?: string;
  trend?: 'up' | 'down' | 'neutral';
  className?: string;
}

const MetricItem = ({ title, value, subValue, trend, className }: MetricItemProps) => (
  <Card className={cn("overflow-hidden", className)}>
    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
      <CardTitle className="text-sm font-medium text-muted-foreground">
        {title}
      </CardTitle>
      {trend === 'up' && <ArrowUpIcon className="h-4 w-4 text-profit" />}
      {trend === 'down' && <ArrowDownIcon className="h-4 w-4 text-loss" />}
      {trend === 'neutral' && <MinusIcon className="h-4 w-4 text-muted-foreground" />}
    </CardHeader>
    <CardContent>
      <div className={cn("text-2xl font-bold", 
        trend === 'up' && "text-profit",
        trend === 'down' && "text-loss"
      )}>
        {value}
      </div>
      {subValue && (
        <p className="text-xs text-muted-foreground mt-1">
          {subValue}
        </p>
      )}
    </CardContent>
  </Card>
);

export function MetricsCards({ result }: MetricsCardsProps) {
  const isProfit = result.total_return_pct >= 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <MetricItem
        title="총 수익률"
        value={formatPercent(result.total_return_pct)}
        subValue={`${formatKRW(result.final_capital - result.initial_capital)}`}
        trend={isProfit ? 'up' : 'down'}
      />
      
      <MetricItem
        title="승률"
        value={formatPercent(result.win_rate)}
        subValue={`${result.winning_trades}승 / ${result.losing_trades}패`}
        trend={result.win_rate >= 50 ? 'up' : 'down'}
      />

      <MetricItem
        title="손익비"
        value={result.profit_factor.toFixed(2)}
        subValue={result.profit_factor >= 1.5 ? "우수" : result.profit_factor >= 1.0 ? "양호" : "미흡"}
        trend={result.profit_factor >= 1.0 ? 'up' : 'down'}
      />

      <MetricItem
        title="최대 낙폭"
        value={formatPercent(result.mdd)}
        trend="down"
        className="border-loss/20"
      />
      
      <MetricItem
        title="샤프 비율"
        value={result.sharpe_ratio.toFixed(2)}
        trend={result.sharpe_ratio >= 1.0 ? 'up' : 'neutral'}
      />

      <MetricItem
        title="총 거래"
        value={result.total_trades.toString()}
        trend="neutral"
      />

      <MetricItem
        title="평균 수익"
        value={formatKRW(result.avg_win)}
        trend="up"
      />

      <MetricItem
        title="평균 손실"
        value={formatKRW(result.avg_loss)}
        trend="down"
      />
    </div>
  );
}
