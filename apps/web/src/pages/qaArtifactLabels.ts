import type { ArtifactResource } from '../api/client'

export type ArtifactLabelSource = Pick<ArtifactResource, 'id' | 'artifact_type' | 'modality' | 'original_filename'>

type ArtifactLabelGroup = 'measurement' | 'dose' | 'structure' | 'ct' | 'plan' | 'archive' | 'log' | 'dicom-image' | 'image' | 'other'

function artifactLabelGroup(artifact: ArtifactLabelSource): ArtifactLabelGroup {
  const filename = artifact.original_filename.toLowerCase()
  if (artifact.artifact_type === 'MEASUREMENT') return 'measurement'
  if (filename.endsWith('.zip')) return 'archive'
  if (['.dlg', '.bin', '.tlog', '.txt'].some((suffix) => filename.endsWith(suffix))) return 'log'
  if (artifact.modality === 'RTDOSE') return 'dose'
  if (artifact.modality === 'RTSTRUCT') return 'structure'
  if (artifact.modality === 'CT') return 'ct'
  if (artifact.modality === 'RTPLAN') return 'plan'
  if (artifact.artifact_type === 'DICOM') return 'dicom-image'
  if (artifact.artifact_type === 'IMAGE') return 'image'
  return 'other'
}

const groupLabels: Record<ArtifactLabelGroup, string> = {
  measurement: 'Số đo',
  dose: 'Tệp liều RTDOSE',
  structure: 'Cấu trúc RT',
  ct: 'Ảnh CT',
  plan: 'Kế hoạch xạ trị',
  archive: 'Bộ ảnh nhiều lớp',
  log: 'Nhật ký máy',
  'dicom-image': 'Ảnh DICOM',
  image: 'Ảnh kiểm tra',
  other: 'Tệp đầu vào'
}

/**
 * Chỉ hiển thị nhãn nghiệp vụ; tên tệp gốc và mã nội bộ không được đưa lên giao diện.
 */
export function artifactDisplayName(artifact: ArtifactLabelSource, artifacts: ArtifactLabelSource[]): string {
  const group = artifactLabelGroup(artifact)
  const sameGroup = artifacts.filter((item) => artifactLabelGroup(item) === group)
  const index = sameGroup.findIndex((item) => item.id === artifact.id)
  const suffix = sameGroup.length > 1 ? ` ${index + 1}` : ''
  return `${groupLabels[group]}${suffix}`
}
