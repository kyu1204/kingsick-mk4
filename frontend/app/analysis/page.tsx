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
            <h1 className="text-3xl font-bold tracking-tight">Analysis</h1>
            <p className="text-muted-foreground">
              Technical analysis with AI-powered signal generation
            </p>
          </div>

          <div className="mb-8">
            <ScannerPanel />
          </div>

          <Card>
            <CardHeader>
              <CardTitle>Stock Analysis</CardTitle>
              <CardDescription>
                Search for a stock to view detailed technical analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <form onSubmit={handleSearch} className="flex gap-2">
                <Input
                  placeholder="Enter stock code (e.g., 005930)"
                  className="flex-1"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                />
                <Button type="submit" disabled={loading}>
                  {loading ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : <Search className="h-4 w-4 mr-2" />}
                  Analyze
                </Button>
              </form>
            </CardContent>
          </Card>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {result && (
            <div className="grid gap-6 md:grid-cols-2">
              <Card className="md:col-span-1">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>AI Signal Analysis</span>
                    <Badge variant="outline">{result.stock_name} ({result.stock_code})</Badge>
                  </CardTitle>
                  <CardDescription>
                    BNF Strategy based signal generation
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-8">
                  <SignalStrengthGauge 
                    strength={result.score} 
                    signal={result.signal} 
                  />

                  <div className="space-y-4">
                    <h4 className="text-sm font-medium text-muted-foreground uppercase tracking-wider">Indicator Contribution</h4>
                    <IndicatorContribution contributions={getContributions(result.indicator_scores)} />
                  </div>
                </CardContent>
              </Card>

              <Card className="md:col-span-1">
                <CardHeader>
                  <CardTitle>Analysis Details</CardTitle>
                  <CardDescription>
                    {new Date(result.analysis_date).toLocaleDateString()} Analysis
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex justify-between items-center p-4 bg-muted/50 rounded-lg">
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">Current Price</p>
                      <p className="text-2xl font-bold">{formatKRW(result.current_price)}</p>
                    </div>
                    <Badge variant={result.change_pct >= 0 ? "profit" : "loss"} className="text-lg px-3 py-1">
                      {formatPercent(result.change_pct)}
                    </Badge>
                  </div>

                  <div className="space-y-3">
                    <h4 className="text-sm font-medium">Analysis Reasoning</h4>
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
                    <p className="text-sm font-medium mb-1">Recommendation</p>
                    <p className="text-sm text-muted-foreground">
                      Based on the {result.signal.replace('_', ' ')} signal with a confidence score of {result.score.toFixed(0)}, 
                      {result.score >= 70 ? ' accumulation is recommended.' : result.score <= 30 ? ' reducing exposure is advised.' : ' monitoring for clearer signals is suggested.'}
                    </p>
                  </div>
                </CardContent>
              </Card>
            </div>
          )}
          
          {!result && !loading && !error && (
             <div className="text-center py-12 text-muted-foreground border-2 border-dashed rounded-lg">
               <Search className="h-12 w-12 mx-auto mb-4 opacity-20" />
               <p>Enter a stock code above to generate an AI analysis report.</p>
             </div>
          )}
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
