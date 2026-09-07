import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router-dom'

import { ApiClientError, apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

export function SessionErrorPage() {
  const { session, signOut } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [organizationName, setOrganizationName] = useState('')
  const [formError, setFormError] = useState<string | null>(null)

  const createOrganization = useMutation({
    mutationFn: () => {
      if (!session?.access_token) throw new Error('Phiên đăng nhập không còn hợp lệ.')
      return apiClient.createOrganization(session.access_token, organizationName.trim())
    },
    onSuccess: async () => {
      if (session?.access_token) {
        queryClient.removeQueries({ queryKey: ['session', session.access_token] })
      }
      navigate('/app', { replace: true })
    }
  })

  async function signOutAndReturn() {
    await signOut()
    navigate('/auth/login', { replace: true })
  }

  function submitOrganization(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const name = organizationName.trim()
    if (!name) {
      setFormError('Hãy nhập tên bệnh viện hoặc organization trước khi tiếp tục.')
      return
    }
    setFormError(null)
    createOrganization.mutate()
  }

  const creationError = createOrganization.error instanceof ApiClientError
    ? createOrganization.error.message
    : createOrganization.error instanceof Error ? createOrganization.error.message : null

  return <main className="auth-state"><section className="auth-card"><p className="eyebrow">SESSION ERROR</p><h1>Chưa có organization</h1><div className="alert alert--error" role="alert"><h2>Identity đã xác thực</h2><p>Tài khoản của anh/chị đã đăng nhập thành công nhưng chưa được gắn vào organization RT-CONNECT nào.</p></div><section className="onboarding-section"><h2>Tạo organization đầu tiên</h2><p className="auth-card__lead">Nếu đây là lần đầu thiết lập workspace, nhập tên bệnh viện hoặc đơn vị để tạo organization. Tài khoản hiện tại sẽ được gắn làm thành viên đầu tiên; mọi bác sĩ và kỹ sư trong cùng organization vẫn thao tác ngang hàng.</p><form className="stack-form" onSubmit={submitOrganization}><label htmlFor="organization-name">Tên bệnh viện / organization<input id="organization-name" value={organizationName} onChange={(event) => setOrganizationName(event.target.value)} placeholder="Ví dụ: Bệnh viện Ung Bướu Thành phố" maxLength={200} autoComplete="organization" /></label>{(formError || creationError) && <div className="alert alert--error" role="alert"><p>{formError ?? creationError}</p></div>}<button type="submit" disabled={createOrganization.isPending}>{createOrganization.isPending ? 'Đang tạo organization…' : 'Tạo organization và mở workspace'}</button></form></section><p className="auth-card__footnote">Nếu organization đã được tạo sẵn, hãy liên hệ người phụ trách để gắn membership cho tài khoản này.</p><button className="button-secondary" onClick={() => void signOutAndReturn()}>Đăng xuất và đăng nhập lại</button><Link className="text-link" to="/app/system/status">Trạng thái dịch vụ</Link></section></main>
}
