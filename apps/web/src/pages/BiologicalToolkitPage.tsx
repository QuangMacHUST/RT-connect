import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

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

const sourceTypeLabels: Record<SourceType, string> = {
  USER_DEFINED: 'Tự nhập',
  REFERENCE: 'Tài liệu tham khảo',
  INTERNAL: 'Tài liệu nội bộ',
  SITE_APPROVED: 'Đã được đơn vị phê duyệt'
}

const statusLabels: Record<StatusFilter, string> = {
  ALL: 'Tất cả',
  DRAFT: 'Đang soạn',
  SAVED: 'Đã lưu',
  ARCHIVED: 'Đã lưu trữ'
}

const toolLabels: Record<string, { name: string; description: string }> = {
  BED_EQD2: { name: 'BED và EQD2', description: 'Tính liều sinh học tương đương và xem đường biểu diễn theo tổng liều.' },
  PLAN_COMPARISON: { name: 'So sánh phác đồ', description: 'Đặt nhiều phương án cạnh nhau trong cùng một bối cảnh điều trị.' },
  RE_IRRADIATION: { name: 'Tái xạ', description: 'Đánh giá nhiều đợt điều trị, khả năng hồi phục và liều tích lũy.' },
  FRACTION_COMPENSATION: { name: 'Bù phân liều', description: 'So sánh các phương án bù phân liều và giữ nguyên phần đã thực hiện.' },
  DOSE_LIMITS_PROTOCOLS: { name: 'Giới hạn liều và phác đồ', description: 'Tra cứu giới hạn liều, phác đồ điều trị và nguồn tham khảo theo bối cảnh.' }
}

function toolCopy(tool: BiologicalToolResource): { name: string; description: string } {
  return toolLabels[tool.tool_key] ?? { name: 'Công cụ khác', description: 'Công cụ này đang được bổ sung nội dung hiển thị.' }
}

function emptyForm(): ScenarioForm {
  return {
    scenario_key: `SCENARIO_${Date.now()}`,
    name: '',
    scenario_type: 'GENERAL',
    tissue_context: 'Chưa xác định mô',
    clinical_context: '',
    source_type: 'USER_DEFINED',
    source_reference: '',
    assumptions: {},
    assumptions_text: ''
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
    assumptions_text: Object.entries(scenario.assumptions)
      .map(([key, value]) => `${key}: ${typeof value === 'object' ? 'Nội dung đã lưu' : String(value)}`)
      .join('\n')
  }
}

function assumptionsFromText(value: string): Record<string, unknown> {
  const lines = value.split('\n').map((line) => line.trim()).filter(Boolean)
  if (!lines.length) return {}
  return lines.reduce<Record<string, unknown>>((result, line, index) => {
    const separator = line.indexOf(':')
    const key = separator > 0 ? line.slice(0, separator).trim() : `ghi_chu_${index + 1}`
    const rawValue = separator > 0 ? line.slice(separator + 1).trim() : line
    result[key] = rawValue
    return result
  }, {})
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message
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

function statusLabel(value: string): string {
  if (value === 'SAVED') return 'Đã lưu'
  if (value === 'ARCHIVED') return 'Đã lưu trữ'
  return 'Đang soạn'
}

function scenarioTypeLabel(value: string): string {
  const labels: Record<string, string> = {
    GENERAL: 'Tổng quát',
    BED_EQD2: 'BED và EQD2',
    PLAN_COMPARISON: 'So sánh phác đồ',
    RE_IRRADIATION: 'Tái xạ',
    FRACTION_COMPENSATION: 'Bù phân liều',
    DOSE_LIMITS_PROTOCOLS: 'Giới hạn liều và phác đồ'
  }
  return labels[value] ?? 'Kịch bản khác'
}

function toolClass(tool: BiologicalToolResource): string {
  return tool.available ? 'biological-tool-card biological-tool-card--available' : 'biological-tool-card'
}

export function BiologicalToolkitPage() {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const navigate = useNavigate()
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
    const assumptions = assumptionsFromText(form.assumptions_text)
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
      setMessage('Đã tạo kịch bản ở trạng thái đang soạn.')
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const updateMutation = useMutation({
    mutationFn: (body: Parameters<typeof apiClient.updateBiologicalScenario>[3]) => apiClient.updateBiologicalScenario(accessToken!, organizationId!, selected!.id, body),
    onSuccess: (scenario) => {
      setForm(formFromScenario(scenario))
      setMessage(`Đã lưu bản cập nhật lần ${scenario.revision} của kịch bản.`)
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validateMutation = useMutation({
    mutationFn: (body: BiologicalScenarioCreateInput) => apiClient.validateBiologicalScenario(accessToken!, organizationId!, body),
    onSuccess: (result) => setValidationMessage(result.valid ? 'Kịch bản hợp lệ; chưa ghi vào cơ sở dữ liệu.' : result.errors.map((item) => `${item.field ?? 'kịch bản'}: ${item.message}`).join(' | ')),
    onError: (error) => setValidationMessage(errorMessage(error))
  })
  const saveMutation = useMutation({
    mutationFn: () => apiClient.saveBiologicalScenario(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (scenario) => { setForm(formFromScenario(scenario)); setMessage(`Đã lưu bản cập nhật lần ${scenario.revision} của kịch bản.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cloneMutation = useMutation({
    mutationFn: (scenarioId: string) => apiClient.cloneBiologicalScenario(accessToken!, organizationId!, scenarioId),
    onSuccess: (scenario) => { setSelectedId(scenario.id); setShowForm(false); setForm(formFromScenario(scenario)); setMessage('Đã tạo một bản sao để chỉnh sửa độc lập.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const archiveMutation = useMutation({
    mutationFn: () => apiClient.archiveBiologicalScenario(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (scenario) => { setForm(formFromScenario(scenario)); setMessage('Đã lưu trữ kịch bản; lịch sử vẫn có thể xem lại.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const reportMutation = useMutation({
    mutationFn: (scenario: BiologicalScenarioResource) => apiClient.createReport(accessToken!, organizationId!, {
      source_type: 'BIOLOGICAL',
      source_id: scenario.id,
      title: `${scenario.name} · Báo cáo công cụ sinh học`,
      blocks: [
        {
          stable_block_id: 'scenario-summary',
          block_type: 'BIOLOGICAL',
          label: 'Tóm tắt kịch bản và giả định',
          sort_order: 0,
          is_visible: true,
          config: {},
          source_binding: { path: 'source_snapshot.payload.scenario_snapshot' }
        },
        {
          stable_block_id: 'provenance',
          block_type: 'PROVENANCE',
          label: 'Nguồn và dấu vết kiểm tra',
          sort_order: 1,
          is_visible: true,
          config: {},
          source_binding: { path: 'source_snapshot.payload' }
        }
      ]
    }),
    onSuccess: (revision) => {
      setMessage(`Đã tạo báo cáo độc lập từ kịch bản (bản cập nhật lần ${revision.revision_number}).`)
      navigate(`/app/reports?reportKey=${revision.report_key}`)
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const busy = createMutation.isPending || updateMutation.isPending || validateMutation.isPending || saveMutation.isPending || cloneMutation.isPending || archiveMutation.isPending || reportMutation.isPending

  if (bootstrap.isPending) return <main className="auth-state">Đang tải công cụ sinh học…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở công cụ sinh học</h1><p>{errorMessage(bootstrap.error)}</p><button onClick={() => void bootstrap.refetch()}>Thử lại</button></section></div>

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
      <div><p className="eyebrow">CÔNG CỤ TÍNH TOÁN SINH HỌC</p><h1>Công cụ sinh học</h1><p>Tính toán và lưu kịch bản độc lập; không tự động liên kết với hồ sơ kiểm tra máy hoặc hồ sơ người bệnh.</p></div>
      <div className="page-header__actions"><button onClick={() => { setSelectedId(undefined); setShowForm(true); setForm(emptyForm()); setMessage(undefined); setValidationMessage(undefined) }}>+ Tạo kịch bản</button><button className="button-secondary" onClick={() => setShowHistory(!showHistory)}>Lịch sử tính toán</button></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {validationMessage && <section className={validationMessage.startsWith('Kịch bản hợp lệ') ? 'alert alert--success' : 'alert alert--warning'} role="status"><p>{validationMessage}</p></section>}
    {(tools.error || summary.error || scenarios.error) && <section className="alert alert--error" role="alert"><h2>Không thể tải dữ liệu công cụ sinh học</h2><p>{errorMessage(tools.error ?? summary.error ?? scenarios.error)}</p><button onClick={() => void Promise.all([tools.refetch(), summary.refetch(), scenarios.refetch()])}>Thử lại</button></section>}

    <section className="biological-notice" role="note"><strong>Không gian tính toán độc lập</strong><span>Kết quả chỉ là ước tính tham khảo. Mỗi phép tính lưu kèm mô hình, nguồn, giả định, bản cập nhật và thời điểm; không tạo chỉ định điều trị và không gửi dữ liệu sang hệ thống lập kế hoạch hoặc lưu trữ ảnh.</span></section>

    <section className="metric-grid biological-metrics"><section className="metric-card"><p>Kịch bản đã lưu</p><strong>{summary.data?.saved_scenarios ?? '—'}</strong><small>Kịch bản đã lưu trong đơn vị</small></section><section className="metric-card"><p>Phép tính hoàn tất</p><strong>{summary.data?.completed_calculations ?? '—'}</strong><small>Kết quả đã ghi nhận từ các công cụ</small></section><section className="metric-card"><p>Báo cáo độc lập</p><strong>{summary.data?.exported_reports ?? '—'}</strong><small>Báo cáo đã xuất thành công</small></section><section className="metric-card biological-metric-card--info"><p>Bản nháp đang soạn</p><strong>{summary.data?.draft_scenarios ?? '—'}</strong><small>Chỉ bản nháp mới có thể sửa trực tiếp</small></section></section>

    <section className="panel biological-tools-panel"><div className="panel-heading"><div><p className="eyebrow">DANH SÁCH CÔNG CỤ</p><h2>Công cụ sinh học</h2></div><span className="status-badge">KỊCH BẢN ĐỘC LẬP</span></div><div className="biological-tool-grid">{toolItems.filter((tool) => tool.tool_key !== 'KNOWLEDGE_LIBRARY').map((tool) => { const copy = toolCopy(tool); return <article className={toolClass(tool)} key={tool.tool_key}><div className="biological-tool-card__top"><span className="biological-tool-icon" aria-hidden="true">◇</span><span className={tool.available ? 'status-badge' : 'status-badge status-badge--warning'}>{tool.available ? 'Sẵn sàng' : 'Đang chuẩn bị'}</span></div><h3>{copy.name}</h3><p>{copy.description}</p>{tool.available ? <Link className="button-link" to={tool.route}>Mở công cụ</Link> : <button className="button-secondary" disabled title="Công cụ đang được chuẩn bị">Sắp triển khai</button>}</article> })}</div></section>

    <div className="biological-workspace-grid">
      <section className="panel biological-scenarios-panel"><div className="panel-heading"><div><p className="eyebrow">THƯ VIỆN KỊCH BẢN</p><h2>Kịch bản gần đây</h2></div><strong>{scenarios.data?.total ?? '—'}</strong></div><div className="biological-filter-row"><label>Tìm kiếm<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tên, loại hoặc mô" /></label><label>Trạng thái<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>{(Object.keys(statusLabels) as StatusFilter[]).map((item) => <option key={item} value={item}>{statusLabels[item]}</option>)}</select></label><label className="checkbox-row"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} /> Hiện mục đã lưu trữ</label></div>{scenarios.isPending ? <p>Đang tải kịch bản…</p> : <div className="table-wrap"><table className="biological-scenario-table"><thead><tr><th>Tên kịch bản</th><th>Loại</th><th>Mô</th><th>Bản cập nhật</th><th>Trạng thái</th><th>Cập nhật lúc</th><th>Thao tác</th></tr></thead><tbody>{scenarios.data?.items.map((scenario) => <tr key={scenario.id}><td><strong>{scenario.name}</strong></td><td>{scenarioTypeLabel(scenario.scenario_type)}</td><td>{scenario.tissue_context}</td><td>{scenario.revision}</td><td><span className={statusClass(scenario.status)}>{statusLabel(scenario.status)}</span></td><td>{dateLabel(scenario.updated_at)}</td><td><div className="table-actions"><button className="button-secondary" onClick={() => choose(scenario)}>Mở</button><button className="button-secondary" disabled={busy} onClick={() => { choose(scenario); cloneMutation.mutate(scenario.id) }}>Sao chép</button><button className="button-secondary" disabled={busy} onClick={() => reportMutation.mutate(scenario)}>Tạo báo cáo</button></div></td></tr>)}</tbody></table></div>}{!scenarios.isPending && !scenarios.data?.items.length && <div className="empty-state biological-empty-state"><strong>Chưa có kịch bản</strong><p>Tạo kịch bản đầu tiên để lưu bối cảnh và giả định độc lập. Không cần tạo bài kiểm tra máy.</p><button onClick={() => { setSelectedId(undefined); setShowForm(true); setForm(emptyForm()) }}>+ Tạo kịch bản đầu tiên</button></div>}</section>

      <aside className="biological-side-column"><section className="panel biological-provenance-panel"><div className="panel-heading"><div><p className="eyebrow">NGUỒN VÀ DẤU VẾT</p><h2>Mỗi kết quả đều truy lại được</h2></div></div><ul><li><strong>Mô hình</strong><span>Tên và phiên bản phép tính</span></li><li><strong>Nguồn</strong><span>Tài liệu hoặc ghi chú do người dùng nhập</span></li><li><strong>Giả định</strong><span>Các điều kiện dùng trong phép tính</span></li><li><strong>Bản cập nhật</strong><span>Thời điểm và nội dung đã lưu</span></li></ul><p className="form-hint">Kịch bản là vùng dữ liệu độc lập. Hồ sơ kiểm tra máy và hồ sơ người bệnh không tự động được đưa vào đây.</p></section><section className="panel biological-workflow-panel"><div className="panel-heading"><div><p className="eyebrow">QUY TRÌNH</p><h2>Cách sử dụng</h2></div></div><ol><li>Chọn công cụ</li><li>Nhập bối cảnh và giả định</li><li>Lưu bản cập nhật</li><li>Thực hiện tính toán</li><li>Kiểm tra lại giả định</li><li>Xuất báo cáo độc lập</li></ol><p className="form-hint">Mỗi công cụ chỉ mở khi phần tính toán và kiểm thử tương ứng đã sẵn sàng.</p></section></aside>
    </div>

    {(showForm || current) && <section className="panel biological-editor-panel"><div className="panel-heading"><div><p className="eyebrow">{showForm ? 'TẠO KỊCH BẢN' : 'CHỈNH SỬA KỊCH BẢN'}</p><h2>{showForm ? 'Tạo kịch bản mới' : current?.name}</h2></div>{current && <span className={statusClass(current.status)}>{statusLabel(current.status)} · bản {current.revision}</span>}</div>{current && !showForm && <div className="protocol-meta"><span>Cập nhật {dateLabel(current.updated_at)}</span></div>}<div className="biological-form-grid"><label>Tên hiển thị<input required disabled={!editable} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Ví dụ: Phác đồ vùng đầu cổ" /></label><label>Loại kịch bản<input disabled={!editable} value={scenarioTypeLabel(form.scenario_type)} onChange={(event) => setForm({ ...form, scenario_type: event.target.value })} /></label><label>Mô hoặc cơ quan<input disabled={!editable} value={form.tissue_context} onChange={(event) => setForm({ ...form, tissue_context: event.target.value })} placeholder="Ví dụ: Vú, phổi, tủy sống" /></label><label>Nguồn thông tin<select disabled={!editable} value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value as SourceType })}>{sourceTypes.map((item) => <option key={item} value={item}>{sourceTypeLabels[item]}</option>)}</select></label><label className="biological-form-grid__wide">Tài liệu tham khảo<input disabled={!editable} value={form.source_reference ?? ''} onChange={(event) => setForm({ ...form, source_reference: event.target.value })} placeholder="Tên tài liệu, đường dẫn hoặc ghi chú nguồn" /></label><label className="biological-form-grid__wide">Bối cảnh sử dụng<textarea disabled={!editable} value={form.clinical_context ?? ''} onChange={(event) => setForm({ ...form, clinical_context: event.target.value })} placeholder="Mô tả ngắn mục đích sử dụng; không nhập thông tin nhận diện người bệnh." /></label><label className="biological-form-grid__wide">Giả định và ghi chú<textarea disabled={!editable} value={form.assumptions_text} onChange={(event) => setForm({ ...form, assumptions_text: event.target.value })} placeholder="Mỗi dòng một nội dung, có thể viết theo mẫu: Tên thông tin: Giá trị" /></label></div><div className="biological-editor-actions">{editable && <><button disabled={busy} onClick={() => { const body = buildBody(); if (body) validateMutation.mutate(body) }}>Kiểm tra thông tin</button><button disabled={busy} onClick={submit}>{showForm ? 'Tạo bản nháp' : 'Lưu bản cập nhật'}</button></>}{current && <><button className="button-secondary" disabled={busy} onClick={() => cloneMutation.mutate(current.id)}>Tạo bản sao</button>{current.status === 'DRAFT' && <button disabled={busy} onClick={() => saveMutation.mutate()}>Xác nhận lưu</button>}{current.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => archiveMutation.mutate()}>Lưu trữ</button>}</>}</div>{current && <p className="form-hint">Kịch bản đã lưu là bản chụp cố định; nếu muốn thử giả định mới, hãy tạo bản sao để chỉnh sửa độc lập.</p>}</section>}

    {showHistory && <section className="panel biological-history-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ</p><h2>Lịch sử cập nhật</h2></div></div>{!selectedId ? <p className="empty-state">Chọn một kịch bản để xem lịch sử cập nhật. Chưa có phép tính nào được tạo ở khu vực này.</p> : history.isPending ? <p>Đang tải lịch sử…</p> : history.error ? <div className="alert alert--error"><p>{errorMessage(history.error)}</p><button onClick={() => void history.refetch()}>Thử lại</button></div> : <><p className="form-hint">Lịch sử được lưu theo từng bản cập nhật và không tự ý thay đổi.</p><div className="table-wrap"><table><thead><tr><th>Bản cập nhật</th><th>Trạng thái</th><th>Thời điểm lưu</th></tr></thead><tbody>{history.data?.map((revision) => <tr key={revision.id}><td>Lần {revision.revision_number}</td><td>{statusLabel(revision.status)}</td><td>{dateLabel(revision.created_at)}</td></tr>)}</tbody></table></div></>}</section>}
  </div>
}
