type PlanarValidationValues = {
  lowContrast: string
  highContrast: string
  centerX: string
  centerY: string
  angle: string
  roiSize: string
  scaling: string
  isMammography: boolean
}

function parseFinite(value: string): number | undefined {
  const parsed = Number(value.trim())
  return value.trim() && Number.isFinite(parsed) ? parsed : undefined
}

function nonNegative(value: string, label: string): string | undefined {
  const parsed = parseFinite(value)
  return parsed === undefined || parsed < 0 ? `${label} phải là số từ 0 trở lên.` : undefined
}

export function validatePlanarValues(values: PlanarValidationValues): string | undefined {
  const lowContrastError = nonNegative(values.lowContrast, 'Ngưỡng tương phản thấp')
  if (lowContrastError) return lowContrastError

  if (!values.isMammography) {
    const highContrastError = nonNegative(values.highContrast, 'Ngưỡng tương phản cao')
    if (highContrastError) return highContrastError
  }

  const hasCenterX = values.centerX.trim() !== ''
  const hasCenterY = values.centerY.trim() !== ''
  if (hasCenterX !== hasCenterY) return 'Tâm ngang và tâm dọc phải được nhập cùng nhau hoặc để trống cả hai.'
  if (hasCenterX && parseFinite(values.centerX) === undefined) return 'Tâm ngang phải là số hợp lệ.'
  if (hasCenterY && parseFinite(values.centerY) === undefined) return 'Tâm dọc phải là số hợp lệ.'

  if (parseFinite(values.angle) === undefined) return 'Điều chỉnh góc phải là số hợp lệ.'
  return nonNegative(values.roiSize, 'Hệ số vùng quan tâm')
    ?? nonNegative(values.scaling, 'Hệ số thang đo')
}
