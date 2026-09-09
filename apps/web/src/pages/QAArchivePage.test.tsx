import { expect, test } from 'vitest'

import { dvhArtifactStatusLabel, summarizeDvhArtifacts } from './dvhArtifactSummary'

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

  expect(dvhArtifactStatusLabel(summary, 'loading')).toBe('Đang kiểm tra artifact cho DVH…')
  expect(dvhArtifactStatusLabel(summary, 'error')).toBe('Chưa đọc được artifact cho DVH')
  expect(dvhArtifactStatusLabel(summary, 'ready')).toBe('DVH preflight: 1 RTDOSE · 0 RTSTRUCT · 0 CT VALID')
})
