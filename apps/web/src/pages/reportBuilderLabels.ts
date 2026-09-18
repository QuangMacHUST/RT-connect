export const reportSourceLabels: Record<string, string> = {
  CUSTOM: 'Báo cáo tùy chỉnh',
  QA_CASE: 'Bài kiểm tra chất lượng máy',
  MACHINE_QA: 'Kết quả kiểm tra máy',
  GAMMA: 'Phân tích PSQA',
  DVH: 'Phân tích liều và thể tích',
  BIOLOGICAL: 'Công cụ sinh học'
}

export const reportBlockLabels: Record<string, string> = {
  TEXT: 'Văn bản',
  METADATA: 'Thông tin bài kiểm tra',
  METRICS: 'Chỉ số kết quả',
  GAMMA_MAP: 'Bản đồ Gamma',
  DOSE_PROFILE: 'Biên dạng liều',
  DVH: 'Đường cong liều–thể tích',
  TREND_CHART: 'Biểu đồ xu hướng',
  COMPARISON: 'Bảng so sánh',
  BIOLOGICAL: 'Kết quả sinh học',
  COMMENTS: 'Nhận xét',
  PROVENANCE: 'Nguồn và phiên bản',
  TABLE: 'Bảng dữ liệu',
  IMAGE: 'Hình phân tích',
  WARNING: 'Cảnh báo'
}

export const reportTemplateStatusLabels: Record<string, string> = {
  DRAFT: 'Bản nháp',
  ACTIVE: 'Đang áp dụng',
  ARCHIVED: 'Đã lưu trữ'
}

export const reportExportLabels: Record<string, string> = {
  JSON: 'Tệp dữ liệu',
  CSV: 'Bảng số liệu',
  PDF: 'Tài liệu PDF',
  PNG: 'Hình ảnh'
}

export const reportRunStatusLabels: Record<string, string> = {
  PASS: 'Đạt',
  PASSED: 'Đạt',
  WARNING: 'Cảnh báo',
  FAIL: 'Không đạt',
  FAILED: 'Không đạt',
  PENDING: 'Đang chờ',
  QUEUED: 'Đang chờ',
  RUNNING: 'Đang chạy',
  PROCESSING: 'Đang xử lý',
  COMPLETED: 'Đã hoàn tất',
  CANCELLED: 'Đã hủy',
  CANCELED: 'Đã hủy'
}

export function reportSourceLabel(value: string): string {
  return reportSourceLabels[value] ?? 'Nguồn báo cáo'
}

export function reportBlockLabel(value: string): string {
  return reportBlockLabels[value] ?? 'Khối nội dung'
}

export function reportTemplateStatusLabel(value: string): string {
  return reportTemplateStatusLabels[value] ?? 'Chưa xác định'
}

export function reportExportLabel(value: string): string {
  return reportExportLabels[value] ?? 'Tệp xuất'
}

export function reportRunStatusLabel(value: string | null | undefined): string {
  if (!value) return 'Chưa có đánh giá'
  return reportRunStatusLabels[value.toUpperCase()] ?? 'Đã ghi nhận'
}
