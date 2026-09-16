type CatPhanValidationValues = {
  huTolerance: string
  cnrThreshold: string
  thicknessTolerance: string
  originSlice: string
  xAdjustment: string
  yAdjustment: string
  angleAdjustment: string
  roiSizeFactor: string
}

function parseFinite(value: string): number | undefined {
  const parsed = Number(value.trim())
  return value.trim() && Number.isFinite(parsed) ? parsed : undefined
}

function nonNegative(value: string, label: string): string | undefined {
  const parsed = parseFinite(value)
  return parsed === undefined || parsed < 0 ? `${label} phải là số từ 0 trở lên.` : undefined
}

export function validateCatPhanValues(values: CatPhanValidationValues): string | undefined {
  return nonNegative(values.huTolerance, 'Dung sai HU')
    ?? nonNegative(values.cnrThreshold, 'Ngưỡng CNR')
    ?? nonNegative(values.thicknessTolerance, 'Dung sai độ dày')
    ?? nonNegative(values.roiSizeFactor, 'Hệ số kích thước vùng')
    ?? (values.originSlice.trim() !== '' && (!Number.isInteger(parseFinite(values.originSlice)) || Number(values.originSlice) < 0)
      ? 'Lát gốc phải là số nguyên từ 0 trở lên hoặc để trống.'
      : undefined)
    ?? (parseFinite(values.xAdjustment) === undefined ? 'Điều chỉnh ngang phải là số hợp lệ.' : undefined)
    ?? (parseFinite(values.yAdjustment) === undefined ? 'Điều chỉnh dọc phải là số hợp lệ.' : undefined)
    ?? (parseFinite(values.angleAdjustment) === undefined ? 'Điều chỉnh góc phải là số hợp lệ.' : undefined)
}
