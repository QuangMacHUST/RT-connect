import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import { ApiClientError, apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { SessionErrorPage } from './SessionErrorPage'

vi.mock('../api/client', () => ({
  ApiClientError: class ApiClientError extends Error {
    readonly code: string
    readonly correlationId: string | undefined

    constructor(message: string, code = 'API_ERROR', correlationId?: string) {
      super(message)
      this.name = 'ApiClientError'
      this.code = code
      this.correlationId = correlationId
    }
  },
  apiClient: { createOrganization: vi.fn() }
}))

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))

function LocationProbe() {
  return <output data-testid="location">{useLocation().pathname}</output>
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/auth/session-error']}>
        <Routes>
          <Route path="*" element={<><SessionErrorPage /><LocationProbe /></>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  )
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
})

test('requires a non-empty organization name before creating anything', () => {
  renderPage()

  fireEvent.click(screen.getByRole('button', { name: 'Tạo organization và mở workspace' }))

  expect(screen.getByText('Hãy nhập tên bệnh viện hoặc organization trước khi tiếp tục.')).toBeInTheDocument()
  expect(apiClient.createOrganization).not.toHaveBeenCalled()
})

test('creates the first organization and navigates to the workspace', async () => {
  vi.mocked(apiClient.createOrganization).mockResolvedValue({
    id: '11111111-1111-4111-8111-111111111111',
    name: 'Bệnh viện thử nghiệm',
    is_archived: false
  })

  renderPage()
  fireEvent.change(screen.getByLabelText('Tên bệnh viện / organization'), { target: { value: '  Bệnh viện thử nghiệm  ' } })
  fireEvent.click(screen.getByRole('button', { name: 'Tạo organization và mở workspace' }))

  await waitFor(() => expect(apiClient.createOrganization).toHaveBeenCalledWith('access-token', 'Bệnh viện thử nghiệm'))
  expect(screen.getByTestId('location')).toHaveTextContent('/app')
})

test('shows the API error and stays on onboarding when creation is rejected', async () => {
  vi.mocked(apiClient.createOrganization).mockRejectedValue(new ApiClientError('Organization đã tồn tại.', 'ORGANIZATION_NAME_CONFLICT'))

  renderPage()
  fireEvent.change(screen.getByLabelText('Tên bệnh viện / organization'), { target: { value: 'Bệnh viện trùng' } })
  fireEvent.click(screen.getByRole('button', { name: 'Tạo organization và mở workspace' }))

  expect(await screen.findByText('Organization đã tồn tại.')).toBeInTheDocument()
  expect(screen.getByTestId('location')).toHaveTextContent('/auth/session-error')
})
