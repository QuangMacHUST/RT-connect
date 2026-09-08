import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  ApiClientError,
  apiClient,
  type BiologicalLibraryDefinitionInput,
  type BiologicalLibraryEntryResource,
  type BiologicalLibraryUseResource
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type EntryType = BiologicalLibraryEntryResource['entry_type']
type EntryStatus = BiologicalLibraryEntryResource['status']
type SourceType = BiologicalLibraryEntryResource['source_type']
type ReferenceStatus = BiologicalLibraryEntryResource['reference_status']
type TargetTool = BiologicalLibraryUseResource['target_tool']

type LibraryForm = {
  entry_key: string
  entry_type: EntryType
  name: string
  description: string
  effective_note: string
  disease: string
  disease_subtype: string
  anatomy_site: string
  treatment_intent: string
  technique: string
  fractions: string
  tissue_or_oar: string
  metric_key: string
  operator: string
  limit_value: string
  lower_limit: string
  upper_limit: string
  unit: string
  volume_cc: string
  metric_parameter: string
  alpha_beta_gy: string
  model_key: string
  model_version: string
  applicability_text: string
  content_text: string
  source_type: SourceType
  source_reference: string
  reference_status: ReferenceStatus
  source_date: string
  evidence_level: string
  citation_text: string
}

const entryTypes: EntryType[] = ['DOSE_LIMIT', 'TREATMENT_PROTOCOL', 'KNOWLEDGE', 'ALPHA_BETA']
const statuses: Array<'ALL' | EntryStatus> = ['ALL', 'DRAFT', 'PUBLISHED', 'ARCHIVED']
const sourceTypes: SourceType[] = ['USER_DEFINED', 'REFERENCE', 'INTERNAL', 'SITE_APPROVED']
const referenceStatuses: ReferenceStatus[] = ['UNVERIFIED', 'AVAILABLE', 'UNAVAILABLE']
const targetTools: TargetTool[] = [
  'P13_BED_EQD2',
  'P14_PLAN_COMPARISON',
  'P15_REIRRADIATION',
  'P15_FRACTION_COMPENSATION',
  'P17_DVH',
  'KNOWLEDGE_REFERENCE'
]

function emptyForm(entryType: EntryType = 'DOSE_LIMIT'): LibraryForm {
  return {
    entry_key: entryType === 'DOSE_LIMIT' ? 'NEW_DOSE_LIMIT' : 'NEW_LIBRARY_ENTRY',
    entry_type: entryType,
    name: entryType === 'DOSE_LIMIT' ? 'New dose limit reference' : 'New biological library entry',
    description: '',
    effective_note: '',
    disease: '',
    disease_subtype: '',
    anatomy_site: '',
    treatment_intent: '',
    technique: '',
    fractions: '',
    tissue_or_oar: '',
    metric_key: entryType === 'DOSE_LIMIT' ? 'DMAX' : '',
    operator: entryType === 'DOSE_LIMIT' ? 'MAX' : '',
    limit_value: '',
    lower_limit: '',
    upper_limit: '',
    unit: entryType === 'DOSE_LIMIT' ? 'Gy' : '',
    volume_cc: '',
    metric_parameter: '',
    alpha_beta_gy: entryType === 'ALPHA_BETA' ? '10' : '',
    model_key: '',
    model_version: '',
    applicability_text: '{}',
    content_text: '{}',
    source_type: 'USER_DEFINED',
    source_reference: '',
    reference_status: 'UNVERIFIED',
    source_date: '',
    evidence_level: '',
    citation_text: '{}'
  }
}

function formFromEntry(entry: BiologicalLibraryEntryResource): LibraryForm {
  return {
    entry_key: entry.entry_key,
    entry_type: entry.entry_type,
    name: entry.name,
    description: entry.description ?? '',
    effective_note: entry.effective_note ?? '',
    disease: entry.disease ?? '',
    disease_subtype: entry.disease_subtype ?? '',
    anatomy_site: entry.anatomy_site ?? '',
    treatment_intent: entry.treatment_intent ?? '',
    technique: entry.technique ?? '',
    fractions: entry.fractions === null ? '' : String(entry.fractions),
    tissue_or_oar: entry.tissue_or_oar ?? '',
    metric_key: entry.metric_key ?? '',
    operator: entry.operator ?? '',
    limit_value: entry.limit_value === null ? '' : String(entry.limit_value),
    lower_limit: entry.lower_limit === null ? '' : String(entry.lower_limit),
    upper_limit: entry.upper_limit === null ? '' : String(entry.upper_limit),
    unit: entry.unit ?? '',
    volume_cc: entry.volume_cc === null ? '' : String(entry.volume_cc),
    metric_parameter: entry.metric_parameter === null ? '' : String(entry.metric_parameter),
    alpha_beta_gy: entry.alpha_beta_gy === null ? '' : String(entry.alpha_beta_gy),
    model_key: entry.model_key ?? '',
    model_version: entry.model_version ?? '',
    applicability_text: JSON.stringify(entry.applicability, null, 2),
    content_text: JSON.stringify(entry.content, null, 2),
    source_type: entry.source_type,
    source_reference: entry.source_reference ?? '',
    reference_status: entry.reference_status,
    source_date: entry.source_date ?? '',
    evidence_level: entry.evidence_level ?? '',
    citation_text: JSON.stringify(entry.citation, null, 2)
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
  if (value === 'PUBLISHED') return 'status-badge'
  if (value === 'ARCHIVED') return 'status-badge machine-status--fail'
  return 'status-badge machine-status--draft'
}

function numberOrNull(value: string, label: string): number | null {
  if (!value.trim()) return null
  const parsed = Number(value)
  if (!Number.isFinite(parsed)) throw new Error(`${label} phải là một số hữu hạn.`)
  return parsed
}

function integerOrNull(value: string, label: string): number | null {
  const parsed = numberOrNull(value, label)
  if (parsed !== null && !Number.isInteger(parsed)) throw new Error(`${label} phải là số nguyên.`)
  return parsed
}

function jsonObject(value: string, label: string): Record<string, unknown> {
  if (!value.trim()) return {}
  let parsed: unknown
  try {
    parsed = JSON.parse(value)
  } catch {
    throw new Error(`${label} phải là JSON hợp lệ.`)
  }
  if (parsed === null || Array.isArray(parsed) || typeof parsed !== 'object') {
    throw new Error(`${label} phải là một JSON object.`)
  }
  return parsed as Record<string, unknown>
}

function bodyFromForm(form: LibraryForm): BiologicalLibraryDefinitionInput {
  return {
    entry_key: form.entry_key,
    entry_type: form.entry_type,
    name: form.name,
    description: form.description || null,
    effective_note: form.effective_note || null,
    disease: form.disease || null,
    disease_subtype: form.disease_subtype || null,
    anatomy_site: form.anatomy_site || null,
    treatment_intent: form.treatment_intent || null,
    technique: form.technique || null,
    fractions: integerOrNull(form.fractions, 'Fractions'),
    tissue_or_oar: form.tissue_or_oar || null,
    metric_key: form.metric_key || null,
    operator: form.operator || null,
    limit_value: numberOrNull(form.limit_value, 'Limit value'),
    lower_limit: numberOrNull(form.lower_limit, 'Lower limit'),
    upper_limit: numberOrNull(form.upper_limit, 'Upper limit'),
    unit: form.unit || null,
    volume_cc: numberOrNull(form.volume_cc, 'Volume'),
    metric_parameter: numberOrNull(form.metric_parameter, 'Metric parameter'),
    alpha_beta_gy: numberOrNull(form.alpha_beta_gy, 'Alpha/beta'),
    model_key: form.model_key || null,
    model_version: form.model_version || null,
    applicability: jsonObject(form.applicability_text, 'Applicability'),
    content: jsonObject(form.content_text, 'Content'),
    source_type: form.source_type,
    source_reference: form.source_reference || null,
    reference_status: form.reference_status,
    source_date: form.source_date || null,
    evidence_level: form.evidence_level || null,
    citation: jsonObject(form.citation_text, 'Citation')
  }
}

function pretty(value: unknown): string {
  return JSON.stringify(value, null, 2)
}

function issueText(issue: { code: string; field: string | null; message: string }): string {
  return `${issue.field ?? 'entry'}: ${issue.message} (${issue.code})`
}

function DownloadButton({
  entry,
  format,
  accessToken,
  organizationId,
  onMessage
}: {
  entry: BiologicalLibraryEntryResource
  format: 'JSON' | 'CSV'
  accessToken: string
  organizationId: string
  onMessage: (message: string) => void
}) {
  return <button className="button-secondary" onClick={async () => {
    try {
      const blob = await apiClient.downloadBiologicalLibrary(accessToken, organizationId, entry.id, format)
      const url = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = url
      anchor.download = `rt-connect-biological-library-${entry.entry_key}-v${entry.version_number}.${format.toLowerCase()}`
      anchor.click()
      URL.revokeObjectURL(url)
      onMessage(`Đã tải ${format} của ${entry.entry_key} v${entry.version_number}.`)
    } catch (error) {
      onMessage(errorMessage(error))
    }
  }}>Tải {format}</button>
}

function ValidationPanel({
  validation
}: {
  validation: { valid: boolean; errors: Array<{ code: string; field: string | null; message: string }>; warnings: Array<{ code: string; field: string | null; message: string }> }
}) {
  return <section className={validation.valid ? 'bed-validation bed-validation--ok' : 'bed-validation bed-validation--error'} aria-live="polite">
    <strong>{validation.valid ? 'VALIDATION OK' : 'VALIDATION FAILED'}</strong>
    {validation.errors.length > 0 && <ul>{validation.errors.map((item, index) => <li key={`${item.code}-${index}`}>{issueText(item)}</li>)}</ul>}
    {validation.warnings.length > 0 && <div className="library-warning-list"><strong>Warnings không chặn:</strong><ul>{validation.warnings.map((item, index) => <li key={`${item.code}-${index}`}>{issueText(item)}</li>)}</ul></div>}
    {validation.valid && validation.errors.length === 0 && <p>Validate-only không ghi dữ liệu vào database.</p>}
  </section>
}

function DetailRows({ entry }: { entry: BiologicalLibraryEntryResource }) {
  return <div className="library-detail-grid">
    <div><span>Key / version</span><strong>{entry.entry_key} · v{entry.version_number}</strong></div>
    <div><span>Revision / status</span><strong>rev {entry.revision} · {entry.status}</strong></div>
    <div><span>Context</span><strong>{[entry.disease, entry.anatomy_site, entry.technique].filter(Boolean).join(' · ') || 'Chưa khai báo'}</strong></div>
    <div><span>Tissue / OAR</span><strong>{entry.tissue_or_oar ?? '—'}</strong></div>
    <div><span>Metric</span><strong>{[entry.metric_key, entry.operator, entry.limit_value, entry.unit].filter((item) => item !== null && item !== '').join(' ') || '—'}</strong></div>
    <div><span>Source</span><strong>{entry.source_type} · {entry.reference_status}</strong></div>
  </div>
}

export function KnowledgeLibraryPage() {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<EntryType | 'ALL'>('ALL')
  const [statusFilter, setStatusFilter] = useState<'ALL' | EntryStatus>('ALL')
  const [disease, setDisease] = useState('')
  const [anatomySite, setAnatomySite] = useState('')
  const [technique, setTechnique] = useState('')
  const [tissue, setTissue] = useState('')
  const [metric, setMetric] = useState('')
  const [fractions, setFractions] = useState('')
  const [includeArchived, setIncludeArchived] = useState(false)
  const [selectedId, setSelectedId] = useState<string>()
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState<LibraryForm>(() => emptyForm())
  const [message, setMessage] = useState<string>()
  const [validation, setValidation] = useState<{ valid: boolean; errors: Array<{ code: string; field: string | null; message: string }>; warnings: Array<{ code: string; field: string | null; message: string }> }>()
  const [showHistory, setShowHistory] = useState(false)
  const [compareId, setCompareId] = useState('')
  const [importText, setImportText] = useState('[\n  {\n    "entry_key": "EXAMPLE_LIMIT",\n    "entry_type": "DOSE_LIMIT",\n    "name": "Example reference",\n    "metric_key": "DMAX",\n    "operator": "MAX",\n    "limit_value": 45,\n    "unit": "Gy",\n    "source_type": "USER_DEFINED",\n    "content": { "note": "Replace with a verified source" }\n  }\n]')
  const [importPreview, setImportPreview] = useState<ReturnType<typeof apiClient.validateBiologicalLibraryImport> extends Promise<infer T> ? T : never>()
  const [targetTool, setTargetTool] = useState<TargetTool>('KNOWLEDGE_REFERENCE')
  const [overrideText, setOverrideText] = useState('{}')
  const [useResult, setUseResult] = useState<BiologicalLibraryUseResource>()

  const bootstrap = useQuery({ queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!), enabled: Boolean(accessToken), retry: false })
  const organizationId = bootstrap.data?.organization.id
  const library = useQuery({
    queryKey: ['biological-library', organizationId, accessToken, search, typeFilter, statusFilter, disease, anatomySite, technique, tissue, metric, fractions, includeArchived],
    queryFn: () => apiClient.biologicalLibrary(accessToken!, organizationId!, {
      q: search || undefined,
      entry_type: typeFilter === 'ALL' ? undefined : typeFilter,
      status: statusFilter === 'ALL' ? undefined : statusFilter,
      disease: disease || undefined,
      anatomy_site: anatomySite || undefined,
      technique: technique || undefined,
      tissue_or_oar: tissue || undefined,
      metric_key: metric || undefined,
      fractions: fractions.trim() ? Number(fractions) : undefined,
      include_archived: includeArchived || statusFilter === 'ARCHIVED'
    }),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const selected = useMemo(() => library.data?.items.find((item) => item.id === selectedId), [library.data?.items, selectedId])
  const detail = useQuery({
    queryKey: ['biological-library-entry', organizationId, selectedId, accessToken],
    queryFn: () => apiClient.biologicalLibraryEntry(accessToken!, organizationId!, selectedId!),
    enabled: Boolean(accessToken && organizationId && selectedId), retry: false
  })
  const current = detail.data ?? selected
  const history = useQuery({
    queryKey: ['biological-library-history', organizationId, selectedId, accessToken],
    queryFn: () => apiClient.biologicalLibraryRevisions(accessToken!, organizationId!, selectedId!),
    enabled: Boolean(accessToken && organizationId && selectedId && showHistory), retry: false
  })

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['biological-library', organizationId] })
    if (selectedId) {
      void queryClient.invalidateQueries({ queryKey: ['biological-library-entry', organizationId, selectedId] })
      void queryClient.invalidateQueries({ queryKey: ['biological-library-history', organizationId, selectedId] })
    }
  }
  const choose = (entry: BiologicalLibraryEntryResource) => {
    setSelectedId(entry.id)
    setShowForm(false)
    setForm(formFromEntry(entry))
    setValidation(undefined)
    setUseResult(undefined)
    setShowHistory(false)
  }

  const parseBody = (): BiologicalLibraryDefinitionInput | undefined => {
    try {
      return bodyFromForm(form)
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Entry không hợp lệ.')
      return undefined
    }
  }
  const createMutation = useMutation({
    mutationFn: (body: BiologicalLibraryDefinitionInput) => apiClient.createBiologicalLibraryEntry(accessToken!, organizationId!, body),
    onSuccess: (entry) => { setSelectedId(entry.id); setShowForm(false); setForm(formFromEntry(entry)); setMessage(`Đã tạo ${entry.entry_key} v${entry.version_number} ở trạng thái DRAFT.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const updateMutation = useMutation({
    mutationFn: (body: Parameters<typeof apiClient.updateBiologicalLibraryEntry>[3]) => apiClient.updateBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, body),
    onSuccess: (entry) => { setForm(formFromEntry(entry)); setMessage(`Đã lưu ${entry.entry_key}, revision ${entry.revision}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validateMutation = useMutation({
    mutationFn: (body: BiologicalLibraryDefinitionInput) => apiClient.validateBiologicalLibraryEntry(accessToken!, organizationId!, body),
    onSuccess: (result) => { setValidation({ valid: result.valid, errors: result.errors, warnings: result.warnings }); setMessage(result.valid ? 'Entry hợp lệ; validate-only chưa ghi database.' : 'Entry chưa hợp lệ; xem danh sách lỗi và sửa lại.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cloneMutation = useMutation({
    mutationFn: () => apiClient.cloneBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, { name: `${current!.name} · local copy` }),
    onSuccess: (entry) => { setSelectedId(entry.id); setShowForm(false); setForm(formFromEntry(entry)); setMessage(`Đã clone thành ${entry.entry_key} v${entry.version_number}; source vẫn giữ nguyên.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const publishMutation = useMutation({
    mutationFn: () => apiClient.publishBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, current!.revision),
    onSuccess: (entry) => { setForm(formFromEntry(entry)); setMessage(`Đã publish ${entry.entry_key} v${entry.version_number}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const archiveMutation = useMutation({
    mutationFn: () => apiClient.archiveBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, current!.revision),
    onSuccess: (entry) => { setForm(formFromEntry(entry)); setMessage(`Đã archive ${entry.entry_key}; lịch sử vẫn được giữ.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const compareMutation = useMutation({
    mutationFn: () => apiClient.compareBiologicalLibraryEntries(accessToken!, organizationId!, current!.id, compareId),
    onError: (error) => setMessage(errorMessage(error))
  })
  const useLibraryMutation = useMutation({
    mutationFn: () => apiClient.useBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, { target_tool: targetTool, override: jsonObject(overrideText, 'Override') }),
    onSuccess: (result) => { setUseResult(result); setMessage(`Đã tạo use snapshot ${result.snapshot_sha256.slice(0, 16)}…; chưa tự động áp dụng vào calculator.`) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const importPreviewMutation = useMutation({
    mutationFn: (rows: BiologicalLibraryDefinitionInput[]) => apiClient.validateBiologicalLibraryImport(accessToken!, organizationId!, rows),
    onSuccess: (result) => { setImportPreview(result); setMessage(`Đã kiểm tra ${result.rows.length} dòng; hợp lệ ${result.rows.filter((row) => row.valid).length}, loại ${result.rejected_count}.`) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const importCommitMutation = useMutation({
    mutationFn: (rows: BiologicalLibraryDefinitionInput[]) => apiClient.importBiologicalLibrary(accessToken!, organizationId!, rows, true),
    onSuccess: (result) => { setImportPreview(result); setMessage(`Đã import ${result.committed_count} dòng hợp lệ; ${result.rejected_count} dòng bị loại theo từng dòng.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const busy = createMutation.isPending || updateMutation.isPending || validateMutation.isPending || cloneMutation.isPending || publishMutation.isPending || archiveMutation.isPending || compareMutation.isPending || useLibraryMutation.isPending || importPreviewMutation.isPending || importCommitMutation.isPending

  if (bootstrap.isPending) return <main className="auth-state">Đang tải Biological Knowledge Library…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở thư viện Biological</h1><p>{errorMessage(bootstrap.error)}</p><Link className="button-link" to="/app/biological">Quay lại Biological Toolkit</Link></section></div>

  const editable = showForm || current?.status === 'DRAFT'
  const save = () => {
    const body = parseBody()
    if (!body) return
    setValidation(undefined)
    if (showForm) createMutation.mutate(body)
    else if (current?.status === 'DRAFT') updateMutation.mutate({ ...body, expected_revision: current.revision })
  }
  const validate = () => {
    const body = parseBody()
    if (body) validateMutation.mutate(body)
  }
  const parseImportRows = (): BiologicalLibraryDefinitionInput[] | undefined => {
    try {
      const parsed: unknown = JSON.parse(importText)
      if (!Array.isArray(parsed) || parsed.length === 0 || parsed.some((row) => row === null || typeof row !== 'object' || Array.isArray(row))) throw new Error('Import phải là một JSON array gồm các object.')
      return parsed as BiologicalLibraryDefinitionInput[]
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Import JSON không hợp lệ.')
      return undefined
    }
  }

  return <div className="page library-page">
    <header className="page-header"><div><p className="eyebrow">P16 · MOD-14 · BIOLOGICAL TOOLKIT</p><h1>Knowledge &amp; Reference Library</h1><p>Thư viện độc lập cho giới hạn liều, phác đồ điều trị, knowledge note và alpha/beta. Nội dung được version hóa, tìm kiếm theo context và chỉ được đưa vào phép tính khi user chủ động tạo snapshot.</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/biological">Biological Hub</Link><button onClick={() => { setShowForm(true); setSelectedId(undefined); setForm(emptyForm()); setValidation(undefined); setMessage(undefined) }}>+ Tạo entry</button></div></header>
    <section className="biological-notice library-notice" role="note"><strong>REFERENCE-ONLY · NO AUTO-APPLY</strong><span>Không chứa patient identifier, không phải prescription, không tự động trở thành QA tolerance và không tự động thay đổi P13–P15. Reference chưa xác minh vẫn được giữ lại nhưng hiển thị warning; dữ liệu nhập sai bị loại theo từng dòng.</span></section>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {library.error && <section className="alert alert--error" role="alert"><h2>Không tải được thư viện</h2><p>{errorMessage(library.error)}</p><button onClick={() => void library.refetch()}>Thử lại</button></section>}

    <section className="metric-grid library-metrics"><article className="metric-card"><p>Entries đang hiển thị</p><strong>{library.data?.total ?? '—'}</strong><small>Đã áp dụng filter hiện tại</small></article><article className="metric-card"><p>Published</p><strong>{library.data?.items.filter((item) => item.status === 'PUBLISHED').length ?? '—'}</strong><small>Reference có thể tạo use snapshot</small></article><article className="metric-card"><p>Draft</p><strong>{library.data?.items.filter((item) => item.status === 'DRAFT').length ?? '—'}</strong><small>Chỉ draft mới sửa trực tiếp</small></article><article className="metric-card library-metric-card--warning"><p>Reference status</p><strong>{library.data?.items.filter((item) => item.reference_status !== 'AVAILABLE').length ?? '—'}</strong><small>UNVERIFIED hoặc UNAVAILABLE cần review</small></article></section>

    <section className="library-filter-panel panel"><div className="panel-heading"><div><p className="eyebrow">SEARCH &amp; FILTER</p><h2>Tra cứu theo bệnh, giải phẫu và metric</h2></div><label className="checkbox-row"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} /> Hiện ARCHIVED</label></div><div className="library-filter-grid"><label>Tìm kiếm<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="key, tên, citation, nội dung…" /></label><label>Loại<select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as EntryType | 'ALL')}><option value="ALL">Tất cả</option>{entryTypes.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label>Trạng thái<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as 'ALL' | EntryStatus)}>{statuses.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label>Bệnh / mặt bệnh<input value={disease} onChange={(event) => setDisease(event.target.value)} placeholder="Lung cancer" /></label><label>Anatomy site<input value={anatomySite} onChange={(event) => setAnatomySite(event.target.value)} placeholder="Thorax" /></label><label>Technique<input value={technique} onChange={(event) => setTechnique(event.target.value)} placeholder="VMAT" /></label><label>Tissue / OAR<input value={tissue} onChange={(event) => setTissue(event.target.value)} placeholder="Spinal cord" /></label><label>Metric<input value={metric} onChange={(event) => setMetric(event.target.value)} placeholder="Dmax, V20…" /></label><label>Fractions<input type="number" min="1" step="1" value={fractions} onChange={(event) => setFractions(event.target.value)} placeholder="30" /></label></div></section>

    <div className="library-workspace-grid"><section className="panel library-list-panel"><div className="panel-heading"><div><p className="eyebrow">VERSIONED CONTENT</p><h2>Library entries</h2></div><strong>{library.data?.total ?? '—'}</strong></div>{library.isPending ? <p>Đang tải entries…</p> : library.data?.items.length ? <div className="table-wrap"><table className="library-table"><thead><tr><th>Entry</th><th>Type</th><th>Context</th><th>Value</th><th>Status</th><th>Updated</th><th></th></tr></thead><tbody>{library.data.items.map((entry) => <tr className={entry.id === current?.id ? 'is-selected' : undefined} key={entry.id}><td><strong>{entry.name}</strong><span className="table-subtitle">{entry.entry_key} · v{entry.version_number}</span></td><td>{entry.entry_type}</td><td><span className="table-subtitle">{[entry.disease, entry.anatomy_site, entry.technique, entry.tissue_or_oar].filter(Boolean).join(' · ') || 'Independent context'}</span></td><td>{[entry.metric_key, entry.limit_value, entry.unit].filter((item) => item !== null && item !== '').join(' ') || entry.alpha_beta_gy ? `${entry.metric_key ?? 'α/β'} ${entry.alpha_beta_gy ?? ''} ${entry.unit ?? 'Gy'}` : '—'}</td><td><span className={statusClass(entry.status)}>{entry.status}</span><span className="table-subtitle">{entry.reference_status}</span></td><td>{dateLabel(entry.updated_at)}</td><td><button className="button-secondary" onClick={() => choose(entry)}>Mở</button></td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>Chưa có entry phù hợp</strong><p>Hãy đổi filter hoặc tạo entry đầu tiên. Không cần tạo scenario/QA case để dùng thư viện.</p><button onClick={() => { setShowForm(true); setSelectedId(undefined); setForm(emptyForm()) }}>+ Tạo entry</button></div>}</section>

      <aside className="library-side-column"><section className="panel library-workflow-panel"><div className="panel-heading"><div><p className="eyebrow">SAFE WORKFLOW</p><h2>Vòng đời entry</h2></div></div><ol><li>Nhập structured fields và source</li><li>Validate-only để xem lỗi/warning</li><li>Tạo DRAFT hoặc import preview</li><li>Clone khi cần version mới</li><li>Publish sau khi review nội dung</li><li>Dùng snapshot có target tool rõ ràng</li></ol><p className="form-hint">Không có auto-fetch citation và không chạy nội dung active. Hash, revision, source và snapshot giúp mở lại đúng dữ liệu đã sử dụng.</p></section><section className="panel library-import-panel"><div className="panel-heading"><div><p className="eyebrow">BATCH IMPORT</p><h2>Import JSON theo từng dòng</h2></div></div><textarea value={importText} onChange={(event) => setImportText(event.target.value)} aria-label="JSON import rows" /><div className="library-editor-actions"><button disabled={busy} onClick={() => { const rows = parseImportRows(); if (rows) importPreviewMutation.mutate(rows) }}>Preview import</button><button className="button-secondary" disabled={busy || !importPreview?.rows.some((row) => row.valid)} onClick={() => { const rows = parseImportRows(); if (rows) importCommitMutation.mutate(rows) }}>Commit dòng hợp lệ</button></div>{importPreview && <div className="library-import-result"><strong>{importPreview.dry_run ? 'PREVIEW' : 'COMMITTED'}</strong><span>Hợp lệ {importPreview.rows.filter((row) => row.valid).length} · loại {importPreview.rejected_count}</span>{importPreview.rows.filter((row) => !row.valid).slice(0, 3).map((row) => <small key={row.row_number}>Row {row.row_number}: {row.errors.map((item) => item.code).join(', ')}</small>)}</div>}</section></aside></div>

    {(showForm || current) && <section className="panel library-editor-panel"><div className="panel-heading"><div><p className="eyebrow">{showForm ? 'NEW DRAFT' : 'ENTRY EDITOR'}</p><h2>{showForm ? 'Tạo biological library entry' : current?.name}</h2></div>{current && <span className={statusClass(current.status)}>{current.status} · rev {current.revision}</span>}</div>{current && !showForm && <><DetailRows entry={current} /><p className="form-hint">Created {dateLabel(current.created_at)} · updated {dateLabel(current.updated_at)} · content SHA256 <code>{current.content_sha256}</code>{current.source_entry_id && <> · cloned from <code>{current.source_entry_id}</code></>}</p></>}<div className="library-form-grid"><label>Entry key<input disabled={!showForm} value={form.entry_key} onChange={(event) => setForm({ ...form, entry_key: event.target.value.toUpperCase() })} /></label><label>Entry type<select disabled={!editable || !showForm} value={form.entry_type} onChange={(event) => { const entryType = event.target.value as EntryType; setForm({ ...emptyForm(entryType), entry_key: form.entry_key, name: form.name }) }}><option value="DOSE_LIMIT">DOSE_LIMIT</option><option value="TREATMENT_PROTOCOL">TREATMENT_PROTOCOL</option><option value="KNOWLEDGE">KNOWLEDGE</option><option value="ALPHA_BETA">ALPHA_BETA</option></select></label><label className="library-form-grid__wide">Tên hiển thị<input disabled={!editable} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>Mô tả<textarea disabled={!editable} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><label>Effective / usage note<textarea disabled={!editable} value={form.effective_note} onChange={(event) => setForm({ ...form, effective_note: event.target.value })} /></label><label>Bệnh<input disabled={!editable} value={form.disease} onChange={(event) => setForm({ ...form, disease: event.target.value })} /></label><label>Bệnh phụ / subtype<input disabled={!editable} value={form.disease_subtype} onChange={(event) => setForm({ ...form, disease_subtype: event.target.value })} /></label><label>Anatomy site<input disabled={!editable} value={form.anatomy_site} onChange={(event) => setForm({ ...form, anatomy_site: event.target.value })} /></label><label>Treatment intent<input disabled={!editable} value={form.treatment_intent} onChange={(event) => setForm({ ...form, treatment_intent: event.target.value })} /></label><label>Technique<input disabled={!editable} value={form.technique} onChange={(event) => setForm({ ...form, technique: event.target.value })} /></label><label>Fractions<input disabled={!editable} type="number" min="1" step="1" value={form.fractions} onChange={(event) => setForm({ ...form, fractions: event.target.value })} /></label><label>Tissue / OAR<input disabled={!editable} value={form.tissue_or_oar} onChange={(event) => setForm({ ...form, tissue_or_oar: event.target.value })} /></label><label>Metric key<input disabled={!editable} value={form.metric_key} onChange={(event) => setForm({ ...form, metric_key: event.target.value.toUpperCase() })} placeholder="DMAX, V20, D95" /></label><label>Operator<input disabled={!editable} value={form.operator} onChange={(event) => setForm({ ...form, operator: event.target.value.toUpperCase() })} placeholder="MAX, MIN, RANGE" /></label><label>Limit value<input disabled={!editable} type="number" step="any" value={form.limit_value} onChange={(event) => setForm({ ...form, limit_value: event.target.value })} /></label><label>Lower limit<input disabled={!editable} type="number" step="any" value={form.lower_limit} onChange={(event) => setForm({ ...form, lower_limit: event.target.value })} /></label><label>Upper limit<input disabled={!editable} type="number" step="any" value={form.upper_limit} onChange={(event) => setForm({ ...form, upper_limit: event.target.value })} /></label><label>Unit<input disabled={!editable} value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} placeholder="Gy, %, cc" /></label><label>Volume (cc)<input disabled={!editable} type="number" step="any" value={form.volume_cc} onChange={(event) => setForm({ ...form, volume_cc: event.target.value })} /></label><label>Metric parameter<input disabled={!editable} type="number" step="any" value={form.metric_parameter} onChange={(event) => setForm({ ...form, metric_parameter: event.target.value })} /></label><label>α/β (Gy)<input disabled={!editable} type="number" step="any" value={form.alpha_beta_gy} onChange={(event) => setForm({ ...form, alpha_beta_gy: event.target.value })} /></label><label>Model key<input disabled={!editable} value={form.model_key} onChange={(event) => setForm({ ...form, model_key: event.target.value })} /></label><label>Model version<input disabled={!editable} value={form.model_version} onChange={(event) => setForm({ ...form, model_version: event.target.value })} /></label><label>Source type<select disabled={!editable} value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value as SourceType })}>{sourceTypes.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label>Reference status<select disabled={!editable} value={form.reference_status} onChange={(event) => setForm({ ...form, reference_status: event.target.value as ReferenceStatus })}>{referenceStatuses.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label className="library-form-grid__wide">Source reference / DOI / document<input disabled={!editable} value={form.source_reference} onChange={(event) => setForm({ ...form, source_reference: event.target.value })} /></label><label>Source date<input disabled={!editable} type="date" value={form.source_date} onChange={(event) => setForm({ ...form, source_date: event.target.value })} /></label><label>Evidence level<input disabled={!editable} value={form.evidence_level} onChange={(event) => setForm({ ...form, evidence_level: event.target.value })} /></label><label className="library-form-grid__wide">Applicability JSON<textarea disabled={!editable} value={form.applicability_text} onChange={(event) => setForm({ ...form, applicability_text: event.target.value })} /></label><label>Content JSON<textarea disabled={!editable} value={form.content_text} onChange={(event) => setForm({ ...form, content_text: event.target.value })} /></label><label>Citation JSON<textarea disabled={!editable} value={form.citation_text} onChange={(event) => setForm({ ...form, citation_text: event.target.value })} /></label></div><div className="library-editor-actions">{editable && <><button disabled={busy} onClick={validate}>Validate only</button><button disabled={busy} onClick={save}>{showForm ? 'Tạo DRAFT' : 'Lưu revision'}</button></>}{current && <><button className="button-secondary" disabled={busy} onClick={() => cloneMutation.mutate()}>Clone version</button>{current.status === 'DRAFT' && <button disabled={busy} onClick={() => publishMutation.mutate()}>Publish</button>}{current.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => archiveMutation.mutate()}>Archive</button>}<button className="button-secondary" disabled={busy} onClick={() => { setShowHistory(!showHistory); setValidation(undefined) }}>Lịch sử version</button><DownloadButton entry={current} format="JSON" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /><DownloadButton entry={current} format="CSV" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /></>}</div>{validation && <ValidationPanel validation={validation} />}</section>}

    {current && <section className="library-use-grid"><section className="panel library-use-panel"><div className="panel-heading"><div><p className="eyebrow">EXPLICIT USE SNAPSHOT</p><h2>Đưa reference vào một phép tính</h2></div><span className="status-badge">NO AUTO-APPLY</span></div><p>Thao tác này chỉ tạo payload snapshot có target tool, source entry, effective values, override và checksum. Calculator chưa tự động dùng nó cho đến khi integration contract của phase tương ứng nhận snapshot này.</p><div className="library-use-form"><label>Target tool<select value={targetTool} onChange={(event) => setTargetTool(event.target.value as TargetTool)}>{targetTools.map((item) => <option key={item} value={item}>{item}</option>)}</select></label><label>Override JSON<textarea value={overrideText} onChange={(event) => setOverrideText(event.target.value)} /></label></div><button disabled={busy || current.status === 'ARCHIVED'} onClick={() => useLibraryMutation.mutate()}>Tạo use snapshot</button>{useResult && <div className="library-use-result"><strong>Snapshot {useResult.snapshot_sha256.slice(0, 20)}…</strong><span>{useResult.target_tool} · {useResult.override_label ?? 'SOURCE_VALUES'}</span>{useResult.warnings.map((item, index) => <small key={`${item.code}-${index}`}>{issueText(item)}</small>)}<details><summary>Xem effective values</summary><pre>{pretty(useResult.effective_values)}</pre></details></div>}</section><section className="panel library-compare-panel"><div className="panel-heading"><div><p className="eyebrow">DIFF &amp; LINEAGE</p><h2>So sánh với version khác</h2></div></div><label>Entry cùng thư viện<select value={compareId} onChange={(event) => setCompareId(event.target.value)}><option value="">Chọn entry</option>{library.data?.items.filter((item) => item.id !== current.id).map((item) => <option key={item.id} value={item.id}>{item.entry_key} v{item.version_number} · {item.name}</option>)}</select></label><button className="button-secondary" disabled={busy || !compareId} onClick={() => compareMutation.mutate()}>So sánh</button>{compareMutation.data && <div className="library-diff-result"><p>{compareMutation.data.same_family ? 'Cùng entry family; khác biệt được hiển thị theo field.' : 'Khác family; dùng diff để kiểm tra trước khi tham chiếu.'}</p>{[...compareMutation.data.metadata_diffs, ...compareMutation.data.content_diffs].map((diff, index) => <div key={`${diff.field}-${index}`}><strong>{diff.field}</strong><pre>{pretty(diff.left)} → {pretty(diff.right)}</pre></div>)}{!compareMutation.data.metadata_diffs.length && !compareMutation.data.content_diffs.length && <p>Hai entry không có khác biệt.</p>}</div>}</section></section>}

    {showHistory && current && <section className="panel library-history-panel"><div className="panel-heading"><div><p className="eyebrow">APPEND-ONLY HISTORY</p><h2>{current.entry_key} versions</h2></div><strong>{history.data?.length ?? '—'}</strong></div>{history.isPending ? <p>Đang tải lịch sử…</p> : history.error ? <div className="alert alert--error"><p>{errorMessage(history.error)}</p><button onClick={() => void history.refetch()}>Thử lại</button></div> : <div className="table-wrap"><table><thead><tr><th>Version</th><th>Status</th><th>Revision</th><th>Hash</th><th>Updated</th><th></th></tr></thead><tbody>{history.data?.map((entry) => <tr key={entry.id}><td>{entry.version_number}</td><td><span className={statusClass(entry.status)}>{entry.status}</span></td><td>{entry.revision}</td><td><code>{entry.content_sha256}</code></td><td>{dateLabel(entry.updated_at)}</td><td><button className="button-secondary" onClick={() => choose(entry)}>Mở</button></td></tr>)}</tbody></table></div>}</section>}
    <p className="form-hint library-footer-note">P16 là thư viện kiến thức độc lập. Một reference được lưu hoặc publish không đồng nghĩa với việc reference đó đúng cho mọi bệnh nhân, mọi máy hoặc mọi protocol; user vẫn phải kiểm tra source, context và assumption trước khi tạo calculation snapshot.</p>
  </div>
}
