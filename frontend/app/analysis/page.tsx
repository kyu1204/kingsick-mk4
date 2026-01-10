'use client';

import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Search } from 'lucide-react';
import { ProtectedRoute } from '@/components/auth';
import { ScannerPanel } from '@/components/scanner';

export default function AnalysisPage() {
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

          {/* Stock Search */}

          <Card>
            <CardHeader>
              <CardTitle>Stock Analysis</CardTitle>
              <CardDescription>
                Search for a stock to view detailed technical analysis
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex gap-2">
                <Input
                  placeholder="Enter stock code or name (e.g., 005930, Samsung)"
                  className="flex-1"
                />
                <Button>
                  <Search className="h-4 w-4 mr-2" />
                  Analyze
                </Button>
              </div>
            </CardContent>
          </Card>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Technical Indicators */}
            <Card>
              <CardHeader>
                <CardTitle>Technical Indicators</CardTitle>
                <CardDescription>
                  Current indicator values for Samsung Electronics (005930)
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  {[
                    { name: 'RSI (14)', value: '28.5', signal: 'Oversold', type: 'profit' },
                    { name: 'MA (5)', value: '71,250', signal: 'Below', type: 'loss' },
                    { name: 'MA (20)', value: '73,400', signal: 'Below', type: 'loss' },
                    { name: 'MACD', value: '-450', signal: 'Bearish', type: 'loss' },
                    { name: 'Bollinger Band', value: '70,800 - 76,200', signal: 'Near Lower', type: 'profit' },
                    { name: 'Volume', value: '12.5M', signal: 'High', type: 'profit' },
                  ].map((indicator) => (
                    <div key={indicator.name} className="flex items-center justify-between py-2 border-b">
                      <div>
                        <p className="font-medium">{indicator.name}</p>
                        <p className="text-sm text-muted-foreground">{indicator.value}</p>
                      </div>
                      <Badge variant={indicator.type === 'profit' ? 'profit' : indicator.type === 'loss' ? 'loss' : 'secondary'}>
                        {indicator.signal}
                      </Badge>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* AI Signal */}
            <Card>
              <CardHeader>
                <CardTitle>AI Signal Analysis</CardTitle>
                <CardDescription>
                  BNF Strategy based signal generation
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Signal Result */}
                <div className="text-center p-6 bg-green-500/10 border border-green-500/20 rounded-lg">
                  <Badge variant="profit" className="text-lg px-4 py-2 mb-2">
                    BUY SIGNAL
                  </Badge>
                  <p className="text-2xl font-bold text-green-500">85%</p>
                  <p className="text-sm text-muted-foreground">Confidence Score</p>
                </div>

                {/* Signal Factors */}
                <div className="space-y-3">
                  <p className="text-sm font-medium">Signal Factors:</p>
                  <ul className="space-y-2 text-sm text-muted-foreground">
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      RSI below 30 (oversold condition)
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      Price near lower Bollinger Band
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-green-500" />
                      Volume spike detected (+45%)
                    </li>
                    <li className="flex items-center gap-2">
                      <span className="w-2 h-2 rounded-full bg-yellow-500" />
                      MACD histogram turning positive
                    </li>
                  </ul>
                </div>

                {/* Suggested Action */}
                <div className="p-4 bg-muted rounded-lg">
                  <p className="text-sm font-medium mb-2">Suggested Action:</p>
                  <p className="text-sm text-muted-foreground">
                    Buy 100 shares at market price. Set stop-loss at 69,500 KRW (-4.1%)
                    and take-profit at 78,000 KRW (+7.6%).
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Chart Placeholder */}
          <Card>
            <CardHeader>
              <CardTitle>Price Chart</CardTitle>
              <CardDescription>
                Candlestick chart with technical indicators
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[400px] flex items-center justify-center border-2 border-dashed border-muted rounded-lg">
              <p className="text-muted-foreground">TradingView Lightweight Chart will be implemented here</p>
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
