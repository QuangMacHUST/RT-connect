import { fireEvent, render, screen } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { expect, test, vi } from 'vitest'

import type { PylinacQARunResource } from '../api/client'
import { PylinacAdjustmentCanvas, PylinacResultPanel, PylinacStructuredResultDetails, WinstonLutzMultiTargetDetails } from './MachineQAPage'
import { calibrationCoefficientKey, validateCalibrationValues } from './calibrationValidation'
import { historyForCatalog } from './pylinacHistory'
import { mapImagePoint } from './pylinacCoordinates'
import { artifactsAreValidated, selectedArtifactsAreValidated } from './qaArtifactLabels'
import { validateManualWinstonLutzAngles, validateWinstonLutzMultiTargetValues, validateWinstonLutzValues } from './winstonLutzValidation'
import { validateLogGammaValues } from './logValidation'
import { validateLogArtifactSelection } from './logSelectionValidation'

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

test('shows Winston-Lutz multi-target details by image and BB without exposing filenames', () => {
  const run = makeRun({
    catalog_key: 'WINSTON_LUTZ_MULTI_TARGET',
    result_snapshot: {
      metrics: {
        bb_arrangement: [{ name: 'Iso' }, { name: '1' }],
        image_details: [
          {
            image_name: 'RT000001.dcm',
            gantry_angle: 0,
            collimator_angle: 10,
            couch_angle: 20,
            bb_distances: { Iso: 0.3, '1': 1.2 },
            couch_yaw_error: 0.1,
          },
          {
            image_name: 'RT000002.dcm',
            gantry_angle: 180,
            collimator_angle: 10,
            couch_angle: 20,
            bb_distances: { Iso: 0.4, '1': null },
            couch_yaw_error: 0.2,
          },
        ],
      },
    },
  })

  render(<PylinacResultPanel {...baseProps(run, [run])} renderResultDetails={(selected) => <WinstonLutzMultiTargetDetails run={selected} />} />)

  expect(screen.getByRole('heading', { name: 'Khoảng cách trường–bi' })).toBeInTheDocument()
  expect(screen.getByRole('rowheader', { name: 'Ảnh 1' })).toBeInTheDocument()
  expect(screen.getByRole('columnheader', { name: 'Bi Iso' })).toBeInTheDocument()
  expect(screen.getByText('0,3')).toBeInTheDocument()
  expect(screen.queryByText('RT000001.dcm')).not.toBeInTheDocument()
  expect(screen.queryByText('RT000002.dcm')).not.toBeInTheDocument()
})

test('renders nested Pylinac metrics in readable groups without technical identifiers', () => {
  const run = makeRun({
    result_snapshot: {
      metrics: {
        ctp404: { low_contrast_visibility: 6.95, image_name: 'CatPhan503.dcm' },
        x_metrics: { 'Field Width (mm)': 100.2, artifact_id: 'internal-artifact' },
      },
    },
  })

  render(<PylinacStructuredResultDetails run={run} />)

  expect(screen.getByRole('heading', { name: 'Các nhóm chỉ số do Pylinac cung cấp' })).toBeInTheDocument()
  expect(screen.getByText('CTP404')).toBeInTheDocument()
  expect(screen.getByText('6,95')).toBeInTheDocument()
  expect(screen.getByText('X METRICS')).toBeInTheDocument()
  expect(screen.getByText('100,2')).toBeInTheDocument()
  expect(screen.queryByText('CatPhan503.dcm')).not.toBeInTheDocument()
  expect(screen.queryByText('internal-artifact')).not.toBeInTheDocument()
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

test('validates calibration readings before sending them to Pylinac', () => {
  const values = {
    institution: 'Bệnh viện tổng hợp',
    physicist: 'Kỹ sư vật lý',
    unit: 'LINAC-01',
    measurement_date: '2026-09-16',
    electrometer: 'Điện kế A',
    energy: '6',
    temp: '22',
    press: '101.3',
    chamber: 'A12',
    p_elec: '1',
    n_dw: '5',
    voltage_reference: '300',
    voltage_reduced: '150',
    m_reference: '10.0, 10.2',
    m_opposite: '10.1',
    m_reduced: '9.8',
    mu: '200',
    measured_pdd10: '66.7',
    clinical_pdd10: '66.7',
  }

  expect(validateCalibrationValues('CALIBRATION_TG51_PHOTON', values)).toBeUndefined()
  expect(validateCalibrationValues('CALIBRATION_TG51_PHOTON', { ...values, m_reference: '10.0, sai' })).toContain('Số đọc tham chiếu')
  expect(validateCalibrationValues('CALIBRATION_TG51_PHOTON', { ...values, measured_pdd10: '' })).toContain('PDD đo tại 10 cm')
})

test('uses the TRS-398 điện kế field for both TRS-398 calibration variants', () => {
  const values = {
    institution: 'Bệnh viện tổng hợp',
    physicist: 'Kỹ sư vật lý',
    unit: 'LINAC-01',
    measurement_date: '2026-09-16',
    electrometer: 'Điện kế A',
    energy: '6 MeV',
    temp: '22',
    press: '101.3',
    chamber: 'A12',
    k_elec: '1',
    n_dw: '5',
    voltage_reference: '300',
    voltage_reduced: '150',
    m_reference: '10.0, 10.2',
    m_opposite: '10.1',
    m_reduced: '9.8',
    mu: '200',
    i_50: '5',
    clinical_pdd_zref: '66.7',
    tissue_correction: '1',
    cone: '10x10',
  }

  expect(validateCalibrationValues('CALIBRATION_TRS398_ELECTRON', values)).toBeUndefined()
  expect(calibrationCoefficientKey('CALIBRATION_TRS398_PHOTON')).toBe('k_elec')
  expect(calibrationCoefficientKey('CALIBRATION_TRS398_ELECTRON')).toBe('k_elec')
  expect(calibrationCoefficientKey('CALIBRATION_TG51_PHOTON')).toBe('p_elec')
})

test('validates Winston-Lutz numeric fields before the request is created', () => {
  const valid = {
    sid: '1000', dpi: '', bbSizeMm: '5', snapTolerance: '3', bbProximityMm: '20',
    gantryReference: '0', collimatorReference: '0', couchReference: '0'
  }

  expect(validateWinstonLutzValues(valid)).toBeUndefined()
  expect(validateWinstonLutzValues({ ...valid, sid: '' })).toContain('Khoảng cách nguồn–ảnh')
  expect(validateWinstonLutzValues({ ...valid, bbSizeMm: '0' })).toContain('Kích thước bi chuẩn')
  expect(validateWinstonLutzValues({ ...valid, dpi: 'sai' })).toContain('Mật độ điểm ảnh')
})

test('validates every multi-target BB row and manual angle mapping', () => {
  const arrangement = [{
    name: 'Iso', offset_left_mm: '0', offset_up_mm: '0', offset_in_mm: '0', bb_size_mm: '5', rad_size_mm: '20'
  }]
  const angles = [
    { gantry: '0', collimator: '10', couch: '20' },
    { gantry: '180', collimator: '10', couch: '20' }
  ]

  expect(validateWinstonLutzMultiTargetValues({ sid: '1000', dpi: '', bbProximityMm: '10', arrangement })).toBeUndefined()
  expect(validateWinstonLutzMultiTargetValues({ sid: '1000', dpi: '', bbProximityMm: '10', arrangement: [{ ...arrangement[0], rad_size_mm: '' }] })).toContain('Bán kính trường')
  expect(validateManualWinstonLutzAngles('MANUAL', angles, 2)).toBeUndefined()
  expect(validateManualWinstonLutzAngles('MANUAL', [{ ...angles[0], couch: '' }, angles[1]], 2)).toContain('Góc bàn')
  expect(validateManualWinstonLutzAngles('MANUAL', angles, 3)).toContain('Số dòng')
})

test('requires positive fluence Gamma tolerances only when Gamma is enabled', () => {
  expect(validateLogGammaValues(false, '', '')).toBeUndefined()
  expect(validateLogGammaValues(true, '1', '1')).toBeUndefined()
  expect(validateLogGammaValues(true, '', '1')).toContain('Dung sai liều')
  expect(validateLogGammaValues(true, '1', '0')).toContain('Dung sai khoảng cách')
})

test('requires a Dynalog A and B pair before analysis', () => {
  expect(validateLogArtifactSelection('LOG_DYNALOG', [{ original_filename: 'AQA.dlg' }, { original_filename: 'BQA.dlg' }])).toBeUndefined()
  expect(validateLogArtifactSelection('LOG_DYNALOG', [{ original_filename: 'AQA.dlg' }])).toContain('đúng hai tệp')
  expect(validateLogArtifactSelection('LOG_DYNALOG', [{ original_filename: 'AQA.dlg' }, { original_filename: 'CQA.dlg' }])).toContain('bắt đầu bằng A')
  expect(validateLogArtifactSelection('LOG_DYNALOG', [{ original_filename: 'AQA.dlg' }, { original_filename: 'notes.txt' }])).toContain('chỉ nhận tệp DLG')
})

test('requires one Trajectory binary and allows one TXT sidecar', () => {
  expect(validateLogArtifactSelection('LOG_TRAJECTORY_3', [{ original_filename: 'Tlog.bin' }])).toBeUndefined()
  expect(validateLogArtifactSelection('LOG_TRAJECTORY_3', [{ original_filename: 'Tlog.bin' }, { original_filename: 'ghi-chu.txt' }])).toBeUndefined()
  expect(validateLogArtifactSelection('LOG_TRAJECTORY_3', [{ original_filename: 'ghi-chu.txt' }])).toContain('đúng một tệp BIN')
  expect(validateLogArtifactSelection('LOG_TRAJECTORY_3', [{ original_filename: 'A.bin' }, { original_filename: 'B.tlog' }])).toContain('đúng một tệp BIN')
})
