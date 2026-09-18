type CtPylinacValidationValues = {
  originSlice: string
  xAdjustment: string
  yAdjustment: string
  angleAdjustment: string
  roiSizeFactor: string
  scalingFactor: string
  roiOneDensity: string
  roiTwoDensity: string
  huTolerance: string
  scalingTolerance: string
  thicknessTolerance: string
  cnrThreshold: string
  rollSliceOffset: string
  isCheese: boolean
  isQuart: boolean
}

function parseFinite(value: string): number | undefined {
  const parsed = Number(value.trim())
  return value.trim() && Number.isFinite(parsed) ? parsed : undefined
}

function nonNegative(value: string, label: string): string | undefined {
  const parsed = parseFinite(value)
  return parsed === undefined || parsed < 0 ? `${label} phải là số từ 0 trở lên.` : undefined
}

function optionalNonNegative(value: string, label: string): string | undefined {
  return value.trim() === '' ? undefined : nonNegative(value, label)
}

export function validateCtPylinacValues(values: CtPylinacValidationValues): string | undefined {
  if (values.originSlice.trim() !== '') {
    const originSlice = parseFinite(values.originSlice)
    if (originSlice === undefined || !Number.isInteger(originSlice) || originSlice < 0) {
      return 'Lát gốc phải là số nguyên từ 0 trở lên hoặc để trống.'
    }
  }

  const geometryError = parseFinite(values.xAdjustment) === undefined
    ? 'Điều chỉnh ngang phải là số hợp lệ.'
    : parseFinite(values.yAdjustment) === undefined
      ? 'Điều chỉnh dọc phải là số hợp lệ.'
      : parseFinite(values.angleAdjustment) === undefined
        ? 'Điều chỉnh góc phải là số hợp lệ.'
        : undefined
  if (geometryError) return geometryError

  const commonError = nonNegative(values.roiSizeFactor, 'Hệ số kích thước vùng')
    ?? nonNegative(values.scalingFactor, 'Hệ số thang đo')
  if (commonError) return commonError

  if (values.isCheese) {
    return optionalNonNegative(values.roiOneDensity, 'Mật độ tham chiếu ROI 1')
      ?? optionalNonNegative(values.roiTwoDensity, 'Mật độ tham chiếu ROI 2')
  }

  if (!values.isQuart) return undefined

  return nonNegative(values.huTolerance, 'Dung sai HU')
    ?? nonNegative(values.scalingTolerance, 'Dung sai thang đo')
    ?? nonNegative(values.thicknessTolerance, 'Dung sai độ dày')
    ?? nonNegative(values.cnrThreshold, 'Ngưỡng CNR')
    ?? (parseFinite(values.rollSliceOffset) === undefined ? 'Dịch lát tìm góc phải là số hợp lệ.' : undefined)
}
