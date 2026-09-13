import { useEffect, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'

import { getSupabaseClient } from '../auth/supabase'

export function AuthCallbackPage() {
  const navigate = useNavigate()
  const supabase = getSupabaseClient()
  const [error, setError] = useState<string | null>(() => (
    supabase ? null : 'Dịch vụ đăng nhập chưa được cấu hình cho môi trường này.'
  ))

  useEffect(() => {
    if (!supabase) return
    void supabase.auth.exchangeCodeForSession(window.location.href).then(({ error: exchangeError }) => {
      if (exchangeError) setError(exchangeError.message)
      else navigate('/app', { replace: true })
    })
  }, [navigate, supabase])

  return <main className="auth-state" aria-live="polite"><h1>{error ? 'Không thể hoàn tất đăng nhập' : 'Đang hoàn tất đăng nhập…'}</h1><p>{error ?? 'Đang xác minh phiên đăng nhập và mở nơi làm việc.'}</p>{error && <Link className="button-link" to="/auth/login">Quay lại đăng nhập</Link>}</main>
}
