import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { ApiClientError, apiClient, type MachineResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

const machineStatuses = ['ACTIVE', 'OFFLINE', 'MAINTENANCE', 'RETIRED'] as const

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function MachineRow({
  machine,
  onArchive,
  onSave
}: {
  machine: MachineResource
  onArchive: (machine: MachineResource) => void
  onSave: (machine: MachineResource, body: Parameters<typeof apiClient.updateMachine>[4]) => void
}) {
  const [displayName, setDisplayName] = useState(machine.display_name)
  const [status, setStatus] = useState(machine.status)
  const dirty = displayName !== machine.display_name || status !== machine.status

  return (
    <tr>
      <td><code>{machine.stable_machine_id}</code></td>
      <td><input aria-label={`Tên máy ${machine.stable_machine_id}`} value={displayName} onChange={(event) => setDisplayName(event.target.value)} /></td>
      <td>{machine.manufacturer ?? '—'} {machine.model ?? ''}</td>
      <td><select aria-label={`Trạng thái ${machine.stable_machine_id}`} value={status} onChange={(event) => setStatus(event.target.value)}>{machineStatuses.map((item) => <option key={item}>{item}</option>)}</select></td>
      <td className="table-actions">
        <button disabled={!dirty} onClick={() => onSave(machine, { display_name: displayName, status })}>Lưu</button>
        <button className="button-secondary" onClick={() => onArchive(machine)}>Archive</button>
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
    queryKey: ['sites', organizationId, accessToken],
    queryFn: () => apiClient.sites(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId),
    retry: false
  })
  const [selectedSiteId, setSelectedSiteId] = useState<string>()
  const selectedSite = useMemo(() => sites.data?.items.find((site) => site.id === selectedSiteId) ?? sites.data?.items[0], [selectedSiteId, sites.data])
  const machines = useQuery({
    queryKey: ['machines', organizationId, selectedSite?.id, accessToken],
    queryFn: () => apiClient.machines(accessToken!, organizationId!, selectedSite!.id),
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
      if (typeof result === 'object' && result !== null && 'token' in result && typeof result.token === 'string') {
        setCreatedInvitationToken(result.token)
      }
      setMessage('Đã lưu thay đổi.')
      refresh()
    },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || organization.isPending || sites.isPending) return <main className="auth-state">Đang tải organization, site và machine…</main>
  const failure = bootstrap.error ?? organization.error ?? sites.error
  if (failure || !organizationId || !organization.data || !sites.data) return <div className="page"><section className="alert alert--error"><h1>Không thể mở phần quản lý</h1><p>{errorMessage(failure)}</p><button onClick={() => { void bootstrap.refetch(); void organization.refetch(); void sites.refetch() }}>Thử lại</button></section></div>

  const submitOrganization = () => {
    const name = (organizationName ?? organization.data.name).trim()
    if (!name) return setMessage('Tên organization không được để trống.')
    mutation.mutate(() => apiClient.updateOrganization(accessToken!, organizationId, { name }))
  }
  const submitSite = () => {
    const name = newSiteName.trim()
    if (!name) return setMessage('Tên site không được để trống.')
    mutation.mutate(() => apiClient.createSite(accessToken!, organizationId, name))
    setNewSiteName('')
  }
  const submitMachine = () => {
    if (!selectedSite) return setMessage('Hãy chọn site trước khi thêm máy.')
    const stableMachineId = newMachineId.trim()
    const displayName = newMachineName.trim()
    if (!stableMachineId || !displayName) return setMessage('Mã máy và tên hiển thị không được để trống.')
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
    <div className="page">
      <header className="page-header"><div><p className="eyebrow">P4 · MOD-02</p><h1>Organization, Site &amp; Machine</h1><p>Quản lý cấu trúc vận hành dùng chung của RT-CONNECT. Mọi thành viên trong cùng organization thao tác ngang nhau; hệ thống chỉ giữ phạm vi dữ liệu theo organization.</p></div><span className="status-badge">API THẬT</span></header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
      <section className="panel management-panel"><div className="panel-heading"><div><p className="eyebrow">ORGANIZATION</p><h2>{organization.data.name}</h2></div><span className={organization.data.is_archived ? 'status-badge status-badge--warning' : 'status-badge'}>{organization.data.is_archived ? 'ARCHIVED' : 'ACTIVE'}</span></div><div className="inline-form"><label>Tên organization<input value={organizationName ?? organization.data.name} onChange={(event) => setOrganizationName(event.target.value)} /></label><button disabled={mutation.isPending} onClick={submitOrganization}>Lưu tên</button></div></section>
      <div className="management-grid">
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">SITES</p><h2>Cơ sở vận hành</h2></div><strong>{sites.data.total}</strong></div><div className="stack-form"><label>Thêm site<input placeholder="Ví dụ: Cơ sở trung tâm" value={newSiteName} onChange={(event) => setNewSiteName(event.target.value)} /></label><button disabled={mutation.isPending} onClick={submitSite}>Thêm site</button></div><div className="site-list" role="list">{sites.data.items.map((site) => <button className={site.id === selectedSite?.id ? 'site-item site-item--selected' : 'site-item'} key={site.id} onClick={() => setSelectedSiteId(site.id)}><span>{site.name}</span><small>{site.is_archived ? 'ARCHIVED' : 'ACTIVE'}</small></button>)}</div></section>
        <section className="panel"><div className="panel-heading"><div><p className="eyebrow">MACHINES</p><h2>{selectedSite?.name ?? 'Chọn site'}</h2></div><strong>{machines.data?.total ?? '—'}</strong></div>{machines.isPending ? <p>Đang tải machine…</p> : machines.error ? <div className="alert alert--error"><p>{errorMessage(machines.error)}</p></div> : selectedSite && machines.data ? <><div className="stack-form"><label>Mã máy ổn định<input placeholder="Ví dụ: LINAC-01" value={newMachineId} onChange={(event) => setNewMachineId(event.target.value)} /></label><label>Tên hiển thị<input placeholder="Ví dụ: TrueBeam 01" value={newMachineName} onChange={(event) => setNewMachineName(event.target.value)} /></label><button disabled={mutation.isPending} onClick={submitMachine}>Thêm máy</button></div><div className="table-wrap"><table><thead><tr><th>Mã ổn định</th><th>Tên hiển thị</th><th>Hãng / model</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{machines.data.items.map((machine) => <MachineRow key={machine.id} machine={machine} onArchive={(item) => mutation.mutate(() => apiClient.updateMachine(accessToken!, organizationId, selectedSite.id, item.id, { is_archived: true }))} onSave={(item, body) => mutation.mutate(() => apiClient.updateMachine(accessToken!, organizationId, selectedSite.id, item.id, body))} />)}</tbody></table></div></> : <p>Chưa có site để quản lý machine.</p>}</section>
      </div>
      <div className="management-grid">
        <section className="panel">
          <div className="panel-heading"><div><p className="eyebrow">MEMBERS</p><h2>Thành viên ngang quyền</h2></div><strong>{members.data?.total ?? '—'}</strong></div>
          <p className="muted">Mọi thành viên active dùng cùng nghiệp vụ. Trạng thái dưới đây chỉ là vòng đời membership, không phải phân quyền bác sĩ/kỹ sư.</p>
          {members.isPending ? <p>Đang tải thành viên…</p> : members.error ? <div className="alert alert--error"><p>{errorMessage(members.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Email</th><th>Tên hiển thị</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{members.data?.items.map((member) => <tr key={member.id}><td>{member.email ?? '—'}</td><td>{member.display_name ?? '—'}</td><td><span className={member.is_active ? 'status-badge' : 'status-badge status-badge--warning'}>{member.is_active ? 'ACTIVE' : 'INACTIVE'}</span></td><td><button className="button-secondary" disabled={mutation.isPending} onClick={() => mutation.mutate(() => apiClient.updateOrganizationMember(accessToken!, organizationId, member.id, !member.is_active))}>{member.is_active ? 'Tạm ngưng' : 'Kích hoạt'}</button></td></tr>)}</tbody></table></div>}
        </section>
        <section className="panel">
          <div className="panel-heading"><div><p className="eyebrow">INVITATION</p><h2>Mời đồng nghiệp</h2></div><strong>{invitations.data?.total ?? '—'}</strong></div>
          <p className="muted">Token chỉ xuất hiện một lần sau khi tạo. Hãy gửi link/token qua kênh nội bộ phù hợp; token gắn với email đã xác thực và hết hạn sau 7 ngày.</p>
          <div className="stack-form"><label>Email đồng nghiệp<input type="email" placeholder="bacsi@example.org" value={inviteEmail} onChange={(event) => setInviteEmail(event.target.value)} /></label><button disabled={mutation.isPending} onClick={submitInvitation}>Tạo lời mời</button></div>
          {createdInvitationToken && <div className="alert alert--success"><p>Token lời mời — chỉ hiển thị trong phiên này:</p><code className="token-display">{createdInvitationToken}</code><p className="muted">Người nhận đăng nhập bằng đúng email rồi dùng token ở luồng nhận lời mời.</p></div>}
          {invitations.isPending ? <p>Đang tải lời mời…</p> : invitations.error ? <div className="alert alert--error"><p>{errorMessage(invitations.error)}</p></div> : <div className="table-wrap"><table><thead><tr><th>Email</th><th>Trạng thái</th><th>Hạn</th><th></th></tr></thead><tbody>{invitations.data?.items.map((invitation) => <tr key={invitation.id}><td>{invitation.invited_email}</td><td>{invitation.status}</td><td>{new Date(invitation.expires_at).toLocaleDateString('vi-VN')}</td><td>{invitation.status === 'PENDING' && <button className="button-secondary" disabled={mutation.isPending} onClick={() => mutation.mutate(() => apiClient.revokeOrganizationInvitation(accessToken!, organizationId, invitation.id))}>Thu hồi</button>}</td></tr>)}</tbody></table></div>}
        </section>
      </div>
    </div>
  )
}
