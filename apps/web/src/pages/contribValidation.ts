type ContribValidationValues = {
  catalogKey: string
  fwxm: string
  bbEdgeThreshold: string
}

function parseFinite(value: string): number | undefined {
  const parsed = Number(value.trim())
  return value.trim() && Number.isFinite(parsed) ? parsed : undefined
}

export function validateContribValues(values: ContribValidationValues): string | undefined {
  if (values.catalogKey !== 'CONTRIB_QUASAR_LIGHT_RAD_SCALING') return undefined

  const fwxm = parseFinite(values.fwxm)
  if (fwxm === undefined || fwxm < 1 || fwxm > 100) return 'Phần trăm FWXM phải nằm trong khoảng từ 1 đến 100.'

  const edgeThreshold = parseFinite(values.bbEdgeThreshold)
  if (edgeThreshold === undefined || edgeThreshold <= 0) return 'Ngưỡng cạnh biên phải lớn hơn 0.'

  return undefined
}
