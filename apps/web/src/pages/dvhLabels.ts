const statusLabels: Record<string, string> = {
  FULL: 'Đủ vùng tính',
  OVERLAP_ONLY: 'Chỉ vùng chồng lấp',
  PASS: 'Đạt',
  REVIEW_REQUIRED: 'Cần xem lại',
  FAIL: 'Không đạt',
  WARNING: 'Cảnh báo'
}

const sourceLabels: Record<string, string> = {
  BIOLOGICAL_LIBRARY: 'Thư viện sinh học',
  QA_PROTOCOL: 'Quy trình QA',
  USER_DEFINED: 'Do đơn vị nhập',
  PUBLISHED: 'Tài liệu đã công bố'
}

const metricLabels: Record<string, string> = {
  D2: 'D2',
  D50: 'D50',
  D95: 'D95',
  D98: 'D98',
  DMEAN: 'Liều trung bình',
  DMIN: 'Liều thấp nhất',
  DMAX: 'Liều cao nhất'
}

export function dvhStatusLabel(value: string | null | undefined): string {
  return value ? statusLabels[value] ?? value : 'Chưa xác định'
}

export function dvhSourceLabel(value: string | null | undefined): string {
  return value ? sourceLabels[value] ?? 'Nguồn tham khảo' : 'Chưa khai báo'
}

export function dvhMetricLabel(value: string | null | undefined): string {
  if (!value) return 'Chỉ số'
  return metricLabels[value] ?? metricLabels[value.toUpperCase()] ?? value
}

export function dvhOperatorLabel(value: string | null | undefined): string {
  if (value === 'MIN') return 'tối thiểu'
  if (value === 'MAX') return 'tối đa'
  if (value === 'RANGE') return 'trong khoảng'
  return value ?? 'theo tiêu chí'
}
