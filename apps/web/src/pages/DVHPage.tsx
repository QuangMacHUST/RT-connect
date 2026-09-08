import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  ApiClientError,
  apiClient,
  type DvhRequest,
  type DvhRunInput,
  type DvhRunResource,
  type DvhValidationResource
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type JsonRecord = Record<string, unknown>

function asRecord(value: unknown): JsonRecord {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonRecord : {}
}

function asNumbers(value: unknown): number[] {
  return Array.isArray(value) ? value.filter((item): item is number => typeof item === 'number' && Number.isFinite(item)) : []
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function textValue(value: unknown, fallback = '—'): string {
  if (value === null || value === undefined || value === '') return fallback
  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

function formatNumber(value: unknown, digits = 3): string {
  const number = numberValue(value)
  return number === undefined ? '—' : number.toFixed(digits)
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function statusClass(status: string | undefined): string {
  if (status === 'FAILED' || status === 'INVALID') return 'status-badge machine-status--fail'
  if (status === 'WARNING' || status === 'OVERLAP_ONLY') return 'status-badge status-badge--warning'
  return 'status-badge'
}

function parseNumberList(value: string): number[] | null {
  const parts = value.split(/[\s,;]+/).map((item) => item.trim()).filter(Boolean)
  const parsed = parts.map(Number)
  return parts.length > 0 && parsed.every((item) => Number.isFinite(item)) ? parsed : null
}

function chartPoints(result: JsonRecord | undefined): string {
  const curve = asRecord(result?.curve)
  const doses = asNumbers(curve.dose_gy)
  const volumes = asNumbers(curve.cumulative_volume_percent)
  if (doses.length < 2 || doses.length !== volumes.length) return ''
  const minimumDose = Math.min(...doses)
  const maximumDose = Math.max(...doses)
  const minimumVolume = Math.min(...volumes)
  const maximumVolume = Math.max(...volumes)
  const doseSpan = maximumDose - minimumDose || 1
  const volumeSpan = maximumVolume - minimumVolume || 1
  return doses.map((dose, index) => {
    const x = ((dose - minimumDose) / doseSpan) * 100
    const y = 92 - ((volumes[index] - minimumVolume) / volumeSpan) * 82
    return `${x},${y}`
  }).join(' ')
}

function PreviewGrid({ result }: { result: JsonRecord | undefined }) {
  const preview = asRecord(result?.visual_preview)
  const dose = asNumbers(preview.dose_gy)
  const mask = Array.isArray(preview.roi_mask) ? preview.roi_mask.map((item) => item === true) : []
  const rows = numberValue(preview.rows) ?? 0
  const columns = numberValue(preview.columns) ?? 0
  if (!dose.length || !rows || !columns || dose.length !== rows * columns) return <p className="empty-state">Chưa có visual preview cho ROI này.</p>
  const minimum = Math.min(...dose)
  const maximum = Math.max(...dose)
  const span = maximum - minimum || 1
  return <div className="dvh-preview-grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }} aria-label="Dose native grid preview">
    {dose.map((value, index) => {
      const intensity = (value - minimum) / span
      const hue = 220 - intensity * 190
      return <span
        className={mask[index] ? 'dvh-preview-cell dvh-preview-cell--roi' : 'dvh-preview-cell'}
        key={`${index}-${value}`}
        style={{ backgroundColor: `hsl(${hue} 70% ${mask[index] ? 56 : 78}%)` }}
        title={`Dose ${formatNumber(value)} Gy${mask[index] ? ' · ROI' : ''}`}
      />
    })}
  </div>
}

function ResultPanel({ result }: { result: JsonRecord | undefined }) {
  if (!result) return <p className="empty-state">Chưa có kết quả. Chạy Validate để xem preview hoặc lưu một DVH run.</p>
  const dose = asRecord(result.dose)
  const roi = asRecord(result.roi)
  const coverage = asRecord(result.coverage)
  const metrics = asRecord(result.metrics)
  const dx = asRecord(metrics.Dx_gy)
  const vxPercent = asRecord(metrics.Vx_percent)
  const vxCc = asRecord(metrics.Vx_cc)
  const curve = chartPoints(result)
  const warnings = Array.isArray(result.warnings) ? result.warnings : []
  return <>
    <div className="dvh-result-banner">
      <div><span className={statusClass(String(coverage.status ?? 'FULL'))}>{textValue(coverage.status, 'FULL')}</span><strong>{textValue(roi.name)}</strong><span>ROI #{textValue(roi.roi_number)} · {textValue(roi.contour_count)} contour</span></div>
      <small>{textValue(result.engine_version)} · {textValue(result.schema_version)}</small>
    </div>
    <div className="metric-grid dvh-metrics">
      <article className="metric-card"><p>Volume</p><strong>{formatNumber(metrics.volume_cc)}<small> cc</small></strong><span>{textValue(coverage.selected_voxel_count)} voxel</span></article>
      <article className="metric-card"><p>Dmean</p><strong>{formatNumber(metrics.Dmean_gy)}<small> Gy</small></strong><span>physical dose</span></article>
      <article className="metric-card"><p>Dmin / Dmax</p><strong>{formatNumber(metrics.Dmin_gy)}–{formatNumber(metrics.Dmax_gy)}</strong><span>Gy</span></article>
      <article className="metric-card"><p>Coverage</p><strong>{textValue(coverage.coverage_percent, 'n/a')}<small>{coverage.coverage_percent === null ? '' : ' %'}</small></strong><span>{textValue(coverage.policy)}</span></article>
    </div>
    <div className="dvh-result-grid">
      <section className="dvh-subpanel"><div className="panel-heading"><div><p className="eyebrow">DVH CURVE</p><h3>Cumulative volume</h3></div><span className="form-hint">Volume receiving at least dose threshold</span></div>{curve ? <div className="dvh-chart"><svg viewBox="0 0 100 100" role="img" aria-label="Cumulative DVH curve" preserveAspectRatio="none"><line x1="0" y1="92" x2="100" y2="92" /><line x1="0" y1="10" x2="0" y2="92" /><polyline points={curve} /></svg></div> : <p className="empty-state">Không đủ điểm để vẽ đường cong.</p>}<div className="dvh-chart-legend"><span>Dose: {formatNumber(asNumbers(asRecord(result.curve).dose_gy)[0])}–{formatNumber(asNumbers(asRecord(result.curve).dose_gy).at(-1))} Gy</span><span>Mode: {textValue(asRecord(result.visual_preview).mode)}</span></div></section>
      <section className="dvh-subpanel"><div className="panel-heading"><div><p className="eyebrow">VISUAL DOSE GRID</p><h3>Slice preview</h3></div><span className="form-hint">ROI overlay</span></div><PreviewGrid result={result} /><div className="dvh-preview-legend"><span><i className="dvh-legend-swatch dvh-legend-swatch--dose" /> Dose intensity</span><span><i className="dvh-legend-swatch dvh-legend-swatch--roi" /> ROI voxel</span></div></section>
    </div>
    <div className="table-wrap"><table className="dvh-metric-table"><thead><tr><th>Metric</th><th>Value</th><th>Unit / definition</th></tr></thead><tbody>
      <tr><td>D2 / D50 / D95 / D98</td><td>{Object.entries(dx).map(([key, value]) => `${key.replace('_gy', '')}: ${formatNumber(value)} Gy`).join(' · ') || '—'}</td><td>Dose received by at least x% of ROI volume</td></tr>
      <tr><td>Vx percent</td><td>{Object.entries(vxPercent).map(([key, value]) => `${key.replace('_gy', '')}: ${formatNumber(value, 2)}%`).join(' · ') || '—'}</td><td>Percentage of selected ROI volume</td></tr>
      <tr><td>Vx absolute</td><td>{Object.entries(vxCc).map(([key, value]) => `${key.replace('_gy', '')}: ${formatNumber(value)} cc`).join(' · ') || '—'}</td><td>Absolute selected volume</td></tr>
      <tr><td>Input dose</td><td>{formatNumber(dose.minimum_gy)}–{formatNumber(dose.maximum_gy)} Gy</td><td>{textValue(dose.units)} · {textValue(dose.dose_type)}</td></tr>
    </tbody></table></div>
    {warnings.length > 0 && <div className="alert alert--warning"><strong>Cảnh báo cần xem xét</strong><ul>{warnings.map((item, index) => <li key={`${textValue(asRecord(item).code)}-${index}`}>{textValue(asRecord(item).message, JSON.stringify(item))}</li>)}</ul></div>}
  </>
}

export function DVHPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const accessToken = session?.access_token
  const [selectedDoseId, setSelectedDoseId] = useState<string>()
  const [selectedStructureId, setSelectedStructureId] = useState<string>()
  const [selectedCtId, setSelectedCtId] = useState<string>('')
  const [roiNumber, setRoiNumber] = useState(0)
  const [coveragePolicy, setCoveragePolicy] = useState<DvhRequest['coverage_policy']>('FULL_ROI')
  const [sliceThickness, setSliceThickness] = useState('')
  const [dxText, setDxText] = useState('2, 50, 95, 98')
  const [vxText, setVxText] = useState('0, 20, 30, 40, 50')
  const [message, setMessage] = useState<string>()
  const [validation, setValidation] = useState<DvhValidationResource>()
  const [selectedRunId, setSelectedRunId] = useState<string>()

  const bootstrap = useQuery({ queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!), enabled: Boolean(accessToken), retry: false })
  const organizationId = bootstrap.data?.organization.id
  const cases = useQuery({ queryKey: ['dvh-case', organizationId, caseId, accessToken], queryFn: () => apiClient.qaCases(accessToken!, organizationId!), enabled: Boolean(accessToken && organizationId && caseId), retry: false })
  const selectedCase = useMemo(() => cases.data?.items.find((item) => item.id === caseId), [cases.data, caseId])
  const inputs = useQuery({
    queryKey: ['dvh-inputs', organizationId, caseId, selectedStructureId, accessToken],
    queryFn: () => apiClient.dvhInputs(accessToken!, organizationId!, caseId!, selectedStructureId),
    enabled: Boolean(accessToken && organizationId && caseId && selectedCase), retry: false
  })
  const doseId = selectedDoseId && inputs.data?.dose_artifacts.some((item) => item.id === selectedDoseId) ? selectedDoseId : inputs.data?.dose_artifacts[0]?.id ?? ''
  const structureId = selectedStructureId && inputs.data?.structure_artifacts.some((item) => item.id === selectedStructureId) ? selectedStructureId : inputs.data?.structure_artifacts[0]?.id ?? ''
  const roiOptions = useMemo(() => (inputs.data?.rois ?? []).map((item) => ({ number: numberValue(item.roi_number), name: textValue(item.name), contours: numberValue(item.contour_count) })).filter((item): item is { number: number; name: string; contours: number | undefined } => item.number !== undefined), [inputs.data?.rois])
  const effectiveRoi = roiOptions.some((item) => item.number === roiNumber) ? roiNumber : roiOptions[0]?.number ?? 0
  const runs = useQuery({ queryKey: ['dvh-runs', organizationId, caseId, accessToken], queryFn: () => apiClient.dvhRuns(accessToken!, organizationId!, caseId!), enabled: Boolean(accessToken && organizationId && caseId && selectedCase), retry: false })
  const activeRun: DvhRunResource | undefined = useMemo(() => runs.data?.items.find((item) => item.id === selectedRunId) ?? runs.data?.items[0], [runs.data, selectedRunId])
  const buildRequest = (): DvhRequest | null => {
    const dx = parseNumberList(dxText)
    const vx = parseNumberList(vxText)
    if (!doseId || !structureId || !effectiveRoi) {
      setMessage('Cần chọn RTDOSE, RTSTRUCT và ROI trước khi chạy DVH.')
      return null
    }
    if (!dx || !vx) {
      setMessage('D2/Dx và Vx phải là danh sách số, phân cách bằng dấu phẩy hoặc khoảng trắng.')
      return null
    }
    const thickness = sliceThickness.trim() ? Number(sliceThickness) : null
    if (thickness !== null && (!Number.isFinite(thickness) || thickness <= 0)) {
      setMessage('Slice thickness phải là số dương hoặc để trống để dùng metadata DICOM.')
      return null
    }
    return {
      dose_artifact_id: doseId,
      structure_artifact_id: structureId,
      ct_artifact_id: selectedCtId || null,
      roi_number: effectiveRoi,
      coverage_policy: coveragePolicy,
      slice_thickness_mm: thickness,
      dx_percentages: dx,
      vx_doses_gy: vx,
      preview_limit: 4096
    }
  }
  const validateMutation = useMutation({
    mutationFn: (body: DvhRequest) => apiClient.validateDvh(accessToken!, organizationId!, caseId!, body),
    onSuccess: (result) => { setValidation(result); setMessage(result.valid ? 'Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.' : 'Validation DVH phát hiện lỗi; chưa lưu kết quả.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const createMutation = useMutation({
    mutationFn: (body: DvhRunInput) => apiClient.createDvhRun(accessToken!, organizationId!, caseId!, body),
    onSuccess: (run) => { setSelectedRunId(run.id); setMessage('Đã lưu DVH run cùng input snapshot, engine version và checksum nguồn.'); void queryClient.invalidateQueries({ queryKey: ['dvh-runs', organizationId, caseId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const runValidation = () => {
    const body = buildRequest()
    if (body) validateMutation.mutate(body)
  }
  const saveRun = () => {
    const body = buildRequest()
    if (body) createMutation.mutate({ ...body, idempotency_key: `dvh-${crypto.randomUUID()}` })
  }
  const download = async (format: 'JSON' | 'CSV') => {
    if (!activeRun) return
    try {
      const blob = await apiClient.downloadDvh(accessToken!, organizationId!, caseId!, activeRun.id, format)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `rt-connect-dvh-${activeRun.id}.${format.toLowerCase()}`
      anchor.click()
      URL.revokeObjectURL(url)
    } catch (error) {
      setMessage(errorMessage(error))
    }
  }

  if (bootstrap.isPending || cases.isPending) return <main className="auth-state">Đang tải Visual Dose / DVH…</main>
  const initialFailure = bootstrap.error ?? cases.error
  if (initialFailure || !organizationId || !caseId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở Visual Dose / DVH</h1><p>{errorMessage(initialFailure)}</p><Link className="button-link" to="/app/qa">Quay lại QA Archive</Link></section></div>
  if (!selectedCase) return <div className="page"><section className="alert alert--error"><h1>Không tìm thấy QA case</h1><p>Case này không thuộc organization hiện tại hoặc đã bị lưu trữ.</p><Link className="button-link" to="/app/qa">Quay lại QA Archive</Link></section></div>

  const previewResult = validation?.valid ? validation.preview ?? undefined : undefined
  const result = activeRun?.result_snapshot ?? previewResult
  const inputError = inputs.error ? errorMessage(inputs.error) : undefined
  const busy = validateMutation.isPending || createMutation.isPending
  return <div className="page page--dvh">
    <header className="page-header"><div><p className="eyebrow">P17 · MOD-15</p><h1>Visual Dose / DVH Workspace</h1><p>{selectedCase.title} · phân tích physical-dose DVH từ RTDOSE và RTSTRUCT đã VALID, kèm preview dose-native và provenance.</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">QA Archive</Link><Link className="button-link button-secondary" to={`/app/qa/cases/${caseId}/gamma`}>Gamma</Link><span className="status-badge">API THẬT</span></div></header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="biological-notice dvh-notice"><strong>PHYSICAL DOSE · P17</strong><span>RTDOSE được quy đổi bằng DoseGridScaling và chỉ chấp nhận DoseUnits=GY. CT là liên kết hình học tùy chọn; khi không chọn CT, kết quả vẫn là DVH trên dose-native grid và không được gọi là anatomy overlay.</span></section>
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">INPUT PREFLIGHT</p><h2>Chọn dữ liệu DICOM đã VALID</h2></div><span className={inputs.error ? 'status-badge machine-status--fail' : 'status-badge'}>{inputs.data ? `${inputs.data.dose_artifacts.length} dose · ${inputs.data.structure_artifacts.length} structure` : 'Đang tải'}</span></div>
      {inputError ? <div className="alert alert--error"><p>{inputError}</p><button onClick={() => void inputs.refetch()}>Thử lại</button></div> : inputs.isPending ? <p>Đang tải input manifest…</p> : <div className="dvh-input-grid">
        <label>RTDOSE · dose<select value={doseId} onChange={(event) => setSelectedDoseId(event.target.value)}><option value="">Chọn RTDOSE</option>{(inputs.data?.dose_artifacts ?? []).map((item) => <option key={item.id} value={item.id}>{item.original_filename} · {item.sha256.slice(0, 12)}…</option>)}</select></label>
        <label>RTSTRUCT · structures<select value={structureId} onChange={(event) => { setSelectedStructureId(event.target.value); setRoiNumber(0); setValidation(undefined) }}><option value="">Chọn RTSTRUCT</option>{(inputs.data?.structure_artifacts ?? []).map((item) => <option key={item.id} value={item.id}>{item.original_filename} · {item.sha256.slice(0, 12)}…</option>)}</select></label>
        <label>CT · optional overlay<select value={selectedCtId} onChange={(event) => setSelectedCtId(event.target.value)}><option value="">Không chọn CT · dose-native</option>{(inputs.data?.ct_artifacts ?? []).map((item) => <option key={item.id} value={item.id}>{item.original_filename} · {item.sha256.slice(0, 12)}…</option>)}</select></label>
        <label>ROI · chọn theo ROINumber<select value={effectiveRoi || ''} onChange={(event) => setRoiNumber(Number(event.target.value))}><option value="">Chọn ROI</option>{roiOptions.map((item) => <option key={item.number} value={item.number}>#{item.number} · {item.name} · {item.contours ?? 0} contour</option>)}</select></label>
      </div>}
      {structureId && inputs.data?.rois.length === 0 && <p className="form-hint">RTSTRUCT đã chọn nhưng chưa có ROI để chọn hoặc chưa đọc được contour definition.</p>}
      <p className="form-hint">Tên ROI chỉ để hiển thị; engine luôn tính theo số ROI duy nhất trong RTSTRUCT. Artifact không ở trạng thái VALID sẽ không xuất hiện trong danh sách.</p>
    </section>
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">CALCULATION CONTRACT</p><h2>Tham số và chính sách coverage</h2></div><span className="status-badge">NO PRESCRIPTION</span></div><div className="dvh-config-grid">
      <label>Coverage policy<select value={coveragePolicy} onChange={(event) => { setCoveragePolicy(event.target.value as DvhRequest['coverage_policy']); setValidation(undefined) }}><option value="FULL_ROI">FULL_ROI · thiếu coverage = lỗi</option><option value="OVERLAP_ONLY">OVERLAP_ONLY · cảnh báo phần giao</option></select></label>
      <label>Slice thickness (mm) · single-frame only<input inputMode="decimal" value={sliceThickness} placeholder="Để trống: dùng DICOM metadata" onChange={(event) => setSliceThickness(event.target.value)} /></label>
      <label>D2/Dx (%)<input value={dxText} onChange={(event) => setDxText(event.target.value)} /></label>
      <label>Vx dose (Gy)<input value={vxText} onChange={(event) => setVxText(event.target.value)} /></label>
    </div><p className="form-hint">D(x) dùng quantile tuyến tính; V(x) là thể tích nhận ít nhất ngưỡng x Gy. Danh sách sẽ được chuẩn hóa và snapshot cùng run.</p><div className="dvh-actions"><button disabled={busy || !doseId || !structureId || !effectiveRoi} onClick={runValidation}>{validateMutation.isPending ? 'Đang validate…' : 'Validate & preview'}</button><button className="button-secondary" disabled={busy || !doseId || !structureId || !effectiveRoi} onClick={saveRun}>{createMutation.isPending ? 'Đang lưu…' : 'Tính và lưu DVH run'}</button></div></section>
    {validation && !validation.valid && <section className="alert alert--error"><h3>DVH không hợp lệ</h3><ul>{validation.errors.map((item, index) => <li key={`${textValue(asRecord(item).code)}-${index}`}><strong>{textValue(asRecord(item).code)}</strong> · {textValue(asRecord(item).message, JSON.stringify(item))}</li>)}</ul></section>}
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">RESULT / PROVENANCE</p><h2>Kết quả DVH</h2></div><div className="page-header__actions">{activeRun && <><button className="button-secondary" onClick={() => void download('JSON')}>JSON</button><button className="button-secondary" onClick={() => void download('CSV')}>CSV</button></>}</div></div><ResultPanel result={result} />
      {activeRun && <div className="dvh-provenance"><span>Run <code>{activeRun.id}</code></span><span>Input fingerprint <code>{textValue(activeRun.input_snapshot.request_fingerprint)}</code></span><span>Result SHA <code>{textValue(activeRun.result_snapshot.result_sha256)}</code></span><span>Saved {new Date(activeRun.created_at).toLocaleString('vi-VN')}</span></div>}
    </section>
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">RUN HISTORY</p><h2>Lịch sử DVH của case</h2></div><strong>{runs.data?.total ?? '—'}</strong></div>{runs.error ? <div className="alert alert--error"><p>{errorMessage(runs.error)}</p><button onClick={() => void runs.refetch()}>Thử lại</button></div> : runs.isPending ? <p>Đang tải lịch sử…</p> : runs.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Run</th><th>ROI</th><th>Coverage</th><th>Engine</th><th>Created</th><th /></tr></thead><tbody>{runs.data.items.map((run) => <tr key={run.id}><td><button className={run.id === activeRun?.id ? 'history-button history-button--selected' : 'history-button'} onClick={() => setSelectedRunId(run.id)}><code>{run.id.slice(0, 8)}…</code></button></td><td>#{run.roi_number}</td><td><span className="status-badge">{textValue(asRecord(run.result_snapshot.coverage).status)}</span></td><td>{run.engine_version}</td><td>{new Date(run.created_at).toLocaleString('vi-VN')}</td><td>{run.id === activeRun?.id && <strong>Đang xem</strong>}</td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có DVH run. Validate chỉ tạo preview; dùng “Tính và lưu” để tạo snapshot truy vết được.</p>}</section>
  </div>
}
