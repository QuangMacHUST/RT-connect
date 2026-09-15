import type { PylinacQARunResource } from '../api/client'

export function historyForCatalog(
  runs: PylinacQARunResource[] | undefined,
  catalogKey: string,
): PylinacQARunResource[] {
  return (runs ?? []).filter((run) => run.catalog_key === catalogKey)
}
