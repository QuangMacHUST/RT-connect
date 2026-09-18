import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { ApiClientError, apiClient, type GammaConfiguration, type GammaRunResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { artifactDisplayName } from './gammaArtifactLabels'
import { validateGammaInputGeometry } from './gammaInputValidation'
import { isGammaWorkflowReady, validateGammaConfiguration } from './gammaValidation'

type JsonRecord = Record<string, unknown>

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    const messages: Record<string, string> = {
      QA_CASE_NOT_FOUND: 'Không tìm thấy bài kiểm tra trong đơn vị hiện tại.',
      QA_CASE_ARCHIVED: 'Bài kiểm tra đã được lưu trữ nên không thể phân tích.',
      GAMMA_ARTIFACT_SCOPE_MISMATCH: 'Tệp đã chọn không thuộc bài kiểm tra này.',
      GAMMA_ARTIFACT_TYPE_INVALID: 'Tệp đã chọn không phải dữ liệu liều hoặc dữ liệu đo được hỗ trợ.',
      GAMMA_INPUT_NOT_VALIDATED: 'Tệp cần được kiểm tra hợp lệ trước khi phân tích.',
      GAMMA_GRID_METADATA_MISSING: 'Tệp chưa có đủ thông tin hình học của lưới liều.',
      RTDOSE_REQUIRED: 'Bài PSQA cần tệp RTDOSE làm liều tham chiếu.',
      COMPARISON_REQUIRED: 'Bài PSQA cần thêm tệp đo hoặc RTDOSE để đối chiếu.',
      PYLINAC_GAMMA_3D_UNAVAILABLE: 'Pylinac hiện chỉ hỗ trợ phân tích Gamma một chiều và hai chiều. Kết quả ba chiều cũ chỉ được xem lại.',
      GAMMA_PYLINAC_ABSOLUTE_UNSUPPORTED: 'Phân tích mới chỉ dùng chênh lệch liều theo phần trăm.',
      GAMMA_PYLINAC_INTERPOLATION_UNSUPPORTED: 'Phân tích mới chỉ dùng dữ liệu trên lưới đã kiểm tra.',
      GAMMA_DTA_GRID_INCOMPATIBLE: 'DTA không khớp với kích thước lưới của hai tệp đã chọn.',
      GAMMA_DIMENSIONALITY_MISMATCH: 'Kiểu dữ liệu đã chọn không phù hợp với phép phân tích một chiều hoặc hai chiều.',
      GAMMA_GRID_INCOMPATIBLE: 'Hai lưới liều không có cùng kích thước để so sánh an toàn.',
      GAMMA_GRID_INVALID: 'Hình học của tệp chưa hợp lệ để phân tích Gamma.',
      GAMMA_PYLINAC_GRID_NON_SQUARE: 'Dữ liệu hai chiều cần có điểm ảnh vuông để tính đúng khoảng cách.',
      GAMMA_INPUT_INCOMPATIBLE: 'Hai tệp không có cùng hệ tọa độ hoặc hình học để so sánh an toàn.',
      GAMMA_COORDINATE_FRAME_INVALID: 'Tệp thiếu thông tin hệ tọa độ đã được kiểm tra.',
      GAMMA_RESOURCE_LIMIT: 'Dữ liệu đã chọn quá lớn so với giới hạn xử lý hiện tại.',
      GAMMA_QUEUE_UNAVAILABLE: 'Dịch vụ xử lý đang tạm thời không sẵn sàng. Hãy thử lại sau.',
      GAMMA_IDEMPOTENCY_CONFLICT: 'Lượt phân tích này đã tồn tại với dữ liệu khác. Hãy tải lại trang.',
      GAMMA_RETRY_NOT_ALLOWED: 'Chỉ có thể phân tích lại một lượt đã xảy ra lỗi.',
      GAMMA_CANCEL_NOT_ALLOWED: 'Chỉ có thể hủy bài phân tích khi bài vẫn đang chờ bắt đầu.',
      GAMMA_PYLINAC_EXECUTION_FAILED: 'Pylinac không thể phân tích hai dữ liệu đã chọn.',
      GAMMA_CONFIGURATION_INVALID: 'Một hoặc nhiều tham số phân tích chưa hợp lệ.'
    }
    return messages[error.code] ?? 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối dịch vụ.'
  }
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối dịch vụ.'
}

function records(value: unknown): JsonRecord[] {
  return Array.isArray(value)
    ? value.filter((item): item is JsonRecord => typeof item === 'object' && item !== null && !Array.isArray(item))
    : []
}

function scalarValue(value: unknown, fallback = '—'): string {
  if (value === null || value === undefined || value === '') return fallback
  if (typeof value === 'string' || typeof value === 'number') return String(value)
  if (typeof value === 'boolean') return value ? 'Có' : 'Không'
  return fallback
}

function numberValue(value: unknown, fallback = '—'): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return fallback
  return value.toLocaleString('vi-VN', { maximumFractionDigits: 3 })
}

function statusLabel(status: unknown): string {
  const labels: Record<string, string> = {
    QUEUED: 'Đang chờ',
    RUNNING: 'Đang phân tích',
    RETRYING: 'Đang thử lại',
    FAILED: 'Lỗi',
    COMPLETED: 'Đã hoàn tất',
    CANCELLED: 'Đã hủy',
    PASS: 'Đạt',
    FAIL: 'Không đạt',
    INVALID: 'Không hợp lệ',
    WARNING: 'Cảnh báo',
    EXCLUDED: 'Đã loại'
  }
  return typeof status === 'string' ? labels[status] ?? 'Chưa xác định' : 'Chưa xác định'
}

function statusClass(status: string | null | undefined): string {
  if (status === 'FAIL' || status === 'FAILED' || status === 'INVALID') return 'status-badge machine-status--fail'
  if (status === 'WARNING' || status === 'RETRYING' || status === 'CANCELLED') return 'status-badge status-badge--warning'
  if (status === 'PASS' || status === 'COMPLETED') return 'status-badge'
  return 'status-badge machine-status--draft'
}

function dimensionalityLabel(value: unknown): string {
  if (value === '1D') return 'Một chiều'
  if (value === '2D') return 'Hai chiều'
  if (value === '3D') return 'Ba chiều'
  return '—'
}

function gammaClassLabel(value: unknown): string {
  if (value === 'gamma_1d') return 'Gamma một chiều'
  if (value === 'gamma_2d') return 'Gamma hai chiều'
  return scalarValue(value)
}

function coverageLabel(value: unknown): string {
  if (value === 'FULL_ROI') return 'Toàn bộ vùng so sánh'
  if (value === 'OVERLAP_ONLY') return 'Chỉ vùng chồng lấp'
  return scalarValue(value)
}

function formatDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString('vi-VN') : '—'
}

function isActiveJob(run: GammaRunResource): boolean {
  return run.status === 'QUEUED' || run.status === 'RUNNING' || run.status === 'RETRYING'
}

function comparisonLabel(key: string): string | undefined {
  const labels: Record<string, string> = {
    engine: 'Bộ phân tích',
    engine_class: 'Phương pháp',
    dimensionality: 'Kiểu dữ liệu',
    overall_status: 'Kết luận'
  }
  return labels[key]
}

function comparisonValue(key: string, value: unknown): string {
  if (key === 'engine') return value === 'pylinac' ? 'Pylinac' : scalarValue(value)
  if (key === 'engine_class') return gammaClassLabel(value)
  if (key === 'dimensionality') return dimensionalityLabel(value)
  if (key === 'overall_status') return statusLabel(value)
  return scalarValue(value)
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
  coverage_policy: 'FULL_ROI',
  max_gamma: 2,
  pass_rate_threshold_percent: 95,
  histogram_bins: 10,
  resolution_factor: 3
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
      item.data_status === 'VALID' && (
        item.artifact_type === 'MEASUREMENT' ||
        (item.artifact_type === 'DICOM' && item.modality === 'RTDOSE')
      )
    ),
    [artifacts.data]
  )
  const preferredReferenceId = configuration.dimensionality === '1D'
    ? eligibleArtifacts.find((item) => item.artifact_type === 'MEASUREMENT' && item.logical_roles.includes('REFERENCE'))?.id
      ?? eligibleArtifacts.find((item) => item.artifact_type === 'MEASUREMENT')?.id
    : eligibleArtifacts.find((item) =>
      item.artifact_type === 'DICOM' && item.modality === 'RTDOSE' && item.logical_roles.includes('REFERENCE')
    )?.id ?? eligibleArtifacts.find((item) => item.artifact_type === 'DICOM' && item.modality === 'RTDOSE')?.id
  const preferredEvaluationId = configuration.dimensionality === '1D'
    ? eligibleArtifacts.find((item) => item.artifact_type === 'MEASUREMENT' && item.logical_roles.includes('EVALUATION'))?.id
      ?? eligibleArtifacts.find((item) => item.artifact_type === 'MEASUREMENT' && item.id !== preferredReferenceId)?.id
    : eligibleArtifacts.find((item) =>
      item.artifact_type === 'MEASUREMENT' && item.logical_roles.includes('EVALUATION')
    )?.id ?? eligibleArtifacts.find((item) => item.artifact_type === 'MEASUREMENT')?.id
  const selectedReferenceId = referenceId && eligibleArtifacts.some((item) => item.id === referenceId)
    ? referenceId
    : preferredReferenceId ?? eligibleArtifacts[0]?.id ?? ''
  const selectedEvaluationId = (evaluationId && evaluationId !== selectedReferenceId && eligibleArtifacts.some((item) => item.id === evaluationId)
    ? evaluationId
    : (preferredEvaluationId && preferredEvaluationId !== selectedReferenceId
      ? preferredEvaluationId
      : eligibleArtifacts.find((item) => item.id !== selectedReferenceId)?.id ?? '')) ?? ''
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
      workflow_profile: 'PSQA_GAMMA',
      configuration
    }),
    onSuccess: (run) => {
      setSelectedRunId(run.id)
      setMessage('Đã đưa bài phân tích vào hàng chờ. Kết quả sẽ tự cập nhật khi hoàn tất.')
      void queryClient.invalidateQueries({ queryKey: ['gamma-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const retryMutation = useMutation({
    mutationFn: (runId: string) => apiClient.retryGammaRun(accessToken!, runId),
    onSuccess: (run) => {
      setSelectedRunId(run.id)
      setMessage('Đã đưa bài phân tích lỗi vào hàng chờ để thực hiện lại.')
      void queryClient.invalidateQueries({ queryKey: ['gamma-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cancelMutation = useMutation({
    mutationFn: (runId: string) => apiClient.cancelGammaRun(accessToken!, runId),
    onSuccess: (run) => {
      setSelectedRunId(run.id)
      setMessage('Đã hủy bài phân tích đang chờ. Không có phép tính nào được thực hiện.')
      void queryClient.invalidateQueries({ queryKey: ['gamma-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || cases.isPending) return <main className="auth-state">Đang tải trang phân tích…</main>
  const initialFailure = bootstrap.error ?? cases.error
  if (initialFailure || !organizationId || !caseId) {
    return <div className="page"><section className="alert alert--error"><h1>Không thể mở trang phân tích</h1><p>{errorMessage(initialFailure)}</p><Link className="button-link" to="/app/qa">Quay lại kiểm tra chất lượng máy</Link></section></div>
  }
  if (!selectedCase) {
    return <div className="page"><section className="alert alert--error"><h1>Không tìm thấy bài kiểm tra</h1><p>Bài kiểm tra này không thuộc đơn vị hiện tại hoặc đã được lưu trữ.</p><Link className="button-link" to="/app/qa">Quay lại kiểm tra chất lượng máy</Link></section></div>
  }

  const resultMetrics = typeof activeRun?.result_snapshot.metrics === 'object' && activeRun.result_snapshot.metrics !== null
    ? activeRun.result_snapshot.metrics as JsonRecord
    : undefined
  const percentiles = resultMetrics && typeof resultMetrics.percentiles === 'object' && resultMetrics.percentiles !== null
    ? resultMetrics.percentiles as JsonRecord
    : undefined
  const histogram = resultMetrics && typeof resultMetrics.histogram === 'object' && resultMetrics.histogram !== null
    ? resultMetrics.histogram as JsonRecord
    : undefined
  const histogramCounts = histogram && Array.isArray(histogram.counts)
    ? histogram.counts.filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    : []
  const histogramEdges = histogram && Array.isArray(histogram.edges)
    ? histogram.edges.filter((value): value is number => typeof value === 'number' && Number.isFinite(value))
    : []
  const histogramPeak = Math.max(...histogramCounts, 0)
  const gammaMap = records(activeRun?.result_snapshot.gamma_map)
  const snapshotConfiguration = activeRun?.config_snapshot ?? {}
  const snapshotDimensionality = typeof snapshotConfiguration.dimensionality === 'string'
    ? snapshotConfiguration.dimensionality
    : undefined
  const snapshotPassTarget = typeof snapshotConfiguration.pass_rate_threshold_percent === 'number'
    ? snapshotConfiguration.pass_rate_threshold_percent
    : undefined
  const snapshotCoveragePolicy = typeof snapshotConfiguration.coverage_policy === 'string'
    ? snapshotConfiguration.coverage_policy
    : undefined
  const snapshotMaxGamma = typeof snapshotConfiguration.max_gamma === 'number'
    ? snapshotConfiguration.max_gamma
    : undefined
  const comparisonRows = comparison.data?.items.filter((item) => comparisonLabel(item.key)) ?? []
  const busy = createMutation.isPending || retryMutation.isPending || cancelMutation.isPending
  const configurationErrors = validateGammaConfiguration(configuration)
  const selectedReference = eligibleArtifacts.find((item) => item.id === selectedReferenceId)
  const selectedEvaluation = eligibleArtifacts.find((item) => item.id === selectedEvaluationId)
  const inputGeometryErrors = validateGammaInputGeometry(configuration, selectedReference, selectedEvaluation)
  const blockingErrors = [...configurationErrors, ...inputGeometryErrors]
  const profileReady = isGammaWorkflowReady(configuration, selectedReference, selectedEvaluation)

  const updateNumber = (key: keyof GammaConfiguration, value: string) => {
    const parsed = Number(value)
    if (Number.isFinite(parsed)) setConfiguration((current) => ({ ...current, [key]: parsed }))
  }

  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">P8 · PHÂN TÍCH PSQA</p><h1>Phân tích độ lệch liều</h1><p>{selectedCase.title} · chọn dữ liệu đã kiểm tra, nhập tiêu chí và theo dõi kết quả bằng Pylinac.</p></div>
        <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kiểm tra chất lượng máy</Link><span className="status-badge">KẾT NỐI DỊCH VỤ</span></div>
      </header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">DỮ LIỆU ĐẦU VÀO</p><h2>Liều tham chiếu và liều đối chiếu</h2></div><strong>{eligibleArtifacts.length}</strong></div>
        {artifacts.isPending ? <p>Đang tải danh sách tệp…</p> : artifacts.error ? <div className="alert alert--error"><p>{errorMessage(artifacts.error)}</p><Link className="button-link" to="/app/qa">Mở phần kiểm tra chất lượng máy</Link></div> : eligibleArtifacts.length < 2 ? <div className="empty-state"><p>Cần ít nhất hai tệp liều hoặc dữ liệu đo đã được kiểm tra hợp lệ. Hãy tải tệp lên và kiểm tra ở phần kiểm tra chất lượng máy trước.</p><Link className="button-link" to="/app/qa">Đi tới kiểm tra chất lượng máy</Link></div> : <>
          <div className="gamma-input-grid">
            <label>Liều tham chiếu<select value={selectedReferenceId} onChange={(event) => setReferenceId(event.target.value)}>{eligibleArtifacts.map((artifact) => <option key={artifact.id} value={artifact.id}>{artifactDisplayName(artifact, eligibleArtifacts)}</option>)}</select></label>
            <label>Liều đối chiếu<select value={selectedEvaluationId} onChange={(event) => setEvaluationId(event.target.value)}>{eligibleArtifacts.filter((item) => item.id !== selectedReferenceId).map((artifact) => <option key={artifact.id} value={artifact.id}>{artifactDisplayName(artifact, eligibleArtifacts)}</option>)}</select></label>
          </div>
          <div className="gamma-input-summary"><span>Tham chiếu: <strong>{selectedReference ? artifactDisplayName(selectedReference, eligibleArtifacts) : '—'}</strong></span><span>Đối chiếu: <strong>{selectedEvaluation ? artifactDisplayName(selectedEvaluation, eligibleArtifacts) : '—'}</strong></span><span className={profileReady ? 'status-badge' : 'status-badge machine-status--fail'}>{profileReady ? 'Đã kiểm tra hợp lệ' : 'Thiếu dữ liệu phù hợp'}</span></div>
          <p className="form-hint">Phân tích một chiều cần hai tệp số đo đã kiểm tra hợp lệ. Phân tích hai chiều cần tệp RTDOSE làm liều tham chiếu và tệp số đo hoặc RTDOSE để đối chiếu. Pylinac thực hiện phép Gamma theo kiểu dữ liệu đã chọn.</p>
        </>}
      </section>

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">TIÊU CHÍ ĐÁNH GIÁ</p><h2>Tham số phân tích</h2></div><span className="status-badge">{dimensionalityLabel(configuration.dimensionality)}</span></div>
        <div className="gamma-config-grid">
          <label>Kiểu dữ liệu<select value={configuration.dimensionality} onChange={(event) => { const dimensionality = event.target.value as GammaConfiguration['dimensionality']; setConfiguration((current) => ({ ...current, dimensionality })); setReferenceId(undefined); setEvaluationId(undefined) }}><option value="1D">Một chiều</option><option value="2D">Hai chiều</option></select></label>
          <label>Chênh lệch liều (%)<input type="number" min="0.01" step="0.1" value={configuration.dose_difference_percent} onChange={(event) => updateNumber('dose_difference_percent', event.target.value)} /></label>
          <label>DTA (mm)<input type="number" min="0.01" step="0.1" value={configuration.distance_to_agreement_mm} onChange={(event) => updateNumber('distance_to_agreement_mm', event.target.value)} /></label>
          <label>Ngưỡng liều thấp (%)<input type="number" min="0" max="100" step="1" value={configuration.dose_threshold_percent} onChange={(event) => updateNumber('dose_threshold_percent', event.target.value)} /></label>
          <label>Ngưỡng đạt (%)<input type="number" min="0" max="100" step="1" value={configuration.pass_rate_threshold_percent} onChange={(event) => updateNumber('pass_rate_threshold_percent', event.target.value)} /></label>
          <label>Chuẩn hóa<select value={configuration.normalization} onChange={(event) => setConfiguration((current) => ({ ...current, normalization: event.target.value as GammaConfiguration['normalization'] }))}><option value="GLOBAL">Toàn cục</option><option value="LOCAL">Cục bộ</option></select></label>
          <label>Phạm vi so sánh<select value={configuration.coverage_policy} onChange={(event) => setConfiguration((current) => ({ ...current, coverage_policy: event.target.value as GammaConfiguration['coverage_policy'] }))}><option value="FULL_ROI">Toàn bộ vùng</option><option value="OVERLAP_ONLY">Chỉ vùng chồng lấp</option></select></label>
          <label>Giới hạn Gamma<input type="number" min="1" max="10" step="0.5" value={configuration.max_gamma} onChange={(event) => updateNumber('max_gamma', event.target.value)} /></label>
          <label>Phép nội suy<select value={configuration.interpolation} disabled><option value="GRID">Trên lưới đã kiểm tra</option></select></label>
          <label>Số khoảng biểu đồ<input type="number" min="2" max="100" step="1" value={configuration.histogram_bins} onChange={(event) => updateNumber('histogram_bins', event.target.value)} /></label>
          <label>Hệ số tinh chỉnh một chiều<input type="number" min="1" max="10" step="1" value={configuration.resolution_factor} onChange={(event) => updateNumber('resolution_factor', event.target.value)} /></label>
        </div>
        <p className="form-hint">Phép tính mới sử dụng Pylinac với chênh lệch liều tương đối và phép tìm trên lưới. Hệ số tinh chỉnh chỉ áp dụng cho Gamma một chiều; số khoảng biểu đồ chỉ thay đổi cách hiển thị kết quả. Mọi tiêu chí được lưu cùng kết quả, không thay đổi các lần phân tích trước.</p>
        {blockingErrors.length > 0 && <div className="alert alert--error" role="alert"><strong>Chưa thể bắt đầu phân tích</strong><ul>{blockingErrors.map((item, index) => <li key={`${item.field}-${index}`}>{item.message}</li>)}</ul></div>}
        <button disabled={busy || !profileReady || selectedReferenceId === selectedEvaluationId || blockingErrors.length > 0} onClick={() => createMutation.mutate()}>Bắt đầu phân tích</button>
      </section>

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ PHÂN TÍCH</p><h2>Tiến độ và kết quả</h2></div><strong>{runs.data?.total ?? '—'}</strong></div>
        {runs.isPending ? <p>Đang tải lịch sử phân tích…</p> : runs.error ? <div className="alert alert--error"><p>{errorMessage(runs.error)}</p><button onClick={() => void runs.refetch()}>Thử lại</button></div> : !activeRun ? <p className="empty-state">Chưa có kết quả. Chọn dữ liệu và bắt đầu phân tích.</p> : <>
          <div className="gamma-run-meta"><span>Loại dữ liệu <strong>{dimensionalityLabel(snapshotDimensionality)}</strong></span><span>Phạm vi <strong>{coverageLabel(snapshotCoveragePolicy)}</strong></span><span>Giới hạn Gamma <strong>{numberValue(snapshotMaxGamma)}</strong></span><span>Trạng thái <strong className={statusClass(activeRun.status)}>{statusLabel(activeRun.status)}</strong></span><span>Tiến độ {activeRun.progress_percent}%</span><span>Lần thực hiện {activeRun.attempt_count}</span></div>
          {snapshotDimensionality === '3D' && <div className="alert alert--warning"><strong>Kết quả cũ chỉ được xem</strong><p>Phép Gamma ba chiều này được tạo bởi bộ tính trước đây. Hệ thống không tính lại bằng Pylinac và không cho tạo phép tính ba chiều mới.</p></div>}
          {isActiveJob(activeRun) && <div className="gamma-progress"><div style={{ width: `${activeRun.progress_percent}%` }} /><div className="gamma-progress__footer"><p>Bài phân tích đang được xử lý; trang sẽ tự cập nhật sau mỗi vài giây.</p>{(activeRun.status === 'QUEUED' || activeRun.status === 'RETRYING') && <button className="button-secondary" disabled={busy} onClick={() => cancelMutation.mutate(activeRun.id)}>Hủy phân tích</button>}</div></div>}
          {activeRun.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Phân tích chưa hoàn tất</h3><ul>{activeRun.error_snapshot.map((item, index) => <li key={index}>{scalarValue(item.message, 'Đã xảy ra lỗi khi phân tích dữ liệu.')}</li>)}</ul><button disabled={busy} onClick={() => retryMutation.mutate(activeRun.id)}>Phân tích lại</button></div>}
          {activeRun.result_snapshot.overall_status && <div className="gamma-result-banner"><span className={statusClass(String(activeRun.result_snapshot.overall_status))}>{statusLabel(activeRun.result_snapshot.overall_status)}</span><strong>{numberValue(resultMetrics?.pass_rate_percent)}%</strong><span>Tỷ lệ đạt · yêu cầu {numberValue(snapshotPassTarget)}%</span></div>}
          {resultMetrics && <div className="metric-grid gamma-metrics"><article><span>Điểm được phân tích</span><strong>{numberValue(resultMetrics.evaluated_points)}</strong></article><article><span>Điểm đạt</span><strong>{numberValue(resultMetrics.passing_points)}</strong></article><article><span>Điểm không đạt</span><strong>{numberValue(resultMetrics.nonpassing_points)}</strong></article><article><span>Điểm loại khỏi tính toán</span><strong>{numberValue(resultMetrics.excluded_points)}</strong></article><article><span>Mức bao phủ</span><strong>{numberValue(resultMetrics.coverage_fraction)}</strong></article><article><span>Gamma P95</span><strong>{numberValue(percentiles?.p95)}</strong></article></div>}
          {histogramCounts.length > 0 && histogramEdges.length >= histogramCounts.length + 1 && <div className="gamma-histogram" aria-label="Biểu đồ phân bố Gamma"><h3>Phân bố Gamma</h3><div className="gamma-histogram__bars">{histogramCounts.map((count, index) => <div className="gamma-histogram__item" key={index}><div className="gamma-histogram__bar"><span style={{ height: `${histogramPeak > 0 ? Math.max(4, count / histogramPeak * 100) : 4}%` }} /></div><small>{numberValue(histogramEdges[index])}–{numberValue(histogramEdges[index + 1])}</small><b>{numberValue(count)}</b></div>)}</div><p className="form-hint">Mỗi cột thể hiện số điểm trong một khoảng Gamma; các điểm dưới ngưỡng liều thấp không nằm trong mẫu số.</p></div>}
          {activeRun.warning_snapshot.length > 0 && <div className="alert alert--warning"><strong>Cảnh báo</strong><ul>{activeRun.warning_snapshot.map((item, index) => <li key={index}>{scalarValue(item.message, 'Có cảnh báo trong kết quả phân tích.')}</li>)}</ul></div>}
          {gammaMap.length > 0 && <div className="table-wrap"><table className="gamma-map-table"><caption>Bản đồ Gamma · hiển thị tối đa 100 điểm đầu tiên</caption><thead>{gammaMap.some((item) => 'coordinate_mm' in item) ? <tr><th>Vị trí (mm)</th><th>Liều tham chiếu</th><th>Gamma</th><th>Đánh giá</th></tr> : <tr><th>Hàng</th><th>Cột</th><th>Liều tham chiếu</th><th>Gamma</th><th>Đánh giá</th></tr>}</thead><tbody>{gammaMap.slice(0, 100).map((item, index) => <tr key={index}>{'coordinate_mm' in item ? <><td>{numberValue(item.coordinate_mm)}</td><td>{numberValue(item.reference_dose_gy)} Gy</td><td>{numberValue(item.gamma)}</td><td><span className={statusClass(String(item.status))}>{statusLabel(item.status)}</span></td></> : <><td>{numberValue(item.row)}</td><td>{numberValue(item.column)}</td><td>{numberValue(item.reference_dose_gy)} Gy</td><td>{numberValue(item.gamma)}</td><td><span className={statusClass(String(item.status))}>{statusLabel(item.status)}</span></td></>}</tr>)}</tbody></table></div>}
        </>}
      </section>

      <section className="panel gamma-panel">
        <div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ</p><h2>Lịch sử và đối chiếu kết quả</h2></div></div>
        {runs.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Lần thực hiện</th><th>Trạng thái</th><th>Kết luận</th><th>Thời điểm</th><th /></tr></thead><tbody>{runs.data.items.map((run, index) => <tr key={run.id}><td><button className={run.id === activeRun?.id ? 'history-button history-button--selected' : 'history-button'} onClick={() => setSelectedRunId(run.id)}>Lần phân tích {index + 1}</button></td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td>{statusLabel(run.result_snapshot.overall_status)}</td><td>{formatDate(run.queued_at)}</td><td>{run.id !== activeRun?.id && <button className="button-secondary" onClick={() => setComparisonRunId(run.id)}>Đối chiếu</button>}</td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có lịch sử phân tích.</p>}
        {runs.data && runs.data.items.length > 1 && activeRun && <div className="compare-controls"><label>Đối chiếu lần đang xem với<select value={comparisonRunId ?? ''} onChange={(event) => setComparisonRunId(event.target.value || undefined)}><option value="">Chọn lần phân tích khác</option>{runs.data.items.filter((run) => run.id !== activeRun.id).map((run) => { const runIndex = runs.data?.items.findIndex((item) => item.id === run.id) ?? 0; return <option key={run.id} value={run.id}>Lần phân tích {runIndex + 1} · {statusLabel(run.status)}</option> })}</select></label>{comparison.isPending && comparisonRunId && <p>Đang tải phần đối chiếu…</p>}{comparison.error && <p className="error-text">{errorMessage(comparison.error)}</p>}{comparison.data && comparisonRows.length > 0 && <div className="table-wrap"><table><thead><tr><th>Thông tin</th><th>Lần đang xem</th><th>Lần đối chiếu</th></tr></thead><tbody>{comparisonRows.map((item) => <tr key={item.key}><td>{comparisonLabel(item.key)}</td><td>{comparisonValue(item.key, item.left)}</td><td>{comparisonValue(item.key, item.right)}</td></tr>)}</tbody></table></div>}{comparison.data && comparisonRows.length === 0 && <p className="empty-state">Hai kết quả không có thông tin tóm tắt để đối chiếu.</p>}</div>}
      </section>
    </div>
  )
}
