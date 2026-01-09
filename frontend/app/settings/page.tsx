'use client';

import { useState, useEffect, useCallback } from 'react';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ApiKeySettings } from '@/components/settings';
import { ProtectedRoute } from '@/components/auth';
import { tradingApi, TradingMode, RiskSettingsResponse } from '@/lib/api/trading';

export default function SettingsPage() {
  const [tradingMode, setTradingMode] = useState<TradingMode>(TradingMode.ALERT);
  const [isLoadingMode, setIsLoadingMode] = useState(true);
  const [isSwitchingMode, setIsSwitchingMode] = useState(false);

  // Risk Settings state
  const [riskSettings, setRiskSettings] = useState<RiskSettingsResponse>({
    stop_loss_pct: -5.0,
    take_profit_pct: 10.0,
    daily_loss_limit_pct: -10.0,
  });
  const [isLoadingRisk, setIsLoadingRisk] = useState(true);
  const [isSavingRisk, setIsSavingRisk] = useState(false);

  // Fetch current trading status on mount
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

  // Fetch risk settings on mount
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

  // Handle mode change
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

  // Handle risk settings save
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
          {/* Page Header */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
            <p className="text-muted-foreground">
              Configure your trading preferences and API connections
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2">
            {/* Trading Mode */}
            <Card>
              <CardHeader>
                <CardTitle>Trading Mode</CardTitle>
                <CardDescription>
                  Choose between automated trading or manual approval
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
                    <p className="font-medium">AUTO Mode</p>
                    <p className="text-sm text-muted-foreground">
                      Automatically execute trades based on AI signals
                    </p>
                  </div>
                  <Badge variant={tradingMode === TradingMode.AUTO ? 'profit' : 'secondary'}>
                    {tradingMode === TradingMode.AUTO ? 'Active' : 'Inactive'}
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
                    <p className="font-medium">ALERT Mode</p>
                    <p className="text-sm text-muted-foreground">
                      Send notifications for manual approval
                    </p>
                  </div>
                  <Badge variant={tradingMode === TradingMode.ALERT ? 'profit' : 'secondary'}>
                    {tradingMode === TradingMode.ALERT ? 'Active' : 'Inactive'}
                  </Badge>
                </button>
              </CardContent>
            </Card>

            {/* Risk Management */}
            <Card>
              <CardHeader>
                <CardTitle>Risk Management</CardTitle>
                <CardDescription>
                  Set your risk tolerance and loss limits
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Daily Loss Limit (%)</label>
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
                  <label className="text-sm font-medium">Stop Loss (%)</label>
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
                  <label className="text-sm font-medium">Take Profit (%)</label>
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
                  {isSavingRisk ? 'Saving...' : 'Save Risk Settings'}
                </Button>
              </CardContent>
            </Card>

            {/* KIS API Connection - Now using the real component */}
            <ApiKeySettings />

            {/* Notifications */}
            <Card>
              <CardHeader>
                <CardTitle>Notifications</CardTitle>
                <CardDescription>
                  Configure alert channels and preferences
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="font-medium">Telegram</p>
                    <p className="text-sm text-muted-foreground">
                      @kingsick_trading_bot
                    </p>
                  </div>
                  <Badge variant="profit">Connected</Badge>
                </div>
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="font-medium">Slack</p>
                    <p className="text-sm text-muted-foreground">
                      #trading-alerts
                    </p>
                  </div>
                  <Badge variant="secondary">Not Connected</Badge>
                </div>
                <Button variant="outline" className="w-full">
                  Manage Notifications
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
