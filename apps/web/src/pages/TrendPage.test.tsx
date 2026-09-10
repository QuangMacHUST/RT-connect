import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import { apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { TrendPage } from './TrendPage'

vi.mock('../api/client', () => ({
  ApiClientError: class ApiClientError extends Error {
    readonly code = 'API_ERROR'
    readonly details: Array<{ field?: string; message: string }> = []
  },
  apiClient: {
    bootstrap: vi.fn(),
    sites: vi.fn(),
    machines: vi.fn(),
    trend: vi.fn(),
    trendEvents: vi.fn(),
    trendBaselines: vi.fn(),
    rebuildTrend: vi.fn(),
    createTrendBaseline: vi.fn(),
    updateTrendBaseline: vi.fn(),
    createTrendEvent: vi.fn(),
    updateTrendEvent: vi.fn(),
    exportTrend: vi.fn()
  }
}))

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))

const organizationId = '8aea79cc-3029-48e3-8458-61d1fc00dc8a'
const machineId = '737a8999-4abd-4fd4-bded-daf186f0f5be'
const baselineId = '8000ff9b-7a02-4cec-850e-e27e4fe50cc4'
const eventId = 'd8230d1d-badd-4c0c-b044-dcc4434215a6'

const baseline = {
  id: baselineId, organization_id: organizationId, machine_id: machineId, metric_key: 'output_factor', unit: '%',
  name: 'Synthetic output baseline', version_number: 2, baseline_value: 100, tolerance: 2, action_level: 3,
  effective_from: '2026-09-01T00:00:00Z', effective_to: null, status: 'ACTIVE', source_type: 'MANUAL', source_id: null,
  context: {}, created_at: '2026-09-01T00:00:00Z', updated_at: '2026-09-01T00:00:00Z'
}

const event = {
  id: eventId, organization_id: organizationId, machine_id: machineId, machine_name: 'Synthetic QA Linac',
  event_type: 'MAINTENANCE', title: 'Synthetic maintenance', started_at: '2026-09-05T01:00:00Z', ended_at: null,
  notes: 'Smoke marker', revision_number: 3, status: 'ACTIVE', metadata: {}, created_at: '2026-09-05T01:00:00Z',
  updated_at: '2026-09-05T01:00:00Z'
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(useAuth).mockReturnValue({ session: { access_token: 'access-token' } as never, loading: false, configured: true } as never)
  vi.mocked(apiClient.bootstrap).mockResolvedValue({ subject: 'user-id', email: 'physicist@example.org', organization: { id: organizationId, name: 'Staging Synthetic Site' } } as never)
  vi.mocked(apiClient.sites).mockResolvedValue({ items: [{ id: 'site-id', organization_id: organizationId, name: 'Synthetic Site', is_archived: false }], total: 1, offset: 0, limit: 100, include_archived: false } as never)
  vi.mocked(apiClient.machines).mockResolvedValue({ items: [{ id: machineId, site_id: 'site-id', organization_id: organizationId, stable_machine_id: 'STAGING-LINAC-01', display_name: 'Synthetic QA Linac', manufacturer: 'Synthetic', model: null, status: 'ACTIVE', is_archived: false }], total: 1, offset: 0, limit: 100, include_archived: false } as never)
  vi.mocked(apiClient.trend).mockResolvedValue({ organization_id: organizationId, timezone: 'Asia/Ho_Chi_Minh', aggregate: 'raw', from_at: null, to_at: null, total_points: 0, series: [], maintenance_events: [event], baselines: [baseline], warnings: [] } as never)
  vi.mocked(apiClient.trendBaselines).mockResolvedValue([baseline] as never)
  vi.mocked(apiClient.trendEvents).mockResolvedValue([event] as never)
  vi.mocked(apiClient.updateTrendBaseline).mockResolvedValue({ ...baseline, name: 'Edited baseline' } as never)
  vi.mocked(apiClient.updateTrendEvent).mockResolvedValue({ ...event, title: 'Edited maintenance' } as never)
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><MemoryRouter><TrendPage /></MemoryRouter></QueryClientProvider>)
}

test('saves a baseline revision with the observed version', async () => {
  renderPage()

  const editButtons = await screen.findAllByRole('button', { name: 'Sửa' })
  fireEvent.click(editButtons[0])
  const name = screen.getByLabelText('Tên baseline')
  fireEvent.change(name, { target: { value: 'Edited baseline' } })
  fireEvent.click(screen.getByRole('button', { name: 'Lưu baseline revision' }))

  await waitFor(() => expect(apiClient.updateTrendBaseline).toHaveBeenCalledWith(
    'access-token', baselineId, expect.objectContaining({ expected_version: 2, name: 'Edited baseline' })
  ))
})

test('archives a maintenance marker with its current revision', async () => {
  renderPage()

  const archiveButtons = await screen.findAllByRole('button', { name: 'Archive' })
  fireEvent.click(archiveButtons[1])

  await waitFor(() => expect(apiClient.updateTrendEvent).toHaveBeenCalledWith(
    'access-token', eventId, { expected_revision: 3, status: 'ARCHIVED' }
  ))
})
