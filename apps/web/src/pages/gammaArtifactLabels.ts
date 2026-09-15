import type { ArtifactResource } from '../api/client'

export function artifactDisplayName(artifact: ArtifactResource, artifacts: ArtifactResource[]): string {
  const sameKind = artifacts.filter((item) =>
    item.artifact_type === artifact.artifact_type && item.modality === artifact.modality
  )
  const index = sameKind.findIndex((item) => item.id === artifact.id)
  const suffix = sameKind.length > 1 ? ` ${index + 1}` : ''
  if (artifact.artifact_type === 'MEASUREMENT') return `Dữ liệu đo liều${suffix}`
  if (artifact.artifact_type === 'DICOM' && artifact.modality === 'RTDOSE') return `Tệp liều RTDOSE${suffix}`
  return 'Dữ liệu phân tích'
}
