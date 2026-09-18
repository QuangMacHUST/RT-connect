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

test('loads the bounded image count for a multi-image preview', async () => {
  const artifactId = '123e4567-e89b-42d3-a456-426614174000'
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ image_count: 2, width: 270, height: 270, pixel_spacing_mm: [1, 1] })
  })
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.previewArtifactInfo('token', artifactId)).resolves.toEqual({ image_count: 2, width: 270, height: 270, pixel_spacing_mm: [1, 1] })
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(`/artifacts/${artifactId}/preview-info`),
    expect.objectContaining({
      headers: expect.objectContaining({
        Accept: 'application/json',
        Authorization: 'Bearer token'
      })
    })
  )
})

test('loads a saved report preview as an image from the renderer endpoint', async () => {
  const reportKey = '123e4567-e89b-42d3-a456-426614174000'
  const revisionId = '123e4567-e89b-42d3-a456-426614174001'
  const preview = new Blob(['png-bytes'], { type: 'image/png' })
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    headers: new Headers({ 'content-type': 'image/png' }),
    blob: async () => preview
  })
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.reportPreview('token', reportKey, revisionId)).resolves.toBe(preview)
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(`/reports/${reportKey}/revisions/${revisionId}/preview?format=PNG`),
    expect.objectContaining({
      headers: expect.objectContaining({
        Accept: 'image/png',
        Authorization: 'Bearer token'
      })
    })
  )
})

test('loads export history for one saved report revision', async () => {
  const reportKey = '123e4567-e89b-42d3-a456-426614174000'
  const revisionId = '123e4567-e89b-42d3-a456-426614174001'
  const exportId = '123e4567-e89b-42d3-a456-426614174002'
  const fetchMock = vi.fn().mockResolvedValue({
    ok: true,
    json: async () => ({
      items: [{
        id: exportId, organization_id: '123e4567-e89b-42d3-a456-426614174003', report_revision_id: revisionId,
        idempotency_key: 'report-export-001', export_format: 'PDF', render_options: {}, renderer_version: 'report-renderer-0.4',
        status: 'COMPLETED', object_key: null, sha256: 'a'.repeat(64), byte_size: 128, media_type: 'application/pdf',
        error_snapshot: [], warning_snapshot: [], download_url: null, download_expires_at: null,
        created_at: '2026-09-18T12:00:00Z', updated_at: '2026-09-18T12:00:01Z'
      }], total: 1, offset: 0, limit: 20
    })
  })
  vi.stubGlobal('fetch', fetchMock)
  const client = new ApiClient('http://api.test/api/v1')

  await expect(client.reportExports('token', reportKey, revisionId)).resolves.toMatchObject({ total: 1, items: [{ export_format: 'PDF' }] })
  expect(fetchMock).toHaveBeenCalledWith(
    expect.stringContaining(`/reports/${reportKey}/revisions/${revisionId}/exports`),
    expect.objectContaining({ headers: expect.objectContaining({ Authorization: 'Bearer token' }) })
  )
})
