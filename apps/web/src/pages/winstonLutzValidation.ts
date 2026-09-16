export type WinstonLutzAngleValues = {
  gantry: string
  collimator: string
  couch: string
}

export type WinstonLutzBBValues = {
  name: string
  offset_left_mm: string
  offset_up_mm: string
  offset_in_mm: string
  bb_size_mm: string
  rad_size_mm: string
}

type NumberRule = {
  label: string
  value: string
  allowEmpty?: boolean
  minimum?: number
  strictlyGreaterThan?: number
}

function validateNumber({ label, value, allowEmpty = false, minimum, strictlyGreaterThan }: NumberRule): string | undefined {
  const trimmed = value.trim()
  if (trimmed === '') return allowEmpty ? undefined : `Nhập ${label}.`
  const parsed = Number(trimmed)
  if (!Number.isFinite(parsed)) return `${label} phải là một số hợp lệ.`
  if (minimum !== undefined && parsed < minimum) return `${label} không được nhỏ hơn ${minimum}.`
  if (strictlyGreaterThan !== undefined && parsed <= strictlyGreaterThan) return `${label} phải lớn hơn ${strictlyGreaterThan}.`
  return undefined
}

export function validateWinstonLutzValues(values: {
  sid: string
  dpi: string
  bbSizeMm: string
  snapTolerance: string
  bbProximityMm: string
  gantryReference: string
  collimatorReference: string
  couchReference: string
}): string | undefined {
  const rules: NumberRule[] = [
    { label: 'Khoảng cách nguồn–ảnh', value: values.sid, strictlyGreaterThan: 0 },
    { label: 'Mật độ điểm ảnh', value: values.dpi, allowEmpty: true, strictlyGreaterThan: 0 },
    { label: 'Kích thước bi chuẩn', value: values.bbSizeMm, strictlyGreaterThan: 0 },
    { label: 'Dung sai bắt ảnh', value: values.snapTolerance, minimum: 0 },
    { label: 'Khoảng cách nhận diện bi', value: values.bbProximityMm, minimum: 0 },
    { label: 'Góc máy tham chiếu', value: values.gantryReference },
    { label: 'Góc chuẩn trực tham chiếu', value: values.collimatorReference },
    { label: 'Góc bàn tham chiếu', value: values.couchReference },
  ]
  return rules.map(validateNumber).find((message) => message)
}

export function validateWinstonLutzMultiTargetValues(values: {
  sid: string
  dpi: string
  bbProximityMm: string
  arrangement: WinstonLutzBBValues[]
}): string | undefined {
  const commonError = [
    validateNumber({ label: 'Khoảng cách nguồn–ảnh', value: values.sid, strictlyGreaterThan: 0 }),
    validateNumber({ label: 'Mật độ điểm ảnh', value: values.dpi, allowEmpty: true, strictlyGreaterThan: 0 }),
    validateNumber({ label: 'Khoảng cách nhận diện bi', value: values.bbProximityMm, minimum: 0 }),
  ].find((message) => message)
  if (commonError) return commonError
  if (values.arrangement.length === 0) return 'Cần có ít nhất một bi chuẩn.'
  if (values.arrangement.length > 32) return 'Không thể khai báo quá 32 bi chuẩn trong một bài.'

  for (const [index, row] of values.arrangement.entries()) {
    const rowNumber = index + 1
    if (!row.name.trim()) return `Nhập tên bi chuẩn số ${rowNumber}.`
    const numericError = [
      validateNumber({ label: `Độ lệch trái/phải của bi ${rowNumber}`, value: row.offset_left_mm }),
      validateNumber({ label: `Độ lệch lên/xuống của bi ${rowNumber}`, value: row.offset_up_mm }),
      validateNumber({ label: `Độ lệch trong/ngoài của bi ${rowNumber}`, value: row.offset_in_mm }),
      validateNumber({ label: `Kích thước bi ${rowNumber}`, value: row.bb_size_mm, strictlyGreaterThan: 0 }),
      validateNumber({ label: `Bán kính trường của bi ${rowNumber}`, value: row.rad_size_mm, strictlyGreaterThan: 0 }),
    ].find((message) => message)
    if (numericError) return numericError
  }
  return undefined
}

export function validateManualWinstonLutzAngles(
  source: 'DICOM' | 'FILENAME' | 'MANUAL',
  rows: WinstonLutzAngleValues[],
  imageCount: number,
): string | undefined {
  if (source !== 'MANUAL') return undefined
  if (imageCount < 2) return 'Cần ít nhất hai ảnh trước khi nhập góc theo thứ tự ảnh.'
  if (rows.length !== imageCount) return 'Số dòng góc nhập tay chưa khớp với số ảnh.'
  for (const [index, row] of rows.entries()) {
    const rowNumber = index + 1
    const error = [
      validateNumber({ label: `Góc máy của ảnh ${rowNumber}`, value: row.gantry }),
      validateNumber({ label: `Góc chuẩn trực của ảnh ${rowNumber}`, value: row.collimator }),
      validateNumber({ label: `Góc bàn của ảnh ${rowNumber}`, value: row.couch }),
    ].find((message) => message)
    if (error) return error
  }
  return undefined
}
