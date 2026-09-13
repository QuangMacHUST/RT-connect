import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiClientError, apiClient, type MachineResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { CompactPage } from '../components/CompactPage'

const machineStatuses = ['ACTIVE', 'OFFLINE', 'MAINTENANCE', 'RETIRED'] as const
type MachineStatus = (typeof machineStatuses)[number]
type MachinePatchFields = Partial<Pick<MachineResource, 'display_name' | 'manufacturer' | 'model' | 'status' | 'is_archived'>>

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối.'
}

function machineStatusLabel(status: string): string {
  const labels: Record<MachineStatus, string> = {
    ACTIVE: 'Đang sử dụng',
    OFFLINE: 'Ngoại tuyến',
    MAINTENANCE: 'Đang bảo trì',
    RETIRED: 'Ngừng sử dụng'
  }
  return labels[status as MachineStatus] ?? status
}

function lifecycleLabel(archived: boolean): string {
  return archived ? 'Đã lưu trữ' : 'Đang sử dụng'
}

function invitationStatusLabel(status: string): string {
  const labels: Record<string, string> = {
    PENDING: 'Đang chờ',
    ACCEPTED: 'Đã tham gia',
    REVOKED: 'Đã thu hồi',
    EXPIRED: 'Đã hết hạn'
  }
  return labels[status] ?? status
}

function MachineRow({
  machine,
  onToggleArchive,
  onSave
}: {
  machine: MachineResource
  onToggleArchive: (machine: MachineResource) => void
  onSave: (machine: MachineResource, body: MachinePatchFields) => void
}) {
  const [displayName, setDisplayName] = useState(machine.display_name)
  const [status, setStatus] = useState(machine.status)
  const dirty = !machine.is_archived && (displayName !== machine.display_name || status !== machine.status)

  return (
    <tr>
      <td><input disabled={machine.is_archived} aria-label={`Tên máy ${machine.display_name}`} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></td>
      <td>{machine.manufacturer ?? '—'} {machine.model ?? ''}</td>
      <td><select disabled={machine.is_archived} aria-label={`Trạng thái máy ${machine.display_name}`} value={status} onChange={(event) => setStatus(event.target.value)}>{machineStatuses.map((item) => <option key={item} value={item}>{machineStatusLabel(item)}</option>)}</select></td>
      <td className="table-actions">
        <button disabled={!dirty} onClick={() => onSave(machine, { display_name: displayName, status })}>Lưu</button>
        <button className="button-secondary" onClick={() => onToggleArchive(machine)}>{machine.is_archived ? 'Khôi phục' : 'Lưu trữ'}</button>
      </td>
    </tr>
  )
}

export function OrganizationManagementPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const accessToken = session?.access_token
  const bootstrap = useQuery({
    queryKey: ['session', accessToken],
    queryFn: () => apiClient.bootstrap(accessToken!),
    enabled: Boolean(accessToken),
    retry: false
  })
  const organizationId = bootstrap.data?.organization.id
  const organization = useQuery({
    queryKey: ['organization', organizationId, accessToken],
    queryFn: () => apiClient.organization(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const sites = useQuery({
    queryKey: ['sites', organizationId, accessToken, true],
    queryFn: () => apiClient.sites(accessToken!, organizationId!, true),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const [selectedSiteId, setSelectedSiteId] = useState<string>()
  const selectedSite = useMemo(() => sites.data?.items.find((site) => site.id === selectedSiteId) ?? sites.data?.items[0], [selectedSiteId, sites.data])
  const machines = useQuery({
    queryKey: ['machines', organizationId, selectedSite?.id, accessToken, true],
    queryFn: () => apiClient.machines(accessToken!, organizationId!, selectedSite!.id, true),
    enabled: Boolean(accessToken && organizationId && selectedSite),
    retry: false
  })
  const members = useQuery({
    queryKey: ['organization-members', organizationId, accessToken],
    queryFn: () => apiClient.organizationMembers(accessToken!, organizationId!, true),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const invitations = useQuery({
    queryKey: ['organization-invitations', organizationId, accessToken],
    queryFn: () => apiClient.organizationInvitations(accessToken!, organizationId!, true),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const [organizationName, setOrganizationName] = useState<string>()
  const [newSiteName, setNewSiteName] = useState('')
  const [newMachineId, setNewMachineId] = useState('')
  const [newMachineName, setNewMachineName] = useState('')
  const [inviteEmail, setInviteEmail] = useState('')
  const [createdInvitationToken, setCreatedInvitationToken] = useState<string>()
  const [message, setMessage] = useState<string>()

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ['organization', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['sites', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['machines', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['organization-members', organizationId] })
    void queryClient.invalidateQueries({ queryKey: ['organization-invitations', organizationId] })
  }
  const mutation = useMutation({
    mutationFn: (action: () => Promise<unknown>) => action(),
    onSuccess: (result) => {
      if (typeof result === 'object' && result !== null && 'token' in result && typeof result.token === 'string') setCreatedInvitationToken(result.token)
      setMessage('Đã lưu thay đổi.')
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || organization.isPending || sites.isPending) return <main className="auth-state">Đang tải thông tin đơn vị…</main>
  const failure = bootstrap.error ?? organization.error ?? sites.error
  if (failure || !organizationId || !organization.data || !sites.data) return <div className="page"><section className="alert alert--error"><h1>Không thể mở phần quản lý</h1><p>{errorMessage(failure)}</p><button onClick={() => { void bootstrap.refetch(); void organization.refetch(); void sites.refetch() }}>Thử lại</button></section></div>

  const submitOrganization = () => {
    const name = (organizationName ?? organization.data.name).trim()
    if (!name) return setMessage('Tên đơn vị không được để trống.')
    mutation.mutate(() => apiClient.updateOrganization(accessToken!, organizationId, { name, expected_revision: organization.data.revision }))
  }
  const submitSite = () => {
    const name = newSiteName.trim()
    if (!name) return setMessage('Tên cơ sở không được để trống.')
    mutation.mutate(() => apiClient.createSite(accessToken!, organizationId, name))
    setNewSiteName('')
  }
  const submitMachine = () => {
    if (!selectedSite) return setMessage('Hãy chọn cơ sở trước khi thêm máy.')
    const stableMachineId = newMachineId.trim()
    const displayName = newMachineName.trim()
    if (!stableMachineId || !displayName) return setMessage('Tên viết tắt và tên hiển thị của máy không được để trống.')
    mutation.mutate(() => apiClient.createMachine(accessToken!, organizationId, selectedSite.id, { stable_machine_id: stableMachineId, display_name: displayName }))
    setNewMachineId('')
    setNewMachineName('')
  }
  const submitInvitation = () => {
    const email = inviteEmail.trim()
    if (!email || !email.includes('@')) return setMessage('Hãy nhập email hợp lệ của đồng nghiệp.')
    setCreatedInvitationToken(undefined)
    mutation.mutate(() => apiClient.createOrganizationInvitation(accessToken!, organizationId, email))
    setInviteEmail('')
  }

  return (
    <CompactPage eyebrow="ĐƠN VỊ VÀ THIẾT BỊ" title="Đơn vị và thiết bị" description="Quản lý đơn vị, cơ sở và máy xạ trị trong cùng một không gian. Mọi thành viên trong đơn vị dùng chung các thao tác nghiệp vụ." actions={<span className="status-badge">ĐANG KẾT NỐI</span>}>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
      <section className="panel management-panel organization-summary-panel">
        <div className="panel-heading"><div><p className="eyebrow">ĐƠN VỊ</p><h2>{organization.data.name}</h2></div><span className={organization.data.is_archived ? 'status-badge status-badge--warning' : 'status-badge'}>{lifecycleLabel(organization.data.is_archived)}</span></div>
        <div className="inline-form"><label>Tên đơn vị<input aria-label="Tên đơn vị" value={organizationName ?? organization.data.name} onChange={(event) => setOrganizationName(event.target.value)} /></label><button disabled={mutation.isPending} onClick={submitOrganization}>Lưu tên</button></div>
      </section>
      <div className="management-grid organization-primary-grid">
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">CƠ SỞ</p><h2>Cơ sở vận hành</h2></div><strong>{sites.data.total}</strong></div><div className="stack-form"><label>Thêm cơ sở<input placeholder="Ví dụ: Cơ sở trung tâm" value={newSiteName} onChange={(event) => setNewSiteName(event.target.value)} /></label><button disabled={mutation.isPending || organization.data.is_archived} onClick={submitSite}>Thêm cơ sở</button></div><div className="site-list" role="list">{sites.data.items.map((site) => <div className="site-item-row" key={site.id}><button className={site.id === selectedSite?.id ? 'site-item site-item--selected' : 'site-item'} onClick={() => setSelectedSiteId(site.id)}><span>{site.name}</span><small>{lifecycleLabel(site.is_archived)}</small></button><button className="button-secondary" disabled={mutation.isPending} onClick={() => mutation.mutate(() => apiClient.updateSite(accessToken!, organizationId, site.id, { is_archived: !site.is_archived, expected_revision: site.revision }))}>{site.is_archived ? 'Khôi phục' : 'Lưu trữ'}</button></div>)}</div></section>
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">MÁY XẠ TRỊ</p><h2>{selectedSite?.name ?? 'Chọn cơ sở'}</h2></div><strong>{machines.data?.total ?? '—'}</strong></div>{machines.isPending ? <p>Đang tải máy…</p> : machines.error ? <div className="alert alert--error"><p>{errorMessage(machines.error)}</p></div> : selectedSite && machines.data ? <><div className="stack-form"><label>Tên viết tắt của máy<input disabled={selectedSite.is_archived || organization.data.is_archived} placeholder="Ví dụ: LINAC-01" value={newMachineId} onChange={(event) => setNewMachineId(event.target.value)} /></label><label>Tên hiển thị<input disabled={selectedSite.is_archived || organization.data.is_archived} placeholder="Ví dụ: TrueBeam 01" value={newMachineName} onChange={(event) => setNewMachineName(event.target.value)} /></label><button disabled={mutation.isPending || selectedSite.is_archived || organization.data.is_archived} onClick={submitMachine}>Thêm máy</button>{selectedSite.is_archived && <p className="form-hint">Cơ sở đã lưu trữ; hãy khôi phục cơ sở trước khi tạo hoặc sửa máy.</p>}</div><div className="table-wrap"><table><thead><tr><th>Tên máy</th><th>Hãng / kiểu máy</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{machines.data.items.map((machine) => <MachineRow key={machine.id} machine={machine} onToggleArchive={(item) => mutation.mutate(() => apiClient.updateMachine(accessToken!, organizationId, selectedSite.id, item.id, { is_archived: !item.is_archived, expected_revision: item.revision }))} onSave={(item, body) => mutation.mutate(() => apiClient.updateMachine(accessToken!, organizationId, selectedSite.id, item.id, { ...body, expected_revision: item.revision }))} />)}</tbody></table></div></> : <p>Chưa có cơ sở để quản lý máy.</p>}</section>
      </div>
      <div className="management-grid organization-secondary-grid">
        <details className="panel compact-details"><summary><span><span className="eyebrow">THÀNH VIÊN</span><strong>Thành viên ngang quyền</strong></span><b>{members.data?.total ?? '—'}</b></summary><p className="muted">Mọi thành viên trong đơn vị dùng chung nghiệp vụ; trạng thái dưới đây chỉ mô tả việc tham gia.</p>{members.isPending ? <p>Đang tải thành viên…</p> : members.error ? <div className="alert alert--error"><p>{errorMessage(members.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Email</th><th>Tên hiển thị</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{members.data?.items.map((member) => <tr key={member.id}><td>{member.email ?? '—'}</td><td>{member.display_name ?? '—'}</td><td><span className={member.is_active ? 'status-badge' : 'status-badge status-badge--warning'}>{member.is_active ? 'Đang hoạt động' : 'Tạm ngưng'}</span></td><td><button className="button-secondary" disabled={mutation.isPending} onClick={() => mutation.mutate(() => apiClient.updateOrganizationMember(accessToken!, organizationId, member.id, !member.is_active))}>{member.is_active ? 'Tạm ngưng' : 'Kích hoạt'}</button></td></tr>)}</tbody></table></div>}</details>
        <details className="panel compact-details"><summary><span><span className="eyebrow">LỜI MỜI</span><strong>Mời đồng nghiệp</strong></span><b>{invitations.data?.total ?? '—'}</b></summary><p className="muted">Mã mời chỉ xuất hiện một lần sau khi tạo và gắn với email của người nhận.</p><div className="stack-form"><label>Email đồng nghiệp<input type="email" placeholder="bacsi@example.org" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} /></label><button disabled={mutation.isPending || organization.data.is_archived} onClick={submitInvitation}>Tạo lời mời</button></div>{createdInvitationToken && <div className="alert alert--success"><p>Mã mời — chỉ hiển thị trong phiên này:</p><code className="token-display">{createdInvitationToken}</code><p className="muted">Người nhận đăng nhập bằng đúng email rồi dùng mã mời để tham gia đơn vị.</p></div>}{invitations.isPending ? <p>Đang tải lời mời…</p> : invitations.error ? <div className="alert alert--error"><p>{errorMessage(invitations.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Email</th><th>Trạng thái</th><th>Hạn</th><th></th></tr></thead><tbody>{invitations.data?.items.map((invitation) => <tr key={invitation.id}><td>{invitation.invited_email}</td><td>{invitationStatusLabel(invitation.status)}</td><td>{new Date(invitation.expires_at).toLocaleDateString('vi-VN')}</td><td>{invitation.status === 'PENDING' && <button className="button-secondary" disabled={mutation.isPending} onClick={() => mutation.mutate(() => apiClient.revokeOrganizationInvitation(accessToken!, organizationId, invitation.id))}>Thu hồi</button>}</td></tr>)}</tbody></table></div>}</details>
      </div>
    </CompactPage>
  )
}
