import { useEffect, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { ApiClientError, apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể nhận lời mời. Hãy thử lại sau khi kiểm tra kết nối.'
}

export function InvitationAcceptPage() {
  const { session, loading, configured } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const token = searchParams.get('token')?.trim() ?? ''
  const [state, setState] = useState<'idle' | 'success' | 'error'>('idle')
  const [message, setMessage] = useState<string>()
  const [organizationId, setOrganizationId] = useState<string>()

  useEffect(() => {
    if (loading || !session || !token || state !== 'idle') return
    void apiClient.acceptOrganizationInvitation(session.access_token, token).then((member) => {
      setOrganizationId(member.organization_id)
      setMessage('Bạn đã tham gia đơn vị. Có thể mở nơi làm việc ngay.')
      setState('success')
    }).catch((error: unknown) => {
      setMessage(errorMessage(error))
      setState('error')
    })
  }, [loading, session, state, token])

  if (!token) return <main className="auth-state"><h1>Lời mời không hợp lệ</h1><p>Đường dẫn không có mã mời.</p><Link className="text-link" to="/auth/login">Đăng nhập</Link></main>
  if (loading) return <main className="auth-state">Đang kiểm tra phiên đăng nhập…</main>
  if (!session) {
    const returnTo = `/invite?token=${encodeURIComponent(token)}`
    return <main className="auth-state"><h1>Nhận lời mời RT-CONNECT</h1><p>Hãy đăng nhập bằng đúng email đã nhận lời mời, sau đó hệ thống sẽ tự kiểm tra mã mời.</p>{!configured && <div className="alert alert--error">Dịch vụ đăng nhập chưa được cấu hình.</div>}<Link className="button-link" to={`/auth/login?returnTo=${encodeURIComponent(returnTo)}`}>Đăng nhập để tiếp tục</Link></main>
  }
  if (state === 'idle') return <main className="auth-state">Đang nhận lời mời…</main>
  return <main className="auth-state"><h1>{state === 'success' ? 'Đã tham gia đơn vị' : 'Không thể nhận lời mời'}</h1><div className={state === 'success' ? 'alert alert--success' : 'alert alert--error'} role="alert"><p>{message}</p></div>{state === 'success' && organizationId ? <button onClick={() => navigate('/app')}>Mở nơi làm việc</button> : <button onClick={() => { setState('idle'); setMessage(undefined) }}>Thử lại</button>}<Link className="text-link" to="/app/system/status">Trạng thái dịch vụ</Link></main>
}
