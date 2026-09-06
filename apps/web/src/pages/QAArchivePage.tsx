import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiClientError, apiClient, type FolderResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

const cycles = ['DAILY', 'MONTHLY', 'ANNUAL', 'CUSTOM'] as const

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
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
  const [search, setSearch] = useState('')
  const [newFolderName, setNewFolderName] = useState('')
  const [rename, setRename] = useState('')
  const [caseTitle, setCaseTitle] = useState('')
  const [caseType, setCaseType] = useState('Machine QA')
  const [caseCycle, setCaseCycle] = useState<(typeof cycles)[number]>('DAILY')
  const [caseDate, setCaseDate] = useState('')
  const [message, setMessage] = useState<string>()

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['folders', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['qa-cases', organizationId] })
  }
  const mutation = useMutation({
    mutationFn: (action: () => Promise<unknown>) => action(),
    onSuccess: () => { setMessage('Đã lưu thay đổi.'); refresh() },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || folders.isPending || sites.isPending) return <main className="auth-state">Đang tải QA Archive…</main>
  const failure = bootstrap.error ?? folders.error ?? sites.error
  if (failure || !organizationId || !folders.data || !sites.data) return <div className="page"><section className="alert alert--error"><h1>Không thể mở QA Archive</h1><p>{errorMessage(failure)}</p><button onClick={() => { void folders.refetch(); void sites.refetch() }}>Thử lại</button></section></div>

  const visibleCases = cases.data?.items.filter((item) => item.title.toLowerCase().includes(search.trim().toLowerCase()) || item.qa_type.toLowerCase().includes(search.trim().toLowerCase())) ?? []
  const createFolder = () => {
    const name = newFolderName.trim()
    if (!name) return setMessage('Tên folder không được để trống.')
    mutation.mutate(() => apiClient.createFolder(accessToken!, organizationId, { name, ...(selectedFolder ? { parent_folder_id: selectedFolder.id } : {}) }))
    setNewFolderName('')
  }
  const renameFolder = () => {
    const name = rename.trim()
    if (!selectedFolder || !name) return setMessage('Chọn folder và nhập tên mới.')
    mutation.mutate(() => apiClient.updateFolder(accessToken!, selectedFolder.id, { name }))
    setRename('')
  }
  const archiveFolder = (folder: FolderResource) => mutation.mutate(() => apiClient.updateFolder(accessToken!, folder.id, { is_archived: true }))
  const createCase = () => {
    if (!selectedFolder || !selectedSite || !selectedMachine) return setMessage('Cần chọn folder, site và machine trước khi tạo QA case.')
    if (!caseTitle.trim() || !caseDate) return setMessage('Tên QA case và thời điểm thực hiện là bắt buộc.')
    mutation.mutate(() => apiClient.createQACase(accessToken!, organizationId, {
      site_id: selectedSite.id, machine_id: selectedMachine.id, primary_folder_id: selectedFolder.id,
      qa_type: caseType, qa_cycle: caseCycle, performed_at: new Date(caseDate).toISOString(), title: caseTitle.trim()
    }))
    setCaseTitle('')
  }

  return (
    <div className="page">
      <header className="page-header"><div><p className="eyebrow">P5 · MOD-03</p><h1>Kho lưu trữ QA &amp; Thư mục</h1><p>Không gian folder giống cách quản lý file quen thuộc, nhưng QA case vẫn được tìm theo site, machine, chu kỳ và metadata nghiệp vụ.</p></div><span className="status-badge">API THẬT</span></header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
      <div className="archive-layout">
        <section className="panel folder-panel"><div className="panel-heading"><div><p className="eyebrow">FOLDER TREE</p><h2>Thư mục QA</h2></div><strong>{folders.data.total}</strong></div><div className="stack-form"><label>Folder mới<input placeholder="Ví dụ: 2026 / Daily QA" value={newFolderName} onChange={(event) => setNewFolderName(event.target.value)} /></label><button disabled={mutation.isPending} onClick={createFolder}>Tạo folder</button></div><div className="folder-tree" role="tree">{folders.data.items.map((folder) => <div className="folder-row" key={folder.id} style={{ paddingLeft: `${folder.depth * 18 + 8}px` }}><button className={folder.id === selectedFolder?.id ? 'folder-link folder-link--selected' : 'folder-link'} onClick={() => setSelectedFolderId(folder.id)}><span aria-hidden="true">{folder.is_archived ? '□' : '▣'}</span>{folder.name}</button><small>{folder.is_archived ? 'ARCHIVED' : ''}</small></div>)}</div>{selectedFolder && <div className="folder-editor"><label>Đổi tên folder<input value={rename || selectedFolder.name} onChange={(event) => setRename(event.target.value)} /></label><div className="table-actions"><button onClick={renameFolder}>Lưu tên</button><button className="button-secondary" onClick={() => archiveFolder(selectedFolder)}>Archive</button></div></div>}</section>
        <section className="panel archive-content"><div className="panel-heading"><div><p className="eyebrow">QA CASES</p><h2>{selectedFolder?.path ?? 'Tất cả QA case'}</h2></div><strong>{cases.data?.total ?? '—'}</strong></div><div className="filter-row"><label>Tìm kiếm<input placeholder="Tên case hoặc loại QA" value={search} onChange={(event) => setSearch(event.target.value)} /></label><label>Site<select value={selectedSite?.id ?? ''} onChange={(event) => setSelectedSiteId(event.target.value)}>{sites.data.items.map((site) => <option key={site.id} value={site.id}>{site.name}</option>)}</select></label><label>Machine<select value={selectedMachine?.id ?? ''} onChange={(event) => setSelectedMachineId(event.target.value)}>{(machines.data?.items ?? []).map((machine) => <option key={machine.id} value={machine.id}>{machine.display_name}</option>)}</select></label></div><div className="stack-form case-form"><label>Tạo QA case<input placeholder="Tên case" value={caseTitle} onChange={(event) => setCaseTitle(event.target.value)} /></label><div className="filter-row"><label>Loại QA<input value={caseType} onChange={(event) => setCaseType(event.target.value)} /></label><label>Chu kỳ<select value={caseCycle} onChange={(event) => setCaseCycle(event.target.value as (typeof cycles)[number])}>{cycles.map((cycle) => <option key={cycle}>{cycle}</option>)}</select></label><label>Thực hiện lúc<input type="datetime-local" value={caseDate} onChange={(event) => setCaseDate(event.target.value)} /></label></div><button disabled={mutation.isPending} onClick={createCase}>Tạo QA case</button></div>{cases.isPending ? <p>Đang tải QA case…</p> : cases.error ? <div className="alert alert--error"><p>{errorMessage(cases.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Tên case</th><th>Loại</th><th>Chu kỳ</th><th>Thực hiện</th><th>Trạng thái</th><th /></tr></thead><tbody>{visibleCases.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><small className="table-subtitle">{item.id}</small></td><td>{item.qa_type}</td><td>{item.qa_cycle}</td><td>{new Date(item.performed_at).toLocaleString('vi-VN')}</td><td><span className="status-badge">{item.is_archived ? 'ARCHIVED' : item.case_status}</span></td><td><button className="button-secondary" onClick={() => mutation.mutate(() => apiClient.updateQACase(accessToken!, item.id, { is_archived: true }))}>Archive</button></td></tr>)}</tbody></table>{!visibleCases.length && <p className="empty-state">Chưa có QA case phù hợp. Tạo case đầu tiên từ biểu mẫu ở trên.</p>}</div>}</section>
      </div>
    </div>
  )
}
