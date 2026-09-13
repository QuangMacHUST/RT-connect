import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { ApiClientError, apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

export function SessionErrorPage() {
  const { session, signOut } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [organizationName, setOrganizationName] = useState('')
  const [formError, setFormError] = useState<string | null>(null)
  const [invitationToken, setInvitationToken] = useState('')
  const [invitationFormError, setInvitationFormError] = useState<string | null>(null)

  const pendingInvitations = useQuery({
    queryKey: ['pending-organization-invitations', session?.access_token],
    queryFn: () => apiClient.pendingOrganizationInvitations(session!.access_token),
    enabled: Boolean(session?.access_token),
    retry: false
  })

  function openWorkspace() {
    if (session?.access_token) {
      queryClient.removeQueries({ queryKey: ['session', session.access_token] })
    }
    navigate('/app', { replace: true })
  }

  const createOrganization = useMutation({
    mutationFn: () => {
      if (!session?.access_token) throw new Error('Phiên đăng nhập không còn hợp lệ.')
      return apiClient.createOrganization(session.access_token, organizationName.trim())
    },
    onSuccess: openWorkspace
  })

  const acceptPendingInvitation = useMutation({
    mutationFn: (invitationId: string) => {
      if (!session?.access_token) throw new Error('Phiên đăng nhập không còn hợp lệ.')
      return apiClient.acceptOrganizationInvitationById(session.access_token, invitationId)
    },
    onSuccess: openWorkspace
  })

  const acceptInvitationByCode = useMutation({
    mutationFn: () => {
      if (!session?.access_token) throw new Error('Phiên đăng nhập không còn hợp lệ.')
      return apiClient.acceptOrganizationInvitation(session.access_token, invitationToken.trim())
    },
    onSuccess: openWorkspace
  })

  async function signOutAndReturn() {
    await signOut()
    navigate('/auth/login', { replace: true })
  }

  function submitOrganization(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = organizationName.trim()
    if (!name) {
      setFormError('Hãy nhập tên bệnh viện hoặc đơn vị trước khi tiếp tục.')
      return
    }
    setFormError(null)
    createOrganization.mutate()
  }

  function submitInvitation(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const token = invitationToken.trim()
    if (!token) {
      setInvitationFormError('Hãy nhập mã mời trước khi tiếp tục.')
      return
    }
    setInvitationFormError(null)
    acceptInvitationByCode.mutate()
  }

  const creationError = createOrganization.error instanceof ApiClientError
    ? createOrganization.error.message
    : createOrganization.error instanceof Error ? createOrganization.error.message : null
  const invitationError = acceptInvitationByCode.error instanceof ApiClientError
    ? acceptInvitationByCode.error.message
    : acceptInvitationByCode.error instanceof Error ? acceptInvitationByCode.error.message
      : acceptPendingInvitation.error instanceof ApiClientError ? acceptPendingInvitation.error.message
        : acceptPendingInvitation.error instanceof Error ? acceptPendingInvitation.error.message : null
  const busy = createOrganization.isPending || acceptPendingInvitation.isPending || acceptInvitationByCode.isPending
  const pendingItems = pendingInvitations.data?.items ?? []

  return <main className="auth-state"><section className="auth-card"><p className="eyebrow">PHIÊN ĐĂNG NHẬP</p><h1>Chưa có đơn vị</h1><div className="alert alert--error" role="alert"><h2>Tài khoản đã xác thực</h2><p>Tài khoản đã đăng nhập thành công nhưng chưa được gắn vào đơn vị RT-CONNECT nào.</p></div><section className="onboarding-section onboarding-section--join"><h2>Tham gia đơn vị bằng lời mời</h2><p className="auth-card__lead">Nếu đồng nghiệp đã mời anh vào một đơn vị, lời mời đang chờ sẽ xuất hiện bên dưới. Chọn <strong>Tham gia</strong> để vào đúng nơi làm việc.</p>{pendingInvitations.isPending ? <p className="form-hint">Đang tìm lời mời gửi cho tài khoản này…</p> : pendingInvitations.error ? <div className="alert alert--error" role="alert"><p>Chưa kiểm tra được lời mời đang chờ. Anh vẫn có thể nhập mã mời bên dưới.</p></div> : pendingItems.length ? <div className="pending-invitation-list">{pendingItems.map((invitation) => <div className="pending-invitation" key={invitation.id}><div><strong>{invitation.organization_name}</strong><span>Hạn đến {new Date(invitation.expires_at).toLocaleDateString('vi-VN')}</span></div><button type="button" disabled={busy} onClick={() => acceptPendingInvitation.mutate(invitation.id)}>{acceptPendingInvitation.isPending ? 'Đang tham gia…' : 'Tham gia'}</button></div>)}</div> : <p className="form-hint">Hiện chưa tìm thấy lời mời đang chờ theo email này.</p>}<form className="stack-form" onSubmit={submitInvitation}><label htmlFor="invitation-token">Mã mời<input id="invitation-token" value={invitationToken} onChange={(event) => setInvitationToken(event.target.value)} placeholder="Dán mã mời do đồng nghiệp gửi" autoComplete="off" spellCheck={false} /></label>{(invitationFormError || invitationError) && <div className="alert alert--error" role="alert"><p>{invitationFormError ?? invitationError}</p></div>}<button type="submit" disabled={busy}>{acceptInvitationByCode.isPending ? 'Đang kiểm tra mã mời…' : 'Tham gia bằng mã mời'}</button></form></section><section className="onboarding-section"><h2>Tạo đơn vị mới</h2><p className="auth-card__lead">Chỉ chọn mục này nếu đơn vị của anh chưa tồn tại và anh là người thiết lập đơn vị đầu tiên. Mọi bác sĩ và kỹ sư trong cùng đơn vị sẽ thao tác ngang hàng.</p><form className="stack-form" onSubmit={submitOrganization}><label htmlFor="organization-name">Tên bệnh viện hoặc đơn vị<input id="organization-name" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} placeholder="Ví dụ: Bệnh viện Ung Bướu Thành phố" maxLength={200} autoComplete="organization" /></label>{(formError || creationError) && <div className="alert alert--error" role="alert"><p>{formError ?? creationError}</p></div>}<button type="submit" disabled={busy}>{createOrganization.isPending ? 'Đang tạo đơn vị…' : 'Tạo đơn vị và mở nơi làm việc'}</button></form></section><p className="auth-card__footnote">Nếu chưa thấy lời mời, hãy kiểm tra tài khoản đang đăng nhập có đúng email người nhận hay chưa hoặc nhờ đồng nghiệp tạo lại lời mời.</p><button className="button-secondary" onClick={() => void signOutAndReturn()}>Đăng xuất và đăng nhập lại</button><Link className="text-link" to="/app/system/status">Trạng thái dịch vụ</Link></section></main>
}
