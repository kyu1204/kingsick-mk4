'use client';

import { useState, useEffect } from 'react';
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
import { watchlistApi, type WatchlistItem, type UpdateWatchlistItemRequest } from '@/lib/api';
import { Loader2 } from 'lucide-react';

interface EditStockModalProps {
  item: WatchlistItem | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess: () => void;
}

export function EditStockModal({ item, open, onOpenChange, onSuccess }: EditStockModalProps) {
  const [targetPrice, setTargetPrice] = useState('');
  const [stopLossPrice, setStopLossPrice] = useState('');
  const [quantity, setQuantity] = useState('');
  const [memo, setMemo] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Populate form when item changes
  useEffect(() => {
    if (item) {
      setTargetPrice(item.target_price?.toString() || '');
      setStopLossPrice(item.stop_loss_price?.toString() || '');
      setQuantity(item.quantity?.toString() || '');
      setMemo(item.memo || '');
    }
  }, [item]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!item) return;

    setLoading(true);
    setError(null);

    try {
      const data: UpdateWatchlistItemRequest = {
        target_price: targetPrice ? parseFloat(targetPrice) : null,
        stop_loss_price: stopLossPrice ? parseFloat(stopLossPrice) : null,
        quantity: quantity ? parseInt(quantity, 10) : null,
        memo: memo || null,
        // Clear flags for null values
        clear_target_price: !targetPrice && item.target_price !== null,
        clear_stop_loss_price: !stopLossPrice && item.stop_loss_price !== null,
        clear_quantity: !quantity && item.quantity !== null,
        clear_memo: !memo && item.memo !== null,
      };

      await watchlistApi.updateWatchlistItem(item.id, data);
      onSuccess();
      onOpenChange(false);
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('수정에 실패했습니다.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleOpenChange = (newOpen: boolean) => {
    if (!newOpen) {
      setError(null);
    }
    onOpenChange(newOpen);
  };

  if (!item) return null;

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>종목 수정</DialogTitle>
          <DialogDescription>
            {item.stock_name} ({item.stock_code})의 매매 설정을 수정합니다.
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit}>
          <div className="grid gap-4 py-4">
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
            <Button type="submit" disabled={loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              저장
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
