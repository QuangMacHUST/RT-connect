export function mapImagePoint(
  clientX: number,
  clientY: number,
  bounds: { left: number; top: number; width: number; height: number },
  naturalWidth: number,
  naturalHeight: number,
  coordinateMode: 'PIXEL' | 'NORMALIZED' | 'OFFSET_MM' = 'PIXEL',
  pixelSpacingMm?: number[],
): { x: string; y: string } | undefined {
  if (!bounds.width || !bounds.height || !naturalWidth || !naturalHeight) return undefined
  const pixelX = Math.max(0, Math.min(naturalWidth, (clientX - bounds.left) * naturalWidth / bounds.width))
  const pixelY = Math.max(0, Math.min(naturalHeight, (clientY - bounds.top) * naturalHeight / bounds.height))
  if (coordinateMode === 'OFFSET_MM') {
    const rowSpacing = pixelSpacingMm?.[0]
    const columnSpacing = pixelSpacingMm?.[1]
    if (!rowSpacing || !columnSpacing || !Number.isFinite(rowSpacing) || !Number.isFinite(columnSpacing)) return undefined
    return {
      x: ((pixelX - naturalWidth / 2) * columnSpacing).toFixed(2),
      y: ((pixelY - naturalHeight / 2) * rowSpacing).toFixed(2),
    }
  }
  return coordinateMode === 'NORMALIZED'
    ? { x: (pixelX / naturalWidth).toFixed(4), y: (pixelY / naturalHeight).toFixed(4) }
    : { x: pixelX.toFixed(1), y: pixelY.toFixed(1) }
}
