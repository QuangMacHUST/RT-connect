import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useSearchParams } from 'react-router-dom'

import {
  ApiClientError,
  apiClient,
  type DvhRunResource,
  type ReportBlock,
  type ReportRevision,
  type ReportSummary
} from '../api/client'
import { useAuth } from '../auth/AuthProvider'
import {
  reportBlockLabel,
  reportExportLabel,
  reportRunStatusLabel,
  reportSourceLabel,
  reportTemplateStatusLabel
} from './reportBuilderLabels'

const blockTypes = [
  'TEXT', 'METADATA', 'METRICS', 'GAMMA_MAP', 'DOSE_PROFILE', 'DVH', 'TREND_CHART',
  'COMPARISON', 'BIOLOGICAL', 'COMMENTS', 'PROVENANCE', 'TABLE', 'IMAGE', 'WARNING'
] as const
const sourceTypes = ['CUSTOM', 'QA_CASE', 'MACHINE_QA', 'PYLINAC_QA', 'GAMMA', 'DVH', 'BIOLOGICAL'] as const
type SourceType = (typeof sourceTypes)[number]
type EditableBlock = ReportBlock & { sort_order: number }

function errorMessage(error: unknown): string {
  if (error instanceof ApiClientError) return error.message
  return 'Không thể hoàn tất thao tác. Hãy thử lại và kiểm tra kết nối API.'
}

function defaultBlocks(): EditableBlock[] {
  return [
    { stable_block_id: 'title', block_type: 'TEXT', label: 'Ghi chú mở đầu', sort_order: 0, is_visible: true, config: { content: '' }, source_binding: {} },
    { stable_block_id: 'metrics', block_type: 'METRICS', label: 'Chỉ số kết quả', sort_order: 1, is_visible: true, config: {}, source_binding: {} },
    { stable_block_id: 'provenance', block_type: 'PROVENANCE', label: 'Nguồn và phiên bản', sort_order: 2, is_visible: true, config: {}, source_binding: {} }
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

function blockDescription(block: EditableBlock): string {
  if (typeof block.config.content === 'string' && block.config.content.trim()) return block.config.content
  if (block.block_type === 'TEXT' || block.block_type === 'COMMENTS') return 'Chưa có nội dung ghi chú.'
  return 'Nội dung sẽ được lấy từ kết quả và nguồn đã chọn khi xuất báo cáo.'
}

export function ReportBuilderPage() {
  const { session } = useAuth()
  const queryClient = useQueryClient()
  const accessToken = session?.access_token
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedReportKey, setSelectedReportKey] = useState<string | undefined>(() => searchParams.get('reportKey') ?? undefined)
  const [exportKeyNamespace] = useState(() => crypto.randomUUID())
  const [title, setTitle] = useState('Báo cáo kiểm tra chất lượng')
  const [sourceType, setSourceType] = useState<SourceType>('CUSTOM')
  const [sourceId, setSourceId] = useState('')
  const [sourceCaseId, setSourceCaseId] = useState('')
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
    queryKey: ['dvh-runs-for-report', organizationId, sourceCaseId, accessToken],
    queryFn: () => apiClient.dvhRuns(accessToken!, organizationId!, sourceCaseId!),
    enabled: Boolean(accessToken && organizationId && sourceType === 'DVH' && sourceCaseId), retry: false
  })
  const machineQARuns = useQuery({
    queryKey: ['machine-qa-runs-for-report', sourceCaseId, accessToken],
    queryFn: () => apiClient.machineQARuns(accessToken!, sourceCaseId!),
    enabled: Boolean(accessToken && sourceType === 'MACHINE_QA' && sourceCaseId), retry: false
  })
  const pylinacRuns = useQuery({
    queryKey: ['pylinac-runs-for-report', sourceCaseId, accessToken],
    queryFn: () => apiClient.pylinacQARuns(accessToken!, sourceCaseId!),
    enabled: Boolean(accessToken && sourceType === 'PYLINAC_QA' && sourceCaseId), retry: false
  })
  const gammaRuns = useQuery({
    queryKey: ['gamma-runs-for-report', sourceCaseId, accessToken],
    queryFn: () => apiClient.gammaRuns(accessToken!, sourceCaseId!),
    enabled: Boolean(accessToken && sourceType === 'GAMMA' && sourceCaseId), retry: false
  })
  const revisions = useQuery({
    queryKey: ['report-revisions', selectedReportKey, accessToken],
    queryFn: () => apiClient.reportRevisions(accessToken!, selectedReportKey!),
    enabled: Boolean(accessToken && selectedReportKey), retry: false
  })
  const currentRevision = revisions.data?.[0]
  const reportPreview = useQuery({
    queryKey: ['report-preview', selectedReportKey, currentRevision?.id, accessToken],
    queryFn: () => apiClient.reportPreview(accessToken!, selectedReportKey!, currentRevision!.id),
    enabled: Boolean(accessToken && selectedReportKey && currentRevision), retry: false
  })
  const reportExports = useQuery({
    queryKey: ['report-exports', selectedReportKey, currentRevision?.id, accessToken],
    queryFn: () => apiClient.reportExports(accessToken!, selectedReportKey!, currentRevision!.id),
    enabled: Boolean(accessToken && selectedReportKey && currentRevision), retry: false
  })
  const reportPreviewUrl = useMemo(() => reportPreview.data ? URL.createObjectURL(reportPreview.data) : undefined, [reportPreview.data])
  useEffect(() => () => { if (reportPreviewUrl) URL.revokeObjectURL(reportPreviewUrl) }, [reportPreviewUrl])
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
    if (typeof payload === 'object' && payload !== null && 'qa_case_id' in payload && typeof payload.qa_case_id === 'string') {
      setSourceCaseId(payload.qa_case_id)
    } else {
      setSourceCaseId(currentRevision.source_type === 'QA_CASE' ? currentRevision.source_id ?? '' : '')
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
      setMessage(`Đã lưu bản báo cáo ${revision.revision_number}.`)
      void queryClient.invalidateQueries({ queryKey: ['reports', organizationId] })
      void queryClient.invalidateQueries({ queryKey: ['report-revisions', revision.report_key] })
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const exportMutation = useMutation({
    mutationFn: (format: 'JSON' | 'CSV' | 'PDF' | 'PNG') => apiClient.exportReport(
      accessToken!, selectedReportKey!, currentRevision!.id,
      {
        export_format: format,
        idempotency_key: `report-${exportKeyNamespace}-${currentRevision!.id}-${format.toLowerCase()}`
      }
    ),
    onSuccess: (job) => {
      setMessage(`Đã tạo tệp ${reportExportLabel(job.export_format)} (${job.byte_size?.toLocaleString('vi-VN') ?? '—'} byte).`)
      void queryClient.invalidateQueries({ queryKey: ['report-exports', selectedReportKey, currentRevision?.id, accessToken] })
      if (job.download_url) window.open(job.download_url, '_blank', 'noopener,noreferrer')
    },
    onError: (error) => setMessage(errorMessage(error))
  })
  const downloadExportMutation = useMutation({
    mutationFn: (jobId: string) => apiClient.reportExportDownload(accessToken!, jobId),
    onSuccess: (download) => window.open(download.url, '_blank', 'noopener,noreferrer'),
    onError: (error) => setMessage(errorMessage(error))
  })

  if (bootstrap.isPending || reports.isPending) return <main className="auth-state">Đang tải trình biên soạn báo cáo…</main>
  const failure = bootstrap.error ?? reports.error
  if (failure || !organizationId || !reports.data) return <div className="page"><section className="alert alert--error"><h1>Không thể mở trình biên soạn báo cáo</h1><p>{errorMessage(failure)}</p><button onClick={() => { void reports.refetch() }}>Thử lại</button></section></div>

  const updateBlock = (index: number, update: Partial<EditableBlock>) => {
    setBlocks((current) => current.map((block, blockIndex) => blockIndex === index ? { ...block, ...update } : block))
  }
  const updateBlockContent = (index: number, content: string) => {
    updateBlock(index, { config: { ...blocks[index].config, content } })
    setEditorError(undefined)
  }
  const addBlock = () => {
    setBlocks((current) => [...current, {
      stable_block_id: `block-${current.length + 1}`,
      block_type: 'TEXT', label: 'Khối văn bản mới', sort_order: current.length, is_visible: true,
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
    setSearchParams({})
    setTitle('Báo cáo kiểm tra chất lượng')
    setSourceType('CUSTOM')
    setSourceId('')
    setSourceCaseId('')
    setTemplateId('')
    setBlocks(defaultBlocks())
    setMessage('Đã mở báo cáo mới; chưa lưu vào hệ thống.')
  }

  return (
    <div className="page">
      <header className="page-header">
        <div><p className="eyebrow">BÁO CÁO KIỂM TRA CHẤT LƯỢNG</p><h1>Trình biên soạn báo cáo</h1><p>Sắp xếp, ẩn, đổi tên và ghi chú cho từng phần. Mỗi lần lưu tạo một bản báo cáo độc lập từ đúng kết quả đã chọn.</p></div>
        <div className="page-header__actions"><Link className="button-link button-secondary" to="/app/qa">Quay lại kiểm tra chất lượng máy</Link><span className="status-badge">ĐANG KẾT NỐI</span></div>
      </header>
      {message && <section className="alert alert--success" role="status"><p>{message}</p></section>}
      <div className="report-layout">
        <aside className="panel report-list-panel">
          <div className="panel-heading"><div><p className="eyebrow">CÁC BẢN BÁO CÁO</p><h2>Lịch sử báo cáo</h2></div><strong>{reports.data.total}</strong></div>
          <button onClick={newReport}>+ Báo cáo mới</button>
          <div className="report-list">
            {reports.data.items.map((report) => <button key={report.report_key} className={report.report_key === selectedReportKey ? 'report-list__item report-list__item--selected' : 'report-list__item'} onClick={() => setSelectedReportKey(report.report_key)}><strong>{report.title}</strong><small>{reportSourceLabel(report.source_type)} · bản {report.latest_revision_number}</small><span className="table-subtitle">Cập nhật {new Date(report.updated_at).toLocaleDateString('vi-VN')}</span></button>)}
            {!reports.data.items.length && <p className="empty-state">Chưa có báo cáo. Hãy tạo báo cáo đầu tiên.</p>}
          </div>
          {templates.data && <div className="report-template-box"><label>Mẫu báo cáo<select value={templateId} onChange={(event) => setTemplateId(event.target.value)}><option value="">Không dùng mẫu có sẵn</option>{templates.data.items.map((template) => <option key={template.id} value={template.id}>{template.name} · bản {template.version_number} · {reportTemplateStatusLabel(template.status)}</option>)}</select></label></div>}
        </aside>
        <section className="panel report-editor-panel">
          <div className="panel-heading"><div><p className="eyebrow">NỘI DUNG BÁO CÁO</p><h2>{selectedReport ? `Bản tiếp theo của ${selectedReport.title}` : 'Bản báo cáo mới'}</h2></div>{currentRevision && <span className="status-badge">BẢN {currentRevision.revision_number}</span>}</div>
          <div className="report-form-grid"><label>Tiêu đề báo cáo<input value={title} onChange={(event) => setTitle(event.target.value)} /></label><label>Loại nguồn<select value={sourceType} onChange={(event) => { const next = event.target.value as SourceType; setSourceType(next); setSourceId(''); setSourceCaseId('') }}>{sourceTypes.map((type) => <option key={type} value={type}>{reportSourceLabel(type)}</option>)}</select></label>{sourceType === 'QA_CASE' && cases.data && <label>Chọn bài kiểm tra<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Chọn bài kiểm tra</option>{cases.data.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}{sourceType === 'DVH' && cases.data && <label>Bài kiểm tra chứa phân tích liều<select value={sourceCaseId} onChange={(event) => { setSourceCaseId(event.target.value); setSourceId('') }}><option value="">Chọn bài kiểm tra</option>{cases.data.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}{sourceType === 'DVH' && sourceCaseId && <label>Chọn kết quả liều–thể tích<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Chọn kết quả</option>{(dvhRuns.data?.items ?? []).map((run: DvhRunResource, index) => <option key={run.id} value={run.id}>Lần phân tích {index + 1} · ROI {run.roi_number} · {reportRunStatusLabel(run.status)}</option>)}</select>{dvhRuns.error && <small className="form-hint">Không tải được lịch sử phân tích liều.</small>}</label>}{sourceType === 'MACHINE_QA' && cases.data && <label>Bài kiểm tra chứa kết quả máy<select value={sourceCaseId} onChange={(event) => { setSourceCaseId(event.target.value); setSourceId('') }}><option value="">Chọn bài kiểm tra</option>{cases.data.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}{sourceType === 'MACHINE_QA' && sourceCaseId && <label>Chọn kết quả kiểm tra máy<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Chọn kết quả</option>{(machineQARuns.data?.items ?? []).map((run, index) => <option key={run.id} value={run.id}>Lần thực hiện {index + 1} · {reportRunStatusLabel(run.overall_status ?? run.status)}</option>)}</select></label>}{sourceType === 'PYLINAC_QA' && cases.data && <label>Bài kiểm tra chứa phân tích Pylinac<select value={sourceCaseId} onChange={(event) => { setSourceCaseId(event.target.value); setSourceId('') }}><option value="">Chọn bài kiểm tra</option>{cases.data.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}{sourceType === 'PYLINAC_QA' && sourceCaseId && <label>Chọn kết quả phân tích<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Chọn kết quả</option>{(pylinacRuns.data?.items ?? []).map((run, index) => <option key={run.id} value={run.id}>{run.name} · Lần phân tích {index + 1} · {reportRunStatusLabel(run.assessment_status ?? run.status)}</option>)}</select>{pylinacRuns.error && <small className="form-hint">Không tải được lịch sử phân tích Pylinac.</small>}</label>}{sourceType === 'GAMMA' && cases.data && <label>Bài kiểm tra chứa phân tích PSQA<select value={sourceCaseId} onChange={(event) => { setSourceCaseId(event.target.value); setSourceId('') }}><option value="">Chọn bài kiểm tra</option>{cases.data.items.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label>}{sourceType === 'GAMMA' && sourceCaseId && <label>Chọn kết quả PSQA<select value={sourceId} onChange={(event) => setSourceId(event.target.value)}><option value="">Chọn kết quả</option>{(gammaRuns.data?.items ?? []).map((run, index) => <option key={run.id} value={run.id}>Lần phân tích {index + 1} · {reportRunStatusLabel(run.status)}</option>)}</select></label>}</div>
          <p className="form-hint">Bản chụp nguồn được lưu cùng báo cáo. Kết quả nguồn thay đổi sau đó không sửa các báo cáo đã lưu.</p>
          {editorError && <div className="alert alert--error"><p>{editorError}</p></div>}
          <div className="report-block-heading"><div><p className="eyebrow">CÁC PHẦN BÁO CÁO</p><h2>Thành phần hiển thị</h2></div><button className="button-secondary" onClick={addBlock}>+ Thêm phần</button></div>
          <div className="report-block-list">{blocks.map((block, index) => <article className="report-block-editor" key={block.stable_block_id}>
            <div className="report-block-editor__top"><strong>Phần {index + 1}</strong><select aria-label={`Loại phần ${index + 1}`} value={block.block_type} onChange={(event) => updateBlock(index, { block_type: event.target.value, label: reportBlockLabel(event.target.value) })}>{blockTypes.map((type) => <option key={type} value={type}>{reportBlockLabel(type)}</option>)}</select><label className="checkbox-row"><input type="checkbox" checked={block.is_visible} onChange={(event) => updateBlock(index, { is_visible: event.target.checked })} /> Hiển thị</label><div className="table-actions"><button className="button-secondary" onClick={() => moveBlock(index, -1)} disabled={index === 0}>↑</button><button className="button-secondary" onClick={() => moveBlock(index, 1)} disabled={index === blocks.length - 1}>↓</button><button className="button-secondary" onClick={() => setBlocks((current) => current.filter((_, blockIndex) => blockIndex !== index))}>Xóa</button></div></div>
            <label>Tên hiển thị<input value={block.label} onChange={(event) => updateBlock(index, { label: event.target.value })} /></label>
            {(block.block_type === 'TEXT' || block.block_type === 'COMMENTS') ? <label>Nội dung ghi chú<textarea value={typeof block.config.content === 'string' ? block.config.content : ''} onChange={(event) => updateBlockContent(index, event.target.value)} rows={4} placeholder="Nhập ghi chú muốn hiển thị trong báo cáo" /></label> : <p className="form-hint">Phần này sẽ lấy dữ liệu từ kết quả đã chọn khi xuất báo cáo.</p>}
          </article>)}</div>
          <div className="report-editor-actions"><button disabled={saveMutation.isPending || Boolean(editorError) || !title.trim()} onClick={() => saveMutation.mutate()}>{saveMutation.isPending ? 'Đang lưu…' : currentRevision ? 'Lưu bản mới' : 'Lưu báo cáo'}</button>{currentRevision && <span className="form-hint">Bản hiện tại: {currentRevision.revision_number}</span>}</div>
        </section>
      </div>
      <section className="panel report-preview-panel"><div className="panel-heading"><div><p className="eyebrow">XEM TRƯỚC VÀ XUẤT</p><h2>Xem trước báo cáo</h2></div>{currentRevision && <span className="status-badge">ĐÃ LƯU</span>}</div>{currentRevision ? <><p className="form-hint">Bản xem trước được dựng từ bản đã lưu {currentRevision.revision_number} bằng cùng bộ dựng với tệp PNG/PDF. Nếu vừa chỉnh sửa, hãy lưu bản mới để cập nhật hình xem trước.</p>{reportPreview.isPending ? <div className="report-preview-engine report-preview-engine--empty">Đang dựng bản xem trước…</div> : reportPreview.error ? <div className="alert alert--error"><p>{errorMessage(reportPreview.error)}</p><button className="button-secondary" onClick={() => void reportPreview.refetch()}>Thử lại</button></div> : reportPreviewUrl ? <figure className="report-preview-engine"><img src={reportPreviewUrl} alt={`Bản xem trước báo cáo ${currentRevision.revision_number}`} /><figcaption>Bản xem trước từ cùng bản chụp dùng để xuất báo cáo.</figcaption></figure> : null}</> : <div className="report-preview report-preview--draft"><h3>{title || 'Báo cáo chưa đặt tên'}</h3><p>Nguồn: {reportSourceLabel(sourceType)}</p>{blocks.filter((block) => block.is_visible).sort((left, right) => left.sort_order - right.sort_order).map((block) => <article key={block.stable_block_id}><strong>{block.label}</strong><small>{reportBlockLabel(block.block_type)}</small><pre>{blockDescription(block)}</pre></article>)}</div>}{currentRevision && <><div className="report-export-actions"><strong>Xuất bản báo cáo {currentRevision.revision_number}</strong>{(['CSV', 'PDF', 'PNG'] as const).map((format) => <button key={format} className="button-secondary" disabled={exportMutation.isPending} onClick={() => exportMutation.mutate(format)}>{exportMutation.isPending ? 'Đang tạo…' : reportExportLabel(format)}</button>)}</div><div className="report-export-history"><div className="panel-heading"><div><p className="eyebrow">LỊCH SỬ TỆP</p><h3>Tệp đã xuất từ bản này</h3></div><strong>{reportExports.data?.total ?? 0}</strong></div>{reportExports.isPending ? <p className="form-hint">Đang tải lịch sử tệp…</p> : reportExports.error ? <div className="alert alert--error"><p>{errorMessage(reportExports.error)}</p><button className="button-secondary" onClick={() => void reportExports.refetch()}>Thử lại</button></div> : reportExports.data?.items.length ? <div className="report-export-history__list">{reportExports.data.items.map((job) => <article key={job.id} className="report-export-history__item"><div><strong>{reportExportLabel(job.export_format)}</strong><small>{reportRunStatusLabel(job.status)} · {new Date(job.created_at).toLocaleString('vi-VN')}</small></div>{job.status === 'COMPLETED' && <button className="button-secondary" disabled={downloadExportMutation.isPending} onClick={() => downloadExportMutation.mutate(job.id)}>Tải lại</button>}</article>)}</div> : <p className="empty-state">Chưa có tệp nào được xuất từ bản này.</p>}</div></>}</section>
    </div>
  )
}
