import { beforeEach, expect, test, vi } from 'vitest'

import { ApiClient, ApiClientError } from './client'

beforeEach(() => {
  vi.restoreAllMocks()
})

test('preserves structured error details for bounded trend queries', async () => {
  vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
    ok: false,
    json: async () => ({
      code: 'TREND_QUERY_TOO_LARGE',
      message: 'The selected trend source is larger than the configured query budget.',
      correlation_id: 'corr-trend-budget',
      details: [
        { field: 'aggregate', message: 'Choose day or week aggregation for a larger source set.' },
        { field: 'matched_points', message: 'The query matched 1001 source points.' },
        { field: 'max_points', message: 'The selected mode allows at most 1000 points.' }
      ]
    })
  }))

  const client = new ApiClient('http://api.test/api/v1')
  await expect(client.trend('token', '00000000-0000-0000-0000-000000000001')).rejects.toMatchObject({
    code: 'TREND_QUERY_TOO_LARGE',
    correlationId: 'corr-trend-budget',
    details: [
      { field: 'aggregate', message: 'Choose day or week aggregation for a larger source set.' },
      { field: 'matched_points', message: 'The query matched 1001 source points.' },
      { field: 'max_points', message: 'The selected mode allows at most 1000 points.' }
    ]
  } satisfies Partial<ApiClientError>)
})
