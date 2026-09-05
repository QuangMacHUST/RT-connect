import { Link } from 'react-router-dom'

export function NotFoundPage() {
  return <div className="page"><p className="eyebrow">ROUTE NOT AVAILABLE</p><h1>Trang này chưa sẵn sàng</h1><p>Route chưa có implementation trong phase hiện tại hoặc đường dẫn không tồn tại.</p><Link className="button-link" to="/app/system/status">Về trạng thái nền tảng</Link></div>
}
