import { useMemo, useState } from 'react'
import { useMutation, useQueries, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import { ApiClientError, apiClient, type BaselineResource, type MaintenanceEventResource, type TrendResource, type TrendSeriesResource } from '../api/client'
import { useAuth } from '../auth/AuthProvider'

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    const details = error.details
      .map((detail) => `${detail.field ? `${detail.field}: ` : ''}${detail.message}`)
      .join(' · ')
    return `${error.message} (${error.code})${details ? ` — ${details}` : ''}`
  }
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function dateLabel(value: string): string {
  return new Date(value).toLocaleString('vi-VN')
}

function localDateTimeValue(value = new Date()): string {
  const pad = (part: number) => String(part).padStart(2, '0')
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(value.getMinutes())}`
}

function localDateTimeFromIso(value: string | null): string {
  if (!value) return ''
  const date = new Date(value)
  return Number.isNaN(date.valueOf()) ? '' : localDateTimeValue(date)
}

type BaselineEditState = {
  id: string
  expectedVersion: number
  name: string
  tolerance: string
  actionLevel: string
  effectiveTo: string
}

type MaintenanceEditState = {
  id: string
  expectedRevision: number
  eventType: string
  title: string
  startedAt: string
  endedAt: string
  notes: string
}

function chartPoints(series: TrendSeriesResource): string {
  const values = series.buckets.length ? series.buckets.map((item) => item.mean) : series.points.map((item) => item.value)
  if (!values.length) return ''
  const minimum = Math.min(...values)
  const maximum = Math.max(...values)
  const span = maximum - minimum || 1
  return values.map((value, index) => {
    const x = values.length === 1 ? 50 : (index / (values.length - 1)) * 100
    const y = 92 - ((value - minimum) / span) * 82
    return `${x},${y}`
  }).join(' ')
}

function SeriesCard({ series }: { series: TrendSeriesResource }) {
  const displayPoints = series.points.slice(-20)
  const displayBuckets = series.buckets.slice(-20)
  const hasData = displayPoints.length > 0 || displayBuckets.length > 0
  return <section className="panel trend-series-card">
    <div className="panel-heading">
      <div><p className="eyebrow">COMPATIBLE SERIES · {series.compatibility_signature}</p><h2>{series.machine_name} · {series.metric_key}</h2><p>{series.unit} · {Object.entries(series.context).map(([key, value]) => `${key}: ${String(value)}`).join(' · ')}</p></div>
      {series.baseline && <span className="status-badge">Baseline {series.baseline.baseline_value} {series.unit}</span>}
    </div>
    {!hasData ? <p className="empty-state">Series chưa có điểm hiển thị.</p> : <>
      <div className="trend-chart" aria-label={`Trend ${series.machine_name} ${series.metric_key}`}>
        <svg viewBox="0 0 100 100" role="img" aria-hidden="true" preserveAspectRatio="none"><line x1="0" y1="92" x2="100" y2="92" /><polyline points={chartPoints(series)} /></svg>
      </div>
      {series.buckets.length > 0 ? <div className="table-wrap"><table><thead><tr><th>Khoảng</th><th>Số điểm</th><th>Trung bình</th><th>Min–max</th><th>Nguồn</th></tr></thead><tbody>{displayBuckets.map((bucket) => <tr key={bucket.start_at}><td>{dateLabel(bucket.start_at)} – {dateLabel(bucket.end_at)}</td><td>{bucket.count}</td><td>{bucket.mean.toFixed(4)} {series.unit}</td><td>{bucket.minimum.toFixed(4)} – {bucket.maximum.toFixed(4)}</td><td>{bucket.source_run_ids.length} run</td></tr>)}</tbody></table></div> : <div className="table-wrap"><table><thead><tr><th>Thời điểm</th><th>Giá trị</th><th>Trạng thái</th><th>Baseline Δ</th><th>Nguồn</th></tr></thead><tbody>{displayPoints.map((point) => <tr key={point.id}><td>{dateLabel(point.measured_at)}</td><td>{point.value} {point.unit}</td><td><span className={point.is_outlier ? 'status-badge status-badge--warning' : 'status-badge'}>{point.status}{point.is_outlier ? ' · OUTLIER' : ''}</span></td><td>{point.baseline_delta === null ? '—' : point.baseline_delta.toFixed(4)}</td><td><Link to={`/app/qa/cases/${point.qa_case_id}/machine-qa`}>Mở case</Link><small className="table-subtitle"><code>{point.source_run_id.slice(0, 8)}…</code>{point.source_archived ? ' · archived' : ''}</small></td></tr>)}</tbody></table></div>}
    </>}
  </section>
}

type TrendLifecyclePanelProps = {
  baselines: BaselineResource[] | undefined
  events: MaintenanceEventResource[] | undefined
  machines: ReadonlyArray<{ id: string; display_name: string }>
  baselineEdit: BaselineEditState | null
  setBaselineEdit: (value: BaselineEditState | null) => void
  eventEdit: MaintenanceEditState | null
  setEventEdit: (value: MaintenanceEditState | null) => void
  busy: boolean
  beginBaselineEdit: (item: BaselineResource) => void
  beginEventEdit: (item: MaintenanceEventResource) => void
  updateBaseline: (input: { id: string; expectedVersion: number; patch: { name?: string; tolerance?: number | null; action_level?: number | null; effective_to?: string | null; status?: 'ACTIVE' | 'ARCHIVED' } }) => void
  updateEvent: (input: { id: string; expectedRevision: number; patch: { event_type?: string; title?: string; started_at?: string; ended_at?: string | null; notes?: string | null; status?: 'ACTIVE' | 'ARCHIVED' } }) => void
}

function TrendLifecyclePanel({
  baselines,
  events,
  machines,
  baselineEdit,
  setBaselineEdit,
  eventEdit,
  setEventEdit,
  busy,
  beginBaselineEdit,
  beginEventEdit,
  updateBaseline,
  updateEvent
}: TrendLifecyclePanelProps) {
  const machineName = (machineId: string) => machines.find((machine) => machine.id === machineId)?.display_name ?? machineId.slice(0, 8)
  return <>
    {baselineEdit && <section className="panel trend-lifecycle-editor" aria-label="Chỉnh sửa baseline">
      <div className="panel-heading"><div><p className="eyebrow">BASELINE REVISION {baselineEdit.expectedVersion}</p><h2>Chỉnh sửa baseline version</h2></div><button className="button-secondary" onClick={() => setBaselineEdit(null)} disabled={busy}>Huỷ</button></div>
      <div className="form-grid">
        <label>Tên baseline<input value={baselineEdit.name} onChange={(event) => setBaselineEdit({ ...baselineEdit, name: event.target.value })} /></label>
        <label>Tolerance<input type="number" step="any" value={baselineEdit.tolerance} onChange={(event) => setBaselineEdit({ ...baselineEdit, tolerance: event.target.value })} /></label>
        <label>Action level<input type="number" step="any" value={baselineEdit.actionLevel} onChange={(event) => setBaselineEdit({ ...baselineEdit, actionLevel: event.target.value })} /></label>
        <label>Có hiệu lực đến<input type="datetime-local" value={baselineEdit.effectiveTo} onChange={(event) => setBaselineEdit({ ...baselineEdit, effectiveTo: event.target.value })} /></label>
      </div>
      <p className="form-hint">Version và giá trị baseline gốc không bị ghi đè. Revision hiện tại là {baselineEdit.expectedVersion}; nếu người khác đã sửa trước đó, API sẽ trả conflict để tải lại.</p>
      <button disabled={busy || !baselineEdit.name.trim()} onClick={() => updateBaseline({
        id: baselineEdit.id,
        expectedVersion: baselineEdit.expectedVersion,
        patch: {
          name: baselineEdit.name.trim(),
          tolerance: baselineEdit.tolerance === '' ? null : Number(baselineEdit.tolerance),
          action_level: baselineEdit.actionLevel === '' ? null : Number(baselineEdit.actionLevel),
          effective_to: baselineEdit.effectiveTo ? new Date(baselineEdit.effectiveTo).toISOString() : null
        }
      })}>Lưu baseline revision</button>
    </section>}
    <section className="panel trend-lifecycle-panel" aria-label="Quản lý baseline version">
      <div className="panel-heading"><div><p className="eyebrow">BASELINE LIFECYCLE</p><h2>Baseline versions</h2></div><strong>{baselines?.length ?? '—'}</strong></div>
      {baselines?.length ? <div className="table-wrap"><table><thead><tr><th>Machine / metric</th><th>Version</th><th>Giá trị</th><th>Hiệu lực</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{baselines.map((item) => <tr key={item.id}><td><strong>{machineName(item.machine_id)}</strong><small className="table-subtitle">{item.metric_key} · {item.unit}</small></td><td>{item.version_number}</td><td>{item.baseline_value} · tol {item.tolerance ?? '—'} · action {item.action_level ?? '—'}</td><td>{dateLabel(item.effective_from)}{item.effective_to ? ` – ${dateLabel(item.effective_to)}` : ' – mở'}</td><td><span className={item.status === 'ARCHIVED' ? 'status-badge status-badge--warning' : 'status-badge'}>{item.status}</span></td><td><div className="table-actions"><button className="button-secondary" disabled={busy} onClick={() => beginBaselineEdit(item)}>Sửa</button>{item.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => updateBaseline({ id: item.id, expectedVersion: item.version_number, patch: { status: 'ARCHIVED' } })}>Archive</button>}</div></td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có baseline version.</p>}
    </section>
    {eventEdit && <section className="panel trend-lifecycle-editor" aria-label="Chỉnh sửa maintenance marker">
      <div className="panel-heading"><div><p className="eyebrow">MAINTENANCE REVISION {eventEdit.expectedRevision}</p><h2>Chỉnh sửa maintenance marker</h2></div><button className="button-secondary" onClick={() => setEventEdit(null)} disabled={busy}>Huỷ</button></div>
      <div className="form-grid">
        <label>Loại event<input value={eventEdit.eventType} onChange={(event) => setEventEdit({ ...eventEdit, eventType: event.target.value })} /></label>
        <label>Tiêu đề<input value={eventEdit.title} onChange={(event) => setEventEdit({ ...eventEdit, title: event.target.value })} /></label>
        <label>Bắt đầu<input type="datetime-local" value={eventEdit.startedAt} onChange={(event) => setEventEdit({ ...eventEdit, startedAt: event.target.value })} /></label>
        <label>Kết thúc<input type="datetime-local" value={eventEdit.endedAt} onChange={(event) => setEventEdit({ ...eventEdit, endedAt: event.target.value })} /></label>
        <label>Ghi chú<textarea value={eventEdit.notes} onChange={(event) => setEventEdit({ ...eventEdit, notes: event.target.value })} /></label>
      </div>
      <p className="form-hint">Revision hiện tại là {eventEdit.expectedRevision}. Nếu revision đã thay đổi, thao tác bị từ chối và không tạo bản ghi một phần.</p>
      <button disabled={busy || !eventEdit.title.trim() || !eventEdit.startedAt} onClick={() => updateEvent({
        id: eventEdit.id,
        expectedRevision: eventEdit.expectedRevision,
        patch: {
          event_type: eventEdit.eventType.trim(),
          title: eventEdit.title.trim(),
          started_at: new Date(eventEdit.startedAt).toISOString(),
          ended_at: eventEdit.endedAt ? new Date(eventEdit.endedAt).toISOString() : null,
          notes: eventEdit.notes || null
        }
      })}>Lưu maintenance revision</button>
    </section>}
    <section className="panel trend-lifecycle-panel" aria-label="Quản lý maintenance marker">
      <div className="panel-heading"><div><p className="eyebrow">MAINTENANCE REVISION HISTORY</p><h2>Maintenance markers</h2></div><strong>{events?.length ?? '—'}</strong></div>
      {events?.length ? <div className="table-wrap"><table><thead><tr><th>Machine / marker</th><th>Khoảng thời gian</th><th>Revision</th><th>Trạng thái</th><th>Thao tác</th></tr></thead><tbody>{events.map((item) => <tr key={item.id}><td><strong>{item.title}</strong><small className="table-subtitle">{machineName(item.machine_id)} · {item.event_type}</small></td><td>{dateLabel(item.started_at)}{item.ended_at ? ` – ${dateLabel(item.ended_at)}` : ''}</td><td>{item.revision_number}</td><td><span className={item.status === 'ARCHIVED' ? 'status-badge status-badge--warning' : 'status-badge'}>{item.status}</span></td><td><div className="table-actions"><button className="button-secondary" disabled={busy} onClick={() => beginEventEdit(item)}>Sửa</button>{item.status !== 'ARCHIVED' && <button className="button-secondary" disabled={busy} onClick={() => updateEvent({ id: item.id, expectedRevision: item.revision_number, patch: { status: 'ARCHIVED' } })}>Archive</button>}</div></td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có maintenance marker.</p>}
    </section>
  </>
}

export function TrendPage() {
  const { session } = useAuth()
  const accessToken = session?.access_token
  const queryClient = useQueryClient()
  const bootstrap = useQuery({ queryKey: ['session', accessToken], queryFn: () => apiClient.bootstrap(accessToken!), enabled: Boolean(accessToken), retry: false })
  const organizationId = bootstrap.data?.organization.id
  const sites = useQuery({ queryKey: ['trend-sites', organizationId, accessToken], queryFn: () => apiClient.sites(accessToken!, organizationId!), enabled: Boolean(accessToken && organizationId), retry: false })
  const machineQueries = useQueries({ queries: (sites.data?.items ?? []).map((site) => ({ queryKey: ['trend-machines', organizationId, site.id, accessToken], queryFn: () => apiClient.machines(accessToken!, organizationId!, site.id), enabled: Boolean(accessToken && organizationId), retry: false })) })
  const machines = useMemo(() => machineQueries.flatMap((query) => query.data?.items ?? []), [machineQueries])
  const [selectedMachineIds, setSelectedMachineIds] = useState<string[]>([])
  const [metricKey, setMetricKey] = useState('')
  const [aggregate, setAggregate] = useState<'raw' | 'day' | 'week'>('raw')
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')
  const [timezone, setTimezone] = useState('Asia/Ho_Chi_Minh')
  const [energy, setEnergy] = useState('')
  const [detector, setDetector] = useState('')
  const [phantom, setPhantom] = useState('')
  const [beamQuality, setBeamQuality] = useState('')
  const [acquisitionMode, setAcquisitionMode] = useState('')
  const [protocolKey, setProtocolKey] = useState('')
  const [qaCycle, setQaCycle] = useState('')
  const [message, setMessage] = useState<string>()
  const [baselineMachineId, setBaselineMachineId] = useState('')
  const [baselineMetric, setBaselineMetric] = useState('output_factor')
  const [baselineUnit, setBaselineUnit] = useState('%')
  const [baselineValue, setBaselineValue] = useState('100')
  const [baselineTolerance, setBaselineTolerance] = useState('2')
  const [baselineActionLevel, setBaselineActionLevel] = useState('')
  const [baselineEffectiveFrom, setBaselineEffectiveFrom] = useState(() => localDateTimeValue())
  const [baselineEffectiveTo, setBaselineEffectiveTo] = useState('')
  const [baselineEdit, setBaselineEdit] = useState<BaselineEditState | null>(null)
  const [eventMachineId, setEventMachineId] = useState('')
  const [eventType, setEventType] = useState('MAINTENANCE')
  const [eventTitle, setEventTitle] = useState('')
  const [eventStartedAt, setEventStartedAt] = useState('')
  const [eventEndedAt, setEventEndedAt] = useState('')
  const [eventNotes, setEventNotes] = useState('')
  const [eventEdit, setEventEdit] = useState<MaintenanceEditState | null>(null)

  const queryParams = useMemo(() => ({
    machine_ids: selectedMachineIds,
    metric_key: metricKey || undefined,
    from: from ? new Date(from).toISOString() : undefined,
    to: to ? new Date(to).toISOString() : undefined,
    timezone,
    aggregate,
    energy: energy || undefined,
    detector: detector || undefined,
    phantom: phantom || undefined,
    beam_quality: beamQuality || undefined,
    acquisition_mode: acquisitionMode || undefined,
    protocol_key: protocolKey || undefined,
    qa_cycle: qaCycle || undefined,
  }), [acquisitionMode, aggregate, beamQuality, detector, energy, from, metricKey, phantom, protocolKey, qaCycle, selectedMachineIds, timezone, to])
  const trend = useQuery({ queryKey: ['trend', organizationId, accessToken, queryParams], queryFn: () => apiClient.trend(accessToken!, organizationId!, queryParams), enabled: Boolean(accessToken && organizationId), retry: false })
  const events = useQuery({ queryKey: ['trend-events', organizationId, accessToken], queryFn: () => apiClient.trendEvents(accessToken!, organizationId!), enabled: Boolean(accessToken && organizationId), retry: false })
  const baselines = useQuery({ queryKey: ['trend-baselines', organizationId, accessToken], queryFn: () => apiClient.trendBaselines(accessToken!, organizationId!), enabled: Boolean(accessToken && organizationId), retry: false })
  const rebuild = useMutation({ mutationFn: () => apiClient.rebuildTrend(accessToken!, organizationId!), onSuccess: (result) => { setMessage(`Đã rebuild trend: ${result.created_points} điểm mới, ${result.existing_points} điểm đã có.`); void trend.refetch() }, onError: (error) => setMessage(errorMessage(error)) })
  const createBaseline = useMutation({ mutationFn: () => apiClient.createTrendBaseline(accessToken!, organizationId!, { machine_id: baselineMachineId || machines[0]?.id || '', metric_key: baselineMetric, unit: baselineUnit, name: `Baseline ${baselineMetric}`, baseline_value: Number(baselineValue), tolerance: baselineTolerance ? Number(baselineTolerance) : undefined, action_level: baselineActionLevel ? Number(baselineActionLevel) : undefined, effective_from: new Date(baselineEffectiveFrom).toISOString(), effective_to: baselineEffectiveTo ? new Date(baselineEffectiveTo).toISOString() : undefined }), onSuccess: () => { setMessage('Đã tạo baseline version mới.'); void queryClient.invalidateQueries({ queryKey: ['trend-baselines', organizationId] }); void trend.refetch() }, onError: (error) => setMessage(errorMessage(error)) })
  const updateBaseline = useMutation({ mutationFn: (input: { id: string; expectedVersion: number; patch: { name?: string; tolerance?: number | null; action_level?: number | null; effective_to?: string | null; status?: 'ACTIVE' | 'ARCHIVED' } }) => apiClient.updateTrendBaseline(accessToken!, input.id, { expected_version: input.expectedVersion, ...input.patch }), onSuccess: (_, input) => { setMessage(input.patch.status === 'ARCHIVED' ? 'Đã archive baseline version.' : 'Đã cập nhật baseline version.'); setBaselineEdit(null); void queryClient.invalidateQueries({ queryKey: ['trend-baselines', organizationId] }); void trend.refetch() }, onError: (error) => setMessage(errorMessage(error)) })
  const createEvent = useMutation({ mutationFn: () => apiClient.createTrendEvent(accessToken!, organizationId!, { machine_id: eventMachineId || machines[0]?.id || '', event_type: eventType, title: eventTitle, started_at: eventStartedAt ? new Date(eventStartedAt).toISOString() : new Date().toISOString(), ended_at: eventEndedAt ? new Date(eventEndedAt).toISOString() : undefined, notes: eventNotes }), onSuccess: () => { setMessage('Đã ghi maintenance marker.'); setEventTitle(''); setEventEndedAt(''); setEventNotes(''); void queryClient.invalidateQueries({ queryKey: ['trend-events', organizationId] }); void trend.refetch() }, onError: (error) => setMessage(errorMessage(error)) })
  const updateEvent = useMutation({ mutationFn: (input: { id: string; expectedRevision: number; patch: { event_type?: string; title?: string; started_at?: string; ended_at?: string | null; notes?: string | null; status?: 'ACTIVE' | 'ARCHIVED' } }) => apiClient.updateTrendEvent(accessToken!, input.id, { expected_revision: input.expectedRevision, ...input.patch }), onSuccess: (_, input) => { setMessage(input.patch.status === 'ARCHIVED' ? 'Đã archive maintenance marker.' : 'Đã cập nhật maintenance marker.'); setEventEdit(null); void queryClient.invalidateQueries({ queryKey: ['trend-events', organizationId] }); void trend.refetch() }, onError: (error) => setMessage(errorMessage(error)) })

  const beginBaselineEdit = (item: BaselineResource) => setBaselineEdit({
    id: item.id,
    expectedVersion: item.version_number,
    name: item.name,
    tolerance: item.tolerance === null ? '' : String(item.tolerance),
    actionLevel: item.action_level === null ? '' : String(item.action_level),
    effectiveTo: localDateTimeFromIso(item.effective_to)
  })

  const beginEventEdit = (item: MaintenanceEventResource) => setEventEdit({
    id: item.id,
    expectedRevision: item.revision_number,
    eventType: item.event_type,
    title: item.title,
    startedAt: localDateTimeFromIso(item.started_at),
    endedAt: localDateTimeFromIso(item.ended_at),
    notes: item.notes ?? ''
  })

  if (bootstrap.isPending || sites.isPending) return <main className="auth-state">Đang tải Trend workspace…</main>
  const initialError = bootstrap.error ?? sites.error
  if (initialError || !organizationId) return <div className="page"><section className="alert alert--error"><h1>Không thể mở Trend workspace</h1><p>{errorMessage(initialError)}</p><button onClick={() => void Promise.all([bootstrap.refetch(), sites.refetch()])}>Thử lại</button></section></div>
  const data: TrendResource | undefined = trend.data
  const failure = trend.error ?? events.error ?? baselines.error
  const busy = rebuild.isPending || createBaseline.isPending || updateBaseline.isPending || createEvent.isPending || updateEvent.isPending
  return <div className="page">
    <TrendLifecyclePanel baselines={baselines.data} events={events.data} machines={machines} baselineEdit={baselineEdit} setBaselineEdit={setBaselineEdit} eventEdit={eventEdit} setEventEdit={setEventEdit} busy={busy} beginBaselineEdit={beginBaselineEdit} beginEventEdit={beginEventEdit} updateBaseline={updateBaseline.mutate} updateEvent={updateEvent.mutate} />
    <header className="page-header"><div><p className="eyebrow">P10 · MOD-08</p><h1>Xu hướng QA</h1><p>Theo dõi điểm đo tương thích theo thời gian, giữ nguyên nguồn run/case và đánh dấu baseline, outlier, bảo trì.</p></div><div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">QA Archive</Link><span className="status-badge">API THẬT</span></div></header>
    {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
    {failure && <section className="alert alert--error" role="alert"><h2>Không thể tải đầy đủ Trend</h2><p>{errorMessage(failure)}</p><button onClick={() => void Promise.all([trend.refetch(), events.refetch(), baselines.refetch()])}>Thử lại</button></section>}
    <section className="panel trend-filter-panel"><div className="panel-heading"><div><p className="eyebrow">FILTER / COMPATIBILITY</p><h2>Chọn chuỗi dữ liệu</h2></div><button disabled={busy} onClick={() => rebuild.mutate()}>Rebuild projection</button></div><div className="trend-filter-grid">
      <label>Machine (Ctrl để chọn nhiều)<select multiple value={selectedMachineIds} onChange={(event) => setSelectedMachineIds(Array.from(event.target.selectedOptions, (option) => option.value))}>{machines.map((machine) => <option key={machine.id} value={machine.id}>{machine.display_name} · {machine.stable_machine_id}</option>)}</select></label>
      <label>Metric key<input value={metricKey} onChange={(event) => setMetricKey(event.target.value)} placeholder="output_factor" /></label>
      <label>Khoảng gộp<select value={aggregate} onChange={(event) => setAggregate(event.target.value as typeof aggregate)}><option value="raw">Raw</option><option value="day">Theo ngày</option><option value="week">Theo tuần</option></select></label>
      <label>Múi giờ<input value={timezone} onChange={(event) => setTimezone(event.target.value)} /></label>
      <label>Từ<input type="datetime-local" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
      <label>Đến<input type="datetime-local" value={to} onChange={(event) => setTo(event.target.value)} /></label>
      <label>Energy<input value={energy} onChange={(event) => setEnergy(event.target.value)} placeholder="6X" /></label>
      <label>Detector<input value={detector} onChange={(event) => setDetector(event.target.value)} placeholder="Detector ID" /></label>
      <label>Phantom<input value={phantom} onChange={(event) => setPhantom(event.target.value)} placeholder="Phantom ID" /></label>
      <label>Beam quality<input value={beamQuality} onChange={(event) => setBeamQuality(event.target.value)} placeholder="TPR20/10" /></label>
      <label>Acquisition mode<input value={acquisitionMode} onChange={(event) => setAcquisitionMode(event.target.value)} placeholder="Measurement mode" /></label>
      <label>Protocol key<input value={protocolKey} onChange={(event) => setProtocolKey(event.target.value)} placeholder="MACHINE_QA_BASELINE" /></label>
      <label>QA cycle<input value={qaCycle} onChange={(event) => setQaCycle(event.target.value)} placeholder="DAILY" /></label>
    </div><p className="form-hint">Không chọn machine nghĩa là tất cả machine trong organization. Context khác unit/energy/detector/phantom/beam quality/acquisition/protocol sẽ tách thành series riêng, không nối sai nghĩa. Khoảng thời gian dùng mốc bắt đầu inclusive và kết thúc exclusive.</p></section>
    <section className="metric-grid"><div className="metric-card"><p>Điểm phù hợp</p><strong>{data?.total_points ?? '—'}</strong><small>{data?.aggregate ?? aggregate} · {data?.timezone ?? timezone}</small></div><div className="metric-card"><p>Compatible series</p><strong>{data?.series.length ?? '—'}</strong><small>Không trộn context khác nghĩa</small></div><div className="metric-card"><p>Baseline</p><strong>{data?.baselines.length ?? baselines.data?.length ?? '—'}</strong><small>Version trong organization</small></div><div className="metric-card"><p>Maintenance</p><strong>{data?.maintenance_events.length ?? events.data?.length ?? '—'}</strong><small>Marker không sửa QA result</small></div></section>
    {data?.warnings.map((warning) => <section className="alert alert--warning" key={warning}><p>{warning}</p></section>)}
    {trend.isPending ? <section className="panel"><p>Đang tải series…</p></section> : data?.series.length ? data.series.map((series) => <SeriesCard key={`${series.machine_id}-${series.metric_key}-${series.compatibility_signature}`} series={series} />) : <section className="panel empty-state"><h2>Chưa có trend point phù hợp</h2><p>Hãy evaluate một Machine QA run, chọn bộ lọc rộng hơn hoặc nhấn rebuild projection. Không tạo điểm 0 để lấp dữ liệu trống.</p></section>}
    <section className="panel"><div className="panel-heading"><div><p className="eyebrow">EXPORT</p><h2>Xuất đúng bộ lọc hiện tại</h2></div><div className="page-header__actions"><button disabled={busy} onClick={async () => { try { const blob = await apiClient.exportTrend(accessToken!, organizationId!, { ...queryParams, export_format: 'CSV' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'rt-connect-trend.csv'; anchor.click(); URL.revokeObjectURL(url); setMessage('Đã tải CSV trend theo bộ lọc hiện tại.') } catch (error) { setMessage(errorMessage(error)) } }}>Tải CSV</button><button disabled={busy} onClick={async () => { try { const blob = await apiClient.exportTrend(accessToken!, organizationId!, { ...queryParams, export_format: 'JSON' }); const url = URL.createObjectURL(blob); const anchor = document.createElement('a'); anchor.href = url; anchor.download = 'rt-connect-trend.json'; anchor.click(); URL.revokeObjectURL(url); setMessage('Đã tải JSON trend theo bộ lọc hiện tại.') } catch (error) { setMessage(errorMessage(error)) } }}>Tải JSON</button></div></div><p className="form-hint">Bản export giữ timezone, aggregate, compatibility signature và source IDs để kiểm tra lại.</p></section>
    <section className="trend-admin-grid"><section className="panel"><div className="panel-heading"><div><p className="eyebrow">BASELINE VERSION</p><h2>Thêm baseline</h2></div></div><div className="form-grid"><label>Machine<select value={baselineMachineId || machines[0]?.id || ''} onChange={(event) => setBaselineMachineId(event.target.value)}>{machines.map((machine) => <option key={machine.id} value={machine.id}>{machine.display_name}</option>)}</select></label><label>Metric<input value={baselineMetric} onChange={(event) => setBaselineMetric(event.target.value)} /></label><label>Unit<input value={baselineUnit} onChange={(event) => setBaselineUnit(event.target.value)} /></label><label>Baseline<input type="number" step="any" value={baselineValue} onChange={(event) => setBaselineValue(event.target.value)} /></label><label>Tolerance<input type="number" step="any" value={baselineTolerance} onChange={(event) => setBaselineTolerance(event.target.value)} /></label><label>Action level<input type="number" step="any" value={baselineActionLevel} onChange={(event) => setBaselineActionLevel(event.target.value)} placeholder="Tuỳ chọn" /></label><label>Có hiệu lực từ<input required type="datetime-local" value={baselineEffectiveFrom} onChange={(event) => setBaselineEffectiveFrom(event.target.value)} /></label><label>Có hiệu lực đến<input type="datetime-local" value={baselineEffectiveTo} onChange={(event) => setBaselineEffectiveTo(event.target.value)} /></label></div><p className="form-hint">Baseline chỉ áp dụng cho điểm có cùng machine/metric/unit và sau mốc hiệu lực. Hãy đặt mốc rõ ràng; không để hệ thống tự áp baseline hồi tố.</p><button disabled={busy || !machines.length || !baselineEffectiveFrom} onClick={() => createBaseline.mutate()}>Tạo version baseline</button></section><section className="panel"><div className="panel-heading"><div><p className="eyebrow">MAINTENANCE EVENT</p><h2>Thêm marker bảo trì</h2></div></div><div className="form-grid"><label>Machine<select value={eventMachineId || machines[0]?.id || ''} onChange={(event) => setEventMachineId(event.target.value)}>{machines.map((machine) => <option key={machine.id} value={machine.id}>{machine.display_name}</option>)}</select></label><label>Loại event<input value={eventType} onChange={(event) => setEventType(event.target.value)} placeholder="MAINTENANCE" /></label><label>Tiêu đề<input value={eventTitle} onChange={(event) => setEventTitle(event.target.value)} placeholder="Thay detector / bảo trì định kỳ" /></label><label>Bắt đầu<input type="datetime-local" value={eventStartedAt} onChange={(event) => setEventStartedAt(event.target.value)} /></label><label>Kết thúc<input type="datetime-local" value={eventEndedAt} onChange={(event) => setEventEndedAt(event.target.value)} /></label><label>Ghi chú<textarea value={eventNotes} onChange={(event) => setEventNotes(event.target.value)} /></label></div><button disabled={busy || !machines.length || !eventTitle.trim()} onClick={() => createEvent.mutate()}>Ghi maintenance marker</button></section></section>
    <section className="panel"><div className="panel-heading"><div><p className="eyebrow">MAINTENANCE TIMELINE</p><h2>Mốc bảo trì trong organization</h2></div><strong>{events.data?.length ?? '—'}</strong></div>{events.data?.length ? <div className="table-wrap"><table><thead><tr><th>Machine</th><th>Mốc</th><th>Khoảng thời gian</th><th>Revision</th><th>Trạng thái</th></tr></thead><tbody>{events.data.map((event) => <tr key={event.id}><td>{event.machine_name}</td><td><strong>{event.title}</strong><small className="table-subtitle">{event.event_type}</small></td><td>{dateLabel(event.started_at)}{event.ended_at ? ` – ${dateLabel(event.ended_at)}` : ''}</td><td>{event.revision_number}</td><td>{event.status}</td></tr>)}</tbody></table></div> : <p className="empty-state">Chưa có maintenance marker.</p>}</section>
  </div>
}
