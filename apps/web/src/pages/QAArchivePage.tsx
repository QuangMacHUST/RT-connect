import { useMemo, useRef, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { ApiClientError, apiClient, type FolderResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { dvhArtifactStatusLabel, summarizeDvhArtifacts } from './dvhArtifactSummary'
import { processUploadQueue, type UploadQueueItem } from './uploadQueue'

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

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    const messages: Record<string, string> = {
      FOLDER_NAME_CONFLICT: 'Tên thư mục đã được sử dụng trong đơn vị này.',
      REVISION_CONFLICT: 'Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại rồi thực hiện lại thao tác.',
      RESOURCE_ARCHIVED: 'Mục này đã được lưu trữ. Hãy khôi phục trước khi sửa.',
      PARENT_NOT_AVAILABLE: 'Mục cha đang được lưu trữ nên không thể thực hiện thao tác này.',
      MACHINE_NOT_FOUND: 'Không tìm thấy máy đang chọn hoặc máy không còn hoạt động.'
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
  const folders = useQuery({
    queryKey: ['folders', organizationId, accessToken],
    queryFn: () => apiClient.folders(accessToken!, organizationId!),
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
    queryKey: ['qa-cases', organizationId, selectedFolder?.id, accessToken],
    queryFn: () => apiClient.qaCases(accessToken!, organizationId!, { folder_id: selectedFolder?.id }),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const [selectedCaseId, setSelectedCaseId] = useState<string>()
  const selectedCase = useMemo(() => cases.data?.items.find((item) => item.id === selectedCaseId) ?? cases.data?.items[0], [cases.data, selectedCaseId])
  const artifacts = useQuery({
    queryKey: ['artifacts', selectedCase?.id, accessToken],
    queryFn: () => apiClient.artifacts(accessToken!, selectedCase!.id),
    enabled: Boolean(accessToken && selectedCase), retry: false
  })
  const dvhArtifactSummary = useMemo(() => summarizeDvhArtifacts(artifacts.data?.items), [artifacts.data])
  const [search, setSearch] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [rename, setRename] = useState('')
  const [caseTitle, setCaseTitle] = useState('')
  const [caseType, setCaseType] = useState('Machine QA')
  const [caseCycle, setCaseCycle] = useState<(typeof cycles)[number]>('DAILY')
  const [caseDate, setCaseDate] = useState('')
  const [message, setMessage] = useState<string>()
  const [artifactType, setArtifactType] = useState('DICOM')
  const [logicalRole, setLogicalRole] = useState('REFERENCE')
  const uploadInputRef = useRef<HTMLInputElement>(null)
  const uploadQueueIdRef = useRef(0)
  const [uploadQueue, setUploadQueue] = useState<UploadQueueItem[]>([])
  const [uploadQueueProcessing, setUploadQueueProcessing] = useState(false)
  const currentUploadQueue = selectedCase ? uploadQueue.filter((item) => item.caseId === selectedCase.id) : []

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['folders', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['qa-cases', organizationId] })
  }
  const mutation = useMutation({
    mutationFn: (action: () => Promise<unknown>) => action(),
    onSuccess: () => { setMessage('Đã lưu thay đổi.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const validationMutation = useMutation({
    mutationFn: (artifactId: string) => apiClient.validateArtifact(accessToken!, artifactId),
    onSuccess: (validation) => {
      setMessage(`Kết quả kiểm tra: ${labelOf(artifactStatusLabels, validation.result)}; ${validation.errors.length} lỗi, ${validation.warnings.length} cảnh báo.`)
      void queryClient.invalidateQueries({ queryKey: ['artifacts', selectedCase?.id] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || folders.isPending || sites.isPending) return <main className="auth-state">Đang tải khu vực kiểm tra chất lượng máy…</main>
  const failure = bootstrap.error ?? folders.error ?? sites.error
  if (failure || !organizationId || !folders.data || !sites.data) return <div className="page"><section className="alert alert--error"><h1>Không thể mở khu vực kiểm tra chất lượng máy</h1><p>{errorMessage(failure)}</p><button onClick={() => { void folders.refetch(); void sites.refetch() }}>Thử lại</button></section></div>

  const visibleCases = cases.data?.items.filter((item) => item.title.toLowerCase().includes(search.trim().toLowerCase()) || item.qa_type.toLowerCase().includes(search.trim().toLowerCase())) ?? []
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
  const archiveFolder = (folder: FolderResource) => mutation.mutate(() => apiClient.updateFolder(accessToken!, folder.id, { is_archived: true }))
  const createCase = () => {
    if (!selectedFolder || !selectedSite || !selectedMachine) return setMessage('Cần chọn thư mục, cơ sở và máy trước khi tạo bài kiểm tra.')
    if (!caseTitle.trim() || !caseDate) return setMessage('Tên bài kiểm tra và thời điểm thực hiện là bắt buộc.')
    mutation.mutate(() => apiClient.createQACase(accessToken!, organizationId, {
      site_id: selectedSite.id, machine_id: selectedMachine.id, primary_folder_id: selectedFolder.id,
      qa_type: caseType, qa_cycle: caseCycle, performed_at: new Date(caseDate).toISOString(), title: caseTitle.trim()
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
    <div className="page">
      <header className="page-header"><div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY</p><h1>Kiểm tra chất lượng máy</h1><p>Chọn bài kiểm tra, lưu kết quả, mở lại lịch sử và quản lý tệp theo cách quen thuộc.</p></div></header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
      <div className="archive-layout">
        <section className="panel folder-panel"><div className="panel-heading"><div><p className="eyebrow">CÂY THƯ MỤC</p><h2>Thư mục kiểm tra</h2></div><strong>{folders.data.total}</strong></div><div className="stack-form"><label>Thư mục mới<input placeholder="Ví dụ: 2026 / Kiểm tra hằng ngày" value={newFolderName} onChange={(event) => setNewFolderName(event.target.value)} /></label><button disabled={mutation.isPending} onClick={createFolder}>Tạo thư mục</button></div><div className="folder-tree" role="tree">{folders.data.items.map((folder) => <div className="folder-row" key={folder.id} style={{ paddingLeft: `${folder.depth * 18 + 8}px` }}><button className={folder.id === selectedFolder?.id ? 'folder-link folder-link--selected' : 'folder-link'} onClick={() => setSelectedFolderId(folder.id)}><span aria-hidden="true">{folder.is_archived ? '□' : '▣'}</span>{folder.name}</button><small>{folder.is_archived ? 'Đã lưu trữ' : ''}</small></div>)}</div>{selectedFolder && <div className="folder-editor"><label>Đổi tên thư mục<input value={rename || selectedFolder.name} onChange={(event) => setRename(event.target.value)} /></label><div className="table-actions"><button onClick={renameFolder}>Lưu tên</button><button className="button-secondary" onClick={() => archiveFolder(selectedFolder)}>Lưu trữ</button></div></div>}</section>
        <section className="panel archive-content"><div className="panel-heading"><div><p className="eyebrow">BÀI KIỂM TRA</p><h2>{selectedFolder?.path ?? 'Tất cả bài kiểm tra'}</h2></div><strong>{cases.data?.total ?? '—'}</strong></div><div className="filter-row"><label>Tìm kiếm<input placeholder="Tên bài hoặc loại kiểm tra" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>Cơ sở<select aria-label="Cơ sở" value={selectedSite?.id ?? ''} onChange={(event) => setSelectedSiteId(event.target.value)}>{sites.data.items.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label>Máy<select aria-label="Máy" value={selectedMachine?.id ?? ''} onChange={(event) => setSelectedMachineId(event.target.value)}>{(machines.data?.items ?? []).map((machine) => <option key={machine.id} value={machine.id}>{machine.display_name}</option>)}</select></label></div><div className="stack-form case-form"><label>Tên bài kiểm tra<input placeholder="Ví dụ: Kiểm tra chất lượng tháng 9" value={caseTitle} onChange={(event) => setCaseTitle(event.target.value)} /></label><div className="filter-row"><label>Loại kiểm tra<select value={caseType} onChange={(event) => setCaseType(event.target.value)}>{Object.entries(qaTypeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Chu kỳ<select value={caseCycle} onChange={(event) => setCaseCycle(event.target.value as (typeof cycles)[number])}>{cycles.map((cycle) => <option key={cycle} value={cycle}>{cycleLabels[cycle]}</option>)}</select></label><label>Thời điểm thực hiện<input type="datetime-local" value={caseDate} onChange={(event) => setCaseDate(event.target.value)} /></label></div><button disabled={mutation.isPending} onClick={createCase}>Tạo bài kiểm tra</button></div>{cases.isPending ? <p>Đang tải bài kiểm tra…</p> : cases.error ? <div className="alert alert--error"><p>{errorMessage(cases.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Tên bài</th><th>Loại</th><th>Chu kỳ</th><th>Thực hiện</th><th>Trạng thái</th><th /></tr></thead><tbody>{visibleCases.map((item) => <tr key={item.id}><td><strong>{item.title}</strong></td><td>{labelOf(qaTypeLabels, item.qa_type)}</td><td>{labelOf(cycleLabels, item.qa_cycle)}</td><td>{new Date(item.performed_at).toLocaleString('vi-VN')}</td><td><span className="status-badge">{labelOf(caseStatusLabels, item.is_archived ? 'ARCHIVED' : item.case_status)}</span></td><td><div className="table-actions"><button className="button-secondary" onClick={() => setSelectedCaseId(item.id)}>Mở bài</button><Link className="button-link button-secondary" to={`/app/qa/cases/${item.id}/machine-qa`}>Kiểm tra máy</Link><Link className="button-link button-secondary" to={`/app/qa/cases/${item.id}/gamma`}>Phân tích Gamma</Link><button className="button-secondary" onClick={() => mutation.mutate(() => apiClient.updateQACase(accessToken!, item.id, { is_archived: true }))}>Lưu trữ</button></div></td></tr>)}</tbody></table>{!visibleCases.length && <p className="empty-state">Chưa có bài kiểm tra phù hợp. Tạo bài đầu tiên từ biểu mẫu ở trên.</p>}</div>}
          <section className="artifact-panel">
            {selectedCase && <div className="dvh-quick-link"><Link className="button-link button-secondary" to={`/app/qa/cases/${selectedCase.id}/dvh`}>Mở phân tích liều cho bài này</Link>{artifacts.isPending ? <span className="form-hint">{dvhArtifactStatusLabel(dvhArtifactSummary, 'loading')}</span> : artifacts.error ? <span className="status-badge status-badge--warning">{dvhArtifactStatusLabel(dvhArtifactSummary, 'error')}</span> : <span className={dvhArtifactSummary.ready ? 'status-badge' : 'status-badge status-badge--warning'}>{dvhArtifactStatusLabel(dvhArtifactSummary, 'ready')}</span>}</div>}
            <div className="panel-heading"><div><p className="eyebrow">TỆP ĐẦU VÀO</p><h2>{selectedCase ? `Tệp của ${selectedCase.title}` : 'Chọn bài kiểm tra để tải tệp'}</h2></div><strong>{artifacts.data?.total ?? '—'}</strong></div>
            {selectedCase ? <>
              <div className="artifact-upload">
                <label>Tệp DICOM hoặc số đo<input ref={uploadInputRef} type="file" multiple onChange={queueArtifactFiles} /></label>
                <label>Loại<select value={artifactType} onChange={(event) => setArtifactType(event.target.value)}><option value="DICOM">Tệp DICOM</option><option value="MEASUREMENT">Số đo</option><option value="OTHER">Tệp khác</option></select></label>
                <label>Vai trò của tệp<select value={logicalRole} onChange={(event) => setLogicalRole(event.target.value)}><option value="REFERENCE">Tệp tham chiếu</option><option value="EVALUATION">Tệp đánh giá</option><option value="CT">Ảnh CT</option><option value="RTSTRUCT">Cấu trúc RT</option><option value="RTPLAN">Kế hoạch xạ trị</option><option value="MEASUREMENT">Số đo</option></select></label>
                <button disabled={uploadQueueProcessing || !currentUploadQueue.some((item) => item.status === 'PENDING')} onClick={() => void uploadPendingQueue()}>{uploadQueueProcessing ? 'Đang tải lên…' : 'Tải lên danh sách'}</button>
              </div>
              {currentUploadQueue.length > 0 && <section className="artifact-upload-queue" aria-live="polite"><div className="panel-heading"><div><p className="eyebrow">HÀNG ĐỢI TẢI LÊN</p><h3>Hàng đợi tệp</h3></div><strong>{currentUploadQueue.filter((item) => item.status === 'UPLOADED').length}/{currentUploadQueue.length}</strong></div><ul>{currentUploadQueue.map((item) => <li key={item.id}><div><strong>{item.file.name}</strong><small>{item.file.size.toLocaleString('vi-VN')} byte · {uploadQueueStatusLabel(item.status)}{item.duplicate ? ' · tệp đã tồn tại' : ''}</small>{item.error && <span className="error-text">{item.error}</span>}</div>{item.status === 'FAILED' && <button className="button-secondary" disabled={uploadQueueProcessing} onClick={() => void retryUploadQueueItem(item.id)}>Thử lại</button>}</li>)}</ul><p className="form-hint">Các tệp thành công được giữ lại; khi một tệp lỗi, chỉ tệp đó được thử lại và các tệp đã tải lên không bị hoàn tác.</p></section>}
              <p className="form-hint">Để chạy phân tích liều, tải lên và kiểm tra một RTDOSE cùng một RTSTRUCT; chọn đúng vai trò của từng tệp. Ảnh CT là tùy chọn để phủ lên hình ảnh giải phẫu. Chỉ tệp DICOM hợp lệ mới được dùng cho phân tích.</p>
              {artifacts.isPending ? <p>Đang tải tệp…</p> : artifacts.error ? <div className="alert alert--error"><p>{errorMessage(artifacts.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Tệp</th><th>Loại</th><th>Trạng thái</th><th /></tr></thead><tbody>{(artifacts.data?.items ?? []).map((artifact) => <tr key={artifact.id}><td><strong>{artifact.original_filename}</strong><small className="table-subtitle">{artifact.byte_size.toLocaleString('vi-VN')} byte</small></td><td>{labelOf(artifactTypeLabels, artifact.artifact_type)}</td><td><span className={artifact.data_status === 'INVALID' ? 'status-badge status-badge--warning' : 'status-badge'}>{labelOf(artifactStatusLabels, artifact.data_status)}</span></td><td><div className="table-actions"><button className="button-secondary" disabled={validationMutation.isPending} onClick={() => validationMutation.mutate(artifact.id)}>Kiểm tra dữ liệu</button><button className="button-secondary" onClick={() => void downloadArtifact(artifact.id)}>Tải xuống</button></div></td></tr>)}</tbody></table>{!artifacts.data?.items.length && <p className="empty-state">Chưa có tệp. Tải tệp đầu tiên để kiểm tra dữ liệu.</p>}</div>}
              </> : <p className="empty-state">Chọn “Mở bài” trong bảng phía trên để quản lý tệp.</p>}
          </section>
        </section>
      </div>
    </div>
  )
}
