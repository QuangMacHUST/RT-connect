import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import {
  ApiClientError,
  apiClient,
  type FractionCompensationInput,
  type P15RunResource,
  type P15ValidationResource,
  type ReIrradiationCourseInput,
  type ReIrradiationInput,
  type ReIrradiationTissueDoseInput
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type Mode = 'REIRRADIATION' | 'FRACTION_COMPENSATION'
type JsonRecord = Record<string, unknown>
type SourceType = 'USER_DEFINED' | 'REFERENCE'
type TissueDraft = {
  tissueKey: string
  doseMetric: string
  totalDose: string
  fractions: string
  dosePerFraction: string
  alphaBeta: string
  sourceType: SourceType
  sourceReference: string
}
type CourseDraft = {
  courseId: string
  label: string
  isPrior: boolean
  startDate: string
  endDate: string
  recoveryFraction: string
  recoverySourceType: SourceType
  recoverySourceReference: string
  tissues: TissueDraft[]
}
type AlternativeDraft = { alternativeId: string; label: string; remaining: string }

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  if (error instanceof Error) return error.message
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function record(value: unknown): JsonRecord | undefined {
  return value && typeof value === 'object' && !Array.isArray(value) ? value as JsonRecord : undefined
}

function records(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.flatMap((item) => { const itemRecord = record(item); return itemRecord ? [itemRecord] : [] }) : []
}

function numberValue(value: unknown): number | undefined {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function formatNumber(value: unknown, digits = 4): string {
  const parsed = numberValue(value)
  return parsed === undefined ? '—' : parsed.toLocaleString('vi-VN', { maximumFractionDigits: digits })
}

function formatDate(value: string): string {
  return new Date(value).toLocaleString('vi-VN')
}

function statusClass(status: string): string {
  if (status === 'COMPLETED') return 'status-badge'
  if (status === 'FAILED') return 'status-badge machine-status--fail'
  return 'status-badge status-badge--warning'
}

function parseDoses(value: string, field: string, allowEmpty = false): number[] {
  const tokens = value.split(/[\s,;]+/).map((item) => item.trim()).filter(Boolean)
  if (!tokens.length && allowEmpty) return []
  if (!tokens.length) throw new Error(`${field} cần ít nhất một giá trị.`)
  const parsed = tokens.map((item) => Number(item))
  if (parsed.some((item) => !Number.isFinite(item) || item < 0)) throw new Error(`${field} chỉ được chứa số hữu hạn không âm.`)
  return parsed
}

function numberRequired(value: string, field: string): number {
  const parsed = Number(value)
  if (!value.trim() || !Number.isFinite(parsed)) throw new Error(`${field} phải là một số hữu hạn.`)
  return parsed
}

function newTissue(index = 0): TissueDraft {
  return {
    tissueKey: index === 0 ? 'TARGET' : `OAR-${index}`,
    doseMetric: index === 0 ? 'TOTAL' : 'MEAN',
    totalDose: index === 0 ? '60' : '30',
    fractions: index === 0 ? '30' : '30',
    dosePerFraction: '2',
    alphaBeta: index === 0 ? '10' : '3',
    sourceType: 'USER_DEFINED',
    sourceReference: 'User-defined P15 scenario assumption'
  }
}

function newCourse(index: number): CourseDraft {
  return {
    courseId: index === 0 ? 'course-prior' : 'course-current',
    label: index === 0 ? 'Prior course' : 'Current course',
    isPrior: index === 0,
    startDate: index === 0 ? '2020-01-01' : '2026-01-01',
    endDate: index === 0 ? '2020-02-15' : '2026-02-15',
    recoveryFraction: index === 0 ? '0.5' : '0',
    recoverySourceType: 'USER_DEFINED',
    recoverySourceReference: 'User-defined recovery assumption',
    tissues: [newTissue()]
  }
}

function initialCourses(): CourseDraft[] {
  return [newCourse(0), newCourse(1)]
}

function initialAlternatives(): AlternativeDraft[] {
  return [
    { alternativeId: 'original-remaining', label: 'Continue original schedule', remaining: '2, 2, 2' },
    { alternativeId: 'alternative-1', label: 'Alternative remaining schedule', remaining: '2.5, 2.5, 1' }
  ]
}

function buildTissue(tissue: TissueDraft): ReIrradiationTissueDoseInput {
  return {
    tissue_key: tissue.tissueKey,
    dose_metric: tissue.doseMetric,
    dose_unit: 'Gy',
    total_dose_gy: numberRequired(tissue.totalDose, `${tissue.tissueKey} total dose`),
    fractions: numberRequired(tissue.fractions, `${tissue.tissueKey} fractions`),
    dose_per_fraction_gy: numberRequired(tissue.dosePerFraction, `${tissue.tissueKey} dose/fraction`),
    alpha_beta_gy: numberRequired(tissue.alphaBeta, `${tissue.tissueKey} alpha/beta`),
    alpha_beta_source_type: tissue.sourceType,
    alpha_beta_source_reference: tissue.sourceReference
  }
}

function buildCourse(course: CourseDraft, recoveryMode: boolean): ReIrradiationCourseInput {
  return {
    course_id: course.courseId,
    label: course.label,
    is_prior: course.isPrior,
    start_date: course.startDate || null,
    end_date: course.endDate || null,
    tissue_doses: course.tissues.map(buildTissue),
    recovery_fraction: recoveryMode ? (course.recoveryFraction.trim() ? numberRequired(course.recoveryFraction, `${course.label} recovery`) : null) : null,
    recovery_source_type: recoveryMode ? course.recoverySourceType : null,
    recovery_source_reference: recoveryMode ? course.recoverySourceReference : null
  }
}

function buildReIrradiationBody(
  revisionId: string,
  name: string,
  idempotencyKey: string,
  courses: CourseDraft[],
  recoveryMode: boolean,
  evaluationDate: string,
  sensitivityText: string,
  spatialRequested: boolean
): ReIrradiationInput {
  const sensitivity = parseDoses(sensitivityText, 'Sensitivity recovery', false)
  if (sensitivity.some((item) => item > 1)) throw new Error('Sensitivity recovery phải nằm trong khoảng 0–1.')
  return {
    scenario_revision_id: revisionId,
    name,
    idempotency_key: idempotencyKey,
    courses: courses.map((course) => buildCourse(course, recoveryMode)),
    recovery_model: recoveryMode ? { mode: 'USER_DEFINED', evaluation_date: evaluationDate } : { mode: 'NONE' },
    sensitivity_recovery_fractions: sensitivity,
    spatial: { requested: spatialRequested }
  }
}

function buildCompensationBody(
  revisionId: string,
  name: string,
  idempotencyKey: string,
  planned: string,
  delivered: string,
  alternatives: AlternativeDraft[],
  alphaBeta: string,
  sourceType: SourceType,
  sourceReference: string,
  interruptionStart: string,
  interruptionEnd: string,
  timeMode: 'NONE' | 'USER_DEFINED_LINEAR',
  timeStart: string,
  timeEvaluation: string,
  timeRate: string,
  timeKickoff: string,
  timeSource: string
): FractionCompensationInput {
  const interruptions = interruptionStart || interruptionEnd ? [{ start_date: interruptionStart, end_date: interruptionEnd, label: 'Treatment interruption' }] : []
  const timeModel = timeMode === 'NONE'
    ? { mode: 'NONE' }
    : {
        mode: timeMode,
        treatment_start_date: timeStart,
        evaluation_date: timeEvaluation,
        repopulation_rate_bed_gy_per_day: numberRequired(timeRate, 'Repopulation rate'),
        kickoff_days: numberRequired(timeKickoff || '0', 'Kick-off days'),
        source_reference: timeSource
      }
  return {
    scenario_revision_id: revisionId,
    name,
    idempotency_key: idempotencyKey,
    planned_fraction_doses_gy: parseDoses(planned, 'Planned schedule'),
    delivered_fraction_doses_gy: parseDoses(delivered, 'Delivered prefix', true),
    consistency_tolerance_gy: 0.01,
    alpha_beta_gy: numberRequired(alphaBeta, 'Alpha/beta'),
    alpha_beta_source_type: sourceType,
    alpha_beta_source_reference: sourceReference,
    alternatives: alternatives.map((alternative) => ({ alternative_id: alternative.alternativeId, label: alternative.label, remaining_fraction_doses_gy: parseDoses(alternative.remaining, `${alternative.label} remaining`, true) })),
    interruptions,
    time_model: timeModel
  }
}

function DownloadButton({ run, mode, format, accessToken, organizationId, onMessage }: { run: P15RunResource; mode: Mode; format: 'JSON' | 'CSV'; accessToken: string; organizationId: string; onMessage: (value: string) => void }) {
  const [busy, setBusy] = useState(false)
  return <button className="button-secondary" disabled={busy} onClick={() => {
    setBusy(true)
    void apiClient.downloadP15(accessToken, organizationId, mode === 'REIRRADIATION' ? 're-irradiation' : 'fraction-compensation', run.id, format).then((blob) => {
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `rt-connect-p15-${run.id}.${format === 'JSON' ? 'json' : 'csv'}`
      anchor.click()
      URL.revokeObjectURL(url)
      onMessage(`Đã tải export ${format} của snapshot ${run.id.slice(0, 8)}…`)
    }).catch((error: unknown) => onMessage(errorMessage(error))).finally(() => setBusy(false))
  }}>{format}</button>
}

function ReIrradiationResults({ run, mode }: { run: P15RunResource; mode: Mode }) {
  const result = run.result_snapshot
  const warningRows = records(result.warnings)
  if (mode === 'REIRRADIATION') {
    const groups = records(result.groups)
    const courses = records(result.course_contributions)
    const sensitivity = records(result.sensitivity)
    return <>
      <section className="p15-result-summary"><article><span>GROUPS</span><strong>{groups.length}</strong><small>tissue / αβ context</small></article><article><span>NO RECOVERY</span><strong>{formatNumber(groups[0]?.bed_no_recovery_gy)}</strong><small>BED Gy baseline</small></article><article><span>WITH RECOVERY</span><strong>{formatNumber(groups[0]?.bed_with_recovery_gy)}</strong><small>BED Gy assumption</small></article><article><span>SPATIAL</span><strong>UNAVAILABLE</strong><small>scalar-only contract</small></article></section>
      {warningRows.length > 0 && <div className="alert alert--warning"><strong>Assumptions / warnings</strong><ul>{warningRows.map((item, index) => <li key={`${String(item.code)}-${index}`}>{String(item.message ?? item.code)}</li>)}</ul></div>}
      <div className="p15-result-meta"><span>Model <code>{run.model_key} · {run.model_version}</code></span><span>Checksum <code>{String(result.result_sha256 ?? '—')}</code></span><span>Snapshot <code>{run.id}</code></span></div>
      <div className="table-wrap"><table className="p15-result-table"><thead><tr><th>Tissue / group</th><th>α/β</th><th>D</th><th>BED no recovery</th><th>BED with recovery</th><th>EQD2 with recovery</th></tr></thead><tbody>{groups.map((item, index) => <tr key={`${String(item.group_key)}-${index}`}><td><strong>{String(item.tissue_key ?? '—')}</strong><span className="table-subtitle">{String(item.group_key ?? '—')}</span></td><td>{formatNumber(item.alpha_beta_gy)}</td><td>{formatNumber(item.total_dose_gy)}</td><td>{formatNumber(item.bed_no_recovery_gy)}</td><td>{formatNumber(item.bed_with_recovery_gy)}</td><td>{formatNumber(item.eqd2_with_recovery_gy)}</td></tr>)}</tbody></table></div>
      <div className="table-wrap"><table className="p15-result-table"><caption>Course contributions — recovery chỉ áp dụng một lần cho course prior</caption><thead><tr><th>Course</th><th>Prior?</th><th>Tissue rows</th><th>Recovery</th></tr></thead><tbody>{courses.map((item, index) => <tr key={`${String(item.course_id)}-${index}`}><td><strong>{String(item.label ?? item.course_id ?? '—')}</strong><span className="table-subtitle">{String(item.course_id ?? '—')}</span></td><td>{item.is_prior === true ? 'YES' : 'NO'}</td><td>{records(item.tissue_doses).length}</td><td>{formatNumber(item.recovery_fraction, 2)}</td></tr>)}</tbody></table></div>
      <div className="table-wrap"><table className="p15-result-table"><caption>Sensitivity — thay đổi recovery để xem độ nhạy, không phải confidence interval</caption><thead><tr><th>Group</th><th>Recovery fraction</th><th>BED</th><th>EQD2</th></tr></thead><tbody>{sensitivity.flatMap((group, groupIndex) => records(group.points).map((point, pointIndex) => <tr key={`${groupIndex}-${pointIndex}`}><td>{String(group.group_key ?? '—')}</td><td>{formatNumber(point.recovery_fraction, 2)}</td><td>{formatNumber(point.bed_gy)}</td><td>{formatNumber(point.eqd2_gy)}</td></tr>))}</tbody></table></div>
    </>
  }
  const alternatives = records(result.alternatives)
  return <>
    <section className="p15-result-summary"><article><span>ALTERNATIVES</span><strong>{alternatives.length}</strong><small>remaining schedules</small></article><article><span>DELIVERED</span><strong>{formatNumber(record(result.delivered_prefix)?.fraction_count, 0)}</strong><small>prefix locked</small></article><article><span>PLANNED BED</span><strong>{formatNumber(record(result.planned_schedule)?.bed_lq_gy)}</strong><small>LQ baseline</small></article><article><span>TIME MODEL</span><strong>{String(record(result.time_model)?.mode ?? 'NONE')}</strong><small>{record(result.time_model)?.applied === true ? 'applied' : 'not applied'}</small></article></section>
    {warningRows.length > 0 && <div className="alert alert--warning"><strong>Assumptions / warnings</strong><ul>{warningRows.map((item, index) => <li key={`${String(item.code)}-${index}`}>{String(item.message ?? item.code)}</li>)}</ul></div>}
    <div className="p15-result-meta"><span>Model <code>{run.model_key} · {run.model_version}</code></span><span>Checksum <code>{String(result.result_sha256 ?? '—')}</code></span><span>Snapshot <code>{run.id}</code></span></div>
    <div className="table-wrap"><table className="p15-result-table"><thead><tr><th>Alternative</th><th>Remaining fx</th><th>Total D</th><th>BED LQ</th><th>EQD2 LQ</th><th>Prefix</th><th>Δ BED</th></tr></thead><tbody>{alternatives.map((item, index) => <tr key={`${String(item.alternative_id)}-${index}`}><td><strong>{String(item.label ?? '—')}</strong><span className="table-subtitle">{String(item.alternative_id ?? '—')}</span></td><td>{formatNumber(item.remaining_fraction_count, 0)}</td><td>{formatNumber(item.total_dose_gy)}</td><td>{formatNumber(item.bed_lq_gy)}</td><td>{formatNumber(item.eqd2_lq_gy)}</td><td>{item.delivered_prefix_unchanged === true ? 'UNCHANGED' : 'INVALID'}</td><td>{formatNumber(item.delta_bed_vs_planned_gy)}</td></tr>)}</tbody></table></div>
  </>
}

export function ReIrradiationPage({ mode }: { mode: Mode }) {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const queryClient = useQueryClient()
  const bootstrap = useQuery({ queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!), enabled: Boolean(accessToken), retry: false })
  const organizationId = bootstrap.data?.organization.id
  const scenarios = useQuery({ queryKey: ['p15-scenarios', organizationId, accessToken], queryFn: () => apiClient.biologicalScenarios(accessToken!, organizationId!, { status: 'SAVED' }), enabled: Boolean(accessToken && organizationId), retry: false })
  const [scenarioId, setScenarioId] = useState('')
  const activeScenarioId = scenarios.data?.items.find((item) => item.id === scenarioId)?.id ?? scenarios.data?.items[0]?.id ?? ''
  const revisions = useQuery({ queryKey: ['p15-revisions', organizationId, activeScenarioId, accessToken], queryFn: () => apiClient.biologicalScenarioRevisions(accessToken!, organizationId!, activeScenarioId), enabled: Boolean(accessToken && organizationId && activeScenarioId), retry: false })
  const savedRevisions = useMemo(() => revisions.data?.filter((item) => item.status === 'SAVED') ?? [], [revisions.data])
  const [revisionId, setRevisionId] = useState('')
  const activeRevisionId = savedRevisions.find((item) => item.id === revisionId)?.id ?? savedRevisions[0]?.id ?? ''
  const runs = useQuery({ queryKey: ['p15-runs', mode, organizationId, activeScenarioId, accessToken], queryFn: () => mode === 'REIRRADIATION' ? apiClient.reIrradiationRuns(accessToken!, organizationId!, activeScenarioId) : apiClient.fractionCompensationRuns(accessToken!, organizationId!, activeScenarioId), enabled: Boolean(accessToken && organizationId), retry: false })

  const [name, setName] = useState(mode === 'REIRRADIATION' ? 'P15 re-irradiation scenario' : 'P15 fraction compensation scenario')
  const [courses, setCourses] = useState<CourseDraft[]>(initialCourses)
  const [recoveryMode, setRecoveryMode] = useState(false)
  const [evaluationDate, setEvaluationDate] = useState('2026-03-01')
  const [sensitivityText, setSensitivityText] = useState('0, 0.25, 0.5, 0.75, 1')
  const [spatialRequested, setSpatialRequested] = useState(false)
  const [plannedText, setPlannedText] = useState('2, 2, 2, 2, 2')
  const [deliveredText, setDeliveredText] = useState('2, 2')
  const [alternatives, setAlternatives] = useState<AlternativeDraft[]>(initialAlternatives)
  const [alphaBeta, setAlphaBeta] = useState('10')
  const [sourceType, setSourceType] = useState<SourceType>('USER_DEFINED')
  const [sourceReference, setSourceReference] = useState('User-defined P15 compensation assumption')
  const [interruptionStart, setInterruptionStart] = useState('')
  const [interruptionEnd, setInterruptionEnd] = useState('')
  const [timeMode, setTimeMode] = useState<'NONE' | 'USER_DEFINED_LINEAR'>('NONE')
  const [timeStart, setTimeStart] = useState('2026-01-01')
  const [timeEvaluation, setTimeEvaluation] = useState('2026-02-15')
  const [timeRate, setTimeRate] = useState('0.1')
  const [timeKickoff, setTimeKickoff] = useState('21')
  const [timeSource, setTimeSource] = useState('User-defined linear time model')
  const [validation, setValidation] = useState<P15ValidationResource>()
  const [selectedRunId, setSelectedRunId] = useState<string>()
  const [message, setMessage] = useState<string>()
  const [idempotencyKey, setIdempotencyKey] = useState(() => `p15-${crypto.randomUUID()}`)
  const selectedRun = runs.data?.items.find((run) => run.id === selectedRunId) ?? runs.data?.items[0]
  const buildBody = (): ReIrradiationInput | FractionCompensationInput => {
    if (!activeRevisionId) throw new Error('Cần chọn một SAVED scenario revision.')
    if (mode === 'REIRRADIATION') return buildReIrradiationBody(activeRevisionId, name.trim(), idempotencyKey, courses, recoveryMode, evaluationDate, sensitivityText, spatialRequested)
    return buildCompensationBody(activeRevisionId, name.trim(), idempotencyKey, plannedText, deliveredText, alternatives, alphaBeta, sourceType, sourceReference, interruptionStart, interruptionEnd, timeMode, timeStart, timeEvaluation, timeRate, timeKickoff, timeSource)
  }
  const validateMutation = useMutation({ mutationFn: (body: ReIrradiationInput | FractionCompensationInput) => mode === 'REIRRADIATION' ? apiClient.validateReIrradiation(accessToken!, organizationId!, activeScenarioId, body as ReIrradiationInput) : apiClient.validateFractionCompensation(accessToken!, organizationId!, activeScenarioId, body as FractionCompensationInput), onSuccess: (result) => { setValidation(result); setMessage(result.valid ? 'P15 input hợp lệ; validate-only không ghi snapshot.' : 'P15 input chưa hợp lệ; xem các trường lỗi bên dưới.') }, onError: (error) => setMessage(errorMessage(error)) })
  const saveMutation = useMutation({ mutationFn: (body: ReIrradiationInput | FractionCompensationInput) => mode === 'REIRRADIATION' ? apiClient.createReIrradiation(accessToken!, organizationId!, activeScenarioId, body as ReIrradiationInput) : apiClient.createFractionCompensation(accessToken!, organizationId!, activeScenarioId, body as FractionCompensationInput), onSuccess: async (run) => { setSelectedRunId(run.id); setValidation(undefined); setMessage(`Đã lưu snapshot ${run.id.slice(0, 8)}…; input và kết quả đã được khóa.`); setIdempotencyKey(`p15-${crypto.randomUUID()}`); await queryClient.invalidateQueries({ queryKey: ['p15-runs', mode, organizationId, activeScenarioId] }) }, onError: (error) => setMessage(errorMessage(error)) })
  const busy = validateMutation.isPending || saveMutation.isPending
  const execute = (action: 'validate' | 'save') => { try { const body = buildBody(); if (action === 'validate') validateMutation.mutate(body); else saveMutation.mutate(body) } catch (error) { setMessage(errorMessage(error)) } }

  const updateCourse = (index: number, update: Partial<CourseDraft>) => setCourses((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, ...update } : item))
  const updateTissue = (courseIndex: number, tissueIndex: number, update: Partial<TissueDraft>) => setCourses((current) => current.map((course, index) => index === courseIndex ? { ...course, tissues: course.tissues.map((tissue, rowIndex) => rowIndex === tissueIndex ? { ...tissue, ...update } : tissue) } : course))

  if (bootstrap.isPending) return <main className="auth-state">Đang tải P15 Biological Workspace…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở P15</h1><p>{errorMessage(bootstrap.error)}</p><Link className="button-link" to="/app/biological">Quay lại Biological Toolkit</Link></section></div>
  if (scenarios.error || revisions.error) return <div className="page"><section className="alert alert--error"><h1>Không tải được scenario</h1><p>{errorMessage(scenarios.error ?? revisions.error)}</p><button onClick={() => void Promise.all([scenarios.refetch(), revisions.refetch()])}>Thử lại</button></section></div>

  return <div className="page p15-page">
    <header className="page-header"><div><p className="eyebrow">P15 · MOD-{mode === 'REIRRADIATION' ? '13' : '14'} · BIOLOGICAL TOOLKIT</p><h1>{mode === 'REIRRADIATION' ? 'Máy tính Tái xạ' : 'Bù fraction'}</h1><p>{mode === 'REIRRADIATION' ? 'Tính BED/EQD2 theo từng course và tissue/OAR, recovery, sensitivity và tổng scalar.' : 'So sánh các lịch bù trên phần prefix đã thực hiện, không thay đổi dữ liệu đã delivered.'}</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/biological">Biological Hub</Link><span className="status-badge status-badge--warning">SCENARIO / ESTIMATE ONLY</span></div></header>
    <nav className="p15-mode-tabs" aria-label="P15 tools"><Link className={mode === 'REIRRADIATION' ? 'is-active' : ''} to="/app/biological/re-irradiation">Tái xạ</Link><Link className={mode === 'FRACTION_COMPENSATION' ? 'is-active' : ''} to="/app/biological/fraction-compensation">Bù fraction</Link></nav>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="biological-notice p15-notice" role="note"><strong>Scalar-only independent calculation</strong><span>Không tạo prescription, không tự gắn QA/patient/TPS/PACS. P15 không thực hiện voxel dose accumulation; recovery, time model và OAR dose phải có giả định/source rõ ràng.</span></section>
    <section className="panel p15-context-panel"><div className="panel-heading"><div><p className="eyebrow">SAVED CONTEXT</p><h2>Scenario và revision</h2></div><span className="status-badge">{savedRevisions.length} SAVED REVISIONS</span></div><div className="p15-form-grid"><label>Scenario SAVED<select value={activeScenarioId} onChange={(event) => { setScenarioId(event.target.value); setRevisionId(''); setSelectedRunId(undefined) }}><option value="">Chọn scenario…</option>{scenarios.data?.items.map((item) => <option value={item.id} key={item.id}>{item.name} · {item.scenario_key}</option>)}</select></label><label>Scenario revision<select value={activeRevisionId} onChange={(event) => { setRevisionId(event.target.value); setSelectedRunId(undefined) }}><option value="">Chọn revision…</option>{savedRevisions.map((item) => <option value={item.id} key={item.id}>rev {item.revision_number} · {formatDate(item.created_at)}</option>)}</select></label><label className="p15-form-grid__wide">Tên snapshot<input value={name} onChange={(event) => setName(event.target.value)} /></label></div></section>
    {mode === 'REIRRADIATION' ? <section className="panel p15-editor-panel"><div className="panel-heading"><div><p className="eyebrow">COURSE × TISSUE MATRIX</p><h2>Course inputs</h2></div><button className="button-secondary" disabled={courses.length >= 20 || busy} onClick={() => setCourses([...courses, newCourse(courses.length)])}>+ Thêm course</button></div><p className="form-hint">Mỗi tissue/OAR phải có liều riêng và đơn vị Gy. Không sao chép target prescription sang OAR. Course prior mặc định chịu recovery; course hiện tại không chịu recovery.</p>{courses.map((course, courseIndex) => <article className="p15-course-card" key={course.courseId}><div className="p15-course-heading"><div><strong>{course.label || course.courseId}</strong><span className="table-subtitle">{course.courseId}</span></div><label className="checkbox-row"><input type="checkbox" checked={course.isPrior} onChange={(event) => updateCourse(courseIndex, { isPrior: event.target.checked })} /> Prior course</label>{courses.length > 2 && <button className="button-secondary" onClick={() => setCourses(courses.filter((_, index) => index !== courseIndex))}>Xóa</button>}</div><div className="p15-form-grid p15-form-grid--course"><label>Course ID<input value={course.courseId} onChange={(event) => updateCourse(courseIndex, { courseId: event.target.value })} /></label><label>Label<input value={course.label} onChange={(event) => updateCourse(courseIndex, { label: event.target.value })} /></label><label>Start date<input type="date" value={course.startDate} onChange={(event) => updateCourse(courseIndex, { startDate: event.target.value })} /></label><label>End date<input type="date" value={course.endDate} onChange={(event) => updateCourse(courseIndex, { endDate: event.target.value })} /></label></div>{course.tissues.map((tissue, tissueIndex) => <div className="p15-tissue-row" key={`${course.courseId}-${tissueIndex}`}><div className="p15-tissue-row__heading"><strong>Tissue / OAR {tissueIndex + 1}</strong>{course.tissues.length > 1 && <button className="button-secondary" onClick={() => updateCourse(courseIndex, { tissues: course.tissues.filter((_, index) => index !== tissueIndex) })}>Xóa row</button>}</div><div className="p15-form-grid p15-form-grid--tissue"><label>Key<input value={tissue.tissueKey} onChange={(event) => updateTissue(courseIndex, tissueIndex, { tissueKey: event.target.value })} /></label><label>Dose metric<input value={tissue.doseMetric} onChange={(event) => updateTissue(courseIndex, tissueIndex, { doseMetric: event.target.value })} placeholder="TOTAL / MEAN / D95" /></label><label>D total (Gy)<input inputMode="decimal" value={tissue.totalDose} onChange={(event) => updateTissue(courseIndex, tissueIndex, { totalDose: event.target.value })} /></label><label>Fractions<input inputMode="numeric" value={tissue.fractions} onChange={(event) => updateTissue(courseIndex, tissueIndex, { fractions: event.target.value })} /></label><label>d / fraction (Gy)<input inputMode="decimal" value={tissue.dosePerFraction} onChange={(event) => updateTissue(courseIndex, tissueIndex, { dosePerFraction: event.target.value })} /></label><label>α/β (Gy)<input inputMode="decimal" value={tissue.alphaBeta} onChange={(event) => updateTissue(courseIndex, tissueIndex, { alphaBeta: event.target.value })} /></label><label>α/β source<select value={tissue.sourceType} onChange={(event) => updateTissue(courseIndex, tissueIndex, { sourceType: event.target.value as SourceType })}><option value="USER_DEFINED">USER_DEFINED</option><option value="REFERENCE">REFERENCE</option></select></label><label>Source reference<input value={tissue.sourceReference} onChange={(event) => updateTissue(courseIndex, tissueIndex, { sourceReference: event.target.value })} /></label></div></div>)}<button className="button-secondary" onClick={() => updateCourse(courseIndex, { tissues: [...course.tissues, newTissue(course.tissues.length)] })}>+ Tissue / OAR row</button>{recoveryMode && course.isPrior && <div className="p15-recovery-row"><label>Recovery fraction [0–1]<input inputMode="decimal" value={course.recoveryFraction} onChange={(event) => updateCourse(courseIndex, { recoveryFraction: event.target.value })} /></label><label>Recovery source<input value={course.recoverySourceReference} onChange={(event) => updateCourse(courseIndex, { recoverySourceReference: event.target.value })} /></label></div>}</article>)}<div className="p15-subsection"><h3>Recovery and sensitivity</h3><div className="p15-form-grid"><label>Recovery mode<select value={recoveryMode ? 'USER_DEFINED' : 'NONE'} onChange={(event) => setRecoveryMode(event.target.value === 'USER_DEFINED')}><option value="NONE">NONE — baseline</option><option value="USER_DEFINED">USER_DEFINED — explicit assumption</option></select></label>{recoveryMode && <label>Evaluation date<input type="date" value={evaluationDate} onChange={(event) => setEvaluationDate(event.target.value)} /></label>}<label>Sensitivity recovery fractions<input value={sensitivityText} onChange={(event) => setSensitivityText(event.target.value)} /></label><label className="checkbox-row"><input type="checkbox" checked={spatialRequested} onChange={(event) => setSpatialRequested(event.target.checked)} /> Request spatial accumulation (will remain unavailable)</label></div></div><div className="p15-actions"><button disabled={busy || !activeRevisionId} onClick={() => execute('validate')}>Validate only</button><button disabled={busy || !activeRevisionId} onClick={() => execute('save')}>Calculate &amp; save snapshot</button></div>{validation && <ValidationBlock validation={validation} />}</section> : <section className="panel p15-editor-panel"><div className="panel-heading"><div><p className="eyebrow">DELIVERED PREFIX · ALTERNATIVE SCHEDULES</p><h2>Fraction compensation inputs</h2></div></div><div className="p15-form-grid"><label className="p15-form-grid__wide">Planned fraction doses (Gy)<input value={plannedText} onChange={(event) => setPlannedText(event.target.value)} placeholder="2, 2, 2, 2, 2" /></label><label className="p15-form-grid__wide">Delivered prefix (Gy)<input value={deliveredText} onChange={(event) => setDeliveredText(event.target.value)} placeholder="2, 2" /></label><label>α/β (Gy)<input inputMode="decimal" value={alphaBeta} onChange={(event) => setAlphaBeta(event.target.value)} /></label><label>α/β source<select value={sourceType} onChange={(event) => setSourceType(event.target.value as SourceType)}><option value="USER_DEFINED">USER_DEFINED</option><option value="REFERENCE">REFERENCE</option></select></label><label>Source reference<input value={sourceReference} onChange={(event) => setSourceReference(event.target.value)} /></label></div><div className="p15-subsection"><div className="panel-heading"><div><h3>Remaining alternatives</h3><p className="form-hint">Chỉ nhập phần còn lại; prefix delivered sẽ được engine khóa và kiểm tra.</p></div><button className="button-secondary" disabled={alternatives.length >= 20} onClick={() => setAlternatives([...alternatives, { alternativeId: `alternative-${alternatives.length + 1}`, label: `Alternative ${alternatives.length + 1}`, remaining: '2, 2, 2' }])}>+ Thêm alternative</button></div>{alternatives.map((alternative, index) => <div className="p15-alternative-row" key={alternative.alternativeId}><label>ID<input value={alternative.alternativeId} onChange={(event) => setAlternatives(alternatives.map((item, itemIndex) => itemIndex === index ? { ...item, alternativeId: event.target.value } : item))} /></label><label>Label<input value={alternative.label} onChange={(event) => setAlternatives(alternatives.map((item, itemIndex) => itemIndex === index ? { ...item, label: event.target.value } : item))} /></label><label className="p15-alternative-row__wide">Remaining doses (Gy)<input value={alternative.remaining} onChange={(event) => setAlternatives(alternatives.map((item, itemIndex) => itemIndex === index ? { ...item, remaining: event.target.value } : item))} /></label>{alternatives.length > 1 && <button className="button-secondary" onClick={() => setAlternatives(alternatives.filter((_, itemIndex) => itemIndex !== index))}>Xóa</button>}</div>)}</div><div className="p15-subsection"><h3>Interruption and optional time model</h3><div className="p15-form-grid"><label>Interruption start<input type="date" value={interruptionStart} onChange={(event) => setInterruptionStart(event.target.value)} /></label><label>Interruption end<input type="date" value={interruptionEnd} onChange={(event) => setInterruptionEnd(event.target.value)} /></label><label>Time model<select value={timeMode} onChange={(event) => setTimeMode(event.target.value as 'NONE' | 'USER_DEFINED_LINEAR')}><option value="NONE">NONE — no repopulation correction</option><option value="USER_DEFINED_LINEAR">USER_DEFINED_LINEAR</option></select></label>{timeMode !== 'NONE' && <><label>Treatment start<input type="date" value={timeStart} onChange={(event) => setTimeStart(event.target.value)} /></label><label>Evaluation date<input type="date" value={timeEvaluation} onChange={(event) => setTimeEvaluation(event.target.value)} /></label><label>Rate BED-Gy/day<input inputMode="decimal" value={timeRate} onChange={(event) => setTimeRate(event.target.value)} /></label><label>Kick-off days<input inputMode="decimal" value={timeKickoff} onChange={(event) => setTimeKickoff(event.target.value)} /></label><label>Time source<input value={timeSource} onChange={(event) => setTimeSource(event.target.value)} /></label></>}</div></div><div className="p15-actions"><button disabled={busy || !activeRevisionId} onClick={() => execute('validate')}>Validate only</button><button disabled={busy || !activeRevisionId} onClick={() => execute('save')}>Calculate &amp; save snapshot</button></div>{validation && <ValidationBlock validation={validation} />}</section>}
    <section className="panel p15-result-panel"><div className="panel-heading"><div><p className="eyebrow">IMMUTABLE RESULT SNAPSHOT</p><h2>{selectedRun ? selectedRun.name : 'Chưa chọn snapshot'}</h2></div>{selectedRun && <div className="p15-export-actions"><DownloadButton run={selectedRun} mode={mode} format="JSON" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /><DownloadButton run={selectedRun} mode={mode} format="CSV" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /></div>}</div>{selectedRun ? <ReIrradiationResults run={selectedRun} mode={mode} /> : <p className="empty-state">Validate input trước, sau đó lưu snapshot để xem course contribution, group, sensitivity, alternative và checksum.</p>}</section>
    <section className="panel p15-history-panel"><div className="panel-heading"><div><p className="eyebrow">HISTORY · APPEND-ONLY</p><h2>{mode === 'REIRRADIATION' ? 'Re-irradiation snapshots' : 'Compensation snapshots'}</h2></div><strong>{runs.data?.total ?? '—'}</strong></div>{runs.error && <div className="alert alert--error"><p>{errorMessage(runs.error)}</p><button onClick={() => void runs.refetch()}>Thử lại</button></div>}{runs.isPending ? <p>Đang tải history…</p> : runs.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Created</th><th>Name</th><th>Revision</th><th>Model</th><th>Status</th><th>Checksum</th><th>Export</th></tr></thead><tbody>{runs.data.items.map((run) => <tr className={run.id === selectedRun?.id ? 'is-selected' : undefined} key={run.id}><td><button className="table-link" onClick={() => setSelectedRunId(run.id)}>{formatDate(run.created_at)}<small className="table-subtitle">{run.id}</small></button></td><td>{run.name}</td><td><code>{run.scenario_revision_id}</code></td><td>{run.model_version}</td><td><span className={statusClass(run.status)}>{run.status}</span></td><td><code>{String(run.result_snapshot.result_sha256 ?? '—')}</code></td><td><div className="table-actions"><DownloadButton run={run} mode={mode} format="JSON" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /><DownloadButton run={run} mode={mode} format="CSV" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /></div></td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có snapshot cho scenario revision này.</p>}</section>
    <p className="form-hint p15-footer-note">P15 result là công cụ tính toán độc lập. Kết quả có checksum và model version để truy xuất lại, nhưng không phải medical prescription, không tự động xếp hạng và không thay thế đánh giá chuyên môn.</p>
  </div>
}

function ValidationBlock({ validation }: { validation: P15ValidationResource }) {
  return <section className={validation.valid ? 'bed-validation bed-validation--ok' : 'bed-validation bed-validation--error'}><strong>{validation.valid ? 'VALIDATION OK' : 'VALIDATION FAILED'}</strong>{validation.errors.length > 0 ? <ul>{validation.errors.map((item, index) => <li key={`${item.code}-${index}`}><strong>{item.field ?? 'input'}</strong>: {item.message} <code>{item.code}</code></li>)}</ul> : <p>{validation.warnings.length > 0 ? validation.warnings.map((item) => `${item.message} (${item.code})`).join(' | ') : `Preview không ghi database · ${String(validation.preview?.result_sha256 ?? 'checksum pending')}`}</p>}</section>
}
