'use client';

import { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ApiKeySettings, TelegramSettings, SlackSettings } from '@/components/settings';
import { ProtectedRoute } from '@/components/auth';
import { tradingApi, TradingMode, RiskSettingsResponse } from '@/lib/api/trading';

export default function SettingsPage() {
  const [tradingMode, setTradingMode] = useState<TradingMode>(TradingMode.ALERT);
  const [isLoadingMode, setIsLoadingMode] = useState(true);
  const [isSwitchingMode, setIsSwitchingMode] = useState(false);

  const [riskSettings, setRiskSettings] = useState<RiskSettingsResponse>({
    stop_loss_pct: -5.0,
    take_profit_pct: 10.0,
    daily_loss_limit_pct: -10.0,
  });
  const [isLoadingRisk, setIsLoadingRisk] = useState(true);
  const [isSavingRisk, setIsSavingRisk] = useState(false);

  const fetchTradingStatus = useCallback(async () => {
    try {
      const status = await tradingApi.getStatus();
      setTradingMode(status.mode);
    } catch (error) {
      console.error('Failed to fetch trading status:', error);
    } finally {
      setIsLoadingMode(false);
    }
  }, []);

  const fetchRiskSettings = useCallback(async () => {
    try {
      const settings = await tradingApi.getRiskSettings();
      setRiskSettings(settings);
    } catch (error) {
      console.error('Failed to fetch risk settings:', error);
    } finally {
      setIsLoadingRisk(false);
    }
  }, []);

  useEffect(() => {
    fetchTradingStatus();
    fetchRiskSettings();
  }, [fetchTradingStatus, fetchRiskSettings]);

  const handleModeChange = async (newMode: TradingMode) => {
    if (newMode === tradingMode || isSwitchingMode) return;

    setIsSwitchingMode(true);
    try {
      const status = await tradingApi.setMode(newMode);
      setTradingMode(status.mode);
    } catch (error) {
      console.error('Failed to change trading mode:', error);
    } finally {
      setIsSwitchingMode(false);
    }
  };

  const handleSaveRiskSettings = async () => {
    if (isSavingRisk) return;

    setIsSavingRisk(true);
    try {
      const updated = await tradingApi.updateRiskSettings({
        stop_loss_pct: riskSettings.stop_loss_pct,
        take_profit_pct: riskSettings.take_profit_pct,
        daily_loss_limit_pct: riskSettings.daily_loss_limit_pct,
      });
      setRiskSettings(updated);
    } catch (error) {
      console.error('Failed to save risk settings:', error);
    } finally {
      setIsSavingRisk(false);
    }
  };

  return (
    <ProtectedRoute>
      <MainLayout>
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">설정</h1>
            <p className="text-muted-foreground">
              트레이딩 환경 설정 및 API 연결 관리
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle>트레이딩 모드</CardTitle>
                <CardDescription>
                  자동 매매 또는 수동 승인 중 선택
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <button
                  onClick={() => handleModeChange(TradingMode.AUTO)}
                  disabled={isLoadingMode || isSwitchingMode}
                  className={`w-full flex items-center justify-between p-4 border rounded-lg transition-all ${
                    tradingMode === TradingMode.AUTO
                      ? 'border-green-500 bg-green-500/10'
                      : 'hover:border-muted-foreground/50 opacity-50'
                  } ${isSwitchingMode ? 'cursor-wait' : 'cursor-pointer'}`}
                >
                  <div className="text-left">
                    <p className="font-medium">자동 모드</p>
                    <p className="text-sm text-muted-foreground">
                      AI 신호에 따라 자동으로 매매 실행
                    </p>
                  </div>
                  <Badge variant={tradingMode === TradingMode.AUTO ? 'profit' : 'secondary'}>
                    {tradingMode === TradingMode.AUTO ? '활성화' : '비활성화'}
                  </Badge>
                </button>
                <button
                  onClick={() => handleModeChange(TradingMode.ALERT)}
                  disabled={isLoadingMode || isSwitchingMode}
                  className={`w-full flex items-center justify-between p-4 border rounded-lg transition-all ${
                    tradingMode === TradingMode.ALERT
                      ? 'border-blue-500 bg-blue-500/10'
                      : 'hover:border-muted-foreground/50 opacity-50'
                  } ${isSwitchingMode ? 'cursor-wait' : 'cursor-pointer'}`}
                >
                  <div className="text-left">
                    <p className="font-medium">알림 모드</p>
                    <p className="text-sm text-muted-foreground">
                      수동 승인을 위한 알림 전송
                    </p>
                  </div>
                  <Badge variant={tradingMode === TradingMode.ALERT ? 'profit' : 'secondary'}>
                    {tradingMode === TradingMode.ALERT ? '활성화' : '비활성화'}
                  </Badge>
                </button>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>리스크 관리</CardTitle>
                <CardDescription>
                  위험 허용도 및 손실 한도 설정
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">일일 손실 한도 (%)</label>
                  <Input
                    type="number"
                    placeholder="-10"
                    value={Math.abs(riskSettings.daily_loss_limit_pct)}
                    onChange={(e) =>
                      setRiskSettings((prev) => ({
                        ...prev,
                        daily_loss_limit_pct: -Math.abs(parseFloat(e.target.value) || 0),
                      }))
                    }
                    disabled={isLoadingRisk}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">손절 (%)</label>
                  <Input
                    type="number"
                    placeholder="-5"
                    value={Math.abs(riskSettings.stop_loss_pct)}
                    onChange={(e) =>
                      setRiskSettings((prev) => ({
                        ...prev,
                        stop_loss_pct: -Math.abs(parseFloat(e.target.value) || 0),
                      }))
                    }
                    disabled={isLoadingRisk}
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">익절 (%)</label>
                  <Input
                    type="number"
                    placeholder="10"
                    value={riskSettings.take_profit_pct}
                    onChange={(e) =>
                      setRiskSettings((prev) => ({
                        ...prev,
                        take_profit_pct: Math.abs(parseFloat(e.target.value) || 0),
                      }))
                    }
                    disabled={isLoadingRisk}
                  />
                </div>
                <Button
                  className="w-full"
                  onClick={handleSaveRiskSettings}
                  disabled={isLoadingRisk || isSavingRisk}
                >
                  {isSavingRisk ? '저장 중...' : '리스크 설정 저장'}
                </Button>
              </CardContent>
            </Card>

            <ApiKeySettings />

            <TelegramSettings />

            <SlackSettings />
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
