'use client';

import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown } from 'lucide-react';
import { ProtectedRoute } from '@/components/auth';

// Placeholder portfolio data
const positions = [
  {
    symbol: '005930',
    name: 'Samsung Electronics',
    quantity: 150,
    avgPrice: 70500,
    currentPrice: 72500,
    pnl: 300000,
    pnlPercent: 2.84,
  },
  {
    symbol: '035420',
    name: 'NAVER',
    quantity: 50,
    avgPrice: 210000,
    currentPrice: 215500,
    pnl: 275000,
    pnlPercent: 2.62,
  },
  {
    symbol: '035720',
    name: 'Kakao',
    quantity: 200,
    avgPrice: 55000,
    currentPrice: 52300,
    pnl: -540000,
    pnlPercent: -4.91,
  },
  {
    symbol: '006400',
    name: 'Samsung SDI',
    quantity: 30,
    avgPrice: 420000,
    currentPrice: 438500,
    pnl: 555000,
    pnlPercent: 4.40,
  },
];

export default function PortfolioPage() {
  const totalValue = positions.reduce((acc, pos) => acc + pos.currentPrice * pos.quantity, 0);
  const totalPnl = positions.reduce((acc, pos) => acc + pos.pnl, 0);
  const totalPnlPercent = (totalPnl / (totalValue - totalPnl)) * 100;

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          {/* Page Header */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Portfolio</h1>
            <p className="text-muted-foreground">
              Your current holdings and position performance
            </p>
          </div>

          {/* Portfolio Summary */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Value</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {totalValue.toLocaleString('ko-KR')}
                  <span className="text-sm font-normal text-muted-foreground ml-1">KRW</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total P&L</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {totalPnl >= 0 ? '+' : ''}{totalPnl.toLocaleString('ko-KR')}
                  <span className="text-sm font-normal ml-1">KRW</span>
                </div>
                <p className={`text-sm ${totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {totalPnl >= 0 ? '+' : ''}{totalPnlPercent.toFixed(2)}%
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Positions</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {positions.length}
                  <span className="text-sm font-normal text-muted-foreground ml-1">stocks</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Positions Table */}
          <Card>
            <CardHeader>
              <CardTitle>Open Positions</CardTitle>
              <CardDescription>
                All your current stock holdings
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Table Header */}
                <div className="grid grid-cols-7 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                  <div>Symbol</div>
                  <div>Name</div>
                  <div className="text-right">Qty</div>
                  <div className="text-right">Avg Price</div>
                  <div className="text-right">Current</div>
                  <div className="text-right">P&L</div>
                  <div className="text-center">Status</div>
                </div>

                {/* Table Body */}
                {positions.map((pos) => (
                  <div
                    key={pos.symbol}
                    className="grid grid-cols-7 gap-4 items-center py-3 border-b border-border/50 hover:bg-accent/50 rounded-lg px-2 -mx-2 transition-colors"
                  >
                    <div className="font-mono text-sm">{pos.symbol}</div>
                    <div className="font-medium">{pos.name}</div>
                    <div className="text-right">{pos.quantity}</div>
                    <div className="text-right">{pos.avgPrice.toLocaleString('ko-KR')}</div>
                    <div className="text-right font-medium">{pos.currentPrice.toLocaleString('ko-KR')}</div>
                    <div className={`text-right ${pos.pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      <div className="flex items-center justify-end gap-1">
                        {pos.pnl >= 0 ? (
                          <TrendingUp className="h-4 w-4" />
                        ) : (
                          <TrendingDown className="h-4 w-4" />
                        )}
                        {pos.pnl >= 0 ? '+' : ''}{pos.pnl.toLocaleString('ko-KR')}
                      </div>
                      <div className="text-xs">
                        ({pos.pnl >= 0 ? '+' : ''}{pos.pnlPercent.toFixed(2)}%)
                      </div>
                    </div>
                    <div className="text-center">
                      <Badge variant={pos.pnl >= 0 ? 'profit' : 'loss'}>
                        {pos.pnl >= 0 ? 'Profit' : 'Loss'}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
