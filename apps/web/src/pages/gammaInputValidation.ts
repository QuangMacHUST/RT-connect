import type { ArtifactResource, GammaConfiguration } from '../api/client'

export type GammaInputValidationError = {
  field: string
  message: string
}

type GridGeometry = {
  shape: number[]
  spacing: number[]
  origin: number[]
}

function isFiniteNumber(value: unknown): value is number {
  return typeof value === 'number' && Number.isFinite(value)
}

function numberList(value: unknown): number[] | undefined {
  if (!Array.isArray(value) || !value.every(isFiniteNumber)) return undefined
  return value
}

function positiveIntegerList(value: unknown): number[] | undefined {
  const values = numberList(value)
  if (!values || !values.every((item) => Number.isInteger(item) && item > 0)) return undefined
  return values
}

function geometryOf(artifact: ArtifactResource): GridGeometry | undefined {
  const metadata = artifact.metadata_snapshot
  const rawGrid = metadata.grid
  if (!rawGrid || typeof rawGrid !== 'object' || Array.isArray(rawGrid)) return undefined
  const grid = rawGrid as Record<string, unknown>
  let shape = positiveIntegerList(grid.shape)
  if (!shape && Number.isInteger(grid.rows) && Number.isInteger(grid.columns) && Number(grid.rows) > 0 && Number(grid.columns) > 0) {
    shape = [Number(grid.rows), Number(grid.columns)]
    if (Number.isInteger(grid.frames) && Number(grid.frames) > 1) shape = [Number(grid.frames), ...shape]
  }
  if (!shape) return undefined

  let spacing = numberList(grid.spacing_mm) ?? numberList(metadata.pixel_spacing_mm)
  if (!spacing) return undefined
  if (shape.length === 3 && spacing.length === 2) {
    const offsets = numberList(metadata.grid_frame_offset_vector_mm)
    if (!offsets || offsets.length !== shape[0]) return undefined
    const differences = offsets.slice(1).map((value, index) => value - offsets[index])
    if (!differences.length || differences.some((value) => value <= 0 || !Number.isFinite(value))) return undefined
    if (differences.some((value) => Math.abs(value - differences[0]) > 1e-6)) return undefined
    spacing = [differences[0], ...spacing]
  }
  if (spacing.length !== shape.length || spacing.some((value) => value <= 0)) return undefined

  let origin = numberList(grid.origin_mm) ?? Array.from({ length: shape.length }, () => 0)
  if (!grid.origin_mm && artifact.artifact_type === 'DICOM' && artifact.modality === 'RTDOSE') {
    const position = numberList(metadata.image_position_patient)
    if (!position || position.length !== 3) return undefined
    if (shape.length === 2) origin = [position[1], position[0]]
    if (shape.length === 3) {
      const offsets = numberList(metadata.grid_frame_offset_vector_mm)
      if (!offsets?.length) return undefined
      origin = [position[2] + offsets[0], position[1], position[0]]
    }
  }
  if (origin.length !== shape.length || origin.some((value) => !Number.isFinite(value))) return undefined
  return { shape, spacing, origin }
}

export function validateGammaInputGeometry(
  configuration: Pick<GammaConfiguration, 'dimensionality' | 'distance_to_agreement_mm'>,
  reference: ArtifactResource | undefined,
  evaluation: ArtifactResource | undefined
): GammaInputValidationError[] {
  if (!reference || !evaluation) return []
  const referenceGeometry = geometryOf(reference)
  const evaluationGeometry = geometryOf(evaluation)
  if (!referenceGeometry || !evaluationGeometry) {
    return [{ field: 'grid', message: 'Hai tệp chưa có đủ thông tin hình học để kiểm tra trước khi phân tích.' }]
  }
  const expectedRank = configuration.dimensionality === '1D' ? 1 : 2
  if (referenceGeometry.shape.length !== expectedRank || evaluationGeometry.shape.length !== expectedRank) {
    return [{
      field: 'dimensionality',
      message: configuration.dimensionality === '1D'
        ? 'Gamma một chiều cần hai dãy liều một chiều.'
        : 'Gamma hai chiều cần hai lưới liều hai chiều.'
    }]
  }
  if (referenceGeometry.shape.some((value, index) => value !== evaluationGeometry.shape[index])) {
    return [{ field: 'shape', message: 'Hai lưới liều phải có cùng số hàng và số cột để so sánh an toàn.' }]
  }
  if (referenceGeometry.spacing.some((value, index) => Math.abs(value - evaluationGeometry.spacing[index]) > 1e-6)) {
    return [{ field: 'spacing', message: 'Hai tệp phải có cùng kích thước điểm ảnh để so sánh an toàn.' }]
  }
  if (referenceGeometry.origin.some((value, index) => Math.abs(value - evaluationGeometry.origin[index]) > 1e-6)) {
    return [{ field: 'origin', message: 'Hai tệp phải có cùng gốc tọa độ trong hệ quy chiếu đã kiểm định.' }]
  }
  if (configuration.dimensionality === '2D') {
    const [rowSpacing, columnSpacing] = referenceGeometry.spacing
    if (Math.abs(rowSpacing - columnSpacing) > 1e-6) {
      return [{ field: 'spacing', message: 'Dữ liệu hai chiều cần có điểm ảnh vuông để tính đúng khoảng cách.' }]
    }
    const pixels = configuration.distance_to_agreement_mm / rowSpacing
    if (!Number.isInteger(pixels) || pixels < 1) {
      return [{ field: 'distance_to_agreement_mm', message: 'DTA phải là bội số nguyên của kích thước điểm ảnh đối với Gamma hai chiều.' }]
    }
  }
  return []
}
