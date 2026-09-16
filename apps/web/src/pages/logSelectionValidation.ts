type LogSelectionArtifact = {
  original_filename: string
}

const trajectoryKeys = new Set(['LOG_TRAJECTORY_2_1', 'LOG_TRAJECTORY_3', 'LOG_TRAJECTORY_4'])

function suffix(filename: string): string {
  const dot = filename.lastIndexOf('.')
  return dot >= 0 ? filename.slice(dot).toLowerCase() : ''
}

export function validateLogArtifactSelection(
  catalogKey: string,
  selected: readonly LogSelectionArtifact[],
): string | undefined {
  if (catalogKey === 'LOG_DYNALOG') {
    if (selected.length !== 2) return 'Dynalog cần chọn đúng hai tệp DLG: một tệp A và một tệp B.'
    if (selected.some((item) => suffix(item.original_filename) !== '.dlg')) {
      return 'Dynalog chỉ nhận tệp DLG; không chọn tệp Trajectory hoặc tệp mô tả.'
    }
    const names = selected.map((item) => item.original_filename.trim().toUpperCase())
    const aCount = names.filter((name) => name.startsWith('A')).length
    const bCount = names.filter((name) => name.startsWith('B')).length
    if (aCount !== 1 || bCount !== 1) {
      return 'Dynalog cần đúng một tệp bắt đầu bằng A và một tệp bắt đầu bằng B.'
    }
    return undefined
  }

  if (trajectoryKeys.has(catalogKey)) {
    if (selected.length < 1 || selected.length > 2) return 'Trajectory Log cần một tệp BIN hoặc TLOG, có thể kèm một tệp TXT.'
    const binaries = selected.filter((item) => ['.bin', '.tlog'].includes(suffix(item.original_filename)))
    if (binaries.length !== 1) return 'Trajectory Log cần đúng một tệp BIN hoặc TLOG; tệp thứ hai nếu có phải là TXT.'
    if (selected.some((item) => !['.bin', '.tlog', '.txt'].includes(suffix(item.original_filename)))) {
      return 'Trajectory Log chỉ nhận tệp BIN, TLOG và tệp TXT mô tả.'
    }
  }

  return undefined
}
