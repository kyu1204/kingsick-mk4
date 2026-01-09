'use client';

import { useState, useEffect } from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Activity, DollarSign, Loader2, AlertCircle } from 'lucide-react';
import { tradingApi, positionsApi, TradingMode } from '@/lib/api';
import { ProtectedRoute } from '@/components/auth';
import type { TradingStatusResponse, BalanceResponse, PositionSchema, AlertSchema } from '@/lib/api';

// Types
type ChangeType = 'profit' | 'loss' | 'neutral';

interface StatItem {
  title: string;
  value: string;
  unit: string;
  change: string;
  changeType: ChangeType;
  icon: React.ComponentType<{ className?: string }>;
}

interface DashboardData {
  tradingStatus: TradingStatusResponse | null;
  balance: BalanceResponse | null;
  positions: PositionSchema[];
  alerts: AlertSchema[];
}

// Format number with commas
function formatNumber(num: number): string {
  return new Intl.NumberFormat('ko-KR').format(num);
}

// Calculate P&L from positions
function calculateTotalPnL(positions: PositionSchema[]): number {
  return positions.reduce((sum, pos) => sum + pos.profit_loss, 0);
}

// Calculate P&L percentage
function calculatePnLPercent(balance: BalanceResponse | null): number {
  if (!balance || balance.purchase_amount === 0) return 0;
  return ((balance.evaluation_amount - balance.purchase_amount) / balance.purchase_amount) * 100;
}

// Build stats from real data
function buildStats(data: DashboardData): StatItem[] {
  const totalPnL = calculateTotalPnL(data.positions);
  const pnlPercent = calculatePnLPercent(data.balance);

  return [
    {
      title: 'Total Portfolio Value',
      value: data.balance ? formatNumber(data.balance.net_worth) : '-',
      unit: 'KRW',
      change: data.balance
        ? `${pnlPercent >= 0 ? '+' : ''}${pnlPercent.toFixed(2)}%`
        : '-',
      changeType: pnlPercent >= 0 ? 'profit' : 'loss',
      icon: DollarSign,
    },
    {
      title: "Today's P&L",
      value: `${totalPnL >= 0 ? '+' : ''}${formatNumber(totalPnL)}`,
      unit: 'KRW',
      change: data.positions.length > 0
        ? `${totalPnL >= 0 ? '+' : ''}${(totalPnL / (data.balance?.purchase_amount || 1) * 100).toFixed(2)}%`
        : '-',
      changeType: totalPnL >= 0 ? 'profit' : 'loss',
      icon: totalPnL >= 0 ? TrendingUp : TrendingDown,
    },
    {
      title: 'Active Positions',
      value: data.positions.length.toString(),
      unit: 'stocks',
      change: `${data.tradingStatus?.trailing_stops_count || 0} with trailing stop`,
      changeType: 'neutral',
      icon: Activity,
    },
    {
      title: 'Pending Alerts',
      value: data.tradingStatus?.pending_alerts_count.toString() || '0',
      unit: '',
      change: `${data.alerts.length} awaiting action`,
      changeType: data.alerts.length > 0 ? 'profit' : 'neutral',
      icon: AlertCircle,
    },
  ];
}

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData>({
    tradingStatus: null,
    balance: null,
    positions: [],
    alerts: [],
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchDashboardData() {
      setLoading(true);
      setError(null);

      try {
        // Fetch all data in parallel
        const [tradingStatus, balance, positionsResult, alertsResult] = await Promise.all([
          tradingApi.getStatus().catch(() => null),
          positionsApi.getBalance().catch(() => null),
          positionsApi.getPositions().catch(() => ({ positions: [] })),
          tradingApi.getAlerts().catch(() => ({ alerts: [] })),
        ]);

        setData({
          tradingStatus,
          balance,
          positions: positionsResult.positions,
          alerts: alertsResult.alerts,
        });
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data');
      } finally {
        setLoading(false);
      }
    }

    fetchDashboardData();

    // Refresh data every 30 seconds
    const interval = setInterval(fetchDashboardData, 30000);
    return () => clearInterval(interval);
  }, []);

  const stats = buildStats(data);
  return (
    <ProtectedRoute>
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Overview of your trading portfolio and recent activity
            </p>
          </div>
          <Badge
            variant={data.tradingStatus?.mode === TradingMode.AUTO ? 'profit' : 'secondary'}
          >
            {data.tradingStatus?.mode === TradingMode.AUTO ? 'AUTO Mode Active' : 'ALERT Mode'}
          </Badge>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="flex items-center justify-center h-32">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}

        {/* Error State */}
        {error && (
          <Card className="border-red-500/50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-red-500">
                <AlertCircle className="h-5 w-5" />
                <p>{error}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stat.value}
                  {stat.unit && (
                    <span className="text-sm font-normal text-muted-foreground ml-1">
                      {stat.unit}
                    </span>
                  )}
                </div>
                <p
                  className={`text-xs ${
                    stat.changeType === 'profit'
                      ? 'text-green-500'
                      : stat.changeType === 'loss'
                      ? 'text-red-500'
                      : 'text-muted-foreground'
                  }`}
                >
                  {stat.change} from yesterday
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          {/* Chart Placeholder */}
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle>Portfolio Performance</CardTitle>
              <CardDescription>
                Your portfolio value over the last 30 days
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center border-2 border-dashed border-muted rounded-lg">
              <p className="text-muted-foreground">Chart will be implemented here</p>
            </CardContent>
          </Card>

          {/* Positions & Alerts */}
          <Card className="col-span-3">
            <CardHeader>
              <CardTitle>Current Positions</CardTitle>
              <CardDescription>
                Your active stock positions and pending alerts
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Pending Alerts */}
                {data.alerts.length > 0 && (
                  <div className="mb-4">
                    <h4 className="text-sm font-semibold text-muted-foreground mb-2">Pending Alerts</h4>
                    {data.alerts.slice(0, 2).map((alert) => (
                      <div key={alert.alert_id} className="flex items-center justify-between py-2 border-b border-muted">
                        <div className="flex items-center gap-3">
                          {alert.signal_type === 'BUY' ? (
                            <TrendingUp className="h-4 w-4 text-green-500" />
                          ) : (
                            <TrendingDown className="h-4 w-4 text-red-500" />
                          )}
                          <div>
                            <p className="text-sm font-medium">{alert.stock_code}</p>
                            <p className="text-xs text-muted-foreground">{alert.reason}</p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={alert.signal_type === 'BUY' ? 'profit' : 'loss'}>
                            {alert.signal_type}
                          </Badge>
                          <p className="text-sm text-muted-foreground mt-1">
                            {formatNumber(alert.current_price)} KRW
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* Current Positions */}
                {data.positions.length > 0 ? (
                  data.positions.slice(0, 4).map((position) => (
                    <div key={position.stock_code} className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        {position.profit_loss >= 0 ? (
                          <TrendingUp className="h-4 w-4 text-green-500" />
                        ) : (
                          <TrendingDown className="h-4 w-4 text-red-500" />
                        )}
                        <div>
                          <p className="text-sm font-medium">{position.stock_name}</p>
                          <p className="text-xs text-muted-foreground">{position.quantity} shares</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <Badge variant={position.profit_loss >= 0 ? 'profit' : 'loss'}>
                          {position.profit_loss >= 0 ? '+' : ''}{position.profit_loss_rate.toFixed(2)}%
                        </Badge>
                        <p className="text-sm text-muted-foreground mt-1">
                          {formatNumber(position.current_price)} KRW
                        </p>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center justify-center h-20 text-muted-foreground">
                    <Activity className="h-4 w-4 mr-2" />
                    <p>No active positions</p>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
    </ProtectedRoute>
  );
}
