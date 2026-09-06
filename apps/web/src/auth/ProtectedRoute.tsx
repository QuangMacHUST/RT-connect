import { Navigate, useLocation } from 'react-router-dom'
import type { PropsWithChildren } from 'react'

import { useAuth } from './AuthProvider'

export function ProtectedRoute({ children }: PropsWithChildren) {
  const { configured, loading, session } = useAuth()
  const location = useLocation()
  if (!configured) {
    return <main className="auth-state"><h1>Chưa thể mở không gian làm việc</h1><p>Supabase Auth chưa được cấu hình cho môi trường này.</p></main>
  }
  if (loading) return <main className="auth-state" aria-live="polite">Đang phục hồi phiên đăng nhập…</main>
  if (!session) {
    const returnTo = `${location.pathname}${location.search}`
    return <Navigate replace to={`/auth/login?returnTo=${encodeURIComponent(returnTo)}`} />
  }
  return <>{children}</>
}
