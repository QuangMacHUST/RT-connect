type NuclearValidationValues = Record<string, string>

function parseFinite(value: string): number | undefined {
  const parsed = Number(value.trim())
  return value.trim() && Number.isFinite(parsed) ? parsed : undefined
}

function numberAtLeast(values: NuclearValidationValues, key: string, label: string, minimum: number): string | undefined {
  const parsed = parseFinite(values[key] ?? '')
  return parsed === undefined || parsed < minimum ? `${label} phải là số từ ${minimum} trở lên.` : undefined
}

function ratio(values: NuclearValidationValues, key: string, label: string): string | undefined {
  const parsed = parseFinite(values[key] ?? '')
  return parsed === undefined || parsed <= 0 || parsed > 1 ? `${label} phải lớn hơn 0 và không vượt quá 1.` : undefined
}

function listOf(values: NuclearValidationValues, key: string, count: number, label: string, minimum: number, allowNegative = false): string | undefined {
  const entries = (values[key] ?? '').split(',').map((entry) => entry.trim()).filter(Boolean)
  if (entries.length !== count) return `${label} phải gồm đúng ${count} giá trị, ngăn cách bằng dấu phẩy.`
  const numbers = entries.map(parseFinite)
  if (numbers.some((value) => value === undefined || (!allowNegative && value < minimum))) {
    return `${label} phải gồm các số hợp lệ${allowNegative ? '' : ` từ ${minimum} trở lên`}.`
  }
  return undefined
}

export function validateNuclearValues(catalogKey: string, values: NuclearValidationValues): string | undefined {
  if (catalogKey === 'NUCLEAR_MCR') return numberAtLeast(values, 'frame_duration', 'Thời lượng mỗi khung hình', 0.000001)

  if (catalogKey === 'NUCLEAR_PU') {
    return ratio(values, 'ufov_ratio', 'Tỷ lệ vùng nhìn hữu ích')
      ?? ratio(values, 'cfov_ratio', 'Tỷ lệ vùng nhìn trung tâm')
      ?? numberAtLeast(values, 'window_size', 'Kích thước cửa sổ', 1)
      ?? ratio(values, 'threshold', 'Ngưỡng loại nền')
  }

  if (catalogKey === 'NUCLEAR_SS') {
    return numberAtLeast(values, 'activity_mbq', 'Hoạt độ', 0.000001)
      ?? (values.nuclide?.trim() ? undefined : 'Đồng vị không được để trống.')
  }

  if (catalogKey === 'NUCLEAR_FBR') {
    return numberAtLeast(values, 'separation_mm', 'Khoảng cách hai vạch', 0.000001)
      ?? numberAtLeast(values, 'roi_width_mm', 'Bề rộng vùng quan tâm', 0.000001)
  }

  if (catalogKey === 'NUCLEAR_QR') {
    return listOf(values, 'bar_widths', 4, 'Bề rộng bốn vạch', 0.000001)
      ?? numberAtLeast(values, 'roi_diameter_mm', 'Đường kính vùng quan tâm', 0.000001)
      ?? numberAtLeast(values, 'distance_from_center_mm', 'Khoảng cách đến tâm', 0)
  }

  if (catalogKey === 'NUCLEAR_TU') {
    const firstFrame = parseFinite(values.first_frame ?? '')
    const lastFrame = parseFinite(values.last_frame ?? '')
    if (firstFrame === undefined || !Number.isInteger(firstFrame) || firstFrame < 0) return 'Khung hình bắt đầu phải là số nguyên từ 0 trở lên.'
    if (lastFrame === undefined || !Number.isInteger(lastFrame) || lastFrame < -1) return 'Khung hình kết thúc phải là số nguyên từ -1 trở lên.'
    if (lastFrame !== -1 && lastFrame < firstFrame) return 'Khung hình kết thúc phải lớn hơn hoặc bằng khung hình bắt đầu hoặc là -1.'
    return ratio(values, 'ufov_ratio', 'Tỷ lệ vùng nhìn hữu ích')
      ?? ratio(values, 'cfov_ratio', 'Tỷ lệ vùng nhìn trung tâm')
      ?? ratio(values, 'center_ratio', 'Tỷ lệ vùng tâm')
      ?? ratio(values, 'threshold', 'Ngưỡng loại nền')
      ?? numberAtLeast(values, 'window_size', 'Kích thước cửa sổ', 1)
  }

  if (catalogKey === 'NUCLEAR_TC') {
    return listOf(values, 'sphere_diameters_mm', 6, 'Đường kính sáu cầu', 0.000001)
      ?? listOf(values, 'sphere_angles', 6, 'Góc sáu cầu', 0, true)
      ?? ratio(values, 'ufov_ratio', 'Tỷ lệ vùng nhìn hữu ích')
      ?? numberAtLeast(values, 'search_window_px', 'Cửa sổ tìm kiếm', 1)
      ?? numberAtLeast(values, 'search_slices', 'Số lát tìm kiếm', 1)
  }

  return undefined
}
