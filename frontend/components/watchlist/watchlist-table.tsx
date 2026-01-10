'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Switch } from '@/components/ui/switch';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { watchlistApi, type WatchlistItem } from '@/lib/api';
import { MoreHorizontal, Pencil, Trash2, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface WatchlistTableProps {
  items: WatchlistItem[];
  loading?: boolean;
  onEdit: (item: WatchlistItem) => void;
  onRefresh: () => void;
}

function formatNumber(num: number | null): string {
  if (num === null) return '-';
  return new Intl.NumberFormat('ko-KR').format(num);
}

export function WatchlistTable({ items, loading, onEdit, onRefresh }: WatchlistTableProps) {
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  const handleToggle = async (item: WatchlistItem) => {
    setActionLoading(item.id);
    try {
      await watchlistApi.toggleWatchlistItem(item.id);
      onRefresh();
    } catch {
      // Silent fail, refresh anyway
      onRefresh();
    } finally {
      setActionLoading(null);
    }
  };

  const handleDelete = async (item: WatchlistItem) => {
    if (!confirm(`${item.stock_name}(${item.stock_code})을(를) 삭제하시겠습니까?`)) {
      return;
    }

    setActionLoading(item.id);
    try {
      await watchlistApi.deleteWatchlistItem(item.id);
      onRefresh();
    } catch {
      // Silent fail, refresh anyway
      onRefresh();
    } finally {
      setActionLoading(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-32">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-32 text-muted-foreground">
        <p>관심 종목이 없습니다.</p>
        <p className="text-sm">종목 추가 버튼을 눌러 관심 종목을 등록하세요.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Table Header */}
      <div className="hidden md:grid md:grid-cols-8 gap-4 text-sm font-medium text-muted-foreground border-b pb-2 px-2">
        <div className="col-span-2">종목</div>
        <div className="text-right">목표가</div>
        <div className="text-right">손절가</div>
        <div className="text-right">수량</div>
        <div>메모</div>
        <div className="text-center">활성</div>
        <div className="text-center">작업</div>
      </div>

      {/* Table Body */}
      {items.map((item) => (
        <div
          key={item.id}
          className={cn(
            'grid grid-cols-1 md:grid-cols-8 gap-2 md:gap-4 items-center py-3 px-2 border-b border-border/50 hover:bg-accent/50 rounded-lg transition-colors',
            !item.is_active && 'opacity-50'
          )}
        >
          {/* Stock Info */}
          <div className="col-span-1 md:col-span-2">
            <div className="flex items-center gap-2">
              <div>
                <div className="font-medium">{item.stock_name}</div>
                <div className="text-sm text-muted-foreground font-mono">{item.stock_code}</div>
              </div>
            </div>
          </div>

          {/* Mobile Layout */}
          <div className="md:hidden grid grid-cols-3 gap-2 text-sm">
            <div>
              <span className="text-muted-foreground">목표가:</span>{' '}
              <span className="font-medium">{formatNumber(item.target_price)}</span>
            </div>
            <div>
              <span className="text-muted-foreground">손절가:</span>{' '}
              <span className="font-medium">{formatNumber(item.stop_loss_price)}</span>
            </div>
            <div>
              <span className="text-muted-foreground">수량:</span>{' '}
              <span className="font-medium">{item.quantity ?? '-'}</span>
            </div>
          </div>

          {/* Desktop Layout */}
          <div className="hidden md:block text-right font-medium">
            {item.target_price ? (
              <span>{formatNumber(item.target_price)}원</span>
            ) : (
              <span className="text-muted-foreground">-</span>
            )}
          </div>
          <div className="hidden md:block text-right font-medium">
            {item.stop_loss_price ? (
              <span>{formatNumber(item.stop_loss_price)}원</span>
            ) : (
              <span className="text-muted-foreground">-</span>
            )}
          </div>
          <div className="hidden md:block text-right font-medium">
            {item.quantity ? (
              <span>{formatNumber(item.quantity)}주</span>
            ) : (
              <span className="text-muted-foreground">-</span>
            )}
          </div>
          <div className="hidden md:block truncate text-sm text-muted-foreground">
            {item.memo || '-'}
          </div>

          {/* Active Toggle */}
          <div className="flex items-center justify-between md:justify-center">
            <span className="md:hidden text-sm text-muted-foreground">활성화:</span>
            <Switch
              checked={item.is_active}
              onCheckedChange={() => handleToggle(item)}
              disabled={actionLoading === item.id}
            />
          </div>

          {/* Actions */}
          <div className="flex items-center justify-end md:justify-center">
            {actionLoading === item.id ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-8 w-8">
                    <MoreHorizontal className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuItem onClick={() => onEdit(item)}>
                    <Pencil className="mr-2 h-4 w-4" />
                    수정
                  </DropdownMenuItem>
                  <DropdownMenuItem
                    className="text-red-600"
                    onClick={() => handleDelete(item)}
                  >
                    <Trash2 className="mr-2 h-4 w-4" />
                    삭제
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            )}
          </div>

          {/* Mobile Memo */}
          {item.memo && (
            <div className="md:hidden text-sm text-muted-foreground col-span-full">
              <span className="font-medium">메모:</span> {item.memo}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
