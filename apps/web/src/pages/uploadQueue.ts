export type UploadQueueStatus = 'PENDING' | 'UPLOADING' | 'UPLOADED' | 'FAILED'

export type UploadQueueItem = {
  id: string
  caseId: string
  file: File
  artifactType: string
  logicalRole: string
  status: UploadQueueStatus
  error?: string
  duplicate?: boolean
}

type UploadResult = { duplicate?: boolean }

type ProcessUploadQueueOptions = {
  items: readonly UploadQueueItem[]
  caseId: string
  allowedStatuses?: readonly UploadQueueStatus[]
  upload: (item: UploadQueueItem) => Promise<UploadResult>
  update: (itemId: string, patch: Partial<UploadQueueItem>) => void
  formatError: (error: unknown) => string
}

/** Runs a captured queue snapshot in order without removing earlier successes. */
export async function processUploadQueue(options: ProcessUploadQueueOptions): Promise<number> {
  const allowedStatuses = options.allowedStatuses ?? ['PENDING']
  const items = options.items.filter((item) => item.caseId === options.caseId && allowedStatuses.includes(item.status))
  for (const item of items) {
    options.update(item.id, { status: 'UPLOADING', error: undefined })
    try {
      const result = await options.upload(item)
      options.update(item.id, { status: 'UPLOADED', duplicate: result.duplicate })
    } catch (error) {
      options.update(item.id, { status: 'FAILED', error: options.formatError(error) })
    }
  }
  return items.length
}
