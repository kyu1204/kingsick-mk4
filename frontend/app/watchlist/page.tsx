'use client';

import { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Plus, AlertCircle, RefreshCw } from 'lucide-react';
import { ProtectedRoute } from '@/components/auth';
import { watchlistApi, type WatchlistItem } from '@/lib/api';
import { WatchlistTable, AddStockModal, EditStockModal } from '@/components/watchlist';

export default function WatchlistPage() {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [addModalOpen, setAddModalOpen] = useState(false);
  const [editItem, setEditItem] = useState<WatchlistItem | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  const fetchWatchlist = useCallback(async () => {
    try {
      const response = await watchlistApi.getWatchlist();
      setItems(response.items);
      setError(null);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('관심 종목을 불러오는데 실패했습니다.');
      }
    }
  }, []);

  const handleRefresh = async () => {
    setRefreshing(true);
    await fetchWatchlist();
    setRefreshing(false);
  };

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      await fetchWatchlist();
      setLoading(false);
    };
    load();
  }, [fetchWatchlist]);

  const activeCount = items.filter((item) => item.is_active).length;

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">관심 종목</h1>
              <p className="text-muted-foreground">
                관심 종목을 관리하고 매매 설정을 입력하세요
              </p>
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="icon"
                onClick={handleRefresh}
                disabled={refreshing}
              >
                <RefreshCw className={`h-4 w-4 ${refreshing ? 'animate-spin' : ''}`} />
              </Button>
              <Button onClick={() => setAddModalOpen(true)}>
                <Plus className="h-4 w-4 mr-2" />
                종목 추가
              </Button>
            </div>
          </div>

          {/* Stats */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">전체 종목</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{items.length}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">활성 종목</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-500">{activeCount}</div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">비활성 종목</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-muted-foreground">
                  {items.length - activeCount}
                </div>
              </CardContent>
            </Card>
          </div>

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

          {/* Watchlist Table */}
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <div>
                  <CardTitle>관심 종목 목록</CardTitle>
                  <CardDescription>
                    {items.length > 0
                      ? `총 ${items.length}개 종목 (활성: ${activeCount})`
                      : '관심 종목을 추가해주세요'}
                  </CardDescription>
                </div>
                {items.length > 0 && (
                  <Badge variant="secondary">{activeCount}개 활성</Badge>
                )}
              </div>
            </CardHeader>
            <CardContent>
              <WatchlistTable
                items={items}
                loading={loading}
                onEdit={setEditItem}
                onRefresh={fetchWatchlist}
              />
            </CardContent>
          </Card>
        </div>

        {/* Add Stock Modal */}
        <AddStockModal
          open={addModalOpen}
          onOpenChange={setAddModalOpen}
          onSuccess={fetchWatchlist}
        />

        {/* Edit Stock Modal */}
        <EditStockModal
          item={editItem}
          open={editItem !== null}
          onOpenChange={(open) => !open && setEditItem(null)}
          onSuccess={fetchWatchlist}
        />
      </MainLayout>
    </ProtectedRoute>
  );
}
