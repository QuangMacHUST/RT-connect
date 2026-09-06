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

const makeCorrelationId = () => crypto.randomUUID()

export class ApiClient {
  constructor(private readonly baseUrl = environment.VITE_API_BASE_URL) {}

  async get<T>(path: string, schema: z.ZodType<T>, accessToken?: string): Promise<T> {
    const correlationId = makeCorrelationId()
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        headers: {
          Accept: 'application/json',
          'X-Correlation-ID': correlationId,
          ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {})
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
}

export const apiClient = new ApiClient()
