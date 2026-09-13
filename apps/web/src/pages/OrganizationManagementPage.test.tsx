import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen } from '@testing-library/react'
import { BrowserRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test, vi } from 'vitest'

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
    updateOrganization: vi.fn(),
    updateSite: vi.fn(),
    updateMachine: vi.fn(),
    createSite: vi.fn(),
    createMachine: vi.fn(),
    createOrganizationInvitation: vi.fn()
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

afterEach(() => vi.restoreAllMocks())

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

test('giữ nội dung biểu mẫu khi tạo cơ sở thất bại', async () => {
  vi.mocked(apiClient.createSite).mockRejectedValue(new ApiClientError('Duplicate site', 'SITE_NAME_CONFLICT'))
  renderPage()

  await screen.findByRole('heading', { name: 'Đơn vị và thiết bị' })
  const siteInput = screen.getByPlaceholderText('Ví dụ: Cơ sở trung tâm')
  fireEvent.change(siteInput, { target: { value: 'Cơ sở mới' } })
  fireEvent.click(screen.getByRole('button', { name: 'Thêm cơ sở' }))

  expect(await screen.findByText('Tên cơ sở đã được sử dụng trong đơn vị này.')).toBeInTheDocument()
  expect(screen.getByDisplayValue('Cơ sở mới')).toBeInTheDocument()
})

test('yêu cầu xác nhận trước khi lưu trữ cơ sở', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  renderPage()

  await screen.findByRole('heading', { name: 'Đơn vị và thiết bị' })
  fireEvent.click(screen.getByRole('button', { name: 'Lưu trữ' }))

  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('Dữ liệu và lịch sử liên quan vẫn được giữ lại'))
  expect(apiClient.updateSite).not.toHaveBeenCalled()
})

test('hủy xác nhận lưu trữ máy thì không thay đổi dữ liệu', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  renderPage()

  await screen.findByRole('heading', { name: 'Đơn vị và thiết bị' })
  await screen.findByDisplayValue('Máy xạ trị 01')
  const archiveButtons = screen.getAllByRole('button', { name: 'Lưu trữ' })
  fireEvent.click(archiveButtons[1])

  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('máy Máy xạ trị 01'))
  expect(apiClient.updateMachine).not.toHaveBeenCalled()
})
