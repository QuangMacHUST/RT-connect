type AcrValidationValues = {
  originSlice: string
  xAdjustment: string
  yAdjustment: string
  angleAdjustment: string
  roiSizeFactor: string
  scalingFactor: string
  echoNumber: string
  lowContrastThreshold: string
  lowContrastSanity: string
  isMri: boolean
}

function parseFinite(value: string): number | undefined {
  const parsed = Number(value.trim())
  return value.trim() && Number.isFinite(parsed) ? parsed : undefined
}

function nonNegative(value: string, label: string): string | undefined {
  const parsed = parseFinite(value)
  return parsed === undefined || parsed < 0 ? `${label} phải là số từ 0 trở lên.` : undefined
}

export function validateAcrValues(values: AcrValidationValues): string | undefined {
  if (values.originSlice.trim() !== '') {
    const originSlice = parseFinite(values.originSlice)
    if (originSlice === undefined || !Number.isInteger(originSlice) || originSlice < 0) return 'Lát gốc phải là số nguyên từ 0 trở lên hoặc để trống.'
  }

  return parseFinite(values.xAdjustment) === undefined ? 'Điều chỉnh ngang phải là số hợp lệ.'
    : parseFinite(values.yAdjustment) === undefined ? 'Điều chỉnh dọc phải là số hợp lệ.'
      : parseFinite(values.angleAdjustment) === undefined ? 'Điều chỉnh góc phải là số hợp lệ.'
        : nonNegative(values.roiSizeFactor, 'Hệ số kích thước vùng')
          ?? nonNegative(values.scalingFactor, 'Hệ số thang đo')
          ?? (!values.isMri ? undefined : validateAcrMriValues(values))
}

function validateAcrMriValues(values: AcrValidationValues): string | undefined {
  if (values.echoNumber.trim() !== '') {
    const echoNumber = parseFinite(values.echoNumber)
    if (echoNumber === undefined || !Number.isInteger(echoNumber) || echoNumber < 1) return 'Số lần vọng phải là số nguyên từ 1 trở lên hoặc để trống.'
  }
  return nonNegative(values.lowContrastThreshold, 'Ngưỡng nhìn thấy tương phản thấp')
    ?? nonNegative(values.lowContrastSanity, 'Hệ số kiểm tra hợp lý')
}
