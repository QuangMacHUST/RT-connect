import type { ArtifactResource } from '../api/client'

export type DvhArtifactSummary = {
  dose: number
  structure: number
  ct: number
  ready: boolean
}

export function dvhArtifactStatusLabel(
  summary: DvhArtifactSummary,
  state: 'loading' | 'error' | 'ready'
): string {
  if (state === 'loading') return 'Đang kiểm tra tệp cho phân tích liều…'
  if (state === 'error') return 'Chưa đọc được tệp cho phân tích liều'
  return `Phân tích liều: ${summary.dose} RTDOSE · ${summary.structure} RTSTRUCT · ${summary.ct} CT hợp lệ`
}

/** Summarize only selectable DICOM inputs; invalid or non-DICOM rows cannot satisfy DVH preflight. */
export function summarizeDvhArtifacts(
  items: Pick<ArtifactResource, 'artifact_type' | 'modality' | 'data_status'>[] | undefined
): DvhArtifactSummary {
  const validDicom = (items ?? []).filter((item) => item.artifact_type === 'DICOM' && item.data_status === 'VALID')
  const dose = validDicom.filter((item) => item.modality === 'RTDOSE').length
  const structure = validDicom.filter((item) => item.modality === 'RTSTRUCT').length
  const ct = validDicom.filter((item) => item.modality === 'CT').length
  return { dose, structure, ct, ready: dose > 0 && structure > 0 }
}
