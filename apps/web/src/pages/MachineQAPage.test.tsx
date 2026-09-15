import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { expect, test, vi } from 'vitest'

import type { PylinacQARunResource } from '../api/client'
import { PylinacAdjustmentCanvas, PylinacResultPanel } from './MachineQAPage'
import { historyForCatalog } from './pylinacHistory'
import { mapImagePoint } from './pylinacCoordinates'
import { artifactsAreValidated, selectedArtifactsAreValidated } from './qaArtifactLabels'

const makeRun = (overrides: Partial<PylinacQARunResource> = {}): PylinacQARunResource => ({
  id: 'run-current',
  catalog_key: 'STARSHOT',
  name: 'Kiểm tra sao',
  family: 'Starshot',
  status: 'COMPLETED',
  assessment_status: null,
  engine_class: 'Starshot',
  engine_version: '3.47.0',
  package_fingerprint: 'package-fingerprint',
  parameters: { start_point: { x: 10, y: 20 } },
  input_files: [],
  result_snapshot: { metrics: { wobble_mm: 0.42, passed: true } },
  warning_snapshot: [],
  error_snapshot: [],
  overlay_artifact_id: null,
  started_at: '2026-09-15T10:00:00Z',
  completed_at: '2026-09-15T10:00:01Z',
  created_at: '2026-09-15T10:00:00Z',
  updated_at: '2026-09-15T10:00:01Z',
  ...overrides
})

const baseProps = (latest: PylinacQARunResource, history: PylinacQARunResource[]) => ({
  latest,
  history,
  accessToken: 'access-token',
  caseId: 'qa-case',
  emptyHistoryLabel: 'Chưa có kết quả kiểm tra sao.',
  metrics: [{ key: 'wobble', label: 'Độ lệch tâm', value: '0,42 mm' }],
  onMessage: vi.fn(),
  onAssess: vi.fn()
})

test('displays engine warnings without changing the user assessment', () => {
  const run = makeRun({ warning_snapshot: [{ code: 'PYLINAC_ENGINE_WARNING', message: 'Phantom cần được xem xét trước khi kết luận.' }] })

  render(<PylinacResultPanel {...baseProps(run, [run])} />)

  expect(screen.getByRole('heading', { name: 'Cảnh báo từ bộ tính' })).toBeInTheDocument()
  expect(screen.getByText('Phantom cần được xem xét trước khi kết luận.')).toBeInTheDocument()
  expect(screen.getByRole('combobox', { name: 'Đánh giá của người dùng' })).toHaveValue('NOT_ASSESSED')
  expect(screen.getByText('LỊCH SỬ PHÂN TÍCH')).toBeInTheDocument()
})

test('keeps the warning attached to the selected historical run', () => {
  const latest = makeRun()
  const previous = makeRun({
    id: 'run-previous',
    warning_snapshot: [{ code: 'PYLINAC_ENGINE_WARNING', message: 'Cảnh báo chỉ thuộc lượt cũ.' }],
    parameters: { start_point: { x: 8, y: 9 } },
    created_at: '2026-09-14T10:00:00Z',
    updated_at: '2026-09-14T10:00:01Z'
  })

  render(<PylinacResultPanel {...baseProps(latest, [latest, previous])} />)
  expect(screen.queryByText('Cảnh báo chỉ thuộc lượt cũ.')).not.toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: 'Mở' }))

  expect(screen.getByText('Cảnh báo chỉ thuộc lượt cũ.')).toBeInTheDocument()
  expect(screen.getByText('Đang xem một lượt cũ trong lịch sử. Kết quả gốc không thay đổi khi xem lại hoặc đánh giá.')).toBeInTheDocument()
})

test('shows parameters removed from the newer analysis in the history diff', () => {
  const latest = makeRun({ parameters: {} })
  const previous = makeRun({
    id: 'run-previous',
    parameters: { start_point: { x: 8, y: 9 } },
    created_at: '2026-09-14T10:00:00Z',
    updated_at: '2026-09-14T10:00:01Z'
  })

  render(<PylinacResultPanel {...baseProps(latest, [latest, previous])} />)

  expect(screen.getByText('Đã bỏ')).toBeInTheDocument()
})

test('does not show a loading state when no image is selected', () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

  render(
    <QueryClientProvider client={queryClient}>
      <PylinacAdjustmentCanvas accessToken="access-token" artifactId={undefined} x="" y="" onPointChange={vi.fn()} />
    </QueryClientProvider>,
  )

  expect(screen.getByText('Chọn ảnh để bật vùng điều chỉnh.')).toBeInTheDocument()
  expect(screen.queryByText('Đang tải ảnh xem trước…')).not.toBeInTheDocument()
})

test('maps pointer coordinates to the original image and clamps outside clicks', () => {
  const bounds = { left: 100, top: 50, width: 400, height: 200 }

  expect(mapImagePoint(300, 150, bounds, 2000, 1000)).toEqual({ x: '1000.0', y: '500.0' })
  expect(mapImagePoint(50, 20, bounds, 2000, 1000)).toEqual({ x: '0.0', y: '0.0' })
  expect(mapImagePoint(600, 300, bounds, 2000, 1000)).toEqual({ x: '2000.0', y: '1000.0' })
  expect(mapImagePoint(300, 150, bounds, 2000, 1000, 'NORMALIZED')).toEqual({ x: '0.5000', y: '0.5000' })
  expect(mapImagePoint(300, 150, { ...bounds, width: 0 }, 2000, 1000)).toBeUndefined()
})

test('keeps each QA page history isolated to its selected test', () => {
  const starshot = makeRun({ id: 'starshot-run', catalog_key: 'STARSHOT' })
  const picketFence = makeRun({ id: 'picket-fence-run', catalog_key: 'PICKET_FENCE' })

  expect(historyForCatalog([starshot, picketFence], 'STARSHOT')).toEqual([starshot])
  expect(historyForCatalog([starshot, picketFence], 'PICKET_FENCE')).toEqual([picketFence])
  expect(historyForCatalog(undefined, 'STARSHOT')).toEqual([])
})

test('requires validated inputs before a Pylinac analysis can start', () => {
  const valid = { id: 'valid-image', data_status: 'VALID' } as import('../api/client').ArtifactResource
  const warning = { id: 'warning-image', data_status: 'WARNING' } as import('../api/client').ArtifactResource

  expect(artifactsAreValidated([valid])).toBe(true)
  expect(artifactsAreValidated([warning])).toBe(false)
  expect(artifactsAreValidated([])).toBe(false)
  expect(selectedArtifactsAreValidated(['valid-image'], [valid])).toBe(true)
  expect(selectedArtifactsAreValidated(['valid-image', 'warning-image'], [valid, warning])).toBe(false)
  expect(selectedArtifactsAreValidated(['missing-image'], [valid])).toBe(false)
})
