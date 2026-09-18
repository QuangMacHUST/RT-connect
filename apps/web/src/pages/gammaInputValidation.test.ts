import { expect, test } from 'vitest'

import type { ArtifactResource, GammaConfiguration } from '../api/client'
import { validateGammaInputGeometry } from './gammaInputValidation'

const configuration: Pick<GammaConfiguration, 'dimensionality' | 'distance_to_agreement_mm'> = {
  dimensionality: '2D',
  distance_to_agreement_mm: 3
}

function artifact(metadata_snapshot: Record<string, unknown>): ArtifactResource {
  return { metadata_snapshot } as ArtifactResource
}

function measurement(overrides: Record<string, unknown> = {}): ArtifactResource {
  return artifact({
    grid: { shape: [3, 3], spacing_mm: [1, 1], origin_mm: [0, 0], ...overrides }
  })
}

test('accepts two matching square grids when DTA is aligned', () => {
  expect(validateGammaInputGeometry(configuration, measurement(), measurement())).toEqual([])
})

test('blocks a dimensionality mismatch before enqueue', () => {
  const errors = validateGammaInputGeometry(
    { ...configuration, dimensionality: '1D' },
    measurement(),
    measurement()
  )
  expect(errors[0]?.field).toBe('dimensionality')
})

test('blocks different shape and origin before enqueue', () => {
  expect(validateGammaInputGeometry(configuration, measurement(), measurement({ shape: [2, 3] }))[0]?.field).toBe('shape')
  expect(validateGammaInputGeometry(configuration, measurement(), measurement({ origin_mm: [1, 0] }))[0]?.field).toBe('origin')
})

test('blocks non-square grids and unaligned DTA before enqueue', () => {
  expect(validateGammaInputGeometry(configuration, measurement({ spacing_mm: [1, 2] }), measurement({ spacing_mm: [1, 2] }))[0]?.field).toBe('spacing')
  expect(validateGammaInputGeometry({ ...configuration, distance_to_agreement_mm: 2.5 }, measurement(), measurement())[0]?.field).toBe('distance_to_agreement_mm')
})

