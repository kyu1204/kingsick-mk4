'use client';

import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { ApiKeySettings } from '@/components/settings';
import { ProtectedRoute } from '@/components/auth';

export default function SettingsPage() {
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
                <div className="flex items-center justify-between p-4 border rounded-lg">
                  <div>
                    <p className="font-medium">AUTO Mode</p>
                    <p className="text-sm text-muted-foreground">
                      Automatically execute trades based on AI signals
                    </p>
                  </div>
                  <Badge variant="profit">Active</Badge>
                </div>
                <div className="flex items-center justify-between p-4 border rounded-lg opacity-50">
                  <div>
                    <p className="font-medium">ALERT Mode</p>
                    <p className="text-sm text-muted-foreground">
                      Send notifications for manual approval
                    </p>
                  </div>
                  <Badge variant="secondary">Inactive</Badge>
                </div>
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
                  <Input type="number" placeholder="5" defaultValue="5" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Stop Loss (%)</label>
                  <Input type="number" placeholder="3" defaultValue="3" />
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Take Profit (%)</label>
                  <Input type="number" placeholder="5" defaultValue="5" />
                </div>
                <Button className="w-full">Save Risk Settings</Button>
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
