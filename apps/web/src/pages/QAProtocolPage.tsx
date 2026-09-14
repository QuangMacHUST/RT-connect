import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { ApiClientError, apiClient, type QAProtocolCreateInput, type QAProtocolDefinitionInput, type QAProtocolResource, type QAProtocolRuleInput } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type SourceType = NonNullable<QAProtocolCreateInput['source_type']>
type ApplicabilityKey = 'site_ids' | 'machine_ids' | 'qa_cycles' | 'qa_types' | 'energies' | 'beam_qualities' | 'techniques' | 'detectors' | 'phantoms'
type FormState = QAProtocolDefinitionInput & { applicability_values: Record<ApplicabilityKey, string>; source_type: SourceType }

const sourceTypes: SourceType[] = ['USER_DEFINED', 'REFERENCE', 'INTERNAL', 'SITE_APPROVED']
const ruleTypes = ['RANGE', 'MAX', 'MIN', 'ABSOLUTE_DEVIATION', 'PERCENT_DEVIATION', 'NA']
const sourceTypeLabels: Record<SourceType, string> = {
  USER_DEFINED: 'Tự xây dựng', REFERENCE: 'Theo tài liệu tham khảo', INTERNAL: 'Quy định nội bộ', SITE_APPROVED: 'Đã được cơ sở phê duyệt'
}
const ruleTypeLabels: Record<string, string> = {
  RANGE: 'Nằm trong khoảng', MAX: 'Không vượt quá', MIN: 'Không thấp hơn',
  ABSOLUTE_DEVIATION: 'Độ lệch tuyệt đối', PERCENT_DEVIATION: 'Độ lệch phần trăm', NA: 'Không áp dụng'
}
const applicabilityDimensions: Array<{ key: ApplicabilityKey; label: string; placeholder: string }> = [
  { key: 'site_ids', label: 'Cơ sở áp dụng', placeholder: 'Ví dụ: Cơ sở trung tâm, Cơ sở 2' },
  { key: 'machine_ids', label: 'Máy áp dụng', placeholder: 'Ví dụ: Máy 1, Máy 2' },
  { key: 'qa_cycles', label: 'Chu kỳ thực hiện', placeholder: 'Ví dụ: Hằng ngày, Hằng tháng' },
  { key: 'qa_types', label: 'Loại bài kiểm tra', placeholder: 'Ví dụ: Picket Fence, Starshot' },
  { key: 'energies', label: 'Năng lượng', placeholder: 'Ví dụ: 6X, 10X' },
  { key: 'beam_qualities', label: 'Chất lượng chùm tia', placeholder: 'Nhập các giá trị, cách nhau bằng dấu phẩy' },
  { key: 'techniques', label: 'Kỹ thuật', placeholder: 'Ví dụ: 3D, VMAT, SBRT' },
  { key: 'detectors', label: 'Đầu dò', placeholder: 'Ví dụ: EPID, ion hóa' },
  { key: 'phantoms', label: 'Mô hình kiểm tra', placeholder: 'Ví dụ: CatPhan, mô hình nước' }
]
const ruleFieldLabels: Record<string, string> = {
  target_value: 'Giá trị chuẩn', lower_limit: 'Giới hạn dưới', upper_limit: 'Giới hạn trên',
  tolerance: 'Mức cảnh báo', action_level: 'Mức hành động'
}

function emptyApplicability(): Record<ApplicabilityKey, string> {
  return Object.fromEntries(applicabilityDimensions.map(({ key }) => [key, ''])) as Record<ApplicabilityKey, string>
}

function applicabilityToText(applicability: Record<string, unknown>): Record<ApplicabilityKey, string> {
  const values = emptyApplicability()
  for (const { key } of applicabilityDimensions) {
    const raw = applicability[key]
    values[key] = Array.isArray(raw) ? raw.filter((item): item is string => typeof item === 'string').join(', ') : ''
  }
  return values
}

function textToApplicability(values: Record<ApplicabilityKey, string>): Record<string, object> {
  return Object.fromEntries(
    applicabilityDimensions
      .map(({ key }) => [key, values[key].split(/[,;\n]/).map((item) => item.trim()).filter(Boolean)])
      .filter(([, items]) => (items as string[]).length > 0)
  )
}

function protocolKeyFromName(name: string): string {
  const key = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_+|_+$/g, '')
  return (key || 'QA_PROTOCOL').slice(0, 120)
}

function metricKeyFromName(name: string, index: number): string {
  const key = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().replace(/[^a-z0-9]+/g, '_').replace(/^_+|_+$/g, '')
  return `${key || 'chi_so'}_${index + 1}`.slice(0, 120)
}

function sourceTypeLabel(value: string): string {
  return sourceTypeLabels[value as SourceType] ?? 'Nguồn khác'
}

function statusLabel(value: string): string {
  if (value === 'ACTIVE') return 'Đang áp dụng'
  if (value === 'ARCHIVED') return 'Đã lưu trữ'
  return 'Bản nháp'
}

function fieldLabel(value: string | null): string {
  if (!value) return 'Nội dung'
  const applicability = value.match(/^applicability\.(.+)$/)?.[1]
  if (applicability) return applicabilityDimensions.find((item) => item.key === applicability)?.label ?? 'Phạm vi áp dụng'
  const rule = value.match(/^rules\.\d+\.(.+)$/)?.[1]
  if (rule) return `Tiêu chí ${ruleFieldLabels[rule] ?? 'bài kiểm tra'}`
  if (value === 'rules') return 'Danh sách tiêu chí'
  const labels: Record<string, string> = { protocol_key: 'Tên bài kiểm tra', name: 'Tên hiển thị', qa_type: 'Nhóm bài kiểm tra', source_type: 'Nguồn tài liệu', source_reference: 'Tài liệu tham khảo' }
  return labels[value] ?? 'Nội dung'
}

function friendlyValidationMessage(message: string): string {
  const messages: Array<[string, string]> = [
    ['Numeric values must be finite.', 'Giá trị số phải là một số hợp lệ.'],
    ['Tolerance and action level cannot be negative.', 'Mức cảnh báo và mức hành động không được âm.'],
    ['RANGE requires lower and upper limits.', 'Tiêu chí “Nằm trong khoảng” cần có giới hạn dưới và giới hạn trên.'],
    ['Lower limit cannot exceed upper limit.', 'Giới hạn dưới không được lớn hơn giới hạn trên.'],
    ['MAX requires an upper limit or tolerance.', 'Tiêu chí “Không vượt quá” cần có giới hạn trên hoặc mức cảnh báo.'],
    ['MIN requires a lower limit or tolerance.', 'Tiêu chí “Không thấp hơn” cần có giới hạn dưới hoặc mức cảnh báo.'],
    ['Metric key is duplicated in this protocol version.', 'Có tiêu chí bị trùng tên trong cùng phiên bản.'],
    ['Display name is required.', 'Cần nhập tên tiêu chí.'],
    ['Unit is required.', 'Cần nhập đơn vị đo.'],
    ['Reference source is required for REFERENCE protocols.', 'Bài kiểm tra theo tài liệu tham khảo cần có nguồn tài liệu.']
  ]
  return messages.find(([english]) => message === english)?.[1] ?? message
}

function displayValue(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—'
  if (Array.isArray(value)) return value.map(displayValue).join(', ')
  if (typeof value === 'object') return Object.entries(value as Record<string, unknown>).map(([key, item]) => `${fieldLabel(key)}: ${displayValue(item)}`).join('; ')
  return String(value)
}

function emptyRule(): QAProtocolRuleInput {
  return {
    metric_key: 'new_metric', display_name: 'Chỉ số mới', unit: '%', rule_type: 'RANGE',
    target_value: null, lower_limit: 0, upper_limit: 100, tolerance: null, action_level: null,
    required: true, sort_order: 0, note: null, reference: null
  }
}

function emptyForm(): FormState {
  return {
    protocol_key: 'NEW_PROTOCOL', name: 'Bài kiểm tra mới', qa_type: 'Kiểm tra chất lượng máy',
    description: '', effective_note: '', applicability: {}, applicability_values: emptyApplicability(),
    source_type: 'USER_DEFINED', source_reference: null, rules: [emptyRule()]
  }
}

function formFromProtocol(protocol: QAProtocolResource): FormState {
  return {
    protocol_key: protocol.protocol_key, name: protocol.name, qa_type: protocol.qa_type,
    description: protocol.description ?? '', effective_note: protocol.effective_note ?? '',
    applicability: protocol.applicability, applicability_values: applicabilityToText(protocol.applicability),
    source_type: sourceTypes.includes(protocol.source_type as SourceType) ? protocol.source_type as SourceType : 'USER_DEFINED',
    source_reference: protocol.source_reference, rules: protocol.rules.map((rule) => ({
      metric_key: rule.metric_key, display_name: rule.display_name, unit: rule.unit, rule_type: rule.rule_type,
      target_value: rule.target_value, lower_limit: rule.lower_limit, upper_limit: rule.upper_limit,
      tolerance: rule.tolerance, action_level: rule.action_level, required: rule.required,
      sort_order: rule.sort_order, note: rule.note, reference: rule.reference
    }))
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function numericValue(value: string): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

function dateLabel(value: string): string {
  return new Date(value).toLocaleString('vi-VN')
}

function statusClass(value: string): string {
  if (value === 'ACTIVE') return 'status-badge'
  if (value === 'ARCHIVED') return 'status-badge machine-status--fail'
  return 'status-badge machine-status--draft'
}

export function QAProtocolPage() {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const queryClient = useQueryClient()
  const bootstrap = useQuery({
    queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!),
    enabled: Boolean(accessToken), retry: false
  })
  const organizationId = bootstrap.data?.organization.id
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState<'ALL' | 'DRAFT' | 'ACTIVE' | 'ARCHIVED'>('ALL')
  const [includeArchived, setIncludeArchived] = useState(false)
  const protocols = useQuery({
    queryKey: ['qa-protocols', organizationId, accessToken, search, statusFilter, includeArchived],
    queryFn: () => apiClient.qaProtocols(accessToken!, organizationId!, {
      q: search || undefined, status: statusFilter === 'ALL' ? undefined : statusFilter,
      include_archived: includeArchived || statusFilter === 'ARCHIVED'
    }),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const [selectedId, setSelectedId] = useState<string>()
  const [newDraft, setNewDraft] = useState(false)
  const [form, setForm] = useState<FormState>(() => emptyForm())
  const [message, setMessage] = useState<string>()
  const [validationMessage, setValidationMessage] = useState<string>()
  const [compareId, setCompareId] = useState('')

  const selected = useMemo(
    () => protocols.data?.items.find((protocol) => protocol.id === selectedId),
    [protocols.data?.items, selectedId]
  )
  const editable = newDraft || selected?.status === 'DRAFT'
  const otherProtocols = protocols.data?.items.filter((protocol) => protocol.id !== selected?.id) ?? []
  const comparison = useQuery({
    queryKey: ['qa-protocol-compare', organizationId, selected?.id, compareId, accessToken],
    queryFn: () => apiClient.compareQAProtocols(accessToken!, organizationId!, selected!.id, compareId),
    enabled: Boolean(accessToken && organizationId && selected && compareId), retry: false
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['qa-protocols', organizationId] })
  }

  const choose = (protocol: QAProtocolResource) => {
    setSelectedId(protocol.id)
    setNewDraft(false)
    setForm(formFromProtocol(protocol))
    setValidationMessage(undefined)
    setCompareId('')
  }

  const createMutation = useMutation({
    mutationFn: (body: QAProtocolCreateInput) => apiClient.createQAProtocol(accessToken!, organizationId!, body),
    onSuccess: (protocol) => {
      setSelectedId(protocol.id); setNewDraft(false); setForm(formFromProtocol(protocol))
      setMessage(`Đã tạo bài kiểm tra ở trạng thái ${statusLabel(protocol.status)}.`)
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const updateMutation = useMutation({
    mutationFn: (body: Parameters<typeof apiClient.updateQAProtocol>[3]) => apiClient.updateQAProtocol(accessToken!, organizationId!, selected!.id, body),
    onSuccess: (protocol) => {
      setForm(formFromProtocol(protocol)); setMessage('Đã lưu bản nháp.'); refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validateMutation = useMutation({
    mutationFn: (body: QAProtocolDefinitionInput) => apiClient.validateQAProtocol(accessToken!, organizationId!, body),
    onSuccess: (result) => setValidationMessage(result.valid ? 'Thông tin hợp lệ; chưa lưu vào hệ thống.' : result.errors.map((item) => `${fieldLabel(item.field)}: ${friendlyValidationMessage(item.message)}`).join(' | ')),
    onError: (error) => setValidationMessage(errorMessage(error))
  })
  const activateMutation = useMutation({
    mutationFn: () => apiClient.activateQAProtocol(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (protocol) => { setForm(formFromProtocol(protocol)); setMessage('Đã kích hoạt bài kiểm tra.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const archiveMutation = useMutation({
    mutationFn: () => apiClient.archiveQAProtocol(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (protocol) => { setForm(formFromProtocol(protocol)); setMessage('Đã lưu trữ phiên bản; lịch sử cũ vẫn xem được.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cloneMutation = useMutation({
    mutationFn: () => apiClient.cloneQAProtocol(accessToken!, organizationId!, selected!.id),
    onSuccess: (protocol) => { setSelectedId(protocol.id); setNewDraft(false); setForm(formFromProtocol(protocol)); setMessage(`Đã tạo phiên bản nháp mới: ${protocol.name}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending) return <main className="auth-state">Đang tải thư viện quy trình QA…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở thư viện quy trình QA</h1><p>{errorMessage(bootstrap.error)}</p></section></div>

  const buildDefinition = (): QAProtocolDefinitionInput | undefined => {
    return {
      protocol_key: newDraft ? protocolKeyFromName(form.name) : form.protocol_key, name: form.name, qa_type: form.qa_type,
      description: form.description || null, effective_note: form.effective_note || null,
      applicability: textToApplicability(form.applicability_values), source_type: form.source_type, source_reference: form.source_reference || null,
      rules: form.rules.map((rule, index) => ({ ...rule, metric_key: rule.metric_key === 'new_metric' ? metricKeyFromName(rule.display_name, index) : rule.metric_key }))
    }
  }
  const submit = () => {
    const definition = buildDefinition()
    if (!definition) return
    setValidationMessage(undefined)
    if (newDraft) createMutation.mutate({ ...definition, activate: false })
    else if (selected?.status === 'DRAFT') updateMutation.mutate({ ...definition, expected_revision: selected.revision })
  }
  const busy = createMutation.isPending || updateMutation.isPending || validateMutation.isPending || activateMutation.isPending || archiveMutation.isPending || cloneMutation.isPending

  return <div className="page">
    <header className="page-header">
      <div><p className="eyebrow">THƯ VIỆN QUY TRÌNH QA</p><h1>Quy trình kiểm tra máy</h1><p>Tạo, kiểm tra và lưu các bộ tiêu chí dùng cho bài kiểm tra chất lượng máy. Phiên bản đang áp dụng không sửa trực tiếp; hãy tạo phiên bản mới khi cần thay đổi.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Mở lịch sử QA</Link><span className="status-badge">ĐANG KẾT NỐI</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {validationMessage && <section className={validationMessage.startsWith('Thông tin hợp lệ') ? 'alert alert--success' : 'alert alert--warning'} role="status"><p>{validationMessage}</p></section>}
    {protocols.error && <section className="alert alert--error"><p>{errorMessage(protocols.error)}</p><button onClick={() => void protocols.refetch()}>Thử lại</button></section>}

    <div className="protocol-layout">
      <aside className="panel protocol-list-panel">
        <div className="panel-heading"><div><p className="eyebrow">DANH SÁCH</p><h2>Các phiên bản</h2></div><strong>{protocols.data?.total ?? '—'}</strong></div>
        <div className="protocol-search"><label>Tìm kiếm<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tên bài hoặc nhóm kiểm tra" /></label><label>Trạng thái<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}><option value="ALL">Tất cả</option><option value="DRAFT">Bản nháp</option><option value="ACTIVE">Đang áp dụng</option><option value="ARCHIVED">Đã lưu trữ</option></select></label><label className="checkbox-row"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} /> Hiện bài đã lưu trữ</label></div>
        <button disabled={busy} onClick={() => { setSelectedId(undefined); setNewDraft(true); setForm(emptyForm()); setMessage(undefined); setValidationMessage(undefined) }}>+ Tạo bài kiểm tra</button>
        {protocols.isPending ? <p>Đang tải…</p> : <div className="protocol-list">{protocols.data?.items.map((protocol) => <button key={protocol.id} className={protocol.id === selected?.id && !newDraft ? 'protocol-list__item protocol-list__item--selected' : 'protocol-list__item'} onClick={() => choose(protocol)}><span><strong>{protocol.name}</strong><small>Phiên bản {protocol.version_number} · {statusLabel(protocol.status)}</small></span><span className={statusClass(protocol.status)}>{statusLabel(protocol.status)}</span></button>)}</div>}
        {!protocols.isPending && !protocols.data?.items.length && <p className="empty-state">Chưa có phiên bản phù hợp. Hãy tạo bài kiểm tra đầu tiên hoặc bật hiển thị bài đã lưu trữ.</p>}
      </aside>

      <main className="protocol-editor-column">
        <section className="panel protocol-editor-panel">
          <div className="panel-heading"><div><p className="eyebrow">{newDraft ? 'BẢN NHÁP MỚI' : 'PHIÊN BẢN QUY TRÌNH'}</p><h2>{newDraft ? 'Tạo bài kiểm tra mới' : selected?.name ?? 'Chọn bài kiểm tra'}</h2></div>{selected && <span className={statusClass(selected.status)}>{statusLabel(selected.status)}</span>}</div>
          {!newDraft && !selected ? <p className="empty-state">Chọn một bài kiểm tra ở danh sách bên trái.</p> : <>
            {selected && <div className="protocol-meta"><span>Phiên bản {selected.version_number}</span><span>Tạo ngày {dateLabel(selected.created_at)}</span><span>Cập nhật ngày {dateLabel(selected.updated_at)}</span></div>}
            <div className="protocol-form-grid"><label>Tên bài kiểm tra<input disabled={!editable} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} placeholder="Ví dụ: Kiểm tra đầu ra hằng ngày" /></label><label>Nhóm bài kiểm tra<input disabled={!editable} value={form.qa_type} onChange={(event) => setForm({ ...form, qa_type: event.target.value })} placeholder="Ví dụ: Kiểm tra chất lượng máy" /></label><label>Nguồn tài liệu<select disabled={!editable} value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value as SourceType })}>{sourceTypes.map((item) => <option key={item} value={item}>{sourceTypeLabel(item)}</option>)}</select></label><label>Tài liệu tham khảo<input disabled={!editable} value={form.source_reference ?? ''} onChange={(event) => setForm({ ...form, source_reference: event.target.value || null })} placeholder="Tên tài liệu, đường dẫn hoặc số hiệu" /></label><label>Mô tả<textarea disabled={!editable} value={form.description ?? ''} onChange={(event) => setForm({ ...form, description: event.target.value })} placeholder="Mục đích và cách sử dụng bài kiểm tra" /></label><label>Ghi chú áp dụng<textarea disabled={!editable} value={form.effective_note ?? ''} onChange={(event) => setForm({ ...form, effective_note: event.target.value })} placeholder="Lưu ý khi đánh giá kết quả" /></label></div>
            <div className="protocol-applicability"><div className="protocol-rule-heading"><div><p className="eyebrow">PHẠM VI ÁP DỤNG</p><h3>Điều kiện sử dụng</h3></div></div><p className="form-hint">Có thể nhập nhiều giá trị, cách nhau bằng dấu phẩy. Để trống nếu bài kiểm tra áp dụng cho mọi trường hợp.</p><div className="protocol-form-grid">{applicabilityDimensions.map(({ key, label, placeholder }) => <label key={key}>{label}<input disabled={!editable} value={form.applicability_values[key]} onChange={(event) => setForm({ ...form, applicability_values: { ...form.applicability_values, [key]: event.target.value } })} placeholder={placeholder} /></label>)}</div></div>
            <div className="protocol-rule-heading"><div><p className="eyebrow">CÁC TIÊU CHÍ ĐÁNH GIÁ</p><h3>Chỉ số và giới hạn</h3></div>{editable && <button className="button-secondary" onClick={() => setForm({ ...form, rules: [...form.rules, { ...emptyRule(), sort_order: form.rules.length }] })}>+ Thêm tiêu chí</button>}</div>
            <div className="table-wrap"><table className="protocol-rule-table"><thead><tr><th>Tên tiêu chí</th><th>Đơn vị</th><th>Cách đánh giá</th><th>Giá trị chuẩn</th><th>Giới hạn dưới</th><th>Giới hạn trên</th><th>Mức cảnh báo</th><th>Mức hành động</th><th>Bắt buộc</th><th>Nguồn và ghi chú</th><th /></tr></thead><tbody>{form.rules.map((rule, index) => <tr key={`${rule.metric_key}-${index}`}><td><input disabled={!editable} value={rule.display_name} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, display_name: event.target.value } : item) })} placeholder="Ví dụ: Độ lệch đầu ra" /></td><td><input disabled={!editable} value={rule.unit} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, unit: event.target.value } : item) })} placeholder="%" /></td><td><select disabled={!editable} value={rule.rule_type} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, rule_type: event.target.value } : item) })}>{ruleTypes.map((item) => <option key={item} value={item}>{ruleTypeLabels[item]}</option>)}</select></td>{(['target_value', 'lower_limit', 'upper_limit', 'tolerance', 'action_level'] as const).map((field) => <td key={field}><input aria-label={ruleFieldLabels[field]} disabled={!editable} type="number" step="any" value={rule[field] ?? ''} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: numericValue(event.target.value) } : item) })} /></td>)}<td><input aria-label="Tiêu chí bắt buộc" disabled={!editable} type="checkbox" checked={rule.required} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, required: event.target.checked } : item) })} /></td><td><input aria-label="Nguồn tài liệu của tiêu chí" disabled={!editable} value={rule.reference ?? ''} placeholder="Nguồn tài liệu" onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, reference: event.target.value || null } : item) })} /><input aria-label="Ghi chú của tiêu chí" disabled={!editable} value={rule.note ?? ''} placeholder="Ghi chú" onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, note: event.target.value || null } : item) })} /></td><td>{editable && <button className="button-secondary" disabled={form.rules.length <= 1} onClick={() => setForm({ ...form, rules: form.rules.filter((_, itemIndex) => itemIndex !== index) })}>Xóa</button>}</td></tr>)}</tbody></table></div>
            <div className="protocol-editor-actions">{editable && <><button disabled={busy} onClick={() => { const definition = buildDefinition(); if (definition) validateMutation.mutate(definition) }}>Kiểm tra thông tin</button><button disabled={busy} onClick={submit}>{newDraft ? 'Tạo bản nháp' : 'Lưu bản nháp'}</button></>}{selected && <><button className="button-secondary" disabled={busy} onClick={() => cloneMutation.mutate()}>Tạo phiên bản mới</button>{selected.status === 'DRAFT' && <button disabled={busy} onClick={() => activateMutation.mutate()}>Đưa vào áp dụng</button>}{selected.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => archiveMutation.mutate()}>Lưu trữ</button>}</>}</div>
            <p className="form-hint">Bản nháp chưa được dùng cho bài kiểm tra mới. Chỉ phiên bản đang áp dụng mới được chọn; khi cần sửa, hãy tạo phiên bản mới để giữ nguyên lịch sử.</p>
          </>}
        </section>

        {selected && <section className="panel protocol-compare-panel"><div className="panel-heading"><div><p className="eyebrow">ĐỐI CHIẾU PHIÊN BẢN</p><h2>So sánh thay đổi</h2></div></div><label>Đối chiếu với<select value={compareId} onChange={(event) => setCompareId(event.target.value)}><option value="">Chọn phiên bản</option>{otherProtocols.map((protocol) => <option key={protocol.id} value={protocol.id}>Phiên bản {protocol.version_number} · {statusLabel(protocol.status)}</option>)}</select></label>{comparison.isPending && <p>Đang so sánh…</p>}{comparison.error && <p className="error-text">{errorMessage(comparison.error)}</p>}{comparison.data && <div className="diff-grid"><div><strong>Thông tin thay đổi: {comparison.data.metadata_diffs.length}</strong>{comparison.data.metadata_diffs.map((item) => <p key={item.field}><strong>{fieldLabel(item.field)}</strong>: {displayValue(item.left)} → {displayValue(item.right)}</p>)}</div><div><strong>Tiêu chí thay đổi: {comparison.data.rule_diffs.length}</strong>{comparison.data.rule_diffs.map((item) => <p key={item.field}><strong>{fieldLabel(item.field)}</strong>: <span className="table-subtitle">{displayValue(item.left)} → {displayValue(item.right)}</span></p>)}</div></div>}</section>}
      </main>
    </div>
  </div>
}
