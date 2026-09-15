import { expect, test } from 'vitest'

import { artifactDisplayName } from './gammaArtifactLabels'
import { artifactDisplayName as qaArtifactDisplayName } from './qaArtifactLabels'

const dose = (id: string, artifactType = 'DICOM', modality: string | null = 'RTDOSE') => ({
  id,
  organization_id: 'organization',
  qa_case_id: 'case',
  artifact_type: artifactType,
  modality,
  original_filename: artifactType === 'MEASUREMENT' ? `${id}.json` : `${id}.dcm`,
  byte_size: 1,
  media_type: 'application/octet-stream',
  sha256: 'a'.repeat(64),
  sop_class_uid: null,
  sop_instance_uid: null,
  study_instance_uid: null,
  series_instance_uid: null,
  frame_of_reference_uid: null,
  source_system: null,
  uploaded_at: '2026-09-15T00:00:00Z',
  data_status: 'VALID',
  parent_artifact_id: null,
  metadata_snapshot: {},
  logical_roles: []
})

test('does not expose JSON filenames in the PSQA input labels', () => {
  const measurement = dose('measurement', 'MEASUREMENT', null)
  const reference = dose('reference')
  const evaluation = dose('evaluation')
  const artifacts = [reference, evaluation, measurement]

  expect(artifactDisplayName(measurement, artifacts)).toBe('Dữ liệu đo liều')
  expect(artifactDisplayName(reference, artifacts)).toBe('Tệp liều RTDOSE 1')
  expect(artifactDisplayName(evaluation, artifacts)).toBe('Tệp liều RTDOSE 2')
})

test('uses business labels for stored QA input types', () => {
  const ct = dose('ct', 'DICOM', 'CT')
  const archive = dose('archive', 'OTHER', null)
  archive.original_filename = 'starshots.json.zip'
  const log = dose('log', 'OTHER', null)
  log.original_filename = 'trajectory.json.tlog'
  const artifacts = [ct, archive, log]

  expect(qaArtifactDisplayName(ct, artifacts)).toBe('Ảnh CT')
  expect(qaArtifactDisplayName(archive, artifacts)).toBe('Bộ ảnh nhiều lớp')
  expect(qaArtifactDisplayName(log, artifacts)).toBe('Nhật ký máy')
  expect(qaArtifactDisplayName(archive, artifacts)).not.toContain('json')
})
