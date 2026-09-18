import type { ArtifactResource, GammaConfiguration } from '../api/client'

export type GammaValidationError = {
  field: keyof GammaConfiguration
  message: string
}

export function isGammaWorkflowReady(
  configuration: Pick<GammaConfiguration, 'dimensionality'>,
  reference: ArtifactResource | undefined,
  evaluation: ArtifactResource | undefined
): boolean {
  if (!reference || !evaluation) return false
  if (configuration.dimensionality === '1D') {
    return reference.artifact_type === 'MEASUREMENT' && evaluation.artifact_type === 'MEASUREMENT'
  }
  return reference.artifact_type === 'DICOM' && reference.modality === 'RTDOSE' && (
    evaluation.artifact_type === 'MEASUREMENT' ||
    (evaluation.artifact_type === 'DICOM' && evaluation.modality === 'RTDOSE')
  )
}

function finite(value: number): boolean {
  return Number.isFinite(value)
}

export function validateGammaConfiguration(configuration: GammaConfiguration): GammaValidationError[] {
  const errors: GammaValidationError[] = []
  if (configuration.dimensionality === '3D') {
    errors.push({ field: 'dimensionality', message: 'Phân tích mới chỉ hỗ trợ dữ liệu một chiều hoặc hai chiều.' })
  }
  if (!finite(configuration.dose_difference_percent) || configuration.dose_difference_percent <= 0 || configuration.dose_difference_percent > 100) {
    errors.push({ field: 'dose_difference_percent', message: 'Chênh lệch liều phải lớn hơn 0 và không vượt quá 100%.' })
  }
  if (!finite(configuration.distance_to_agreement_mm) || configuration.distance_to_agreement_mm <= 0) {
    errors.push({ field: 'distance_to_agreement_mm', message: 'DTA phải là số lớn hơn 0 mm.' })
  }
  if (!finite(configuration.dose_threshold_percent) || configuration.dose_threshold_percent < 0 || configuration.dose_threshold_percent > 100) {
    errors.push({ field: 'dose_threshold_percent', message: 'Ngưỡng liều thấp phải nằm trong khoảng từ 0 đến 100%.' })
  }
  if (!finite(configuration.pass_rate_threshold_percent) || configuration.pass_rate_threshold_percent < 0 || configuration.pass_rate_threshold_percent > 100) {
    errors.push({ field: 'pass_rate_threshold_percent', message: 'Ngưỡng đạt phải nằm trong khoảng từ 0 đến 100%.' })
  }
  if (!finite(configuration.max_gamma) || configuration.max_gamma < 1 || configuration.max_gamma > 10) {
    errors.push({ field: 'max_gamma', message: 'Giới hạn Gamma phải nằm trong khoảng từ 1 đến 10.' })
  }
  if (!Number.isInteger(configuration.histogram_bins) || configuration.histogram_bins < 2 || configuration.histogram_bins > 100) {
    errors.push({ field: 'histogram_bins', message: 'Số khoảng biểu đồ phải là số nguyên từ 2 đến 100.' })
  }
  if (!Number.isInteger(configuration.resolution_factor) || configuration.resolution_factor < 1 || configuration.resolution_factor > 10) {
    errors.push({ field: 'resolution_factor', message: 'Hệ số tinh chỉnh một chiều phải là số nguyên từ 1 đến 10.' })
  }
  return errors
}
