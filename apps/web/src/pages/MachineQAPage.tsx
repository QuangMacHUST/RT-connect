import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'

import { ApiClientError, apiClient, type MachineQAMeasurement, type MachineQARunResource, type PylinacQARunResource, type QAProtocolResource } from '../api/client'
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
      MACHINE_QA_EVALUATION_FAILED: 'Không thể đánh giá lượt kiểm tra. Hãy kiểm tra số đo rồi thử lại.',
      PYLINAC_INPUT_NOT_FOUND: 'Không tìm thấy tệp đầu vào trong bài kiểm tra này.',
      PYLINAC_INPUT_COUNT_INVALID: 'Số lượng tệp đầu vào chưa đúng với bài kiểm tra.',
      PYLINAC_INPUT_FORMAT_INVALID: 'Định dạng tệp chưa đúng với bài kiểm tra. Hãy chọn đúng tệp được yêu cầu.',
      PYLINAC_EXECUTION_FAILED: 'Bộ tính Pylinac không thể phân tích tệp này. Hãy kiểm tra tệp rồi thử lại.',
      PYLINAC_INPUT_NOT_AVAILABLE: 'Không thể đọc tệp từ kho lưu trữ. Hãy thử lại sau.',
      PYLINAC_PARAMETER_INVALID: 'Tham số chưa hợp lệ. Hãy kiểm tra lại các trường nhập.',
      PYLINAC_PARAMETER_UNSUPPORTED: 'Bài QA này không hỗ trợ một trong các tham số đã chọn.',
      PYLINAC_RUNTIME_UNAVAILABLE: 'Bộ tính Pylinac hiện chưa sẵn sàng trên máy chủ.',
      PYLINAC_ADAPTER_NOT_READY: 'Bài QA này đang được hoàn thiện giao diện phân tích.',
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

function pylinacMetric(value: PylinacQARunResource | undefined, key: string): unknown {
  const metrics = objectValue(value?.result_snapshot.metrics)
  return metrics?.[key]
}

function PicketFencePage({ caseId, accessToken, title }: { caseId: string; accessToken: string; title: string }) {
  const queryClient = useQueryClient()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string>()
  const [tolerance, setTolerance] = useState('0.5')
  const [cropMm, setCropMm] = useState('3')
  const [mlc, setMlc] = useState('Millennium')
  const [message, setMessage] = useState<string>()
  const artifacts = useQuery({
    queryKey: ['pylinac-artifacts', caseId, accessToken],
    queryFn: () => apiClient.artifacts(accessToken, caseId), retry: false
  })
  const runs = useQuery({
    queryKey: ['pylinac-runs', caseId, accessToken],
    queryFn: () => apiClient.pylinacQARuns(accessToken, caseId), retry: false
  })
  const upload = useMutation({
    mutationFn: (file: File) => apiClient.uploadArtifact(accessToken, caseId, file, 'DICOM', 'EVALUATION'),
    onSuccess: (artifact) => {
      setSelectedArtifactId(artifact.id)
      setMessage('Đã tải tệp ảnh lên; có thể bắt đầu phân tích.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-artifacts', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const analyze = useMutation({
    mutationFn: () => apiClient.createPylinacQARun(accessToken, caseId, {
      catalog_key: 'PICKET_FENCE',
      artifact_ids: [selectedArtifactId!],
      parameters: { tolerance: Number(tolerance), crop_mm: Number(cropMm), mlc }
    }),
    onSuccess: (run) => {
      setMessage(run.status === 'COMPLETED' ? 'Đã phân tích Picket Fence bằng Pylinac.' : 'Pylinac không thể hoàn tất phân tích; hãy xem thông báo lỗi bên dưới.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const assess = useMutation({
    mutationFn: ({ runId, value }: { runId: string; value: 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' }) => apiClient.assessPylinacQARun(accessToken, runId, value),
    onSuccess: () => { setMessage('Đã lưu đánh giá của người dùng.'); void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const imageArtifacts = (artifacts.data?.items ?? []).filter((item) => item.artifact_type === 'DICOM' || item.artifact_type === 'IMAGE')
  const selected = imageArtifacts.find((item) => item.id === selectedArtifactId) ?? imageArtifacts[0]
  const history = runs.data?.items ?? []
  const latest = history[0]
  const isBusy = upload.isPending || analyze.isPending || assess.isPending

  return <div className="page">
    <header className="page-header">
      <div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY · PYLİNAC</p><h1>Kiểm tra hàng rào lá</h1><p>{title} · tải ảnh lên, chọn tham số và lưu kết quả phân tích.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kho QA</Link><span className="status-badge">BỘ TÍNH PYLINAC 3.47.0</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="panel machine-qa-panel">
      <div className="panel-heading"><div><p className="eyebrow">TỆP ĐẦU VÀO</p><h2>Ảnh Picket Fence</h2></div><strong>{imageArtifacts.length}</strong></div>
      <p>Chỉ phần bài QA cần ảnh mới hiện khu vực tải tệp. Ảnh gốc được giữ nguyên; Pylinac chịu trách nhiệm toàn bộ phép phân tích.</p>
      <div className="machine-qa-actions"><label className="button-link">Chọn ảnh DICOM<input type="file" accept=".dcm,application/dicom" hidden disabled={isBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.currentTarget.value = '' }} /></label></div>
      {imageArtifacts.length > 0 && <label>Ảnh đang dùng<select value={selected?.id ?? ''} onChange={(event) => setSelectedArtifactId(event.target.value)}>{imageArtifacts.map((artifact, index) => <option key={artifact.id} value={artifact.id}>Ảnh {index + 1} · {artifact.original_filename}</option>)}</select></label>}
      <div className="machine-qa-protocol-controls"><label>Dung sai (mm)<input type="number" min="0" step="0.01" value={tolerance} onChange={(event) => setTolerance(event.target.value)} /></label><label>Mẫu MLC<select value={mlc} onChange={(event) => setMlc(event.target.value)}><option value="Millennium">Millennium</option><option value="HD120">HD120</option><option value="Agility">Agility</option><option value="Halcyon">Halcyon</option></select></label><label>Cắt ảnh (mm)<input type="number" min="0" step="1" value={cropMm} onChange={(event) => setCropMm(event.target.value)} /></label></div>
      <div className="machine-qa-actions"><button disabled={!selected || isBusy} onClick={() => analyze.mutate()}>{analyze.isPending ? 'Đang phân tích…' : 'Bắt đầu phân tích'}</button></div>
    </section>
    {latest && <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ MỚI NHẤT</p><h2>{latest.name}</h2></div><span className={statusClass(latest.status)}>{statusLabel(latest.status)}</span></div>{latest.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Không thể phân tích</h3><ul>{latest.error_snapshot.map((item, index) => <li key={index}>{textValue(item.message, 'Đã xảy ra lỗi trong bộ tính.')}</li>)}</ul></div>}{latest.status === 'COMPLETED' && <><div className="machine-qa-run-meta"><span>Độ chính xác lá đạt: {textValue(pylinacMetric(latest, 'percent_leaves_passing'))}%</span><span>Số vạch: {textValue(pylinacMetric(latest, 'number_of_pickets'))}</span><span>Sai lệch lớn nhất: {textValue(pylinacMetric(latest, 'max_error_mm'))} mm</span></div>{latest.overlay_artifact_id && <button className="button-secondary" onClick={() => { void apiClient.downloadArtifact(accessToken, latest.overlay_artifact_id!).then((download) => window.open(download.url, '_blank', 'noopener,noreferrer')).catch((error) => setMessage(errorMessage(error))) }}>Mở ảnh phân tích</button>}<label>Đánh giá của người dùng<select value={latest.assessment_status ?? 'NOT_ASSESSED'} onChange={(event) => assess.mutate({ runId: latest.id, value: event.target.value as 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' })}><option value="NOT_ASSESSED">Chưa đánh giá</option><option value="PASS">Đạt</option><option value="WARNING">Cảnh báo</option><option value="REVIEW">Cần xem lại</option><option value="FAIL">Không đạt</option></select></label></>}</section>}
    <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ PHÂN TÍCH</p><h2>Kết quả đã lưu</h2></div><strong>{history.length}</strong></div>{history.length === 0 ? <p className="empty-state">Chưa có kết quả Picket Fence.</p> : <div className="table-wrap"><table><thead><tr><th>Lần phân tích</th><th>Trạng thái</th><th>Đánh giá</th><th>Thời điểm</th></tr></thead><tbody>{history.map((run, index) => <tr key={run.id}><td>Lần {history.length - index}</td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td>{statusLabel(run.assessment_status)}</td><td>{formatDate(run.completed_at ?? run.created_at)}</td></tr>)}</tbody></table></div>}</section>
  </div>
}

function StarshotPage({ caseId, accessToken, title }: { caseId: string; accessToken: string; title: string }) {
  const queryClient = useQueryClient()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string>()
  const [sid, setSid] = useState('1000')
  const [dpi, setDpi] = useState('')
  const [radius, setRadius] = useState('0.85')
  const [tolerance, setTolerance] = useState('1')
  const [startX, setStartX] = useState('')
  const [startY, setStartY] = useState('')
  const [message, setMessage] = useState<string>()
  const artifacts = useQuery({
    queryKey: ['pylinac-artifacts', caseId, accessToken],
    queryFn: () => apiClient.artifacts(accessToken, caseId), retry: false
  })
  const runs = useQuery({
    queryKey: ['pylinac-runs', caseId, accessToken],
    queryFn: () => apiClient.pylinacQARuns(accessToken, caseId), retry: false
  })
  const upload = useMutation({
    mutationFn: (file: File) => apiClient.uploadArtifact(accessToken, caseId, file, 'IMAGE', 'EVALUATION'),
    onSuccess: (artifact) => {
      setSelectedArtifactId(artifact.id)
      setMessage('Đã tải ảnh kiểm tra sao lên; có thể bắt đầu phân tích.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-artifacts', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const analyze = useMutation({
    mutationFn: () => {
      const parameters: Record<string, unknown> = {
        sid: Number(sid), radius: Number(radius), tolerance: Number(tolerance)
      }
      if (dpi.trim()) parameters.dpi = Number(dpi)
      if (startX.trim() || startY.trim()) parameters.start_point = { x: Number(startX), y: Number(startY) }
      return apiClient.createPylinacQARun(accessToken, caseId, {
        catalog_key: 'STARSHOT', artifact_ids: [selectedArtifactId!], parameters
      })
    },
    onSuccess: (run) => {
      setMessage(run.status === 'COMPLETED' ? 'Đã phân tích kiểm tra sao bằng Pylinac.' : 'Pylinac không thể hoàn tất phân tích; hãy xem thông báo lỗi bên dưới.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const assess = useMutation({
    mutationFn: ({ runId, value }: { runId: string; value: 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' }) => apiClient.assessPylinacQARun(accessToken, runId, value),
    onSuccess: () => { setMessage('Đã lưu đánh giá của người dùng.'); void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const imageArtifacts = (artifacts.data?.items ?? []).filter((item) => item.artifact_type === 'DICOM' || item.artifact_type === 'IMAGE')
  const selected = imageArtifacts.find((item) => item.id === selectedArtifactId) ?? imageArtifacts[0]
  const history = runs.data?.items ?? []
  const latest = history[0]
  const isBusy = upload.isPending || analyze.isPending || assess.isPending
  const center = pylinacMetric(latest, 'circle_center_x_y')

  return <div className="page">
    <header className="page-header">
      <div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY · Pylinac</p><h1>Kiểm tra sao</h1><p>{title} · chọn tâm phân tích, theo dõi độ lệch và lưu lịch sử kết quả.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kho QA</Link><span className="status-badge">BỘ TÍNH Pylinac 3.47.0</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="panel machine-qa-panel">
      <div className="panel-heading"><div><p className="eyebrow">TỆP ĐẦU VÀO</p><h2>Ảnh kiểm tra sao</h2></div><strong>{imageArtifacts.length}</strong></div>
      <p>Khu vực tệp chỉ hiện vì bài này cần ảnh. Có thể để Pylinac tự tìm tâm hoặc nhập tâm bắt đầu đã chọn trên ảnh để chạy lại một phiên bản mới.</p>
      <div className="machine-qa-actions"><label className="button-link">Chọn ảnh DICOM hoặc ảnh đo<input type="file" accept=".dcm,.tif,.tiff,.png,.jpg,.jpeg,application/dicom,image/*" hidden disabled={isBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.currentTarget.value = '' }} /></label></div>
      {imageArtifacts.length > 0 && <label>Ảnh đang dùng<select value={selected?.id ?? ''} onChange={(event) => setSelectedArtifactId(event.target.value)}>{imageArtifacts.map((artifact, index) => <option key={artifact.id} value={artifact.id}>Ảnh {index + 1} · {artifact.original_filename}</option>)}</select></label>}
      <div className="machine-qa-protocol-controls">
        <label>Khoảng cách nguồn–ảnh (mm)<input type="number" min="0" step="0.1" value={sid} onChange={(event) => setSid(event.target.value)} /></label>
        <label>Mật độ điểm ảnh (dpi, nếu ảnh thiếu thang đo)<input type="number" min="0" step="0.1" value={dpi} onChange={(event) => setDpi(event.target.value)} placeholder="Tự đọc từ ảnh" /></label>
        <label>Bán kính phân tích<input type="number" min="0.2" max="0.95" step="0.01" value={radius} onChange={(event) => setRadius(event.target.value)} /></label>
        <label>Dung sai (mm)<input type="number" min="0" step="0.01" value={tolerance} onChange={(event) => setTolerance(event.target.value)} /></label>
      </div>
      <div className="machine-qa-protocol-controls">
        <label>Tâm bắt đầu X (pixel, tùy chọn)<input type="number" step="0.1" value={startX} onChange={(event) => setStartX(event.target.value)} /></label>
        <label>Tâm bắt đầu Y (pixel, tùy chọn)<input type="number" step="0.1" value={startY} onChange={(event) => setStartY(event.target.value)} /></label>
      </div>
      <div className="machine-qa-actions"><button disabled={!selected || isBusy || ((startX.trim() === '') !== (startY.trim() === ''))} onClick={() => analyze.mutate()}>{analyze.isPending ? 'Đang phân tích…' : 'Bắt đầu phân tích'}</button></div>
    </section>
    {latest && <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ MỚI NHẤT</p><h2>{latest.name}</h2></div><span className={statusClass(latest.status)}>{statusLabel(latest.status)}</span></div>{latest.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Không thể phân tích</h3><ul>{latest.error_snapshot.map((item, index) => <li key={index}>{textValue(item.message, 'Đã xảy ra lỗi trong bộ tính.')}</li>)}</ul></div>}{latest.status === 'COMPLETED' && <><div className="machine-qa-run-meta"><span>Độ lệch đường kính: {textValue(pylinacMetric(latest, 'circle_diameter_mm'))} mm</span><span>Tâm phân tích: {Array.isArray(center) ? `${textValue(center[0])}, ${textValue(center[1])}` : 'Tự động'}</span><span>Số tia: {Array.isArray(pylinacMetric(latest, 'angles')) ? (pylinacMetric(latest, 'angles') as unknown[]).length : '—'}</span></div>{latest.overlay_artifact_id && <button className="button-secondary" onClick={() => { void apiClient.downloadArtifact(accessToken, latest.overlay_artifact_id!).then((download) => window.open(download.url, '_blank', 'noopener,noreferrer')).catch((error) => setMessage(errorMessage(error))) }}>Mở ảnh phân tích</button>}<label>Đánh giá của người dùng<select value={latest.assessment_status ?? 'NOT_ASSESSED'} onChange={(event) => assess.mutate({ runId: latest.id, value: event.target.value as 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' })}><option value="NOT_ASSESSED">Chưa đánh giá</option><option value="PASS">Đạt</option><option value="WARNING">Cảnh báo</option><option value="REVIEW">Cần xem lại</option><option value="FAIL">Không đạt</option></select></label></>}</section>}
    <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ PHÂN TÍCH</p><h2>Kết quả đã lưu</h2></div><strong>{history.length}</strong></div>{history.length === 0 ? <p className="empty-state">Chưa có kết quả kiểm tra sao.</p> : <div className="table-wrap"><table><thead><tr><th>Lần phân tích</th><th>Trạng thái</th><th>Đánh giá</th><th>Thời điểm</th></tr></thead><tbody>{history.map((run, index) => <tr key={run.id}><td>Lần {history.length - index}</td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td>{statusLabel(run.assessment_status)}</td><td>{formatDate(run.completed_at ?? run.created_at)}</td></tr>)}</tbody></table></div>}</section>
  </div>
}

function WinstonLutzPage({ caseId, accessToken, title }: { caseId: string; accessToken: string; title: string }) {
  const queryClient = useQueryClient()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string>()
  const [sid, setSid] = useState('1000')
  const [dpi, setDpi] = useState('')
  const [bbSize, setBbSize] = useState('5')
  const [snapTolerance, setSnapTolerance] = useState('3')
  const [bbProximity, setBbProximity] = useState('20')
  const [gantryReference, setGantryReference] = useState('0')
  const [collimatorReference, setCollimatorReference] = useState('0')
  const [couchReference, setCouchReference] = useState('0')
  const [useFilenames, setUseFilenames] = useState(false)
  const [lowDensityBb, setLowDensityBb] = useState(false)
  const [openField, setOpenField] = useState(false)
  const [applyVirtualShift, setApplyVirtualShift] = useState(false)
  const [message, setMessage] = useState<string>()
  const artifacts = useQuery({
    queryKey: ['pylinac-artifacts', caseId, accessToken],
    queryFn: () => apiClient.artifacts(accessToken, caseId), retry: false
  })
  const runs = useQuery({
    queryKey: ['pylinac-runs', caseId, accessToken],
    queryFn: () => apiClient.pylinacQARuns(accessToken, caseId), retry: false
  })
  const upload = useMutation({
    mutationFn: (file: File) => apiClient.uploadArtifact(accessToken, caseId, file, 'OTHER', 'EVALUATION'),
    onSuccess: (artifact) => {
      setSelectedArtifactId(artifact.id)
      setMessage('Đã tải bộ ảnh Winston–Lutz lên; có thể bắt đầu phân tích.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-artifacts', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const analyze = useMutation({
    mutationFn: () => {
      const parameters: Record<string, unknown> = {
        sid: Number(sid), bb_size_mm: Number(bbSize), snap_tolerance: Number(snapTolerance),
        bb_proximity_mm: Number(bbProximity), gantry_reference: Number(gantryReference),
        collimator_reference: Number(collimatorReference), couch_reference: Number(couchReference),
        use_filenames: useFilenames, low_density_bb: lowDensityBb, open_field: openField,
        apply_virtual_shift: applyVirtualShift
      }
      if (dpi.trim()) parameters.dpi = Number(dpi)
      return apiClient.createPylinacQARun(accessToken, caseId, {
        catalog_key: 'WINSTON_LUTZ', artifact_ids: [selectedArtifactId!], parameters
      })
    },
    onSuccess: (run) => {
      setMessage(run.status === 'COMPLETED' ? 'Đã phân tích Winston–Lutz bằng Pylinac.' : 'Pylinac không thể hoàn tất phân tích; hãy xem thông báo lỗi bên dưới.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const assess = useMutation({
    mutationFn: ({ runId, value }: { runId: string; value: 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' }) => apiClient.assessPylinacQARun(accessToken, runId, value),
    onSuccess: () => { setMessage('Đã lưu đánh giá của người dùng.'); void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const zipArtifacts = (artifacts.data?.items ?? []).filter((item) => item.original_filename.toLowerCase().endsWith('.zip'))
  const selected = zipArtifacts.find((item) => item.id === selectedArtifactId) ?? zipArtifacts[0]
  const history = runs.data?.items ?? []
  const latest = history[0]
  const isBusy = upload.isPending || analyze.isPending || assess.isPending
  const metric = (key: string) => textValue(pylinacMetric(latest, key))

  return <div className="page">
    <header className="page-header">
      <div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY · Pylinac</p><h1>Kiểm tra Winston–Lutz</h1><p>{title} · phân tích độ chính xác hình học từ bộ ảnh theo các góc máy.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kho QA</Link><span className="status-badge">BỘ TÍNH Pylinac 3.47.0</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="panel machine-qa-panel">
      <div className="panel-heading"><div><p className="eyebrow">TỆP ĐẦU VÀO</p><h2>Bộ ảnh Winston–Lutz</h2></div><strong>{zipArtifacts.length}</strong></div>
      <p>Chọn một tệp ZIP chứa toàn bộ ảnh DICOM và tên góc máy. Phần giao diện chỉ hỏi các tham số cần thiết; Pylinac chịu trách nhiệm đọc ảnh và tính toán.</p>
      <div className="machine-qa-actions"><label className="button-link">Chọn tệp ZIP<input type="file" accept=".zip,application/zip" hidden disabled={isBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.currentTarget.value = '' }} /></label></div>
      {zipArtifacts.length > 0 && <label>Tệp đang dùng<select value={selected?.id ?? ''} onChange={(event) => setSelectedArtifactId(event.target.value)}>{zipArtifacts.map((artifact, index) => <option key={artifact.id} value={artifact.id}>Bộ ảnh {index + 1} · {artifact.original_filename}</option>)}</select></label>}
      <div className="machine-qa-protocol-controls">
        <label>Khoảng cách nguồn–ảnh (mm)<input type="number" min="0" step="0.1" value={sid} onChange={(event) => setSid(event.target.value)} /></label>
        <label>Mật độ điểm ảnh (dpi, nếu cần)<input type="number" min="0" step="0.1" value={dpi} onChange={(event) => setDpi(event.target.value)} placeholder="Tự đọc từ ảnh" /></label>
        <label>Kích thước bi chuẩn (mm)<input type="number" min="0" step="0.1" value={bbSize} onChange={(event) => setBbSize(event.target.value)} /></label>
        <label>Dung sai bắt ảnh (mm)<input type="number" min="0" step="0.1" value={snapTolerance} onChange={(event) => setSnapTolerance(event.target.value)} /></label>
      </div>
      <div className="machine-qa-protocol-controls">
        <label>Khoảng cách nhận diện bi (mm)<input type="number" min="0" step="0.1" value={bbProximity} onChange={(event) => setBbProximity(event.target.value)} /></label>
        <label>Góc máy tham chiếu<input type="number" step="0.1" value={gantryReference} onChange={(event) => setGantryReference(event.target.value)} /></label>
        <label>Góc chuẩn trực tham chiếu<input type="number" step="0.1" value={collimatorReference} onChange={(event) => setCollimatorReference(event.target.value)} /></label>
        <label>Góc bàn tham chiếu<input type="number" step="0.1" value={couchReference} onChange={(event) => setCouchReference(event.target.value)} /></label>
      </div>
      <div className="machine-qa-checks">
        <label><input type="checkbox" checked={useFilenames} onChange={(event) => setUseFilenames(event.target.checked)} /> Ưu tiên đọc góc máy từ tên tệp</label>
        <label><input type="checkbox" checked={lowDensityBb} onChange={(event) => setLowDensityBb(event.target.checked)} /> Bi chuẩn có mật độ thấp</label>
        <label><input type="checkbox" checked={openField} onChange={(event) => setOpenField(event.target.checked)} /> Ảnh trường mở</label>
        <label><input type="checkbox" checked={applyVirtualShift} onChange={(event) => setApplyVirtualShift(event.target.checked)} /> Áp dụng dịch chuyển ảo</label>
      </div>
      <div className="machine-qa-actions"><button disabled={!selected || isBusy} onClick={() => analyze.mutate()}>{analyze.isPending ? 'Đang phân tích…' : 'Bắt đầu phân tích'}</button></div>
    </section>
    {latest && <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ MỚI NHẤT</p><h2>{latest.name}</h2></div><span className={statusClass(latest.status)}>{statusLabel(latest.status)}</span></div>{latest.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Không thể phân tích</h3><ul>{latest.error_snapshot.map((item, index) => <li key={index}>{textValue(item.message, 'Đã xảy ra lỗi trong bộ tính.')}</li>)}</ul></div>}{latest.status === 'COMPLETED' && <><div className="machine-qa-run-meta"><span>Sai lệch trục–bi lớn nhất: {metric('max_2d_cax_to_bb_mm')} mm</span><span>Đường kính đồng tâm bàn gantry: {metric('gantry_3d_iso_diameter_mm')} mm</span><span>Đường kính đồng tâm chuẩn trực: {metric('coll_2d_iso_diameter_mm')} mm</span><span>Đường kính đồng tâm bàn: {metric('couch_2d_iso_diameter_mm')} mm</span></div>{latest.overlay_artifact_id && <button className="button-secondary" onClick={() => { void apiClient.downloadArtifact(accessToken, latest.overlay_artifact_id!).then((download) => window.open(download.url, '_blank', 'noopener,noreferrer')).catch((error) => setMessage(errorMessage(error))) }}>Mở ảnh phân tích</button>}<label>Đánh giá của người dùng<select value={latest.assessment_status ?? 'NOT_ASSESSED'} onChange={(event) => assess.mutate({ runId: latest.id, value: event.target.value as 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' })}><option value="NOT_ASSESSED">Chưa đánh giá</option><option value="PASS">Đạt</option><option value="WARNING">Cảnh báo</option><option value="REVIEW">Cần xem lại</option><option value="FAIL">Không đạt</option></select></label></>}</section>}
    <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ PHÂN TÍCH</p><h2>Kết quả đã lưu</h2></div><strong>{history.length}</strong></div>{history.length === 0 ? <p className="empty-state">Chưa có kết quả Winston–Lutz.</p> : <div className="table-wrap"><table><thead><tr><th>Lần phân tích</th><th>Trạng thái</th><th>Đánh giá</th><th>Thời điểm</th></tr></thead><tbody>{history.map((run, index) => <tr key={run.id}><td>Lần {history.length - index}</td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td>{statusLabel(run.assessment_status)}</td><td>{formatDate(run.completed_at ?? run.created_at)}</td></tr>)}</tbody></table></div>}</section>
  </div>
}

type WinstonLutzBBRow = {
  name: string
  offset_left_mm: string
  offset_up_mm: string
  offset_in_mm: string
  bb_size_mm: string
  rad_size_mm: string
}

function WinstonLutzMultiTargetPage({ caseId, accessToken, title }: { caseId: string; accessToken: string; title: string }) {
  const queryClient = useQueryClient()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string>()
  const [sid, setSid] = useState('1000')
  const [dpi, setDpi] = useState('')
  const [bbProximity, setBbProximity] = useState('10')
  const [useFilenames, setUseFilenames] = useState(false)
  const [isLowDensity, setIsLowDensity] = useState(false)
  const [isOpenField, setIsOpenField] = useState(false)
  const [message, setMessage] = useState<string>()
  const [arrangement, setArrangement] = useState<WinstonLutzBBRow[]>([
    { name: 'Iso', offset_left_mm: '0', offset_up_mm: '0', offset_in_mm: '0', bb_size_mm: '5', rad_size_mm: '20' },
    { name: '1', offset_left_mm: '0', offset_up_mm: '0', offset_in_mm: '30', bb_size_mm: '5', rad_size_mm: '20' },
    { name: '2', offset_left_mm: '-30', offset_up_mm: '0', offset_in_mm: '15', bb_size_mm: '5', rad_size_mm: '20' },
    { name: '3', offset_left_mm: '0', offset_up_mm: '0', offset_in_mm: '-30', bb_size_mm: '5', rad_size_mm: '20' },
    { name: '4', offset_left_mm: '30', offset_up_mm: '0', offset_in_mm: '-50', bb_size_mm: '5', rad_size_mm: '20' },
    { name: '5', offset_left_mm: '0', offset_up_mm: '0', offset_in_mm: '-70', bb_size_mm: '5', rad_size_mm: '20' }
  ])
  const artifacts = useQuery({
    queryKey: ['pylinac-artifacts', caseId, accessToken],
    queryFn: () => apiClient.artifacts(accessToken, caseId), retry: false
  })
  const runs = useQuery({
    queryKey: ['pylinac-runs', caseId, accessToken],
    queryFn: () => apiClient.pylinacQARuns(accessToken, caseId), retry: false
  })
  const upload = useMutation({
    mutationFn: (file: File) => apiClient.uploadArtifact(accessToken, caseId, file, 'OTHER', 'EVALUATION'),
    onSuccess: (artifact) => {
      setSelectedArtifactId(artifact.id)
      setMessage('Đã tải bộ ảnh nhiều bi lên; có thể bắt đầu phân tích.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-artifacts', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const analyze = useMutation({
    mutationFn: () => {
      const parameters: Record<string, unknown> = {
        sid: Number(sid), bb_proximity_mm: Number(bbProximity), use_filenames: useFilenames,
        is_low_density: isLowDensity, is_open_field: isOpenField,
        bb_arrangement: arrangement.map((row) => ({
          name: row.name, offset_left_mm: Number(row.offset_left_mm), offset_up_mm: Number(row.offset_up_mm),
          offset_in_mm: Number(row.offset_in_mm), bb_size_mm: Number(row.bb_size_mm), rad_size_mm: Number(row.rad_size_mm)
        }))
      }
      if (dpi.trim()) parameters.dpi = Number(dpi)
      return apiClient.createPylinacQARun(accessToken, caseId, {
        catalog_key: 'WINSTON_LUTZ_MULTI_TARGET', artifact_ids: [selectedArtifactId!], parameters
      })
    },
    onSuccess: (run) => {
      setMessage(run.status === 'COMPLETED' ? 'Đã phân tích Winston–Lutz nhiều bi bằng Pylinac.' : 'Pylinac không thể hoàn tất phân tích; hãy xem thông báo lỗi bên dưới.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const assess = useMutation({
    mutationFn: ({ runId, value }: { runId: string; value: 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' }) => apiClient.assessPylinacQARun(accessToken, runId, value),
    onSuccess: () => { setMessage('Đã lưu đánh giá của người dùng.'); void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const updateBB = (index: number, key: keyof WinstonLutzBBRow, value: string) => {
    setArrangement((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row))
  }
  const zipArtifacts = (artifacts.data?.items ?? []).filter((item) => item.original_filename.toLowerCase().endsWith('.zip'))
  const selected = zipArtifacts.find((item) => item.id === selectedArtifactId) ?? zipArtifacts[0]
  const history = runs.data?.items ?? []
  const latest = history[0]
  const isBusy = upload.isPending || analyze.isPending || assess.isPending
  const metric = (key: string) => textValue(pylinacMetric(latest, key))

  return <div className="page">
    <header className="page-header">
      <div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY · Pylinac</p><h1>Winston–Lutz nhiều bi</h1><p>{title} · ghép nhiều bi chuẩn và trường chiếu để đánh giá hình học từng mục tiêu.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kho QA</Link><span className="status-badge">BỘ TÍNH Pylinac 3.47.0</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="panel machine-qa-panel">
      <div className="panel-heading"><div><p className="eyebrow">TỆP ĐẦU VÀO</p><h2>Bộ ảnh nhiều bi, nhiều trường</h2></div><strong>{zipArtifacts.length}</strong></div>
      <p>Chọn một tệp ZIP chứa bộ ảnh DICOM. Bảng bên dưới là cấu hình vị trí bi chuẩn; không cần tạo tệp cấu hình riêng.</p>
      <div className="machine-qa-actions"><label className="button-link">Chọn tệp ZIP<input type="file" accept=".zip,application/zip" hidden disabled={isBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.currentTarget.value = '' }} /></label></div>
      {zipArtifacts.length > 0 && <label>Tệp đang dùng<select value={selected?.id ?? ''} onChange={(event) => setSelectedArtifactId(event.target.value)}>{zipArtifacts.map((artifact, index) => <option key={artifact.id} value={artifact.id}>Bộ ảnh {index + 1} · {artifact.original_filename}</option>)}</select></label>}
      <div className="machine-qa-protocol-controls">
        <label>Khoảng cách nguồn–ảnh (mm)<input type="number" min="0" step="0.1" value={sid} onChange={(event) => setSid(event.target.value)} /></label>
        <label>Mật độ điểm ảnh (dpi, nếu cần)<input type="number" min="0" step="0.1" value={dpi} onChange={(event) => setDpi(event.target.value)} placeholder="Tự đọc từ ảnh" /></label>
        <label>Khoảng cách nhận diện bi (mm)<input type="number" min="0" step="0.1" value={bbProximity} onChange={(event) => setBbProximity(event.target.value)} /></label>
      </div>
      <div className="table-wrap"><table><thead><tr><th>Tên bi</th><th>Lệch trái/phải (mm)</th><th>Lệch lên/xuống (mm)</th><th>Lệch trong/ngoài (mm)</th><th>Kích thước bi (mm)</th><th>Bán kính trường (mm)</th></tr></thead><tbody>{arrangement.map((row, index) => <tr key={`${row.name}-${index}`}><td><input aria-label={`Tên bi ${index + 1}`} value={row.name} onChange={(event) => updateBB(index, 'name', event.target.value)} /></td><td><input aria-label={`Lệch trái phải ${index + 1}`} type="number" step="0.1" value={row.offset_left_mm} onChange={(event) => updateBB(index, 'offset_left_mm', event.target.value)} /></td><td><input aria-label={`Lệch lên xuống ${index + 1}`} type="number" step="0.1" value={row.offset_up_mm} onChange={(event) => updateBB(index, 'offset_up_mm', event.target.value)} /></td><td><input aria-label={`Lệch trong ngoài ${index + 1}`} type="number" step="0.1" value={row.offset_in_mm} onChange={(event) => updateBB(index, 'offset_in_mm', event.target.value)} /></td><td><input aria-label={`Kích thước bi ${index + 1}`} type="number" min="0" step="0.1" value={row.bb_size_mm} onChange={(event) => updateBB(index, 'bb_size_mm', event.target.value)} /></td><td><input aria-label={`Bán kính trường ${index + 1}`} type="number" min="0" step="0.1" value={row.rad_size_mm} onChange={(event) => updateBB(index, 'rad_size_mm', event.target.value)} /></td></tr>)}</tbody></table></div>
      <div className="machine-qa-checks">
        <label><input type="checkbox" checked={useFilenames} onChange={(event) => setUseFilenames(event.target.checked)} /> Ưu tiên đọc góc máy từ tên tệp</label>
        <label><input type="checkbox" checked={isLowDensity} onChange={(event) => setIsLowDensity(event.target.checked)} /> Bi chuẩn có mật độ thấp</label>
        <label><input type="checkbox" checked={isOpenField} onChange={(event) => setIsOpenField(event.target.checked)} /> Trường chiếu mở</label>
      </div>
      <div className="machine-qa-actions"><button disabled={!selected || isBusy} onClick={() => analyze.mutate()}>{analyze.isPending ? 'Đang phân tích…' : 'Bắt đầu phân tích'}</button></div>
    </section>
    {latest && <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ MỚI NHẤT</p><h2>{latest.name}</h2></div><span className={statusClass(latest.status)}>{statusLabel(latest.status)}</span></div>{latest.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Không thể phân tích</h3><ul>{latest.error_snapshot.map((item, index) => <li key={index}>{textValue(item.message, 'Đã xảy ra lỗi trong bộ tính.')}</li>)}</ul></div>}{latest.status === 'COMPLETED' && <><div className="machine-qa-run-meta"><span>Sai lệch trường–bi lớn nhất: {metric('max_2d_field_to_bb_mm')} mm</span><span>Sai lệch trường–bi trung vị: {metric('median_2d_field_to_bb_mm')} mm</span><span>Số ảnh: {metric('num_total_images')}</span><span>Số bi: {Array.isArray(pylinacMetric(latest, 'bb_arrangement')) ? (pylinacMetric(latest, 'bb_arrangement') as unknown[]).length : '—'}</span></div>{latest.overlay_artifact_id && <button className="button-secondary" onClick={() => { void apiClient.downloadArtifact(accessToken, latest.overlay_artifact_id!).then((download) => window.open(download.url, '_blank', 'noopener,noreferrer')).catch((error) => setMessage(errorMessage(error))) }}>Mở ảnh phân tích</button>}<label>Đánh giá của người dùng<select value={latest.assessment_status ?? 'NOT_ASSESSED'} onChange={(event) => assess.mutate({ runId: latest.id, value: event.target.value as 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' })}><option value="NOT_ASSESSED">Chưa đánh giá</option><option value="PASS">Đạt</option><option value="WARNING">Cảnh báo</option><option value="REVIEW">Cần xem lại</option><option value="FAIL">Không đạt</option></select></label></>}</section>}
    <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ PHÂN TÍCH</p><h2>Kết quả đã lưu</h2></div><strong>{history.length}</strong></div>{history.length === 0 ? <p className="empty-state">Chưa có kết quả Winston–Lutz nhiều bi.</p> : <div className="table-wrap"><table><thead><tr><th>Lần phân tích</th><th>Trạng thái</th><th>Đánh giá</th><th>Thời điểm</th></tr></thead><tbody>{history.map((run, index) => <tr key={run.id}><td>Lần {history.length - index}</td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td>{statusLabel(run.assessment_status)}</td><td>{formatDate(run.completed_at ?? run.created_at)}</td></tr>)}</tbody></table></div>}</section>
  </div>
}

type VmatCatalogKey = 'VMAT_DRGS' | 'VMAT_DRMLC' | 'VMAT_DRCS'

function VmatPage({ caseId, accessToken, title, catalogKey }: { caseId: string; accessToken: string; title: string; catalogKey: VmatCatalogKey }) {
  const queryClient = useQueryClient()
  const [selectedArtifactIds, setSelectedArtifactIds] = useState<string[]>([])
  const [tolerance, setTolerance] = useState('1.5')
  const [segmentWidth, setSegmentWidth] = useState('5')
  const [segmentLength, setSegmentLength] = useState('100')
  const [collimatorMin, setCollimatorMin] = useState('30')
  const [collimatorMax, setCollimatorMax] = useState('70')
  const [message, setMessage] = useState<string>()
  const artifacts = useQuery({
    queryKey: ['pylinac-artifacts', caseId, accessToken],
    queryFn: () => apiClient.artifacts(accessToken, caseId), retry: false
  })
  const runs = useQuery({
    queryKey: ['pylinac-runs', caseId, accessToken],
    queryFn: () => apiClient.pylinacQARuns(accessToken, caseId), retry: false
  })
  const upload = useMutation({
    mutationFn: (files: File[]) => Promise.all(files.slice(0, 2).map((file) => apiClient.uploadArtifact(accessToken, caseId, file, 'DICOM', 'EVALUATION'))),
    onSuccess: (uploaded) => {
      setSelectedArtifactIds(uploaded.map((artifact) => artifact.id))
      setMessage('Đã tải cặp ảnh VMAT lên; hãy xác nhận ảnh mở và ảnh điều biến rồi bắt đầu phân tích.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-artifacts', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const analyze = useMutation({
    mutationFn: () => {
      const parameters: Record<string, unknown> = {
        ground: true, check_inversion: true, tolerance: Number(tolerance),
        segment_size_mm: [Number(segmentWidth), Number(segmentLength)], invert_image_order: false
      }
      if (catalogKey === 'VMAT_DRCS') parameters.collimator_radial_distances = [Number(collimatorMin), Number(collimatorMax)]
      return apiClient.createPylinacQARun(accessToken, caseId, {
        catalog_key: catalogKey, artifact_ids: selectedPair, parameters
      })
    },
    onSuccess: (run) => {
      setMessage(run.status === 'COMPLETED' ? `Đã phân tích ${catalogKey.replace('VMAT_', '')} bằng Pylinac.` : 'Pylinac không thể hoàn tất phân tích; hãy xem thông báo lỗi bên dưới.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const assess = useMutation({
    mutationFn: ({ runId, value }: { runId: string; value: 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' }) => apiClient.assessPylinacQARun(accessToken, runId, value),
    onSuccess: () => { setMessage('Đã lưu đánh giá của người dùng.'); void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const imageArtifacts = (artifacts.data?.items ?? []).filter((item) => item.artifact_type === 'DICOM' || item.artifact_type === 'IMAGE')
  const selectedPair = selectedArtifactIds.length === 2 ? selectedArtifactIds : imageArtifacts.slice(0, 2).map((artifact) => artifact.id)
  const history = runs.data?.items ?? []
  const latest = history[0]
  const isBusy = upload.isPending || analyze.isPending || assess.isPending
  const displayName = catalogKey.replace('VMAT_', '')

  const setPairItem = (index: number, value: string) => {
    setSelectedArtifactIds((current) => {
      const next = current.length === 2 ? [...current] : imageArtifacts.slice(0, 2).map((artifact) => artifact.id)
      next[index] = value
      return next
    })
  }

  return <div className="page">
    <header className="page-header">
      <div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY · Pylinac</p><h1>Kiểm tra VMAT {displayName}</h1><p>{title} · so sánh cặp ảnh trường mở và trường điều biến.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kho QA</Link><span className="status-badge">BỘ TÍNH Pylinac 3.47.0</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="panel machine-qa-panel">
      <div className="panel-heading"><div><p className="eyebrow">CẶP TỆP ĐẦU VÀO</p><h2>Ảnh trường mở và ảnh trường điều biến</h2></div><strong>{imageArtifacts.length}</strong></div>
      <p>Bài VMAT luôn cần đúng hai ảnh. Sau khi tải lên, chọn rõ ảnh trường mở và ảnh trường điều biến để giữ đúng thứ tự phân tích.</p>
      <div className="machine-qa-actions"><label className="button-link">Chọn hai ảnh DICOM<input type="file" accept=".dcm,application/dicom" multiple hidden disabled={isBusy} onChange={(event) => { const files = event.target.files ? Array.from(event.target.files) : []; if (files.length === 2) upload.mutate(files); else if (files.length > 0) setMessage('Hãy chọn đúng hai ảnh DICOM: một ảnh trường mở và một ảnh trường điều biến.'); event.currentTarget.value = '' }} /></label></div>
      <div className="machine-qa-protocol-controls">
        <label>Ảnh trường mở<select value={selectedPair[0] ?? ''} onChange={(event) => setPairItem(0, event.target.value)}>{imageArtifacts.map((artifact, index) => <option key={artifact.id} value={artifact.id}>Ảnh {index + 1} · {artifact.original_filename}</option>)}</select></label>
        <label>Ảnh trường điều biến<select value={selectedPair[1] ?? ''} onChange={(event) => setPairItem(1, event.target.value)}>{imageArtifacts.map((artifact, index) => <option key={artifact.id} value={artifact.id}>Ảnh {index + 1} · {artifact.original_filename}</option>)}</select></label>
        <label>Dung sai (%)<input type="number" min="0" step="0.1" value={tolerance} onChange={(event) => setTolerance(event.target.value)} /></label>
      </div>
      <div className="machine-qa-protocol-controls">
        <label>Chiều rộng đoạn phân tích (mm)<input type="number" min="0" step="0.1" value={segmentWidth} onChange={(event) => setSegmentWidth(event.target.value)} /></label>
        <label>Chiều dài đoạn phân tích (mm)<input type="number" min="0" step="0.1" value={segmentLength} onChange={(event) => setSegmentLength(event.target.value)} /></label>
        {catalogKey === 'VMAT_DRCS' && <><label>Khoảng cách xuyên tâm nhỏ nhất (mm)<input type="number" min="0" step="0.1" value={collimatorMin} onChange={(event) => setCollimatorMin(event.target.value)} /></label><label>Khoảng cách xuyên tâm lớn nhất (mm)<input type="number" min="0" step="0.1" value={collimatorMax} onChange={(event) => setCollimatorMax(event.target.value)} /></label></>}
      </div>
      <div className="machine-qa-actions"><button disabled={selectedPair.length !== 2 || selectedPair[0] === selectedPair[1] || isBusy} onClick={() => analyze.mutate()}>{analyze.isPending ? 'Đang phân tích…' : 'Bắt đầu phân tích'}</button></div>
    </section>
    {latest && <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ MỚI NHẤT</p><h2>{latest.name}</h2></div><span className={statusClass(latest.status)}>{statusLabel(latest.status)}</span></div>{latest.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Không thể phân tích</h3><ul>{latest.error_snapshot.map((item, index) => <li key={index}>{textValue(item.message, 'Đã xảy ra lỗi trong bộ tính.')}</li>)}</ul></div>}{latest.status === 'COMPLETED' && <><div className="machine-qa-run-meta"><span>Sai lệch lớn nhất: {textValue(pylinacMetric(latest, 'max_deviation_percent'))}%</span><span>Sai lệch trung bình tuyệt đối: {textValue(pylinacMetric(latest, 'abs_mean_deviation'))}%</span><span>Dung sai: {textValue(pylinacMetric(latest, 'tolerance_percent'))}%</span><span>Số đoạn: {Array.isArray(pylinacMetric(latest, 'segment_data')) ? (pylinacMetric(latest, 'segment_data') as unknown[]).length : '—'}</span></div>{latest.overlay_artifact_id && <button className="button-secondary" onClick={() => { void apiClient.downloadArtifact(accessToken, latest.overlay_artifact_id!).then((download) => window.open(download.url, '_blank', 'noopener,noreferrer')).catch((error) => setMessage(errorMessage(error))) }}>Mở ảnh phân tích</button>}<label>Đánh giá của người dùng<select value={latest.assessment_status ?? 'NOT_ASSESSED'} onChange={(event) => assess.mutate({ runId: latest.id, value: event.target.value as 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' })}><option value="NOT_ASSESSED">Chưa đánh giá</option><option value="PASS">Đạt</option><option value="WARNING">Cảnh báo</option><option value="REVIEW">Cần xem lại</option><option value="FAIL">Không đạt</option></select></label></>}</section>}
    <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ PHÂN TÍCH</p><h2>Kết quả đã lưu</h2></div><strong>{history.length}</strong></div>{history.length === 0 ? <p className="empty-state">Chưa có kết quả {displayName}.</p> : <div className="table-wrap"><table><thead><tr><th>Lần phân tích</th><th>Trạng thái</th><th>Đánh giá</th><th>Thời điểm</th></tr></thead><tbody>{history.map((run, index) => <tr key={run.id}><td>Lần {history.length - index}</td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td>{statusLabel(run.assessment_status)}</td><td>{formatDate(run.completed_at ?? run.created_at)}</td></tr>)}</tbody></table></div>}</section>
  </div>
}

type FieldAnalysisCatalogKey = 'FIELD_PROFILE_ANALYSIS' | 'FIELD_ANALYSIS_LEGACY'

function FieldAnalysisPage({ caseId, accessToken, title, catalogKey }: { caseId: string; accessToken: string; title: string; catalogKey: FieldAnalysisCatalogKey }) {
  const queryClient = useQueryClient()
  const [selectedArtifactId, setSelectedArtifactId] = useState<string>()
  const [centering, setCentering] = useState('BEAM_CENTER')
  const [positionX, setPositionX] = useState('0.5')
  const [positionY, setPositionY] = useState('0.5')
  const [widthX, setWidthX] = useState('0')
  const [widthY, setWidthY] = useState('0')
  const [normalization, setNormalization] = useState(catalogKey === 'FIELD_PROFILE_ANALYSIS' ? 'NONE' : 'BEAM_CENTER')
  const [edge, setEdge] = useState('INFLECTION_DERIVATIVE')
  const [protocol, setProtocol] = useState('VARIAN')
  const [interpolation, setInterpolation] = useState('LINEAR')
  const [message, setMessage] = useState<string>()
  const artifacts = useQuery({
    queryKey: ['pylinac-artifacts', caseId, accessToken],
    queryFn: () => apiClient.artifacts(accessToken, caseId), retry: false
  })
  const runs = useQuery({
    queryKey: ['pylinac-runs', caseId, accessToken],
    queryFn: () => apiClient.pylinacQARuns(accessToken, caseId), retry: false
  })
  const upload = useMutation({
    mutationFn: (file: File) => apiClient.uploadArtifact(accessToken, caseId, file, 'DICOM', 'EVALUATION'),
    onSuccess: (artifact) => {
      setSelectedArtifactId(artifact.id)
      setMessage('Đã tải tệp ảnh lên; có thể bắt đầu phân tích biên dạng.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-artifacts', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const imageArtifacts = (artifacts.data?.items ?? []).filter((item) => item.artifact_type === 'DICOM' || item.artifact_type === 'IMAGE')
  const selectedInput = selectedArtifactId ?? imageArtifacts[0]?.id
  const analyze = useMutation({
    mutationFn: () => {
      const parameters: Record<string, unknown> = catalogKey === 'FIELD_PROFILE_ANALYSIS'
        ? { centering, position: [Number(positionX), Number(positionY)], x_width: Number(widthX), y_width: Number(widthY), normalization, edge_type: edge, ground: true }
        : { protocol, centering, vert_position: Number(positionY), horiz_position: Number(positionX), vert_width: Number(widthY), horiz_width: Number(widthX), interpolation, normalization_method: normalization, edge_detection_method: edge, ground: true }
      return apiClient.createPylinacQARun(accessToken, caseId, { catalog_key: catalogKey, artifact_ids: [selectedInput!], parameters })
    },
    onSuccess: (run) => {
      setMessage(run.status === 'COMPLETED' ? 'Đã phân tích biên dạng bằng Pylinac.' : 'Pylinac không thể hoàn tất phân tích; hãy xem thông báo lỗi bên dưới.')
      void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const assess = useMutation({
    mutationFn: ({ runId, value }: { runId: string; value: 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' }) => apiClient.assessPylinacQARun(accessToken, runId, value),
    onSuccess: () => { setMessage('Đã lưu đánh giá của người dùng.'); void queryClient.invalidateQueries({ queryKey: ['pylinac-runs', caseId, accessToken] }) },
    onError: (error) => setMessage(errorMessage(error))
  })
  const history = runs.data?.items ?? []
  const latest = history[0]
  const latestMetrics = objectValue(latest?.result_snapshot.metrics)
  const xMetrics = objectValue(latestMetrics?.x_metrics)
  const yMetrics = objectValue(latestMetrics?.y_metrics)
  const protocolResults = objectValue(latestMetrics?.protocol_results)
  const isBusy = upload.isPending || analyze.isPending || assess.isPending
  const isLegacy = catalogKey === 'FIELD_ANALYSIS_LEGACY'
  const displayName = isLegacy ? 'Phân tích trường phiên bản cũ' : 'Phân tích biên dạng trường'
  const metricItems: Array<[string, unknown]> = isLegacy
    ? [['Độ phẳng ngang', protocolResults?.flatness_horizontal], ['Độ phẳng dọc', protocolResults?.flatness_vertical], ['Đối xứng ngang', protocolResults?.symmetry_horizontal], ['Đối xứng dọc', protocolResults?.symmetry_vertical]]
    : [['Độ phẳng trục X', xMetrics?.['Flatness (Difference) (%)']], ['Độ phẳng trục Y', yMetrics?.['Flatness (Difference) (%)']], ['Độ rộng trường X', xMetrics?.['Field Width (mm)']], ['Độ rộng trường Y', yMetrics?.['Field Width (mm)']]]

  return <div className="page">
    <header className="page-header">
      <div><p className="eyebrow">KIỂM TRA CHẤT LƯỢNG MÁY · Pylinac</p><h1>{displayName}</h1><p>{title} · đọc biên dạng từ một tệp ảnh DICOM.</p></div>
      <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kho QA</Link><span className="status-badge">BỘ TÍNH Pylinac 3.47.0</span></div>
    </header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    <section className="panel machine-qa-panel">
      <div className="panel-heading"><div><p className="eyebrow">TỆP ĐẦU VÀO</p><h2>Ảnh trường hoặc dữ liệu biên dạng</h2></div><strong>{imageArtifacts.length}</strong></div>
      <p>Bài kiểm tra cần một tệp ảnh. Pylinac chịu trách nhiệm phân tích; RT-CONNECT chỉ thu thập lựa chọn và tham số của người thực hiện.</p>
      <div className="machine-qa-actions"><label className="button-link">Chọn ảnh DICOM<input type="file" accept=".dcm,application/dicom" hidden disabled={isBusy} onChange={(event) => { const file = event.target.files?.[0]; if (file) upload.mutate(file); event.currentTarget.value = '' }} /></label></div>
      {imageArtifacts.length > 0 && <label>Tệp đang chọn<select value={selectedInput ?? ''} onChange={(event) => setSelectedArtifactId(event.target.value)}>{imageArtifacts.map((artifact, index) => <option key={artifact.id} value={artifact.id}>Ảnh {index + 1} · {artifact.original_filename}</option>)}</select></label>}
      <div className="machine-qa-protocol-controls">
        <label>Cách xác định tâm<select value={centering} onChange={(event) => setCentering(event.target.value)}><option value="BEAM_CENTER">Tâm chùm tia</option><option value="GEOMETRIC_CENTER">Tâm hình học</option><option value="MANUAL">Chọn thủ công</option></select></label>
        <label>Vị trí ngang (0–1)<input type="number" min="0" max="1" step="0.01" value={positionX} onChange={(event) => setPositionX(event.target.value)} /></label>
        <label>Vị trí dọc (0–1)<input type="number" min="0" max="1" step="0.01" value={positionY} onChange={(event) => setPositionY(event.target.value)} /></label>
        <label>Dải ngang (mm)<input type="number" min="0" step="0.1" value={widthX} onChange={(event) => setWidthX(event.target.value)} /></label>
        <label>Dải dọc (mm)<input type="number" min="0" step="0.1" value={widthY} onChange={(event) => setWidthY(event.target.value)} /></label>
      </div>
      <div className="machine-qa-protocol-controls">
        {isLegacy && <label>Quy trình<select value={protocol} onChange={(event) => setProtocol(event.target.value)}><option value="VARIAN">Varian</option><option value="SIEMENS">Siemens</option><option value="ELEKTA">Elekta</option><option value="NONE">Không dùng</option></select></label>}
        {isLegacy && <label>Nội suy<select value={interpolation} onChange={(event) => setInterpolation(event.target.value)}><option value="LINEAR">Tuyến tính</option><option value="SPLINE">Spline</option><option value="NONE">Không dùng</option></select></label>}
        <label>Chuẩn hóa<select value={normalization} onChange={(event) => setNormalization(event.target.value)}><option value="NONE">Không chuẩn hóa</option><option value="BEAM_CENTER">Tâm chùm tia</option><option value="GEOMETRIC_CENTER">Tâm hình học</option><option value="MAX">Giá trị lớn nhất</option></select></label>
        <label>Phương pháp nhận biên<select value={edge} onChange={(event) => setEdge(event.target.value)}><option value="INFLECTION_DERIVATIVE">Đạo hàm điểm uốn</option><option value="FWHM">Nửa cực đại</option><option value="INFLECTION_HILL">Đỉnh điểm uốn</option></select></label>
      </div>
      <div className="machine-qa-actions"><button disabled={!selectedInput || isBusy} onClick={() => analyze.mutate()}>{analyze.isPending ? 'Đang phân tích…' : 'Bắt đầu phân tích'}</button></div>
    </section>
    {latest && <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">KẾT QUẢ MỚI NHẤT</p><h2>{latest.name}</h2></div><span className={statusClass(latest.status)}>{statusLabel(latest.status)}</span></div>{latest.error_snapshot.length > 0 && <div className="alert alert--error"><h3>Không thể phân tích</h3><ul>{latest.error_snapshot.map((item, index) => <li key={index}>{textValue(item.message, 'Đã xảy ra lỗi trong bộ tính.')}</li>)}</ul></div>}{latest.status === 'COMPLETED' && <><div className="machine-qa-run-meta">{metricItems.map(([label, value]) => <span key={label}>{label}: {textValue(value)}</span>)}</div>{latest.overlay_artifact_id && <button className="button-secondary" onClick={() => { void apiClient.downloadArtifact(accessToken, latest.overlay_artifact_id!).then((download) => window.open(download.url, '_blank', 'noopener,noreferrer')).catch((error) => setMessage(errorMessage(error))) }}>Mở ảnh phân tích</button>}<label>Đánh giá của người dùng<select value={latest.assessment_status ?? 'NOT_ASSESSED'} onChange={(event) => assess.mutate({ runId: latest.id, value: event.target.value as 'PASS' | 'WARNING' | 'FAIL' | 'REVIEW' | 'NOT_ASSESSED' })}><option value="NOT_ASSESSED">Chưa đánh giá</option><option value="PASS">Đạt</option><option value="WARNING">Cảnh báo</option><option value="REVIEW">Cần xem lại</option><option value="FAIL">Không đạt</option></select></label></>}</section>}
    <section className="panel machine-qa-panel"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ PHÂN TÍCH</p><h2>Kết quả đã lưu</h2></div><strong>{history.length}</strong></div>{history.length === 0 ? <p className="empty-state">Chưa có kết quả phân tích.</p> : <div className="table-wrap"><table><thead><tr><th>Lần phân tích</th><th>Trạng thái</th><th>Đánh giá</th><th>Thời điểm</th></tr></thead><tbody>{history.map((run, index) => <tr key={run.id}><td>Lần {history.length - index}</td><td><span className={statusClass(run.status)}>{statusLabel(run.status)}</span></td><td>{statusLabel(run.assessment_status)}</td><td>{formatDate(run.completed_at ?? run.created_at)}</td></tr>)}</tbody></table></div>}</section>
  </div>
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
  if (selectedCase.qa_definition_key === 'PICKET_FENCE' && accessToken) {
    return <PicketFencePage caseId={caseId} accessToken={accessToken} title={selectedCase.title} />
  }
  if (selectedCase.qa_definition_key === 'STARSHOT' && accessToken) {
    return <StarshotPage caseId={caseId} accessToken={accessToken} title={selectedCase.title} />
  }
  if (selectedCase.qa_definition_key === 'WINSTON_LUTZ' && accessToken) {
    return <WinstonLutzPage caseId={caseId} accessToken={accessToken} title={selectedCase.title} />
  }
  if (selectedCase.qa_definition_key === 'WINSTON_LUTZ_MULTI_TARGET' && accessToken) {
    return <WinstonLutzMultiTargetPage caseId={caseId} accessToken={accessToken} title={selectedCase.title} />
  }
  if ((selectedCase.qa_definition_key === 'VMAT_DRGS' || selectedCase.qa_definition_key === 'VMAT_DRMLC' || selectedCase.qa_definition_key === 'VMAT_DRCS') && accessToken) {
    return <VmatPage caseId={caseId} accessToken={accessToken} title={selectedCase.title} catalogKey={selectedCase.qa_definition_key} />
  }
  if ((selectedCase.qa_definition_key === 'FIELD_PROFILE_ANALYSIS' || selectedCase.qa_definition_key === 'FIELD_ANALYSIS_LEGACY') && accessToken) {
    return <FieldAnalysisPage caseId={caseId} accessToken={accessToken} title={selectedCase.title} catalogKey={selectedCase.qa_definition_key} />
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
