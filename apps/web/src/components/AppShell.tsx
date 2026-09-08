import type { PropsWithChildren } from 'react'
import { Link, useLocation } from 'react-router-dom'

import { environment } from '../env'
import { routeRegistry } from '../routeRegistry'
import { useAuth } from '../auth/AuthProvider'

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
        <p className="sidebar__caption">Clinical QA &amp; calculation workspace</p>
        <nav>
          {routeRegistry.filter((route) => route.showInSidebar !== false).map((route) => {
            const isCurrent = location.pathname === route.path
            const isAvailable = route.available
            return isAvailable ? (
              <Link aria-current={isCurrent ? 'page' : undefined} className="nav-item" key={route.path} to={route.path}>
                <span>{route.label}</span><small>{route.module}</small>
              </Link>
            ) : (
              <span aria-disabled="true" className="nav-item nav-item--planned" key={route.path} title={`Sẽ được triển khai ở ${route.phase}`}>
                <span>{route.label}</span><small>{route.phase}</small>
              </span>
            )
          })}
        </nav>
        {session && <button className="sidebar__signout" onClick={() => void signOut()}>Đăng xuất</button>}
        <div className="sidebar__footer">Build {environment.VITE_APP_VERSION}</div>
      </aside>
      <main className="workspace">{children}</main>
    </div>
  )
}
