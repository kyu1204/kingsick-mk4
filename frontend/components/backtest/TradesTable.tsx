import * as React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui';
import { BacktestTrade } from '@/lib/api/backtest';
import { cn, formatKRW, formatPercent } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface TradesTableProps {
  trades: BacktestTrade[];
}

export function TradesTable({ trades }: TradesTableProps) {
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>일자</TableHead>
            <TableHead>종목</TableHead>
            <TableHead>구분</TableHead>
            <TableHead className="text-right">가격</TableHead>
            <TableHead className="text-right">수량</TableHead>
            <TableHead className="text-right">금액</TableHead>
            <TableHead className="text-right">손익</TableHead>
            <TableHead>사유</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {trades.map((trade, index) => {
            const isBuy = trade.side === 'BUY';
            const isProfit = trade.pnl >= 0;

            return (
              <TableRow key={`${trade.stock_code}-${trade.trade_date}-${index}`}>
                <TableCell>{trade.trade_date}</TableCell>
                <TableCell className="font-medium">{trade.stock_code}</TableCell>
                <TableCell>
                  <Badge 
                    variant={isBuy ? "default" : "secondary"}
                    className={cn(
                      isBuy ? "bg-blue-500 hover:bg-blue-600" : "bg-orange-500 hover:bg-orange-600"
                    )}
                  >
                    {trade.side}
                  </Badge>
                </TableCell>
                <TableCell className="text-right">{formatKRW(trade.price)}</TableCell>
                <TableCell className="text-right">{trade.quantity}</TableCell>
                <TableCell className="text-right">{formatKRW(trade.amount)}</TableCell>
                <TableCell className={cn("text-right font-medium", 
                  !isBuy && (isProfit ? "text-profit" : "text-loss")
                )}>
                  {!isBuy ? `${formatKRW(trade.pnl)} (${formatPercent(trade.pnl_pct)})` : '-'}
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {trade.signal_reason}
                </TableCell>
              </TableRow>
            );
          })}
          {trades.length === 0 && (
            <TableRow>
              <TableCell colSpan={8} className="h-24 text-center">
                거래 내역이 없습니다.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  );
}
