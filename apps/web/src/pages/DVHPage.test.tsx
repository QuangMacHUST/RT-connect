import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
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
    biologicalLibrary: vi.fn(),
    qaProtocols: vi.fn(),
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
  vi.mocked(apiClient.biologicalLibrary).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100, include_archived: false })
  vi.mocked(apiClient.qaProtocols).mockResolvedValue({ items: [], total: 0, offset: 0, limit: 100, include_archived: false })
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
  expect(screen.getByText('Chưa chọn CT')).toBeInTheDocument()
  expect(vi.mocked(apiClient.dvhInputs).mock.calls).toHaveLength(2)
  expect(vi.mocked(apiClient.dvhInputs).mock.calls[1]?.[3]).toBe(structureId)
})

test('keeps the blob URL alive until a DVH export has started', async () => {
  vi.mocked(apiClient.dvhRuns).mockResolvedValue({
    items: [{
      id: '8000ff9b-7a02-4cec-850e-e27e4fe50cc4', organization_id: organizationId, qa_case_id: caseId,
      dose_artifact_id: '737a8999-4abd-4fd4-bded-daf186f0f5be', structure_artifact_id: structureId,
      ct_artifact_id: null, roi_number: 1, idempotency_key: 'dvh-export-test-001', engine_key: 'visual-dose.dvh',
      engine_version: 'p17-dvh-1.1.0', status: 'COMPLETED', input_snapshot: { request_fingerprint: 'input-fp' },
      result_snapshot: { result_sha256: 'result-sha' }, warning_snapshot: [], error_snapshot: [],
      created_by_user_identity_id: null, created_at: '2026-09-09T00:00:00Z', updated_at: '2026-09-09T00:00:00Z'
    }], total: 1
  })
  vi.mocked(apiClient.downloadDvh).mockResolvedValue(new Blob(['{}'], { type: 'application/json' }))
  const createObjectUrl = vi.spyOn(URL, 'createObjectURL').mockReturnValue('blob:test')
  const revokeObjectUrl = vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined)
  const anchorClick = vi.spyOn(HTMLAnchorElement.prototype, 'click').mockImplementation(() => undefined)

  renderPage()
  fireEvent.click(await screen.findByRole('button', { name: /^JSON$/ }))

  await waitFor(() => expect(vi.mocked(apiClient.downloadDvh)).toHaveBeenCalledWith(
    'access-token', organizationId, caseId, '8000ff9b-7a02-4cec-850e-e27e4fe50cc4', 'JSON'
  ))
  expect(createObjectUrl).toHaveBeenCalledOnce()
  expect(anchorClick).toHaveBeenCalledOnce()
  expect(revokeObjectUrl).not.toHaveBeenCalled()

  await new Promise((resolve) => setTimeout(resolve, 1050))
  expect(revokeObjectUrl).toHaveBeenCalledWith('blob:test')
  createObjectUrl.mockRestore()
  revokeObjectUrl.mockRestore()
  anchorClick.mockRestore()
})

test('sends only the explicitly selected P16 limit binding', async () => {
  vi.mocked(apiClient.biologicalLibrary).mockResolvedValue({
    items: [{
      id: 'limit-entry-id', organization_id: organizationId, entry_type: 'DOSE_LIMIT', entry_key: 'P17_TEST_DMAX', name: 'Synthetic Dmax limit', version_number: 1, status: 'PUBLISHED', revision: 1,
      description: null, effective_note: null, disease: 'Synthetic QA', disease_subtype: null, anatomy_site: 'Synthetic target', treatment_intent: null, technique: 'TEST', fractions: null,
      tissue_or_oar: 'Synthetic target', metric_key: 'DMAX', operator: 'MAX', limit_value: 10, lower_limit: null, upper_limit: null, unit: 'Gy', volume_cc: null, metric_parameter: null,
      alpha_beta_gy: null, model_key: null, model_version: null, applicability: {}, content: {}, source_type: 'USER_DEFINED', source_reference: null, reference_status: 'AVAILABLE', source_date: null,
      evidence_level: 'SYNTHETIC', citation: {}, content_sha256: 'c'.repeat(64), source_entry_id: null, created_by_user_identity_id: null, created_at: '2026-09-09T00:00:00Z', updated_at: '2026-09-09T00:00:00Z'
    }], total: 1, offset: 0, limit: 100, include_archived: false
  })
  vi.mocked(apiClient.validateDvh).mockResolvedValue({ valid: false, errors: [], warnings: [], normalized_input: null, preview: null })

  renderPage()
  expect(await screen.findByRole('option', { name: '#1 · P17_TARGET · 1 contour' })).toBeInTheDocument()
  fireEvent.change(screen.getByLabelText('Nguồn binding'), { target: { value: 'DOSE_LIMIT' } })
  const limitSelect = await screen.findByRole('combobox', { name: 'P16 DOSE_LIMIT' })
  const limitOption = await screen.findByRole('option', { name: /P17_TEST_DMAX · Synthetic Dmax limit/ })
  ;(limitSelect as HTMLSelectElement).value = 'limit-entry-id'
  ;(limitOption as HTMLOptionElement).selected = true
  fireEvent.change(limitSelect)
  await waitFor(() => expect(limitSelect).toHaveValue('limit-entry-id'))
  fireEvent.click(screen.getByRole('button', { name: 'Validate & preview' }))

  await waitFor(() => expect(vi.mocked(apiClient.validateDvh)).toHaveBeenCalledWith(
    'access-token', organizationId, caseId, expect.objectContaining({ limit_entry_id: 'limit-entry-id' })
  ))
})
