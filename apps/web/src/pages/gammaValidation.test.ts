import { expect, test } from 'vitest'

import type { ArtifactResource, GammaConfiguration } from '../api/client'
import { isGammaWorkflowReady, validateGammaConfiguration } from './gammaValidation'

const validConfiguration: GammaConfiguration = {
  dimensionality: '2D',
  dose_difference_percent: 3,
  dose_difference_mode: 'RELATIVE',
  absolute_dose_difference_gy: null,
  distance_to_agreement_mm: 3,
  dose_threshold_percent: 10,
  normalization: 'GLOBAL',
  interpolation: 'GRID',
  coverage_policy: 'FULL_ROI',
  max_gamma: 2,
  pass_rate_threshold_percent: 95,
  histogram_bins: 10,
  resolution_factor: 3
}

test('accepts the visible PSQA defaults', () => {
  expect(validateGammaConfiguration(validConfiguration)).toEqual([])
})

test('rejects non-positive dose difference and DTA before enqueue', () => {
  const errors = validateGammaConfiguration({ ...validConfiguration, dose_difference_percent: 0, distance_to_agreement_mm: -1 })
  expect(errors.map((item) => item.field)).toEqual(['dose_difference_percent', 'distance_to_agreement_mm'])
})

test('rejects out-of-range thresholds and non-integer histogram settings', () => {
  const errors = validateGammaConfiguration({
    ...validConfiguration,
    dose_threshold_percent: 101,
    pass_rate_threshold_percent: -1,
    histogram_bins: 2.5,
    resolution_factor: 0
  })
  expect(errors).toHaveLength(4)
})

test('does not allow a new 3D run through the PSQA form', () => {
  const errors = validateGammaConfiguration({ ...validConfiguration, dimensionality: '3D' })
  expect(errors).toEqual([{ field: 'dimensionality', message: 'Phân tích mới chỉ hỗ trợ dữ liệu một chiều hoặc hai chiều.' }])
})

function artifact(artifactType: string, modality: string | null = null): ArtifactResource {
  return { artifact_type: artifactType, modality } as ArtifactResource
}

test('allows two validated measurements for one-dimensional Gamma', () => {
  expect(isGammaWorkflowReady({ dimensionality: '1D' }, artifact('MEASUREMENT'), artifact('MEASUREMENT'))).toBe(true)
  expect(isGammaWorkflowReady({ dimensionality: '1D' }, artifact('DICOM', 'RTDOSE'), artifact('MEASUREMENT'))).toBe(false)
})

test('keeps the RTDOSE reference requirement for two-dimensional Gamma', () => {
  expect(isGammaWorkflowReady({ dimensionality: '2D' }, artifact('DICOM', 'RTDOSE'), artifact('MEASUREMENT'))).toBe(true)
  expect(isGammaWorkflowReady({ dimensionality: '2D' }, artifact('MEASUREMENT'), artifact('MEASUREMENT'))).toBe(false)
})
