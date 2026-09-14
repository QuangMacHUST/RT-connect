import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { ApiClientError, apiClient, type FolderResource, type QACasePurgePreviewResource, type QATestDefinitionResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { dvhArtifactStatusLabel, summarizeDvhArtifacts } from './dvhArtifactSummary'
import { isCaseInArchiveView, toggleAllVisibleCaseSelection, toggleCaseSelection } from './qaArchiveView'
import { processUploadQueue, type UploadQueueItem, updatePendingUploadMetadata } from './uploadQueue'

type BatchCaseItem = { id: string; title: string }
type BatchSkippedItem = BatchCaseItem & { reason: string }

const purgeReferenceLabels: Record<string, string> = {
  machine_qa_runs: 'kết quả kiểm tra máy',
  gamma_analysis_runs: 'lần phân tích Gamma',
  dvh_analysis_runs: 'lần phân tích liều',
  trend_points: 'điểm xu hướng',
  artifacts: 'tệp đầu vào',
  reports: 'báo cáo'
}

const cycles = ['DAILY', 'MONTHLY', 'ANNUAL', 'CUSTOM'] as const
const cycleLabels: Record<(typeof cycles)[number], string> = {
  DAILY: 'Hằng ngày',
  MONTHLY: 'Hằng tháng',
  ANNUAL: 'Hằng năm',
  CUSTOM: 'Tùy chỉnh'
}

const artifactTypeLabels: Record<string, string> = {
  DICOM: 'Tệp DICOM',
  MEASUREMENT: 'Số đo',
  OTHER: 'Tệp khác'
}

const caseStatusLabels: Record<string, string> = {
  DRAFT: 'Bản nháp',
  OPEN: 'Đang mở',
  IN_REVIEW: 'Đang xem xét',
  ACTIVE: 'Đang thực hiện',
  COMPLETED: 'Đã hoàn tất',
  CANCELLED: 'Đã hủy',
  ARCHIVED: 'Đã lưu trữ'
}

const qaTypeLabels: Record<string, string> = {
  'Machine QA': 'Kiểm tra chất lượng máy',
  'Machine Output': 'Kiểm tra đầu ra máy',
  'Picket Fence': 'Kiểm tra hàng rào lá',
  Starshot: 'Kiểm tra sao',
  'Winston-Lutz': 'Kiểm tra Winston–Lutz',
  PSQA: 'Kiểm tra chất lượng kế hoạch',
  Gamma: 'Phân tích Gamma'
}

const artifactStatusLabels: Record<string, string> = {
  UPLOADED: 'Đã tải lên',
  VALID: 'Hợp lệ',
  INVALID: 'Không hợp lệ',
  PENDING: 'Đang chờ kiểm tra'
}

function uploadQueueStatusLabel(status: UploadQueueItem['status']): string {
  if (status === 'PENDING') return 'Đang chờ'
  if (status === 'UPLOADING') return 'Đang tải lên…'
  if (status === 'UPLOADED') return 'Đã tải lên'
  return 'Tải lên lỗi'
}

function labelOf(labels: Record<string, string>, value: string): string {
  return labels[value] ?? value
}

function purgeReferenceSummary(references: Array<{ source: string; count: number }>): string {
  return references.map((reference) => `${reference.count} ${purgeReferenceLabels[reference.source] ?? 'dữ liệu liên quan'}`).join(', ')
}

function definitionNeedsInputFile(definition: QATestDefinitionResource | undefined): boolean {
  if (!definition) return false
  return definition.input_kind !== 'MEASUREMENT' || definition.required_inputs.some((item) => /ảnh|tệp|dicom|chuỗi|biên dạng|dose|liều/i.test(item))
}

function definitionSupportsDoseAnalysis(definition: QATestDefinitionResource | undefined): boolean {
  if (!definition) return false
  return definition.key.startsWith('PSQA_')
    || definition.input_kind.includes('DOSE')
    || definition.required_inputs.some((item) => /rtdose|dose|liều/i.test(item))
}

function inputKindLabel(inputKind: string): string {
  if (inputKind === 'MEASUREMENT') return 'Nhập số đo'
  if (inputKind.includes('SERIES')) return 'Bộ ảnh DICOM'
  if (inputKind.includes('IMAGE')) return 'Ảnh hoặc tệp DICOM'
  if (inputKind.includes('PROFILE')) return 'Biên dạng liều'
  if (inputKind.includes('LOG')) return 'Tệp nhật ký máy'
  return 'Tệp đầu vào'
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    const messages: Record<string, string> = {
      FOLDER_NAME_CONFLICT: 'Tên thư mục đã được sử dụng trong đơn vị này.',
      REVISION_CONFLICT: 'Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại rồi thực hiện lại thao tác.',
      RESOURCE_ARCHIVED: 'Mục này đã được lưu trữ. Hãy khôi phục trước khi sửa.',
      PARENT_NOT_AVAILABLE: 'Mục cha đang được lưu trữ nên không thể thực hiện thao tác này.',
      MACHINE_NOT_FOUND: 'Không tìm thấy máy đang chọn hoặc máy không còn hoạt động.',
      QA_CASE_IDEMPOTENCY_CONFLICT: 'Lượt tạo bài này đã được dùng cho dữ liệu khác. Hãy tạo lại từ đầu.',
      QA_CASE_REFERENCED: 'Bài vẫn còn kết quả, tệp hoặc báo cáo liên quan nên chưa thể xóa vĩnh viễn.',
      QA_CASE_PURGE_REQUIRES_ARCHIVE: 'Hãy lưu trữ bài trước khi xóa vĩnh viễn.',
      ACTION_CANCELLED: 'Đã hủy thao tác xóa vĩnh viễn.',
      QA_DEFINITION_NOT_FOUND: 'Loại bài kiểm tra không còn trong danh mục hiện tại.'
    }
    return messages[error.code] ?? 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối.'
  }
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối.'
}

export function QAArchivePage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const accessToken = session?.access_token
  const bootstrap = useQuery({
    queryKey: ['session', accessToken],
    queryFn: () => apiClient.bootstrap(accessToken!),
    enabled: Boolean(accessToken), retry: false
  })
  const organizationId = bootstrap.data?.organization.id
  const [showTrash, setShowTrash] = useState(false)
  const testDefinitions = useQuery({
    queryKey: ['qa-test-definitions', organizationId, accessToken],
    queryFn: () => apiClient.qaTestDefinitions(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const folders = useQuery({
    queryKey: ['folders', organizationId, accessToken, showTrash],
    queryFn: () => apiClient.folders(accessToken!, organizationId!, showTrash),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const sites = useQuery({
    queryKey: ['sites', organizationId, accessToken],
    queryFn: () => apiClient.sites(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const [selectedFolderId, setSelectedFolderId] = useState<string>()
  const [selectedSiteId, setSelectedSiteId] = useState<string>()
  const selectedFolder = useMemo(() => folders.data?.items.find((item) => item.id === selectedFolderId) ?? folders.data?.items[0], [folders.data, selectedFolderId])
  const selectedSite = useMemo(() => sites.data?.items.find((item) => item.id === selectedSiteId) ?? sites.data?.items[0], [sites.data, selectedSiteId])
  const machines = useQuery({
    queryKey: ['machines', organizationId, selectedSite?.id, accessToken],
    queryFn: () => apiClient.machines(accessToken!, organizationId!, selectedSite!.id),
    enabled: Boolean(accessToken && organizationId && selectedSite), retry: false
  })
  const [selectedMachineId, setSelectedMachineId] = useState<string>()
  const selectedMachine = useMemo(() => machines.data?.items.find((item) => item.id === selectedMachineId) ?? machines.data?.items[0], [machines.data, selectedMachineId])
  const cases = useQuery({
    queryKey: ['qa-cases', organizationId, selectedFolder?.id, accessToken, showTrash],
    queryFn: () => apiClient.qaCases(accessToken!, organizationId!, { folder_id: selectedFolder?.id, include_archived: showTrash, archived_only: showTrash }),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const [selectedCaseId, setSelectedCaseId] = useState<string>()
  const [selectedCaseIds, setSelectedCaseIds] = useState<string[]>([])
  const [batchProcessing, setBatchProcessing] = useState(false)
  const [purgePreview, setPurgePreview] = useState<QACasePurgePreviewResource>()
  const [purgePreviewLoading, setPurgePreviewLoading] = useState(false)
  const selectedCase = useMemo(() => cases.data?.items.find((item) => item.id === selectedCaseId), [cases.data, selectedCaseId])
  const artifacts = useQuery({
    queryKey: ['artifacts', selectedCase?.id, accessToken],
    queryFn: () => apiClient.artifacts(accessToken!, selectedCase!.id),
    enabled: Boolean(accessToken && selectedCase), retry: false
  })
  const dvhArtifactSummary = useMemo(() => summarizeDvhArtifacts(artifacts.data?.items), [artifacts.data])
  const [search, setSearch] = useState('')
  const [catalogSearch, setCatalogSearch] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [rename, setRename] = useState('')
  const [caseTitle, setCaseTitle] = useState('')
  const [caseType, setCaseType] = useState('MANUAL_MACHINE_QA')
  const [caseCycle, setCaseCycle] = useState<(typeof cycles)[number]>('DAILY')
  const [caseDate, setCaseDate] = useState('')
  const [message, setMessage] = useState<string>()
  const [artifactType, setArtifactType] = useState('DICOM')
  const [logicalRole, setLogicalRole] = useState('REFERENCE')
  const uploadInputRef = useRef<HTMLInputElement>(null)
  const uploadQueueIdRef = useRef(0)
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([])
  const [uploadQueueProcessing, setUploadQueueProcessing] = useState(false)
  const caseCreateKeyRef = useRef<string | undefined>(undefined)
  const currentUploadQueue = selectedCase ? uploadQueue.filter((item) => item.caseId === selectedCase.id) : []

  const syncPendingUploadMetadata = (nextArtifactType: string, nextLogicalRole: string) => {
    if (!selectedCase) return
    setUploadQueue((current) => updatePendingUploadMetadata(current, selectedCase.id, nextArtifactType, nextLogicalRole))
  }
  const handleArtifactTypeChange = (nextArtifactType: string) => {
    setArtifactType(nextArtifactType)
    syncPendingUploadMetadata(nextArtifactType, logicalRole)
  }
  const handleLogicalRoleChange = (nextLogicalRole: string) => {
    setLogicalRole(nextLogicalRole)
    syncPendingUploadMetadata(artifactType, nextLogicalRole)
  }

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['folders', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['qa-cases', organizationId] })
  }
  const runBatch = async (items: BatchCaseItem[], action: (caseId: string) => Promise<unknown>, actionLabel: string, skipped: BatchSkippedItem[] = [], alreadyProcessing = false) => {
    if (!items.length || (batchProcessing && !alreadyProcessing)) return
    if (!alreadyProcessing) setBatchProcessing(true)
    const results = await Promise.allSettled(items.map((item) => action(item.id)))
    const completed = items.filter((_, index) => results[index]?.status === 'fulfilled')
    const failed = items.filter((_, index) => results[index]?.status === 'rejected')
    setSelectedCaseIds([...skipped.map((item) => item.id), ...failed.map((item) => item.id)])
    setBatchProcessing(false)
    refresh()
    if (failed.length || skipped.length) {
      const completedNames = completed.map((item) => item.title).join(', ') || 'Không có bài nào'
      const failedDetails = items.flatMap((item, index) => {
        const result = results[index]
        return result?.status === 'rejected' ? [`${item.title}: ${errorMessage(result.reason)}`] : []
      })
      const skippedDetails = skipped.map((item) => `${item.title}: ${item.reason}`)
      setMessage(`${actionLabel}. Đã xử lý: ${completedNames}. Chưa xử lý: ${[...failedDetails, ...skippedDetails].join('; ')}.`)
    } else {
      setMessage(`${actionLabel}. Đã xử lý: ${completed.map((item) => item.title).join(', ')}.`)
    }
  }
  const mutation = useMutation({
    mutationFn: (action: () => Promise<unknown>) => action(),
    onSuccess: () => { caseCreateKeyRef.current = undefined; setMessage('Đã lưu thay đổi.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validationMutation = useMutation({
    mutationFn: (artifactId: string) => apiClient.validateArtifact(accessToken!, artifactId, true),
    onSuccess: (validation) => {
      const details = [...validation.errors, ...validation.warnings]
        .map((item) => typeof item.message === 'string' ? `${item.field ? `${item.field}: ` : ''}${item.message}` : '')
        .filter(Boolean)
        .join(' | ')
      setMessage(`Kết quả kiểm tra: ${labelOf(artifactStatusLabels, validation.result)}; ${validation.errors.length} lỗi, ${validation.warnings.length} cảnh báo.${details ? ` ${details}` : ''}`)
      void queryClient.invalidateQueries({ queryKey: ['artifacts', selectedCase?.id] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || folders.isPending || sites.isPending || testDefinitions.isPending) return <main className="auth-state">Đang tải khu vực kiểm tra chất lượng máy…</main>
  const failure = bootstrap.error ?? folders.error ?? sites.error ?? testDefinitions.error
  if (failure || !organizationId || !folders.data || !sites.data) return <div className="page"><section className="alert alert--error"><h1>Không thể mở khu vực kiểm tra chất lượng máy</h1><p>{errorMessage(failure)}</p><button onClick={() => { void folders.refetch(); void sites.refetch() }}>Thử lại</button></section></div>

  const definitions = testDefinitions.data?.items ?? []
  const definitionByKey = new Map(definitions.map((item) => [item.key, item]))
  const selectedDefinition = definitionByKey.get(caseType)
  const selectedCaseDefinition = selectedCase?.qa_definition_key ? definitionByKey.get(selectedCase.qa_definition_key) : undefined
  const selectedCaseNeedsInputFile = Boolean(selectedCase && (definitionNeedsInputFile(selectedCaseDefinition) || (!selectedCaseDefinition && (artifacts.data?.items ?? []).some((item) => item.artifact_type === 'DICOM'))))
  const selectedCaseSupportsDoseAnalysis = Boolean(selectedCase && (definitionSupportsDoseAnalysis(selectedCaseDefinition) || dvhArtifactSummary.dose > 0 || dvhArtifactSummary.structure > 0))
  const visibleDefinitions = definitions.filter((item) => {
    const query = catalogSearch.trim().toLowerCase()
    return !query || `${item.name} ${item.family} ${item.description}`.toLowerCase().includes(query)
  })
  const groupedDefinitions = visibleDefinitions.reduce<Record<string, QATestDefinitionResource[]>>((groups, item) => {
    (groups[item.family] ??= []).push(item)
    return groups
  }, {})
  const displayCaseType = (item: { qa_definition_key: string | null; qa_type: string }) => item.qa_definition_key ? definitionByKey.get(item.qa_definition_key)?.name ?? item.qa_type : labelOf(qaTypeLabels, item.qa_type)
  const visibleCases = cases.data?.items.filter((item) => isCaseInArchiveView(item.is_archived, showTrash) && (item.title.toLowerCase().includes(search.trim().toLowerCase()) || displayCaseType(item).toLowerCase().includes(search.trim().toLowerCase()))) ?? []
  const selectedCases = visibleCases.filter((item) => selectedCaseIds.includes(item.id))
  const allVisibleSelected = visibleCases.length > 0 && visibleCases.every((item) => selectedCaseIds.includes(item.id))
  const toggleTrash = () => {
    setShowTrash((current) => !current)
    setSelectedCaseIds([])
    setSelectedCaseId(undefined)
    setPurgePreview(undefined)
  }
  const toggleSelectedCase = (caseId: string) => {
    setSelectedCaseIds((current) => toggleCaseSelection(current, caseId))
  }
  const toggleAllVisibleCases = () => {
    setSelectedCaseIds((current) => toggleAllVisibleCaseSelection(current, visibleCases.map((item) => item.id)))
  }
  const archiveSelectedCases = () => void runBatch(selectedCases, (caseId) => apiClient.updateQACase(accessToken!, caseId, { is_archived: true }), 'Đưa vào thùng rác')
  const restoreSelectedCases = () => void runBatch(selectedCases, (caseId) => apiClient.restoreQACase(accessToken!, caseId), 'Khôi phục')
  const previewPurgeCase = async (item: BatchCaseItem) => {
    setPurgePreviewLoading(true)
    setPurgePreview(undefined)
    try {
      setPurgePreview(await apiClient.purgeQACasePreview(accessToken!, item.id))
    } catch (error) {
      setMessage(`${item.title}: ${errorMessage(error)}`)
    } finally {
      setPurgePreviewLoading(false)
    }
  }
  const purgeSelectedCases = async () => {
    if (!selectedCases.length || batchProcessing) return
    const items = [...selectedCases]
    setBatchProcessing(true)
    const previews = await Promise.allSettled(items.map((item) => apiClient.purgeQACasePreview(accessToken!, item.id)))
    const previewFailures = items.filter((_, index) => previews[index]?.status === 'rejected')
    if (previewFailures.length) {
      setSelectedCaseIds(previewFailures.map((item) => item.id))
      setBatchProcessing(false)
      const reasons = items.flatMap((item, index) => {
        const result = previews[index]
        return result?.status === 'rejected' ? [`${item.title}: ${errorMessage(result.reason)}`] : []
      })
      setMessage(`Chưa thể chuẩn bị xóa. ${reasons.join('; ')}`)
      return
    }
    const successfulPreviews = previews.map((result) => result.status === 'fulfilled' ? result.value : undefined)
    const blocked = items.filter((_, index) => !successfulPreviews[index]?.can_purge)
    const eligible = items.filter((_, index) => successfulPreviews[index]?.can_purge)
    if (!eligible.length) {
      setSelectedCaseIds(blocked.map((item) => item.id))
      setBatchProcessing(false)
      const reasons = items.map((item, index) => {
        const preview = successfulPreviews[index]
        if (!preview?.is_archived) return `${item.title}: Hãy lưu trữ bài trước khi xóa vĩnh viễn.`
        return `${item.title}: còn ${purgeReferenceSummary(preview.references)}`
      })
      setMessage(`Chưa có bài nào đủ điều kiện xóa. ${reasons.join('; ')}`)
      return
    }
    const summary = items.map((item, index) => {
      const preview = successfulPreviews[index]!
      const date = new Date(preview.performed_at).toLocaleString('vi-VN')
      const status = preview.can_purge
        ? `${preview.site_name} · ${preview.machine_name} · ${date}`
        : `Chưa thể xóa: ${preview.is_archived ? `còn ${purgeReferenceSummary(preview.references)}` : 'bài chưa được lưu trữ'}`
      return `• ${item.title} — ${status}`
    }).join('\n')
    if (!window.confirm(`Xóa vĩnh viễn các bài đủ điều kiện sau?\n\n${summary}\n\nCác bài còn liên kết sẽ được giữ nguyên. Thao tác này không thể khôi phục.`)) {
      setBatchProcessing(false)
      setMessage('Đã hủy thao tác xóa vĩnh viễn.')
      return
    }
    const skipped = blocked.map((item) => {
      const preview = successfulPreviews[items.indexOf(item)]!
      return {
        ...item,
        reason: preview.is_archived
          ? `còn ${purgeReferenceSummary(preview.references)}`
          : 'bài chưa được lưu trữ'
      }
    })
    void runBatch(eligible, (caseId) => apiClient.purgeQACaseConfirmed(accessToken!, caseId), 'Xóa vĩnh viễn', skipped, true)
  }
  const createFolder = () => {
    const name = newFolderName.trim()
    if (!name) return setMessage('Tên thư mục không được để trống.')
    mutation.mutate(() => apiClient.createFolder(accessToken!, organizationId, { name, ...(selectedFolder ? { parent_folder_id: selectedFolder.id } : {}) }))
    setNewFolderName('')
  }
  const renameFolder = () => {
    const name = rename.trim()
    if (!selectedFolder || !name) return setMessage('Chọn thư mục và nhập tên mới.')
    mutation.mutate(() => apiClient.updateFolder(accessToken!, selectedFolder.id, { name }))
    setRename('')
  }
  const archiveFolder = (folder: FolderResource) => mutation.mutate(() => apiClient.updateFolder(accessToken!, folder.id, { is_archived: !folder.is_archived }))
  const createCase = () => {
    if (!selectedFolder || !selectedSite || !selectedMachine) return setMessage('Cần chọn thư mục, cơ sở và máy trước khi tạo bài kiểm tra.')
    if (!caseTitle.trim() || !caseDate) return setMessage('Tên bài kiểm tra và thời điểm thực hiện là bắt buộc.')
    caseCreateKeyRef.current ??= crypto.randomUUID()
    mutation.mutate(() => apiClient.createQACase(accessToken!, organizationId, {
      site_id: selectedSite.id, machine_id: selectedMachine.id, primary_folder_id: selectedFolder.id,
      qa_definition_key: caseType, qa_type: selectedDefinition?.name, qa_cycle: caseCycle,
      performed_at: new Date(caseDate).toISOString(), title: caseTitle.trim(), idempotency_key: caseCreateKeyRef.current
    }))
    setCaseTitle('')
  }
  const queueArtifactFiles = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? [])
    if (!files.length) return
    const batchId = Date.now()
    setUploadQueue((current) => [
      ...current,
      ...files.map((file, index) => {
        uploadQueueIdRef.current += 1
        return {
          id: `upload-${batchId}-${index}-${uploadQueueIdRef.current}`,
          caseId: selectedCase!.id,
          file,
          artifactType,
          logicalRole,
          status: 'PENDING' as const
        }
      })
    ])
    event.target.value = ''
    setMessage(`${files.length} tệp đã được thêm vào hàng đợi tải lên.`)
  }
  const updateUploadQueueItem = (itemId: string, patch: Partial<UploadQueueItem>) => {
    setUploadQueue((current) => current.map((item) => item.id === itemId ? { ...item, ...patch } : item))
  }
  const uploadPendingQueue = async () => {
    if (!selectedCase || uploadQueueProcessing) return
    const pending = currentUploadQueue.filter((item) => item.status === 'PENDING')
    if (!pending.length) return setMessage('Không có tệp đang chờ tải lên.')
    setUploadQueueProcessing(true)
    await processUploadQueue({
      items: pending,
      caseId: selectedCase.id,
      upload: (item) => apiClient.uploadArtifact(accessToken!, item.caseId, item.file, item.artifactType, item.logicalRole),
      update: updateUploadQueueItem,
      formatError: errorMessage
    })
    void queryClient.invalidateQueries({ queryKey: ['artifacts', selectedCase.id] })
    setUploadQueueProcessing(false)
    setMessage(`Đã xử lý ${pending.length} tệp trong hàng đợi; tệp lỗi có thể thử lại riêng.`)
  }
  const retryUploadQueueItem = async (itemId: string) => {
    if (uploadQueueProcessing || !selectedCase) return
    const item = uploadQueue.find((candidate) => candidate.id === itemId)
    if (!item || item.caseId !== selectedCase.id || item.status !== 'FAILED') return
    setUploadQueueProcessing(true)
    await processUploadQueue({
      items: [item],
      caseId: selectedCase.id,
      allowedStatuses: ['FAILED'],
      upload: (candidate) => apiClient.uploadArtifact(accessToken!, candidate.caseId, candidate.file, candidate.artifactType, candidate.logicalRole),
      update: updateUploadQueueItem,
      formatError: errorMessage
    })
    void queryClient.invalidateQueries({ queryKey: ['artifacts', selectedCase.id] })
    setUploadQueueProcessing(false)
  }
  const downloadArtifact = async (artifactId: string) => {
    try {
      const result = await apiClient.downloadArtifact(accessToken!, artifactId)
      window.open(result.url, '_blank', 'noopener,noreferrer')
    } catch (error) {
      setMessage(errorMessage(error))
    }
  }

  return (
    <div className="page page--wide">
      <header className="page-header"><div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY</p><h1>Kiểm tra chất lượng máy</h1><p>Chọn bài kiểm tra, nhập đúng loại dữ liệu, lưu kết quả và mở lại lịch sử khi cần.</p></div><button className="button-secondary" onClick={toggleTrash}>{showTrash ? 'Đóng thùng rác' : 'Mở thùng rác'}</button></header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
      <div className="archive-layout">
        <section className="panel folder-panel"><div className="panel-heading"><div><p className="eyebrow">CÂY THƯ MỤC</p><h2>{showTrash ? 'Thư mục và bài đã lưu trữ' : 'Thư mục kiểm tra'}</h2></div><strong>{folders.data.total}</strong></div>{!showTrash && <div className="stack-form"><label>Thư mục mới<input placeholder="Ví dụ: 2026 / Kiểm tra hằng ngày" value={newFolderName} onChange={(event) => setNewFolderName(event.target.value)} /></label><button disabled={mutation.isPending} onClick={createFolder}>Tạo thư mục</button></div>}<div className="folder-tree" role="tree">{folders.data.items.map((folder) => <div className="folder-row" key={folder.id} style={{ paddingLeft: `${folder.depth * 18 + 8}px` }}><button className={folder.id === selectedFolder?.id ? 'folder-link folder-link--selected' : 'folder-link'} onClick={() => setSelectedFolderId(folder.id)}><span aria-hidden="true">{folder.is_archived ? '□' : '▣'}</span>{folder.name}</button><small>{folder.is_archived ? 'Đã lưu trữ' : ''}</small></div>)}</div>{selectedFolder && <div className="folder-editor"><label>Đổi tên thư mục<input disabled={selectedFolder.is_archived} value={rename || selectedFolder.name} onChange={(event) => setRename(event.target.value)} /></label><div className="table-actions">{!selectedFolder.is_archived && <button onClick={renameFolder}>Lưu tên</button>}<button className="button-secondary" onClick={() => archiveFolder(selectedFolder)}>{selectedFolder.is_archived ? 'Khôi phục' : 'Lưu trữ'}</button></div></div>}</section>
        <section className="panel archive-content"><div className="panel-heading"><div><p className="eyebrow">{showTrash ? 'THÙNG RÁC' : 'BÀI KIỂM TRA VÀ LỊCH SỬ'}</p><h2>{selectedFolder?.path ?? 'Tất cả bài kiểm tra'}</h2></div><strong>{showTrash ? visibleCases.length : cases.data?.total ?? '—'}</strong></div><div className="filter-row"><label>Tìm kiếm lịch sử<input placeholder="Tên bài hoặc loại kiểm tra" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>Cơ sở<select aria-label="Cơ sở" value={selectedSite?.id ?? ''} onChange={(event) => setSelectedSiteId(event.target.value)}>{sites.data.items.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label>Máy<select aria-label="Máy" value={selectedMachine?.id ?? ''} onChange={(event) => setSelectedMachineId(event.target.value)}>{(machines.data?.items ?? []).map((machine) => <option key={machine.id} value={machine.id}>{machine.display_name}</option>)}</select></label></div>{visibleCases.length > 0 && <div className="case-selection-toolbar" role="group" aria-label="Thao tác với các bài đã chọn"><label className="checkbox-row"><input type="checkbox" aria-label="Chọn tất cả bài đang hiển thị" checked={allVisibleSelected} onChange={toggleAllVisibleCases} /> Chọn tất cả</label>{selectedCaseIds.length > 0 && <><span>Đã chọn {selectedCaseIds.length} bài</span><button className="button-secondary" disabled={batchProcessing} onClick={showTrash ? restoreSelectedCases : archiveSelectedCases}>{showTrash ? 'Khôi phục đã chọn' : 'Đưa vào thùng rác'}</button>{showTrash && <button className="button-secondary" disabled={batchProcessing} onClick={purgeSelectedCases}>Xóa vĩnh viễn đã chọn</button>}<button className="button-secondary" disabled={batchProcessing} onClick={() => setSelectedCaseIds([])}>Bỏ chọn</button></>}</div>}{!showTrash && <>
          <section className="qa-catalog-panel"><div className="panel-heading"><div><p className="eyebrow">DANH MỤC BÀI KIỂM TRA</p><h2>Chọn bài kiểm tra</h2></div><strong>{visibleDefinitions.length}/{definitions.length}</strong></div><div className="qa-catalog-toolbar"><label>Tìm trong danh mục<input placeholder="Tìm tên bài, nhóm hoặc mô tả" value={catalogSearch} onChange={(event) => setCatalogSearch(event.target.value)} /></label><p>Chọn trực tiếp một bài bên dưới. Bài chưa sẵn sàng vẫn được hiển thị để anh nhìn thấy đầy đủ danh mục.</p></div><div className="qa-catalog-groups">{Object.entries(groupedDefinitions).map(([family, items]) => <section className="qa-catalog-family" key={family}><h3>{family}</h3><div className="qa-test-grid">{items.map((item) => { const ready = item.implementation_status === 'READY'; const selected = item.key === caseType; return <button type="button" className={`qa-test-card${selected ? ' qa-test-card--selected' : ''}${!ready ? ' qa-test-card--planned' : ''}`} key={item.key} aria-pressed={selected} disabled={!ready} title={ready ? item.description : 'Bài kiểm tra này đang được chuẩn bị.'} onClick={() => { if (ready) { setCaseType(item.key); setMessage(undefined) } }}><span className="qa-test-card__name">{item.name}</span><span className="qa-test-card__meta">{inputKindLabel(item.input_kind)}{item.supports_manual_adjustment ? ' · Có thể chỉnh tay' : ''}</span><span className={ready ? 'qa-test-card__status' : 'qa-test-card__status qa-test-card__status--planned'}>{ready ? 'Sẵn sàng' : 'Đang chuẩn bị'}</span></button> })}</div></section>)}</div>{!visibleDefinitions.length && <p className="empty-state">Không tìm thấy bài kiểm tra phù hợp.</p>}</section>
          <div className="stack-form case-form"><div className="case-form__selected"><span className="eyebrow">BÀI ĐÃ CHỌN</span><strong>{selectedDefinition?.name ?? 'Chưa chọn bài kiểm tra'}</strong>{selectedDefinition && <><p>{selectedDefinition.description}</p><small>Dữ liệu cần chuẩn bị: {selectedDefinition.required_inputs.join(', ')}.</small></>}</div><label>Tên bài kiểm tra<input placeholder="Ví dụ: Kiểm tra chất lượng tháng 9" value={caseTitle} onChange={(event) => setCaseTitle(event.target.value)} /></label><div className="filter-row"><label>Chu kỳ<select value={caseCycle} onChange={(event) => setCaseCycle(event.target.value as (typeof cycles)[number])}>{cycles.map((cycle) => <option key={cycle} value={cycle}>{cycleLabels[cycle]}</option>)}</select></label><label>Thời điểm thực hiện<input type="datetime-local" value={caseDate} onChange={(event) => setCaseDate(event.target.value)} /></label><div className="case-form__action"><button disabled={mutation.isPending || !selectedDefinition || selectedDefinition.implementation_status !== 'READY'} onClick={createCase}>Bắt đầu bài kiểm tra</button></div></div></div>
        </>}{cases.isPending ? <p>Đang tải lịch sử bài kiểm tra…</p> : cases.error ? <div className="alert alert--error"><p>{errorMessage(cases.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th><span className="visually-hidden">Chọn</span></th><th>Tên bài</th><th>Loại</th><th>Phân loại</th><th>Chu kỳ</th><th>Thực hiện</th><th>Trạng thái</th><th /></tr></thead><tbody>{visibleCases.map((item) => <tr key={item.id}><td><input type="checkbox" aria-label={`Chọn ${item.title}`} checked={selectedCaseIds.includes(item.id)} onChange={() => toggleSelectedCase(item.id)} /></td><td><strong>{item.title}</strong></td><td>{displayCaseType(item)}</td><td>{!item.qa_definition_key && !item.is_archived ? <select aria-label={`Gắn loại bài cho ${item.title}`} defaultValue="" onChange={(event) => { if (event.target.value) mutation.mutate(() => apiClient.updateQACase(accessToken!, item.id, { qa_definition_key: event.target.value })) }}><option value="">Chọn loại</option>{definitions.map((definition) => <option key={definition.key} value={definition.key}>{definition.name}</option>)}</select> : item.qa_definition_key ? 'Đã gắn' : '—'}</td><td>{labelOf(cycleLabels, item.qa_cycle)}</td><td>{new Date(item.performed_at).toLocaleString('vi-VN')}</td><td><span className="status-badge">{labelOf(caseStatusLabels, item.is_archived ? 'ARCHIVED' : item.case_status)}</span></td><td><div className="table-actions"><button className="button-secondary" onClick={() => setSelectedCaseId(item.id)}>Mở bài</button>{!item.is_archived && (!item.qa_definition_key || definitionByKey.get(item.qa_definition_key)?.implementation_status === 'READY') && <Link className="button-link button-secondary" to={`/app/qa/cases/${item.id}/machine-qa`}>Kiểm tra máy</Link>}{!item.is_archived && item.qa_definition_key === 'PSQA_GAMMA_2D' && <Link className="button-link button-secondary" to={`/app/qa/cases/${item.id}/gamma`}>Phân tích Gamma</Link>}{item.is_archived ? <><button className="button-secondary" onClick={() => mutation.mutate(() => apiClient.restoreQACase(accessToken!, item.id))}>Khôi phục</button><button className="button-secondary" onClick={() => void previewPurgeCase(item)}>Xem trước xóa</button><button className="button-secondary" onClick={() => mutation.mutate(() => apiClient.purgeQACase(accessToken!, item.id))}>Xóa vĩnh viễn</button></> : <button className="button-secondary" onClick={() => mutation.mutate(() => apiClient.updateQACase(accessToken!, item.id, { is_archived: true }))}>Lưu trữ</button>}</div></td></tr>)}</tbody></table>{!visibleCases.length && <p className="empty-state">{showTrash ? 'Thùng rác đang trống.' : 'Chưa có bài kiểm tra phù hợp. Hãy chọn một bài trong danh mục để bắt đầu.'}</p>}</div>}
          {showTrash && (purgePreviewLoading || purgePreview) && <section className="purge-preview-panel" aria-live="polite">
            <div className="panel-heading"><div><p className="eyebrow">XEM TRƯỚC XÓA</p><h2>Kiểm tra điều kiện xóa</h2></div><button className="button-secondary" onClick={() => setPurgePreview(undefined)}>Đóng</button></div>
            {purgePreviewLoading ? <p>Đang kiểm tra liên kết của bài…</p> : purgePreview && <><p><strong>{purgePreview.title}</strong></p><p className="form-hint">{purgePreview.site_name} · {purgePreview.machine_name} · {new Date(purgePreview.performed_at).toLocaleString('vi-VN')}</p>{purgePreview.can_purge ? <p className="preview-status preview-status--allowed">Bài đã lưu trữ và chưa có dữ liệu liên quan. Có thể xóa sau khi xác nhận.</p> : <div className="preview-status preview-status--blocked"><strong>Chưa thể xóa vĩnh viễn.</strong><p>{purgePreview.is_archived ? `Còn ${purgeReferenceSummary(purgePreview.references)} liên quan.` : 'Bài chưa được lưu trữ.'}</p><p>Hồ sơ và toàn bộ dữ liệu liên quan vẫn được giữ nguyên.</p></div>}</>}
          </section>}
          {selectedCase && (selectedCaseNeedsInputFile || selectedCaseSupportsDoseAnalysis) && <section className="artifact-panel">
            {selectedCaseSupportsDoseAnalysis && <div className="dvh-quick-link"><Link className="button-link button-secondary" to={`/app/qa/cases/${selectedCase.id}/dvh`}>Mở phân tích liều cho bài này</Link>{artifacts.isPending ? <span className="form-hint">{dvhArtifactStatusLabel(dvhArtifactSummary, 'loading')}</span> : artifacts.error ? <span className="status-badge status-badge--warning">{dvhArtifactStatusLabel(dvhArtifactSummary, 'error')}</span> : <span className={dvhArtifactSummary.ready ? 'status-badge' : 'status-badge status-badge--warning'}>{dvhArtifactStatusLabel(dvhArtifactSummary, 'ready')}</span>}</div>}
            {selectedCaseNeedsInputFile && <><div className="panel-heading"><div><p className="eyebrow">TỆP ĐẦU VÀO</p><h2>Tệp của {selectedCase.title}</h2></div><strong>{artifacts.data?.total ?? '—'}</strong></div><div className="artifact-upload"><label>Tệp cần phân tích<input ref={uploadInputRef} type="file" multiple onChange={queueArtifactFiles} /></label><label>Loại<select value={artifactType} onChange={(event) => handleArtifactTypeChange(event.target.value)}><option value="DICOM">Tệp DICOM</option><option value="MEASUREMENT">Số đo</option><option value="OTHER">Tệp khác</option></select></label><label>Vai trò của tệp<select value={logicalRole} onChange={(event) => handleLogicalRoleChange(event.target.value)}><option value="REFERENCE">Tệp tham chiếu</option><option value="EVALUATION">Tệp đánh giá</option><option value="CT">Ảnh CT</option><option value="RTSTRUCT">Cấu trúc RT</option><option value="RTPLAN">Kế hoạch xạ trị</option><option value="MEASUREMENT">Số đo</option></select></label><button disabled={uploadQueueProcessing || !currentUploadQueue.some((item) => item.status === 'PENDING')} onClick={() => void uploadPendingQueue()}>{uploadQueueProcessing ? 'Đang tải lên…' : 'Tải lên danh sách'}</button></div>{currentUploadQueue.length > 0 && <section className="artifact-upload-queue" aria-live="polite"><div className="panel-heading"><div><p className="eyebrow">HÀNG ĐỢI TẢI LÊN</p><h3>Hàng đợi tệp</h3></div><strong>{currentUploadQueue.filter((item) => item.status === 'UPLOADED').length}/{currentUploadQueue.length}</strong></div><ul>{currentUploadQueue.map((item) => <li key={item.id}><div><strong>{item.file.name}</strong><small>{item.file.size.toLocaleString('vi-VN')} byte · {uploadQueueStatusLabel(item.status)}{item.duplicate ? ' · tệp đã tồn tại' : ''}</small>{item.error && <span className="error-text">{item.error}</span>}</div>{item.status === 'FAILED' && <button className="button-secondary" disabled={uploadQueueProcessing} onClick={() => void retryUploadQueueItem(item.id)}>Thử lại</button>}</li>)}</ul><p className="form-hint">Các tệp đang chờ sẽ dùng loại và vai trò đang chọn; có thể đổi trước khi tải lên. Các tệp thành công được giữ lại; khi một tệp lỗi, chỉ tệp đó được thử lại và các tệp đã tải lên không bị hoàn tác.</p></section>}{selectedCaseSupportsDoseAnalysis && <p className="form-hint">Để chạy phân tích liều, tải lên và kiểm tra một RTDOSE cùng một RTSTRUCT; chọn đúng vai trò của từng tệp. Ảnh CT là tùy chọn để phủ lên hình ảnh giải phẫu. Chỉ tệp DICOM hợp lệ mới được dùng cho phân tích.</p>}{artifacts.isPending ? <p>Đang tải tệp…</p> : artifacts.error ? <div className="alert alert--error"><p>{errorMessage(artifacts.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Tệp</th><th>Loại</th><th>Trạng thái</th><th /></tr></thead><tbody>{(artifacts.data?.items ?? []).map((artifact) => <tr key={artifact.id}><td><strong>{artifact.original_filename}</strong><small className="table-subtitle">{artifact.byte_size.toLocaleString('vi-VN')} byte</small></td><td>{labelOf(artifactTypeLabels, artifact.artifact_type)}</td><td><span className={artifact.data_status === 'INVALID' ? 'status-badge status-badge--warning' : 'status-badge'}>{labelOf(artifactStatusLabels, artifact.data_status)}</span></td><td><div className="table-actions"><button className="button-secondary" disabled={validationMutation.isPending} onClick={() => validationMutation.mutate(artifact.id)}>Kiểm tra dữ liệu</button><button className="button-secondary" onClick={() => void downloadArtifact(artifact.id)}>Tải xuống</button></div></td></tr>)}</tbody></table>{!artifacts.data?.items.length && <p className="empty-state">Chưa có tệp. Tải tệp đầu tiên để kiểm tra dữ liệu.</p>}</div>}</>}
          </section>}
          {selectedCase && !selectedCaseNeedsInputFile && !selectedCaseSupportsDoseAnalysis && <p className="selected-case-note">Bài này dùng số đo nhập tay, nên không cần tải tệp đầu vào hoặc mở phân tích liều. Chọn “Kiểm tra máy” để nhập số đo và đánh giá kết quả.</p>}
          {!selectedCase && <p className="selected-case-note">Chọn “Mở bài” trong lịch sử để xem chi tiết. Khu vực tệp chỉ xuất hiện với bài kiểm tra cần tệp đầu vào.</p>}
        </section>
      </div>
    </div>
  )
}
