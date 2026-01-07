import { Metadata } from 'next';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Download } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Trade History',
  description: 'View your past trading activity',
};

// Placeholder trade history data
const trades = [
  {
    id: 1,
    date: '2024-01-15 14:23:45',
    symbol: '005930',
    name: 'Samsung Electronics',
    type: 'BUY',
    quantity: 100,
    price: 71000,
    total: 7100000,
    status: 'completed',
  },
  {
    id: 2,
    date: '2024-01-15 10:15:22',
    symbol: '000660',
    name: 'SK Hynix',
    type: 'SELL',
    quantity: 50,
    price: 186500,
    total: 9325000,
    status: 'completed',
  },
  {
    id: 3,
    date: '2024-01-14 15:28:11',
    symbol: '035420',
    name: 'NAVER',
    type: 'BUY',
    quantity: 30,
    price: 213000,
    total: 6390000,
    status: 'completed',
  },
  {
    id: 4,
    date: '2024-01-14 09:31:05',
    symbol: '035720',
    name: 'Kakao',
    type: 'BUY',
    quantity: 200,
    price: 55000,
    total: 11000000,
    status: 'completed',
  },
  {
    id: 5,
    date: '2024-01-13 14:45:33',
    symbol: '006400',
    name: 'Samsung SDI',
    type: 'BUY',
    quantity: 30,
    price: 420000,
    total: 12600000,
    status: 'completed',
  },
];

export default function HistoryPage() {
  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Trade History</h1>
            <p className="text-muted-foreground">
              View and export your past trading activity
            </p>
          </div>
          <Button variant="outline">
            <Download className="h-4 w-4 mr-2" />
            Export CSV
          </Button>
        </div>

        {/* Trade History Table */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Trades</CardTitle>
            <CardDescription>
              Your last {trades.length} executed trades
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {/* Table Header */}
              <div className="grid grid-cols-8 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                <div className="col-span-2">Date</div>
                <div>Symbol</div>
                <div>Name</div>
                <div className="text-center">Type</div>
                <div className="text-right">Qty</div>
                <div className="text-right">Price</div>
                <div className="text-right">Total</div>
              </div>

              {/* Table Body */}
              {trades.map((trade) => (
                <div
                  key={trade.id}
                  className="grid grid-cols-8 gap-4 items-center py-3 border-b border-border/50 hover:bg-accent/50 rounded-lg px-2 -mx-2 transition-colors"
                >
                  <div className="col-span-2 text-sm text-muted-foreground">
                    {trade.date}
                  </div>
                  <div className="font-mono text-sm">{trade.symbol}</div>
                  <div className="font-medium truncate">{trade.name}</div>
                  <div className="text-center">
                    <Badge variant={trade.type === 'BUY' ? 'profit' : 'loss'}>
                      {trade.type}
                    </Badge>
                  </div>
                  <div className="text-right">{trade.quantity}</div>
                  <div className="text-right">{trade.price.toLocaleString('ko-KR')}</div>
                  <div className="text-right font-medium">
                    {trade.total.toLocaleString('ko-KR')}
                  </div>
                </div>
              ))}
            </div>

            {/* Pagination placeholder */}
            <div className="flex items-center justify-between mt-6">
              <p className="text-sm text-muted-foreground">
                Showing 1-5 of 156 trades
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" disabled>
                  Previous
                </Button>
                <Button variant="outline" size="sm">
                  Next
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </MainLayout>
  );
}
