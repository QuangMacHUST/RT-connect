import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  ApiClientError,
  apiClient,
  type BiologicalCalculationResource,
  type PlanComparisonChartResource,
  type PlanComparisonInput,
  type PlanComparisonResource
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type JsonRecord = Record<string, unknown>
type OptionRow = { option_id: string; label: string; calculation_id: string }
type ComparisonRow = {
  option_id: string
  label: string
  calculation_id: string
  total_dose_gy: number
  fractions: number
  dose_per_fraction_gy: number
  alpha_beta_gy: number
  bed_gy: number
  eqd2_gy: number
  is_baseline: boolean
  delta_bed_gy: number
  delta_bed_percent: number | null
  delta_bed_percent_reason: string | null
  delta_eqd2_gy: number
  delta_eqd2_percent: number | null
  delta_eqd2_percent_reason: string | null
}
type ChartCategory = { option_id: string; label: string; bed_gy: number; eqd2_gy: number; is_baseline: boolean }

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function formatNumber(value: unknown, digits = 3): string {
  return typeof value === 'number' && Number.isFinite(value)
    ? value.toLocaleString('vi-VN', { maximumFractionDigits: digits })
    : '—'
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('vi-VN')
}

function rowFrom(value: unknown): ComparisonRow | undefined {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return undefined
  const raw = value as JsonRecord
  const numericKeys = ['total_dose_gy', 'fractions', 'dose_per_fraction_gy', 'alpha_beta_gy', 'bed_gy', 'eqd2_gy', 'delta_bed_gy', 'delta_eqd2_gy']
  if (!numericKeys.every((key) => typeof raw[key] === 'number' && Number.isFinite(raw[key]))) return undefined
  const optionalNumber = (key: string) => typeof raw[key] === 'number' && Number.isFinite(raw[key]) ? raw[key] as number : null
  return {
    option_id: String(raw.option_id ?? ''), label: String(raw.label ?? ''), calculation_id: String(raw.calculation_id ?? ''),
    total_dose_gy: raw.total_dose_gy as number, fractions: raw.fractions as number, dose_per_fraction_gy: raw.dose_per_fraction_gy as number,
    alpha_beta_gy: raw.alpha_beta_gy as number, bed_gy: raw.bed_gy as number, eqd2_gy: raw.eqd2_gy as number,
    is_baseline: raw.is_baseline === true, delta_bed_gy: raw.delta_bed_gy as number, delta_bed_percent: optionalNumber('delta_bed_percent'),
    delta_bed_percent_reason: typeof raw.delta_bed_percent_reason === 'string' ? raw.delta_bed_percent_reason : null,
    delta_eqd2_gy: raw.delta_eqd2_gy as number, delta_eqd2_percent: optionalNumber('delta_eqd2_percent'),
    delta_eqd2_percent_reason: typeof raw.delta_eqd2_percent_reason === 'string' ? raw.delta_eqd2_percent_reason : null
  }
}

function rowsFrom(value: unknown): ComparisonRow[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item) => {
    const row = rowFrom(item)
    return row ? [row] : []
  })
}

function categoriesFrom(value: unknown): ChartCategory[] {
  if (!value || typeof value !== 'object' || Array.isArray(value)) return []
  const chart = value as JsonRecord
  if (!Array.isArray(chart.categories)) return []
  return chart.categories.flatMap((item) => {
    if (!item || typeof item !== 'object' || Array.isArray(item)) return []
    const raw = item as JsonRecord
    if (typeof raw.bed_gy !== 'number' || typeof raw.eqd2_gy !== 'number') return []
    return [{
      option_id: String(raw.option_id ?? ''), label: String(raw.label ?? ''), bed_gy: raw.bed_gy,
      eqd2_gy: raw.eqd2_gy, is_baseline: raw.is_baseline === true
    }]
  })
}

function calculationSummary(calculation: BiologicalCalculationResource | undefined): string {
  if (!calculation) return 'Chưa chọn calculation'
  const primary = calculation.result_snapshot.primary
  if (!primary || typeof primary !== 'object' || Array.isArray(primary)) return `${calculation.id.slice(0, 8)}… · ${calculation.model_version}`
  const value = primary as JsonRecord
  return `D ${formatNumber(value.total_dose_gy)} Gy · n ${formatNumber(value.fractions, 0)} · d ${formatNumber(value.dose_per_fraction_gy)} Gy/fx · α/β ${formatNumber(value.alpha_beta_gy)} Gy`
}

function ExportButton({ comparison, format, accessToken, organizationId, onMessage }: { comparison: PlanComparisonResource; format: 'JSON' | 'CSV'; accessToken: string; organizationId: string; onMessage: (message: string) => void }) {
  return <button className="button-secondary" onClick={async () => {
    try {
      const blob = await apiClient.downloadPlanComparison(accessToken, organizationId, comparison.id, format)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `rt-connect-plan-comparison-${comparison.id}.${format.toLowerCase()}`
      anchor.click()
      URL.revokeObjectURL(url)
      onMessage(`Đã tải export ${format} của comparison ${comparison.id.slice(0, 8)}…`)
    } catch (error) { onMessage(errorMessage(error)) }
  }}>Tải {format}</button>
}

function ComparisonChart({ categories }: { categories: ChartCategory[] }) {
  const [metric, setMetric] = useState<'bed_gy' | 'eqd2_gy'>('bed_gy')
  const maximum = Math.max(...categories.map((item) => item[metric]), 1)
  return <div className="comparison-chart-block">
    <div className="bed-chart-toolbar"><div><strong>{metric === 'bed_gy' ? 'BED giữa các phương án' : 'EQD2 giữa các phương án'}</strong><span>{categories.length} options · baseline được đánh dấu, không có xếp hạng tự động</span></div><div className="segmented-control"><button className={metric === 'bed_gy' ? 'is-active' : ''} onClick={() => setMetric('bed_gy')}>BED</button><button className={metric === 'eqd2_gy' ? 'is-active' : ''} onClick={() => setMetric('eqd2_gy')}>EQD2</button></div></div>
    <div className="comparison-bars" role="img" aria-label={`${metric === 'bed_gy' ? 'BED' : 'EQD2'} theo phương án`}>
      {categories.map((item) => <div className={`comparison-bar${item.is_baseline ? ' comparison-bar--baseline' : ''}`} key={item.option_id}><div className="comparison-bar__value">{formatNumber(item[metric])}</div><div className="comparison-bar__track"><i style={{ height: `${Math.max(3, item[metric] / maximum * 100)}%` }} /></div><strong>{item.label}</strong><small>{item.is_baseline ? 'BASELINE' : item.option_id}</small></div>)}
    </div>
  </div>
}

export function PlanComparisonPage() {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const queryClient = useQueryClient()
  const [options, setOptions] = useState<OptionRow[]>([])
  const [name, setName] = useState('P14 treatment plan comparison')
  const [baselineOptionId, setBaselineOptionId] = useState('')
  const [selectedComparisonId, setSelectedComparisonId] = useState<string>()
  const [validation, setValidation] = useState<{ valid: boolean; errors: Array<{ code: string; field: string | null; message: string }>; warnings: Array<{ code: string; field: string | null; message: string }>; preview: JsonRecord | null }>()
  const [chartPreview, setChartPreview] = useState<PlanComparisonChartResource>()
  const [message, setMessage] = useState<string>()
  const [idempotencyKey, setIdempotencyKey] = useState(() => `p14-${crypto.randomUUID()}`)

  const bootstrap = useQuery({ queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!), enabled: Boolean(accessToken), retry: false })
  const organizationId = bootstrap.data?.organization.id
  const calculations = useQuery({ queryKey: ['p14-calculations', organizationId, accessToken], queryFn: () => apiClient.biologicalCalculations(accessToken!, organizationId!), enabled: Boolean(accessToken && organizationId), retry: false })
  const completedCalculations = useMemo(() => calculations.data?.items.filter((item) => item.calculation_type === 'BED_EQD2' && item.status === 'COMPLETED') ?? [], [calculations.data?.items])
  const comparisons = useQuery({ queryKey: ['p14-comparisons', organizationId, accessToken], queryFn: () => apiClient.planComparisons(accessToken!, organizationId!), enabled: Boolean(accessToken && organizationId), retry: false })
  const selectedComparison = comparisons.data?.items.find((item) => item.id === selectedComparisonId) ?? comparisons.data?.items[0]
  const result = chartPreview ? selectedComparison && { ...selectedComparison.result_snapshot, table_rows: chartPreview.table_rows, chart_dataset: chartPreview.chart_dataset } : selectedComparison?.result_snapshot
  const resultRows = rowsFrom(result?.table_rows)
  const chartCategories = categoriesFrom(result?.chart_dataset)
  const suggestedOptions = useMemo(() => completedCalculations.slice(0, 2).map((calculation, index) => ({ option_id: `option-${String.fromCharCode(97 + index)}`, label: `Phương án ${String.fromCharCode(65 + index)}`, calculation_id: calculation.id })), [completedCalculations])
  const activeOptions = options.length ? options : suggestedOptions
  const activeBaselineOptionId = baselineOptionId || activeOptions[0]?.option_id || ''

  const body = (): PlanComparisonInput | undefined => {
    if (activeOptions.length < 2) { setMessage('Cần ít nhất hai calculation BED/EQD2 khác nhau để so sánh.'); return undefined }
    if (!activeBaselineOptionId) { setMessage('Cần chọn một phương án baseline.'); return undefined }
    if (activeOptions.some((item) => !item.label.trim() || !item.calculation_id)) { setMessage('Mỗi phương án cần có tên và calculation snapshot.'); return undefined }
    return { name: name.trim(), idempotency_key: idempotencyKey, baseline_option_id: activeBaselineOptionId, options: activeOptions }
  }
  const validateMutation = useMutation({
    mutationFn: (request: PlanComparisonInput) => apiClient.validatePlanComparison(accessToken!, organizationId!, request),
    onSuccess: (response) => { setValidation({ valid: response.valid, errors: response.errors, warnings: response.warnings, preview: response.preview }); setMessage(response.valid ? 'Comparison hợp lệ; validate-only không ghi snapshot.' : 'Comparison chưa hợp lệ; sửa các trường được báo rồi kiểm tra lại.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const calculateMutation = useMutation({
    mutationFn: (request: PlanComparisonInput) => apiClient.createPlanComparison(accessToken!, organizationId!, request),
    onSuccess: async (comparison) => { setSelectedComparisonId(comparison.id); setChartPreview(undefined); setValidation(undefined); setMessage(`Đã lưu comparison snapshot ${comparison.id.slice(0, 8)}…; baseline và source calculations được khóa.`); setIdempotencyKey(`p14-${crypto.randomUUID()}`); await queryClient.invalidateQueries({ queryKey: ['p14-comparisons', organizationId] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const chartMutation = useMutation({
    mutationFn: (order: string[]) => apiClient.planComparisonChart(accessToken!, organizationId!, selectedComparison!.id, order),
    onSuccess: (preview) => { setChartPreview(preview); setMessage('Đã dựng chart/table preview theo thứ tự mới; baseline không thay đổi và history không bị ghi đè.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cloneMutation = useMutation({
    mutationFn: () => apiClient.clonePlanComparison(accessToken!, organizationId!, selectedComparison!.id, { idempotency_key: idempotencyKey, name: `${selectedComparison!.name} (clone)` }),
    onSuccess: async (comparison) => { setSelectedComparisonId(comparison.id); setChartPreview(undefined); setMessage(`Đã clone comparison thành ${comparison.name}.`); setIdempotencyKey(`p14-${crypto.randomUUID()}`); await queryClient.invalidateQueries({ queryKey: ['p14-comparisons', organizationId] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const busy = validateMutation.isPending || calculateMutation.isPending || chartMutation.isPending || cloneMutation.isPending
  const moveOption = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= activeOptions.length) return
    const next = [...activeOptions]
    const [item] = next.splice(index, 1)
    next.splice(target, 0, item)
    setOptions(next)
    setChartPreview(undefined)
  }
  const addOption = () => {
    if (activeOptions.length >= 10) { setMessage('P14 giới hạn tối đa 10 phương án; không tự cắt bớt danh sách.'); return }
    const unused = completedCalculations.find((item) => !activeOptions.some((option) => option.calculation_id === item.id)) ?? completedCalculations[0]
    const nextId = `option-${String.fromCharCode(97 + activeOptions.length)}`
    setOptions([...activeOptions, { option_id: nextId, label: `Phương án ${String.fromCharCode(65 + activeOptions.length)}`, calculation_id: unused?.id ?? '' }])
  }

  if (bootstrap.isPending) return <main className="auth-state">Đang tải Plan Comparison…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở Plan Comparison</h1><p>{errorMessage(bootstrap.error)}</p><Link className="button-link" to="/app/biological">Quay lại Biological Toolkit</Link></section></div>

  return <div className="page comparison-page">
    <header className="page-header"><div><p className="eyebrow">P14 · MOD-12 · BIOLOGICAL TOOLKIT</p><h1>So sánh phác đồ xạ trị</h1><p>So sánh các calculation BED/EQD2 đã lưu trong cùng context; không tự xếp hạng và không tạo prescription.</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/biological">Biological Hub</Link><span className="status-badge">INDEPENDENT COMPARISON</span></div></header>
    <section className="biological-notice" role="note"><strong>Same context required</strong><span>Tất cả options phải dùng cùng scenario revision, tissue context, model key/version. Khác alpha/beta được tính riêng và cảnh báo; % của baseline bằng 0 là null có lý do, không phải 0 hay Infinity.</span></section>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {(calculations.error || comparisons.error) && <section className="alert alert--error" role="alert"><h2>Không tải được dữ liệu P14</h2><p>{errorMessage(calculations.error ?? comparisons.error)}</p><button onClick={() => void Promise.all([calculations.refetch(), comparisons.refetch()])}>Thử lại</button></section>}
    {!calculations.isPending && !completedCalculations.length && <section className="panel empty-state"><h2>Cần calculation BED/EQD2 trước</h2><p>P14 không tự tính lại dữ liệu và không tạo option giả. Hãy tạo ít nhất hai calculation đã COMPLETED ở P13, cùng một scenario revision.</p><Link className="button-link" to="/app/biological/bed-eqd2">Mở BED &amp; EQD2 Calculator</Link></section>}
    <section className="comparison-workspace-grid">
      <section className="panel comparison-editor-panel"><div className="panel-heading"><div><p className="eyebrow">COMPARISON INPUT</p><h2>Danh sách phương án</h2></div><span className="status-badge">{activeOptions.length}/10 OPTIONS</span></div>
        <label className="comparison-name-field">Tên comparison<input value={name} onChange={(event) => setName(event.target.value)} /></label>
        <div className="table-wrap"><table className="comparison-option-table"><thead><tr><th>ID ổn định</th><th>Tên hiển thị</th><th>P13 calculation snapshot</th><th>Input snapshot</th><th>Thứ tự</th><th>Xóa</th></tr></thead><tbody>{activeOptions.map((option, index) => { const calculation = completedCalculations.find((item) => item.id === option.calculation_id); return <tr key={option.option_id}><td><code>{option.option_id}</code></td><td><input value={option.label} onChange={(event) => setOptions(activeOptions.map((item) => item.option_id === option.option_id ? { ...item, label: event.target.value } : item))} /></td><td><select value={option.calculation_id} onChange={(event) => setOptions(activeOptions.map((item) => item.option_id === option.option_id ? { ...item, calculation_id: event.target.value } : item))}><option value="">Chọn snapshot…</option>{completedCalculations.map((item) => <option value={item.id} key={item.id}>{item.id.slice(0, 8)}… · {item.model_version}</option>)}</select></td><td><small>{calculationSummary(calculation)}</small><span className="table-subtitle">{calculation ? `rev ${calculation.scenario_revision_id.slice(0, 8)}…` : '—'}</span></td><td><div className="table-actions"><button className="button-secondary" disabled={index === 0 || busy} onClick={() => moveOption(index, -1)} aria-label={`Đưa ${option.label} lên`}>↑</button><button className="button-secondary" disabled={index === activeOptions.length - 1 || busy} onClick={() => moveOption(index, 1)} aria-label={`Đưa ${option.label} xuống`}>↓</button></div></td><td><button className="button-secondary" disabled={activeOptions.length <= 2 || busy} onClick={() => { const next = activeOptions.filter((item) => item.option_id !== option.option_id); setOptions(next); if (activeBaselineOptionId === option.option_id) setBaselineOptionId(next[0]?.option_id ?? '') }}>Xóa</button></td></tr> })}</tbody></table></div>
        <div className="comparison-editor-actions"><button className="button-secondary" disabled={activeOptions.length >= 10 || busy || !completedCalculations.length} onClick={addOption}>+ Thêm option</button><label className="comparison-baseline-field">Baseline<select value={activeBaselineOptionId} onChange={(event) => setBaselineOptionId(event.target.value)}><option value="">Chọn baseline…</option>{activeOptions.map((item) => <option key={item.option_id} value={item.option_id}>{item.label} · {item.option_id}</option>)}</select></label></div>
        <p className="form-hint">Đổi thứ tự chỉ đổi presentation order. baseline luôn tham chiếu bằng option_id ổn định; không dùng vị trí cột làm baseline.</p>
        <div className="comparison-actions"><button disabled={busy || activeOptions.length < 2} onClick={() => { const request = body(); if (request) validateMutation.mutate(request) }}>Validate only</button><button disabled={busy || activeOptions.length < 2} onClick={() => { const request = body(); if (request) calculateMutation.mutate(request) }}>Calculate &amp; save comparison</button></div>
        {validation && <section className={validation.valid ? 'bed-validation bed-validation--ok' : 'bed-validation bed-validation--error'}><strong>{validation.valid ? 'VALIDATION OK' : 'VALIDATION FAILED'}</strong>{validation.errors.length ? <ul>{validation.errors.map((item, index) => <li key={`${item.code}-${index}`}><strong>{item.field ?? 'comparison'}</strong>: {item.message} <code>{item.code}</code></li>)}</ul> : <p>{validation.warnings.length ? validation.warnings.map((item) => `${item.message} (${item.code})`).join(' | ') : `Preview không ghi database · ${String(validation.preview?.dataset_sha256 ?? 'checksum pending')}`}</p>}</section>}
      </section>
      <aside className="panel comparison-context-panel"><div className="panel-heading"><div><p className="eyebrow">COMPATIBILITY</p><h2>Context kiểm tra</h2></div></div>{activeOptions.length ? <ul className="comparison-context-list"><li><strong>Scenario revision</strong><span>{completedCalculations.find((item) => item.id === activeOptions[0]?.calculation_id)?.scenario_revision_id ?? 'Chưa chọn'}</span></li><li><strong>Model</strong><span>{completedCalculations.find((item) => item.id === activeOptions[0]?.calculation_id)?.model_version ?? 'Chưa chọn'}</span></li><li><strong>Options</strong><span>{activeOptions.length} · yêu cầu 2–10</span></li><li><strong>Source</strong><span>P13 immutable calculation snapshots</span></li></ul> : <p className="empty-state">Chọn calculation snapshot để bắt đầu.</p>}<div className="comparison-warning-box"><strong>Không dùng để xếp hạng</strong><span>Khác alpha/beta chỉ là cảnh báo tương thích. P14 hiển thị chênh lệch số học, không kết luận phương án tốt hơn.</span></div></aside>
    </section>
    {selectedComparison && resultRows.length ? <section className="panel comparison-result-panel"><div className="panel-heading"><div><p className="eyebrow">RESULT SNAPSHOT · {selectedComparison.status}</p><h2>{selectedComparison.name}</h2></div><div className="comparison-result-actions"><ExportButton comparison={selectedComparison} format="JSON" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /><ExportButton comparison={selectedComparison} format="CSV" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /><button className="button-secondary" disabled={busy} onClick={() => cloneMutation.mutate()}>Clone comparison</button></div></div><div className="comparison-result-meta"><span>Baseline: <strong>{String(result?.baseline_option_id ?? '—')}</strong></span><span>Model: <code>{selectedComparison.model_key} · {selectedComparison.model_version}</code></span><span>Revision: <code>{selectedComparison.scenario_revision_id}</code></span><span>Checksum: <code>{String((result?.chart_dataset as JsonRecord | undefined)?.dataset_sha256 ?? '—')}</code></span></div>{selectedComparison.warning_snapshot.length > 0 && <div className="alert alert--warning"><p>{selectedComparison.warning_snapshot.map((item) => String(item.message ?? 'Comparison warning')).join(' ')}</p></div>}<div className="table-wrap"><table className="comparison-result-table"><thead><tr><th>Option</th><th>D / n / d</th><th>α/β</th><th>BED</th><th>Δ BED</th><th>Δ BED %</th><th>EQD2</th><th>Δ EQD2</th><th>Δ EQD2 %</th></tr></thead><tbody>{resultRows.map((row) => <tr className={row.is_baseline ? 'is-baseline' : undefined} key={row.option_id}><td><strong>{row.label}</strong><span className="table-subtitle">{row.is_baseline ? 'BASELINE · ' : ''}{row.option_id}</span></td><td>{formatNumber(row.total_dose_gy)} / {formatNumber(row.fractions, 0)} / {formatNumber(row.dose_per_fraction_gy)}</td><td>{formatNumber(row.alpha_beta_gy)}</td><td>{formatNumber(row.bed_gy)}</td><td>{formatNumber(row.delta_bed_gy)}</td><td>{row.delta_bed_percent === null ? <span title="Baseline bằng 0">null <small>{row.delta_bed_percent_reason}</small></span> : `${formatNumber(row.delta_bed_percent)}%`}</td><td>{formatNumber(row.eqd2_gy)}</td><td>{formatNumber(row.delta_eqd2_gy)}</td><td>{row.delta_eqd2_percent === null ? <span title="Baseline bằng 0">null <small>{row.delta_eqd2_percent_reason}</small></span> : `${formatNumber(row.delta_eqd2_percent)}%`}</td></tr>)}</tbody></table></div>{chartCategories.length ? <ComparisonChart categories={chartCategories} /> : null}<div className="comparison-preview-actions"><button className="button-secondary" disabled={busy} onClick={() => chartMutation.mutate(activeOptions.map((item) => item.option_id))}>Preview theo thứ tự input hiện tại</button>{chartPreview && <span className="status-badge status-badge--warning">PREVIEW · NOT PERSISTED</span>}</div></section> : <section className="panel empty-state"><h2>Chưa có comparison snapshot được chọn</h2><p>Validate trước để kiểm tra compatibility; sau đó lưu comparison để mở bảng, đồ thị, history và export.</p></section>}
    <section className="panel comparison-history-panel"><div className="panel-heading"><div><p className="eyebrow">IMMUTABLE HISTORY</p><h2>Comparison snapshots</h2></div><strong>{comparisons.data?.total ?? '—'}</strong></div>{comparisons.isPending ? <p>Đang tải history…</p> : comparisons.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Created</th><th>Tên</th><th>Baseline</th><th>Options</th><th>Model</th><th>Checksum</th></tr></thead><tbody>{comparisons.data.items.map((comparison) => { const rows = rowsFrom(comparison.result_snapshot.table_rows); return <tr className={comparison.id === selectedComparison?.id ? 'is-selected' : undefined} key={comparison.id}><td><button className="table-link" onClick={() => { setSelectedComparisonId(comparison.id); setChartPreview(undefined) }}>{formatDate(comparison.created_at)}</button><small className="table-subtitle">{comparison.id}</small></td><td>{comparison.name}</td><td><code>{String(comparison.result_snapshot.baseline_option_id ?? '—')}</code></td><td>{rows.length}</td><td>{comparison.model_version}</td><td><code>{String((comparison.result_snapshot.chart_dataset as JsonRecord | undefined)?.dataset_sha256 ?? '—')}</code></td></tr> })}</tbody></table></div> : <p className="empty-state">Chưa có comparison snapshot.</p>}</section>
    <p className="form-hint comparison-footer-note">Mọi option là một P13 snapshot đã lưu. P14 không cộng các phương án thay thế với nhau, không tự gắn vào QA/patient/TPS/PACS và calculation cũ không đổi khi scenario mới được tạo.</p>
  </div>
}
