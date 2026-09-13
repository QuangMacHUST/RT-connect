import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { beforeEach, expect, test, vi } from 'vitest'

import { ApiClientError, apiClient } from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import { OrganizationManagementPage } from './OrganizationManagementPage'

vi.mock('../api/client', () => ({
  ApiClientError: class ApiClientError extends Error {
    readonly code: string

    constructor(message = 'API error', code = 'API_ERROR') {
      super(message)
      this.code = code
    }
  },
  apiClient: {
    bootstrap: vi.fn(),
    organization: vi.fn(),
    sites: vi.fn(),
    machines: vi.fn(),
    organizationMembers: vi.fn(),
    organizationInvitations: vi.fn(),
    updateOrganization: vi.fn()
  }
}))

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
  vi.mocked(apiClient.bootstrap).mockResolvedValue({ organization: { id: 'org-id', name: 'Bệnh viện thử nghiệm' } } as never)
  vi.mocked(apiClient.organization).mockResolvedValue({ id: 'org-id', name: 'Bệnh viện thử nghiệm', is_archived: false, revision: 1 } as never)
  vi.mocked(apiClient.sites).mockResolvedValue({ items: [{ id: 'site-id', organization_id: 'org-id', name: 'Cơ sở trung tâm', is_archived: false, revision: 1 }], total: 1 } as never)
  vi.mocked(apiClient.machines).mockResolvedValue({ items: [{ id: 'machine-id', site_id: 'site-id', organization_id: 'org-id', stable_machine_id: 'LINAC-01', display_name: 'Máy xạ trị 01', manufacturer: 'Hãng thử nghiệm', model: 'Mẫu 1', status: 'ACTIVE', is_archived: false, revision: 1 }], total: 1 } as never)
  vi.mocked(apiClient.organizationMembers).mockResolvedValue({ items: [{ id: 'member-id', email: 'bacsi@example.org', display_name: 'Bác sĩ thử nghiệm', is_active: true }], total: 1 } as never)
  vi.mocked(apiClient.organizationInvitations).mockResolvedValue({ items: [], total: 0 } as never)
})

function renderPage() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={queryClient}><BrowserRouter><OrganizationManagementPage /></BrowserRouter></QueryClientProvider>)
}

test('hiển thị cơ cấu gọn bằng tiếng Việt và không đưa mã máy kỹ thuật vào bảng', async () => {
  renderPage()

  expect(await screen.findByRole('heading', { name: 'Đơn vị và thiết bị' })).toBeInTheDocument()
  expect(screen.getByText('Bệnh viện thử nghiệm')).toBeInTheDocument()
  expect(screen.getAllByText('Cơ sở trung tâm')).not.toHaveLength(0)
  expect(await screen.findByDisplayValue('Máy xạ trị 01')).toBeInTheDocument()
  expect(screen.getAllByText('Đang sử dụng')).not.toHaveLength(0)
  expect(screen.getByText('Mã máy được hệ thống tạo tự động.')).toBeInTheDocument()
  expect(screen.getByText('Thành viên ngang quyền')).toBeInTheDocument()
  expect(screen.getByText('Mời đồng nghiệp')).toBeInTheDocument()
  expect(screen.queryByText('LINAC-01')).not.toBeInTheDocument()
  expect(document.body).not.toHaveTextContent('MOD-')
  expect(document.body).not.toHaveTextContent('API THẬT')
})

test('dịch lỗi xung đột dữ liệu sang tiếng Việt', async () => {
  vi.mocked(apiClient.updateOrganization).mockRejectedValue(new ApiClientError('Revision conflict', 'REVISION_CONFLICT'))
  renderPage()

  await screen.findByRole('heading', { name: 'Đơn vị và thiết bị' })
  fireEvent.click(screen.getByRole('button', { name: 'Lưu tên' }))

  expect(await screen.findByText('Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại rồi thực hiện lại thao tác.')).toBeInTheDocument()
})
