function validatePositiveNumber(label: string, value: string): string | undefined {
  const trimmed = value.trim()
  if (trimmed === '') return `Nhập ${label} khi bật bản đồ Gamma fluence.`
  const parsed = Number(trimmed)
  if (!Number.isFinite(parsed) || parsed <= 0) return `${label} phải là số lớn hơn 0.`
  return undefined
}

export function validateLogGammaValues(
  calculateGamma: boolean,
  doseTolerance: string,
  distanceTolerance: string,
): string | undefined {
  if (!calculateGamma) return undefined
  return validatePositiveNumber('Dung sai liều', doseTolerance)
    ?? validatePositiveNumber('Dung sai khoảng cách', distanceTolerance)
}
