export function isCaseInArchiveView(isArchived: boolean, showTrash: boolean): boolean {
  return isArchived === showTrash
}

export function toggleCaseSelection(selectedIds: string[], caseId: string): string[] {
  return selectedIds.includes(caseId)
    ? selectedIds.filter((id) => id !== caseId)
    : [...selectedIds, caseId]
}

export function toggleAllVisibleCaseSelection(selectedIds: string[], visibleIds: string[]): string[] {
  const allSelected = visibleIds.length > 0 && visibleIds.every((id) => selectedIds.includes(id))
  return allSelected
    ? selectedIds.filter((id) => !visibleIds.includes(id))
    : Array.from(new Set([...selectedIds, ...visibleIds]))
}
