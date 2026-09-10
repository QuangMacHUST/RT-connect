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
    ['health', health.error],
    ['ready', readiness.error],
    ['version', version.error]
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
        <div><p className="eyebrow">P1 · DEVELOPMENT FOUNDATION</p><h1>Trạng thái nền tảng</h1><p>Kiểm tra API thực, schema readiness, version contract và đường đi tới các module tiếp theo.</p></div>
        <div className="page-header__actions">
          <span className={`status-badge ${assessment.badgeClass}`} title={assessment.explanation}>{assessment.label}</span>
          <small className="status-observation" aria-live="polite">{platformRefreshing ? 'Đang cập nhật…' : `Lần kiểm tra gần nhất: ${lastObservedLabel}`}</small>
        </div>
      </header>
      {Boolean(failure) && (
        <section aria-live="polite" className="alert alert--error"><h2>Không thể đọc đầy đủ trạng thái API</h2><p>{failures.map(([name, error]) => `${name}: ${statusErrorMessage(error)}`).join(' · ')}</p><p>Trạng thái tổng hợp: {assessment.explanation}</p><button onClick={retryPlatform}>Thử lại</button></section>
      )}
      {!failure && platformPending ? (
        <section aria-live="polite" className="alert"><h2>Đang kết nối API</h2><p>RT-CONNECT đang lấy health, readiness và release metadata; không dùng dữ liệu mô phỏng.</p></section>
      ) : !platformPending ? (
        <div className="status-grid">
          <StatusCard label="API health" value={endpointValue(health.data, health.error, health.isPending)} detail={health.data ? `Correlation ID: ${health.data.correlation_id}` : statusErrorMessage(health.error)} />
          <StatusCard label="Schema readiness" value={endpointValue(readiness.data, readiness.error, readiness.isPending)} detail={readiness.data ? `Schema: ${readiness.data.schema_revision ?? '—'} · Correlation ID: ${readiness.data.correlation_id}` : statusErrorMessage(readiness.error)} />
          <StatusCard label="API version" value={version.data?.version ?? endpointValue(undefined, version.error, version.isPending)} detail={version.data ? `${version.data.application} · ${version.data.environment}` : statusErrorMessage(version.error)} />
          <StatusCard label="Schema parity" value={schemaParityValue(readiness.data, version.data, readiness.error ?? version.error)} detail={`${readiness.data?.schema_revision ?? '—'} ↔ ${version.data?.schema_revision ?? '—'}`} />
          <StatusCard label="Analysis engine" value={version.data?.engine_version ?? '—'} detail="Capability sẽ được kích hoạt theo phase" />
          <StatusCard label="Report renderer" value={version.data?.renderer_version ?? '—'} detail="Capability sẽ được kích hoạt theo phase" />
        </div>
      ) : null}
      {assessment.key === 'NEEDS_REVIEW' && !failure && !platformPending && (
        <section aria-live="polite" className="alert alert--warning"><h2>Release cần được xem xét</h2><p>{assessment.explanation}</p><button onClick={retryPlatform}>Kiểm tra lại</button></section>
      )}
      {session?.access_token && queueMetrics.data && (
        <section className="provenance-panel" aria-live="polite">
          <h2>Gamma queue &amp; run counters</h2>
          <p>{queueMetrics.data.backend} · {queueMetrics.data.available ? 'available' : 'unavailable'} · {queueMetrics.data.configured ? 'configured' : 'database fallback'}</p>
          <p>Stream: {queueMetrics.data.stream_length ?? '—'} · Pending: {queueMetrics.data.pending_count ?? '—'} · Consumers: {queueMetrics.data.consumer_count ?? '—'}</p>
          <p>Organization runs — queued: {queueMetrics.data.queued_runs}, running: {queueMetrics.data.running_runs}, retrying: {queueMetrics.data.retrying_runs}, failed (terminal history): {queueMetrics.data.failed_runs}</p>
          {queueMetrics.data.failed_runs > 0 && <p className="status-note--warning">Có run FAILED trong lịch sử organization. Hãy mở run và đọc error snapshot để triage; bộ đếm lịch sử này không tự chứng minh worker đang outage.</p>}
        </section>
      )}
      {session?.access_token && queueMetrics.isError && (
        <section className="alert alert--error" aria-live="polite"><h2>Không thể đọc Gamma queue</h2><p>{queueMetrics.error instanceof Error ? queueMetrics.error.message : 'API queue metrics chưa trả về dữ liệu.'}</p><button onClick={() => void queueMetrics.refetch()}>Thử lại</button></section>
      )}
      <section className="provenance-panel"><h2>Nguyên tắc dữ liệu</h2><p>Không có dữ liệu bệnh nhân, token hay mật khẩu trong giao diện. Supabase Auth quản lý identity/session, còn Railway PostgreSQL lưu dữ liệu ứng dụng; các module chuyên môn chỉ được mở sau khi API, database và kiểm thử tương ứng đã sẵn sàng.</p></section>
    </div>
  )
}
