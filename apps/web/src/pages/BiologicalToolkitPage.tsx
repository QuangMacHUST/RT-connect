import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  ApiClientError,
  apiClient,
  type BiologicalScenarioCreateInput,
  type BiologicalScenarioResource,
  type BiologicalToolResource
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type SourceType = NonNullable<BiologicalScenarioCreateInput['source_type']>
type StatusFilter = 'ALL' | 'DRAFT' | 'SAVED' | 'ARCHIVED'
type ScenarioForm = BiologicalScenarioCreateInput & { assumptions_text: string; source_type: SourceType }

const sourceTypes: SourceType[] = ['USER_DEFINED', 'REFERENCE', 'INTERNAL', 'SITE_APPROVED']

function emptyForm(): ScenarioForm {
  return {
    scenario_key: 'NEW_SCENARIO',
    name: 'New biological scenario',
    scenario_type: 'GENERAL',
    tissue_context: 'Chưa xác định mô',
    clinical_context: '',
    source_type: 'USER_DEFINED',
    source_reference: '',
    assumptions: {},
    assumptions_text: '{}'
  }
}

function formFromScenario(scenario: BiologicalScenarioResource): ScenarioForm {
  const source = sourceTypes.includes(scenario.source_type as SourceType)
    ? scenario.source_type as SourceType
    : 'USER_DEFINED'
  return {
    scenario_key: scenario.scenario_key,
    name: scenario.name,
    scenario_type: scenario.scenario_type,
    tissue_context: scenario.tissue_context,
    clinical_context: scenario.clinical_context ?? '',
    source_type: source,
    source_reference: scenario.source_reference ?? '',
    assumptions: scenario.assumptions,
    assumptions_text: JSON.stringify(scenario.assumptions, null, 2)
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function dateLabel(value: string): string {
  return new Date(value).toLocaleString('vi-VN')
}

function statusClass(value: string): string {
  if (value === 'SAVED') return 'status-badge'
  if (value === 'ARCHIVED') return 'status-badge machine-status--fail'
  return 'status-badge machine-status--draft'
}

function toolClass(tool: BiologicalToolResource): string {
  return tool.available ? 'biological-tool-card biological-tool-card--available' : 'biological-tool-card'
}

export function BiologicalToolkitPage() {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const queryClient = useQueryClient()
  const bootstrap = useQuery({
    queryKey: ['session', accessToken],
    queryFn: () => apiClient.bootstrap(accessToken!),
    enabled: Boolean(accessToken),
    retry: false
  })
  const organizationId = bootstrap.data?.organization.id
  const tools = useQuery({
    queryKey: ['biological-tools', organizationId, accessToken],
    queryFn: () => apiClient.biologicalTools(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const summary = useQuery({
    queryKey: ['biological-summary', organizationId, accessToken],
    queryFn: () => apiClient.biologicalSummary(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')
  const [includeArchived, setIncludeArchived] = useState(false)
  const scenarios = useQuery({
    queryKey: ['biological-scenarios', organizationId, accessToken, search, statusFilter, includeArchived],
    queryFn: () => apiClient.biologicalScenarios(accessToken!, organizationId!, {
      q: search || undefined,
      status: statusFilter === 'ALL' ? undefined : statusFilter,
      include_archived: includeArchived || statusFilter === 'ARCHIVED'
    }),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const [selectedId, setSelectedId] = useState<string>()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<ScenarioForm>(() => emptyForm())
  const [message, setMessage] = useState<string>()
  const [validationMessage, setValidationMessage] = useState<string>()
  const [showHistory, setShowHistory] = useState(false)

  const selected = useMemo(
    () => scenarios.data?.items.find((scenario) => scenario.id === selectedId),
    [scenarios.data?.items, selectedId]
  )
  const detail = useQuery({
    queryKey: ['biological-scenario', organizationId, selectedId, accessToken],
    queryFn: () => apiClient.biologicalScenario(accessToken!, organizationId!, selectedId!),
    enabled: Boolean(accessToken && organizationId && selectedId),
    retry: false
  })
  const current = detail.data ?? selected
  const editable = showForm || current?.status === 'DRAFT'
  const history = useQuery({
    queryKey: ['biological-scenario-revisions', organizationId, selectedId, accessToken],
    queryFn: () => apiClient.biologicalScenarioRevisions(accessToken!, organizationId!, selectedId!),
    enabled: Boolean(accessToken && organizationId && selectedId && showHistory),
    retry: false
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['biological-scenarios', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['biological-summary', organizationId] })
    if (selectedId) {
      void queryClient.invalidateQueries({ queryKey: ['biological-scenario', organizationId, selectedId] })
      void queryClient.invalidateQueries({ queryKey: ['biological-scenario-revisions', organizationId, selectedId] })
    }
  }

  const choose = (scenario: BiologicalScenarioResource) => {
    setSelectedId(scenario.id)
    setShowForm(false)
    setForm(formFromScenario(scenario))
    setValidationMessage(undefined)
    setShowHistory(false)
  }

  const buildBody = (): BiologicalScenarioCreateInput | undefined => {
    let assumptions: Record<string, unknown>
    try {
      const parsed: unknown = JSON.parse(form.assumptions_text || '{}')
      if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') {
        throw new Error('Assumptions phải là một JSON object.')
      }
      assumptions = parsed as Record<string, unknown>
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Assumptions JSON không hợp lệ.')
      return undefined
    }
    return {
      scenario_key: form.scenario_key,
      name: form.name,
      scenario_type: form.scenario_type,
      tissue_context: form.tissue_context,
      clinical_context: form.clinical_context || null,
      source_type: form.source_type,
      source_reference: form.source_reference || null,
      assumptions
    }
  }

  const createMutation = useMutation({
    mutationFn: (body: BiologicalScenarioCreateInput) => apiClient.createBiologicalScenario(accessToken!, organizationId!, body),
    onSuccess: (scenario) => {
      setSelectedId(scenario.id)
      setShowForm(false)
      setForm(formFromScenario(scenario))
      setMessage(`Đã tạo scenario ${scenario.scenario_key} ở trạng thái DRAFT.`)
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const updateMutation = useMutation({
    mutationFn: (body: Parameters<typeof apiClient.updateBiologicalScenario>[3]) => apiClient.updateBiologicalScenario(accessToken!, organizationId!, selected!.id, body),
    onSuccess: (scenario) => {
      setForm(formFromScenario(scenario))
      setMessage(`Đã lưu revision ${scenario.revision} của scenario.`)
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validateMutation = useMutation({
    mutationFn: (body: BiologicalScenarioCreateInput) => apiClient.validateBiologicalScenario(accessToken!, organizationId!, body),
    onSuccess: (result) => setValidationMessage(result.valid ? 'Scenario hợp lệ; chưa ghi vào database.' : result.errors.map((item) => `${item.field ?? 'scenario'}: ${item.message} (${item.code})`).join(' | ')),
    onError: (error) => setValidationMessage(errorMessage(error))
  })
  const saveMutation = useMutation({
    mutationFn: () => apiClient.saveBiologicalScenario(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (scenario) => { setForm(formFromScenario(scenario)); setMessage(`Đã lưu scenario revision ${scenario.revision}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cloneMutation = useMutation({
    mutationFn: (scenarioId: string) => apiClient.cloneBiologicalScenario(accessToken!, organizationId!, scenarioId),
    onSuccess: (scenario) => { setSelectedId(scenario.id); setShowForm(false); setForm(formFromScenario(scenario)); setMessage(`Đã clone thành ${scenario.scenario_key}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const archiveMutation = useMutation({
    mutationFn: () => apiClient.archiveBiologicalScenario(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (scenario) => { setForm(formFromScenario(scenario)); setMessage(`Đã archive ${scenario.scenario_key}; lịch sử vẫn đọc được.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const busy = createMutation.isPending || updateMutation.isPending || validateMutation.isPending || saveMutation.isPending || cloneMutation.isPending || archiveMutation.isPending

  if (bootstrap.isPending) return <main className="auth-state">Đang tải Biological Toolkit…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở Biological Toolkit</h1><p>{errorMessage(bootstrap.error)}</p><button onClick={() => void bootstrap.refetch()}>Thử lại</button></section></div>

  const submit = () => {
    const body = buildBody()
    if (!body) return
    setValidationMessage(undefined)
    if (showForm) createMutation.mutate(body)
    else if (selected?.status === 'DRAFT') updateMutation.mutate({ ...body, expected_revision: selected.revision })
  }
  const toolItems = tools.data ?? []

  return <div className="page biological-page">
    <header className="page-header">
      <div><p className="eyebrow">P12 · MOD-10</p><h1>Biological Toolkit</h1><p>Không gian tính toán và kịch bản độc lập; không tự động liên kết với hồ sơ QA hoặc ca lâm sàng.</p></div>
      <div className="page-header__actions"><button onClick={() => { setSelectedId(undefined); setShowForm(true); setForm(emptyForm()); setMessage(undefined); setValidationMessage(undefined) }}>+ Tạo scenario</button><button className="button-secondary" onClick={() => setShowHistory(!showHistory)}>Lịch sử tính toán</button></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {validationMessage && <section className={validationMessage.startsWith('Scenario hợp lệ') ? 'alert alert--success' : 'alert alert--warning'} role="status"><p>{validationMessage}</p></section>}
    {(tools.error || summary.error || scenarios.error) && <section className="alert alert--error" role="alert"><h2>Không thể tải dữ liệu Biological Toolkit</h2><p>{errorMessage(tools.error ?? summary.error ?? scenarios.error)}</p><button onClick={() => void Promise.all([tools.refetch(), summary.refetch(), scenarios.refetch()])}>Thử lại</button></section>}

    <section className="biological-notice" role="note"><strong>Independent Calculation Workspace</strong><span>Kết quả chỉ là estimate/scenario tham khảo. Mọi calculation sẽ đi kèm model, source, assumptions, revision và timestamp; không tạo prescription và không gửi dữ liệu sang TPS/PACS.</span></section>

    <section className="metric-grid biological-metrics"><section className="metric-card"><p>Kịch bản đã lưu</p><strong>{summary.data?.saved_scenarios ?? '—'}</strong><small>Scenario SAVED trong organization</small></section><section className="metric-card"><p>Phép tính hoàn tất</p><strong>{summary.data?.completed_calculations ?? '—'}</strong><small>Calculation snapshot từ các module</small></section><section className="metric-card"><p>Báo cáo độc lập</p><strong>{summary.data?.exported_reports ?? '—'}</strong><small>Export thành công từ Biological source</small></section><section className="metric-card biological-metric-card--info"><p>Draft đang soạn</p><strong>{summary.data?.draft_scenarios ?? '—'}</strong><small>Chỉ DRAFT mới có thể sửa trực tiếp</small></section></section>

    <section className="panel biological-tools-panel"><div className="panel-heading"><div><p className="eyebrow">MODULE EXPLORER</p><h2>Công cụ Biological</h2></div><span className="status-badge">SCENARIO ONLY</span></div><div className="biological-tool-grid">{toolItems.map((tool) => <article className={toolClass(tool)} key={tool.tool_key}><div className="biological-tool-card__top"><span className="biological-tool-icon" aria-hidden="true">◇</span><span className={tool.available ? 'status-badge' : 'status-badge status-badge--warning'}>{tool.available ? 'AVAILABLE' : `${tool.phase} · PLANNED`}</span></div><h3>{tool.label}</h3><p>{tool.description}</p>{tool.available ? <Link className="button-link" to={tool.route}>Mở công cụ</Link> : <button className="button-secondary" disabled title={`Tính năng sẽ được triển khai ở ${tool.phase}`}>Sắp triển khai</button>}</article>)}</div></section>

    <div className="biological-workspace-grid">
      <section className="panel biological-scenarios-panel"><div className="panel-heading"><div><p className="eyebrow">SCENARIO LIBRARY</p><h2>Scenarios gần đây</h2></div><strong>{scenarios.data?.total ?? '—'}</strong></div><div className="biological-filter-row"><label>Tìm kiếm<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="key, tên, loại, mô" /></label><label>Trạng thái<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}><option value="ALL">Tất cả</option><option value="DRAFT">DRAFT</option><option value="SAVED">SAVED</option><option value="ARCHIVED">ARCHIVED</option></select></label><label className="checkbox-row"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} /> Hiện archived</label></div>{scenarios.isPending ? <p>Đang tải scenarios…</p> : <div className="table-wrap"><table className="biological-scenario-table"><thead><tr><th>Tên kịch bản</th><th>Loại</th><th>Mô / context</th><th>Revision</th><th>Trạng thái</th><th>Cập nhật</th><th>Thao tác</th></tr></thead><tbody>{scenarios.data?.items.map((scenario) => <tr key={scenario.id}><td><strong>{scenario.name}</strong><span className="table-subtitle">{scenario.scenario_key}</span></td><td>{scenario.scenario_type}</td><td>{scenario.tissue_context}</td><td>{scenario.revision}</td><td><span className={statusClass(scenario.status)}>{scenario.status}</span></td><td>{dateLabel(scenario.updated_at)}</td><td><div className="table-actions"><button className="button-secondary" onClick={() => choose(scenario)}>Mở</button><button className="button-secondary" disabled={busy} onClick={() => { choose(scenario); cloneMutation.mutate(scenario.id) }}>Clone</button><button className="button-secondary" disabled title="Export sẽ mở sau khi calculation/report module sẵn sàng">Export</button></div></td></tr>)}</tbody></table></div>}{!scenarios.isPending && !scenarios.data?.items.length && <div className="empty-state biological-empty-state"><strong>Chưa có scenario</strong><p>Tạo scenario đầu tiên để lưu context và giả định độc lập. Không cần tạo QA case.</p><button onClick={() => { setSelectedId(undefined); setShowForm(true); setForm(emptyForm()) }}>+ Tạo scenario đầu tiên</button></div>}</section>

      <aside className="biological-side-column"><section className="panel biological-provenance-panel"><div className="panel-heading"><div><p className="eyebrow">PROVENANCE</p><h2>Mỗi kết quả phải truy lại được</h2></div></div><ul><li><strong>Model</strong><span>engine key và version</span></li><li><strong>Source</strong><span>citation hoặc user-defined note</span></li><li><strong>Assumptions</strong><span>JSON context snapshot</span></li><li><strong>Revision</strong><span>input revision + timestamp</span></li></ul><p className="form-hint">Scenario là namespace riêng. QA case, patient record và treatment plan không được tự động kéo vào đây.</p></section><section className="panel biological-workflow-panel"><div className="panel-heading"><div><p className="eyebrow">WORKFLOW</p><h2>Quy trình làm việc</h2></div></div><ol><li>Chọn công cụ</li><li>Nhập scenario/context</li><li>Lưu revision</li><li>Tính toán</li><li>Kiểm tra giả định</li><li>Xuất báo cáo độc lập</li></ol><p className="form-hint">Scenario ≠ QA Case. Mỗi module chỉ mở khi capability và test tương ứng đã sẵn sàng.</p></section></aside>
    </div>

    {(showForm || current) && <section className="panel biological-editor-panel"><div className="panel-heading"><div><p className="eyebrow">{showForm ? 'NEW SCENARIO' : 'SCENARIO REVISION'}</p><h2>{showForm ? 'Tạo scenario mới' : current?.name}</h2></div>{current && <span className={statusClass(current.status)}>{current.status} · rev {current.revision}</span>}</div>{current && !showForm && <div className="protocol-meta"><span><strong>{current.scenario_key}</strong></span><span>Cập nhật {dateLabel(current.updated_at)}</span>{current.source_scenario_revision_id && <span>Clone từ <code>{current.source_scenario_revision_id.slice(0, 8)}…</code></span>}</div>}<div className="biological-form-grid"><label>Scenario key<input disabled={!showForm} value={form.scenario_key} onChange={(event) => setForm({ ...form, scenario_key: event.target.value.toUpperCase() })} /></label><label>Tên hiển thị<input disabled={!editable} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>Scenario type<input disabled={!editable} value={form.scenario_type} onChange={(event) => setForm({ ...form, scenario_type: event.target.value })} /></label><label>Tissue / context<input disabled={!editable} value={form.tissue_context} onChange={(event) => setForm({ ...form, tissue_context: event.target.value })} /></label><label>Source type<select disabled={!editable} value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value as SourceType })}>{sourceTypes.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label>Source reference<input disabled={!editable} value={form.source_reference ?? ''} onChange={(event) => setForm({ ...form, source_reference: event.target.value })} placeholder="DOI, guideline, local document…" /></label><label className="biological-form-grid__wide">Clinical / working context<textarea disabled={!editable} value={form.clinical_context ?? ''} onChange={(event) => setForm({ ...form, clinical_context: event.target.value })} placeholder="Không nhập patient identifier hoặc dữ liệu nhận diện." /></label><label className="biological-form-grid__wide">Assumptions JSON<textarea disabled={!editable} value={form.assumptions_text} onChange={(event) => setForm({ ...form, assumptions_text: event.target.value })} /></label></div><div className="biological-editor-actions">{editable && <><button disabled={busy} onClick={() => { const body = buildBody(); if (body) validateMutation.mutate(body) }}>Kiểm tra scenario</button><button disabled={busy} onClick={submit}>{showForm ? 'Tạo bản nháp' : 'Lưu revision'}</button></>}{current && <><button className="button-secondary" disabled={busy} onClick={() => cloneMutation.mutate(current.id)}>Clone scenario</button>{current.status === 'DRAFT' && <button disabled={busy} onClick={() => saveMutation.mutate()}>Lưu scenario</button>}{current.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => archiveMutation.mutate()}>Archive</button>}</>}</div>{current && <p className="form-hint">Scenario {current.status} là snapshot đã lưu; muốn thử giả định mới hãy clone để tạo revision độc lập. Các nút tính toán sẽ xuất hiện khi module P13–P15 đạt capability tương ứng.</p>}</section>}

    {showHistory && <section className="panel biological-history-panel"><div className="panel-heading"><div><p className="eyebrow">HISTORY</p><h2>Calculation history</h2></div></div>{!selectedId ? <p className="empty-state">Chọn một scenario để xem input revisions. Chưa có calculation nào được tạo ở P12.</p> : history.isPending ? <p>Đang tải revision history…</p> : history.error ? <div className="alert alert--error"><p>{errorMessage(history.error)}</p><button onClick={() => void history.refetch()}>Thử lại</button></div> : <><p className="form-hint">Lịch sử scenario là append-only snapshot; calculation thực tế sẽ được thêm bởi P13–P15.</p><div className="table-wrap"><table><thead><tr><th>Revision</th><th>Status</th><th>Snapshot</th><th>Created</th></tr></thead><tbody>{history.data?.map((revision) => <tr key={revision.id}><td>{revision.revision_number}</td><td>{revision.status}</td><td><code>{JSON.stringify(revision.snapshot)}</code></td><td>{dateLabel(revision.created_at)}</td></tr>)}</tbody></table></div></>}</section>}
  </div>
}
