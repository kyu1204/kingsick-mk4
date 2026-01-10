'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { slackApi, SlackStatusResponse } from '@/lib/api';

export function SlackSettings() {
  const [status, setStatus] = useState<SlackStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [webhookUrl, setWebhookUrl] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStatus = useCallback(async () => {
    try {
      setError(null);
      const data = await slackApi.getStatus();
      setStatus(data);
    } catch (err) {
      console.error(err);
      setError('Failed to load Slack status');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  const handleSave = async () => {
    if (!webhookUrl) return;

    setIsSaving(true);
    setError(null);
    try {
      const data = await slackApi.saveWebhook({ webhook_url: webhookUrl });
      setStatus(data);
      setWebhookUrl('');
    } catch (err) {
      console.error(err);
      setError('Failed to save Slack webhook');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    setIsTesting(true);
    setError(null);
    try {
      const result = await slackApi.testWebhook();
      if (!result.success) {
        setError('Test message failed');
      }
    } catch (err) {
      console.error(err);
      setError('Failed to send test message');
    } finally {
      setIsTesting(false);
    }
  };

  const handleDelete = async () => {
    setIsDeleting(true);
    setError(null);
    try {
      await slackApi.deleteWebhook();
      setStatus({ configured: false, webhook_url_masked: null });
    } catch (err) {
      console.error(err);
      setError('Failed to disconnect Slack');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Slack Notifications</CardTitle>
        <CardDescription>
          Connect Slack to receive trading alerts
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {error && (
          <div className="p-3 text-sm text-red-500 bg-red-500/10 border border-red-500/20 rounded-lg">
            {error}
          </div>
        )}

        {isLoading ? (
          <div className="flex items-center justify-center p-4">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary"></div>
          </div>
        ) : status?.configured ? (
          <>
            <div className="flex items-center justify-between p-4 border rounded-lg bg-green-500/5 border-green-500/20">
              <div>
                <p className="font-medium">Slack</p>
                <p className="text-sm text-muted-foreground">
                  Configured: {status.webhook_url_masked}
                </p>
              </div>
              <Badge variant="profit">Connected</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              You will receive trading alerts in your configured Slack channel.
            </p>
            <div className="flex gap-2">
              <Button
                variant="outline"
                className="flex-1"
                onClick={handleTest}
                disabled={isTesting}
              >
                {isTesting ? 'Sending...' : 'Test'}
              </Button>
              <Button
                variant="outline"
                className="flex-1 text-red-500 hover:text-red-600 hover:bg-red-500/10"
                onClick={handleDelete}
                disabled={isDeleting}
              >
                {isDeleting ? 'Disconnecting...' : 'Disconnect'}
              </Button>
            </div>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium">Slack</p>
                <p className="text-sm text-muted-foreground">
                  Not configured
                </p>
              </div>
              <Badge variant="secondary">Disconnected</Badge>
            </div>
            <div className="space-y-2">
              <Input
                placeholder="https://hooks.slack.com/services/..."
                value={webhookUrl}
                onChange={(e) => setWebhookUrl(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Enter your Slack Incoming Webhook URL
              </p>
            </div>
            <Button
              className="w-full"
              onClick={handleSave}
              disabled={isSaving || !webhookUrl}
            >
              {isSaving ? 'Saving...' : 'Save Webhook'}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
