'use client';

import * as React from 'react';
import { Button, Input, Card, CardContent, CardHeader, CardTitle, CardDescription, Label } from '@/components/ui';
import { BacktestRunRequest } from '@/lib/api/backtest';
import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { StockSearchInput } from '@/components/watchlist/stock-search-input';
import { Badge } from '@/components/ui/badge';
import { X } from 'lucide-react';
import { type StockInfo } from '@/lib/api';

interface BacktestFormProps {
  onSubmit: (request: BacktestRunRequest) => void;
  isLoading?: boolean;
}

export function BacktestForm({ onSubmit, isLoading = false }: BacktestFormProps) {
  const [stockCodes, setStockCodes] = useState<string[]>([]);
  const [formData, setFormData] = useState({
    startDate: '2023-01-01',
    endDate: new Date().toISOString().split('T')[0],
    initialCapital: '10000000',
    stopLossPct: '5',
    takeProfitPct: '10',
    maxPositionPct: '100',
    maxPositions: '1',
    name: '',
  });

  const handleStockSelect = (stock: StockInfo) => {
    if (!stockCodes.includes(stock.code)) {
      setStockCodes([...stockCodes, stock.code]);
    }
  };

  const handleRemoveStock = (codeToRemove: string) => {
    setStockCodes(stockCodes.filter(code => code !== codeToRemove));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (stockCodes.length === 0) return;

    onSubmit({
      stock_codes: stockCodes,
      start_date: formData.startDate,
      end_date: formData.endDate,
      name: formData.name || `Backtest ${new Date().toLocaleDateString()}`,
      initial_capital: Number(formData.initialCapital),
      stop_loss_pct: Number(formData.stopLossPct),
      take_profit_pct: Number(formData.takeProfitPct),
      max_position_pct: Number(formData.maxPositionPct),
      max_positions: Number(formData.maxPositions),
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>백테스트 실행</CardTitle>
        <CardDescription>
          과거 데이터로 전략을 테스트하기 위한 파라미터를 설정하세요.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label>대상 종목</Label>
            <StockSearchInput onSelect={handleStockSelect} />
            <div className="flex flex-wrap gap-2 mt-2">
              {stockCodes.map((code) => (
                <Badge key={code} variant="secondary" className="pl-2 pr-1 py-1">
                  {code}
                  <button
                    type="button"
                    onClick={() => handleRemoveStock(code)}
                    className="ml-1 hover:text-destructive"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
              {stockCodes.length === 0 && (
                <span className="text-sm text-muted-foreground">선택된 종목 없음</span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="startDate">시작일</Label>
              <Input
                id="startDate"
                type="date"
                value={formData.startDate}
                onChange={(e) => setFormData({ ...formData, startDate: e.target.value })}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="endDate">종료일</Label>
              <Input
                id="endDate"
                type="date"
                value={formData.endDate}
                onChange={(e) => setFormData({ ...formData, endDate: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="initialCapital">초기 자본금 (원)</Label>
              <Input
                id="initialCapital"
                type="number"
                value={formData.initialCapital}
                onChange={(e) => setFormData({ ...formData, initialCapital: e.target.value })}
                min="0"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">백테스트명 (선택)</Label>
              <Input
                id="name"
                placeholder="예: 전략 테스트 #1"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="space-y-2">
              <Label htmlFor="stopLoss">손절 (%)</Label>
              <Input
                id="stopLoss"
                type="number"
                value={formData.stopLossPct}
                onChange={(e) => setFormData({ ...formData, stopLossPct: e.target.value })}
                step="0.1"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="takeProfit">익절 (%)</Label>
              <Input
                id="takeProfit"
                type="number"
                value={formData.takeProfitPct}
                onChange={(e) => setFormData({ ...formData, takeProfitPct: e.target.value })}
                step="0.1"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxPositionPct">최대 포지션 (%)</Label>
              <Input
                id="maxPositionPct"
                type="number"
                value={formData.maxPositionPct}
                onChange={(e) => setFormData({ ...formData, maxPositionPct: e.target.value })}
                min="1"
                max="100"
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="maxPositions">최대 종목 수</Label>
              <Input
                id="maxPositions"
                type="number"
                value={formData.maxPositions}
                onChange={(e) => setFormData({ ...formData, maxPositions: e.target.value })}
                min="1"
                required
              />
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={isLoading || stockCodes.length === 0}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                백테스트 실행 중...
              </>
            ) : (
              '백테스트 실행'
            )}
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
