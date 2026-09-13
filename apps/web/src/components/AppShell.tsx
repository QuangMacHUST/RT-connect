import type { PropsWithChildren } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { routeRegistry } from '../routeRegistry'
import { useAuth } from '../auth/AuthProvider'

const primaryNavigation = ['/app', '/app/qa', '/app/biological', '/app/knowledge', '/app/organization']

export function AppShell({ children }: PropsWithChildren) {
  const location = useLocation()
  const { session, signOut } = useAuth()
  return (
    <div className="app-shell">
      <aside aria-label="Điều hướng chính" className="sidebar">
        <div className="product-mark">
          <span aria-hidden="true" className="product-mark__glyph">◉</span>
          <span>RT-CONNECT</span>
        </div>
        <p className="sidebar__caption">Không gian làm việc QA xạ trị</p>
        <nav aria-label="Các mục chính">
          {routeRegistry.filter((route) => route.showInSidebar !== false && primaryNavigation.includes(route.path)).map((route) => {
            const isCurrent = route.path === '/app'
              ? location.pathname === route.path
              : location.pathname === route.path || location.pathname.startsWith(`${route.path}/`)
            return route.available ? (
              <Link aria-current={isCurrent ? 'page' : undefined} className="nav-item" key={route.path} to={route.path}>
                <span>{route.label}</span>
              </Link>
            ) : (
              <span aria-disabled="true" className="nav-item nav-item--planned" key={route.path} title={`Sẽ được triển khai ở ${route.phase}`}>
                <span>{route.label}</span>
              </span>
            )
          })}
        </nav>
        <div className="sidebar__tools">
          <Link className="nav-item nav-item--utility" to="/app/system/status">Trạng thái dịch vụ</Link>
          {session && <button className="sidebar__signout" onClick={() => void signOut()}>Đăng xuất</button>}
        </div>
        <div className="sidebar__footer">Không gian lâm sàng RT-CONNECT</div>
      </aside>
      <main className="workspace">{children}</main>
    </div>
  )
}
