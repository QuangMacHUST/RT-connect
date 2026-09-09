import type { Health, Readiness, Version } from '../api/client'

export type PlatformStatusAssessment = {
  key: 'CHECKING' | 'OPERATIONAL' | 'NEEDS_REVIEW' | 'UNAVAILABLE'
  label: string
  badgeClass: string
  explanation: string
}

type PlatformStatusInput = {
  health?: Health
  readiness?: Readiness
  version?: Version
  healthError?: unknown
  readinessError?: unknown
  versionError?: unknown
  pending: boolean
}

export function assessPlatformStatus(input: PlatformStatusInput): PlatformStatusAssessment {
  const hasHealthError = Boolean(input.healthError)
  const hasAnyError = hasHealthError || Boolean(input.readinessError) || Boolean(input.versionError)

  if (hasHealthError && !input.health) {
    return {
      key: 'UNAVAILABLE',
      label: 'API KHÔNG KHẢ DỤNG',
      badgeClass: 'machine-status--fail',
      explanation: 'Không đọc được health endpoint; không thể coi nền tảng là sẵn sàng.'
    }
  }

  if (hasAnyError) {
    return {
      key: 'NEEDS_REVIEW',
      label: 'CẦN XEM XÉT',
      badgeClass: 'status-badge--warning',
      explanation: 'Một hoặc nhiều endpoint vận hành lỗi; /health OK không đủ để xác nhận readiness.'
    }
  }

  if (input.pending) {
    return {
      key: 'CHECKING',
      label: 'ĐANG KIỂM TRA',
      badgeClass: '',
      explanation: 'Đang đọc health, readiness và release metadata từ API thật.'
    }
  }

  const healthOk = input.health?.status === 'ok'
  const readinessOk = input.readiness?.status === 'ready'
  const schemaComparable = Boolean(input.readiness?.schema_revision && input.version?.schema_revision)
  const schemaMatches = schemaComparable && input.readiness?.schema_revision === input.version?.schema_revision

  if (!healthOk || !readinessOk || !schemaMatches) {
    return {
      key: 'NEEDS_REVIEW',
      label: 'CẦN XEM XÉT',
      badgeClass: 'status-badge--warning',
      explanation: 'Health, readiness và schema parity phải cùng đạt trước khi coi release sẵn sàng.'
    }
  }

  return {
    key: 'OPERATIONAL',
    label: 'SẴN SÀNG',
    badgeClass: '',
    explanation: 'Health, readiness và schema parity đang phù hợp trong lần quan sát này.'
  }
}

export function endpointValue(data: { status: string } | undefined, error: unknown, pending: boolean): string {
  if (error) return 'ERROR'
  if (pending || !data) return 'PENDING'
  return data.status.toUpperCase()
}

export function schemaParityValue(readiness?: Readiness, version?: Version, error?: unknown): string {
  if (error) return 'ERROR'
  if (!readiness || !version) return 'PENDING'
  if (!readiness.schema_revision || !version.schema_revision) return 'UNKNOWN'
  return readiness.schema_revision === version.schema_revision ? 'MATCH' : 'MISMATCH'
}

export function statusErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Endpoint không trả về phản hồi hợp lệ.'
}
