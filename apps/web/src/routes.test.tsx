import { render, screen } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { expect, test, vi } from 'vitest'

vi.mock('./auth/ProtectedRoute', () => ({ ProtectedRoute: ({ children }: { children: ReactNode }) => children }))
vi.mock('./pages/KnowledgeLibraryPage', () => ({ KnowledgeLibraryPage: () => <p>Đăng nhập để mở thư viện kiến thức.</p> }))

import { ApplicationRoutes } from './routes'

test('chuyển liên kết thư viện cũ về mục thư viện kiến thức mới', () => {
  render(<MemoryRouter initialEntries={['/app/biological/knowledge']}><ApplicationRoutes /></MemoryRouter>)

  expect(screen.getByText('Đăng nhập để mở thư viện kiến thức.')).toBeInTheDocument()
})
