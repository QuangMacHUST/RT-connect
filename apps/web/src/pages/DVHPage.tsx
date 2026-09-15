import { useEffect, useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import {
  ApiClientError,
  apiClient,
  type DvhCtPreviewResource,
  type DvhRequest,
  type DvhRunInput,
  type DvhRunResource,
  type DvhValidationResource,
  type BiologicalLibraryEntryResource,
  type QAProtocolResource
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { artifactDisplayName } from './qaArtifactLabels'
import { dvhIndexLabel, dvhIndexMissingLabel, dvhIndexStatusLabel, dvhMetricLabel, dvhOperatorLabel, dvhSourceLabel, dvhStatusLabel } from './dvhLabels'

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
  return typeof value === 'object' ? fallback : String(value)
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

const indexOptions = [
  { value: 'HI_D2_D98_OVER_D50', label: 'Độ đồng nhất (D2 − D98) / D50', hint: 'Dùng D2, D98 và D50 của thể tích ROI.' },
  { value: 'HI_D5_OVER_D95', label: 'Độ đồng nhất D5 / D95', hint: 'Dùng D5 và D95 của thể tích ROI.' },
  { value: 'CI_RTOG_95', label: 'Chỉ số phù hợp RTOG ở mức 95%', hint: 'Cần liều kê đơn để xác định thể tích liều 95%.' },
  { value: 'CI_PADDICK_95', label: 'Chỉ số phù hợp Paddick ở mức 95%', hint: 'Cần liều kê đơn và thể tích đích nhận đủ 95%.' }
]

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

function CtPreviewCanvas({ preview }: { preview: DvhCtPreviewResource }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const { rows, columns } = preview.ct.output_grid
    const pixels = preview.ct.display_pixels
    if (pixels.length !== rows * columns) return
    canvas.width = columns
    canvas.height = rows
    const context = canvas.getContext('2d')
    if (!context) return
    context.imageSmoothingEnabled = false
    const image = context.createImageData(columns, rows)
    pixels.forEach((value, index) => {
      const offset = index * 4
      image.data[offset] = value
      image.data[offset + 1] = value
      image.data[offset + 2] = value
      image.data[offset + 3] = 255
    })
    context.putImageData(image, 0, 0)

    const dose = preview.overlay.dose_gy
    const finiteDose = dose.filter((value): value is number => value !== null && Number.isFinite(value))
    if (finiteDose.length > 0) {
      const minimum = Math.min(...finiteDose)
      const maximum = Math.max(...finiteDose)
      const span = maximum - minimum || 1
      dose.forEach((value, index) => {
        if (value === null || !Number.isFinite(value)) return
        const intensity = (value - minimum) / span
        const x = index % columns
        const y = Math.floor(index / columns)
        context.fillStyle = `rgba(${Math.round(255 * intensity)}, ${Math.round(110 + 100 * (1 - intensity))}, 40, .42)`
        context.fillRect(x, y, 1, 1)
      })
    }
    if (preview.overlay.roi_mask?.some(Boolean)) {
      preview.overlay.roi_mask.forEach((selected, index) => {
        if (!selected) return
        const x = index % columns
        const y = Math.floor(index / columns)
        context.fillStyle = 'rgba(10, 148, 136, .62)'
        context.fillRect(x, y, 1, 1)
      })
    }
    const stride = preview.ct.output_grid.stride
    const crosshair = preview.registration.crosshair.nearest_pixel
    if (crosshair.length >= 3 && preview.registration.crosshair.visible) {
      const x = crosshair[2] / stride
      const y = crosshair[1] / stride
      context.strokeStyle = '#f8fafc'
      context.lineWidth = Math.max(1, 1 / Math.max(columns, rows) * 100)
      context.beginPath()
      context.moveTo(x, 0)
      context.lineTo(x, rows)
      context.moveTo(0, y)
      context.lineTo(columns, y)
      context.stroke()
    }
  }, [preview])

  return <canvas className="dvh-ct-canvas" ref={canvasRef} role="img" aria-label={`CT slice ${preview.ct.frame_index + 1}`} />
}

function CtPreviewPanel({
  preview,
  onFrameChange,
  isPending,
  error,
  onRetry
}: {
  preview: DvhCtPreviewResource | undefined
  onFrameChange: (value: number) => void
  isPending: boolean
  error: string | undefined
  onRetry: () => void
}) {
  if (isPending) return <section className="dvh-subpanel"><div className="panel-heading"><div><p className="eyebrow">CT ANATOMY PREVIEW</p><h3>Đang đọc lát cắt CT…</h3></div></div><p className="empty-state">Đang tải pixel CT và kiểm tra mapping theo patient LPS.</p></section>
  if (error) return <section className="dvh-subpanel"><div className="panel-heading"><div><p className="eyebrow">CT ANATOMY PREVIEW</p><h3>Không thể hiển thị CT</h3></div></div><div className="alert alert--error"><p>{error}</p><button onClick={onRetry}>Thử lại</button></div></section>
  if (!preview) return <section className="dvh-subpanel"><div className="panel-heading"><div><p className="eyebrow">CT ANATOMY PREVIEW</p><h3>Chưa chọn CT</h3></div></div><p className="empty-state">Chọn một CT đã VALID để mở anatomy preview; dose-native DVH vẫn có thể chạy mà không cần CT.</p></section>
  const warnings = preview.warnings
  return <section className="dvh-subpanel dvh-ct-panel">
    <div className="panel-heading"><div><p className="eyebrow">CT ANATOMY PREVIEW</p><h3>CT + dose/ROI overlay</h3></div><span className={preview.registration.overlay_available ? 'status-badge' : 'status-badge status-badge--warning'}>{preview.registration.overlay_available ? 'LPS LINKED' : 'NO DOSE OVERLAP'}</span></div>
    <div className="dvh-ct-controls"><label>Lát cắt CT<select value={preview.ct.frame_index} onChange={(event) => onFrameChange(Number(event.target.value))}>{Array.from({ length: preview.ct.frame_count }, (_, index) => <option value={index} key={index}>#{index + 1} · offset {formatNumber(preview.ct.slice_offset_mm)} mm{index === preview.ct.frame_index ? ' · đang xem' : ''}</option>)}</select></label><span className="form-hint">{preview.ct.value_unit} · window {formatNumber(preview.ct.window_center)} / {formatNumber(preview.ct.window_width)} · {preview.ct.output_grid.rows}×{preview.ct.output_grid.columns}</span></div>
    <div className="dvh-ct-view"><CtPreviewCanvas preview={preview} /></div>
    <div className="dvh-chart-legend"><span>Overlay: {preview.registration.overlay_algorithm}</span><span>ROI: {preview.roi ? `#${preview.roi.roi_number} · ${preview.roi.name}` : 'chưa chọn'}</span><span>Crosshair: {preview.registration.crosshair.visible ? 'dose grid center' : 'ngoài CT'}</span></div>
    <p className="form-hint">Frame of Reference: {preview.registration.source_frame_of_reference_uid}. Mapping là nearest-neighbor trong patient LPS; đây không phải deformable registration.</p>
    {warnings.length > 0 && <div className="alert alert--warning"><strong>Cảnh báo CT</strong><ul>{warnings.map((item, index) => <li key={`${textValue(asRecord(item).code)}-${index}`}>{textValue(asRecord(item).message, 'Cần xem lại thông tin CT.')}</li>)}</ul></div>}
  </section>
}

function ResultPanel({ result, isPreview = false }: { result: JsonRecord | undefined; isPreview?: boolean }) {
  if (!result) return <p className="empty-state">Chưa có kết quả. Chạy Validate để xem preview hoặc lưu một DVH run.</p>
  const dose = asRecord(result.dose)
  const roi = asRecord(result.roi)
  const coverage = asRecord(result.coverage)
  const metrics = asRecord(result.metrics)
  const dx = asRecord(metrics.Dx_gy)
  const vxPercent = asRecord(metrics.Vx_percent)
  const vxCc = asRecord(metrics.Vx_cc)
  const indices = asRecord(result.indices)
  const indexItems = Array.isArray(indices.items) ? indices.items.map(asRecord) : []
  const curve = chartPoints(result)
  const warnings = Array.isArray(result.warnings) ? result.warnings : []
  const limitEvaluation = asRecord(result.limit_evaluation)
  return <>
    <div className="dvh-result-banner">
      <div><span className={statusClass(String(coverage.status ?? 'FULL'))}>{dvhStatusLabel(textValue(coverage.status, 'FULL'))}</span><strong>{textValue(roi.name)}</strong><span>Vùng số {textValue(roi.roi_number)} · {textValue(roi.contour_count)} đường viền</span></div>
      <small>{isPreview ? 'Bản xem trước · chưa lưu' : 'Kết quả đã được tính và lưu'}</small>
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
    {Object.keys(limitEvaluation).length > 0 && <section className="dvh-subpanel dvh-limit-result"><div className="panel-heading"><div><p className="eyebrow">ĐÁNH GIÁ GIỚI HẠN</p><h3>Đánh giá theo nguồn đã chọn</h3></div><span className={statusClass(textValue(limitEvaluation.status))}>{dvhStatusLabel(textValue(limitEvaluation.status))}</span></div><div className="dvh-chart-legend"><span>Chỉ số: {dvhMetricLabel(textValue(limitEvaluation.metric_key))}</span><span>Thực tế: {formatNumber(limitEvaluation.actual)} {textValue(limitEvaluation.actual_unit)}</span><span>Giới hạn: {dvhOperatorLabel(textValue(limitEvaluation.operator))} {formatNumber(limitEvaluation.limit)} {textValue(limitEvaluation.actual_unit)}</span><span>Biên: {formatNumber(limitEvaluation.margin)} {textValue(limitEvaluation.margin_unit)}</span></div><p className="form-hint">Nguồn tham khảo: {dvhSourceLabel(textValue(limitEvaluation.source_type))}. Nguồn này được chọn rõ ràng và không tự áp dụng.</p></section>}
    {indexItems.length > 0 && <section className="dvh-subpanel dvh-index-result"><div className="panel-heading"><div><p className="eyebrow">CHỈ SỐ KẾ HOẠCH</p><h3>HI và CI theo công thức đã chọn</h3></div><span className={textValue(indices.status) === 'COMPUTED' ? 'status-badge' : 'status-badge status-badge--warning'}>{dvhIndexStatusLabel(textValue(indices.status))}</span></div><div className="table-wrap"><table><thead><tr><th>Chỉ số</th><th>Giá trị</th><th>Công thức</th><th>Trạng thái</th></tr></thead><tbody>{indexItems.map((item, index) => { const missing = Array.isArray(item.missing_inputs) ? item.missing_inputs.map((value) => dvhIndexMissingLabel(textValue(value))).join(', ') : ''; return <tr key={`${textValue(item.formula_id)}-${index}`}><td>{dvhIndexLabel(textValue(item.formula_id))}</td><td>{formatNumber(item.value, 4)}</td><td>{textValue(item.formula)}</td><td><span className={textValue(item.status) === 'COMPUTED' ? 'status-badge' : 'status-badge status-badge--warning'}>{dvhIndexStatusLabel(textValue(item.status))}</span>{missing && <small className="table-note">Thiếu: {missing}</small>}</td></tr> })}</tbody></table></div><p className="form-hint">Các chỉ số chỉ được tính theo công thức đã chọn. Hệ thống không tự kết luận đạt hay không đạt nếu chưa có nguồn và ngưỡng đánh giá phù hợp.</p></section>}
    {warnings.length > 0 && <div className="alert alert--warning"><strong>Cảnh báo cần xem xét</strong><ul>{warnings.map((item, index) => <li key={`${textValue(asRecord(item).code)}-${index}`}>{textValue(asRecord(item).message, 'Có cảnh báo cần xem xét trong kết quả.')}</li>)}</ul></div>}
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
  const [ctFrameIndex, setCtFrameIndex] = useState(0)
  const [roiNumber, setRoiNumber] = useState(0)
  const [coveragePolicy, setCoveragePolicy] = useState<DvhRequest['coverage_policy']>('FULL_ROI')
  const [sliceThickness, setSliceThickness] = useState('')
  const [dxText, setDxText] = useState('2, 50, 95, 98')
  const [vxText, setVxText] = useState('0, 20, 30, 40, 50')
  const [indexDefinitions, setIndexDefinitions] = useState<string[]>([])
  const [prescriptionDose, setPrescriptionDose] = useState('')
  const [bindingSource, setBindingSource] = useState<'NONE' | 'DOSE_LIMIT' | 'PROTOCOL'>('NONE')
  const [selectedLimitEntryId, setSelectedLimitEntryId] = useState('')
  const [selectedProtocolVersionId, setSelectedProtocolVersionId] = useState('')
  const [selectedProtocolMetricKey, setSelectedProtocolMetricKey] = useState('')
  const [message, setMessage] = useState<string>()
  const [validation, setValidation] = useState<DvhValidationResource>()
  const [selectedRunId, setSelectedRunId] = useState<string>()

  const bootstrap = useQuery({ queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!), enabled: Boolean(accessToken), retry: false })
  const organizationId = bootstrap.data?.organization.id
  const cases = useQuery({ queryKey: ['dvh-case', organizationId, caseId, accessToken], queryFn: () => apiClient.qaCases(accessToken!, organizationId!), enabled: Boolean(accessToken && organizationId && caseId), retry: false })
  const selectedCase = useMemo(() => cases.data?.items.find((item) => item.id === caseId), [cases.data, caseId])
  const inputManifest = useQuery({
    queryKey: ['dvh-input-manifest', organizationId, caseId, accessToken],
    queryFn: () => apiClient.dvhInputs(accessToken!, organizationId!, caseId!),
    enabled: Boolean(accessToken && organizationId && caseId && selectedCase), retry: false
  })
  const manifestData = inputManifest.data
  const structureId = selectedStructureId && manifestData?.structure_artifacts.some((item) => item.id === selectedStructureId) ? selectedStructureId : manifestData?.structure_artifacts[0]?.id ?? ''
  const inputs = useQuery({
    queryKey: ['dvh-inputs', organizationId, caseId, structureId, accessToken],
    queryFn: () => apiClient.dvhInputs(accessToken!, organizationId!, caseId!, structureId),
    enabled: Boolean(accessToken && organizationId && caseId && selectedCase && structureId), retry: false
  })
  const inputData = inputs.data ?? manifestData
  const doseId = selectedDoseId && inputData?.dose_artifacts.some((item) => item.id === selectedDoseId) ? selectedDoseId : inputData?.dose_artifacts[0]?.id ?? ''
  const roiOptions = useMemo(() => (inputData?.rois ?? []).map((item) => ({ number: numberValue(item.roi_number), name: textValue(item.name), contours: numberValue(item.contour_count) })).filter((item): item is { number: number; name: string; contours: number | undefined } => item.number !== undefined), [inputData?.rois])
  const effectiveRoi = roiOptions.some((item) => item.number === roiNumber) ? roiNumber : roiOptions[0]?.number ?? 0
  const ctPreview = useQuery({
    queryKey: ['dvh-ct-preview', organizationId, caseId, doseId, selectedCtId, structureId, effectiveRoi, ctFrameIndex, accessToken],
    queryFn: () => apiClient.dvhCtPreview(accessToken!, organizationId!, caseId!, {
      dose_artifact_id: doseId,
      ct_artifact_id: selectedCtId,
      ...(structureId && effectiveRoi ? { structure_artifact_id: structureId, roi_number: effectiveRoi } : {}),
      frame_index: ctFrameIndex
    }),
    enabled: Boolean(accessToken && organizationId && caseId && doseId && selectedCtId), retry: false
  })
  const runs = useQuery({ queryKey: ['dvh-runs', organizationId, caseId, accessToken], queryFn: () => apiClient.dvhRuns(accessToken!, organizationId!, caseId!), enabled: Boolean(accessToken && organizationId && caseId && selectedCase), retry: false })
  const doseLimitEntries = useQuery({
    queryKey: ['dvh-dose-limit-entries', organizationId, accessToken],
    queryFn: () => apiClient.biologicalLibrary(accessToken!, organizationId!, { entry_type: 'DOSE_LIMIT', status: 'PUBLISHED' }),
    enabled: Boolean(accessToken && organizationId && bindingSource === 'DOSE_LIMIT'), retry: false
  })
  const activeProtocols = useQuery({
    queryKey: ['dvh-active-protocols', organizationId, accessToken],
    queryFn: () => apiClient.qaProtocols(accessToken!, organizationId!, { status: 'ACTIVE' }),
    enabled: Boolean(accessToken && organizationId && bindingSource === 'PROTOCOL'), retry: false
  })
  const selectedProtocol = useMemo(() => activeProtocols.data?.items.find((item) => item.id === selectedProtocolVersionId), [activeProtocols.data?.items, selectedProtocolVersionId])
  const protocolMetricOptions = useMemo(() => (selectedProtocol?.rules ?? []).filter((rule) => ['MAX', 'MIN', 'RANGE', 'TARGET'].includes(rule.rule_type)), [selectedProtocol?.rules])
  const activeRun: DvhRunResource | undefined = useMemo(() => runs.data?.items.find((item) => item.id === selectedRunId) ?? runs.data?.items[0], [runs.data, selectedRunId])
  const ciRequested = indexDefinitions.some((value) => value.startsWith('CI_'))
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
    const prescription = prescriptionDose.trim() ? Number(prescriptionDose) : null
    if (prescription !== null && (!Number.isFinite(prescription) || prescription <= 0)) {
      setMessage('Liều kê đơn phải là số Gy dương hoặc để trống.')
      return null
    }
    if (ciRequested && prescription === null) {
      setMessage('Muốn tính CI, hãy nhập liều kê đơn bằng Gy.')
      return null
    }
    if (bindingSource === 'DOSE_LIMIT' && !selectedLimitEntryId) {
      setMessage('Đã chọn nguồn DOSE_LIMIT nhưng chưa chọn entry P16.')
      return null
    }
    if (bindingSource === 'PROTOCOL' && (!selectedProtocolVersionId || !selectedProtocolMetricKey)) {
      setMessage('Đã chọn nguồn QA protocol nhưng chưa chọn version ACTIVE và metric rule.')
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
      index_definitions: indexDefinitions,
      prescription_dose_gy: prescription,
      preview_limit: 4096,
      ...(bindingSource === 'DOSE_LIMIT' ? { limit_entry_id: selectedLimitEntryId } : {}),
      ...(bindingSource === 'PROTOCOL' ? { protocol_version_id: selectedProtocolVersionId, protocol_metric_key: selectedProtocolMetricKey } : {})
    }
  }
  const validateMutation = useMutation({
    mutationFn: (body: DvhRequest) => apiClient.validateDvh(accessToken!, organizationId!, caseId!, body),
    onSuccess: (result) => { setValidation(result); setMessage(result.valid ? 'Validation DVH hợp lệ; chưa tạo bản ghi lưu trữ.' : 'Validation DVH phát hiện lỗi; chưa lưu kết quả.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const createMutation = useMutation({
    mutationFn: (body: DvhRunInput) => apiClient.createDvhRun(accessToken!, organizationId!, caseId!, body),
    onSuccess: (run) => { setSelectedRunId(run.id); setMessage('Đã lưu kết quả DVH cùng thông tin nguồn và phiên bản bộ tính.'); void queryClient.invalidateQueries({ queryKey: ['dvh-runs', organizationId, caseId, accessToken] }) },
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
  const download = async () => {
    if (!activeRun) return
    try {
      const blob = await apiClient.downloadDvh(accessToken!, organizationId!, caseId!, activeRun.id, 'CSV')
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = 'rt-connect-bang-so-lieu-dvh.csv'
      anchor.style.display = 'none'
      document.body.appendChild(anchor)
      anchor.click()
      anchor.remove()
      // Keep the Blob URL alive until the browser has started consuming it.
      // Revoking it synchronously can leave Chromium downloads in .crdownload.
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      setMessage(errorMessage(error))
    }
  }

  if (bootstrap.isPending || cases.isPending) return <main className="auth-state">Đang tải Visual Dose / DVH…</main>
  const initialFailure = bootstrap.error ?? cases.error
  if (initialFailure || !organizationId || !caseId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở Visual Dose / DVH</h1><p>{errorMessage(initialFailure)}</p><Link className="button-link" to="/app/qa">Quay lại QA Archive</Link></section></div>
  if (!selectedCase) return <div className="page"><section className="alert alert--error"><h1>Không tìm thấy QA case</h1><p>Case này không thuộc organization hiện tại hoặc đã bị lưu trữ.</p><Link className="button-link" to="/app/qa">Quay lại QA Archive</Link></section></div>

  const previewResult = validation?.valid ? validation.preview ?? undefined : undefined
  const result = validation?.valid ? previewResult ?? activeRun?.result_snapshot : activeRun?.result_snapshot
  const inputRequestError = inputManifest.error ?? inputs.error
  const inputError = inputRequestError ? errorMessage(inputRequestError) : undefined
  const refetchInputs = () => {
    void inputManifest.refetch()
    if (structureId) void inputs.refetch()
  }
  const busy = validateMutation.isPending || createMutation.isPending
  return <div className="page page--dvh">
    <header className="page-header"><div><p className="eyebrow">P17 · MOD-15</p><h1>Visual Dose / DVH Workspace</h1><p>{selectedCase.title} · phân tích physical-dose DVH từ RTDOSE và RTSTRUCT đã VALID, kèm preview dose-native và provenance.</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">QA Archive</Link><Link className="button-link button-secondary" to={`/app/qa/cases/${caseId}/gamma`}>Gamma</Link><span className="status-badge">API THẬT</span></div></header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="biological-notice dvh-notice"><strong>PHYSICAL DOSE · P17</strong><span>RTDOSE được quy đổi bằng DoseGridScaling và chỉ chấp nhận DoseUnits=GY. CT là liên kết hình học tùy chọn; khi không chọn CT, kết quả vẫn là DVH trên dose-native grid và không được gọi là anatomy overlay.</span></section>
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">KIỂM TRA DỮ LIỆU ĐẦU VÀO</p><h2>Chọn dữ liệu DICOM hợp lệ</h2></div><span className={inputRequestError ? 'status-badge machine-status--fail' : 'status-badge'}>{inputData ? `${inputData.dose_artifacts.length} dữ liệu liều · ${inputData.structure_artifacts.length} cấu trúc` : 'Đang tải'}</span></div>
      {inputError ? <div className="alert alert--error"><p>{inputError}</p><button onClick={refetchInputs}>Thử lại</button></div> : !inputData ? <p>Đang tải input manifest…</p> : <div className="dvh-input-grid">
        <label>RTDOSE · dữ liệu liều<select value={doseId} onChange={(event) => setSelectedDoseId(event.target.value)}><option value="">Chọn RTDOSE</option>{inputData.dose_artifacts.map((item) => <option key={item.id} value={item.id}>{artifactDisplayName(item, inputData.dose_artifacts)}</option>)}</select></label>
        <label>RTSTRUCT · cấu trúc<select value={structureId} onChange={(event) => { setSelectedStructureId(event.target.value); setRoiNumber(0); setValidation(undefined) }}><option value="">Chọn RTSTRUCT</option>{inputData.structure_artifacts.map((item) => <option key={item.id} value={item.id}>{artifactDisplayName(item, inputData.structure_artifacts)}</option>)}</select></label>
        <label>CT · phủ ảnh giải phẫu tùy chọn<select value={selectedCtId} onChange={(event) => { setSelectedCtId(event.target.value); setCtFrameIndex(0); setValidation(undefined) }}><option value="">Không chọn CT · tính trên lưới liều</option>{inputData.ct_artifacts.map((item) => <option key={item.id} value={item.id}>{artifactDisplayName(item, inputData.ct_artifacts)}</option>)}</select></label>
        <label>ROI · chọn theo số vùng<select value={effectiveRoi || ''} onChange={(event) => setRoiNumber(Number(event.target.value))}><option value="">Chọn ROI</option>{roiOptions.map((item) => <option key={item.number} value={item.number}>Vùng số {item.number} · {item.name} · {item.contours ?? 0} đường viền</option>)}</select></label>
      </div>}
      {structureId && inputData && inputData.rois.length === 0 && !inputs.isPending && <p className="form-hint">RTSTRUCT đã chọn nhưng chưa có ROI để chọn hoặc chưa đọc được contour definition.</p>}
      <p className="form-hint">Tên ROI chỉ để hiển thị; engine luôn tính theo số ROI duy nhất trong RTSTRUCT. Artifact không ở trạng thái VALID sẽ không xuất hiện trong danh sách.</p>
    </section>
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">THAM SỐ TÍNH TOÁN</p><h2>Tham số và chính sách độ bao phủ</h2></div><span className="status-badge">Không tự áp dụng chỉ định</span></div><div className="dvh-config-grid">
      <label>Chính sách độ bao phủ<select value={coveragePolicy} onChange={(event) => { setCoveragePolicy(event.target.value as DvhRequest['coverage_policy']); setValidation(undefined) }}><option value="FULL_ROI">Đủ vùng ROI · thiếu vùng = lỗi</option><option value="OVERLAP_ONLY">Chỉ vùng chồng lấp · cảnh báo phần giao</option></select></label>
      <label>Độ dày lát cắt (mm) · chỉ một khung hình<input inputMode="decimal" value={sliceThickness} placeholder="Để trống: dùng thông tin DICOM" onChange={(event) => setSliceThickness(event.target.value)} /></label>
      <label>D2/Dx (%)<input value={dxText} onChange={(event) => setDxText(event.target.value)} /></label>
      <label>Vx liều (Gy)<input value={vxText} onChange={(event) => setVxText(event.target.value)} /></label>
      <fieldset className="dvh-index-picker"><legend>Chỉ số đồng nhất và phù hợp (tùy chọn)</legend><div className="dvh-index-options">{indexOptions.map((option) => <label className="dvh-index-option" key={option.value}><input type="checkbox" checked={indexDefinitions.includes(option.value)} onChange={(event) => { setIndexDefinitions((current) => event.target.checked ? [...current, option.value] : current.filter((value) => value !== option.value)); setValidation(undefined) }} /><span><strong>{option.label}</strong><small>{option.hint}</small></span></label>)}</div>{ciRequested && <label htmlFor="dvh-prescription-dose">Liều kê đơn (Gy)<input id="dvh-prescription-dose" inputMode="decimal" value={prescriptionDose} placeholder="Ví dụ: 60" onChange={(event) => { setPrescriptionDose(event.target.value); setValidation(undefined) }} /><small className="form-hint">Dùng để xác định ngưỡng liều 95% cho chỉ số phù hợp.</small></label>}</fieldset>
    </div><p className="form-hint">D(x) dùng phân vị tuyến tính; V(x) là thể tích nhận ít nhất ngưỡng x Gy. Danh sách được chuẩn hóa và lưu cùng kết quả.</p><section className="dvh-binding-panel"><div className="panel-heading"><div><p className="eyebrow">CHỌN NGUỒN GIỚI HẠN</p><h3>Đánh giá theo nguồn tham khảo</h3></div><span className="status-badge">Không tự áp dụng</span></div><div className="dvh-config-grid"><label>Nguồn tham khảo<select value={bindingSource} onChange={(event) => { const value = event.target.value as 'NONE' | 'DOSE_LIMIT' | 'PROTOCOL'; setBindingSource(value); setSelectedLimitEntryId(''); setSelectedProtocolVersionId(''); setSelectedProtocolMetricKey(''); setValidation(undefined) }}><option value="NONE">Không dùng nguồn P16/P11</option><option value="DOSE_LIMIT">Giới hạn liều đã công bố</option><option value="PROTOCOL">Quy trình QA đang dùng</option></select></label>{bindingSource === 'DOSE_LIMIT' && <label>Giới hạn liều<select value={selectedLimitEntryId} onChange={(event) => { setSelectedLimitEntryId(event.target.value); setValidation(undefined) }}><option value="">Chọn giới hạn liều</option>{(doseLimitEntries.data?.items ?? []).map((entry: BiologicalLibraryEntryResource) => <option key={entry.id} value={entry.id}>{entry.name} · phiên bản {entry.version_number} · {entry.metric_key ?? '—'} · {entry.operator ?? '—'} {entry.limit_value ?? entry.upper_limit ?? '—'} {entry.unit ?? ''}</option>)}</select></label>}{bindingSource === 'PROTOCOL' && <><label>Quy trình QA<select value={selectedProtocolVersionId} onChange={(event) => { setSelectedProtocolVersionId(event.target.value); setSelectedProtocolMetricKey(''); setValidation(undefined) }}><option value="">Chọn quy trình</option>{(activeProtocols.data?.items ?? []).map((protocol: QAProtocolResource) => <option key={protocol.id} value={protocol.id}>{protocol.name} · phiên bản {protocol.version_number}</option>)}</select></label><label>Tiêu chí đánh giá<select value={selectedProtocolMetricKey} onChange={(event) => { setSelectedProtocolMetricKey(event.target.value); setValidation(undefined) }} disabled={!selectedProtocol}><option value="">Chọn tiêu chí</option>{protocolMetricOptions.map((rule) => <option key={rule.metric_key} value={rule.metric_key}>{rule.metric_key} · {rule.rule_type} · {rule.target_value ?? rule.upper_limit ?? rule.lower_limit ?? '—'} {rule.unit}</option>)}</select></label></>}</div><p className="form-hint">Nguồn chỉ được dùng khi người thực hiện chọn rõ. Hệ thống không tự tìm, không xếp hạng và không biến tài liệu tham khảo thành chỉ định điều trị.</p>{bindingSource === 'DOSE_LIMIT' && doseLimitEntries.error && <div className="alert alert--error"><p>{errorMessage(doseLimitEntries.error)}</p></div>}{bindingSource === 'PROTOCOL' && activeProtocols.error && <div className="alert alert--error"><p>{errorMessage(activeProtocols.error)}</p></div>}</section><div className="dvh-actions"><button disabled={busy || !doseId || !structureId || !effectiveRoi} onClick={runValidation}>{validateMutation.isPending ? 'Đang kiểm tra…' : 'Kiểm tra và xem trước'}</button><button className="button-secondary" disabled={busy || !doseId || !structureId || !effectiveRoi} onClick={saveRun}>{createMutation.isPending ? 'Đang lưu…' : 'Tính và lưu kết quả'}</button></div></section>
    {validation && !validation.valid && <section className="alert alert--error"><h3>DVH không hợp lệ</h3><ul>{validation.errors.map((item, index) => <li key={`${textValue(asRecord(item).code)}-${index}`}><strong>{textValue(asRecord(item).code)}</strong> · {textValue(asRecord(item).message, 'Dữ liệu chưa đáp ứng điều kiện tính.')}</li>)}</ul></section>}
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ VÀ NGUỒN</p><h2>Kết quả DVH</h2></div><div className="page-header__actions">{activeRun && <button className="button-secondary" onClick={() => void download()}>Tải bảng số liệu</button>}</div></div><ResultPanel result={result} isPreview={Boolean(previewResult)} />
      <div className="dvh-ct-workspace"><CtPreviewPanel preview={ctPreview.data} onFrameChange={setCtFrameIndex} isPending={Boolean(selectedCtId) && ctPreview.isPending} error={ctPreview.error ? errorMessage(ctPreview.error) : undefined} onRetry={() => void ctPreview.refetch()} /></div>
      {previewResult ? <div className="dvh-provenance"><span>Bản xem trước chưa lưu</span><span>Chưa tạo lần tính mới; lịch sử vẫn giữ nguyên.</span><span>Chỉ khi chọn “Tính và lưu kết quả”, hệ thống mới tạo bản ghi lưu trữ.</span></div> : activeRun && <div className="dvh-provenance"><span>Kết quả đã lưu</span><span>Thời điểm lưu: {new Date(activeRun.created_at).toLocaleString('vi-VN')}</span><span>Thông tin nguồn và phiên bản bộ tính đã được lưu kèm kết quả.</span></div>}
    </section>
    <section className="panel dvh-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ KẾT QUẢ</p><h2>Lịch sử DVH của hồ sơ</h2></div><strong>{runs.data?.total ?? '—'}</strong></div>{runs.error ? <div className="alert alert--error"><p>{errorMessage(runs.error)}</p><button onClick={() => void runs.refetch()}>Thử lại</button></div> : runs.isPending ? <p>Đang tải lịch sử…</p> : runs.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Lần tính</th><th>Vùng ROI</th><th>Độ bao phủ</th><th>Bộ tính</th><th>Thời điểm</th><th /></tr></thead><tbody>{runs.data.items.map((run, index) => <tr key={run.id}><td><button aria-label={`Mở lần tính ${index + 1}`} className={run.id === activeRun?.id ? 'history-button history-button--selected' : 'history-button'} onClick={() => setSelectedRunId(run.id)}>Lần tính {index + 1}</button></td><td>Vùng số {run.roi_number}</td><td><span className="status-badge">{dvhStatusLabel(textValue(asRecord(run.result_snapshot.coverage).status))}</span></td><td>Đã ghi nhận</td><td>{new Date(run.created_at).toLocaleString('vi-VN')}</td><td>{run.id === activeRun?.id && <strong>Đang xem</strong>}</td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có kết quả DVH. Kiểm tra chỉ tạo bản xem trước; dùng “Tính và lưu kết quả” để lưu.</p>}</section>
  </div>
}
