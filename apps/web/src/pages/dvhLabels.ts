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

const indexLabels: Record<string, string> = {
  HI_D2_D98_OVER_D50: 'Độ đồng nhất (D2 − D98) / D50',
  HI_D5_OVER_D95: 'Độ đồng nhất D5 / D95',
  CI_RTOG_95: 'Chỉ số phù hợp RTOG ở mức 95%',
  CI_PADDICK_95: 'Chỉ số phù hợp Paddick ở mức 95%'
}

const indexStatusLabels: Record<string, string> = {
  COMPUTED: 'Đã tính',
  NOT_COMPUTED: 'Chưa đủ dữ liệu'
}

const indexMissingLabels: Record<string, string> = {
  prescription_dose_gy: 'liều kê đơn',
  D50_gy_positive: 'D50 lớn hơn 0',
  D95_gy_positive: 'D95 lớn hơn 0',
  PIV95_cc_positive: 'thể tích liều 95% lớn hơn 0',
  TV_cc_positive: 'thể tích đích lớn hơn 0',
  TV95_cc_positive: 'thể tích đích nhận đủ 95% lớn hơn 0',
  finite_result: 'kết quả hữu hạn'
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

export function dvhIndexLabel(value: string | null | undefined): string {
  if (!value) return 'Chỉ số hình học/liều'
  return indexLabels[value] ?? 'Chỉ số hình học/liều'
}

export function dvhIndexStatusLabel(value: string | null | undefined): string {
  if (!value) return 'Chưa xác định'
  return indexStatusLabels[value] ?? 'Chưa xác định'
}

export function dvhIndexMissingLabel(value: string | null | undefined): string {
  if (!value) return 'dữ liệu bắt buộc'
  return indexMissingLabels[value] ?? 'dữ liệu bắt buộc'
}
