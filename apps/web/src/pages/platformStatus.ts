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
      label: 'DỊCH VỤ KHÔNG KHẢ DỤNG',
      badgeClass: 'machine-status--fail',
      explanation: 'Không đọc được kiểm tra kết nối; chưa thể coi dịch vụ là sẵn sàng.'
    }
  }

  if (hasAnyError) {
    return {
      key: 'NEEDS_REVIEW',
      label: 'CẦN XEM XÉT',
      badgeClass: 'status-badge--warning',
      explanation: 'Một hoặc nhiều phép kiểm tra vận hành bị lỗi; kết nối bình thường chưa đủ để xác nhận dịch vụ sẵn sàng.'
    }
  }

  if (input.pending) {
    return {
      key: 'CHECKING',
      label: 'ĐANG KIỂM TRA',
      badgeClass: '',
      explanation: 'Đang đọc kết nối, mức sẵn sàng và thông tin phiên bản từ dịch vụ thật.'
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
      explanation: 'Kết nối, mức sẵn sàng và tính nhất quán dữ liệu phải cùng đạt trước khi coi bản phát hành sẵn sàng.'
    }
  }

  return {
    key: 'OPERATIONAL',
    label: 'SẴN SÀNG',
    badgeClass: '',
    explanation: 'Kết nối, mức sẵn sàng và tính nhất quán dữ liệu đang phù hợp trong lần quan sát này.'
  }
}

export function endpointValue(data: { status: string } | undefined, error: unknown, pending: boolean): string {
  if (error) return 'LỖI'
  if (pending || !data) return 'ĐANG KIỂM TRA'
  if (data.status === 'ok') return 'BÌNH THƯỜNG'
  if (data.status === 'ready') return 'SẴN SÀNG'
  return data.status
}

export function schemaParityValue(readiness?: Readiness, version?: Version, error?: unknown): string {
  if (error) return 'LỖI'
  if (!readiness || !version) return 'ĐANG KIỂM TRA'
  if (!readiness.schema_revision || !version.schema_revision) return 'CHƯA RÕ'
  return readiness.schema_revision === version.schema_revision ? 'PHÙ HỢP' : 'KHÔNG KHỚP'
}

export function statusErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Endpoint không trả về phản hồi hợp lệ.'
}
