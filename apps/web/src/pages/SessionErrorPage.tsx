import { Link, useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthProvider'

export function SessionErrorPage() {
  const { signOut } = useAuth()
  const navigate = useNavigate()
  async function signOutAndReturn() {
    await signOut()
    navigate('/auth/login', { replace: true })
  }
  return <main className="auth-state"><section className="auth-card"><p className="eyebrow">SESSION ERROR</p><h1>Không thể mở organization</h1><div className="alert alert--error" role="alert"><h2>Yêu cầu quyền thành viên</h2><p>Identity đã xác thực nhưng chưa có membership RT-CONNECT đang hoạt động. Không có dữ liệu organization nào được hiển thị.</p></div><p className="auth-card__footnote">Nếu lỗi tiếp diễn, liên hệ đầu mối tổ chức và cung cấp mã định danh của request trong nhật ký hỗ trợ.</p><button onClick={() => navigate('/app', { replace: true })}>Thử lại</button><button className="button-secondary" onClick={() => void signOutAndReturn()}>Đăng xuất và đăng nhập lại</button><Link className="text-link" to="/app/system/status">Trạng thái dịch vụ</Link></section></main>
}
