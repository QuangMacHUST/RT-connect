import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { expect, test, vi } from 'vitest'

import { apiClient } from '../api/client'
import { PlatformStatusPage } from './PlatformStatusPage'

vi.mock('../api/client', () => ({
  apiClient: { health: vi.fn(), version: vi.fn() }
}))

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><BrowserRouter><PlatformStatusPage /></BrowserRouter></QueryClientProvider>)
}

test('renders an API-backed platform health state', async () => {
  vi.mocked(apiClient.health).mockResolvedValue({ status: 'ok', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'test-id' })
  vi.mocked(apiClient.version).mockResolvedValue({ application: 'rt-connect-api', version: '0.1.0', environment: 'test', engine_version: 'not-yet', renderer_version: 'not-yet' })

  renderPage()

  expect(await screen.findByText('OK')).toBeInTheDocument()
  expect(screen.getByText('0.1.0')).toBeInTheDocument()
  expect(screen.getByText(/Không có dữ liệu bệnh nhân/)).toBeInTheDocument()
})
