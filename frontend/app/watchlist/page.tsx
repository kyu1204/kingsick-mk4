import { Metadata } from 'next';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, TrendingUp, TrendingDown } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Watchlist',
  description: 'Monitor your favorite stocks',
};

// Placeholder watchlist data
const watchlistItems = [
  { symbol: '005930', name: 'Samsung Electronics', price: 72500, change: 1.23, signal: 'BUY' },
  { symbol: '000660', name: 'SK Hynix', price: 185000, change: -0.54, signal: 'HOLD' },
  { symbol: '035420', name: 'NAVER', price: 215500, change: 2.15, signal: 'BUY' },
  { symbol: '035720', name: 'Kakao', price: 52300, change: -1.87, signal: 'SELL' },
  { symbol: '051910', name: 'LG Chem', price: 382000, change: 0.79, signal: 'HOLD' },
  { symbol: '006400', name: 'Samsung SDI', price: 438500, change: 1.45, signal: 'BUY' },
];

export default function WatchlistPage() {
  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Watchlist</h1>
            <p className="text-muted-foreground">
              Monitor your favorite stocks and receive AI trading signals
            </p>
          </div>
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            Add Stock
          </Button>
        </div>

        {/* Watchlist Table */}
        <Card>
          <CardHeader>
            <CardTitle>My Watchlist</CardTitle>
            <CardDescription>
              {watchlistItems.length} stocks being monitored
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Table Header */}
              <div className="grid grid-cols-5 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                <div>Symbol</div>
                <div>Name</div>
                <div className="text-right">Price (KRW)</div>
                <div className="text-right">Change</div>
                <div className="text-center">AI Signal</div>
              </div>

              {/* Table Body */}
              {watchlistItems.map((item) => (
                <div
                  key={item.symbol}
                  className="grid grid-cols-5 gap-4 items-center py-2 border-b border-border/50 hover:bg-accent/50 rounded-lg px-2 -mx-2 transition-colors"
                >
                  <div className="font-mono text-sm">{item.symbol}</div>
                  <div className="font-medium">{item.name}</div>
                  <div className="text-right font-medium">
                    {item.price.toLocaleString('ko-KR')}
                  </div>
                  <div className={`text-right flex items-center justify-end gap-1 ${
                    item.change >= 0 ? 'text-green-500' : 'text-red-500'
                  }`}>
                    {item.change >= 0 ? (
                      <TrendingUp className="h-4 w-4" />
                    ) : (
                      <TrendingDown className="h-4 w-4" />
                    )}
                    {item.change >= 0 ? '+' : ''}{item.change.toFixed(2)}%
                  </div>
                  <div className="text-center">
                    <Badge
                      variant={
                        item.signal === 'BUY'
                          ? 'profit'
                          : item.signal === 'SELL'
                          ? 'loss'
                          : 'secondary'
                      }
                    >
                      {item.signal}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
