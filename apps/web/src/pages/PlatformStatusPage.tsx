import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../api/client'

function StatusCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <section className="status-card"><p>{label}</p><strong>{value}</strong><small>{detail}</small></section>
}

export function PlatformStatusPage() {
  const health = useQuery({ queryKey: ['platform', 'health'], queryFn: () => apiClient.health(), retry: 1 })
  const version = useQuery({ queryKey: ['platform', 'version'], queryFn: () => apiClient.version(), retry: 1 })
  const failure = health.error ?? version.error

  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">P1 · DEVELOPMENT FOUNDATION</p><h1>Trạng thái nền tảng</h1><p>Kiểm tra API thực, version contract và đường đi tới các module tiếp theo.</p></div>
        <span className={failure ? 'status-badge status-badge--warning' : 'status-badge'}>{failure ? 'API cần kiểm tra' : 'Đang kiểm tra API'}</span>
      </header>
      {failure ? (
        <section aria-live="polite" className="alert alert--error"><h2>Không thể đọc trạng thái API</h2><p>{failure.message}</p><button onClick={() => void Promise.all([health.refetch(), version.refetch()])}>Thử lại</button></section>
      ) : health.isPending || version.isPending ? (
        <section aria-live="polite" className="alert"><h2>Đang kết nối API</h2><p>RT-CONNECT đang lấy health và release metadata; không dùng dữ liệu mô phỏng.</p></section>
      ) : health.data && version.data ? (
        <div className="status-grid">
          <StatusCard label="API health" value={health.data.status.toUpperCase()} detail={`Correlation ID: ${health.data.correlation_id}`} />
          <StatusCard label="API version" value={version.data.version} detail={`${version.data.application} · ${version.data.environment}`} />
          <StatusCard label="Analysis engine" value={version.data.engine_version} detail="Capability sẽ được kích hoạt theo phase" />
          <StatusCard label="Report renderer" value={version.data.renderer_version} detail="Capability sẽ được kích hoạt theo phase" />
        </div>
      ) : (
        <section aria-live="polite" className="alert alert--error"><h2>Phản hồi API chưa đầy đủ</h2><p>Không thể hiển thị trạng thái nền tảng khi thiếu một phần contract.</p><button onClick={() => void Promise.all([health.refetch(), version.refetch()])}>Thử lại</button></section>
      )}
      <section className="provenance-panel"><h2>Nguyên tắc dữ liệu</h2><p>Không có dữ liệu bệnh nhân, token hay mật khẩu trong giao diện. Supabase Auth và Railway PostgreSQL sẽ được cấu hình ở P2; các module chuyên môn chỉ được mở sau khi API, database và kiểm thử tương ứng đã sẵn sàng.</p></section>
    </div>
  )
}
