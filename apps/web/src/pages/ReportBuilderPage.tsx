import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'

import {
  ApiClientError,
  apiClient,
  type DvhRunResource,
  type ReportBlock,
  type ReportRevision,
  type ReportSummary
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'

const blockTypes = [
  'TEXT', 'METADATA', 'METRICS', 'GAMMA_MAP', 'DOSE_PROFILE', 'DVH', 'TREND_CHART',
  'COMPARISON', 'BIOLOGICAL', 'COMMENTS', 'PROVENANCE', 'TABLE', 'IMAGE', 'WARNING'
] as const
const sourceTypes = ['CUSTOM', 'QA_CASE', 'MACHINE_QA', 'GAMMA', 'DVH', 'BIOLOGICAL'] as const
type SourceType = (typeof sourceTypes)[number]
type EditableBlock = ReportBlock & { sort_order: number }

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return `${error.message} (${error.code})`
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function defaultBlocks(): EditableBlock[] {
  return [
    { stable_block_id: 'title', block_type: 'TEXT', label: 'Ghi chú mở đầu', sort_order: 0, is_visible: true, config: { content: '' }, source_binding: {} },
    { stable_block_id: 'metrics', block_type: 'METRICS', label: 'Metrics', sort_order: 1, is_visible: true, config: {}, source_binding: {} },
    { stable_block_id: 'provenance', block_type: 'PROVENANCE', label: 'Provenance', sort_order: 2, is_visible: true, config: {}, source_binding: {} }
  ]
}

function blockFromRevision(block: ReportRevision['blocks'][number]): EditableBlock {
  return {
    stable_block_id: block.stable_block_id,
    block_type: block.block_type,
    label: block.label,
    sort_order: block.sort_order,
    is_visible: block.is_visible,
    config: block.config,
    source_binding: block.source_binding
  }
}

function textValue(value: unknown): string {
  if (typeof value === 'string') return value
  return value === undefined ? '' : JSON.stringify(value, null, 2)
}

export function ReportBuilderPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const accessToken = session?.access_token
  const [selectedReportKey, setSelectedReportKey] = useState<string>()
  const [title, setTitle] = useState('Clinical report')
  const [sourceType, setSourceType] = useState<SourceType>('CUSTOM')
  const [sourceId, setSourceId] = useState('')
  const [dvhCaseId, setDvhCaseId] = useState('')
  const [templateId, setTemplateId] = useState('')
  const [blocks, setBlocks] = useState<EditableBlock[]>(defaultBlocks)
  const [message, setMessage] = useState<string>()
  const [editorError, setEditorError] = useState<string>()

  const bootstrap = useQuery({
    queryKey: ['session', accessToken],
    queryFn: () => apiClient.bootstrap(accessToken!),
    enabled: Boolean(accessToken), retry: false
  })
  const organizationId = bootstrap.data?.organization.id
  const reports = useQuery({
    queryKey: ['reports', organizationId, accessToken],
    queryFn: () => apiClient.reports(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const templates = useQuery({
    queryKey: ['report-templates', organizationId, accessToken],
    queryFn: () => apiClient.reportTemplates(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const cases = useQuery({
    queryKey: ['qa-cases-for-reports', organizationId, accessToken],
    queryFn: () => apiClient.qaCases(accessToken!, organizationId!),
    enabled: Boolean(accessToken && organizationId), retry: false
  })
  const dvhRuns = useQuery({
    queryKey: ['dvh-runs-for-report', organizationId, dvhCaseId, accessToken],
    queryFn: () => apiClient.dvhRuns(accessToken!, organizationId!, dvhCaseId!),
    enabled: Boolean(accessToken && organizationId && sourceType === 'DVH' && dvhCaseId), retry: false
  })
  const revisions = useQuery({
    queryKey: ['report-revisions', selectedReportKey, accessToken],
    queryFn: () => apiClient.reportRevisions(accessToken!, selectedReportKey!),
    enabled: Boolean(accessToken && selectedReportKey), retry: false
  })
  const currentRevision = revisions.data?.[0]
  const selectedReport = useMemo<ReportSummary | undefined>(
    () => reports.data?.items.find((item) => item.report_key === selectedReportKey),
    [reports.data, selectedReportKey]
  )

  // Hydrate the controlled editor when the remote revision selected by the user changes.
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (!currentRevision) return
    setTitle(currentRevision.title)
    setSourceType(currentRevision.source_type as SourceType)
    setSourceId(currentRevision.source_id ?? '')
    const payload = currentRevision.source_snapshot.payload
    if (currentRevision.source_type === 'DVH' && typeof payload === 'object' && payload !== null && 'qa_case_id' in payload && typeof payload.qa_case_id === 'string') {
      setDvhCaseId(payload.qa_case_id)
    } else {
      setDvhCaseId('')
    }
    setTemplateId(currentRevision.template_version_id ?? '')
    setBlocks(currentRevision.blocks.map(blockFromRevision))
    setEditorError(undefined)
  }, [currentRevision])
  /* eslint-enable react-hooks/set-state-in-effect */

  const saveMutation = useMutation({
    mutationFn: () => {
      const cleanBlocks = blocks.map((block, index) => ({
        stable_block_id: block.stable_block_id,
        block_type: block.block_type,
        label: block.label,
        sort_order: index,
        is_visible: block.is_visible,
        config: block.config,
        source_binding: block.source_binding
      }))
      if (selectedReportKey && currentRevision) {
        return apiClient.createReportRevision(accessToken!, selectedReportKey, {
          expected_revision: currentRevision.revision_number,
          title: title.trim(),
          source_type: sourceType,
          ...(sourceId.trim() ? { source_id: sourceId.trim() } : {}),
          ...(templateId ? { template_version_id: templateId } : {}),
          blocks: cleanBlocks
        })
      }
      return apiClient.createReport(accessToken!, organizationId!, {
        source_type: sourceType,
        ...(sourceId.trim() ? { source_id: sourceId.trim() } : {}),
        title: title.trim(),
        ...(templateId ? { template_version_id: templateId } : {}),
        blocks: cleanBlocks
      })
    },
    onSuccess: (revision) => {
      setSelectedReportKey(revision.report_key)
      setMessage(`Đã lưu report revision ${revision.revision_number}. Snapshot SHA-256: ${revision.content_sha256.slice(0, 16)}…`)
      void queryClient.invalidateQueries({ queryKey: ['reports', organizationId] })
      void queryClient.invalidateQueries({ queryKey: ['report-revisions', revision.report_key] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const exportMutation = useMutation({
    mutationFn: (format: 'JSON' | 'CSV' | 'PDF' | 'PNG') => apiClient.exportReport(
      accessToken!, selectedReportKey!, currentRevision!.id,
      { export_format: format, idempotency_key: `report-${currentRevision!.id}-${format.toLowerCase()}` }
    ),
    onSuccess: (job) => {
      setMessage(`Đã tạo export ${job.export_format} (${job.byte_size?.toLocaleString('vi-VN') ?? '—'} bytes).`)
      if (job.download_url) window.open(job.download_url, '_blank', 'noopener,noreferrer')
    },
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || reports.isPending) return <main className="auth-state">Đang tải Report Builder…</main>
  const failure = bootstrap.error ?? reports.error
  if (failure || !organizationId || !reports.data) return <div className="page"><section className="alert alert--error"><h1>Không thể mở Report Builder</h1><p>{errorMessage(failure)}</p><button onClick={() => { void reports.refetch() }}>Thử lại</button></section></div>

  const updateBlock = (index: number, update: Partial<EditableBlock>) => {
    setBlocks((current) => current.map((block, blockIndex) => blockIndex === index ? { ...block, ...update } : block))
  }
  const updateJson = (index: number, key: 'config' | 'source_binding', value: string) => {
    try {
      const parsed: unknown = JSON.parse(value || '{}')
      if (typeof parsed !== 'object' || parsed === null || Array.isArray(parsed)) throw new Error('object')
      updateBlock(index, { [key]: parsed as Record<string, unknown> })
      setEditorError(undefined)
    } catch {
      setEditorError(`Block ${index + 1}: ${key} phải là một JSON object hợp lệ.`)
    }
  }
  const addBlock = () => {
    setBlocks((current) => [...current, {
      stable_block_id: `block-${current.length + 1}`,
      block_type: 'TEXT', label: 'Block mới', sort_order: current.length, is_visible: true,
      config: { content: '' }, source_binding: {}
    }])
  }
  const moveBlock = (index: number, direction: -1 | 1) => {
    const target = index + direction
    if (target < 0 || target >= blocks.length) return
    setBlocks((current) => {
      const next = [...current]
      const [item] = next.splice(index, 1)
      next.splice(target, 0, item)
      return next.map((block, order) => ({ ...block, sort_order: order }))
    })
  }
  const newReport = () => {
    setSelectedReportKey(undefined)
    setTitle('Clinical report')
    setSourceType('CUSTOM')
    setSourceId('')
    setDvhCaseId('')
    setTemplateId('')
    setBlocks(defaultBlocks())
    setMessage('Đã mở report mới; chưa ghi vào database.')
  }

  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">P9 · MOD-07</p><h1>Trình biên soạn Báo cáo</h1><p>Toàn quyền sắp xếp, ẩn, đổi tên và cấu hình block. Mỗi lần lưu tạo revision mới với source snapshot và provenance độc lập.</p></div>
        <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">QA Archive</Link><span className="status-badge">API THẬT</span></div>
      </header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
      <div className="report-layout">
        <aside className="panel report-list-panel">
          <div className="panel-heading"><div><p className="eyebrow">REPORT HISTORY</p><h2>Reports</h2></div><strong>{reports.data.total}</strong></div>
          <button onClick={newReport}>+ Report mới</button>
          <div className="report-list">
            {reports.data.items.map((report) => <button key={report.report_key} className={report.report_key === selectedReportKey ? 'report-list__item report-list__item--selected' : 'report-list__item'} onClick={() => setSelectedReportKey(report.report_key)}><strong>{report.title}</strong><small>{report.source_type} · rev {report.latest_revision_number}</small><code>{report.report_key.slice(0, 8)}…</code></button>)}
            {!reports.data.items.length && <p className="empty-state">Chưa có report. Hãy tạo report đầu tiên.</p>}
          </div>
          {templates.data && <div className="report-template-box"><label>Template version<select value={templateId} onChange={(event) => setTemplateId(event.target.value)}><option value="">Không dùng template</option>{templates.data.items.map((template) => <option key={template.id} value={template.id}>{template.name} · v{template.version_number} · {template.status}</option>)}</select></label></div>}
        </aside>
        <section className="panel report-editor-panel">
          <div className="panel-heading"><div><p className="eyebrow">EDITOR</p><h2>{selectedReport ? `Revision tiếp theo của ${selectedReport.title}` : 'Report draft mới'}</h2></div>{currentRevision && <span className="status-badge">REV {currentRevision.revision_number}</span>}</div>
          <div className="report-form-grid"><label>Tiêu đề report<input value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>Loại source<select value={sourceType} onChange={(event) => { const next = event.target.value as SourceType; setSourceType(next); setSourceId(''); setDvhCaseId('') }}>{sourceTypes.map((type) => <option key={type}>{type}</option>)}</select></label><label>Source ID<input value={sourceId} onChange={(event) => setSourceId(event.target.value)} placeholder={sourceType === 'CUSTOM' || sourceType === 'BIOLOGICAL' ? 'Không bắt buộc' : sourceType === 'DVH' ? 'UUID của DVH run' : 'UUID của source run/case'} /></label>{sourceType === 'QA_CASE' && cases.data && <label>Chọn nhanh QA case<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Chọn QA case</option>{cases.data.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}{sourceType === 'DVH' && cases.data && <label>QA case chứa DVH run<select value={dvhCaseId} onChange={(event) => { setDvhCaseId(event.target.value); setSourceId('') }}><option value="">Chọn QA case</option>{cases.data.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}{sourceType === 'DVH' && dvhCaseId && <label>Chọn DVH run<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Chọn DVH run</option>{(dvhRuns.data?.items ?? []).map((run: DvhRunResource) => <option key={run.id} value={run.id}>ROI #{run.roi_number} · {run.id.slice(0, 8)}… · {run.status}</option>)}</select>{dvhRuns.error && <small className="form-hint">Không tải được lịch sử DVH; có thể nhập UUID thủ công.</small>}</label>}</div>
          <p className="form-hint">Source snapshot chỉ được chụp khi lưu revision. Source thay đổi sau đó không sửa report cũ; revision tiếp theo có thể chụp dữ liệu mới.</p>
          {editorError && <div className="alert alert--error"><p>{editorError}</p></div>}
          <div className="report-block-heading"><div><p className="eyebrow">BLOCK CANVAS</p><h2>Cấu trúc report</h2></div><button className="button-secondary" onClick={addBlock}>+ Thêm block</button></div>
          <div className="report-block-list">{blocks.map((block, index) => <article className="report-block-editor" key={block.stable_block_id}>
            <div className="report-block-editor__top"><strong>#{index + 1}</strong><input aria-label={`Block ${index + 1} ID`} value={block.stable_block_id} onChange={(event) => updateBlock(index, { stable_block_id: event.target.value })} /><select aria-label={`Block ${index + 1} type`} value={block.block_type} onChange={(event) => updateBlock(index, { block_type: event.target.value })}>{blockTypes.map((type) => <option key={type}>{type}</option>)}</select><label className="checkbox-row"><input type="checkbox" checked={block.is_visible} onChange={(event) => updateBlock(index, { is_visible: event.target.checked })} /> Hiển thị</label><div className="table-actions"><button className="button-secondary" onClick={() => moveBlock(index, -1)} disabled={index === 0}>↑</button><button className="button-secondary" onClick={() => moveBlock(index, 1)} disabled={index === blocks.length - 1}>↓</button><button className="button-secondary" onClick={() => setBlocks((current) => current.filter((_, blockIndex) => blockIndex !== index))}>Xóa</button></div></div>
            <label>Tên hiển thị<input value={block.label} onChange={(event) => updateBlock(index, { label: event.target.value })} /></label>
            <div className="report-json-grid"><label>Config JSON<textarea value={JSON.stringify(block.config, null, 2)} onChange={(event) => updateJson(index, 'config', event.target.value)} rows={4} /></label><label>Source binding JSON<textarea value={JSON.stringify(block.source_binding, null, 2)} onChange={(event) => updateJson(index, 'source_binding', event.target.value)} rows={4} /></label></div>
          </article>)}</div>
          <div className="report-editor-actions"><button disabled={saveMutation.isPending || Boolean(editorError) || !title.trim()} onClick={() => saveMutation.mutate()}>{saveMutation.isPending ? 'Đang lưu…' : currentRevision ? 'Lưu revision mới' : 'Lưu report'}</button>{currentRevision && <span className="form-hint">Expected revision: {currentRevision.revision_number}</span>}</div>
        </section>
      </div>
      <section className="panel report-preview-panel"><div className="panel-heading"><div><p className="eyebrow">PREVIEW / EXPORT</p><h2>Preview snapshot hiện tại</h2></div>{currentRevision && <code>{currentRevision.content_sha256}</code>}</div><div className="report-preview"><h3>{title || 'Untitled report'}</h3><p>Source: {sourceType}{sourceId ? ` · ${sourceId}` : ''}</p>{blocks.filter((block) => block.is_visible).sort((left, right) => left.sort_order - right.sort_order).map((block) => <article key={block.stable_block_id}><strong>{block.label}</strong><small>{block.block_type}</small><pre>{textValue(block.config.content) || JSON.stringify(block.config, null, 2)}</pre></article>)}</div>{currentRevision && <div className="report-export-actions"><strong>Export revision {currentRevision.revision_number}</strong>{(['JSON', 'CSV', 'PDF', 'PNG'] as const).map((format) => <button key={format} className="button-secondary" disabled={exportMutation.isPending} onClick={() => exportMutation.mutate(format)}>{exportMutation.isPending ? 'Đang tạo…' : `Tải ${format}`}</button>)}</div>}</section>
    </div>
  )
}
