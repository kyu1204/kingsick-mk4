'use client';

import * as React from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { ProtectedRoute } from '@/components/auth';
import { AlertCircle, Loader2, History } from 'lucide-react';
import { ApiError } from '@/lib/api/client';
import {
  backtestApi,
  type BacktestResult,
  type BacktestRunRequest,
  type BacktestListItem,
} from '@/lib/api/backtest';
import {
  BacktestForm,
  MetricsCards,
  EquityCurveChart,
  DrawdownChart,
  TradesTable,
} from '@/components/backtest';
import { Button } from '@/components/ui/button';
import { formatPercent } from '@/lib/utils';

export default function BacktestPage() {
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<BacktestResult | null>(null);
  const [error, setError] = React.useState<string | null>(null);
  const [history, setHistory] = React.useState<BacktestListItem[]>([]);
  const [historyLoading, setHistoryLoading] = React.useState(true);

  React.useEffect(() => {
    const loadHistory = async () => {
      try {
        const response = await backtestApi.listResults(10, 0);
        setHistory(response.results);
      } catch (err) {
        console.error('Failed to load backtest history:', err);
      } finally {
        setHistoryLoading(false);
      }
    };
    loadHistory();
  }, []);

  const handleRunBacktest = async (request: BacktestRunRequest) => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await backtestApi.runBacktest(request);
      setResult(data);
      const response = await backtestApi.listResults(10, 0);
      setHistory(response.results);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to run backtest');
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleLoadResult = async (id: string) => {
    setLoading(true);
    setError(null);

    try {
      const data = await backtestApi.getResult(id);
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to load backtest result');
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">백테스트</h1>
            <p className="text-muted-foreground">
              과거 데이터로 트레이딩 전략을 테스트하세요
            </p>
          </div>

          <div className="grid gap-6 lg:grid-cols-3">
            <div className="space-y-6">
              <BacktestForm onSubmit={handleRunBacktest} isLoading={loading} />

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <History className="h-5 w-5" />
                    최근 백테스트
                  </CardTitle>
                  <CardDescription>
                    클릭하여 이전 결과 확인
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  {historyLoading ? (
                    <div className="flex items-center justify-center py-4">
                      <Loader2 className="h-4 w-4 animate-spin" />
                    </div>
                  ) : history.length === 0 ? (
                    <p className="text-sm text-muted-foreground text-center py-4">
                      백테스트 기록이 없습니다
                    </p>
                  ) : (
                    <div className="space-y-2">
                      {history.map((item) => (
                        <Button
                          key={item.id}
                          variant="ghost"
                          className="w-full justify-start h-auto py-2"
                          onClick={() => handleLoadResult(item.id)}
                        >
                          <div className="flex flex-col items-start text-left">
                            <span className="font-medium text-sm">
                              {item.name || `Backtest ${item.start_date}`}
                            </span>
                            <span className="text-xs text-muted-foreground">
                              {item.start_date} ~ {item.end_date} •{' '}
                              <span
                                className={
                                  item.total_return_pct >= 0
                                    ? 'text-profit'
                                    : 'text-loss'
                                }
                              >
                                {formatPercent(item.total_return_pct)}
                              </span>
                            </span>
                          </div>
                        </Button>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            <div className="lg:col-span-2 space-y-6">
              {error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertTitle>오류</AlertTitle>
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}

              {loading && !result && (
                <Card>
                  <CardContent className="flex items-center justify-center py-12">
                    <div className="flex flex-col items-center gap-2">
                      <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
                      <p className="text-sm text-muted-foreground">
                        백테스트 실행 중...
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}

              {result && (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle>{result.name || '백테스트 결과'}</CardTitle>
                      <CardDescription>
                        {result.start_date} ~ {result.end_date} •{' '}
                        {result.total_trades}회 거래
                      </CardDescription>
                    </CardHeader>
                  </Card>

                  <MetricsCards result={result} />

                  <Card>
                    <CardHeader>
                      <CardTitle>자산 곡선</CardTitle>
                      <CardDescription>
                        시간에 따른 포트폴리오 가치
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <EquityCurveChart
                        dailyEquity={result.daily_equity}
                        startDate={result.start_date}
                      />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>낙폭</CardTitle>
                      <CardDescription>
                        최대 낙폭: {formatPercent(result.mdd)}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <DrawdownChart
                        drawdownCurve={result.drawdown_curve}
                        startDate={result.start_date}
                      />
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>거래 내역</CardTitle>
                      <CardDescription>
                        백테스트 기간 동안 실행된 모든 거래
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <TradesTable trades={result.trades} />
                    </CardContent>
                  </Card>
                </>
              )}

              {!result && !loading && !error && (
                <Card>
                  <CardContent className="flex items-center justify-center py-12">
                    <div className="text-center">
                      <History className="h-12 w-12 mx-auto mb-4 text-muted-foreground opacity-20" />
                      <p className="text-muted-foreground">
                        백테스트 매개변수를 설정하고 &quot;백테스트 실행&quot; 버튼을
                        클릭하여 결과를 확인하세요
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )}
            </div>
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
