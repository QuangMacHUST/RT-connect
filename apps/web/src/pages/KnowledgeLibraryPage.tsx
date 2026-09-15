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

const entryTypeLabels: Record<EntryType, string> = {
  DOSE_LIMIT: 'Giới hạn liều',
  TREATMENT_PROTOCOL: 'Phác đồ điều trị',
  KNOWLEDGE: 'Bài kiến thức',
  ALPHA_BETA: 'Hệ số alpha/beta'
}

const statusLabels: Record<EntryStatus, string> = {
  DRAFT: 'Bản nháp',
  PUBLISHED: 'Đã xuất bản',
  ARCHIVED: 'Đã lưu trữ'
}

const sourceTypeLabels: Record<SourceType, string> = {
  USER_DEFINED: 'Nội dung do đơn vị nhập',
  REFERENCE: 'Tài liệu tham khảo',
  INTERNAL: 'Tài liệu nội bộ',
  SITE_APPROVED: 'Đã được cơ sở phê duyệt'
}

const referenceStatusLabels: Record<ReferenceStatus, string> = {
  UNVERIFIED: 'Chưa xác minh',
  AVAILABLE: 'Đã kiểm tra nguồn',
  UNAVAILABLE: 'Chưa có nguồn truy cập'
}

const targetToolLabels: Record<TargetTool, string> = {
  P13_BED_EQD2: 'Tính BED và EQD2',
  P14_PLAN_COMPARISON: 'So sánh phác đồ',
  P15_REIRRADIATION: 'Tính tái xạ',
  P15_FRACTION_COMPENSATION: 'Tính bù phân liều',
  P17_DVH: 'Phân tích liều và thể tích',
  KNOWLEDGE_REFERENCE: 'Tra cứu kiến thức'
}

const operatorLabels: Record<string, string> = {
  MAX: 'Không vượt quá',
  MIN: 'Không thấp hơn',
  RANGE: 'Nằm trong khoảng',
  AT_LEAST: 'Ít nhất',
  AT_MOST: 'Nhiều nhất'
}

const operatorOptions = ['MAX', 'MIN', 'RANGE', 'AT_LEAST', 'AT_MOST']

const fieldLabels: Record<string, string> = {
  entry: 'bài viết',
  entry_key: 'bài viết',
  entry_type: 'loại nội dung',
  name: 'tên hiển thị',
  source_type: 'loại nguồn',
  source_reference: 'nguồn tài liệu',
  reference_status: 'trạng thái nguồn',
  description: 'mô tả',
  effective_note: 'ghi chú áp dụng',
  disease: 'mặt bệnh',
  disease_subtype: 'phân nhóm mặt bệnh',
  anatomy_site: 'vị trí giải phẫu',
  treatment_intent: 'mục tiêu điều trị',
  technique: 'kỹ thuật điều trị',
  fractions: 'số phân liều',
  tissue_or_oar: 'mô hoặc cơ quan',
  metric_key: 'tên chỉ số',
  operator: 'cách đánh giá',
  limit_value: 'giá trị giới hạn',
  lower_limit: 'giới hạn dưới',
  upper_limit: 'giới hạn trên',
  unit: 'đơn vị',
  volume_cc: 'thể tích',
  metric_parameter: 'tham số chỉ số',
  alpha_beta_gy: 'hệ số alpha/beta',
  source_date: 'ngày của nguồn',
  evidence_level: 'mức độ bằng chứng'
}

function emptyForm(entryType: EntryType = 'DOSE_LIMIT'): LibraryForm {
  return {
    entry_key: '',
    entry_type: entryType,
    name: entryType === 'DOSE_LIMIT' ? 'Giới hạn liều mới' : 'Bài kiến thức mới',
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
    applicability_text: '',
    content_text: '',
    source_type: 'USER_DEFINED',
    source_reference: '',
    reference_status: 'UNVERIFIED',
    source_date: '',
    evidence_level: '',
    citation_text: ''
  }
}

function readText(value: unknown): string {
  if (typeof value === 'string') return value
  if (!value || typeof value !== 'object' || Array.isArray(value)) return ''
  const record = value as Record<string, unknown>
  for (const key of ['summary', 'note', 'description', 'text']) {
    if (typeof record[key] === 'string') return record[key]
  }
  return Object.values(record).filter((item): item is string => typeof item === 'string').join('\n')
}

function automaticEntryKey(name: string, entryType: EntryType): string {
  const normalized = name.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toUpperCase().replace(/[^A-Z0-9]+/g, '_').replace(/^_|_$/g, '').slice(0, 100)
  return `${normalized || 'BAI_VIET_MOI'}_${entryType}`.slice(0, 120)
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
    applicability_text: '',
    content_text: readText(entry.content),
    source_type: entry.source_type,
    source_reference: entry.source_reference ?? '',
    reference_status: entry.reference_status,
    source_date: entry.source_date ?? '',
    evidence_level: entry.evidence_level ?? '',
    citation_text: readText(entry.citation)
  }
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message
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

function bodyFromForm(form: LibraryForm): BiologicalLibraryDefinitionInput {
  const applicability: Record<string, unknown> = {}
  if (form.disease.trim()) applicability.diseases = [form.disease.trim()]
  if (form.disease_subtype.trim()) applicability.subtypes = [form.disease_subtype.trim()]
  if (form.anatomy_site.trim()) applicability.anatomy_sites = [form.anatomy_site.trim()]
  if (form.technique.trim()) applicability.techniques = [form.technique.trim()]
  if (form.tissue_or_oar.trim()) applicability.tissue_or_oars = [form.tissue_or_oar.trim()]
  const fractionValue = integerOrNull(form.fractions, 'Số phân liều')
  if (fractionValue !== null) applicability.fractions = [fractionValue]
  const content = form.content_text.trim() ? { note: form.content_text.trim() } : {}
  const citation = form.citation_text.trim() ? { note: form.citation_text.trim() } : {}
  return {
    entry_key: form.entry_key || automaticEntryKey(form.name, form.entry_type),
    entry_type: form.entry_type,
    name: form.name,
    description: form.description || null,
    effective_note: form.effective_note || null,
    disease: form.disease || null,
    disease_subtype: form.disease_subtype || null,
    anatomy_site: form.anatomy_site || null,
    treatment_intent: form.treatment_intent || null,
    technique: form.technique || null,
    fractions: integerOrNull(form.fractions, 'Số phân liều'),
    tissue_or_oar: form.tissue_or_oar || null,
    metric_key: form.metric_key || null,
    operator: form.operator || null,
    limit_value: numberOrNull(form.limit_value, 'Giá trị giới hạn'),
    lower_limit: numberOrNull(form.lower_limit, 'Giới hạn dưới'),
    upper_limit: numberOrNull(form.upper_limit, 'Giới hạn trên'),
    unit: form.unit || null,
    volume_cc: numberOrNull(form.volume_cc, 'Thể tích'),
    metric_parameter: numberOrNull(form.metric_parameter, 'Tham số chỉ số'),
    alpha_beta_gy: numberOrNull(form.alpha_beta_gy, 'Alpha/beta'),
    model_key: form.model_key || null,
    model_version: form.model_version || null,
    applicability,
    content,
    source_type: form.source_type,
    source_reference: form.source_reference || null,
    reference_status: form.reference_status,
    source_date: form.source_date || null,
    evidence_level: form.evidence_level || null,
    citation
  }
}

function issueText(issue: { code: string; field: string | null; message: string }): string {
  return `${fieldLabels[issue.field ?? 'entry'] ?? 'Thông tin'}: ${issue.message}`
}

function displayDiffValue(value: unknown): string {
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (typeof value === 'string') {
    if (value in statusLabels) return statusLabels[value as EntryStatus]
    if (value in sourceTypeLabels) return sourceTypeLabels[value as SourceType]
    if (value in referenceStatusLabels) return referenceStatusLabels[value as ReferenceStatus]
    if (value in operatorLabels) return operatorLabels[value]
    return value
  }
  return readText(value) || 'Đã thay đổi'
}

function DownloadButton({
  entry,
  format,
  accessToken,
  organizationId,
  onMessage
}: {
  entry: BiologicalLibraryEntryResource
  format: 'CSV'
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
      anchor.download = `rt-connect-thu-vien-kien-thuc-v${entry.version_number}.csv`
      anchor.click()
      URL.revokeObjectURL(url)
      onMessage(`Đã tải bảng dữ liệu của bài viết phiên bản ${entry.version_number}.`)
    } catch (error) {
      onMessage(errorMessage(error))
    }
  }}>Tải bảng dữ liệu</button>
}

function ValidationPanel({
  validation
}: {
  validation: { valid: boolean; errors: Array<{ code: string; field: string | null; message: string }>; warnings: Array<{ code: string; field: string | null; message: string }> }
}) {
  return <section className={validation.valid ? 'bed-validation bed-validation--ok' : 'bed-validation bed-validation--error'} aria-live="polite">
    <strong>{validation.valid ? 'Kiểm tra hợp lệ' : 'Cần sửa thông tin'}</strong>
    {validation.errors.length > 0 && <ul>{validation.errors.map((item, index) => <li key={`${item.code}-${index}`}>{issueText(item)}</li>)}</ul>}
    {validation.warnings.length > 0 && <div className="library-warning-list"><strong>Lưu ý cần xem lại:</strong><ul>{validation.warnings.map((item, index) => <li key={`${item.code}-${index}`}>{issueText(item)}</li>)}</ul></div>}
    {validation.valid && validation.errors.length === 0 && <p>Kiểm tra này chỉ xem trước và chưa lưu thay đổi.</p>}
  </section>
}

function DetailRows({ entry }: { entry: BiologicalLibraryEntryResource }) {
  return <div className="library-detail-grid">
    <div><span>Phiên bản</span><strong>Phiên bản {entry.version_number}</strong></div>
    <div><span>Trạng thái</span><strong>{statusLabels[entry.status]}</strong></div>
    <div><span>Context</span><strong>{[entry.disease, entry.anatomy_site, entry.technique].filter(Boolean).join(' · ') || 'Chưa khai báo'}</strong></div>
    <div><span>Mô hoặc cơ quan</span><strong>{entry.tissue_or_oar ?? '—'}</strong></div>
    <div><span>Chỉ số</span><strong>{[entry.metric_key, entry.operator, entry.limit_value, entry.unit].filter((item) => item !== null && item !== '').join(' ') || '—'}</strong></div>
    <div><span>Nguồn</span><strong>{sourceTypeLabels[entry.source_type]} · {referenceStatusLabels[entry.reference_status]}</strong></div>
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
  const [targetTool, setTargetTool] = useState<TargetTool>('KNOWLEDGE_REFERENCE')
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
       setMessage(error instanceof Error ? error.message : 'Bài viết không hợp lệ.')
      return undefined
    }
  }
  const createMutation = useMutation({
    mutationFn: (body: BiologicalLibraryDefinitionInput) => apiClient.createBiologicalLibraryEntry(accessToken!, organizationId!, body),
     onSuccess: (entry) => { setSelectedId(entry.id); setShowForm(false); setForm(formFromEntry(entry)); setMessage(`Đã tạo bài viết phiên bản ${entry.version_number} ở trạng thái bản nháp.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const updateMutation = useMutation({
    mutationFn: (body: Parameters<typeof apiClient.updateBiologicalLibraryEntry>[3]) => apiClient.updateBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, body),
     onSuccess: (entry) => { setForm(formFromEntry(entry)); setMessage(`Đã lưu bài viết phiên bản ${entry.version_number}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validateMutation = useMutation({
    mutationFn: (body: BiologicalLibraryDefinitionInput) => apiClient.validateBiologicalLibraryEntry(accessToken!, organizationId!, body),
     onSuccess: (result) => { setValidation({ valid: result.valid, errors: result.errors, warnings: result.warnings }); setMessage(result.valid ? 'Bài viết hợp lệ; kiểm tra trước khi lưu chưa ghi dữ liệu.' : 'Bài viết chưa hợp lệ; hãy xem danh sách lỗi và sửa lại.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const cloneMutation = useMutation({
     mutationFn: () => apiClient.cloneBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, { name: `${current!.name} · bản sao nội bộ` }),
     onSuccess: (entry) => { setSelectedId(entry.id); setShowForm(false); setForm(formFromEntry(entry)); setMessage(`Đã tạo bản sao phiên bản ${entry.version_number}; bài gốc vẫn được giữ nguyên.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const publishMutation = useMutation({
    mutationFn: () => apiClient.publishBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, current!.revision),
     onSuccess: (entry) => { setForm(formFromEntry(entry)); setMessage(`Đã xuất bản bài viết phiên bản ${entry.version_number}.`); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const archiveMutation = useMutation({
    mutationFn: () => apiClient.archiveBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, current!.revision),
     onSuccess: (entry) => { setForm(formFromEntry(entry)); setMessage('Đã lưu trữ bài viết; lịch sử vẫn được giữ lại.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const compareMutation = useMutation({
    mutationFn: () => apiClient.compareBiologicalLibraryEntries(accessToken!, organizationId!, current!.id, compareId),
    onError: (error) => setMessage(errorMessage(error))
  })
  const useLibraryMutation = useMutation({
    mutationFn: () => apiClient.useBiologicalLibraryEntry(accessToken!, organizationId!, current!.id, { target_tool: targetTool, override: {} }),
    onSuccess: (result) => { setUseResult(result); setMessage('Đã tạo bản ghi tham chiếu cho phép tính; chưa tự động áp dụng.') },
    onError: (error) => setMessage(errorMessage(error))
  })
  const busy = createMutation.isPending || updateMutation.isPending || validateMutation.isPending || cloneMutation.isPending || publishMutation.isPending || archiveMutation.isPending || compareMutation.isPending || useLibraryMutation.isPending

  if (bootstrap.isPending) return <main className="auth-state">Đang tải thư viện kiến thức…</main>
  if (bootstrap.error || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở thư viện kiến thức</h1><p>{errorMessage(bootstrap.error)}</p><Link className="button-link" to="/app/biological">Quay lại công cụ sinh học</Link></section></div>

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
  return <div className="page library-page">
    <header className="page-header"><div><p className="eyebrow">THƯ VIỆN KIẾN THỨC</p><h1>Thư viện kiến thức và tài liệu</h1><p>Nơi lưu trữ giới hạn liều, phác đồ điều trị, bài giải thích và hệ số alpha/beta theo từng mặt bệnh. Nội dung được lưu theo phiên bản và chỉ đưa vào phép tính khi người dùng chủ động chọn.</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/biological">Quay lại công cụ sinh học</Link><button onClick={() => { setShowForm(true); setSelectedId(undefined); setForm(emptyForm()); setValidation(undefined); setMessage(undefined) }}>+ Tạo bài viết</button></div></header>
    <section className="biological-notice library-notice" role="note"><strong>TÀI LIỆU THAM KHẢO · KHÔNG TỰ ĐỘNG ÁP DỤNG</strong><span>Thư viện không chứa thông tin nhận diện người bệnh và không tự biến thành chỉ tiêu đánh giá. Nguồn chưa xác minh sẽ được đánh dấu để xem lại; nội dung chỉ được đưa vào công cụ khi người dùng chọn rõ ràng.</span></section>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {library.error && <section className="alert alert--error" role="alert"><h2>Không tải được thư viện</h2><p>{errorMessage(library.error)}</p><button onClick={() => void library.refetch()}>Thử lại</button></section>}

    <section className="metric-grid library-metrics"><article className="metric-card"><p>Bài đang hiển thị</p><strong>{library.data?.total ?? '—'}</strong><small>Theo điều kiện tìm kiếm hiện tại</small></article><article className="metric-card"><p>Đã xuất bản</p><strong>{library.data?.items.filter((item) => item.status === 'PUBLISHED').length ?? '—'}</strong><small>Có thể dùng làm tài liệu tham khảo</small></article><article className="metric-card"><p>Bản nháp</p><strong>{library.data?.items.filter((item) => item.status === 'DRAFT').length ?? '—'}</strong><small>Đang chờ hoàn thiện hoặc duyệt</small></article><article className="metric-card library-metric-card--warning"><p>Cần xem lại nguồn</p><strong>{library.data?.items.filter((item) => item.reference_status !== 'AVAILABLE').length ?? '—'}</strong><small>Nguồn chưa xác minh hoặc chưa truy cập được</small></article></section>

    <section className="library-filter-panel panel"><div className="panel-heading"><div><p className="eyebrow">TÌM KIẾM VÀ LỌC</p><h2>Tra cứu theo mặt bệnh và điều kiện áp dụng</h2></div><label className="checkbox-row"><input type="checkbox" checked={includeArchived} onChange={(event) => setIncludeArchived(event.target.checked)} /> Hiện bài đã lưu trữ</label></div><div className="library-filter-grid"><label>Tìm kiếm<input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Tên bài, mặt bệnh, nội dung…" /></label><label>Loại nội dung<select value={typeFilter} onChange={(event) => setTypeFilter(event.target.value as EntryType | 'ALL')}><option value="ALL">Tất cả</option>{entryTypes.map((item) => <option key={item} value={item}>{entryTypeLabels[item]}</option>)}</select></label><label>Trạng thái<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as 'ALL' | EntryStatus)}>{statuses.map((item) => <option key={item} value={item}>{item === 'ALL' ? 'Tất cả' : statusLabels[item]}</option>)}</select></label><label>Mặt bệnh<input value={disease} onChange={(event) => setDisease(event.target.value)} placeholder="Ví dụ: ung thư phổi" /></label><label>Vị trí giải phẫu<input value={anatomySite} onChange={(event) => setAnatomySite(event.target.value)} placeholder="Ví dụ: lồng ngực" /></label><label>Kỹ thuật điều trị<input value={technique} onChange={(event) => setTechnique(event.target.value)} placeholder="Ví dụ: xạ trị điều biến" /></label><label>Mô hoặc cơ quan<input value={tissue} onChange={(event) => setTissue(event.target.value)} placeholder="Ví dụ: tủy sống" /></label><label>Chỉ số<input value={metric} onChange={(event) => setMetric(event.target.value)} placeholder="Ví dụ: liều tối đa, V20" /></label><label>Số phân liều<input type="number" min="1" step="1" value={fractions} onChange={(event) => setFractions(event.target.value)} placeholder="Ví dụ: 30" /></label></div></section>

    <div className="library-workspace-grid"><section className="panel library-list-panel"><div className="panel-heading"><div><p className="eyebrow">NỘI DUNG THEO PHIÊN BẢN</p><h2>Các bài trong thư viện</h2></div><strong>{library.data?.total ?? '—'}</strong></div>{library.isPending ? <p>Đang tải bài viết…</p> : library.data?.items.length ? <div className="table-wrap"><table className="library-table"><thead><tr><th>Bài viết</th><th>Loại nội dung</th><th>Bối cảnh</th><th>Giá trị</th><th>Trạng thái</th><th>Cập nhật</th><th /></tr></thead><tbody>{library.data.items.map((entry) => <tr className={entry.id === current?.id ? 'is-selected' : undefined} key={entry.id}><td><strong>{entry.name}</strong><span className="table-subtitle">Phiên bản {entry.version_number}</span></td><td>{entryTypeLabels[entry.entry_type]}</td><td><span className="table-subtitle">{[entry.disease, entry.anatomy_site, entry.technique, entry.tissue_or_oar].filter(Boolean).join(' · ') || 'Chưa khai báo'}</span></td><td>{[entry.metric_key, entry.limit_value, entry.unit].filter((item) => item !== null && item !== '').join(' ') || (entry.alpha_beta_gy ? `α/β ${entry.alpha_beta_gy} ${entry.unit ?? 'Gy'}` : '—')}</td><td><span className={statusClass(entry.status)}>{statusLabels[entry.status]}</span><span className="table-subtitle">{referenceStatusLabels[entry.reference_status]}</span></td><td>{dateLabel(entry.updated_at)}</td><td><button className="button-secondary" onClick={() => choose(entry)}>Mở bài</button></td></tr>)}</tbody></table></div> : <div className="empty-state"><strong>Chưa có bài viết phù hợp</strong><p>Hãy đổi điều kiện tìm kiếm hoặc tạo bài viết đầu tiên.</p><button onClick={() => { setShowForm(true); setSelectedId(undefined); setForm(emptyForm()) }}>+ Tạo bài viết</button></div>}</section>

      <aside className="library-side-column"><section className="panel library-workflow-panel"><div className="panel-heading"><div><p className="eyebrow">QUY TRÌNH BIÊN TẬP</p><h2>Vòng đời bài viết</h2></div></div><ol><li>Nhập nội dung và bối cảnh áp dụng</li><li>Kiểm tra để xem lỗi và lưu ý</li><li>Lưu thành bản nháp</li><li>Tạo phiên bản mới khi cần thay đổi</li><li>Xuất bản sau khi đã xem lại nguồn</li><li>Chọn bài viết rõ ràng trước khi đưa vào công cụ</li></ol><p className="form-hint">Bài viết không tự động thay đổi kết quả tính toán. Nguồn, phiên bản và lịch sử được giữ lại để người dùng có thể kiểm tra.</p></section></aside></div>

     {(showForm || current) && <section className="panel library-editor-panel"><div className="panel-heading"><div><p className="eyebrow">{showForm ? 'BÀI VIẾT MỚI' : 'CHỈNH SỬA BÀI VIẾT'}</p><h2>{showForm ? 'Tạo bài viết mới' : current?.name}</h2></div>{current && <span className={statusClass(current.status)}>{statusLabels[current.status]} · phiên bản {current.version_number}</span>}</div>{current && !showForm && <><DetailRows entry={current} /><p className="form-hint">Cập nhật lần cuối: {dateLabel(current.updated_at)}. Nội dung và nguồn được lưu theo phiên bản để có thể kiểm tra lại.</p></>}<div className="library-form-grid"><label>Loại nội dung<select disabled={!editable || !showForm} value={form.entry_type} onChange={(event) => { const entryType = event.target.value as EntryType; setForm({ ...emptyForm(entryType), name: form.name }) }}>{entryTypes.map((item) => <option key={item} value={item}>{entryTypeLabels[item]}</option>)}</select></label><label className="library-form-grid__wide">Tên bài viết<input required disabled={!editable} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} /></label><label>Mô tả ngắn<textarea disabled={!editable} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} /></label><label>Ghi chú áp dụng<textarea disabled={!editable} value={form.effective_note} onChange={(event) => setForm({ ...form, effective_note: event.target.value })} /></label><label>Mặt bệnh<input disabled={!editable} value={form.disease} onChange={(event) => setForm({ ...form, disease: event.target.value })} placeholder="Ví dụ: ung thư vú" /></label><label>Phân nhóm mặt bệnh<input disabled={!editable} value={form.disease_subtype} onChange={(event) => setForm({ ...form, disease_subtype: event.target.value })} /></label><label>Vị trí giải phẫu<input disabled={!editable} value={form.anatomy_site} onChange={(event) => setForm({ ...form, anatomy_site: event.target.value })} placeholder="Ví dụ: vú, phổi, tủy sống" /></label><label>Mục tiêu điều trị<input disabled={!editable} value={form.treatment_intent} onChange={(event) => setForm({ ...form, treatment_intent: event.target.value })} /></label><label>Kỹ thuật điều trị<input disabled={!editable} value={form.technique} onChange={(event) => setForm({ ...form, technique: event.target.value })} placeholder="Ví dụ: điều biến liều" /></label><label>Số phân liều<input disabled={!editable} type="number" min="1" step="1" value={form.fractions} onChange={(event) => setForm({ ...form, fractions: event.target.value })} /></label><label>Mô hoặc cơ quan<input disabled={!editable} value={form.tissue_or_oar} onChange={(event) => setForm({ ...form, tissue_or_oar: event.target.value })} placeholder="Ví dụ: tủy sống, phổi" /></label><label>Tên chỉ số đánh giá<input disabled={!editable} value={form.metric_key} onChange={(event) => setForm({ ...form, metric_key: event.target.value.toUpperCase() })} placeholder="Ví dụ: liều tối đa, V20, D95" /></label><label>Cách đánh giá<select disabled={!editable} value={form.operator || 'MAX'} onChange={(event) => setForm({ ...form, operator: event.target.value })}>{operatorOptions.map((item) => <option key={item} value={item}>{operatorLabels[item]}</option>)}</select></label><label>Giá trị giới hạn<input disabled={!editable} type="number" step="any" value={form.limit_value} onChange={(event) => setForm({ ...form, limit_value: event.target.value })} /></label><label>Giới hạn dưới<input disabled={!editable} type="number" step="any" value={form.lower_limit} onChange={(event) => setForm({ ...form, lower_limit: event.target.value })} /></label><label>Giới hạn trên<input disabled={!editable} type="number" step="any" value={form.upper_limit} onChange={(event) => setForm({ ...form, upper_limit: event.target.value })} /></label><label>Đơn vị<input disabled={!editable} value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} placeholder="Ví dụ: Gy, %, cm³" /></label><label>Thể tích (cm³)<input disabled={!editable} type="number" step="any" value={form.volume_cc} onChange={(event) => setForm({ ...form, volume_cc: event.target.value })} /></label><label>Tham số chỉ số<input disabled={!editable} type="number" step="any" value={form.metric_parameter} onChange={(event) => setForm({ ...form, metric_parameter: event.target.value })} /></label><label>Hệ số alpha/beta (Gy)<input disabled={!editable} type="number" step="any" value={form.alpha_beta_gy} onChange={(event) => setForm({ ...form, alpha_beta_gy: event.target.value })} /></label><label>Loại nguồn<select disabled={!editable} value={form.source_type} onChange={(event) => setForm({ ...form, source_type: event.target.value as SourceType })}>{sourceTypes.map((item) => <option key={item} value={item}>{sourceTypeLabels[item]}</option>)}</select></label><label>Trạng thái nguồn<select disabled={!editable} value={form.reference_status} onChange={(event) => setForm({ ...form, reference_status: event.target.value as ReferenceStatus })}>{referenceStatuses.map((item) => <option key={item} value={item}>{referenceStatusLabels[item]}</option>)}</select></label><label className="library-form-grid__wide">Nguồn tài liệu<input disabled={!editable} value={form.source_reference} onChange={(event) => setForm({ ...form, source_reference: event.target.value })} placeholder="Tên tài liệu, đường dẫn hoặc ghi chú nguồn" /></label><label>Ngày của nguồn<input disabled={!editable} type="date" value={form.source_date} onChange={(event) => setForm({ ...form, source_date: event.target.value })} /></label><label>Mức độ bằng chứng<input disabled={!editable} value={form.evidence_level} onChange={(event) => setForm({ ...form, evidence_level: event.target.value })} /></label><label className="library-form-grid__wide">Nội dung bài viết<textarea rows={8} disabled={!editable} value={form.content_text} onChange={(event) => setForm({ ...form, content_text: event.target.value })} placeholder="Viết quy trình, cách phân tích, tiêu chí đánh giá hoặc lưu ý thực hành." /></label><label className="library-form-grid__wide">Ghi chú nguồn tài liệu<textarea rows={4} disabled={!editable} value={form.citation_text} onChange={(event) => setForm({ ...form, citation_text: event.target.value })} placeholder="Ghi tên bài báo, hướng dẫn hoặc tài liệu làm căn cứ." /></label></div><div className="library-editor-actions">{editable && <><button disabled={busy} onClick={validate}>Kiểm tra trước khi lưu</button><button disabled={busy} onClick={save}>{showForm ? 'Lưu bài viết' : 'Lưu phiên bản mới'}</button></>}{current && <><button className="button-secondary" disabled={busy} onClick={() => cloneMutation.mutate()}>Tạo phiên bản mới</button>{current.status === 'DRAFT' && <button disabled={busy} onClick={() => publishMutation.mutate()}>Xuất bản</button>}{current.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => archiveMutation.mutate()}>Lưu trữ</button>}<button className="button-secondary" disabled={busy} onClick={() => { setShowHistory(!showHistory); setValidation(undefined) }}>Xem lịch sử</button><DownloadButton entry={current} format="CSV" accessToken={accessToken!} organizationId={organizationId} onMessage={setMessage} /></>}</div>{validation && <ValidationPanel validation={validation} />}</section>}

     {current && <section className="library-use-grid"><section className="panel library-use-panel"><div className="panel-heading"><div><p className="eyebrow">ĐƯA VÀO CÔNG CỤ</p><h2>Đưa tài liệu vào một phép tính</h2></div><span className="status-badge">Không tự áp dụng</span></div><p>Chỉ tạo một bản ghi tham khảo cho công cụ được chọn. Hệ thống không tự biến tài liệu thành chỉ tiêu đánh giá và không tự thay đổi phép tính.</p><div className="library-use-form"><label>Công cụ sử dụng<select value={targetTool} onChange={(event) => setTargetTool(event.target.value as TargetTool)}>{targetTools.map((item) => <option key={item} value={item}>{targetToolLabels[item]}</option>)}</select></label></div><button disabled={busy || current.status === 'ARCHIVED'} onClick={() => useLibraryMutation.mutate()}>Đưa tài liệu vào công cụ</button>{useResult && <div className="library-use-result"><strong>Đã tạo bản ghi tham khảo</strong><span>Đã chọn cho: {targetToolLabels[useResult.target_tool]}</span>{useResult.warnings.map((item, index) => <small key={`${item.code}-${index}`}>{issueText(item)}</small>)}</div>}</section><section className="panel library-compare-panel"><div className="panel-heading"><div><p className="eyebrow">SO SÁNH PHIÊN BẢN</p><h2>So sánh với bài viết khác</h2></div></div><label>Bài viết cùng thư viện<select value={compareId} onChange={(event) => setCompareId(event.target.value)}><option value="">Chọn bài viết</option>{library.data?.items.filter((item) => item.id !== current.id).map((item) => <option key={item.id} value={item.id}>{item.name} · phiên bản {item.version_number}</option>)}</select></label><button className="button-secondary" disabled={busy || !compareId} onClick={() => compareMutation.mutate()}>So sánh</button>{compareMutation.data && <div className="library-diff-result"><p>{compareMutation.data.same_family ? 'Hai phiên bản cùng một nhóm bài viết; các điểm khác nhau được liệt kê bên dưới.' : 'Hai bài viết khác nhóm; hãy kiểm tra kỹ trước khi dùng làm tài liệu tham khảo.'}</p>{[...compareMutation.data.metadata_diffs, ...compareMutation.data.content_diffs].map((diff, index) => <div key={`${diff.field}-${index}`}><strong>{fieldLabels[diff.field] ?? 'Nội dung liên quan'}</strong><p>{displayDiffValue(diff.left)} → {displayDiffValue(diff.right)}</p></div>)}{!compareMutation.data.metadata_diffs.length && !compareMutation.data.content_diffs.length && <p>Hai bài viết không có khác biệt.</p>}</div>}</section></section>}

     {showHistory && current && <section className="panel library-history-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ BÀI VIẾT</p><h2>Các phiên bản đã lưu</h2></div><strong>{history.data?.length ?? '—'}</strong></div>{history.isPending ? <p>Đang tải lịch sử…</p> : history.error ? <div className="alert alert--error"><p>{errorMessage(history.error)}</p><button onClick={() => void history.refetch()}>Thử lại</button></div> : <div className="table-wrap"><table><thead><tr><th>Phiên bản</th><th>Trạng thái</th><th>Cập nhật</th><th></th></tr></thead><tbody>{history.data?.map((entry) => <tr key={entry.id}><td>Phiên bản {entry.version_number}</td><td><span className={statusClass(entry.status)}>{statusLabels[entry.status]}</span></td><td>{dateLabel(entry.updated_at)}</td><td><button className="button-secondary" onClick={() => choose(entry)}>Mở phiên bản</button></td></tr>)}</tbody></table></div>}</section>}
     <p className="form-hint library-footer-note">Thư viện kiến thức hoạt động độc lập. Một bài viết được lưu hoặc xuất bản không có nghĩa là nội dung đó phù hợp cho mọi người bệnh, mọi máy hoặc mọi quy trình; người dùng vẫn phải kiểm tra nguồn, bối cảnh và giả định trước khi đưa vào phép tính.</p>
  </div>
}
