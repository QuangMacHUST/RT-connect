import { describe, expect, test } from 'vitest'

import { assessPlatformStatus, schemaParityValue } from './platformStatus'

describe('platform status assessment', () => {
  test('requires readiness and schema parity in addition to health', () => {
    const result = assessPlatformStatus({
      health: { status: 'ok', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'h' },
      readiness: { status: 'ready', timestamp: '2026-09-05T00:00:00Z', correlation_id: 'r', schema_revision: 'a' },
      version: { application: 'api', version: '1', environment: 'test', engine_version: 'e', renderer_version: 'r', schema_revision: 'b' },
      pending: false
    })

    expect(result.key).toBe('NEEDS_REVIEW')
    expect(result.label).toBe('CẦN XEM XÉT')
    expect(schemaParityValue({ status: 'ready', timestamp: '', correlation_id: '', schema_revision: 'a' }, { application: '', version: '', environment: '', engine_version: '', renderer_version: '', schema_revision: 'b' })).toBe('KHÔNG KHỚP')
  })

  test('reports operational only when all independent probes agree', () => {
    const result = assessPlatformStatus({
      health: { status: 'ok', timestamp: '', correlation_id: 'h' },
      readiness: { status: 'ready', timestamp: '', correlation_id: 'r', schema_revision: 'a' },
      version: { application: 'api', version: '1', environment: 'test', engine_version: 'e', renderer_version: 'r', schema_revision: 'a' },
      pending: false
    })

    expect(result.key).toBe('OPERATIONAL')
    expect(result.label).toBe('SẴN SÀNG')
  })
})
