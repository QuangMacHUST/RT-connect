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
  apiClient: {
    createOrganization: vi.fn(),
    pendingOrganizationInvitations: vi.fn(),
    acceptOrganizationInvitation: vi.fn(),
    acceptOrganizationInvitationById: vi.fn()
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
  vi.mocked(apiClient.pendingOrganizationInvitations).mockResolvedValue({ items: [], total: 0 })
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

  fireEvent.click(screen.getByRole('button', { name: 'Tạo đơn vị và mở nơi làm việc' }))

  expect(screen.getByText('Hãy nhập tên bệnh viện hoặc đơn vị trước khi tiếp tục.')).toBeInTheDocument()
  expect(apiClient.createOrganization).not.toHaveBeenCalled()
})

test('creates the first organization and navigates to the workspace', async () => {
  vi.mocked(apiClient.createOrganization).mockResolvedValue({
    id: '11111111-1111-4111-8111-111111111111',
    name: 'Bệnh viện thử nghiệm',
    is_archived: false,
    revision: 1
  })

  renderPage()
  fireEvent.change(screen.getByLabelText('Tên bệnh viện hoặc đơn vị'), { target: { value: '  Bệnh viện thử nghiệm  ' } })
  fireEvent.click(screen.getByRole('button', { name: 'Tạo đơn vị và mở nơi làm việc' }))

  await waitFor(() => expect(apiClient.createOrganization).toHaveBeenCalledWith('access-token', 'Bệnh viện thử nghiệm'))
  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/app'))
})

test('shows a pending invitation and accepts it without creating an organization', async () => {
  vi.mocked(apiClient.pendingOrganizationInvitations).mockResolvedValue({
    items: [{
      id: '22222222-2222-4222-8222-222222222222',
      organization_id: '33333333-3333-4333-8333-333333333333',
      organization_name: 'Bệnh viện được mời',
      expires_at: '2026-09-20T00:00:00Z'
    }],
    total: 1
  })
  vi.mocked(apiClient.acceptOrganizationInvitationById).mockResolvedValue({
    id: '44444444-4444-4444-8444-444444444444',
    organization_id: '33333333-3333-4333-8333-333333333333',
    email: 'invitee@example.com',
    display_name: null,
    is_active: true
  })

  renderPage()

  expect(await screen.findByText('Bệnh viện được mời')).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Tham gia' }))

  await waitFor(() => expect(apiClient.acceptOrganizationInvitationById).toHaveBeenCalledWith(
    'access-token',
    '22222222-2222-4222-8222-222222222222'
  ))
  expect(apiClient.createOrganization).not.toHaveBeenCalled()
  expect(screen.getByTestId('location')).toHaveTextContent('/app')
})

test('accepts a manually entered invitation code', async () => {
  vi.mocked(apiClient.acceptOrganizationInvitation).mockResolvedValue({
    id: '55555555-5555-4555-8555-555555555555',
    organization_id: '33333333-3333-4333-8333-333333333333',
    email: 'invitee@example.com',
    display_name: null,
    is_active: true
  })

  renderPage()
  fireEvent.change(screen.getByLabelText('Mã mời'), { target: { value: 'invitation-code-123456789012345' } })
  fireEvent.click(screen.getByRole('button', { name: 'Tham gia bằng mã mời' }))

  await waitFor(() => expect(apiClient.acceptOrganizationInvitation).toHaveBeenCalledWith(
    'access-token',
    'invitation-code-123456789012345'
  ))
  expect(screen.getByTestId('location')).toHaveTextContent('/app')
})

test('keeps the invitation code fallback when pending invitations cannot be loaded', async () => {
  vi.mocked(apiClient.pendingOrganizationInvitations).mockRejectedValue(new Error('network unavailable'))

  renderPage()

  expect(await screen.findByText('Chưa kiểm tra được lời mời đang chờ. Anh vẫn có thể nhập mã mời bên dưới.')).toBeInTheDocument()
  expect(screen.getByLabelText('Mã mời')).toBeInTheDocument()
  expect(screen.getByRole('button', { name: 'Tham gia bằng mã mời' })).toBeInTheDocument()
})

test('shows an invalid invitation code error and does not create an organization', async () => {
  vi.mocked(apiClient.acceptOrganizationInvitation).mockRejectedValue(
    new ApiClientError('Mã mời không hợp lệ hoặc đã hết hạn.', 'INVITATION_INVALID')
  )

  renderPage()
  fireEvent.change(screen.getByLabelText('Mã mời'), { target: { value: 'invalid-invitation-code-123456' } })
  fireEvent.click(screen.getByRole('button', { name: 'Tham gia bằng mã mời' }))

  expect(await screen.findByText('Mã mời không hợp lệ hoặc đã hết hạn.')).toBeInTheDocument()
  expect(screen.getByTestId('location')).toHaveTextContent('/auth/session-error')
  expect(apiClient.createOrganization).not.toHaveBeenCalled()
})

test('shows the API error and stays on onboarding when creation is rejected', async () => {
  vi.mocked(apiClient.createOrganization).mockRejectedValue(new ApiClientError('Đơn vị đã tồn tại.', 'ORGANIZATION_NAME_CONFLICT'))

  renderPage()
  fireEvent.change(screen.getByLabelText('Tên bệnh viện hoặc đơn vị'), { target: { value: 'Bệnh viện trùng' } })
  fireEvent.click(screen.getByRole('button', { name: 'Tạo đơn vị và mở nơi làm việc' }))

  expect(await screen.findByText('Đơn vị đã tồn tại.')).toBeInTheDocument()
  expect(screen.getByTestId('location')).toHaveTextContent('/auth/session-error')
})
