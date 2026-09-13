import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import { AppShell } from './AppShell'
import { useAuth } from '../auth/AuthProvider'

vi.mock('../auth/AuthProvider', () => ({ useAuth: vi.fn() }))

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

test('renders five compact primary navigation areas without technical module labels', () => {
  render(<MemoryRouter initialEntries={['/app']}><AppShell><p>Nội dung</p></AppShell></MemoryRouter>)

  const navigation = screen.getByRole('navigation', { name: 'Các mục chính' })
  expect(navigation).toHaveTextContent('Trang chủ')
  expect(navigation).toHaveTextContent('QA máy')
  expect(navigation).toHaveTextContent('Công cụ sinh học')
  expect(navigation).toHaveTextContent('Thư viện kiến thức')
  expect(navigation).toHaveTextContent('Đơn vị và thiết bị')
  expect(navigation).not.toHaveTextContent('MOD-')
  expect(screen.getByRole('link', { name: 'Trạng thái dịch vụ' })).toBeInTheDocument()
})
