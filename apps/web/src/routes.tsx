import { Navigate, Route, Routes } from 'react-router-dom'

import { ProtectedRoute } from './auth/ProtectedRoute'
import { AuthCallbackPage } from './pages/AuthCallbackPage'
import { BiologicalToolkitPage } from './pages/BiologicalToolkitPage'
import { KnowledgeLibraryPage } from './pages/KnowledgeLibraryPage'
import { BedEqd2Page } from './pages/BedEqd2Page'
import { PlanComparisonPage } from './pages/PlanComparisonPage'
import { ReIrradiationPage } from './pages/ReIrradiationPage'
import { HomeDashboardPage } from './pages/HomeDashboardPage'
import { GammaPage } from './pages/GammaPage'
import { DVHPage } from './pages/DVHPage'
import { LoginPage } from './pages/LoginPage'
import { MachineQAPage } from './pages/MachineQAPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OrganizationManagementPage } from './pages/OrganizationManagementPage'
import { QAArchivePage } from './pages/QAArchivePage'
import { ReportBuilderPage } from './pages/ReportBuilderPage'
import { TrendPage } from './pages/TrendPage'
import { PasswordRecoveryPage } from './pages/PasswordRecoveryPage'
import { PlatformStatusPage } from './pages/PlatformStatusPage'
import { QAProtocolPage } from './pages/QAProtocolPage'
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
      <Route path="/app/reports" element={<ProtectedRoute><ReportBuilderPage /></ProtectedRoute>} />
      <Route path="/app/trend" element={<ProtectedRoute><TrendPage /></ProtectedRoute>} />
      <Route path="/app/qa-protocols" element={<ProtectedRoute><QAProtocolPage /></ProtectedRoute>} />
      <Route path="/app/biological" element={<ProtectedRoute><BiologicalToolkitPage /></ProtectedRoute>} />
      <Route path="/app/biological/bed-eqd2" element={<ProtectedRoute><BedEqd2Page /></ProtectedRoute>} />
      <Route path="/app/biological/compare" element={<ProtectedRoute><PlanComparisonPage /></ProtectedRoute>} />
      <Route path="/app/biological/re-irradiation" element={<ProtectedRoute><ReIrradiationPage mode="REIRRADIATION" /></ProtectedRoute>} />
      <Route path="/app/biological/fraction-compensation" element={<ProtectedRoute><ReIrradiationPage mode="FRACTION_COMPENSATION" /></ProtectedRoute>} />
      <Route path="/app/biological/knowledge" element={<ProtectedRoute><KnowledgeLibraryPage /></ProtectedRoute>} />
      <Route path="/app/qa/cases/:caseId/machine-qa" element={<ProtectedRoute><MachineQAPage /></ProtectedRoute>} />
      <Route path="/app/qa/cases/:caseId/gamma" element={<ProtectedRoute><GammaPage /></ProtectedRoute>} />
      <Route path="/app/qa/cases/:caseId/dvh" element={<ProtectedRoute><DVHPage /></ProtectedRoute>} />
      <Route path="/app/system/status" element={<PlatformStatusPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
