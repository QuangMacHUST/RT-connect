type VmatValidationValues = {
  tolerance: string
  segmentWidth: string
  segmentLength: string
  collimatorMin?: string
  collimatorMax?: string
  requiresCollimator?: boolean
}

function parseFinite(value: string): number | undefined {
  const parsed = Number(value.trim())
  return value.trim() && Number.isFinite(parsed) ? parsed : undefined
}

export function validateVmatValues(values: VmatValidationValues): string | undefined {
  const tolerance = parseFinite(values.tolerance)
  if (tolerance === undefined || tolerance < 0) return 'Dung sai phải là số từ 0 trở lên.'

  const segmentWidth = parseFinite(values.segmentWidth)
  if (segmentWidth === undefined || segmentWidth <= 0) return 'Chiều rộng đoạn phân tích phải lớn hơn 0.'

  const segmentLength = parseFinite(values.segmentLength)
  if (segmentLength === undefined || segmentLength <= 0) return 'Chiều dài đoạn phân tích phải lớn hơn 0.'

  if (!values.requiresCollimator) return undefined

  const collimatorMin = parseFinite(values.collimatorMin ?? '')
  if (collimatorMin === undefined || collimatorMin < 0) return 'Khoảng cách xuyên tâm nhỏ nhất phải là số từ 0 trở lên.'

  const collimatorMax = parseFinite(values.collimatorMax ?? '')
  if (collimatorMax === undefined || collimatorMax < collimatorMin) return 'Khoảng cách xuyên tâm lớn nhất phải lớn hơn hoặc bằng khoảng cách nhỏ nhất.'

  return undefined
}
