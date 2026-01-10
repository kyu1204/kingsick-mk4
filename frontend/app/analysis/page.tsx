'use client';

import * as React from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search, Loader2, AlertCircle } from 'lucide-react';
import { ProtectedRoute } from '@/components/auth';
import { ScannerPanel } from '@/components/scanner';
import { analysisApi, type StockScoreResponse } from '@/lib/api/analysis';
import { SignalStrengthGauge, IndicatorContribution, type Contribution } from '@/components/analysis';
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert';
import { formatKRW, formatPercent } from '@/lib/utils';
import { ApiError } from '@/lib/api/client';

export default function AnalysisPage() {
  const [query, setQuery] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [result, setResult] = React.useState<StockScoreResponse | null>(null);
  const [error, setError] = React.useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const data = await analysisApi.getStockScore(query);
      setResult(data);
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message || 'Failed to fetch analysis');
      } else {
        setError('An unexpected error occurred');
      }
    } finally {
      setLoading(false);
    }
  };

  const getContributions = (scores: StockScoreResponse['indicator_scores']): Contribution[] => {
    return [
      { name: 'Trend', score: scores.trend_score, weight: 20 },
      { name: 'RSI', score: scores.rsi_score, weight: 30 },
      { name: 'MACD', score: scores.macd_score, weight: 20 },
      { name: 'Bollinger', score: scores.bollinger_score, weight: 15 },
      { name: 'Volume', score: scores.volume_score, weight: 15 },
    ].sort((a, b) => b.score - a.score);
  };

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">분석</h1>
            <p className="text-muted-foreground">
              AI 기반 신호 생성을 활용한 기술적 분석
            </p>
          </div>

          <div className="mb-8">
            <ScannerPanel />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>종목 분석</CardTitle>
              <CardDescription>
                종목 코드를 검색하여 상세 기술적 분석을 확인하세요
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSearch} className="flex gap-2">
                <Input
                  placeholder="종목 코드 입력 (예: 005930)"
                  className="flex-1"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <Button type="submit" disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Search className="h-4 w-4 mr-2" />}
                  분석
                </Button>
              </form>
            </CardContent>
          </Card>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>오류</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {result && (
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="md:col-span-1">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>AI 신호 분석</span>
                    <Badge variant="outline">{result.stock_name} ({result.stock_code})</Badge>
                  </CardTitle>
                  <CardDescription>
                    BNF 전략 기반 신호 생성
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-8">
                  <SignalStrengthGauge 
                    strength={result.score} 
                    signal={result.signal} 
                  />

                  <div className="space-y-4">
                    <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">지표 기여도</h4>
                    <IndicatorContribution contributions={getContributions(result.indicator_scores)} />
                  </div>
                </CardContent>
              </Card>

              <Card className="md:col-span-1">
                <CardHeader>
                  <CardTitle>분석 상세</CardTitle>
                  <CardDescription>
                    {new Date(result.analysis_date).toLocaleDateString('ko-KR')} 분석
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">현재가</p>
                      <p className="text-2xl font-bold">{formatKRW(result.current_price)}</p>
                    </div>
                    <Badge variant={result.change_pct >= 0 ? "profit" : "loss"} className="text-lg px-3 py-1">
                      {formatPercent(result.change_pct)}
                    </Badge>
                  </div>

                  <div className="space-y-3">
                    <h4 className="text-sm font-medium">분석 근거</h4>
                    <ul className="space-y-2">
                      {result.reasons.map((reason, i) => (
                        <li key={i} className="flex items-start gap-2 text-sm text-muted-foreground">
                          <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-primary flex-shrink-0" />
                          <span>{reason}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="p-4 bg-muted rounded-lg border border-dashed">
                    <p className="text-sm font-medium mb-1">투자 의견</p>
                    <p className="text-sm text-muted-foreground">
                      신뢰도 {result.score.toFixed(0)}점의 {result.signal.replace('_', ' ')} 신호를 기반으로, 
                      {result.score >= 70 ? ' 매수 비중 확대를 권장합니다.' : result.score <= 30 ? ' 비중 축소를 권장합니다.' : ' 추가 신호 확인 후 진입을 권장합니다.'}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
          
          {!result && !loading && !error && (
             <div className="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg">
               <Search className="h-12 w-12 mx-auto mb-4 opacity-20" />
               <p>위에 종목 코드를 입력하여 AI 분석 리포트를 생성하세요.</p>
             </div>
          )}
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
