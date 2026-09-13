import { useState, type FormEvent } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'

function safeReturnTo(value: string | null): string {
  return value?.startsWith('/app') || value?.startsWith('/invite') ? value : '/app'
}

export function LoginPage() {
  const { configured, signInWithPassword, sendMagicLink } = useAuth()
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const returnTo = safeReturnTo(searchParams.get('returnTo'))
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [sentMagicLink, setSentMagicLink] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setMessage(null)
    const error = await signInWithPassword(email, password)
    setBusy(false)
    if (error) setMessage(error)
    else navigate(returnTo, { replace: true })
  }

  async function requestMagicLink() {
    setBusy(true)
    setMessage(null)
    const error = await sendMagicLink(email)
    setBusy(false)
    if (error) setMessage(error)
    else setSentMagicLink(true)
  }

  return <div className="auth-layout">
    <section className="auth-brand" aria-label="Giới thiệu RT-CONNECT">
      <div className="product-mark"><span aria-hidden="true" className="product-mark__glyph">◉</span><span>RT-CONNECT</span></div>
      <div><p className="eyebrow auth-brand__eyebrow">KHÔNG GIAN QA XẠ TRỊ</p><h1>Không gian làm việc QA xạ trị</h1><p>Phân tích, báo cáo và tính toán được sắp xếp gọn trong một nơi làm việc thống nhất.</p></div>
      <ul><li>Kiểm tra QA máy và PSQA</li><li>Lịch sử và báo cáo</li><li>Công cụ sinh học độc lập</li></ul>
      <div className="auth-brand__footer"><span>Kết nối an toàn</span><small>Chỉ sử dụng dữ liệu đã được phép</small></div>
    </section>
    <main className="auth-panel">
      <form className="auth-card" onSubmit={submit}>
        <p className="eyebrow">ĐĂNG NHẬP</p><h2>Đăng nhập RT-CONNECT</h2><p className="auth-card__lead">Tài khoản được cấp bởi đơn vị. Không nhập thông tin bệnh nhân ở đây.</p>
        {!configured && <div className="alert alert--error" role="alert">Dịch vụ đăng nhập chưa được cấu hình cho môi trường này.</div>}
        {message && <div className="alert alert--error" role="alert">{message}</div>}
        {sentMagicLink && <div className="alert alert--success" role="status">Liên kết đăng nhập đã được gửi nếu địa chỉ email thuộc tổ chức.</div>}
        <label htmlFor="email">Email</label><input autoComplete="email" id="email" onChange={(event) => setEmail(event.target.value)} required type="email" value={email} />
        <label htmlFor="password">Mật khẩu</label><input autoComplete="current-password" id="password" minLength={8} onChange={(event) => setPassword(event.target.value)} required type="password" value={password} />
        <label className="checkbox-row"><input type="checkbox" />Giữ phiên đăng nhập trên thiết bị này</label>
        <button disabled={!configured || busy} type="submit">{busy ? 'Đang đăng nhập…' : 'Đăng nhập'}</button>
        <Link className="text-link" to="/auth/recovery">Quên mật khẩu?</Link>
        <div className="auth-divider"><span>hoặc</span></div>
        <button className="button-secondary" disabled={!configured || busy || !email} onClick={() => void requestMagicLink()} type="button">Gửi liên kết đăng nhập</button>
        <p className="auth-card__footnote">Phiên đăng nhập được bảo vệ và quản lý riêng cho từng đơn vị.</p>
        <footer><span>RT-CONNECT</span><Link to="/app/system/status">Trạng thái dịch vụ</Link></footer>
      </form>
    </main>
  </div>
}
