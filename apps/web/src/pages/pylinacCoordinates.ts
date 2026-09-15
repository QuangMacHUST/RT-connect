export function mapImagePoint(
  clientX: number,
  clientY: number,
  bounds: { left: number; top: number; width: number; height: number },
  naturalWidth: number,
  naturalHeight: number,
  coordinateMode: 'PIXEL' | 'NORMALIZED' = 'PIXEL',
): { x: string; y: string } | undefined {
  if (!bounds.width || !bounds.height || !naturalWidth || !naturalHeight) return undefined
  const pixelX = Math.max(0, Math.min(naturalWidth, (clientX - bounds.left) * naturalWidth / bounds.width))
  const pixelY = Math.max(0, Math.min(naturalHeight, (clientY - bounds.top) * naturalHeight / bounds.height))
  return coordinateMode === 'NORMALIZED'
    ? { x: (pixelX / naturalWidth).toFixed(4), y: (pixelY / naturalHeight).toFixed(4) }
    : { x: pixelX.toFixed(1), y: pixelY.toFixed(1) }
}
