import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { ApiClientError, apiClient, type GammaConfiguration, type GammaRunResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type JsonRecord = Record<string, unknown>

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function records(value: unknown): JsonRecord[] {
  return Array.isArray(value)
    ? value.filter((item): item is JsonRecord => typeof item === 'object' && item !== null && !Array.isArray(item))
    : []
}

function textValue(value: unknown, fallback = '—'): string {
  if (value === null || value === undefined || value === '') return fallback
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function statusClass(status: string | null | undefined): string {
  if (status === 'FAIL' || status === 'FAILED') return 'status-badge machine-status--fail'
  if (status === 'WARNING' || status === 'RETRYING') return 'status-badge status-badge--warning'
  if (status === 'PASS' || status === 'COMPLETED') return 'status-badge'
  return 'status-badge machine-status--draft'
}

function formatDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString('vi-VN') : '—'
}

function isActiveJob(run: GammaRunResource): boolean {
  return run.status === 'QUEUED' || run.status === 'RUNNING' || run.status === 'RETRYING'
}

const initialConfiguration: GammaConfiguration = {
  dimensionality: '2D',
  dose_difference_percent: 3,
  dose_difference_mode: 'RELATIVE',
  absolute_dose_difference_gy: null,
  distance_to_agreement_mm: 3,
  dose_threshold_percent: 10,
  normalization: 'GLOBAL',
  interpolation: 'GRID',
  pass_rate_threshold_percent: 95,
  histogram_bins: 10
}

export function GammaPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const accessToken = session?.access_token
  const [referenceId, setReferenceId] = useState<string>()
  const [evaluationId, setEvaluationId] = useState<string>()
  const [configuration, setConfiguration] = useState<GammaConfiguration>(initialConfiguration)
  const [selectedRunId, setSelectedRunId] = useState<string>()
  const [comparisonRunId, setComparisonRunId] = useState<string>()
  const [message, setMessage] = useState<string>()

  const bootstrap = useQuery({
    queryKey: ['session', accessToken],
    queryFn: () => apiClient.bootstrap(accessToken!),
    enabled: Boolean(accessToken), retry: false
  })
  const organizationId = bootstrap.data?.organization.id
  const cases = useQuery({
    queryKey: ['qa-case', organizationId, caseId, accessToken],
    queryFn: () => apiClient.qaCases(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId && caseId), retry: false
  })
  const selectedCase = useMemo(
    () => cases.data?.items.find((item) => item.id === caseId),
    [cases.data, caseId]
  )
  const artifacts = useQuery({
    queryKey: ['artifacts', caseId, accessToken],
    queryFn: () => apiClient.artifacts(accessToken!, caseId!),
    enabled: Boolean(accessToken && caseId && selectedCase), retry: false
  })
  const eligibleArtifacts = useMemo(
    () => (artifacts.data?.items ?? []).filter((item) =>
      item.data_status === 'VALID' && (item.artifact_type === 'MEASUREMENT' || item.artifact_type === 'JSON')
    ),
    [artifacts.data]
  )
  const roleReferenceId = eligibleArtifacts.find((item) => item.logical_roles.includes('REFERENCE'))?.id
  const roleEvaluationId = eligibleArtifacts.find((item) => item.logical_roles.includes('EVALUATION'))?.id
  const selectedReferenceId = referenceId && eligibleArtifacts.some((item) => item.id === referenceId)
    ? referenceId
    : roleReferenceId ?? eligibleArtifacts[0]?.id ?? ''
  const selectedEvaluationId = evaluationId && evaluationId !== selectedReferenceId && eligibleArtifacts.some((item) => item.id === evaluationId)
    ? evaluationId
    : (roleEvaluationId && roleEvaluationId !== selectedReferenceId
      ? roleEvaluationId
      : eligibleArtifacts.find((item) => item.id !== selectedReferenceId)?.id ?? '')
  const runs = useQuery({
    queryKey: ['gamma-runs', caseId, accessToken],
    queryFn: () => apiClient.gammaRuns(accessToken!, caseId!),
    enabled: Boolean(accessToken && caseId && selectedCase),
    refetchInterval: 2500,
    retry: false
  })
  const activeRun = useMemo(
    () => runs.data?.items.find((item) => item.id === selectedRunId) ?? runs.data?.items[0],
    [runs.data, selectedRunId]
  )
  const comparison = useQuery({
    queryKey: ['gamma-compare', activeRun?.id, comparisonRunId, accessToken],
    queryFn: () => apiClient.compareGammaRuns(accessToken!, activeRun!.id, comparisonRunId!),
    enabled: Boolean(accessToken && activeRun && comparisonRunId && activeRun.id !== comparisonRunId),
    retry: false
  })
  const createMutation = useMutation({
    mutationFn: () => apiClient.createGammaRun(accessToken!, caseId!, {
      reference_artifact_id: selectedReferenceId,
      evaluation_artifact_id: selectedEvaluationId,
      idempotency_key: `gamma-${crypto.randomUUID()}`,
      configuration
    }),
    onSuccess: (run) => {
      setSelectedRunId(run.id)
      setMessage('Đã đưa Gamma job vào hàng đợi. Worker sẽ cập nhật tiến độ sau khi nhận job.')
      void queryClient.invalidateQueries({ queryKey: ['gamma-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const retryMutation = useMutation({
    mutationFn: (runId: string) => apiClient.retryGammaRun(accessToken!, runId),
    onSuccess: (run) => {
      setSelectedRunId(run.id)
      setMessage('Đã đưa lại Gamma job vào hàng đợi.')
      void queryClient.invalidateQueries({ queryKey: ['gamma-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || cases.isPending) return <main className="auth-state">Đang tải Gamma Workspace…</main>
  const initialFailure = bootstrap.error ?? cases.error
  if (initialFailure || !organizationId || !caseId) {
    return <div className="page"><section className="alert alert--error"><h1>Không thể mở Gamma Workspace</h1><p>{errorMessage(initialFailure)}</p><Link className="button-link" to="/app/qa">Quay lại QA Archive</Link></section></div>
  }
  if (!selectedCase) {
    return <div className="page"><section className="alert alert--error"><h1>Không tìm thấy QA case</h1><p>Case này không thuộc organization hiện tại hoặc đã bị lưu trữ.</p><Link className="button-link" to="/app/qa">Quay lại QA Archive</Link></section></div>
  }

  const resultMetrics = typeof activeRun?.result_snapshot.metrics === 'object' && activeRun.result_snapshot.metrics !== null
    ? activeRun.result_snapshot.metrics as JsonRecord
    : undefined
  const percentiles = resultMetrics && typeof resultMetrics.percentiles === 'object' && resultMetrics.percentiles !== null
    ? resultMetrics.percentiles as JsonRecord
    : undefined
  const gammaMap = records(activeRun?.result_snapshot.gamma_map)
  const busy = createMutation.isPending || retryMutation.isPending

  const updateNumber = (key: keyof GammaConfiguration, value: string) => {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) setConfiguration((current) => ({ ...current, [key]: parsed }))
  }

  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">P8 · MOD-06</p><h1>Phân tích PSQA Gamma Workspace</h1><p>{selectedCase.title} · chọn hai input đã VALID, cấu hình Gamma 2D và theo dõi job/result có provenance.</p></div>
        <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">QA Archive</Link><span className="status-badge">API THẬT</span></div>
      </header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">INPUT PREFLIGHT</p><h2>Reference / Evaluation</h2></div><strong>{eligibleArtifacts.length}</strong></div>
        {artifacts.isPending ? <p>Đang tải artifact…</p> : artifacts.error ? <div className="alert alert--error"><p>{errorMessage(artifacts.error)}</p><Link className="button-link" to="/app/qa">Mở QA Archive để kiểm tra artifact</Link></div> : eligibleArtifacts.length < 2 ? <div className="empty-state"><p>Cần ít nhất hai artifact measurement/JSON có trạng thái VALID. Hãy upload và Validate ở QA Archive trước khi đưa vào Gamma.</p><Link className="button-link" to="/app/qa">Đi tới QA Archive</Link></div> : <>
          <div className="gamma-input-grid">
            <label>Reference<select value={selectedReferenceId} onChange={(event) => setReferenceId(event.target.value)}>{eligibleArtifacts.map((artifact) => <option key={artifact.id} value={artifact.id}>{artifact.original_filename} · {artifact.sha256.slice(0, 12)}…</option>)}</select></label>
            <label>Evaluation<select value={selectedEvaluationId} onChange={(event) => setEvaluationId(event.target.value)}>{eligibleArtifacts.filter((item) => item.id !== selectedReferenceId).map((artifact) => <option key={artifact.id} value={artifact.id}>{artifact.original_filename} · {artifact.sha256.slice(0, 12)}…</option>)}</select></label>
          </div>
          <div className="gamma-input-summary"><span>Reference: <strong>{eligibleArtifacts.find((item) => item.id === selectedReferenceId)?.original_filename ?? '—'}</strong></span><span>Evaluation: <strong>{eligibleArtifacts.find((item) => item.id === selectedEvaluationId)?.original_filename ?? '—'}</strong></span><span className="status-badge">PREFLIGHT VALID</span></div>
        </>}
      </section>

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">GAMMA CONFIGURATION</p><h2>Tham số tính toán</h2></div><span className="status-badge">2D · P8</span></div>
        <div className="gamma-config-grid">
          <label>Dose difference (%)<input type="number" min="0.01" step="0.1" value={configuration.dose_difference_percent} onChange={(event) => updateNumber('dose_difference_percent', event.target.value)} /></label>
          <label>DTA (mm)<input type="number" min="0.01" step="0.1" value={configuration.distance_to_agreement_mm} onChange={(event) => updateNumber('distance_to_agreement_mm', event.target.value)} /></label>
          <label>Dose threshold (%)<input type="number" min="0" max="100" step="1" value={configuration.dose_threshold_percent} onChange={(event) => updateNumber('dose_threshold_percent', event.target.value)} /></label>
          <label>Pass rate target (%)<input type="number" min="0" max="100" step="1" value={configuration.pass_rate_threshold_percent} onChange={(event) => updateNumber('pass_rate_threshold_percent', event.target.value)} /></label>
          <label>Dose difference mode<select value={configuration.dose_difference_mode} onChange={(event) => setConfiguration((current) => ({ ...current, dose_difference_mode: event.target.value as GammaConfiguration['dose_difference_mode'] }))}><option value="RELATIVE">Relative</option><option value="ABSOLUTE">Absolute</option></select></label>
          <label>Normalization<select value={configuration.normalization} onChange={(event) => setConfiguration((current) => ({ ...current, normalization: event.target.value as GammaConfiguration['normalization'] }))}><option value="GLOBAL">Global</option><option value="LOCAL">Local</option></select></label>
          <label>Interpolation<select value={configuration.interpolation} onChange={(event) => setConfiguration((current) => ({ ...current, interpolation: event.target.value as GammaConfiguration['interpolation'] }))}><option value="GRID">Grid node</option><option value="BILINEAR">Bilinear</option></select></label>
          {configuration.dose_difference_mode === 'ABSOLUTE' && <label>Absolute dose difference (Gy)<input type="number" min="0.001" step="0.01" value={configuration.absolute_dose_difference_gy ?? ''} onChange={(event) => updateNumber('absolute_dose_difference_gy', event.target.value)} /></label>}
        </div>
        <p className="form-hint">Cấu hình sẽ được snapshot cùng job; đổi cấu hình không làm thay đổi run cũ.</p>
        <button disabled={busy || eligibleArtifacts.length < 2 || selectedReferenceId === selectedEvaluationId} onClick={() => createMutation.mutate()}>Đưa vào hàng đợi Gamma</button>
      </section>

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">JOB / RESULT</p><h2>Tiến độ và kết quả</h2></div><strong>{runs.data?.total ?? '—'}</strong></div>
        {runs.isPending ? <p>Đang tải lịch sử Gamma…</p> : runs.error ? <div className="alert alert--error"><p>{errorMessage(runs.error)}</p><button onClick={() => void runs.refetch()}>Thử lại</button></div> : !activeRun ? <p className="empty-state">Chưa có Gamma run. Chọn input và đưa job vào hàng đợi.</p> : <>
          <div className="gamma-run-meta"><span>Run <code>{activeRun.id}</code></span><span>Trạng thái <strong className={statusClass(activeRun.status)}>{activeRun.status}</strong></span><span>Tiến độ {activeRun.progress_percent}%</span><span>Attempt {activeRun.attempt_count}</span><span>Engine {activeRun.engine_version}</span></div>
          {isActiveJob(activeRun) && <div className="gamma-progress"><div style={{ width: `${activeRun.progress_percent}%` }} /><p>Job đang được worker xử lý; trang sẽ tự đồng bộ sau mỗi 2,5 giây.</p></div>}
          {activeRun.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Gamma không hoàn tất</h3><ul>{activeRun.error_snapshot.map((item, index) => <li key={`${String(item.code)}-${index}`}><strong>{textValue(item.code)}</strong>: {textValue(item.message, JSON.stringify(item))}</li>)}</ul><button disabled={busy} onClick={() => retryMutation.mutate(activeRun.id)}>Retry job</button></div>}
          {activeRun.result_snapshot.overall_status && <div className="gamma-result-banner"><span className={statusClass(String(activeRun.result_snapshot.overall_status))}>{String(activeRun.result_snapshot.overall_status)}</span><strong>{textValue(resultMetrics?.pass_rate_percent)}%</strong><span>pass rate · target {textValue(configuration.pass_rate_threshold_percent)}%</span></div>}
          {resultMetrics && <div className="metric-grid gamma-metrics"><article><span>Evaluated points</span><strong>{textValue(resultMetrics.evaluated_points)}</strong></article><article><span>Passing points</span><strong>{textValue(resultMetrics.passing_points)}</strong></article><article><span>Excluded points</span><strong>{textValue(resultMetrics.excluded_points)}</strong></article><article><span>Gamma P95</span><strong>{textValue(percentiles?.p95)}</strong></article></div>}
          {activeRun.warning_snapshot.length > 0 && <div className="alert alert--warning"><strong>Cảnh báo:</strong><ul>{activeRun.warning_snapshot.map((item, index) => <li key={`${String(item.code)}-${index}`}>{textValue(item.message, JSON.stringify(item))}</li>)}</ul></div>}
          {gammaMap.length > 0 && <div className="table-wrap"><table className="gamma-map-table"><caption>Gamma map · hiển thị tối đa 100 điểm đầu trong snapshot</caption><thead><tr><th>Row</th><th>Column</th><th>Reference dose</th><th>Gamma</th><th>Status</th></tr></thead><tbody>{gammaMap.slice(0, 100).map((item, index) => <tr key={`${String(item.row)}-${String(item.column)}-${index}`}><td>{textValue(item.row)}</td><td>{textValue(item.column)}</td><td>{textValue(item.reference_dose_gy)} Gy</td><td>{textValue(item.gamma)}</td><td><span className={statusClass(String(item.status))}>{textValue(item.status)}</span></td></tr>)}</tbody></table></div>}
        </>}
      </section>

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">RUN HISTORY</p><h2>Lịch sử và so sánh</h2></div></div>
        {runs.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Run</th><th>Status</th><th>Result</th><th>Queued</th><th /></tr></thead><tbody>{runs.data.items.map((run) => <tr key={run.id}><td><button className={run.id === activeRun?.id ? 'history-button history-button--selected' : 'history-button'} onClick={() => setSelectedRunId(run.id)}><code>{run.id.slice(0, 8)}…</code></button></td><td><span className={statusClass(run.status)}>{run.status}</span></td><td>{textValue(run.result_snapshot.overall_status)}</td><td>{formatDate(run.queued_at)}</td><td>{run.id !== activeRun?.id && <button className="button-secondary" onClick={() => setComparisonRunId(run.id)}>So sánh</button>}</td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có lịch sử Gamma.</p>}
        {runs.data && runs.data.items.length > 1 && activeRun && <div className="compare-controls"><label>So sánh run đang chọn với<select value={comparisonRunId ?? ''} onChange={(event) => setComparisonRunId(event.target.value || undefined)}><option value="">Chọn run khác</option>{runs.data.items.filter((run) => run.id !== activeRun.id).map((run) => <option key={run.id} value={run.id}>{run.id.slice(0, 8)}… · {run.status}</option>)}</select></label>{comparison.isPending && comparisonRunId && <p>Đang tải so sánh…</p>}{comparison.error && <p className="error-text">{errorMessage(comparison.error)}</p>}{comparison.data && <div className="table-wrap"><table><thead><tr><th>Snapshot key</th><th>Run hiện tại</th><th>Run đối chiếu</th></tr></thead><tbody>{comparison.data.items.map((item) => <tr key={item.key}><td>{item.key}</td><td>{textValue(item.left)}</td><td>{textValue(item.right)}</td></tr>)}</tbody></table></div>}</div>}
      </section>
    </div>
  )
}
