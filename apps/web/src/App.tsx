import { useLocation } from 'react-router-dom'

import { AppShell } from './components/AppShell'
import { ApplicationRoutes } from './routes'

export function App() {
  const location = useLocation()
  if (location.pathname.startsWith('/auth/')) return <ApplicationRoutes />
  return <AppShell><ApplicationRoutes /></AppShell>
}
