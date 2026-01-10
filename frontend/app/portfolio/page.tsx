'use client';

import { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Loader2, AlertCircle } from 'lucide-react';
import { ProtectedRoute } from '@/components/auth';
import { positionsApi, PositionSchema, BalanceResponse } from '@/lib/api/positions';

// Mock data for when KIS API is not configured
const mockPositions: PositionSchema[] = [
  {
    stock_code: '005930',
    stock_name: 'Samsung Electronics',
    quantity: 150,
    avg_price: 70500,
    current_price: 72500,
    profit_loss: 300000,
    profit_loss_rate: 2.84,
  },
  {
    stock_code: '035420',
    stock_name: 'NAVER',
    quantity: 50,
    avg_price: 210000,
    current_price: 215500,
    profit_loss: 275000,
    profit_loss_rate: 2.62,
  },
  {
    stock_code: '035720',
    stock_name: 'Kakao',
    quantity: 200,
    avg_price: 55000,
    current_price: 52300,
    profit_loss: -540000,
    profit_loss_rate: -4.91,
  },
  {
    stock_code: '006400',
    stock_name: 'Samsung SDI',
    quantity: 30,
    avg_price: 420000,
    current_price: 438500,
    profit_loss: 555000,
    profit_loss_rate: 4.40,
  },
];

export default function PortfolioPage() {
  const [positions, setPositions] = useState<PositionSchema[]>([]);
  const [balance, setBalance] = useState<BalanceResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isMockData, setIsMockData] = useState(false);

  const fetchPortfolioData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setIsMockData(false);

    try {
      const [positionsRes, balanceRes] = await Promise.all([
        positionsApi.getPositions(),
        positionsApi.getBalance(),
      ]);
      setPositions(positionsRes.positions);
      setBalance(balanceRes);
    } catch (err) {
      console.error('Failed to fetch portfolio data:', err);
      // Use mock data if KIS API is not configured (503 error)
      setPositions(mockPositions);
      setIsMockData(true);
      setError('KIS API가 설정되지 않아 샘플 데이터를 표시합니다.');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchPortfolioData();
  }, [fetchPortfolioData]);

  const totalValue = positions.reduce((acc, pos) => acc + pos.current_price * pos.quantity, 0);
  const totalPnl = positions.reduce((acc, pos) => acc + pos.profit_loss, 0);
  const totalPnlPercent = totalValue - totalPnl > 0 ? (totalPnl / (totalValue - totalPnl)) * 100 : 0;

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
          <div>
            <h1 className="text-3xl font-bold tracking-tight">포트폴리오</h1>
            <p className="text-muted-foreground">
              현재 보유 종목 및 성과
            </p>
          </div>

          {/* Warning for mock data */}
          {isMockData && error && (
            <div className="flex items-center gap-2 p-4 bg-yellow-500/10 border border-yellow-500/50 rounded-lg">
              <AlertCircle className="h-5 w-5 text-yellow-500" />
              <p className="text-sm text-yellow-500">{error}</p>
            </div>
          )}

          {/* Portfolio Summary */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">총 평가금액</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {totalValue.toLocaleString('ko-KR')}
                  <span className="text-sm font-normal text-muted-foreground ml-1">원</span>
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">총 손익</CardTitle>
              </CardHeader>
              <CardContent>
                <div className={`text-2xl font-bold ${totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {totalPnl >= 0 ? '+' : ''}{totalPnl.toLocaleString('ko-KR')}
                  <span className="text-sm font-normal ml-1">원</span>
                </div>
                <p className={`text-sm ${totalPnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                  {totalPnl >= 0 ? '+' : ''}{totalPnlPercent.toFixed(2)}%
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">보유 종목</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {positions.length}
                  <span className="text-sm font-normal text-muted-foreground ml-1">종목</span>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Positions Table */}
          <Card>
            <CardHeader>
              <CardTitle>보유 종목</CardTitle>
              <CardDescription>
                현재 보유 중인 모든 종목
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {/* Table Header */}
                <div className="grid grid-cols-7 gap-4 text-sm font-medium text-muted-foreground border-b pb-2">
                  <div>종목코드</div>
                  <div>종목명</div>
                  <div className="text-right">수량</div>
                  <div className="text-right">평균단가</div>
                  <div className="text-right">현재가</div>
                  <div className="text-right">손익</div>
                  <div className="text-center">상태</div>
                </div>

                {/* Table Body */}
                {positions.map((pos) => (
                  <div
                    key={pos.stock_code}
                    className="grid grid-cols-7 gap-4 items-center py-3 border-b border-border/50 hover:bg-accent/50 rounded-lg px-2 -mx-2 transition-colors"
                  >
                    <div className="font-mono text-sm">{pos.stock_code}</div>
                    <div className="font-medium">{pos.stock_name}</div>
                    <div className="text-right">{pos.quantity}</div>
                    <div className="text-right">{pos.avg_price.toLocaleString('ko-KR')}</div>
                    <div className="text-right font-medium">{pos.current_price.toLocaleString('ko-KR')}</div>
                    <div className={`text-right ${pos.profit_loss >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                      <div className="flex items-center justify-end gap-1">
                        {pos.profit_loss >= 0 ? (
                          <TrendingUp className="h-4 w-4" />
                        ) : (
                          <TrendingDown className="h-4 w-4" />
                        )}
                        {pos.profit_loss >= 0 ? '+' : ''}{pos.profit_loss.toLocaleString('ko-KR')}
                      </div>
                      <div className="text-xs">
                        ({pos.profit_loss >= 0 ? '+' : ''}{pos.profit_loss_rate.toFixed(2)}%)
                      </div>
                    </div>
                    <div className="text-center">
                      <Badge variant={pos.profit_loss >= 0 ? 'profit' : 'loss'}>
                        {pos.profit_loss >= 0 ? '이익' : '손실'}
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
