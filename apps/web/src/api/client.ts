import { z } from 'zod'

import { environment } from '../env'

const errorSchema = z.object({
  code: z.string(),
  message: z.string(),
  correlation_id: z.string(),
  details: z.array(z.object({ field: z.string().nullable().optional(), message: z.string() })).default([])
})

export class ApiClientError extends Error {
  readonly code: string
  readonly correlationId: string | undefined

  constructor(message: string, code = 'NETWORK_ERROR', correlationId?: string) {
    super(message)
    this.name = 'ApiClientError'
    this.code = code
    this.correlationId = correlationId
  }
}

export type Health = { status: string; timestamp: string; correlation_id: string }
export type Version = {
  application: string
  version: string
  environment: string
  engine_version: string
  renderer_version: string
  schema_revision: string
}

export type OrganizationContext = { id: string; name: string }
export type SessionBootstrap = { subject: string; email: string | null; organization: OrganizationContext }
export type DashboardSummary = {
  organization: OrganizationContext
  site_count: number
  machine_count: number
  recent_qa_count: number
  active_job_count: number
  warnings: string[]
}
export type OrganizationResource = { id: string; name: string; is_archived: boolean }
export type SiteResource = { id: string; organization_id: string; name: string; is_archived: boolean }
export type MachineResource = {
  id: string
  organization_id: string
  site_id: string
  stable_machine_id: string
  display_name: string
  manufacturer: string | null
  model: string | null
  status: string
  is_archived: boolean
}
export type Collection<T> = { items: T[]; total: number; offset: number; limit: number }
export type FolderResource = {
  id: string
  organization_id: string
  parent_folder_id: string | null
  name: string
  path: string
  depth: number
  is_archived: boolean
}
export type QACaseResource = {
  id: string
  organization_id: string
  site_id: string
  machine_id: string
  primary_folder_id: string
  qa_type: string
  qa_cycle: string
  performed_at: string
  scheduled_at: string | null
  title: string
  description: string | null
  protocol_version_id: string | null
  status_note: string | null
  case_status: string
  is_archived: boolean
}
export type ArtifactResource = {
  id: string
  organization_id: string
  qa_case_id: string | null
  artifact_type: string
  modality: string | null
  original_filename: string
  byte_size: number
  media_type: string
  sha256: string
  sop_class_uid: string | null
  sop_instance_uid: string | null
  study_instance_uid: string | null
  series_instance_uid: string | null
  frame_of_reference_uid: string | null
  source_system: string | null
  uploaded_at: string
  data_status: string
  parent_artifact_id: string | null
  metadata_snapshot: Record<string, unknown>
  logical_roles: string[]
}
export type ValidationResource = {
  id: string
  subject_type: string
  subject_id: string
  validation_type: string
  validator_version: string
  started_at: string
  completed_at: string | null
  result: string
  checks: Array<Record<string, unknown>>
  warnings: Array<Record<string, unknown>>
  errors: Array<Record<string, unknown>>
  input_manifest_snapshot: Record<string, unknown>
}
export type QAProtocolRuleResource = {
  id: string
  metric_key: string
  display_name: string
  unit: string
  rule_type: string
  target_value: number | null
  lower_limit: number | null
  upper_limit: number | null
  tolerance: number | null
  action_level: number | null
  required: boolean
  sort_order: number
  note: string | null
}
export type QAProtocolResource = {
  id: string
  organization_id: string
  protocol_key: string
  name: string
  qa_type: string
  version_number: number
  status: string
  effective_note: string | null
  rules: QAProtocolRuleResource[]
}
export type MachineQAMeasurement = {
  metric_key: string
  value: number | null
  unit: string
  note: string | null
}
export type MachineQARunResource = {
  id: string
  organization_id: string
  qa_case_id: string
  machine_id: string
  protocol_version_id: string
  status: string
  overall_status: string | null
  measurement_revision: number
  measurements: Array<Record<string, unknown>>
  result_snapshot: Record<string, unknown>
  error_snapshot: Array<Record<string, unknown>>
  supersedes_run_id: string | null
  started_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
  protocol: QAProtocolResource
}
export type MachineQACompareResource = {
  left_run_id: string
  right_run_id: string
  items: Array<{
    metric_key: string
    left: Record<string, unknown> | null
    right: Record<string, unknown> | null
  }>
}
export type GammaConfiguration = {
  dimensionality: '2D' | '3D'
  dose_difference_percent: number
  dose_difference_mode: 'ABSOLUTE' | 'RELATIVE'
  absolute_dose_difference_gy: number | null
  distance_to_agreement_mm: number
  dose_threshold_percent: number
  normalization: 'GLOBAL' | 'LOCAL'
  interpolation: 'GRID' | 'BILINEAR'
  coverage_policy: 'FULL_ROI' | 'OVERLAP_ONLY'
  max_gamma: number
  pass_rate_threshold_percent: number
  histogram_bins: number
}
export type GammaWorkflowProfile = 'PSQA_GAMMA' | 'ENGINE_TEST'
export type GammaRunResource = {
  id: string
  organization_id: string
  qa_case_id: string
  reference_artifact_id: string
  evaluation_artifact_id: string
  idempotency_key: string
  workflow_profile: GammaWorkflowProfile
  status: string
  progress_percent: number
  attempt_count: number
  engine_version: string
  config_snapshot: Record<string, unknown>
  input_manifest_snapshot: Record<string, unknown>
  result_snapshot: Record<string, unknown>
  error_snapshot: Array<Record<string, unknown>>
  warning_snapshot: Array<Record<string, unknown>>
  queued_at: string
  started_at: string | null
  heartbeat_at: string | null
  completed_at: string | null
  created_at: string
  updated_at: string
}
export type GammaCompareResource = {
  left_run_id: string
  right_run_id: string
  items: Array<{ key: string; left: unknown; right: unknown }>
}
export type GammaQueueMetrics = {
  backend: string
  configured: boolean
  available: boolean
  stream_length: number | null
  pending_count: number | null
  consumer_count: number | null
  queued_runs: number
  running_runs: number
  retrying_runs: number
  failed_runs: number
  error: string | null
}

export type ReportBlock = {
  stable_block_id: string
  block_type: string
  label: string
  sort_order?: number
  is_visible: boolean
  config: Record<string, unknown>
  source_binding: Record<string, unknown>
}
export type ReportTemplateVersion = {
  id: string
  organization_id: string
  template_key: string
  name: string
  version_number: number
  status: string
  description: string | null
  blocks_snapshot: Array<Record<string, unknown>>
  render_options: Record<string, unknown>
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
}
export type ReportRevision = {
  id: string
  organization_id: string
  report_key: string
  revision_number: number
  source_type: string
  source_id: string | null
  title: string
  template_version_id: string | null
  source_snapshot: Record<string, unknown>
  render_options: Record<string, unknown>
  content_sha256: string
  status: string
  supersedes_revision_id: string | null
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
  blocks: Array<ReportBlock & { id: string; sort_order: number }>
}
export type ReportSummary = {
  report_key: string
  organization_id: string
  title: string
  source_type: string
  source_id: string | null
  latest_revision_id: string
  latest_revision_number: number
  status: string
  content_sha256: string
  created_at: string
  updated_at: string
}
export type ExportJob = {
  id: string
  organization_id: string
  report_revision_id: string
  idempotency_key: string
  export_format: string
  render_options: Record<string, unknown>
  renderer_version: string
  status: string
  object_key: string | null
  sha256: string | null
  byte_size: number | null
  media_type: string | null
  error_snapshot: Array<Record<string, unknown>>
  warning_snapshot: Array<Record<string, unknown>>
  download_url: string | null
  download_expires_at: string | null
  created_at: string
  updated_at: string
}

const qaProtocolRuleSchema = z.object({
  id: z.string().uuid(), metric_key: z.string(), display_name: z.string(), unit: z.string(),
  rule_type: z.string(), target_value: z.number().nullable(), lower_limit: z.number().nullable(),
  upper_limit: z.number().nullable(), tolerance: z.number().nullable(), action_level: z.number().nullable(),
  required: z.boolean(), sort_order: z.number().int(), note: z.string().nullable()
})
const qaProtocolSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), protocol_key: z.string(), name: z.string(),
  qa_type: z.string(), version_number: z.number().int(), status: z.string(), effective_note: z.string().nullable(),
  rules: z.array(qaProtocolRuleSchema)
})
const machineQARunSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), qa_case_id: z.string().uuid(),
  machine_id: z.string().uuid(), protocol_version_id: z.string().uuid(), status: z.string(),
  overall_status: z.string().nullable(), measurement_revision: z.number().int(),
  measurements: z.array(z.record(z.string(), z.unknown())),
  result_snapshot: z.record(z.string(), z.unknown()),
  error_snapshot: z.array(z.record(z.string(), z.unknown())),
  supersedes_run_id: z.string().uuid().nullable(), started_at: z.string().nullable(),
  completed_at: z.string().nullable(), created_at: z.string(), updated_at: z.string(), protocol: qaProtocolSchema
})
const gammaRunSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), qa_case_id: z.string().uuid(),
  reference_artifact_id: z.string().uuid(), evaluation_artifact_id: z.string().uuid(),
  idempotency_key: z.string(), workflow_profile: z.enum(['PSQA_GAMMA', 'ENGINE_TEST']), status: z.string(), progress_percent: z.number().int(),
  attempt_count: z.number().int(), engine_version: z.string(),
  config_snapshot: z.record(z.string(), z.unknown()), input_manifest_snapshot: z.record(z.string(), z.unknown()),
  result_snapshot: z.record(z.string(), z.unknown()), error_snapshot: z.array(z.record(z.string(), z.unknown())),
  warning_snapshot: z.array(z.record(z.string(), z.unknown())), queued_at: z.string(),
  started_at: z.string().nullable(), heartbeat_at: z.string().nullable(), completed_at: z.string().nullable(),
  created_at: z.string(), updated_at: z.string()
})
const gammaQueueMetricsSchema = z.object({
  backend: z.string(), configured: z.boolean(), available: z.boolean(),
  stream_length: z.number().int().nullable(), pending_count: z.number().int().nullable(),
  consumer_count: z.number().int().nullable(), queued_runs: z.number().int(),
  running_runs: z.number().int(), retrying_runs: z.number().int(), failed_runs: z.number().int(),
  error: z.string().nullable()
})

const reportBlockSchema = z.object({
  id: z.string().uuid().optional(),
  stable_block_id: z.string(), block_type: z.string(), label: z.string(),
  sort_order: z.number().int(), is_visible: z.boolean(),
  config: z.record(z.string(), z.unknown()),
  source_binding: z.record(z.string(), z.unknown())
})
const reportTemplateVersionSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), template_key: z.string(),
  name: z.string(), version_number: z.number().int(), status: z.string(),
  description: z.string().nullable(), blocks_snapshot: z.array(z.record(z.string(), z.unknown())),
  render_options: z.record(z.string(), z.unknown()),
  created_by_user_identity_id: z.string().uuid().nullable(), created_at: z.string(), updated_at: z.string()
})
const reportRevisionSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), report_key: z.string().uuid(),
  revision_number: z.number().int(), source_type: z.string(), source_id: z.string().uuid().nullable(),
  title: z.string(), template_version_id: z.string().uuid().nullable(),
  source_snapshot: z.record(z.string(), z.unknown()), render_options: z.record(z.string(), z.unknown()),
  content_sha256: z.string(), status: z.string(), supersedes_revision_id: z.string().uuid().nullable(),
  created_by_user_identity_id: z.string().uuid().nullable(), created_at: z.string(), updated_at: z.string(),
  blocks: z.array(reportBlockSchema.extend({ id: z.string().uuid() }))
})
const reportSummarySchema = z.object({
  report_key: z.string().uuid(), organization_id: z.string().uuid(), title: z.string(),
  source_type: z.string(), source_id: z.string().uuid().nullable(), latest_revision_id: z.string().uuid(),
  latest_revision_number: z.number().int(), status: z.string(), content_sha256: z.string(),
  created_at: z.string(), updated_at: z.string()
})
const exportJobSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), report_revision_id: z.string().uuid(),
  idempotency_key: z.string(), export_format: z.string(), render_options: z.record(z.string(), z.unknown()),
  renderer_version: z.string(), status: z.string(), object_key: z.string().nullable(),
  sha256: z.string().nullable(), byte_size: z.number().int().nullable(), media_type: z.string().nullable(),
  error_snapshot: z.array(z.record(z.string(), z.unknown())), warning_snapshot: z.array(z.record(z.string(), z.unknown())),
  download_url: z.string().nullable(), download_expires_at: z.string().nullable(),
  created_at: z.string(), updated_at: z.string()
})
const exportDownloadSchema = z.object({
  export_job_id: z.string().uuid(), report_revision_id: z.string().uuid(), url: z.string(),
  expires_at: z.string(), sha256: z.string(), media_type: z.string()
})

const makeCorrelationId = () => crypto.randomUUID()

export class ApiClient {
  constructor(private readonly baseUrl = environment.VITE_API_BASE_URL) {}

  async get<T>(path: string, schema: z.ZodType<T>, accessToken?: string): Promise<T> {
    return this.request(path, schema, accessToken)
  }

  async request<T>(
    path: string,
    schema: z.ZodType<T>,
    accessToken: string | undefined,
    init: RequestInit = {}
  ): Promise<T> {
    const correlationId = makeCorrelationId()
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        ...init,
        headers: {
          Accept: 'application/json',
          ...(init.body && !(init.body instanceof FormData) ? { 'Content-Type': 'application/json' } : {}),
          'X-Correlation-ID': correlationId,
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
          ...init.headers
        }
      })
    } catch {
      throw new ApiClientError('Không thể kết nối tới RT-CONNECT API.', 'NETWORK_ERROR', correlationId)
    }
    const body: unknown = await response.json().catch(() => undefined)
    if (!response.ok) {
      const parsed = errorSchema.safeParse(body)
      if (parsed.success) {
        throw new ApiClientError(parsed.data.message, parsed.data.code, parsed.data.correlation_id)
      }
      throw new ApiClientError('API trả về phản hồi không hợp lệ.', 'INVALID_API_RESPONSE', correlationId)
    }
    const result = schema.safeParse(body)
    if (!result.success) {
      throw new ApiClientError('API trả về hợp đồng dữ liệu không hợp lệ.', 'INVALID_API_RESPONSE', correlationId)
    }
    return result.data
  }

  health(): Promise<Health> {
    return this.get('/health', z.object({ status: z.string(), timestamp: z.string(), correlation_id: z.string() }))
  }

  version(): Promise<Version> {
    return this.get(
      '/version',
      z.object({
        application: z.string(),
        version: z.string(),
        environment: z.string(),
        engine_version: z.string(),
        renderer_version: z.string(),
        schema_revision: z.string()
      })
    )
  }

  bootstrap(accessToken: string): Promise<SessionBootstrap> {
    return this.get('/session/bootstrap', z.object({
      subject: z.string(),
      email: z.string().nullable(),
      organization: z.object({ id: z.string().uuid(), name: z.string() })
    }), accessToken)
  }

  createOrganization(accessToken: string, name: string): Promise<OrganizationResource> {
    return this.request('/organizations', z.object({
      id: z.string().uuid(), name: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'POST', body: JSON.stringify({ name }) })
  }

  dashboard(accessToken: string, organizationId: string): Promise<DashboardSummary> {
    return this.get(`/organizations/${organizationId}/dashboard`, z.object({
      organization: z.object({ id: z.string().uuid(), name: z.string() }),
      site_count: z.number().int().nonnegative(),
      machine_count: z.number().int().nonnegative(),
      recent_qa_count: z.number().int().nonnegative(),
      active_job_count: z.number().int().nonnegative(),
      warnings: z.array(z.string())
    }), accessToken)
  }

  organization(accessToken: string, organizationId: string): Promise<OrganizationResource> {
    return this.get(`/organizations/${organizationId}`, z.object({
      id: z.string().uuid(), name: z.string(), is_archived: z.boolean()
    }), accessToken)
  }

  updateOrganization(accessToken: string, organizationId: string, body: { name?: string; is_archived?: boolean }): Promise<OrganizationResource> {
    return this.request(`/organizations/${organizationId}`, z.object({
      id: z.string().uuid(), name: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'PATCH', body: JSON.stringify(body) })
  }

  sites(accessToken: string, organizationId: string, includeArchived = false): Promise<Collection<SiteResource>> {
    return this.get(`/organizations/${organizationId}/sites?include_archived=${includeArchived}`, z.object({
      items: z.array(z.object({ id: z.string().uuid(), organization_id: z.string().uuid(), name: z.string(), is_archived: z.boolean() })),
      total: z.number().int(), offset: z.number().int(), limit: z.number().int()
    }), accessToken)
  }

  createSite(accessToken: string, organizationId: string, name: string): Promise<SiteResource> {
    return this.request(`/organizations/${organizationId}/sites`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), name: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'POST', body: JSON.stringify({ name }) })
  }

  updateSite(accessToken: string, organizationId: string, siteId: string, body: { name?: string; is_archived?: boolean }): Promise<SiteResource> {
    return this.request(`/organizations/${organizationId}/sites/${siteId}`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), name: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'PATCH', body: JSON.stringify(body) })
  }

  machines(accessToken: string, organizationId: string, siteId: string, includeArchived = false): Promise<Collection<MachineResource>> {
    return this.get(`/organizations/${organizationId}/sites/${siteId}/machines?include_archived=${includeArchived}`, z.object({
      items: z.array(z.object({
        id: z.string().uuid(), organization_id: z.string().uuid(), site_id: z.string().uuid(),
        stable_machine_id: z.string(), display_name: z.string(), manufacturer: z.string().nullable(),
        model: z.string().nullable(), status: z.string(), is_archived: z.boolean()
      })),
      total: z.number().int(), offset: z.number().int(), limit: z.number().int()
    }), accessToken)
  }

  createMachine(accessToken: string, organizationId: string, siteId: string, body: {
    stable_machine_id: string; display_name: string; manufacturer?: string; model?: string; status?: string
  }): Promise<MachineResource> {
    return this.request(`/organizations/${organizationId}/sites/${siteId}/machines`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), site_id: z.string().uuid(),
      stable_machine_id: z.string(), display_name: z.string(), manufacturer: z.string().nullable(),
      model: z.string().nullable(), status: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'POST', body: JSON.stringify({ status: 'ACTIVE', ...body }) })
  }

  updateMachine(accessToken: string, organizationId: string, siteId: string, machineId: string, body: Partial<Pick<MachineResource, 'display_name' | 'manufacturer' | 'model' | 'status' | 'is_archived'>>): Promise<MachineResource> {
    return this.request(`/organizations/${organizationId}/sites/${siteId}/machines/${machineId}`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), site_id: z.string().uuid(),
      stable_machine_id: z.string(), display_name: z.string(), manufacturer: z.string().nullable(),
      model: z.string().nullable(), status: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'PATCH', body: JSON.stringify(body) })
  }

  folders(accessToken: string, organizationId: string, includeArchived = false): Promise<{ items: FolderResource[]; total: number; include_archived: boolean }> {
    return this.get(`/organizations/${organizationId}/folders/tree?include_archived=${includeArchived}`, z.object({
      items: z.array(z.object({
        id: z.string().uuid(), organization_id: z.string().uuid(), parent_folder_id: z.string().uuid().nullable(),
        name: z.string(), path: z.string(), depth: z.number().int().nonnegative(), is_archived: z.boolean()
      })), total: z.number().int(), include_archived: z.boolean()
    }), accessToken)
  }

  createFolder(accessToken: string, organizationId: string, body: { name: string; parent_folder_id?: string }): Promise<FolderResource> {
    return this.request(`/organizations/${organizationId}/folders`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), parent_folder_id: z.string().uuid().nullable(),
      name: z.string(), path: z.string(), depth: z.number().int().nonnegative(), is_archived: z.boolean()
    }), accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  updateFolder(accessToken: string, folderId: string, body: { name?: string; parent_folder_id?: string | null; is_archived?: boolean }): Promise<FolderResource> {
    return this.request(`/folders/${folderId}`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), parent_folder_id: z.string().uuid().nullable(),
      name: z.string(), path: z.string(), depth: z.number().int().nonnegative(), is_archived: z.boolean()
    }), accessToken, { method: 'PATCH', body: JSON.stringify(body) })
  }

  qaCases(accessToken: string, organizationId: string, params: { q?: string; folder_id?: string; include_archived?: boolean } = {}): Promise<Collection<QACaseResource> & { include_archived: boolean }> {
    const query = new URLSearchParams()
    if (params.q) query.set('q', params.q)
    if (params.folder_id) query.set('folder_id', params.folder_id)
    if (params.include_archived) query.set('include_archived', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return this.get(`/organizations/${organizationId}/qa-cases${suffix}`, z.object({
      items: z.array(z.object({
        id: z.string().uuid(), organization_id: z.string().uuid(), site_id: z.string().uuid(), machine_id: z.string().uuid(),
        primary_folder_id: z.string().uuid(), qa_type: z.string(), qa_cycle: z.string(), performed_at: z.string(),
        scheduled_at: z.string().nullable(), title: z.string(), description: z.string().nullable(),
        protocol_version_id: z.string().uuid().nullable(), status_note: z.string().nullable(),
        case_status: z.string(), is_archived: z.boolean()
      })), total: z.number().int(), offset: z.number().int(), limit: z.number().int(), include_archived: z.boolean()
    }), accessToken)
  }

  createQACase(accessToken: string, organizationId: string, body: {
    site_id: string; machine_id: string; primary_folder_id: string; qa_type: string; qa_cycle: string;
    performed_at: string; title: string
  }): Promise<QACaseResource> {
    return this.request(`/organizations/${organizationId}/qa-cases`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), site_id: z.string().uuid(), machine_id: z.string().uuid(),
      primary_folder_id: z.string().uuid(), qa_type: z.string(), qa_cycle: z.string(), performed_at: z.string(),
      scheduled_at: z.string().nullable(), title: z.string(), description: z.string().nullable(),
      protocol_version_id: z.string().uuid().nullable(), status_note: z.string().nullable(),
      case_status: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  updateQACase(accessToken: string, caseId: string, body: { is_archived?: boolean; title?: string }): Promise<QACaseResource> {
    return this.request(`/qa-cases/${caseId}`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), site_id: z.string().uuid(), machine_id: z.string().uuid(),
      primary_folder_id: z.string().uuid(), qa_type: z.string(), qa_cycle: z.string(), performed_at: z.string(),
      scheduled_at: z.string().nullable(), title: z.string(), description: z.string().nullable(),
      protocol_version_id: z.string().uuid().nullable(), status_note: z.string().nullable(),
      case_status: z.string(), is_archived: z.boolean()
    }), accessToken, { method: 'PATCH', body: JSON.stringify(body) })
  }

  artifacts(accessToken: string, caseId: string): Promise<{ items: ArtifactResource[]; total: number; offset: number; limit: number }> {
    return this.get(`/qa-cases/${caseId}/artifacts`, z.object({
      items: z.array(z.object({
        id: z.string().uuid(), organization_id: z.string().uuid(), qa_case_id: z.string().uuid().nullable(),
        artifact_type: z.string(), modality: z.string().nullable(), original_filename: z.string(),
        byte_size: z.number().int().nonnegative(), media_type: z.string(), sha256: z.string(),
        sop_class_uid: z.string().nullable(), sop_instance_uid: z.string().nullable(),
        study_instance_uid: z.string().nullable(), series_instance_uid: z.string().nullable(),
        frame_of_reference_uid: z.string().nullable(), source_system: z.string().nullable(),
        uploaded_at: z.string(), data_status: z.string(), parent_artifact_id: z.string().uuid().nullable(),
        metadata_snapshot: z.record(z.string(), z.unknown()), logical_roles: z.array(z.string())
      })), total: z.number().int(), offset: z.number().int(), limit: z.number().int()
    }), accessToken)
  }

  uploadArtifact(accessToken: string, caseId: string, file: File, artifactType: string, logicalRole: string): Promise<ArtifactResource & { duplicate: boolean }> {
    const body = new FormData()
    body.append('file', file)
    body.append('artifact_type', artifactType)
    body.append('logical_role', logicalRole)
    return this.request(`/qa-cases/${caseId}/artifacts`, z.object({
      id: z.string().uuid(), organization_id: z.string().uuid(), qa_case_id: z.string().uuid().nullable(),
      artifact_type: z.string(), modality: z.string().nullable(), original_filename: z.string(),
      byte_size: z.number().int().nonnegative(), media_type: z.string(), sha256: z.string(),
      sop_class_uid: z.string().nullable(), sop_instance_uid: z.string().nullable(),
      study_instance_uid: z.string().nullable(), series_instance_uid: z.string().nullable(),
      frame_of_reference_uid: z.string().nullable(), source_system: z.string().nullable(),
      uploaded_at: z.string(), data_status: z.string(), parent_artifact_id: z.string().uuid().nullable(),
      metadata_snapshot: z.record(z.string(), z.unknown()), logical_roles: z.array(z.string()), duplicate: z.boolean()
    }), accessToken, { method: 'POST', body })
  }

  validateArtifact(accessToken: string, artifactId: string, force = false): Promise<ValidationResource> {
    return this.request(`/artifacts/${artifactId}/validate?force=${force}`, z.object({
      id: z.string().uuid(), subject_type: z.string(), subject_id: z.string().uuid(),
      validation_type: z.string(), validator_version: z.string(), started_at: z.string(),
      completed_at: z.string().nullable(), result: z.string(),
      checks: z.array(z.record(z.string(), z.unknown())),
      warnings: z.array(z.record(z.string(), z.unknown())),
      errors: z.array(z.record(z.string(), z.unknown())),
      input_manifest_snapshot: z.record(z.string(), z.unknown())
    }), accessToken, { method: 'POST' })
  }

  downloadArtifact(accessToken: string, artifactId: string): Promise<{ artifact_id: string; url: string; expires_at: string }> {
    return this.get(`/artifacts/${artifactId}/download`, z.object({
      artifact_id: z.string().uuid(), url: z.string(), expires_at: z.string()
    }), accessToken)
  }

  machineQAProtocols(accessToken: string, organizationId: string): Promise<{ items: QAProtocolResource[]; total: number }> {
    return this.get(`/organizations/${organizationId}/machine-qa/protocols`, z.object({
      items: z.array(qaProtocolSchema), total: z.number().int()
    }), accessToken)
  }

  seedMachineQAProtocol(accessToken: string, organizationId: string): Promise<QAProtocolResource> {
    return this.request(`/organizations/${organizationId}/machine-qa/protocols/seed`, qaProtocolSchema, accessToken, { method: 'POST' })
  }

  createMachineQARun(accessToken: string, caseId: string, protocolVersionId: string, measurements: MachineQAMeasurement[] = []): Promise<MachineQARunResource> {
    return this.request(`/qa-cases/${caseId}/machine-qa-runs`, machineQARunSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ protocol_version_id: protocolVersionId, measurements })
    })
  }

  machineQARuns(accessToken: string, caseId: string): Promise<{ items: MachineQARunResource[]; total: number }> {
    return this.get(`/qa-cases/${caseId}/machine-qa-runs`, z.object({
      items: z.array(machineQARunSchema), total: z.number().int()
    }), accessToken)
  }

  updateMachineQAMeasurements(accessToken: string, runId: string, expectedRevision: number, measurements: MachineQAMeasurement[]): Promise<MachineQARunResource> {
    return this.request(`/machine-qa-runs/${runId}/measurements`, machineQARunSchema, accessToken, {
      method: 'PATCH', body: JSON.stringify({ expected_revision: expectedRevision, measurements })
    })
  }

  evaluateMachineQARun(accessToken: string, runId: string): Promise<MachineQARunResource> {
    return this.request(`/machine-qa-runs/${runId}/evaluate`, machineQARunSchema, accessToken, { method: 'POST' })
  }

  rerunMachineQARun(accessToken: string, runId: string): Promise<MachineQARunResource> {
    return this.request(`/machine-qa-runs/${runId}/rerun`, machineQARunSchema, accessToken, { method: 'POST' })
  }

  compareMachineQARuns(accessToken: string, runId: string, otherRunId: string): Promise<MachineQACompareResource> {
    return this.get(`/machine-qa-runs/${runId}/compare?other_run_id=${encodeURIComponent(otherRunId)}`, z.object({
      left_run_id: z.string().uuid(), right_run_id: z.string().uuid(),
      items: z.array(z.object({ metric_key: z.string(), left: z.record(z.string(), z.unknown()).nullable(), right: z.record(z.string(), z.unknown()).nullable() }))
    }), accessToken)
  }

  gammaRuns(accessToken: string, caseId: string): Promise<{ items: GammaRunResource[]; total: number }> {
    return this.get(`/qa-cases/${caseId}/gamma-runs`, z.object({
      items: z.array(gammaRunSchema), total: z.number().int()
    }), accessToken)
  }

  createGammaRun(accessToken: string, caseId: string, body: {
    reference_artifact_id: string
    evaluation_artifact_id: string
    idempotency_key: string
    workflow_profile: GammaWorkflowProfile
    configuration: GammaConfiguration
  }): Promise<GammaRunResource> {
    return this.request(`/qa-cases/${caseId}/gamma-runs`, gammaRunSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  retryGammaRun(accessToken: string, runId: string): Promise<GammaRunResource> {
    return this.request(`/gamma-runs/${runId}/retry`, gammaRunSchema, accessToken, { method: 'POST' })
  }

  gammaQueueMetrics(accessToken: string): Promise<GammaQueueMetrics> {
    return this.get('/gamma/queue-metrics', gammaQueueMetricsSchema, accessToken)
  }

  compareGammaRuns(accessToken: string, runId: string, otherRunId: string): Promise<GammaCompareResource> {
    return this.get(`/gamma-runs/${runId}/compare?other_run_id=${encodeURIComponent(otherRunId)}`, z.object({
      left_run_id: z.string().uuid(), right_run_id: z.string().uuid(),
      items: z.array(z.object({ key: z.string(), left: z.unknown().nullable(), right: z.unknown().nullable() }))
    }), accessToken)
  }

  reportTemplates(accessToken: string, organizationId: string, includeArchived = true): Promise<{ items: ReportTemplateVersion[]; total: number }> {
    return this.get(`/organizations/${organizationId}/report-templates?include_archived=${includeArchived}`, z.object({
      items: z.array(reportTemplateVersionSchema), total: z.number().int()
    }), accessToken)
  }

  reports(accessToken: string, organizationId: string): Promise<{ items: ReportSummary[]; total: number; offset: number; limit: number }> {
    return this.get(`/organizations/${organizationId}/reports`, z.object({
      items: z.array(reportSummarySchema), total: z.number().int(), offset: z.number().int(), limit: z.number().int()
    }), accessToken)
  }

  createReport(accessToken: string, organizationId: string, body: {
    source_type: 'CUSTOM' | 'QA_CASE' | 'MACHINE_QA' | 'GAMMA' | 'BIOLOGICAL'
    source_id?: string
    title: string
    template_version_id?: string
    blocks?: Array<{
      stable_block_id: string; block_type: string; label: string; sort_order?: number
      is_visible?: boolean; config?: Record<string, unknown>; source_binding?: Record<string, unknown>
    }>
    render_options?: Record<string, unknown>
  }): Promise<ReportRevision> {
    return this.request(`/organizations/${organizationId}/reports`, reportRevisionSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  reportRevisions(accessToken: string, reportKey: string): Promise<ReportRevision[]> {
    return this.get(`/reports/${reportKey}/revisions`, z.array(reportRevisionSchema), accessToken)
  }

  createReportRevision(accessToken: string, reportKey: string, body: {
    expected_revision?: number
    source_type?: 'CUSTOM' | 'QA_CASE' | 'MACHINE_QA' | 'GAMMA' | 'BIOLOGICAL'
    source_id?: string
    title?: string
    template_version_id?: string
    blocks?: Array<{
      stable_block_id: string; block_type: string; label: string; sort_order?: number
      is_visible?: boolean; config?: Record<string, unknown>; source_binding?: Record<string, unknown>
    }>
    render_options?: Record<string, unknown>
  }): Promise<ReportRevision> {
    return this.request(`/reports/${reportKey}/revisions`, reportRevisionSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  exportReport(accessToken: string, reportKey: string, revisionId: string, body: {
    export_format: 'JSON' | 'CSV' | 'PDF' | 'PNG'; idempotency_key: string; render_options?: Record<string, unknown>
  }): Promise<ExportJob> {
    return this.request(`/reports/${reportKey}/revisions/${revisionId}/exports`, exportJobSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  reportExportDownload(accessToken: string, exportJobId: string): Promise<{ export_job_id: string; report_revision_id: string; url: string; expires_at: string; sha256: string; media_type: string }> {
    return this.get(`/report-exports/${exportJobId}/download`, exportDownloadSchema, accessToken)
  }
}

export const apiClient = new ApiClient()
