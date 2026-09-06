import { useQuery } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'
import { ApiClientError, apiClient } from '../api/client'

function MetricCard({ label, value, detail }: { label: string; value: number; detail: string }) {
  return <section className="metric-card"><p>{label}</p><strong>{value}</strong><small>{detail}</small></section>
}

export function HomeDashboardPage() {
  const { session } = useAuth()
  const bootstrap = useQuery({ queryKey: ['session', session?.access_token], queryFn: () => apiClient.bootstrap(session!.access_token), enabled: Boolean(session), retry: false })
  const dashboard = useQuery({
    queryKey: ['dashboard', bootstrap.data?.organization.id, session?.access_token],
    queryFn: () => apiClient.dashboard(session!.access_token, bootstrap.data!.organization.id),
    enabled: Boolean(session && bootstrap.data),
    retry: false
  })
  const failure = bootstrap.error ?? dashboard.error
  if (failure) {
    if (failure instanceof ApiClientError && failure.code === 'ORGANIZATION_MEMBERSHIP_REQUIRED') {
      return <Navigate replace to="/auth/session-error" />
    }
    const detail = failure.message
    return <div className="page"><section className="alert alert--error" role="alert"><h1>Không thể mở organization</h1><p>{detail}</p><button onClick={() => void Promise.all([bootstrap.refetch(), dashboard.refetch()])}>Thử lại</button></section></div>
  }
  if (bootstrap.isPending || dashboard.isPending || !bootstrap.data || !dashboard.data) return <main className="auth-state" aria-live="polite">Đang tải organization và dashboard…</main>
  const data = dashboard.data
  return <div className="page dashboard-page">
    <header className="page-header"><div><p className="eyebrow">ORGANIZATION DASHBOARD</p><h1>{data.organization.name}</h1><p>Dashboard đọc dữ liệu thật từ RT-CONNECT API. Các module QA chưa triển khai sẽ hiển thị trạng thái trống, không dùng số liệu mô phỏng.</p></div><span className="status-badge">PHIÊN ĐÃ XÁC THỰC</span></header>
    <section className="metric-grid"><MetricCard label="Cơ sở" value={data.site_count} detail="Site hiện có trong organization" /><MetricCard label="Máy xạ trị" value={data.machine_count} detail="Machine đang được quản lý" /><MetricCard label="QA gần đây" value={data.recent_qa_count} detail="Sẽ có từ phase QA Archive" /><MetricCard label="Job đang chạy" value={data.active_job_count} detail="Sẽ có từ phase analysis" /></section>
    <section className="dashboard-grid"><section className="panel"><h2>Cảnh báo</h2>{data.warnings.length ? <ul>{data.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p>Chưa có cảnh báo nghiệp vụ.</p>}</section><section className="panel"><h2>Hành động tiếp theo</h2><p>Thiết lập Site và Machine tại P4 trước khi tạo QA case. Các hành động chỉ mở khi module có API và nghiệm thu tương ứng.</p></section></section>
  </div>
}
