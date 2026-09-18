import { expect, test } from 'vitest'

import {
  reportBlockLabel,
  reportExportLabel,
  reportRunStatusLabel,
  reportSourceLabel,
  reportTemplateStatusLabel
} from './reportBuilderLabels'

test('maps report sources and blocks to Vietnamese labels', () => {
  expect(reportSourceLabel('GAMMA')).toBe('Phân tích PSQA')
  expect(reportBlockLabel('GAMMA_MAP')).toBe('Bản đồ Gamma')
  expect(reportBlockLabel('UNKNOWN')).toBe('Khối nội dung')
})

test('does not expose internal template or export values as user labels', () => {
  expect(reportTemplateStatusLabel('ACTIVE')).toBe('Đang áp dụng')
  expect(reportExportLabel('PDF')).toBe('Tài liệu PDF')
  expect(reportRunStatusLabel('COMPLETED')).toBe('Đã hoàn tất')
  expect(reportRunStatusLabel('UNKNOWN')).toBe('Đã ghi nhận')
})
