import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from './auth/ProtectedRoute'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { HomeDashboardPage } from './pages/HomeDashboardPage'
import { LoginPage } from './pages/LoginPage'
import { MachineQAPage } from './pages/MachineQAPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OrganizationManagementPage } from './pages/OrganizationManagementPage'
import { QAArchivePage } from './pages/QAArchivePage'
import { PasswordRecoveryPage } from './pages/PasswordRecoveryPage'
import { PlatformStatusPage } from './pages/PlatformStatusPage'
import { SessionErrorPage } from './pages/SessionErrorPage'

export function ApplicationRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/app" replace />} />
      <Route path="/auth/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route path="/auth/recovery" element={<PasswordRecoveryPage />} />
      <Route path="/auth/session-error" element={<SessionErrorPage />} />
      <Route path="/app" element={<ProtectedRoute><HomeDashboardPage /></ProtectedRoute>} />
      <Route path="/app/organization" element={<ProtectedRoute><OrganizationManagementPage /></ProtectedRoute>} />
      <Route path="/app/qa" element={<ProtectedRoute><QAArchivePage /></ProtectedRoute>} />
      <Route path="/app/qa/cases/:caseId/machine-qa" element={<ProtectedRoute><MachineQAPage /></ProtectedRoute>} />
      <Route path="/app/system/status" element={<PlatformStatusPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
