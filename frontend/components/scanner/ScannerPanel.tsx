import * as React from 'react';
import { cn, formatKRW } from '@/lib/utils';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
  Button,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
  Badge,
  Input,
} from '@/components/ui';
import { scannerApi } from '@/lib/api';
import { ScanResultResponse, ScanTypeEnum } from '@/types/api';
import { Search, SlidersHorizontal, ArrowUpRight, ArrowDownRight, Activity } from 'lucide-react';

export function ScannerPanel() {
  const [results, setResults] = React.useState<ScanResultResponse[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [total, setTotal] = React.useState(0);
  const [error, setError] = React.useState<string | null>(null);

  const [scanType, setScanType] = React.useState<ScanTypeEnum>('BUY');
  const [minConfidence, setMinConfidence] = React.useState(0.7);
  const [limit, setLimit] = React.useState(10);

  const handleScan = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await scannerApi.scanMarket(scanType, minConfidence, limit);
      setResults(response.results);
      setTotal(response.total);
    } catch (err) {
      setError('Failed to scan market. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="border-border/40 shadow-sm">
      <CardHeader>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-xl flex items-center gap-2">
              <Activity className="h-5 w-5 text-primary" />
              AI 시장 스캐너
            </CardTitle>
            <CardDescription>
              AI 기반으로 한국 시장의 트레이딩 기회를 스캔합니다
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Button 
              onClick={handleScan} 
              disabled={loading}
              className="w-full sm:w-auto min-w-[120px]"
            >
              {loading ? (
                <div className="flex items-center gap-2">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-background border-t-transparent" />
                  스캔 중...
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Search className="h-4 w-4" />
                  시장 스캔
                </div>
              )}
            </Button>
          </div>
        </div>

        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-end bg-muted/30 p-4 rounded-lg border border-border/40">
          <div className="grid gap-2 flex-1">
            <label className="text-sm font-medium">스캔 유형</label>
            <select
              className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
              value={scanType} 
              onChange={(e) => setScanType(e.target.value as ScanTypeEnum)}
            >
              <option value="BUY">매수 신호</option>
              <option value="SELL">매도 신호</option>
            </select>
          </div>

          <div className="grid gap-2 flex-1">
            <label className="text-sm font-medium">최소 신뢰도 (0.0 - 1.0)</label>
            <Input
              type="number"
              min={0}
              max={1}
              step={0.1}
              value={minConfidence}
              onChange={(e) => setMinConfidence(parseFloat(e.target.value))}
            />
          </div>

          <div className="grid gap-2 flex-1">
            <label className="text-sm font-medium">결과 수 제한</label>
            <Input
              type="number"
              min={1}
              max={50}
              value={limit}
              onChange={(e) => setLimit(parseInt(e.target.value))}
            />
          </div>
        </div>
      </CardHeader>

      <CardContent>
        {error && (
          <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </div>
        )}

        {results.length > 0 ? (
          <div className="rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>종목</TableHead>
                  <TableHead>신호</TableHead>
                  <TableHead className="text-right">현재가</TableHead>
                  <TableHead className="text-right">신뢰도</TableHead>
                  <TableHead className="text-right">RSI</TableHead>
                  <TableHead className="text-center">거래량 급등</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {results.map((result) => (
                  <TableRow key={result.stock_code}>
                    <TableCell>
                      <div className="flex flex-col">
                        <span className="font-medium">{result.stock_name}</span>
                        <span className="text-xs text-muted-foreground">{result.stock_code}</span>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge 
                        variant={result.signal === 'BUY' ? 'profit' : 'loss'}
                        className="font-mono"
                      >
                        {result.signal === 'BUY' ? (
                          <ArrowUpRight className="mr-1 h-3 w-3" />
                        ) : (
                          <ArrowDownRight className="mr-1 h-3 w-3" />
                        )}
                        {result.signal}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {formatKRW(result.current_price)}
                    </TableCell>
                    <TableCell className="text-right font-mono">
                      {(result.confidence * 100).toFixed(1)}%
                    </TableCell>
                    <TableCell className="text-right font-mono text-muted-foreground">
                      {result.rsi?.toFixed(1) || '-'}
                    </TableCell>
                    <TableCell className="text-center">
                      {result.volume_spike && (
                        <Badge variant="outline" className="text-xs border-orange-500/50 text-orange-500 bg-orange-500/10">
                          급등
                        </Badge>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ) : (
          <div className="flex h-[200px] flex-col items-center justify-center rounded-md border border-dashed text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted">
              <SlidersHorizontal className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="mt-4 text-lg font-semibold">스캔 결과 없음</h3>
            <p className="text-sm text-muted-foreground">
              파라미터를 조정하고 시장 스캔을 클릭하여 기회를 찾으세요.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
