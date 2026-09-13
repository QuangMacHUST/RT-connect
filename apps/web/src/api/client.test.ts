import { beforeEach, expect, test, vi } from 'vitest'
import { z } from 'zod'

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

test('requires confirmation before permanently purging a QA case', async () => {
  const confirm = vi.spyOn(window, 'confirm').mockReturnValue(false)
  const fetchMock = vi.fn()
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.purgeQACase('token', '00000000-0000-0000-0000-000000000001')).rejects.toMatchObject({
    code: 'ACTION_CANCELLED',
    message: 'Đã hủy thao tác xóa vĩnh viễn.'
  })
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('không thể khôi phục'))
  expect(fetchMock).not.toHaveBeenCalled()
})

test('translates a network failure into a retryable localized client error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

  const client = new ApiClient('http://api.test/api/v1')
  await expect(client.get('/health', z.object({ status: z.string() }))).rejects.toMatchObject({
    code: 'NETWORK_ERROR',
    message: 'Không thể kết nối tới RT-CONNECT API.'
  } satisfies Partial<ApiClientError>)
})
