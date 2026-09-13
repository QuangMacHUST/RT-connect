export type RouteDefinition = {
  path: string
  label: string
  module: string
  phase: string
  nav: 'workspace' | 'biological' | 'system'
  available: boolean
  showInSidebar?: boolean
}

// This is the source counterpart of docs/route-registry.md. Routes become active only
// after their API contract and focused tests are present.
export const routeRegistry: readonly RouteDefinition[] = [
  { path: '/invite', label: 'Nhận lời mời', module: 'MOD-02', phase: 'P4', nav: 'workspace', available: true, showInSidebar: false },
  { path: '/app', label: 'Trang chủ', module: 'MOD-01', phase: 'P3', nav: 'workspace', available: true },
  { path: '/app/organization', label: 'Đơn vị và thiết bị', module: 'MOD-02', phase: 'P4', nav: 'workspace', available: true },
  { path: '/app/qa', label: 'QA máy', module: 'MOD-03', phase: 'P5', nav: 'workspace', available: true },
  { path: '/app/qa/cases/:caseId/dvh', label: 'Visual Dose / DVH', module: 'MOD-15', phase: 'P17', nav: 'workspace', available: true, showInSidebar: false },
  { path: '/app/reports', label: 'Biên soạn báo cáo', module: 'MOD-07', phase: 'P9', nav: 'workspace', available: true, showInSidebar: false },
  { path: '/app/qa-protocols', label: 'Tài liệu QA máy', module: 'MOD-09', phase: 'P11', nav: 'workspace', available: true, showInSidebar: false },
  { path: '/app/trend', label: 'Xu hướng QA', module: 'MOD-08', phase: 'P10', nav: 'workspace', available: true, showInSidebar: false },
  { path: '/app/biological', label: 'Công cụ sinh học', module: 'MOD-10', phase: 'P12', nav: 'biological', available: true },
  { path: '/app/biological/bed-eqd2', label: 'BED và EQD2', module: 'MOD-11', phase: 'P13', nav: 'biological', available: true, showInSidebar: false },
  { path: '/app/biological/compare', label: 'So sánh phác đồ', module: 'MOD-12', phase: 'P14', nav: 'biological', available: true, showInSidebar: false },
  { path: '/app/biological/re-irradiation', label: 'Tái xạ', module: 'MOD-13', phase: 'P15', nav: 'biological', available: true },
  { path: '/app/biological/fraction-compensation', label: 'Bù phân liều', module: 'MOD-13', phase: 'P15', nav: 'biological', available: true, showInSidebar: false },
  { path: '/app/knowledge', label: 'Thư viện kiến thức', module: 'MOD-14', phase: 'P16', nav: 'workspace', available: true },
  { path: '/app/biological/knowledge', label: 'Thư viện kiến thức', module: 'MOD-14', phase: 'P16', nav: 'workspace', available: true, showInSidebar: false },
  { path: '/app/system/status', label: 'Trạng thái dịch vụ', module: 'MOD-16', phase: 'P1', nav: 'system', available: true, showInSidebar: false }
]
