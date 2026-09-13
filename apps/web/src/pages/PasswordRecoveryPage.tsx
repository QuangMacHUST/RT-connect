import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'

export function PasswordRecoveryPage() {
  const { configured, sendMagicLink } = useAuth()
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setMessage(null)
    const error = await sendMagicLink(email)
    setBusy(false)
    setMessage(error ?? 'Nếu email thuộc tổ chức, liên kết khôi phục đã được gửi.')
  }
  return <main className="auth-state"><section className="auth-card"><p className="eyebrow">KHÔI PHỤC TRUY CẬP</p><h1>Khôi phục truy cập</h1><p>Nhập email của đơn vị để nhận liên kết an toàn.</p>{message && <div className="alert" role="status">{message}</div>}<form onSubmit={submit}><label htmlFor="recovery-email">Email</label><input id="recovery-email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} /><button disabled={!configured || busy} type="submit">{busy ? 'Đang gửi…' : 'Gửi liên kết khôi phục'}</button></form><Link className="text-link" to="/auth/login">Quay lại đăng nhập</Link></section></main>
}
