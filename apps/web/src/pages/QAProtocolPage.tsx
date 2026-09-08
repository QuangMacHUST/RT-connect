import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { ApiClientError, apiClient, type QAProtocolCreateInput, type QAProtocolDefinitionInput, type QAProtocolResource, type QAProtocolRuleInput } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type SourceType = NonNullable<QAProtocolCreateInput['source_type']>
type FormState = QAProtocolDefinitionInput & { applicability_text: string; source_type: SourceType }

const sourceTypes: SourceType[] = ['USER_DEFINED', 'REFERENCE', 'INTERNAL', 'SITE_APPROVED']
const ruleTypes = ['RANGE', 'MAX', 'MIN', 'ABSOLUTE_DEVIATION', 'PERCENT_DEVIATION', 'NA']

function emptyRule(): QAProtocolRuleInput {
  return {
    metric_key: 'new_metric', display_name: 'New metric', unit: '%', rule_type: 'RANGE',
    target_value: null, lower_limit: 0, upper_limit: 100, tolerance: null, action_level: null,
    required: true, sort_order: 0, note: null, reference: null
  }
}

function emptyForm(): FormState {
  return {
    protocol_key: 'NEW_PROTOCOL', name: 'New QA protocol', qa_type: 'Machine QA',
    description: '', effective_note: '', applicability: {}, applicability_text: '{}',
    source_type: 'USER_DEFINED', source_reference: null, rules: [emptyRule()]
  }
}

function formFromProtocol(protocol: QAProtocolResource): FormState {
  return {
    protocol_key: protocol.protocol_key, name: protocol.name, qa_type: protocol.qa_type,
    description: protocol.description ?? '', effective_note: protocol.effective_note ?? '',
    applicability: protocol.applicability, applicability_text: JSON.stringify(protocol.applicability, null, 2),
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
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
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
      setMessage(`Đã tạo protocol ${protocol.protocol_key} v${protocol.version_number} ở trạng thái ${protocol.status}.`)
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const updateMutation = useMutation({
    mutationFn: (body: Parameters<typeof apiClient.updateQAProtocol>[3]) => apiClient.updateQAProtocol(accessToken!, organizationId!, selected!.id, body),
    onSuccess: (protocol) => {
      setForm(formFromProtocol(protocol)); setMessage(`Đã lưu bản nháp, revision ${protocol.revision}.`); refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validateMutation = useMutation({
    mutationFn: (body: QAProtocolDefinitionInput) => apiClient.validateQAProtocol(accessToken!, organizationId!, body),
    onSuccess: (result) => setValidationMessage(result.valid ? 'Protocol hợp lệ; chưa ghi vào database.' : result.errors.map((item) => `${item.field ?? 'protocol'}: ${item.message} (${item.code})`).join(' | ')),
    onError: (error) => setValidationMessage(errorMessage(error))
  })
  const activateMutation = useMutation({
    mutationFn: () => apiClient.activateQAProtocol(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (protocol) => { setForm(formFromProtocol(protocol)); setMessage(`Đã kích hoạt ${protocol.protocol_key} v${protocol.version_number}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const archiveMutation = useMutation({
    mutationFn: () => apiClient.archiveQAProtocol(accessToken!, organizationId!, selected!.id, selected!.revision),
    onSuccess: (protocol) => { setForm(formFromProtocol(protocol)); setMessage(`Đã archive ${protocol.protocol_key} v${protocol.version_number}; lịch sử cũ vẫn đọc được.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cloneMutation = useMutation({
    mutationFn: () => apiClient.cloneQAProtocol(accessToken!, organizationId!, selected!.id),
    onSuccess: (protocol) => { setSelectedId(protocol.id); setNewDraft(false); setForm(formFromProtocol(protocol)); setMessage(`Đã clone thành ${protocol.protocol_key} v${protocol.version_number}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending) return <main className="auth-state">Đang tải QA Protocol Library…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở QA Protocol Library</h1><p>{errorMessage(bootstrap.error)}</p></section></div>

  const buildDefinition = (): QAProtocolDefinitionInput | undefined => {
    let applicability: Record<string, unknown>
    try {
      const parsed: unknown = JSON.parse(form.applicability_text || '{}')
      if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') throw new Error('JSON applicability phải là object.')
      applicability = parsed as Record<string, unknown>
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Applicability JSON không hợp lệ.')
      return undefined
    }
    return {
      protocol_key: form.protocol_key, name: form.name, qa_type: form.qa_type,
      description: form.description || null, effective_note: form.effective_note || null,
      applicability, source_type: form.source_type, source_reference: form.source_reference || null,
      rules: form.rules
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
      <div><p className="eyebrow">P11 · MOD-09</p><h1>QA Protocol Library</h1><p>Quản lý protocol theo family/version, rule, nguồn tham chiếu và applicability. ACTIVE/ARCHIVED không sửa tại chỗ; hãy clone để tạo version mới.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">QA Archive</Link><span className="status-badge">API THẬT</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {validationMessage && <section className={validationMessage.startsWith('Protocol hợp lệ') ? 'alert alert--success' : 'alert alert--warning'} role="status"><p>{validationMessage}</p></section>}
    {protocols.error && <section className="alert alert--error"><p>{errorMessage(protocols.error)}</p><button onClick={() => void protocols.refetch()}>Thử lại</button></section>}

    <div className="protocol-layout">
      <aside className="panel protocol-list-panel">
        <div className="panel-heading"><div><p className="eyebrow">LIBRARY</p><h2>Protocol versions</h2></div><strong>{protocols.data?.total ?? '—'}</strong></div>
        <div className="protocol-search"><label>Tìm kiếm<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="protocol key, tên, QA type" /></label><label>Trạng thái<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as typeof statusFilter)}><option value="ALL">Tất cả</option><option value="DRAFT">DRAFT</option><option value="ACTIVE">ACTIVE</option><option value="ARCHIVED">ARCHIVED</option></select></label><label className="checkbox-row"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} /> Hiện archived</label></div>
        <button disabled={busy} onClick={() => { setSelectedId(undefined); setNewDraft(true); setForm(emptyForm()); setMessage(undefined); setValidationMessage(undefined) }}>+ Tạo protocol draft</button>
        {protocols.isPending ? <p>Đang tải…</p> : <div className="protocol-list">{protocols.data?.items.map((protocol) => <button key={protocol.id} className={protocol.id === selected?.id && !newDraft ? 'protocol-list__item protocol-list__item--selected' : 'protocol-list__item'} onClick={() => choose(protocol)}><span><strong>{protocol.name}</strong><small>{protocol.protocol_key} · v{protocol.version_number}</small></span><span className={statusClass(protocol.status)}>{protocol.status}</span></button>)}</div>}
        {!protocols.isPending && !protocols.data?.items.length && <p className="empty-state">Chưa có version phù hợp. Tạo draft đầu tiên hoặc bật archived.</p>}
      </aside>

      <main className="protocol-editor-column">
        <section className="panel protocol-editor-panel">
          <div className="panel-heading"><div><p className="eyebrow">{newDraft ? 'NEW DRAFT' : 'PROTOCOL VERSION'}</p><h2>{newDraft ? 'Tạo protocol mới' : selected?.name ?? 'Chọn protocol'}</h2></div>{selected && <span className={statusClass(selected.status)}>{selected.status} · rev {selected.revision}</span>}</div>
          {!newDraft && !selected ? <p className="empty-state">Chọn một protocol ở danh sách bên trái.</p> : <>
            {selected && <div className="protocol-meta"><span><strong>{selected.protocol_key}</strong> · v{selected.version_number}</span><span>Tạo {dateLabel(selected.created_at)}</span><span>Cập nhật {dateLabel(selected.updated_at)}</span>{selected.source_protocol_version_id && <span>Clone từ <code>{selected.source_protocol_version_id.slice(0, 8)}…</code></span>}</div>}
            <div className="protocol-form-grid"><label>Protocol key<input disabled={!editable} value={form.protocol_key} onChange={(event) => setForm({ ...form, protocol_key: event.target.value })} /></label><label>Tên hiển thị<input disabled={!editable} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>QA type<input disabled={!editable} value={form.qa_type} onChange={(event) => setForm({ ...form, qa_type: event.target.value })} /></label><label>Source type<select disabled={!editable} value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value as SourceType })}>{sourceTypes.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label>Source reference<input disabled={!editable} value={form.source_reference ?? ''} onChange={(event) => setForm({ ...form, source_reference: event.target.value || null })} placeholder="DOI, guideline, local document…" /></label><label>Mô tả<textarea disabled={!editable} value={form.description ?? ''} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><label>Ghi chú hiệu lực<textarea disabled={!editable} value={form.effective_note ?? ''} onChange={(event) => setForm({ ...form, effective_note: event.target.value })} /></label><label>Applicability JSON<textarea disabled={!editable} value={form.applicability_text} onChange={(event) => setForm({ ...form, applicability_text: event.target.value })} /></label></div>
            <div className="protocol-rule-heading"><div><p className="eyebrow">RULE SET</p><h3>Metric rules</h3></div>{editable && <button className="button-secondary" onClick={() => setForm({ ...form, rules: [...form.rules, { ...emptyRule(), sort_order: form.rules.length }] })}>+ Thêm rule</button>}</div>
            <div className="table-wrap"><table className="protocol-rule-table"><thead><tr><th>Key</th><th>Tên</th><th>Unit</th><th>Type</th><th>Target</th><th>Min</th><th>Max</th><th>Tolerance</th><th>Action</th><th>Bắt buộc</th><th>Source/note</th><th /></tr></thead><tbody>{form.rules.map((rule, index) => <tr key={`${rule.metric_key}-${index}`}><td><input disabled={!editable} value={rule.metric_key} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, metric_key: event.target.value } : item) })} /></td><td><input disabled={!editable} value={rule.display_name} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, display_name: event.target.value } : item) })} /></td><td><input disabled={!editable} value={rule.unit} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, unit: event.target.value } : item) })} /></td><td><select disabled={!editable} value={rule.rule_type} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, rule_type: event.target.value } : item) })}>{ruleTypes.map((item) => <option key={item} value={item}>{item}</option>)}</select></td>{(['target_value', 'lower_limit', 'upper_limit', 'tolerance', 'action_level'] as const).map((field) => <td key={field}><input disabled={!editable} type="number" step="any" value={rule[field] ?? ''} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, [field]: numericValue(event.target.value) } : item) })} /></td>)}<td><input disabled={!editable} type="checkbox" checked={rule.required} onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, required: event.target.checked } : item) })} /></td><td><input disabled={!editable} value={rule.reference ?? ''} placeholder="Nguồn" onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, reference: event.target.value || null } : item) })} /><input disabled={!editable} value={rule.note ?? ''} placeholder="Ghi chú" onChange={(event) => setForm({ ...form, rules: form.rules.map((item, itemIndex) => itemIndex === index ? { ...item, note: event.target.value || null } : item) })} /></td><td>{editable && <button className="button-secondary" disabled={form.rules.length <= 1} onClick={() => setForm({ ...form, rules: form.rules.filter((_, itemIndex) => itemIndex !== index) })}>Xóa</button>}</td></tr>)}</tbody></table></div>
            <div className="protocol-editor-actions">{editable && <><button disabled={busy} onClick={() => { const definition = buildDefinition(); if (definition) validateMutation.mutate(definition) }}>Kiểm tra protocol</button><button disabled={busy} onClick={submit}>{newDraft ? 'Tạo bản nháp' : 'Lưu bản nháp'}</button></>}{selected && <><button className="button-secondary" disabled={busy} onClick={() => cloneMutation.mutate()}>Clone version</button>{selected.status === 'DRAFT' && <button disabled={busy} onClick={() => activateMutation.mutate()}>Kích hoạt</button>}{selected.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => archiveMutation.mutate()}>Archive</button>}</>}</div>
            <p className="form-hint">Lưu draft không làm protocol được dùng cho Machine QA. Chỉ version ACTIVE mới được chọn cho run mới; sau khi active, mọi thay đổi phải clone sang version kế tiếp.</p>
          </>}
        </section>

        {selected && <section className="panel protocol-compare-panel"><div className="panel-heading"><div><p className="eyebrow">VERSION DIFF</p><h2>So sánh protocol</h2></div></div><label>Đối chiếu với<select value={compareId} onChange={(event) => setCompareId(event.target.value)}><option value="">Chọn version</option>{otherProtocols.map((protocol) => <option key={protocol.id} value={protocol.id}>{protocol.protocol_key} · v{protocol.version_number} · {protocol.status}</option>)}</select></label>{comparison.isPending && <p>Đang so sánh…</p>}{comparison.error && <p className="error-text">{errorMessage(comparison.error)}</p>}{comparison.data && <div className="diff-grid"><div><strong>Metadata khác: {comparison.data.metadata_diffs.length}</strong>{comparison.data.metadata_diffs.map((item) => <p key={item.field}><code>{item.field}</code>: {JSON.stringify(item.left)} → {JSON.stringify(item.right)}</p>)}</div><div><strong>Rule khác: {comparison.data.rule_diffs.length}</strong>{comparison.data.rule_diffs.map((item) => <p key={item.field}><code>{item.field}</code>: <span className="table-subtitle">{JSON.stringify(item.left)} → {JSON.stringify(item.right)}</span></p>)}</div></div>}</section>}
      </main>
    </div>
  </div>
}
