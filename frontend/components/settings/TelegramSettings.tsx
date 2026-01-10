'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { telegramApi, TelegramStatusResponse } from '@/lib/api';

export function TelegramSettings() {
  const [status, setStatus] = useState<TelegramStatusResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLinking, setIsLinking] = useState(false);
  const [isUnlinking, setIsUnlinking] = useState(false);
  const [deepLink, setDeepLink] = useState<string | null>(null);
  const [expiresIn, setExpiresIn] = useState<number>(0);
  const [error, setError] = useState<string | null>(null);

  // Fetch Telegram status on mount
  const fetchStatus = useCallback(async () => {
    try {
      setError(null);
      const data = await telegramApi.getStatus();
      setStatus(data);
      // Clear deep link if already connected
      if (data.linked) {
        setDeepLink(null);
      }
    } catch (err) {
      console.error('Failed to fetch Telegram status:', err);
      setError('Failed to load Telegram status');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchStatus();
  }, [fetchStatus]);

  // Countdown timer for deep link expiry
  useEffect(() => {
    if (expiresIn <= 0) return;

    const timer = setInterval(() => {
      setExpiresIn((prev) => {
        if (prev <= 1) {
          setDeepLink(null);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [expiresIn]);

  // Poll for status updates when linking
  useEffect(() => {
    if (!deepLink || !expiresIn) return;

    const pollInterval = setInterval(async () => {
      try {
        const data = await telegramApi.getStatus();
        if (data.linked) {
          setStatus(data);
          setDeepLink(null);
          setExpiresIn(0);
        }
      } catch (err) {
        console.error('Failed to poll Telegram status:', err);
      }
    }, 3000); // Poll every 3 seconds

    return () => clearInterval(pollInterval);
  }, [deepLink, expiresIn]);

  // Handle link request
  const handleLink = async () => {
    if (isLinking) return;

    setIsLinking(true);
    setError(null);
    try {
      const data = await telegramApi.createLinkToken();
      setDeepLink(data.deep_link);
      setExpiresIn(data.expires_in);
    } catch (err) {
      console.error('Failed to create link token:', err);
      setError('Failed to create link. Please try again.');
    } finally {
      setIsLinking(false);
    }
  };

  // Handle unlink request
  const handleUnlink = async () => {
    if (isUnlinking) return;

    setIsUnlinking(true);
    setError(null);
    try {
      await telegramApi.unlink();
      setStatus({ linked: false, linked_at: null });
    } catch (err) {
      console.error('Failed to unlink Telegram:', err);
      setError('Failed to unlink. Please try again.');
    } finally {
      setIsUnlinking(false);
    }
  };

  // Format time remaining
  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  // Format linked date
  const formatLinkedDate = (dateStr: string | null): string => {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString('ko-KR', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Telegram Notifications</CardTitle>
        <CardDescription>
          Connect your Telegram account to receive trading alerts
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
        ) : status?.linked ? (
          // Connected state
          <>
            <div className="flex items-center justify-between p-4 border rounded-lg bg-green-500/5 border-green-500/20">
              <div>
                <p className="font-medium">Telegram</p>
                <p className="text-sm text-muted-foreground">
                  Connected {status.linked_at && `on ${formatLinkedDate(status.linked_at)}`}
                </p>
              </div>
              <Badge variant="profit">Connected</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              You will receive trading alerts and can approve/reject trades directly from Telegram.
            </p>
            <Button
              variant="outline"
              className="w-full text-red-500 hover:text-red-600 hover:bg-red-500/10"
              onClick={handleUnlink}
              disabled={isUnlinking}
            >
              {isUnlinking ? 'Disconnecting...' : 'Disconnect Telegram'}
            </Button>
          </>
        ) : deepLink ? (
          // Linking in progress
          <>
            <div className="flex items-center justify-between p-4 border rounded-lg border-blue-500/20 bg-blue-500/5">
              <div>
                <p className="font-medium">Telegram</p>
                <p className="text-sm text-muted-foreground">
                  Waiting for connection...
                </p>
              </div>
              <Badge variant="secondary">Pending</Badge>
            </div>
            <div className="space-y-3">
              <p className="text-sm">
                Click the button below to open Telegram and connect your account:
              </p>
              <a
                href={deepLink}
                target="_blank"
                rel="noopener noreferrer"
                className="block"
              >
                <Button className="w-full" variant="default">
                  Open Telegram
                </Button>
              </a>
              <p className="text-xs text-center text-muted-foreground">
                Link expires in {formatTime(expiresIn)}
              </p>
            </div>
            <Button
              variant="ghost"
              className="w-full"
              onClick={() => {
                setDeepLink(null);
                setExpiresIn(0);
              }}
            >
              Cancel
            </Button>
          </>
        ) : (
          // Not connected state
          <>
            <div className="flex items-center justify-between p-4 border rounded-lg">
              <div>
                <p className="font-medium">Telegram</p>
                <p className="text-sm text-muted-foreground">
                  Not connected
                </p>
              </div>
              <Badge variant="secondary">Disconnected</Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              Connect your Telegram account to receive real-time trading alerts and approve/reject trades with a single tap.
            </p>
            <Button
              className="w-full"
              onClick={handleLink}
              disabled={isLinking}
            >
              {isLinking ? 'Creating Link...' : 'Connect Telegram'}
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
}
