export type CalibrationCatalogKey =
  | 'CALIBRATION_TG51_PHOTON'
  | 'CALIBRATION_TG51_ELECTRON_LEGACY'
  | 'CALIBRATION_TG51_ELECTRON_MODERN'
  | 'CALIBRATION_TRS398_PHOTON'
  | 'CALIBRATION_TRS398_ELECTRON'

export const calibrationNames: Record<CalibrationCatalogKey, string> = {
  CALIBRATION_TG51_PHOTON: 'Hiệu chuẩn TG-51 photon',
  CALIBRATION_TG51_ELECTRON_LEGACY: 'Hiệu chuẩn TG-51 điện tử phiên bản cũ',
  CALIBRATION_TG51_ELECTRON_MODERN: 'Hiệu chuẩn TG-51 điện tử phiên bản hiện hành',
  CALIBRATION_TRS398_PHOTON: 'Hiệu chuẩn TRS-398 photon',
  CALIBRATION_TRS398_ELECTRON: 'Hiệu chuẩn TRS-398 điện tử',
}

export function calibrationCoefficientKey(catalogKey: CalibrationCatalogKey): 'p_elec' | 'k_elec' {
  return catalogKey.startsWith('CALIBRATION_TRS398_') ? 'k_elec' : 'p_elec'
}

const calibrationFieldLabels: Record<string, string> = {
  institution: 'Tên đơn vị',
  physicist: 'Người thực hiện',
  unit: 'Tên máy',
  measurement_date: 'Ngày đo',
  electrometer: 'Điện kế',
  energy: 'Năng lượng',
  temp: 'Nhiệt độ',
  press: 'Áp suất',
  n_dw: 'Hệ số NDW',
  p_elec: 'Hệ số điện kế',
  k_elec: 'Hệ số điện kế',
  voltage_reference: 'Điện áp tham chiếu',
  voltage_reduced: 'Điện áp giảm',
  m_reference: 'Số đọc tham chiếu',
  m_opposite: 'Số đọc ngược cực',
  m_reduced: 'Số đọc điện áp giảm',
  mu: 'Số MU',
  chamber: 'Buồng ion hóa',
  measured_pdd10: 'PDD đo tại 10 cm',
  clinical_pdd10: 'PDD lâm sàng tại 10 cm',
  clinical_pdd: 'PDD lâm sàng',
  i_50: 'Độ sâu I50',
  k_ecal: 'Hệ số kecal',
  m_gradient: 'Số đọc gradient',
  tpr2010: 'TPR(20)/TPR(10)',
  clinical_pdd_zref: 'PDD tại độ sâu tham chiếu',
  clinical_tmr_zref: 'TMR tại độ sâu tham chiếu',
  tissue_correction: 'Hiệu chỉnh mô',
  cone: 'Kích thước nón',
}

function calibrationNumber(value: string | undefined): number | undefined {
  if (!value?.trim()) return undefined
  const number = Number(value)
  return Number.isFinite(number) ? number : undefined
}

function calibrationReadings(value: string | undefined): number[] | undefined {
  if (!value?.trim()) return undefined
  const parts = value.split(',').map((item) => item.trim())
  if (parts.some((item) => item === '')) return undefined
  const numbers = parts.map((item) => calibrationNumber(item))
  return numbers.every((item): item is number => item !== undefined) ? numbers : undefined
}

/**
 * Kiểm tra ngay trên giao diện để người dùng biết trường nào còn thiếu hoặc
 * sai định dạng trước khi gửi số đo tới Pylinac. Máy chủ vẫn kiểm tra lại
 * toàn bộ hợp đồng; hàm này chỉ tránh việc âm thầm bỏ qua giá trị lỗi.
 */
export function validateCalibrationValues(catalogKey: CalibrationCatalogKey, values: Record<string, string>): string | undefined {
  const requiredText = (key: string): string | undefined => {
    if (!values[key]?.trim()) return `Hãy nhập ${calibrationFieldLabels[key] ?? key}.`
    return undefined
  }
  const requiredNumber = (key: string, minimum?: number): string | undefined => {
    const value = calibrationNumber(values[key])
    if (value === undefined) return `Hãy nhập ${calibrationFieldLabels[key] ?? key} bằng số hợp lệ.`
    if (minimum !== undefined && value < minimum) return `${calibrationFieldLabels[key] ?? key} phải lớn hơn hoặc bằng ${minimum}.`
    return undefined
  }
  const requiredReadings = (key: string): string | undefined => {
    if (!calibrationReadings(values[key])?.length) return `Hãy nhập ${calibrationFieldLabels[key] ?? key} bằng một hoặc nhiều số, cách nhau bằng dấu phẩy.`
    return undefined
  }
  const firstError = (...errors: Array<string | undefined>): string | undefined => errors.find((error): error is string => Boolean(error))

  const commonError = firstError(
    requiredText('institution'),
    requiredText('physicist'),
    requiredText('unit'),
    requiredText('measurement_date'),
    requiredText('electrometer'),
    requiredText('chamber'),
    requiredText('energy'),
    requiredNumber('temp'),
    requiredNumber('press', 0),
    requiredNumber('n_dw', 0),
    requiredNumber(calibrationCoefficientKey(catalogKey), 0),
    requiredNumber('voltage_reference', 1),
    requiredNumber('voltage_reduced', 1),
    requiredReadings('m_reference'),
    requiredReadings('m_opposite'),
    requiredReadings('m_reduced'),
    requiredNumber('mu', 1),
  )
  if (commonError) return commonError

  if (catalogKey.startsWith('CALIBRATION_TG51_') && requiredNumber('energy', 1)) return requiredNumber('energy', 1)
  if (catalogKey === 'CALIBRATION_TG51_PHOTON') return firstError(requiredNumber('measured_pdd10', 0), requiredNumber('clinical_pdd10', 0))
  if (catalogKey === 'CALIBRATION_TG51_ELECTRON_LEGACY') return firstError(requiredNumber('k_ecal', 0), requiredNumber('clinical_pdd', 0), requiredNumber('i_50', 0), requiredReadings('m_gradient'), requiredText('cone'))
  if (catalogKey === 'CALIBRATION_TG51_ELECTRON_MODERN') return firstError(requiredNumber('clinical_pdd', 0), requiredNumber('i_50', 0), requiredText('cone'), requiredNumber('tissue_correction', 0))
  if (catalogKey === 'CALIBRATION_TRS398_PHOTON') {
    const pddOrTmr = calibrationNumber(values.clinical_pdd_zref) !== undefined || calibrationNumber(values.clinical_tmr_zref) !== undefined
    if (!pddOrTmr) return 'Hãy nhập PDD hoặc TMR tại độ sâu tham chiếu bằng số hợp lệ.'
    return firstError(requiredText('setup'), requiredNumber('tpr2010', 0))
  }
  return firstError(requiredNumber('i_50', 0), requiredNumber('clinical_pdd_zref', 0), requiredNumber('tissue_correction', 0), requiredText('cone'))
}
