'use client';

import { MainLayout } from '@/components/layout';
import { InvitationManager } from '@/components/admin';
import { ProtectedRoute } from '@/components/auth';

export default function AdminPage() {
  return (
    <ProtectedRoute requireAdmin>
      <MainLayout>
        <div className="space-y-6">
          {/* Page Header */}
          <div>
            <h1 className="text-3xl font-bold tracking-tight">관리자</h1>
            <p className="text-muted-foreground">
              사용자 및 시스템 설정 관리
            </p>
          </div>

          <div className="grid gap-6">
            <InvitationManager />
          </div>
        </div>
      </MainLayout>
    </ProtectedRoute>
  );
}
