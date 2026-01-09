'use client';

import { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Download, Loader2, Info } from 'lucide-react';
import { ProtectedRoute } from '@/components/auth';
import { tradesApi, TradeSchema } from '@/lib/api/trades';

export default function HistoryPage() {
  const [trades, setTrades] = useState<TradeSchema[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchTrades = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await tradesApi.getTrades(page, pageSize);
      setTrades(response.trades);
      setTotalCount(response.total_count);
    } catch (err) {
      console.error('Failed to fetch trades:', err);
      setError('거래 내역을 불러오는데 실패했습니다.');
    } finally {
      setIsLoading(false);
    }
  }, [page, pageSize]);

  useEffect(() => {
    fetchTrades();
  }, [fetchTrades]);

  const totalPages = Math.ceil(totalCount / pageSize);
  const startIdx = (page - 1) * pageSize + 1;
  const endIdx = Math.min(page * pageSize, totalCount);

  if (isLoading) {
    return (
      <ProtectedRoute>
        <MainLayout>
          <div className="flex items-center justify-center h-[60vh]">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        </MainLayout>
      </ProtectedRoute>
    );
  }

  return (
    <ProtectedRoute>
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

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-red-500/10 border border-red-500/50 rounded-lg">
              <p className="text-sm text-red-500">{error}</p>
            </div>
          )}

          {/* Trade History Table */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Trades</CardTitle>
              <CardDescription>
                Your executed trades with AI signal reasons
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Table Header */}
                <div className="grid grid-cols-9 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                  <div className="col-span-2">Date</div>
                  <div>Symbol</div>
                  <div>Name</div>
                  <div className="text-center">Type</div>
                  <div className="text-right">Qty</div>
                  <div className="text-right">Price</div>
                  <div className="text-right">Total</div>
                  <div className="text-center">AI</div>
                </div>

                {/* Table Body */}
                {trades.map((trade) => (
                  <div
                    key={trade.id}
                    className="grid grid-cols-9 gap-4 items-center py-3 border-b border-border/50 hover:bg-accent/50 rounded-lg px-2 -mx-2 transition-colors"
                  >
                    <div className="col-span-2 text-sm text-muted-foreground">
                      {trade.date}
                    </div>
                    <div className="font-mono text-sm">{trade.stock_code}</div>
                    <div className="font-medium truncate">{trade.stock_name}</div>
                    <div className="text-center">
                      <Badge variant={trade.trade_type === 'BUY' ? 'profit' : 'loss'}>
                        {trade.trade_type}
                      </Badge>
                    </div>
                    <div className="text-right">{trade.quantity}</div>
                    <div className="text-right">{trade.price.toLocaleString('ko-KR')}</div>
                    <div className="text-right font-medium">
                      {trade.total.toLocaleString('ko-KR')}
                    </div>
                    <div className="text-center">
                      {trade.signal_reason && (
                        <button
                          title={trade.signal_reason}
                          className="p-1 rounded hover:bg-accent transition-colors"
                        >
                          <Info className="h-4 w-4 text-blue-500" />
                        </button>
                      )}
                    </div>
                  </div>
                ))}

                {trades.length === 0 && !error && (
                  <div className="text-center py-8 text-muted-foreground">
                    거래 내역이 없습니다.
                  </div>
                )}
              </div>

              {/* Pagination */}
              {totalCount > 0 && (
                <div className="flex items-center justify-between mt-6">
                  <p className="text-sm text-muted-foreground">
                    Showing {startIdx}-{endIdx} of {totalCount} trades
                  </p>
                  <div className="flex gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page <= 1}
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                    >
                      Previous
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      disabled={page >= totalPages}
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    >
                      Next
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
