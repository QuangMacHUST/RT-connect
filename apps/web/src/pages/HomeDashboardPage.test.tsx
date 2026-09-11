import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import { ApiClientError, apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { HomeDashboardPage } from './HomeDashboardPage'

vi.mock('../api/client', () => ({
  ApiClientError: class ApiClientError extends Error {
    readonly code: string

    constructor(message: string, code = 'API_ERROR') {
      super(message)
      this.name = 'ApiClientError'
      this.code = code
    }
  },
  apiClient: {
    bootstrap: vi.fn(),
    dashboard: vi.fn()
  }
}))

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))

function LocationProbe() {
  return <output data-testid="location">{useLocation().pathname}</output>
}

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/app']}>
        <Routes>
          <Route path="/app" element={<HomeDashboardPage />} />
          <Route path="/auth/session-error" element={<LocationProbe />} />
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

test('routes an identity without membership to organization onboarding', async () => {
  vi.mocked(apiClient.bootstrap).mockRejectedValue(
    new ApiClientError('No active organization membership.', 'ORGANIZATION_MEMBERSHIP_REQUIRED')
  )

  renderPage()

  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/auth/session-error'))
  expect(apiClient.dashboard).not.toHaveBeenCalled()
})
