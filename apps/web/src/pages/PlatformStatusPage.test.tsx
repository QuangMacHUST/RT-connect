import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import { apiClient } from '../api/client'
import { AuthProvider } from '../auth/AuthProvider'
import { PlatformStatusPage } from './PlatformStatusPage'

vi.mock('../api/client', () => ({
  apiClient: { health: vi.fn(), ready: vi.fn(), version: vi.fn(), gammaQueueMetrics: vi.fn() }
}))

beforeEach(() => {
  vi.clearAllMocks()
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><BrowserRouter><AuthProvider><PlatformStatusPage /></AuthProvider></BrowserRouter></QueryClientProvider>)
}

test('renders an API-backed platform health state', async () => {
  vi.mocked(apiClient.health).mockResolvedValue({ status: 'ok', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'test-id' })
  vi.mocked(apiClient.ready).mockResolvedValue({ status: 'ready', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'ready-id', schema_revision: 'test-schema' })
  vi.mocked(apiClient.version).mockResolvedValue({ application: 'rt-connect-api', version: '0.1.0', environment: 'test', engine_version: 'not-yet', renderer_version: 'not-yet', schema_revision: 'test-schema' })

  renderPage()

  expect(await screen.findByText('BÌNH THƯỜNG')).toBeInTheDocument()
  expect(screen.getAllByText('SẴN SÀNG')).toHaveLength(2)
  expect(screen.getByText(/Mức sẵn sàng và phiên bản phải phù hợp/)).toBeInTheDocument()
  expect(screen.getByText('ĐANG HOẠT ĐỘNG')).toBeInTheDocument()
  expect(screen.getByText(/Lần kiểm tra gần nhất:/)).toBeInTheDocument()
  expect(screen.getByText(/Không hiển thị dữ liệu bệnh nhân/)).toBeInTheDocument()
})

test('surfaces readiness failure instead of claiming the platform is ready', async () => {
  vi.mocked(apiClient.health).mockResolvedValue({ status: 'ok', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'test-id' })
  vi.mocked(apiClient.ready).mockRejectedValue(new Error('schema mismatch'))
  vi.mocked(apiClient.version).mockResolvedValue({ application: 'rt-connect-api', version: '0.1.0', environment: 'test', engine_version: 'not-yet', renderer_version: 'not-yet', schema_revision: 'test-schema' })

  renderPage()

  expect(await screen.findByText('Không thể đọc đầy đủ trạng thái dịch vụ', {}, { timeout: 5000 })).toBeInTheDocument()
  expect(screen.getByText('schema mismatch')).toBeInTheDocument()
  expect(screen.getByText('CẦN XEM XÉT')).toBeInTheDocument()
})

test('marks schema mismatch as needs review even when health is ok', async () => {
  vi.mocked(apiClient.health).mockResolvedValue({ status: 'ok', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'test-id' })
  vi.mocked(apiClient.ready).mockResolvedValue({ status: 'ready', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'ready-id', schema_revision: 'schema-a' })
  vi.mocked(apiClient.version).mockResolvedValue({ application: 'rt-connect-api', version: '0.1.0', environment: 'test', engine_version: 'not-yet', renderer_version: 'not-yet', schema_revision: 'schema-b' })

  renderPage()

  expect(await screen.findByText('CẦN XEM XÉT')).toBeInTheDocument()
  expect(screen.getByText('KHÔNG KHỚP')).toBeInTheDocument()
  expect(screen.getByText(/Mức sẵn sàng và phiên bản phải phù hợp/)).toBeInTheDocument()
})
