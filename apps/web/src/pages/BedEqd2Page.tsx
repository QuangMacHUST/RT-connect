import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  ApiClientError,
  apiClient,
  type BedEqd2CalculationInput,
  type BedEqd2ChartResource,
  type BedEqd2CurveInput,
  type BiologicalCalculationResource
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type JsonRecord = Record<string, unknown>
type SourceType = NonNullable<BedEqd2CalculationInput['alpha_beta_source_type']>
type ChartPoint = {
  total_dose_gy: number
  fractions: number
  dose_per_fraction_gy: number
  alpha_beta_gy: number
  bed_gy: number
  eqd2_gy: number
}
type ChartSeries = { series_key: string; alpha_beta_gy: number; points: ChartPoint[] }
type ChartDataset = {
  parameters: JsonRecord
  series: ChartSeries[]
  point_count: number
  dataset_sha256: string
}

type FormState = {
  totalDose: string
  fractions: string
  dosePerFraction: string
  tolerance: string
  alphaBeta: string
  sourceType: SourceType
  sourceReference: string
  curveMode: 'FIXED_N' | 'FIXED_D'
  curveMin: string
  curveMax: string
  curveStep: string
  fixedN: string
  fixedD: string
  curveAlphaBetas: string
  pointLimit: string
}

const colors = ['#087785', '#d97706', '#4968a8', '#9c4f78', '#5b8c5a', '#7b61a8', '#b45309', '#0f766e']

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function emptyForm(): FormState {
  return {
    totalDose: '60', fractions: '30', dosePerFraction: '2', tolerance: '0.01', alphaBeta: '10',
    sourceType: 'USER_DEFINED', sourceReference: 'Synthetic known-answer fixture / user-defined model',
    curveMode: 'FIXED_N', curveMin: '0', curveMax: '100', curveStep: '1', fixedN: '', fixedD: '',
    curveAlphaBetas: '2, 3, 10', pointLimit: '501'
  }
}

function numberOrNull(value: string): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function numberRequired(value: string, label: string): number {
  const parsed = numberOrNull(value)
  if (parsed === null) throw new Error(`${label} phải là một số hữu hạn.`)
  return parsed
}

function parseAlphaBetas(value: string): number[] {
  if (!value.trim()) return []
  const values = value.split(',').map((item) => Number(item.trim()))
  if (values.some((item) => !Number.isFinite(item))) throw new Error('Danh sách alpha/beta có giá trị không hợp lệ.')
  return values
}

function curveFromForm(form: FormState): BedEqd2CurveInput {
  return {
    mode: form.curveMode,
    dose_min_gy: numberRequired(form.curveMin, 'D min'),
    dose_max_gy: numberRequired(form.curveMax, 'D max'),
    dose_step_gy: numberRequired(form.curveStep, 'Step'),
    fixed_n: numberOrNull(form.fixedN),
    fixed_d_gy: numberOrNull(form.fixedD),
    alpha_beta_values_gy: parseAlphaBetas(form.curveAlphaBetas),
    point_limit: Math.trunc(numberRequired(form.pointLimit, 'Point limit'))
  }
}

function formatNumber(value: unknown, digits = 6): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString('vi-VN', { maximumFractionDigits: digits })
    : '—'
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('vi-VN')
}

function statusClass(status: string): string {
  if (status === 'COMPLETED') return 'status-badge'
  if (status === 'FAILED') return 'status-badge machine-status--fail'
  return 'status-badge status-badge--warning'
}

function chartDatasetFrom(value: unknown): ChartDataset | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
  const raw = value as JsonRecord
  const rawSeries = Array.isArray(raw.series) ? raw.series : []
  const series: ChartSeries[] = rawSeries.flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return []
    const record = item as JsonRecord
    const alpha = typeof record.alpha_beta_gy === 'number' ? record.alpha_beta_gy : undefined
    const points = Array.isArray(record.points) ? record.points.flatMap((point) => {
      if (!point || typeof point !== 'object' || Array.isArray(point)) return []
      const p = point as JsonRecord
      const keys = ['total_dose_gy', 'fractions', 'dose_per_fraction_gy', 'alpha_beta_gy', 'bed_gy', 'eqd2_gy']
      if (!keys.every((key) => typeof p[key] === 'number' && Number.isFinite(p[key]))) return []
      return [{
        total_dose_gy: p.total_dose_gy as number,
        fractions: p.fractions as number,
        dose_per_fraction_gy: p.dose_per_fraction_gy as number,
        alpha_beta_gy: p.alpha_beta_gy as number,
        bed_gy: p.bed_gy as number,
        eqd2_gy: p.eqd2_gy as number
      }]
    }) : []
    if (alpha === undefined || !points.length) return []
    return [{ series_key: String(record.series_key ?? `alpha-beta-${alpha}`), alpha_beta_gy: alpha, points }]
  })
  if (!series.length || typeof raw.dataset_sha256 !== 'string') return undefined
  return {
    parameters: raw.parameters && typeof raw.parameters === 'object' && !Array.isArray(raw.parameters) ? raw.parameters as JsonRecord : {},
    series,
    point_count: typeof raw.point_count === 'number' ? raw.point_count : series.reduce((sum, item) => sum + item.points.length, 0),
    dataset_sha256: raw.dataset_sha256
  }
}

function primaryFrom(run: BiologicalCalculationResource | undefined): JsonRecord | undefined {
  const result = run?.result_snapshot
  if (!result || typeof result.primary !== 'object' || result.primary === null || Array.isArray(result.primary)) return undefined
  return result.primary as JsonRecord
}

function ChartPanel({ dataset, primaryDose }: { dataset: ChartDataset; primaryDose: number | undefined }) {
  const [metric, setMetric] = useState<'bed_gy' | 'eqd2_gy'>('bed_gy')
  const points = dataset.series.flatMap((item) => item.points)
  const xValues = points.map((point) => point.total_dose_gy)
  const yValues = points.map((point) => point[metric])
  const xMin = Math.min(...xValues)
  const xMax = Math.max(...xValues)
  const yMax = Math.max(...yValues, 1) * 1.08
  const width = 760
  const height = 300
  const left = 58
  const right = 18
  const top = 20
  const bottom = 42
  const plotWidth = width - left - right
  const plotHeight = height - top - bottom
  const x = (value: number) => left + ((value - xMin) / Math.max(xMax - xMin, 1)) * plotWidth
  const y = (value: number) => top + plotHeight - (value / yMax) * plotHeight
  const markerX = primaryDose === undefined ? undefined : x(Math.min(Math.max(primaryDose, xMin), xMax))

  return <div className="bed-chart-block">
    <div className="bed-chart-toolbar"><div><strong>{metric === 'bed_gy' ? 'BED theo D' : 'EQD2 theo D'}</strong><span>{formatNumber(dataset.point_count, 0)} points · checksum {dataset.dataset_sha256.slice(0, 16)}…</span></div><div className="segmented-control"><button className={metric === 'bed_gy' ? 'is-active' : ''} onClick={() => setMetric('bed_gy')}>BED</button><button className={metric === 'eqd2_gy' ? 'is-active' : ''} onClick={() => setMetric('eqd2_gy')}>EQD2</button></div></div>
    <div className="bed-chart-scroll"><svg className="bed-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label={`${metric === 'bed_gy' ? 'BED' : 'EQD2'} theo tổng liều D`}>
      {[0, .25, .5, .75, 1].map((fraction) => <g key={fraction}><line x1={left} x2={width - right} y1={y(yMax * fraction)} y2={y(yMax * fraction)} /><text x={left - 8} y={y(yMax * fraction) + 4} textAnchor="end">{formatNumber(yMax * fraction, 0)}</text></g>)}
      <line className="bed-chart-axis" x1={left} x2={width - right} y1={height - bottom} y2={height - bottom} /><line className="bed-chart-axis" x1={left} x2={left} y1={top} y2={height - bottom} />
      {markerX !== undefined && <g><line className="bed-chart-marker" x1={markerX} x2={markerX} y1={top} y2={height - bottom} /><text className="bed-chart-marker-label" x={markerX + 5} y={top + 14}>primary D</text></g>}
      {dataset.series.map((series, index) => <g key={series.series_key}><polyline fill="none" stroke={colors[index % colors.length]} points={series.points.map((point) => `${x(point.total_dose_gy)},${y(point[metric])}`).join(' ')} /><circle fill={colors[index % colors.length]} cx={x(series.points[0].total_dose_gy)} cy={y(series.points[0][metric])} r="2" /></g>)}
      <text x={width / 2} y={height - 8} textAnchor="middle">Tổng liều D (Gy)</text><text transform={`translate(14 ${height / 2}) rotate(-90)`} textAnchor="middle">{metric === 'bed_gy' ? 'BED (Gy)' : 'EQD2 (Gy)'}</text>
    </svg></div>
    <div className="bed-chart-legend">{dataset.series.map((series, index) => <span key={series.series_key}><i style={{ background: colors[index % colors.length] }} /> α/β {formatNumber(series.alpha_beta_gy)} Gy</span>)}</div>
  </div>
}

function ExportButton({ run, format, accessToken, organizationId, onMessage }: { run: BiologicalCalculationResource; format: 'JSON' | 'CSV'; accessToken: string; organizationId: string; onMessage: (message: string) => void }) {
  return <button className="button-secondary" onClick={async () => {
    try {
      const blob = await apiClient.downloadBedEqd2(accessToken, organizationId, run.id, format)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `rt-connect-bed-eqd2-${run.id}.${format.toLowerCase()}`
      anchor.click()
      URL.revokeObjectURL(url)
      onMessage(`Đã tải export ${format} của calculation ${run.id.slice(0, 8)}…`)
    } catch (error) { onMessage(errorMessage(error)) }
  }}>Tải {format}</button>
}

export function BedEqd2Page() {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const queryClient = useQueryClient()
  const [selectedScenarioId, setSelectedScenarioId] = useState<string>()
  const [selectedRevisionId, setSelectedRevisionId] = useState<string>()
  const [selectedCalculationId, setSelectedCalculationId] = useState<string>()
  const [form, setForm] = useState<FormState>(() => emptyForm())
  const [validation, setValidation] = useState<{ valid: boolean; errors: Array<{ code: string; field: string | null; message: string }>; preview: JsonRecord | null }>()
  const [chartPreview, setChartPreview] = useState<BedEqd2ChartResource>()
  const [message, setMessage] = useState<string>()
  const [idempotencyKey, setIdempotencyKey] = useState(() => `p13-${crypto.randomUUID()}`)

  const bootstrap = useQuery({ queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!), enabled: Boolean(accessToken), retry: false })
  const organizationId = bootstrap.data?.organization.id
  const scenarios = useQuery({
    queryKey: ['p13-saved-scenarios', organizationId, accessToken],
    queryFn: () => apiClient.biologicalScenarios(accessToken!, organizationId!, { status: 'SAVED' }),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const activeScenarioId = scenarios.data?.items.some((item) => item.id === selectedScenarioId)
    ? selectedScenarioId
    : scenarios.data?.items[0]?.id
  const detail = useQuery({ queryKey: ['p13-scenario', organizationId, activeScenarioId, accessToken], queryFn: () => apiClient.biologicalScenario(accessToken!, organizationId!, activeScenarioId!), enabled: Boolean(accessToken && organizationId && activeScenarioId), retry: false })
  const revisions = useQuery({ queryKey: ['p13-revisions', organizationId, activeScenarioId, accessToken], queryFn: () => apiClient.biologicalScenarioRevisions(accessToken!, organizationId!, activeScenarioId!), enabled: Boolean(accessToken && organizationId && activeScenarioId), retry: false })
  const savedRevisions = revisions.data?.filter((item) => item.status === 'SAVED') ?? []
  const activeRevisionId = savedRevisions.some((item) => item.id === selectedRevisionId) ? selectedRevisionId : savedRevisions[0]?.id
  const calculations = useQuery({ queryKey: ['p13-calculations', organizationId, activeScenarioId, accessToken], queryFn: () => apiClient.biologicalCalculations(accessToken!, organizationId!, activeScenarioId!), enabled: Boolean(accessToken && organizationId && activeScenarioId), retry: false })
  const selectedCalculation = useMemo(() => calculations.data?.items.find((item) => item.id === selectedCalculationId) ?? calculations.data?.items[0], [calculations.data?.items, selectedCalculationId])
  const persistedDataset = chartDatasetFrom(selectedCalculation?.result_snapshot.chart_dataset)
  const activeDataset = chartPreview?.chart_dataset ? chartDatasetFrom(chartPreview.chart_dataset) : persistedDataset
  const primary = primaryFrom(selectedCalculation)

  const body = (): BedEqd2CalculationInput | undefined => {
    try {
      if (!activeScenarioId || !activeRevisionId) throw new Error('Cần chọn một scenario SAVED và một revision SAVED trước khi tính.')
      const curve = curveFromForm(form)
      const fractions = numberOrNull(form.fractions)
      if (fractions !== null && !Number.isInteger(fractions)) throw new Error('n phải là số nguyên dương.')
      return {
        scenario_revision_id: activeRevisionId,
        idempotency_key: idempotencyKey,
        total_dose_gy: numberOrNull(form.totalDose),
        fractions: fractions === null ? null : fractions,
        dose_per_fraction_gy: numberOrNull(form.dosePerFraction),
        consistency_tolerance_gy: numberRequired(form.tolerance, 'Tolerance'),
        alpha_beta_gy: numberRequired(form.alphaBeta, 'Alpha/beta'),
        alpha_beta_source_type: form.sourceType,
        alpha_beta_source_reference: form.sourceReference,
        curve
      }
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Input không hợp lệ.'); return undefined }
  }

  const validateMutation = useMutation({
    mutationFn: (request: BedEqd2CalculationInput) => apiClient.validateBedEqd2(accessToken!, organizationId!, activeScenarioId!, request),
    onSuccess: (result) => { setValidation({ valid: result.valid, errors: result.errors, preview: result.preview }); setMessage(result.valid ? 'Input hợp lệ; validate-only không ghi calculation vào database.' : 'Input chưa hợp lệ; sửa các trường được đánh dấu rồi kiểm tra lại.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const calculateMutation = useMutation({
    mutationFn: (request: BedEqd2CalculationInput) => apiClient.createBedEqd2Calculation(accessToken!, organizationId!, activeScenarioId!, request),
    onSuccess: (run) => { setSelectedCalculationId(run.id); setChartPreview(undefined); setValidation(undefined); setMessage(`Đã lưu BED/EQD2 calculation snapshot ${run.id.slice(0, 8)}…; input revision được khóa theo snapshot.`); setIdempotencyKey(`p13-${crypto.randomUUID()}`); void queryClient.invalidateQueries({ queryKey: ['p13-calculations', organizationId, activeScenarioId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const chartMutation = useMutation({
    mutationFn: (request: BedEqd2CurveInput) => apiClient.bedEqd2Chart(accessToken!, organizationId!, selectedCalculation!.id, request),
    onSuccess: (result) => { setChartPreview(result); setMessage('Đã dựng chart preview từ calculation snapshot; preview không ghi đè history.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const busy = validateMutation.isPending || calculateMutation.isPending || chartMutation.isPending

  if (bootstrap.isPending) return <main className="auth-state">Đang tải BED/EQD2 Calculator…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở BED/EQD2 Calculator</h1><p>{errorMessage(bootstrap.error)}</p><Link className="button-link" to="/app/biological">Quay lại Biological Toolkit</Link></section></div>

  return <div className="page bed-page">
    <header className="page-header"><div><p className="eyebrow">P13 · MOD-11 · BIOLOGICAL TOOLKIT</p><h1>BED &amp; EQD2 Calculator</h1><p>Linear-quadratic estimate từ một fractionation snapshot tường minh; không phải prescription và không phải QA result.</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/biological">Biological Hub</Link><span className="status-badge">INDEPENDENT CALCULATION</span></div></header>
    <section className="biological-notice bed-safety-notice" role="note"><strong>Estimate / scenario only</strong><span>Không có spatial dose accumulation, không tự động liên kết QA/patient/TPS/PACS, không đưa ra khuyến nghị điều trị. Mọi kết quả lưu cùng model, source, assumptions, scenario revision và checksum dataset.</span></section>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {(scenarios.error || detail.error || revisions.error || calculations.error) && <section className="alert alert--error" role="alert"><h2>Không tải được dữ liệu P13</h2><p>{errorMessage(scenarios.error ?? detail.error ?? revisions.error ?? calculations.error)}</p><button onClick={() => void Promise.all([scenarios.refetch(), detail.refetch(), revisions.refetch(), calculations.refetch()])}>Thử lại</button></section>}
    {!scenarios.isPending && !scenarios.data?.items.length && <section className="panel empty-state"><h2>Cần scenario SAVED trước khi tính</h2><p>P13 không tự tạo scenario và không dùng dữ liệu bệnh nhân. Hãy tạo context độc lập ở Biological Hub, lưu thành SAVED rồi quay lại đây.</p><Link className="button-link" to="/app/biological">Mở Biological Hub</Link></section>}
    {scenarios.data?.items.length ? <>
      <section className="bed-workspace-grid">
        <section className="panel bed-input-panel"><div className="panel-heading"><div><p className="eyebrow">CALCULATION INPUT</p><h2>Fractionation &amp; model</h2></div><span className="status-badge">SERVER VALIDATED</span></div>
          <div className="bed-form-grid"><label>Scenario SAVED<select value={activeScenarioId ?? ''} onChange={(event) => { setSelectedScenarioId(event.target.value); setSelectedRevisionId(undefined); setSelectedCalculationId(undefined); setChartPreview(undefined) }}>{scenarios.data.items.map((item) => <option key={item.id} value={item.id}>{item.name} · {item.scenario_key}</option>)}</select></label><label>Input revision<select value={activeRevisionId ?? ''} onChange={(event) => { setSelectedRevisionId(event.target.value); setSelectedCalculationId(undefined); setChartPreview(undefined) }}>{savedRevisions.map((item) => <option key={item.id} value={item.id}>rev {item.revision_number} · {formatDate(item.created_at)}</option>)}</select></label></div>
          <div className="bed-subsection"><div className="panel-heading"><h3>Fractionation</h3><span className="form-hint">D = n × d · tolerance {form.tolerance} Gy</span></div><div className="bed-form-grid bed-form-grid--three"><label>Total dose D (Gy)<input type="number" min="0" step="any" value={form.totalDose} onChange={(event) => setForm({ ...form, totalDose: event.target.value })} /></label><label>Fractions n<input type="number" min="1" step="1" value={form.fractions} onChange={(event) => setForm({ ...form, fractions: event.target.value })} /></label><label>Dose / fraction d (Gy/fx)<input type="number" min="0" step="any" value={form.dosePerFraction} onChange={(event) => setForm({ ...form, dosePerFraction: event.target.value })} /></label></div><label className="bed-inline-field">Consistency tolerance (Gy)<input type="number" min="0.000001" step="any" value={form.tolerance} onChange={(event) => setForm({ ...form, tolerance: event.target.value })} /></label></div>
          <div className="bed-subsection"><div className="panel-heading"><h3>Alpha / beta provenance</h3><span className="form-hint">Bắt buộc source hoặc user-defined note</span></div><div className="bed-form-grid"><label>Alpha / beta (Gy)<input type="number" min="0.000001" step="any" value={form.alphaBeta} onChange={(event) => setForm({ ...form, alphaBeta: event.target.value })} /></label><label>Source type<select value={form.sourceType} onChange={(event) => setForm({ ...form, sourceType: event.target.value as SourceType })}><option value="USER_DEFINED">USER_DEFINED</option><option value="REFERENCE">REFERENCE</option></select></label><label className="bed-form-grid__wide">Source / reference note<input value={form.sourceReference} onChange={(event) => setForm({ ...form, sourceReference: event.target.value })} placeholder="DOI, guideline, hoặc user-defined note" /></label></div></div>
          <div className="bed-subsection"><div className="panel-heading"><h3>Curve controls</h3><span className="form-hint">Tổng số điểm bao gồm tất cả alpha/beta series</span></div><div className="bed-form-grid"><label>Curve mode<select value={form.curveMode} onChange={(event) => setForm({ ...form, curveMode: event.target.value as FormState['curveMode'] })}><option value="FIXED_N">FIXED_N · giữ n</option><option value="FIXED_D">FIXED_D · giữ d</option></select></label><label>D min (Gy)<input type="number" min="0" step="any" value={form.curveMin} onChange={(event) => setForm({ ...form, curveMin: event.target.value })} /></label><label>D max (Gy)<input type="number" min="0" step="any" value={form.curveMax} onChange={(event) => setForm({ ...form, curveMax: event.target.value })} /></label><label>Step (Gy)<input type="number" min="0.000001" step="any" value={form.curveStep} onChange={(event) => setForm({ ...form, curveStep: event.target.value })} /></label><label>Fixed n <span className="form-hint">trống = n input</span><input type="number" min="1" step="1" value={form.fixedN} onChange={(event) => setForm({ ...form, fixedN: event.target.value })} /></label><label>Fixed d (Gy) <span className="form-hint">trống = d input</span><input type="number" min="0" step="any" value={form.fixedD} onChange={(event) => setForm({ ...form, fixedD: event.target.value })} /></label><label className="bed-form-grid__wide">Alpha / beta curves (Gy)<input value={form.curveAlphaBetas} onChange={(event) => setForm({ ...form, curveAlphaBetas: event.target.value })} placeholder="2, 3, 10" /><span className="form-hint">Để trống sẽ dùng alpha/beta chính. Tối đa 10 series.</span></label><label>Point limit<input type="number" min="1" max="5001" step="1" value={form.pointLimit} onChange={(event) => setForm({ ...form, pointLimit: event.target.value })} /></label></div><p className="form-hint">FIXED_N tạo D = Dmin…Dmax theo step. FIXED_D chỉ tạo các điểm D = n × d với n nguyên; step phải là bội nguyên của d.</p></div>
          <div className="bed-actions"><button disabled={busy || !activeRevisionId} onClick={() => { const request = body(); if (request) validateMutation.mutate(request) }}>Validate only</button><button disabled={busy || !activeRevisionId} onClick={() => { const request = body(); if (request) calculateMutation.mutate(request) }}>Calculate &amp; save snapshot</button></div>
          {validation && <section className={validation.valid ? 'bed-validation bed-validation--ok' : 'bed-validation bed-validation--error'}><strong>{validation.valid ? 'VALIDATION OK' : 'VALIDATION FAILED'}</strong>{validation.errors.length ? <ul>{validation.errors.map((item, index) => <li key={`${item.code}-${index}`}><strong>{item.field ?? 'input'}</strong>: {item.message} <code>{item.code}</code></li>)}</ul> : validation.preview && <p>Preview primary và checksum đã được tính nhưng chưa ghi database: <code>{String(validation.preview.chart_dataset_sha256 ?? '')}</code></p>}</section>}
        </section>
        <section className="panel bed-result-panel"><div className="panel-heading"><div><p className="eyebrow">RESULT SNAPSHOT</p><h2>BED / EQD2</h2></div>{selectedCalculation && <span className={statusClass(selectedCalculation.status)}>{selectedCalculation.status}</span>}</div>{selectedCalculation && primary ? <><div className="bed-result-values"><article><span>BED</span><strong>{formatNumber(primary.bed_gy)}</strong><small>Gy<sub>{formatNumber(primary.alpha_beta_gy)}</sub></small></article><article><span>EQD2</span><strong>{formatNumber(primary.eqd2_gy)}</strong><small>Gy</small></article></div><div className="bed-result-meta"><p><strong>Input:</strong> D {formatNumber(primary.total_dose_gy)} Gy · n {formatNumber(primary.fractions, 0)} · d {formatNumber(primary.dose_per_fraction_gy)} Gy/fx</p><p><strong>Model:</strong> {selectedCalculation.model_key} · {selectedCalculation.model_version}</p><p><strong>Scenario revision:</strong> <code>{selectedCalculation.scenario_revision_id}</code></p><p><strong>Idempotency:</strong> <code>{selectedCalculation.idempotency_key ?? '—'}</code></p></div><details><summary>Công thức &amp; provenance</summary><pre>{JSON.stringify({ formula: selectedCalculation.result_snapshot.formula, alpha_beta: selectedCalculation.result_snapshot.alpha_beta, fractionation: selectedCalculation.result_snapshot.fractionation }, null, 2)}</pre></details><div className="bed-result-actions"><ExportButton run={selectedCalculation} format="JSON" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /><ExportButton run={selectedCalculation} format="CSV" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /></div></> : <div className="empty-state"><h3>Chưa có calculation snapshot</h3><p>Validate trước để xem lỗi; sau đó Calculate &amp; save snapshot để mở kết quả và chart.</p></div>}</section>
      </section>
      {activeDataset && <section className="panel bed-chart-panel"><div className="panel-heading"><div><p className="eyebrow">CHART DATASET</p><h2>BED &amp; EQD2 theo tổng liều D</h2></div><div className="page-header__actions">{chartPreview && <span className="status-badge status-badge--warning">PREVIEW · NOT PERSISTED</span>}{selectedCalculation && <button className="button-secondary" disabled={busy} onClick={() => { try { chartMutation.mutate(curveFromForm(form)) } catch (error) { setMessage(error instanceof Error ? error.message : 'Curve không hợp lệ.') } }}>Preview curve mới</button>}</div></div><ChartPanel dataset={activeDataset} primaryDose={typeof primary?.total_dose_gy === 'number' ? primary.total_dose_gy : undefined} /><div className="table-wrap"><table className="bed-data-table"><caption>Table dùng cùng chart dataset · {activeDataset.point_count} points</caption><thead><tr><th>D (Gy)</th><th>n</th><th>d (Gy/fx)</th><th>α/β (Gy)</th><th>BED (Gy)</th><th>EQD2 (Gy)</th></tr></thead><tbody>{activeDataset.series.flatMap((series) => series.points).map((point, index) => <tr key={`${point.alpha_beta_gy}-${point.total_dose_gy}-${index}`}><td>{formatNumber(point.total_dose_gy)}</td><td>{formatNumber(point.fractions, 0)}</td><td>{formatNumber(point.dose_per_fraction_gy)}</td><td>{formatNumber(point.alpha_beta_gy)}</td><td>{formatNumber(point.bed_gy)}</td><td>{formatNumber(point.eqd2_gy)}</td></tr>)}</tbody></table></div></section>}
      <section className="panel bed-history-panel"><div className="panel-heading"><div><p className="eyebrow">IMMUTABLE HISTORY</p><h2>Calculation snapshots</h2></div><strong>{calculations.data?.total ?? '—'}</strong></div>{calculations.isPending ? <p>Đang tải history…</p> : calculations.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Created</th><th>Scenario revision</th><th>Model</th><th>Status</th><th>Dataset checksum</th><th>Export</th></tr></thead><tbody>{calculations.data.items.map((run) => { const dataset = chartDatasetFrom(run.result_snapshot.chart_dataset); return <tr key={run.id} className={run.id === selectedCalculation?.id ? 'is-selected' : undefined}><td><button className="table-link" onClick={() => { setSelectedCalculationId(run.id); setChartPreview(undefined) }}>{formatDate(run.created_at)}</button><small className="table-subtitle">{run.id}</small></td><td><code>{run.scenario_revision_id}</code></td><td>{run.model_key}<small className="table-subtitle">{run.model_version}</small></td><td><span className={statusClass(run.status)}>{run.status}</span></td><td><code>{dataset?.dataset_sha256 ?? '—'}</code></td><td><div className="table-actions"><ExportButton run={run} format="JSON" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /><ExportButton run={run} format="CSV" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /></div></td></tr> })}</tbody></table></div> : <p className="empty-state">Chưa có calculation snapshot trong scenario này.</p>}</section>
      <p className="form-hint bed-footer-note">P13 dùng mô hình LQ cho mục đích ước tính. Giá trị hiển thị được làm tròn ở lớp trình bày; engine không làm tròn trước phép tính. Calculation cũ không đổi khi scenario được clone hoặc revision mới được tạo.</p>
    </> : null}
  </div>
}
