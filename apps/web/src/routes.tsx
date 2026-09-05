import { Navigate, Route, Routes } from 'react-router-dom'

import { NotFoundPage } from './pages/NotFoundPage'
import { PlatformStatusPage } from './pages/PlatformStatusPage'

export function ApplicationRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app/system/status" replace />} />
      <Route path="/app/system/status" element={<PlatformStatusPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
