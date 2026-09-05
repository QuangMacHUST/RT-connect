export type RouteDefinition = {
  path: string
  label: string
  module: string
  phase: string
  nav: 'workspace' | 'biological' | 'system'
}

// This is the source counterpart of docs/route-registry.md. Only P1 routes render today.
export const routeRegistry: readonly RouteDefinition[] = [
  { path: '/app', label: 'Trang chủ', module: 'MOD-01', phase: 'P3', nav: 'workspace' },
  { path: '/app/qa', label: 'Kho lưu trữ QA', module: 'MOD-03', phase: 'P5', nav: 'workspace' },
  { path: '/app/qa-protocols', label: 'QA Protocols', module: 'MOD-09', phase: 'P11', nav: 'workspace' },
  { path: '/app/trend', label: 'Xu hướng', module: 'MOD-08', phase: 'P10', nav: 'workspace' },
  { path: '/app/biological', label: 'Biological Toolkit', module: 'MOD-10', phase: 'P12', nav: 'biological' },
  { path: '/app/biological/bed-eqd2', label: 'BED & EQD2', module: 'MOD-11', phase: 'P13', nav: 'biological' },
  { path: '/app/biological/compare', label: 'So sánh phác đồ', module: 'MOD-12', phase: 'P14', nav: 'biological' },
  { path: '/app/biological/re-irradiation', label: 'Tái xạ', module: 'MOD-13', phase: 'P15', nav: 'biological' },
  { path: '/app/system/status', label: 'Trạng thái hệ thống', module: 'MOD-16', phase: 'P1', nav: 'system' }
]
