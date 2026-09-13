import { useQuery } from '@tanstack/react-query'
import { Navigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'
import { ApiClientError, apiClient } from '../api/client'
import { CompactPage } from '../components/CompactPage'
import { SplitPane } from '../components/SplitPane'

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
    return <div className="page"><section className="alert alert--error" role="alert"><h1>Không thể mở đơn vị</h1><p>{detail}</p><button onClick={() => void Promise.all([bootstrap.refetch(), dashboard.refetch()])}>Thử lại</button></section></div>
  }
  if (bootstrap.isPending || dashboard.isPending || !bootstrap.data || !dashboard.data) return <main className="auth-state" aria-live="polite">Đang tải thông tin đơn vị…</main>
  const data = dashboard.data
  return <CompactPage eyebrow="TRANG CHỦ" title={data.organization.name} description="Tổng quan hoạt động của đơn vị từ dữ liệu thật. Các phần chưa sẵn sàng sẽ được thông báo rõ ràng, không dùng số liệu minh họa." actions={<span className="status-badge">PHIÊN ĐÃ XÁC THỰC</span>}>
    <section className="metric-grid"><MetricCard label="Cơ sở" value={data.site_count} detail="Số cơ sở đang dùng" /><MetricCard label="Máy xạ trị" value={data.machine_count} detail="Số máy đang quản lý" /><MetricCard label="Kết quả QA gần đây" value={data.recent_qa_count} detail="Kết quả đã lưu trong đơn vị" /><MetricCard label="Việc đang xử lý" value={data.active_job_count} detail="Tác vụ đang chờ hoàn tất" /></section>
    <SplitPane><section className="panel"><h2>Cảnh báo</h2>{data.warnings.length ? <ul>{data.warnings.map((warning) => <li key={warning}>{warning}</li>)}</ul> : <p>Chưa có cảnh báo nghiệp vụ.</p>}</section><section className="panel"><h2>Việc cần làm tiếp theo</h2><p>Chọn một mục ở thanh bên để bắt đầu quản lý đơn vị, thực hiện QA máy, mở công cụ sinh học hoặc tra cứu thư viện kiến thức.</p></section></SplitPane>
  </CompactPage>
}
