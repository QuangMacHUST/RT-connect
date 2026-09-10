import { expect, test } from 'vitest'

import { processUploadQueue, type UploadQueueItem } from './uploadQueue'

function item(id: string, caseId = 'case-a', status: UploadQueueItem['status'] = 'PENDING'): UploadQueueItem {
  return {
    id,
    caseId,
    file: new File([id], `${id}.dcm`, { type: 'application/dicom' }),
    artifactType: 'DICOM',
    logicalRole: 'REFERENCE',
    status
  }
}

test('processes a captured queue sequentially and preserves earlier success on later failure', async () => {
  const updates: Record<string, Partial<UploadQueueItem>> = {}
  const order: string[] = []
  const processed = await processUploadQueue({
    items: [item('first'), item('second')],
    caseId: 'case-a',
    upload: async (candidate) => {
      order.push(candidate.id)
      if (candidate.id === 'second') throw new Error('temporary storage failure')
      return { duplicate: true }
    },
    update: (id, patch) => { updates[id] = { ...updates[id], ...patch } },
    formatError: (error) => error instanceof Error ? error.message : 'unknown error'
  })

  expect(processed).toBe(2)
  expect(order).toEqual(['first', 'second'])
  expect(updates.first).toMatchObject({ status: 'UPLOADED', duplicate: true })
  expect(updates.second).toMatchObject({ status: 'FAILED', error: 'temporary storage failure' })
})

test('retry mode processes only failed items in the selected case', async () => {
  const updates: Record<string, Partial<UploadQueueItem>> = {}
  const uploaded: string[] = []
  const processed = await processUploadQueue({
    items: [item('failed-target', 'case-a', 'FAILED'), item('still-pending', 'case-a'), item('failed-other-case', 'case-b', 'FAILED')],
    caseId: 'case-a',
    allowedStatuses: ['FAILED'],
    upload: async (candidate) => { uploaded.push(candidate.id); return { duplicate: false } },
    update: (id, patch) => { updates[id] = { ...updates[id], ...patch } },
    formatError: () => 'unreachable'
  })

  expect(processed).toBe(1)
  expect(uploaded).toEqual(['failed-target'])
  expect(updates['still-pending']).toBeUndefined()
  expect(updates['failed-other-case']).toBeUndefined()
  expect(updates['failed-target']).toMatchObject({ status: 'UPLOADED', duplicate: false })
})
