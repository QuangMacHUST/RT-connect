import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import { apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { DVHPage } from './DVHPage'

vi.mock('../api/client', () => ({
  ApiClientError: class ApiClientError extends Error {
    readonly code = 'API_ERROR'
  },
  apiClient: {
    bootstrap: vi.fn(),
    qaCases: vi.fn(),
    dvhInputs: vi.fn(),
    dvhCtPreview: vi.fn(),
    dvhRuns: vi.fn(),
    validateDvh: vi.fn(),
    createDvhRun: vi.fn(),
    downloadDvh: vi.fn()
  }
}))

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))

const caseId = '8bc86303-c7e9-4e1a-b012-cfbe2a07ba24'
const organizationId = '8aea79cc-3029-48e3-8458-61d1fc00dc8a'
const structureId = '6d2ded42-a892-4686-8d76-394819b2f59f'

const inputManifest = {
  case_id: caseId,
  dose_artifacts: [{
    id: '737a8999-4abd-4fd4-bded-daf186f0f5be', artifact_type: 'DICOM', modality: 'RTDOSE',
    original_filename: 'gamma-rtdose-v1-smoke.dcm', sha256: 'a'.repeat(64), byte_size: 898,
    data_status: 'VALID', frame_of_reference_uid: '1.2.3.4', metadata: {}
  }],
  structure_artifacts: [{
    id: structureId, artifact_type: 'DICOM', modality: 'RTSTRUCT',
    original_filename: 'p17-rtstruct-v1-smoke.dcm', sha256: 'b'.repeat(64), byte_size: 866,
    data_status: 'VALID', frame_of_reference_uid: '1.2.3.4', metadata: {}
  }],
  ct_artifacts: [],
  rois: []
}

const selectedStructureInputs = {
  ...inputManifest,
  rois: [{ roi_number: 1, name: 'P17_TARGET', contour_count: 1 }]
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useAuth).mockReturnValue({
    session: { access_token: 'access-token' } as never,
    loading: false,
    configured: true,
    signInWithPassword: vi.fn(),
    sendMagicLink: vi.fn(),
    signOut: vi.fn().mockResolvedValue(undefined)
  })
  vi.mocked(apiClient.bootstrap).mockResolvedValue({
    subject: 'user-id', email: 'physicist@example.org', organization: { id: organizationId, name: 'Staging Synthetic Site' }
  })
  vi.mocked(apiClient.qaCases).mockResolvedValue({
    items: [{
      id: caseId, organization_id: organizationId, site_id: 'site-id', machine_id: 'machine-id',
      primary_folder_id: 'folder-id', qa_type: 'DICOM', qa_cycle: 'CUSTOM', performed_at: '2026-09-09T00:00:00Z',
      scheduled_at: null, title: 'P17 staging smoke', description: null, protocol_version_id: null,
      status_note: null, case_status: 'DRAFT', is_archived: false
    }],
    total: 1, offset: 0, limit: 100, include_archived: false
  })
  vi.mocked(apiClient.dvhInputs)
    .mockResolvedValueOnce(inputManifest)
    .mockResolvedValueOnce(selectedStructureInputs)
  vi.mocked(apiClient.dvhRuns).mockResolvedValue({ items: [], total: 0 })
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/app/qa/cases/${caseId}/dvh`]}>
        <Routes><Route path="/app/qa/cases/:caseId/dvh" element={<DVHPage />} /></Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
}

test('automatically loads the first valid RTSTRUCT ROI after the manifest request', async () => {
  renderPage()

  expect(await screen.findByRole('option', { name: '#1 · P17_TARGET · 1 contour' })).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Validate & preview' })).toBeEnabled()
  expect(vi.mocked(apiClient.dvhInputs).mock.calls).toHaveLength(2)
  expect(vi.mocked(apiClient.dvhInputs).mock.calls[1]?.[3]).toBe(structureId)
})
