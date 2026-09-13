import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { ApiClientError, apiClient, type MachineQAMeasurement, type MachineQARunResource, type QAProtocolResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

type JsonRecord = Record<string, unknown>

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    const messages: Record<string, string> = {
      NETWORK_ERROR: 'Không thể kết nối tới máy chủ. Hãy kiểm tra mạng rồi thử lại.',
      REVISION_CONFLICT: 'Dữ liệu đã thay đổi ở nơi khác. Hãy tải lại rồi thực hiện lại thao tác.',
      RESOURCE_ARCHIVED: 'Mục này đã được lưu trữ. Hãy khôi phục trước khi sửa.',
      MACHINE_QA_RUN_NOT_FOUND: 'Không tìm thấy lượt kiểm tra này.',
      MACHINE_QA_RUN_NOT_EDITABLE: 'Lượt kiểm tra này đã hoàn tất nên không thể sửa số đo.',
      MACHINE_QA_PROTOCOL_NOT_FOUND: 'Không tìm thấy quy trình đánh giá đang chọn.',
      MACHINE_QA_PROTOCOL_INACTIVE: 'Quy trình đánh giá này chưa được kích hoạt.',
      MACHINE_QA_MEASUREMENT_INVALID: 'Số đo chưa hợp lệ. Hãy kiểm tra lại các trường bắt buộc.',
      MACHINE_QA_EVALUATION_FAILED: 'Không thể đánh giá lượt kiểm tra. Hãy kiểm tra số đo rồi thử lại.'
    }
    return messages[error.code] ?? 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối.'
  }
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function records(value: unknown): JsonRecord[] {
  return Array.isArray(value) ? value.filter((item): item is JsonRecord => typeof item === 'object' && item !== null && !Array.isArray(item)) : []
}

function objectValue(value: unknown): JsonRecord | undefined {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as JsonRecord : undefined
}

function textValue(value: unknown, fallback = '—'): string {
  return value === null || value === undefined || value === '' ? fallback : String(value)
}

function statusClass(status: string | null | undefined): string {
  if (status === 'FAIL' || status === 'FAILED') return 'status-badge machine-status--fail'
  if (status === 'WARNING' || status === 'REVIEW' || status === 'NA' || status === 'N/A') return 'status-badge status-badge--warning'
  if (status === 'PASS' || status === 'COMPLETED') return 'status-badge'
  return 'status-badge machine-status--draft'
}

function statusLabel(status: string | null | undefined): string {
  const labels: Record<string, string> = {
    PASS: 'Đạt',
    FAIL: 'Không đạt',
    FAILED: 'Lỗi',
    WARNING: 'Cảnh báo',
    REVIEW: 'Cần xem lại',
    NA: 'Không áp dụng',
    'N/A': 'Không áp dụng',
    DRAFT: 'Bản nháp',
    COMPLETED: 'Đã hoàn tất',
    OPEN: 'Đang mở',
    IN_REVIEW: 'Đang xem lại',
    CANCELLED: 'Đã hủy',
    ACTIVE: 'Đang dùng',
    INACTIVE: 'Không dùng'
  }
  return status ? labels[status] ?? 'Chưa xác định' : '—'
}

function sourceTypeLabel(sourceType: string | null | undefined): string {
  const labels: Record<string, string> = {
    USER_DEFINED: 'Do đơn vị nhập',
    PUBLISHED: 'Tài liệu đã công bố',
    HOSPITAL: 'Tài liệu của bệnh viện',
    PAPER: 'Bài báo chuyên môn',
    SYSTEM: 'Nguồn hệ thống'
  }
  return sourceType ? labels[sourceType] ?? 'Nguồn khác' : 'Chưa khai báo'
}

function formatDate(value: string | null | undefined): string {
  return value ? new Date(value).toLocaleString('vi-VN') : '—'
}

type DraftMeasurementState = {
  values: Record<string, string>
  naFlags: Record<string, boolean>
  naReasons: Record<string, string>
}

function measurementPayload(
  protocol: QAProtocolResource | undefined,
  values: Record<string, string>,
  naFlags: Record<string, boolean>,
  naReasons: Record<string, string>
): MachineQAMeasurement[] {
  if (!protocol) return []
  return protocol.rules.map((rule) => {
    const raw = values[rule.metric_key]?.trim() ?? ''
    const isNotApplicable = naFlags[rule.metric_key] === true
    const parsed = raw === '' || isNotApplicable ? null : Number(raw)
    const reason = naReasons[rule.metric_key]?.trim() ?? ''
    return {
      metric_key: rule.metric_key,
      value: parsed !== null && Number.isFinite(parsed) ? parsed : null,
      unit: rule.unit,
      note: null,
      is_not_applicable: isNotApplicable,
      na_reason: isNotApplicable && reason ? reason : null
    }
  })
}

function draftStateFromRun(run: MachineQARunResource | undefined): DraftMeasurementState {
  const state: DraftMeasurementState = { values: {}, naFlags: {}, naReasons: {} }
  for (const measurement of run?.measurements ?? []) {
    const metricKey = measurement.metric_key
    if (typeof metricKey === 'string' && measurement.value !== null && measurement.value !== undefined) {
      state.values[metricKey] = String(measurement.value)
    }
    if (typeof metricKey === 'string' && measurement.is_not_applicable === true) state.naFlags[metricKey] = true
    if (typeof metricKey === 'string' && typeof measurement.na_reason === 'string') state.naReasons[metricKey] = measurement.na_reason
  }
  return state
}

function ruleDescription(rule: QAProtocolResource['rules'][number]): string {
  if (rule.rule_type === 'RANGE') return `${textValue(rule.lower_limit)} – ${textValue(rule.upper_limit)} ${rule.unit}`
  if (rule.rule_type === 'ABSOLUTE_DEVIATION' || rule.rule_type === 'PERCENT_DEVIATION') {
    return `Đích ${textValue(rule.target_value)} · dung sai ${textValue(rule.tolerance)} ${rule.unit}`
  }
  if (rule.rule_type === 'MAX') return `≤ ${textValue(rule.upper_limit ?? rule.tolerance)} ${rule.unit}`
  if (rule.rule_type === 'MIN') return `≥ ${textValue(rule.lower_limit ?? rule.tolerance)} ${rule.unit}`
  return rule.rule_type
}

export function MachineQAPage() {
  const { caseId } = useParams<{ caseId: string }>()
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const accessToken = session?.access_token
  const bootstrap = useQuery({
    queryKey: ['session', accessToken],
    queryFn: () => apiClient.bootstrap(accessToken!),
    enabled: Boolean(accessToken), retry: false
  })
  const organizationId = bootstrap.data?.organization.id
  const cases = useQuery({
    queryKey: ['qa-case', organizationId, caseId, accessToken],
    queryFn: () => apiClient.qaCases(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId && caseId), retry: false
  })
  const selectedCase = useMemo(
    () => cases.data?.items.find((item) => item.id === caseId),
    [cases.data, caseId]
  )
  const protocols = useQuery({
    queryKey: ['machine-qa-protocols', organizationId, accessToken],
    queryFn: () => apiClient.machineQAProtocols(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const [selectedProtocolId, setSelectedProtocolId] = useState<string>()
  const selectedProtocol = useMemo(
    () => protocols.data?.items.find((item) => item.id === selectedProtocolId) ?? protocols.data?.items[0],
    [protocols.data, selectedProtocolId]
  )
  const runs = useQuery({
    queryKey: ['machine-qa-runs', caseId, accessToken],
    queryFn: () => apiClient.machineQARuns(accessToken!, caseId!),
    enabled: Boolean(accessToken && caseId && selectedCase), retry: false
  })
  const [selectedRunId, setSelectedRunId] = useState<string>()
  const activeRun = useMemo(
    () => runs.data?.items.find((item) => item.id === selectedRunId) ?? runs.data?.items[0],
    [runs.data, selectedRunId]
  )
  // A persisted run owns its protocol snapshot. Do not redraw an existing
  // draft/result with a different library selection.
  const runProtocol = activeRun?.protocol ?? selectedProtocol
  const pinnedProtocolSnapshot = objectValue(activeRun?.result_snapshot.protocol_snapshot)
  const pinnedProtocolSource = objectValue(pinnedProtocolSnapshot?.source)
  const protocolApplicability = pinnedProtocolSnapshot?.applicability ?? runProtocol?.applicability
  const pinnedProtocolRuleCount = Array.isArray(pinnedProtocolSnapshot?.rules) ? pinnedProtocolSnapshot.rules.length : runProtocol?.rules.length ?? 0
  const protocolSourceType = textValue(pinnedProtocolSource?.type ?? runProtocol?.source_type)
  const protocolSourceReference = textValue(pinnedProtocolSource?.reference ?? runProtocol?.source_reference, '')
  const protocolRevision = textValue(pinnedProtocolSnapshot?.revision ?? runProtocol?.revision)
  const protocolApplicabilityLabel = typeof protocolApplicability === 'object' && protocolApplicability !== null && !Array.isArray(protocolApplicability) && Object.keys(protocolApplicability).length
    ? 'Có điều kiện áp dụng'
    : 'Không giới hạn'
  const [draftValues, setDraftValues] = useState<Record<string, string>>({})
  const [draftNaFlags, setDraftNaFlags] = useState<Record<string, boolean>>({})
  const [draftNaReasons, setDraftNaReasons] = useState<Record<string, string>>({})
  const [comparisonRunId, setComparisonRunId] = useState<string>()
  const [message, setMessage] = useState<string>()

  const refreshRuns = () => {
    void queryClient.invalidateQueries({ queryKey: ['machine-qa-runs', caseId, accessToken] })
  }
  const createRunMutation = useMutation({
    mutationFn: (protocolId: string) => apiClient.createMachineQARun(accessToken!, caseId!, protocolId),
    onSuccess: (run) => {
      setSelectedRunId(run.id)
      const draft = draftStateFromRun(run)
      setDraftValues(draft.values)
      setDraftNaFlags(draft.naFlags)
      setDraftNaReasons(draft.naReasons)
      setMessage('Đã tạo lượt kiểm tra chất lượng máy ở trạng thái bản nháp.')
      refreshRuns()
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const saveMutation = useMutation({
    mutationFn: ({ run, measurements }: { run: MachineQARunResource; measurements: MachineQAMeasurement[] }) =>
      apiClient.updateMachineQAMeasurements(accessToken!, run.id, run.measurement_revision, measurements),
    onSuccess: () => { setMessage('Đã lưu số đo vào bản nháp.'); refreshRuns() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const evaluateMutation = useMutation({
    mutationFn: async ({ run, measurements }: { run: MachineQARunResource; measurements: MachineQAMeasurement[] }) => {
      let evaluatedRevision = run.measurement_revision
      if (run.status === 'DRAFT') {
        const saved = await apiClient.updateMachineQAMeasurements(accessToken!, run.id, run.measurement_revision, measurements)
        evaluatedRevision = saved.measurement_revision
      }
      return apiClient.evaluateMachineQARun(accessToken!, run.id, evaluatedRevision)
    },
    onSuccess: (run) => { setSelectedRunId(run.id); setMessage(`Đã đánh giá lượt kiểm tra: ${statusLabel(run.status === 'COMPLETED' ? run.overall_status : run.status)}.`); refreshRuns() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const rerunMutation = useMutation({
    mutationFn: (runId: string) => apiClient.rerunMachineQARun(accessToken!, runId),
    onSuccess: (run) => { setSelectedRunId(run.id); setMessage('Đã tạo lượt đánh giá mới từ kết quả trước; lượt cũ vẫn giữ nguyên.'); refreshRuns() },
    onError: (error) => setMessage(errorMessage(error))
  })
  const comparison = useQuery({
    queryKey: ['machine-qa-compare', activeRun?.id, comparisonRunId, accessToken],
    queryFn: () => apiClient.compareMachineQARuns(accessToken!, activeRun!.id, comparisonRunId!),
    enabled: Boolean(accessToken && activeRun && comparisonRunId && activeRun.id !== comparisonRunId), retry: false
  })

  if (bootstrap.isPending || cases.isPending) return <main className="auth-state">Đang tải bài kiểm tra máy…</main>
  const initialFailure = bootstrap.error ?? cases.error
  if (initialFailure || !organizationId || !caseId) {
    return <div className="page"><section className="alert alert--error"><h1>Không thể mở bài kiểm tra máy</h1><p>{errorMessage(initialFailure)}</p><Link className="button-link" to="/app/qa">Quay lại kho QA</Link></section></div>
  }
  if (!selectedCase) {
    return <div className="page"><section className="alert alert--error"><h1>Không tìm thấy bài kiểm tra</h1><p>Bài này không thuộc đơn vị hiện tại hoặc đã bị lưu trữ.</p><Link className="button-link" to="/app/qa">Quay lại kho QA</Link></section></div>
  }

  const metrics = records(activeRun?.result_snapshot.metrics)
  const runErrors = activeRun?.error_snapshot ?? []
  const compareItems = comparison.data?.items ?? []
  const isBusy = saveMutation.isPending || evaluateMutation.isPending || rerunMutation.isPending || createRunMutation.isPending
  const activeDraft = draftStateFromRun(activeRun)
  const currentDraftValues = Object.keys(draftValues).length ? draftValues : activeDraft.values
  const currentDraftNaFlags = Object.keys(draftNaFlags).length ? draftNaFlags : activeDraft.naFlags
  const currentDraftNaReasons = Object.keys(draftNaReasons).length ? draftNaReasons : activeDraft.naReasons
  const currentMeasurements = measurementPayload(runProtocol, currentDraftValues, currentDraftNaFlags, currentDraftNaReasons)

  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY</p><h1>Nhập số đo và đánh giá</h1><p>{selectedCase.title} · nhập số đo theo quy trình đã chọn và lưu lịch sử kết quả.</p></div>
        <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kho QA</Link><span className="status-badge">ĐANG KẾT NỐI MÁY CHỦ</span></div>
      </header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}

      <section className="panel machine-qa-panel">
        <div className="panel-heading"><div><p className="eyebrow">QUY TRÌNH ĐÁNH GIÁ</p><h2>Quy trình kiểm tra máy</h2></div><strong>{protocols.data?.total ?? '—'}</strong></div>
        {protocols.isPending ? <p>Đang tải quy trình…</p> : protocols.error ? <div className="alert alert--error"><p>{errorMessage(protocols.error)}</p><button onClick={() => void protocols.refetch()}>Thử lại</button></div> : protocols.data?.items.length ? <div className="machine-qa-protocol-controls"><label>Quy trình đang dùng<select disabled={Boolean(activeRun)} value={activeRun?.protocol.id ?? selectedProtocol?.id ?? ''} onChange={(event) => setSelectedProtocolId(event.target.value)}>{protocols.data.items.map((protocol) => <option key={protocol.id} value={protocol.id}>{protocol.name} · bản {protocol.version_number} · {statusLabel(protocol.status)}</option>)}</select></label><p>{runProtocol?.effective_note ?? 'Quy trình được giữ nguyên theo phiên bản khi tạo lượt kiểm tra.'}</p></div> : <div className="empty-state"><p>Đơn vị chưa có quy trình đánh giá đang dùng. Hãy tạo, kiểm tra và kích hoạt một quy trình trước khi mở lượt đo.</p><Link className="button-link button-secondary" to="/app/qa-protocols">Mở thư viện quy trình QA</Link></div>}
        {runProtocol && <div className="machine-qa-protocol-source"><strong>Nguồn và phạm vi áp dụng</strong><span>{sourceTypeLabel(protocolSourceType)}{protocolSourceReference ? ` · ${protocolSourceReference}` : ''}</span><span>Bản {protocolRevision} · {pinnedProtocolRuleCount} tiêu chí · {protocolApplicabilityLabel}</span>{activeRun && <small>Lượt này đã giữ nguyên quy trình tại thời điểm tạo; thay đổi về sau không làm đổi kết quả lịch sử.</small>}</div>}
      </section>

      <section className="panel machine-qa-panel">
        <div className="panel-heading"><div><p className="eyebrow">NHẬP SỐ ĐO</p><h2>Lượt kiểm tra máy</h2></div>{activeRun && <span className={statusClass(activeRun.overall_status ?? activeRun.status)}>{statusLabel(activeRun.overall_status ?? activeRun.status)}</span>}</div>
        {!selectedProtocol ? <p className="empty-state">Hãy tạo và kích hoạt quy trình trong thư viện quy trình QA trước khi tạo lượt đo.</p> : !activeRun ? <div className="empty-state"><p>Chưa có lượt đo cho bài kiểm tra này.</p><button disabled={createRunMutation.isPending} onClick={() => createRunMutation.mutate(selectedProtocol.id)}>{createRunMutation.isPending ? 'Đang tạo…' : 'Tạo lượt đo nháp'}</button></div> : <>
          <div className="machine-qa-run-meta"><span>Lượt đang mở</span><span>Lần chỉnh sửa {activeRun.measurement_revision}</span><span>Tạo lúc {formatDate(activeRun.created_at)}</span>{activeRun.supersedes_run_id && <span>Được tạo từ kết quả trước</span>}</div>
          {activeRun.status === 'DRAFT' && <div className="table-wrap"><table className="machine-qa-table"><thead><tr><th>Chỉ số</th><th>Số đo</th><th>Đơn vị</th><th>Giới hạn</th><th>Không áp dụng và lý do</th><th>Ghi chú</th></tr></thead><tbody>{runProtocol?.rules.map((rule) => { const isNotApplicable = currentDraftNaFlags[rule.metric_key] === true; return <tr key={rule.metric_key}><td><strong>{rule.display_name}</strong>{rule.required && <small className="table-subtitle">Bắt buộc</small>}</td><td><input aria-label={rule.display_name} disabled={isNotApplicable} type="number" step="any" value={currentDraftValues[rule.metric_key] ?? ''} onChange={(event) => setDraftValues((current) => ({ ...current, [rule.metric_key]: event.target.value }))} /></td><td>{rule.unit}</td><td>{ruleDescription(rule)}</td><td><label className="machine-qa-na-control"><input type="checkbox" aria-label={`Đánh dấu ${rule.display_name} là không áp dụng`} checked={isNotApplicable} onChange={(event) => { const checked = event.target.checked; setDraftNaFlags((current) => ({ ...current, [rule.metric_key]: checked })); if (checked) setDraftValues((current) => ({ ...current, [rule.metric_key]: '' })); else setDraftNaReasons((current) => ({ ...current, [rule.metric_key]: '' })) }} /><span>Không áp dụng</span></label>{isNotApplicable && <input aria-label={`Lý do không áp dụng cho ${rule.display_name}`} required value={currentDraftNaReasons[rule.metric_key] ?? ''} onChange={(event) => setDraftNaReasons((current) => ({ ...current, [rule.metric_key]: event.target.value }))} placeholder="Nêu lý do" />}</td><td>{rule.note ?? '—'}</td></tr> })}</tbody></table></div>}
          {activeRun.status === 'DRAFT' && <div className="machine-qa-actions"><button disabled={isBusy} onClick={() => saveMutation.mutate({ run: activeRun, measurements: currentMeasurements })}>Lưu bản nháp</button><button disabled={isBusy} onClick={() => evaluateMutation.mutate({ run: activeRun, measurements: currentMeasurements })}>Đánh giá lượt kiểm tra</button></div>}
          {activeRun.status !== 'DRAFT' && <div className="machine-qa-actions"><button disabled={isBusy} onClick={() => rerunMutation.mutate(activeRun.id)}>Tạo lượt mới từ kết quả này</button></div>}
          {runErrors.length > 0 && <div className="alert alert--error"><h3>Không thể hoàn tất đánh giá</h3><ul>{runErrors.map((item, index) => <li key={`${String(item.code)}-${index}`}>{textValue(item.message, 'Không có mô tả lỗi.')}</li>)}</ul></div>}
          {metrics.length > 0 && <div className="table-wrap"><table className="machine-qa-table"><thead><tr><th>Chỉ số</th><th>Thực tế</th><th>Mốc so sánh</th><th>Khoảng cách</th><th>Đánh giá</th></tr></thead><tbody>{metrics.map((metric, index) => <tr key={`${String(metric.metric_key)}-${index}`}><td><strong>{textValue(metric.display_name, 'Chỉ số')}</strong>{metric.is_not_applicable === true && <small className="table-subtitle">Không áp dụng</small>}{typeof metric.na_reason === 'string' && <small className="table-subtitle">Lý do: {metric.na_reason}</small>}</td><td>{metric.status === 'NA' ? 'Không áp dụng' : `${textValue(metric.actual)} ${textValue(metric.unit, '')}`}</td><td>{textValue(metric.baseline)} {textValue(metric.unit, '')}</td><td>{textValue(metric.margin)}</td><td><span className={statusClass(typeof metric.status === 'string' ? metric.status : undefined)}>{statusLabel(typeof metric.status === 'string' ? metric.status : undefined)}</span></td></tr>)}</tbody></table></div>}
        </>}
      </section>

      <section className="panel machine-qa-panel">
        <div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ KẾT QUẢ</p><h2>Lịch sử và so sánh</h2></div><strong>{runs.data?.total ?? '—'}</strong></div>
        {runs.isPending ? <p>Đang tải lịch sử…</p> : runs.error ? <div className="alert alert--error"><p>{errorMessage(runs.error)}</p><button onClick={() => void runs.refetch()}>Thử lại</button></div> : <>
          {runs.data?.items.length ? <div className="table-wrap"><table><thead><tr><th>Lượt kiểm tra</th><th>Trạng thái</th><th>Kết quả</th><th>Thời điểm</th><th /></tr></thead><tbody>{runs.data.items.map((run, index) => <tr key={run.id}><td><button aria-label={`Mở lượt kiểm tra thứ ${index + 1}`} className={run.id === activeRun?.id ? 'history-button history-button--selected' : 'history-button'} onClick={() => { setSelectedRunId(run.id); const draft = draftStateFromRun(run); setDraftValues(draft.values); setDraftNaFlags(draft.naFlags); setDraftNaReasons(draft.naReasons) }}>Lượt {index + 1}</button></td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td><span className={statusClass(run.overall_status)}>{statusLabel(run.overall_status)}</span></td><td>{formatDate(run.completed_at ?? run.created_at)}</td><td>{run.id !== activeRun?.id && <button className="button-secondary" onClick={() => setComparisonRunId(run.id)}>So sánh</button>}</td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có lịch sử. Tạo lượt đo đầu tiên ở phần trên.</p>}
          {runs.data && runs.data.items.length > 1 && activeRun && <div className="compare-controls"><label>So sánh lượt đang chọn với<select value={comparisonRunId ?? ''} onChange={(event) => setComparisonRunId(event.target.value || undefined)}><option value="">Chọn lượt khác</option>{runs.data.items.filter((run) => run.id !== activeRun.id).map((run, index) => <option key={run.id} value={run.id}>Lượt {index + 1} · {statusLabel(run.overall_status ?? run.status)}</option>)}</select></label>{comparisonRunId && comparison.isPending && <p>Đang tải so sánh…</p>}{comparison.error && <p className="error-text">{errorMessage(comparison.error)}</p>}{compareItems.length > 0 && <div className="table-wrap"><table><thead><tr><th>Chỉ số</th><th>Lượt hiện tại</th><th>Lượt đối chiếu</th></tr></thead><tbody>{compareItems.map((item, index) => <tr key={item.metric_key}><td>Chỉ số {index + 1}</td><td>{textValue(item.left?.actual)} {statusLabel(typeof item.left?.status === 'string' ? item.left.status : undefined)}</td><td>{textValue(item.right?.actual)} {statusLabel(typeof item.right?.status === 'string' ? item.right.status : undefined)}</td></tr>)}</tbody></table></div>}</div>}
        </>}
      </section>
    </div>
  )
}
