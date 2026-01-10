'use client';

import { useState } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { StockSearchInput } from './stock-search-input';
import { watchlistApi, type StockInfo, type CreateWatchlistItemRequest } from '@/lib/api';
import { Loader2 } from 'lucide-react';

interface AddStockModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function AddStockModal({ open, onOpenChange, onSuccess }: AddStockModalProps) {
  const [selectedStock, setSelectedStock] = useState<StockInfo | null>(null);
  const [targetPrice, setTargetPrice] = useState('');
  const [stopLossPrice, setStopLossPrice] = useState('');
  const [quantity, setQuantity] = useState('');
  const [memo, setMemo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedStock) {
      setError('종목을 선택해주세요.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const data: CreateWatchlistItemRequest = {
        stock_code: selectedStock.code,
        stock_name: selectedStock.name,
        target_price: targetPrice ? parseFloat(targetPrice) : null,
        stop_loss_price: stopLossPrice ? parseFloat(stopLossPrice) : null,
        quantity: quantity ? parseInt(quantity, 10) : null,
        memo: memo || null,
      };

      await watchlistApi.createWatchlistItem(data);
      resetForm();
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('종목 추가에 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const resetForm = () => {
    setSelectedStock(null);
    setTargetPrice('');
    setStopLossPrice('');
    setQuantity('');
    setMemo('');
    setError(null);
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      resetForm();
    }
    onOpenChange(newOpen);
  };

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>종목 추가</DialogTitle>
          <DialogDescription>
            관심 종목을 추가하고 매매 설정을 입력하세요.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
            {/* Stock Search */}
            <div className="space-y-2">
              <label className="text-sm font-medium">종목 검색</label>
              {selectedStock ? (
                <div className="flex items-center justify-between p-3 rounded-md border bg-muted/50">
                  <div>
                    <span className="font-medium">{selectedStock.name}</span>
                    <span className="ml-2 text-sm text-muted-foreground font-mono">
                      {selectedStock.code}
                    </span>
                  </div>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => setSelectedStock(null)}
                  >
                    변경
                  </Button>
                </div>
              ) : (
                <StockSearchInput onSelect={setSelectedStock} />
              )}
            </div>

            {/* Target Price */}
            <div className="space-y-2">
              <label className="text-sm font-medium">목표가 (원)</label>
              <Input
                type="number"
                value={targetPrice}
                onChange={(e) => setTargetPrice(e.target.value)}
                placeholder="목표가 입력 (선택사항)"
                min="0"
                step="100"
              />
            </div>

            {/* Stop Loss Price */}
            <div className="space-y-2">
              <label className="text-sm font-medium">손절가 (원)</label>
              <Input
                type="number"
                value={stopLossPrice}
                onChange={(e) => setStopLossPrice(e.target.value)}
                placeholder="손절가 입력 (선택사항)"
                min="0"
                step="100"
              />
            </div>

            {/* Quantity */}
            <div className="space-y-2">
              <label className="text-sm font-medium">수량 (주)</label>
              <Input
                type="number"
                value={quantity}
                onChange={(e) => setQuantity(e.target.value)}
                placeholder="수량 입력 (선택사항)"
                min="0"
                step="1"
              />
            </div>

            {/* Memo */}
            <div className="space-y-2">
              <label className="text-sm font-medium">메모</label>
              <Input
                type="text"
                value={memo}
                onChange={(e) => setMemo(e.target.value)}
                placeholder="메모 입력 (선택사항)"
                maxLength={500}
              />
            </div>

            {error && (
              <div className="text-sm text-red-500">{error}</div>
            )}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={() => handleOpenChange(false)}
              disabled={loading}
            >
              취소
            </Button>
            <Button type="submit" disabled={loading || !selectedStock}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              추가
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
