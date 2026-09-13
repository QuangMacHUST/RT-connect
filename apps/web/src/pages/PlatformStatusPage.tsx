import { useQuery } from '@tanstack/react-query'

import { apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { assessPlatformStatus, endpointValue, schemaParityValue, statusErrorMessage } from './platformStatus'

const OPERATIONAL_REFRESH_INTERVAL_MS = 30_000

function StatusCard({ label, value, detail }: { label: string; value: string; detail: string }) {
  return <section className="status-card"><p>{label}</p><strong>{value}</strong><small>{detail}</small></section>
}

export function PlatformStatusPage() {
  const { session } = useAuth()
  const health = useQuery({
    queryKey: ['platform', 'health'],
    queryFn: () => apiClient.health(),
    retry: 1,
    refetchInterval: OPERATIONAL_REFRESH_INTERVAL_MS,
    refetchIntervalInBackground: true
  })
  const readiness = useQuery({
    queryKey: ['platform', 'readiness'],
    queryFn: () => apiClient.ready(),
    retry: 1,
    refetchInterval: OPERATIONAL_REFRESH_INTERVAL_MS,
    refetchIntervalInBackground: true
  })
  const version = useQuery({
    queryKey: ['platform', 'version'],
    queryFn: () => apiClient.version(),
    retry: 1,
    refetchInterval: OPERATIONAL_REFRESH_INTERVAL_MS,
    refetchIntervalInBackground: true
  })
  const queueMetrics = useQuery({
    queryKey: ['platform', 'gamma-queue', session?.access_token],
    queryFn: () => apiClient.gammaQueueMetrics(session!.access_token),
    enabled: Boolean(session?.access_token),
    retry: false,
    refetchInterval: OPERATIONAL_REFRESH_INTERVAL_MS,
    refetchIntervalInBackground: true
  })
  const assessment = assessPlatformStatus({
    health: health.data,
    readiness: readiness.data,
    version: version.data,
    healthError: health.error,
    readinessError: readiness.error,
    versionError: version.error,
    pending: health.isPending || readiness.isPending || version.isPending
  })
  const failures = [
    ['kết nối', health.error],
    ['mức sẵn sàng', readiness.error],
    ['phiên bản', version.error]
  ].filter(([, error]) => Boolean(error)) as Array<[string, unknown]>
  const failure = failures[0]?.[1]
  const platformPending = health.isPending || readiness.isPending || version.isPending
  const platformRefreshing = health.isFetching || readiness.isFetching || version.isFetching
  const lastObservedAt = Math.max(health.dataUpdatedAt, readiness.dataUpdatedAt, version.dataUpdatedAt, queueMetrics.dataUpdatedAt)
  const lastObservedLabel = lastObservedAt > 0
    ? new Date(lastObservedAt).toLocaleString('vi-VN')
    : 'Chưa có kết quả kiểm tra'
  const retryPlatform = () => void Promise.all([health.refetch(), readiness.refetch(), version.refetch()])

  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">TRẠNG THÁI DỊCH VỤ</p><h1>Trạng thái dịch vụ</h1><p>Kiểm tra kết nối, mức sẵn sàng và phiên bản đang phục vụ của RT-CONNECT.</p></div>
        <div className="page-header__actions">
          <span className={`status-badge ${assessment.badgeClass}`} title={assessment.explanation}>{assessment.label}</span>
          <small className="status-observation" aria-live="polite">{platformRefreshing ? 'Đang cập nhật…' : `Lần kiểm tra gần nhất: ${lastObservedLabel}`}</small>
        </div>
      </header>
      {Boolean(failure) && (
        <section aria-live="polite" className="alert alert--error"><h2>Không thể đọc đầy đủ trạng thái dịch vụ</h2><p>{failures.map(([name, error]) => `${name}: ${statusErrorMessage(error)}`).join(' · ')}</p><p>Trạng thái tổng hợp: {assessment.explanation}</p><button onClick={retryPlatform}>Thử lại</button></section>
      )}
      {!failure && platformPending ? (
        <section aria-live="polite" className="alert"><h2>Đang kết nối API</h2><p>RT-CONNECT đang lấy health, readiness và release metadata; không dùng dữ liệu mô phỏng.</p></section>
      ) : !platformPending ? (
        <div className="status-grid">
          <StatusCard label="Kết nối dịch vụ" value={endpointValue(health.data, health.error, health.isPending)} detail={health.data ? 'Dịch vụ đang phản hồi.' : statusErrorMessage(health.error)} />
          <StatusCard label="Mức sẵn sàng" value={endpointValue(readiness.data, readiness.error, readiness.isPending)} detail={readiness.data ? 'Dữ liệu nền tảng đã sẵn sàng.' : statusErrorMessage(readiness.error)} />
          <StatusCard label="Phiên bản đang phục vụ" value={version.data ? 'ĐANG HOẠT ĐỘNG' : endpointValue(undefined, version.error, version.isPending)} detail={version.data ? `Môi trường ${version.data.environment}.` : statusErrorMessage(version.error)} />
          <StatusCard label="Tính nhất quán dữ liệu" value={schemaParityValue(readiness.data, version.data, readiness.error ?? version.error)} detail="Mức sẵn sàng và phiên bản phải phù hợp." />
          <StatusCard label="Bộ tính" value={version.data?.engine_version && version.data.engine_version !== 'not-yet' ? 'ĐÃ BẬT' : 'CHƯA BẬT'} detail="Sẽ hiển thị khi bộ tính được bật." />
          <StatusCard label="Bộ xuất báo cáo" value={version.data?.renderer_version && version.data.renderer_version !== 'not-yet' ? 'ĐÃ BẬT' : 'CHƯA BẬT'} detail="Sẽ hiển thị khi chức năng được bật." />
        </div>
      ) : null}
      {assessment.key === 'NEEDS_REVIEW' && !failure && !platformPending && (
        <section aria-live="polite" className="alert alert--warning"><h2>Release cần được xem xét</h2><p>{assessment.explanation}</p><button onClick={retryPlatform}>Kiểm tra lại</button></section>
      )}
      {session?.access_token && queueMetrics.data && (
        <section className="provenance-panel" aria-live="polite">
          <h2>Tác vụ phân tích</h2>
          <p>{queueMetrics.data.available ? 'Hàng đợi đang hoạt động.' : 'Hàng đợi chưa khả dụng.'} · {queueMetrics.data.configured ? 'Đã cấu hình.' : 'Đang dùng đường dự phòng trong cơ sở dữ liệu.'}</p>
          <p>Đang chờ: {queueMetrics.data.pending_count ?? '—'} · Người xử lý: {queueMetrics.data.consumer_count ?? '—'}</p>
          <p>Đã xếp hàng: {queueMetrics.data.queued_runs} · Đang chạy: {queueMetrics.data.running_runs} · Đang thử lại: {queueMetrics.data.retrying_runs} · Lỗi cuối: {queueMetrics.data.failed_runs}</p>
          {queueMetrics.data.failed_runs > 0 && <p className="status-note--warning">Có tác vụ lỗi trong lịch sử đơn vị. Hãy mở kết quả tương ứng để xem nguyên nhân; bộ đếm này không tự khẳng định dịch vụ đang ngừng hoạt động.</p>}
        </section>
      )}
      {session?.access_token && queueMetrics.isError && (
        <section className="alert alert--error" aria-live="polite"><h2>Không thể đọc hàng đợi phân tích</h2><p>{queueMetrics.error instanceof Error ? queueMetrics.error.message : 'Chưa nhận được dữ liệu hàng đợi.'}</p><button onClick={() => void queueMetrics.refetch()}>Thử lại</button></section>
      )}
      <section className="provenance-panel"><h2>Nguyên tắc dữ liệu</h2><p>Không hiển thị dữ liệu bệnh nhân, mã truy cập hay mật khẩu trong giao diện. Dịch vụ xác thực quản lý phiên đăng nhập, còn cơ sở dữ liệu của Railway lưu dữ liệu ứng dụng.</p></section>
    </div>
  )
}
