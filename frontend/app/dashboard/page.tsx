import { Metadata } from 'next';
import { MainLayout } from '@/components/layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { TrendingUp, TrendingDown, Activity, DollarSign } from 'lucide-react';

export const metadata: Metadata = {
  title: 'Dashboard',
  description: 'KingSick trading dashboard overview',
};

// Placeholder stats data
type ChangeType = 'profit' | 'loss' | 'neutral';

interface StatItem {
  title: string;
  value: string;
  unit: string;
  change: string;
  changeType: ChangeType;
  icon: React.ComponentType<{ className?: string }>;
}

const stats: StatItem[] = [
  {
    title: 'Total Portfolio Value',
    value: '125,340,000',
    unit: 'KRW',
    change: '+3.2%',
    changeType: 'profit',
    icon: DollarSign,
  },
  {
    title: "Today's P&L",
    value: '+2,450,000',
    unit: 'KRW',
    change: '+1.95%',
    changeType: 'profit',
    icon: TrendingUp,
  },
  {
    title: 'Active Positions',
    value: '8',
    unit: 'stocks',
    change: '+2',
    changeType: 'neutral',
    icon: Activity,
  },
  {
    title: 'Win Rate (30d)',
    value: '68.5%',
    unit: '',
    change: '+5.2%',
    changeType: 'profit',
    icon: TrendingUp,
  },
];

export default function DashboardPage() {
  return (
    <MainLayout>
      <div className="space-y-6">
        {/* Page Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
            <p className="text-muted-foreground">
              Overview of your trading portfolio and recent activity
            </p>
          </div>
          <Badge variant="profit">AUTO Mode Active</Badge>
        </div>

        {/* Stats Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => (
            <Card key={stat.title}>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium">
                  {stat.title}
                </CardTitle>
                <stat.icon className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">
                  {stat.value}
                  {stat.unit && (
                    <span className="text-sm font-normal text-muted-foreground ml-1">
                      {stat.unit}
                    </span>
                  )}
                </div>
                <p
                  className={`text-xs ${
                    stat.changeType === 'profit'
                      ? 'text-green-500'
                      : stat.changeType === 'loss'
                      ? 'text-red-500'
                      : 'text-muted-foreground'
                  }`}
                >
                  {stat.change} from yesterday
                </p>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Main Content Grid */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-7">
          {/* Chart Placeholder */}
          <Card className="col-span-4">
            <CardHeader>
              <CardTitle>Portfolio Performance</CardTitle>
              <CardDescription>
                Your portfolio value over the last 30 days
              </CardDescription>
            </CardHeader>
            <CardContent className="h-[300px] flex items-center justify-center border-2 border-dashed border-muted rounded-lg">
              <p className="text-muted-foreground">Chart will be implemented here</p>
            </CardContent>
          </Card>

          {/* Recent Activity */}
          <Card className="col-span-3">
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
              <CardDescription>
                Latest trading signals and executions
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { stock: 'Samsung Electronics', action: 'BUY', price: '72,500', time: '2 min ago', type: 'profit' },
                  { stock: 'SK Hynix', action: 'SELL', price: '185,000', time: '15 min ago', type: 'loss' },
                  { stock: 'NAVER', action: 'BUY', price: '215,500', time: '1 hour ago', type: 'profit' },
                  { stock: 'Kakao', action: 'HOLD', price: '52,300', time: '2 hours ago', type: 'neutral' },
                ].map((activity, index) => (
                  <div key={index} className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {activity.action === 'BUY' ? (
                        <TrendingUp className="h-4 w-4 text-green-500" />
                      ) : activity.action === 'SELL' ? (
                        <TrendingDown className="h-4 w-4 text-red-500" />
                      ) : (
                        <Activity className="h-4 w-4 text-muted-foreground" />
                      )}
                      <div>
                        <p className="text-sm font-medium">{activity.stock}</p>
                        <p className="text-xs text-muted-foreground">{activity.time}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <Badge
                        variant={
                          activity.action === 'BUY'
                            ? 'profit'
                            : activity.action === 'SELL'
                            ? 'loss'
                            : 'secondary'
                        }
                      >
                        {activity.action}
                      </Badge>
                      <p className="text-sm text-muted-foreground mt-1">
                        {activity.price} KRW
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </MainLayout>
  );
}
