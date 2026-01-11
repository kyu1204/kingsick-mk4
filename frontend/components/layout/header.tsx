'use client';

import { useState, useEffect, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import { Moon, Sun, Bell, User, Activity, LogOut, Settings, Shield, TrendingUp, TrendingDown, BellOff } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useAuth } from '@/lib/auth';
import { tradingApi, AlertSchema } from '@/lib/api';

function isMarketOpen(): boolean {
  const now = new Date();
  const kstOffset = 9 * 60;
  const utcMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
  const kstMinutes = utcMinutes + kstOffset;
  const kstHour = Math.floor((kstMinutes % (24 * 60)) / 60);
  const kstMinute = kstMinutes % 60;

  const kstDate = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Seoul' }));
  const dayOfWeek = kstDate.getDay();
  if (dayOfWeek === 0 || dayOfWeek === 6) return false;

  const marketOpenMinutes = 9 * 60;
  const marketCloseMinutes = 15 * 60 + 30;
  const currentMinutes = kstHour * 60 + kstMinute;

  return currentMinutes >= marketOpenMinutes && currentMinutes <= marketCloseMinutes;
}

export function Header() {
  const { theme, setTheme } = useTheme();
  const { user, logout } = useAuth();
  const router = useRouter();
  const [marketOpen, setMarketOpen] = useState(false);
  const [pendingAlertsCount, setPendingAlertsCount] = useState(0);
  const [alerts, setAlerts] = useState<AlertSchema[]>([]);

  const updateMarketStatus = useCallback(() => {
    setMarketOpen(isMarketOpen());
  }, []);

  useEffect(() => {
    updateMarketStatus();
    const interval = setInterval(updateMarketStatus, 60000);
    return () => clearInterval(interval);
  }, [updateMarketStatus]);

  useEffect(() => {
    const fetchAlerts = async () => {
      try {
        const [status, alertsRes] = await Promise.all([
          tradingApi.getStatus(),
          tradingApi.getAlerts(),
        ]);
        setPendingAlertsCount(status.pending_alerts_count);
        setAlerts(alertsRes.alerts);
      } catch {
        setPendingAlertsCount(0);
        setAlerts([]);
      }
    };

    fetchAlerts();
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = async () => {
    await logout();
    router.push('/login');
  };

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="flex h-14 items-center px-4 md:px-6">
        {/* Logo */}
        <Link href="/dashboard" className="flex items-center gap-2 font-bold">
          <Activity className="h-6 w-6 text-primary" />
          <span className="hidden md:inline-block">KingSick</span>
        </Link>

        {/* Spacer */}
        <div className="flex-1" />

        {/* Right side actions */}
        <div className="flex items-center gap-2">
          {/* Market Status Indicator */}
          <div className="hidden md:flex items-center gap-2 mr-4 text-sm">
            <span className="relative flex h-2 w-2">
              {marketOpen ? (
                <>
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
                </>
              ) : (
                <span className="relative inline-flex rounded-full h-2 w-2 bg-gray-400"></span>
              )}
            </span>
            <span className="text-muted-foreground">
              {marketOpen ? '장 운영중' : '장 마감'}
            </span>
          </div>

          {/* Notifications */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" className="relative">
                <Bell className="h-5 w-5" />
                {pendingAlertsCount > 0 && (
                  <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-destructive" />
                )}
                <span className="sr-only">알림</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-80">
              <DropdownMenuLabel>알림</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {alerts.length > 0 ? (
                alerts.slice(0, 5).map((alert) => (
                  <DropdownMenuItem key={alert.alert_id} className="flex flex-col items-start gap-1 p-3">
                    <div className="flex items-center gap-2 w-full">
                      {alert.signal_type === 'BUY' ? (
                        <TrendingUp className="h-4 w-4 text-green-500 shrink-0" />
                      ) : (
                        <TrendingDown className="h-4 w-4 text-red-500 shrink-0" />
                      )}
                      <span className="font-medium">{alert.stock_code}</span>
                      <Badge variant={alert.signal_type === 'BUY' ? 'profit' : 'loss'} className="ml-auto">
                        {alert.signal_type}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground line-clamp-2">{alert.reason}</p>
                    <p className="text-xs text-muted-foreground">
                      {alert.current_price.toLocaleString('ko-KR')}원 · {alert.suggested_quantity}주
                    </p>
                  </DropdownMenuItem>
                ))
              ) : (
                <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                  <BellOff className="h-8 w-8 mb-2 opacity-50" />
                  <p className="text-sm">대기 중인 알림이 없습니다</p>
                </div>
              )}
              {alerts.length > 5 && (
                <>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem asChild>
                    <Link href="/dashboard" className="text-center text-sm text-primary cursor-pointer justify-center">
                      모든 알림 보기 ({alerts.length}건)
                    </Link>
                  </DropdownMenuItem>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>

          {/* Theme toggle */}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
          >
            <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
            <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
            <span className="sr-only">테마 전환</span>
          </Button>

          {/* User menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon">
                <User className="h-5 w-5" />
                <span className="sr-only">사용자 메뉴</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="font-normal">
                <div className="flex flex-col space-y-1">
                  <p className="text-sm font-medium leading-none">
                    {user?.email || 'User'}
                  </p>
                  {user?.is_admin && (
                    <p className="text-xs leading-none text-muted-foreground">
                      관리자
                    </p>
                  )}
                </div>
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem asChild>
                <Link href="/settings" className="cursor-pointer">
                  <Settings className="mr-2 h-4 w-4" />
                  설정
                </Link>
              </DropdownMenuItem>
              {user?.is_admin && (
                <DropdownMenuItem asChild>
                  <Link href="/admin" className="cursor-pointer">
                    <Shield className="mr-2 h-4 w-4" />
                    관리자
                  </Link>
                </DropdownMenuItem>
              )}
              <DropdownMenuSeparator />
              <DropdownMenuItem
                onClick={handleLogout}
                className="cursor-pointer text-destructive focus:text-destructive"
              >
                <LogOut className="mr-2 h-4 w-4" />
                로그아웃
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>
    </header>
  );
}
