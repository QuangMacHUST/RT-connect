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
        renderer_version: z.string()
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
        metadata_snapshot: z.record(z.string(), z.unknown())
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
      metadata_snapshot: z.record(z.string(), z.unknown()), duplicate: z.boolean()
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
}

export const apiClient = new ApiClient()
