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
  const caseId = '123e4567-e89b-42d3-a456-426614174000'
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      case_id: caseId,
      title: 'Kiểm tra đầu ngày',
      site_name: 'Cơ sở trung tâm',
      machine_name: 'Máy xạ trị 01',
      performed_at: '2026-09-14T08:00:00Z',
      is_archived: true,
      can_purge: true,
      references: []
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.purgeQACase('token', caseId)).rejects.toMatchObject({
    code: 'ACTION_CANCELLED',
    message: 'Đã hủy thao tác xóa vĩnh viễn.'
  })
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('Máy: Máy xạ trị 01'))
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('không thể khôi phục'))
  expect(fetchMock).toHaveBeenCalledTimes(1)
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining(`/qa-cases/${caseId}/purge-preview`), expect.anything())
})

test('does not send a purge request when the preview finds linked data', async () => {
  const confirm = vi.spyOn(window, 'confirm')
  const caseId = '123e4567-e89b-42d3-a456-426614174000'
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      case_id: caseId,
      title: 'Bài có báo cáo',
      site_name: 'Cơ sở trung tâm',
      machine_name: 'Máy xạ trị 01',
      performed_at: '2026-09-14T08:00:00Z',
      is_archived: true,
      can_purge: false,
      references: [{ source: 'reports', count: 1 }]
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.purgeQACase('token', caseId)).rejects.toMatchObject({
    code: 'QA_CASE_REFERENCED',
    message: 'Bài vẫn còn dữ liệu liên quan nên chưa thể xóa vĩnh viễn.'
  })
  expect(confirm).not.toHaveBeenCalled()
  expect(fetchMock).toHaveBeenCalledTimes(1)
})

test('allows a confirmed batch purge helper to send one request without prompting again', async () => {
  const caseId = '123e4567-e89b-42d3-a456-426614174000'
  const confirm = vi.spyOn(window, 'confirm')
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ status: 'PURGED', case_id: caseId })
  })
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.purgeQACaseConfirmed('token', caseId)).resolves.toMatchObject({ status: 'PURGED' })
  expect(confirm).not.toHaveBeenCalled()
  expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining(`/qa-cases/${caseId}/purge`), expect.objectContaining({ method: 'POST' }))
})

test('sends a Gamma cancellation request to the run endpoint', async () => {
  const runId = '123e4567-e89b-42d3-a456-426614174000'
  const fetchMock = vi.fn().mockResolvedValue({
    ok: false,
    json: async () => ({
      code: 'GAMMA_CANCEL_NOT_ALLOWED',
      message: 'Only a queued Gamma analysis can be cancelled before it starts.',
      correlation_id: 'corr-gamma-cancel',
      details: []
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.cancelGammaRun('token', runId)).rejects.toMatchObject({
    code: 'GAMMA_CANCEL_NOT_ALLOWED'
  })
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(`/gamma-runs/${runId}/cancel`),
    expect.objectContaining({ method: 'POST' })
  )
})

test('translates a network failure into a retryable localized client error', async () => {
  vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')))

  const client = new ApiClient('http://api.test/api/v1')
  await expect(client.get('/health', z.object({ status: z.string() }))).rejects.toMatchObject({
    code: 'NETWORK_ERROR',
    message: 'Không thể kết nối tới RT-CONNECT API.'
  } satisfies Partial<ApiClientError>)
})
