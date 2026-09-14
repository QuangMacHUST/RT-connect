import { expect, test } from 'vitest'

import { dvhArtifactStatusLabel, summarizeDvhArtifacts } from './dvhArtifactSummary'
import { isCaseInArchiveView, toggleAllVisibleCaseSelection, toggleCaseSelection } from './qaArchiveView'

test('thùng rác chỉ hiển thị hồ sơ đã lưu trữ', () => {
  expect(isCaseInArchiveView(true, true)).toBe(true)
  expect(isCaseInArchiveView(false, true)).toBe(false)
  expect(isCaseInArchiveView(false, false)).toBe(true)
})

test('chọn nhiều chỉ thay đổi các bài đang hiển thị và không tạo mục trùng', () => {
  expect(toggleCaseSelection(['case-a'], 'case-a')).toEqual([])
  expect(toggleCaseSelection(['case-a'], 'case-b')).toEqual(['case-a', 'case-b'])
  expect(toggleAllVisibleCaseSelection(['case-old'], ['case-a', 'case-b'])).toEqual(['case-old', 'case-a', 'case-b'])
  expect(toggleAllVisibleCaseSelection(['case-old', 'case-a', 'case-b'], ['case-a', 'case-b'])).toEqual(['case-old'])
})

test('summarizes only valid DICOM inputs for the DVH preflight', () => {
  expect(summarizeDvhArtifacts([
    { artifact_type: 'DICOM', modality: 'RTDOSE', data_status: 'VALID' },
    { artifact_type: 'DICOM', modality: 'RTSTRUCT', data_status: 'VALID' },
    { artifact_type: 'DICOM', modality: 'CT', data_status: 'VALID' },
    { artifact_type: 'DICOM', modality: 'RTSTRUCT', data_status: 'UPLOADED' },
    { artifact_type: 'JSON', modality: null, data_status: 'VALID' }
  ])).toEqual({ dose: 1, structure: 1, ct: 1, ready: true })
})

test('does not claim DVH readiness when structure or dose is missing', () => {
  expect(summarizeDvhArtifacts([
    { artifact_type: 'DICOM', modality: 'RTDOSE', data_status: 'VALID' },
    { artifact_type: 'DICOM', modality: 'RTSTRUCT', data_status: 'INVALID' }
  ])).toEqual({ dose: 1, structure: 0, ct: 0, ready: false })
})

test('uses truthful loading and error labels for the archive DVH shortcut', () => {
  const summary = { dose: 1, structure: 0, ct: 0, ready: false }

  expect(dvhArtifactStatusLabel(summary, 'loading')).toBe('Đang kiểm tra tệp cho phân tích liều…')
  expect(dvhArtifactStatusLabel(summary, 'error')).toBe('Chưa đọc được tệp cho phân tích liều')
  expect(dvhArtifactStatusLabel(summary, 'ready')).toBe('Phân tích liều: 1 RTDOSE · 0 RTSTRUCT · 0 CT hợp lệ')
})
