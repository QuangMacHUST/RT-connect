import type { QATestDefinitionResource } from '../api/client'

/** Chỉ bài có hợp đồng đầu vào liều mới được mở không gian phân tích liều. */
export function definitionSupportsDoseAnalysis(definition: QATestDefinitionResource | undefined): boolean {
  if (!definition) return false
  return definition.key.startsWith('PSQA_')
    || definition.input_kind.includes('DOSE')
    || definition.required_inputs.some((item) => /rtdose|dose|liều/i.test(item))
}
