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
  reference: string | null
}
export type QAProtocolResource = {
  id: string
  organization_id: string
  protocol_key: string
  name: string
  qa_type: string
  version_number: number
  status: string
  revision: number
  description: string | null
  effective_note: string | null
  applicability: Record<string, unknown>
  source_type: string
  source_reference: string | null
  source_protocol_version_id: string | null
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
  rules: QAProtocolRuleResource[]
}
export type QAProtocolRuleInput = Omit<QAProtocolRuleResource, 'id'>
export type QAProtocolDefinitionInput = {
  protocol_key: string
  name: string
  qa_type: string
  description?: string | null
  effective_note?: string | null
  applicability?: Record<string, unknown>
  source_type?: 'USER_DEFINED' | 'REFERENCE' | 'INTERNAL' | 'SITE_APPROVED'
  source_reference?: string | null
  rules: QAProtocolRuleInput[]
}
export type QAProtocolCreateInput = QAProtocolDefinitionInput & { activate?: boolean }
export type QAProtocolValidationResource = {
  valid: boolean
  errors: Array<{ code: string; field: string | null; message: string }>
  warnings: Array<{ code: string; field: string | null; message: string }>
}
export type QAProtocolCompareResource = {
  left: QAProtocolResource
  right: QAProtocolResource
  same_family: boolean
  metadata_diffs: Array<{ field: string; left: unknown; right: unknown }>
  rule_diffs: Array<{ field: string; left: unknown; right: unknown }>
}
export type MachineQAMeasurement = {
  metric_key: string
  value: number | null
  unit: string
  note: string | null
  context?: Record<string, string>
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
export type BaselineResource = {
  id: string
  organization_id: string
  machine_id: string
  metric_key: string
  unit: string
  name: string
  version_number: number
  baseline_value: number
  tolerance: number | null
  action_level: number | null
  effective_from: string
  effective_to: string | null
  status: string
  source_type: string
  source_id: string | null
  context: Record<string, unknown>
  created_at: string
  updated_at: string
}
export type MaintenanceEventResource = {
  id: string
  organization_id: string
  machine_id: string
  machine_name: string
  event_type: string
  title: string
  started_at: string
  ended_at: string | null
  notes: string | null
  revision_number: number
  status: string
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}
export type TrendPointResource = {
  id: string
  machine_id: string
  machine_name: string
  qa_case_id: string
  source_run_id: string
  metric_key: string
  value: number
  unit: string
  status: string
  measured_at: string
  context: Record<string, unknown>
  compatibility_signature: string
  source_archived: boolean
  source_status: string
  baseline_value: number | null
  baseline_delta: number | null
  is_outlier: boolean
}
export type TrendBucketResource = {
  start_at: string
  end_at: string
  count: number
  mean: number
  minimum: number
  maximum: number
  first_value: number
  last_value: number
  statuses: Record<string, number>
  source_point_ids: string[]
  source_run_ids: string[]
}
export type TrendSeriesResource = {
  machine_id: string
  machine_name: string
  metric_key: string
  unit: string
  context: Record<string, unknown>
  compatibility_signature: string
  baseline: BaselineResource | null
  points: TrendPointResource[]
  buckets: TrendBucketResource[]
}
export type TrendResource = {
  organization_id: string
  timezone: string
  aggregate: 'raw' | 'day' | 'week'
  from_at: string | null
  to_at: string | null
  total_points: number
  series: TrendSeriesResource[]
  maintenance_events: MaintenanceEventResource[]
  baselines: BaselineResource[]
  warnings: string[]
}

export type BiologicalScenarioResource = {
  id: string
  organization_id: string
  scenario_key: string
  name: string
  scenario_type: string
  tissue_context: string
  clinical_context: string | null
  source_type: string
  source_reference: string | null
  assumptions: Record<string, unknown>
  status: string
  revision: number
  source_scenario_revision_id: string | null
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
  latest_snapshot: Record<string, unknown> | null
}
export type BiologicalScenarioCreateInput = {
  scenario_key: string
  name: string
  scenario_type: string
  tissue_context: string
  clinical_context?: string | null
  source_type?: 'USER_DEFINED' | 'REFERENCE' | 'INTERNAL' | 'SITE_APPROVED'
  source_reference?: string | null
  assumptions?: Record<string, unknown>
}
export type BiologicalScenarioRevisionResource = {
  id: string
  organization_id: string
  scenario_id: string
  revision_number: number
  status: string
  snapshot: Record<string, unknown>
  created_by_user_identity_id: string | null
  created_at: string
}
export type BiologicalCalculationResource = {
  id: string
  organization_id: string
  scenario_id: string
  scenario_revision_id: string
  calculation_type: string
  idempotency_key: string | null
  model_key: string
  model_version: string
  status: string
  input_snapshot: Record<string, unknown>
  result_snapshot: Record<string, unknown>
  warning_snapshot: Array<Record<string, unknown>>
  error_snapshot: Array<Record<string, unknown>>
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
}
export type BiologicalToolResource = {
  tool_key: string
  label: string
  route: string
  phase: string
  status: string
  available: boolean
  description: string
}
export type BiologicalSummaryResource = {
  organization_id: string
  total_scenarios: number
  draft_scenarios: number
  saved_scenarios: number
  archived_scenarios: number
  completed_calculations: number
  exported_reports: number
}
export type BiologicalLibraryEntryResource = {
  id: string
  organization_id: string
  entry_type: 'DOSE_LIMIT' | 'TREATMENT_PROTOCOL' | 'KNOWLEDGE' | 'ALPHA_BETA'
  entry_key: string
  name: string
  version_number: number
  status: 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
  revision: number
  description: string | null
  effective_note: string | null
  disease: string | null
  disease_subtype: string | null
  anatomy_site: string | null
  treatment_intent: string | null
  technique: string | null
  fractions: number | null
  tissue_or_oar: string | null
  metric_key: string | null
  operator: string | null
  limit_value: number | null
  lower_limit: number | null
  upper_limit: number | null
  unit: string | null
  volume_cc: number | null
  metric_parameter: number | null
  alpha_beta_gy: number | null
  model_key: string | null
  model_version: string | null
  applicability: Record<string, unknown>
  content: Record<string, unknown>
  source_type: 'USER_DEFINED' | 'REFERENCE' | 'INTERNAL' | 'SITE_APPROVED'
  source_reference: string | null
  reference_status: 'UNVERIFIED' | 'AVAILABLE' | 'UNAVAILABLE'
  source_date: string | null
  evidence_level: string | null
  citation: Record<string, unknown>
  content_sha256: string
  source_entry_id: string | null
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
}
export type BiologicalLibraryDefinitionInput = {
  entry_key: string
  entry_type: BiologicalLibraryEntryResource['entry_type']
  name: string
  description?: string | null
  effective_note?: string | null
  disease?: string | null
  disease_subtype?: string | null
  anatomy_site?: string | null
  treatment_intent?: string | null
  technique?: string | null
  fractions?: number | null
  tissue_or_oar?: string | null
  metric_key?: string | null
  operator?: string | null
  limit_value?: number | null
  lower_limit?: number | null
  upper_limit?: number | null
  unit?: string | null
  volume_cc?: number | null
  metric_parameter?: number | null
  alpha_beta_gy?: number | null
  model_key?: string | null
  model_version?: string | null
  applicability?: Record<string, unknown>
  content?: Record<string, unknown>
  source_type?: BiologicalLibraryEntryResource['source_type']
  source_reference?: string | null
  reference_status?: BiologicalLibraryEntryResource['reference_status']
  source_date?: string | null
  evidence_level?: string | null
  citation?: Record<string, unknown>
}
export type BiologicalLibraryValidationResource = {
  valid: boolean
  errors: Array<{ code: string; field: string | null; message: string }>
  warnings: Array<{ code: string; field: string | null; message: string }>
  normalized_entry: Record<string, unknown> | null
  content_sha256: string | null
}
export type BiologicalLibraryImportRowResource = {
  row_number: number
  valid: boolean
  errors: Array<{ code: string; field: string | null; message: string }>
  warnings: Array<{ code: string; field: string | null; message: string }>
  entry_id: string | null
}
export type BiologicalLibraryImportResource = {
  dry_run: boolean
  committed_count: number
  rejected_count: number
  rows: BiologicalLibraryImportRowResource[]
  entries: BiologicalLibraryEntryResource[]
}
export type BiologicalLibraryCompareResource = {
  left: BiologicalLibraryEntryResource
  right: BiologicalLibraryEntryResource
  same_family: boolean
  metadata_diffs: Array<{ field: string; left: unknown; right: unknown }>
  content_diffs: Array<{ field: string; left: unknown; right: unknown }>
}
export type BiologicalLibraryUseResource = {
  schema_version: string
  target_tool: 'P13_BED_EQD2' | 'P14_PLAN_COMPARISON' | 'P15_REIRRADIATION' | 'P15_FRACTION_COMPENSATION' | 'P17_DVH' | 'KNOWLEDGE_REFERENCE'
  entry: BiologicalLibraryEntryResource
  source_snapshot: Record<string, unknown>
  effective_values: Record<string, unknown>
  override: Record<string, unknown>
  override_label: string | null
  snapshot_sha256: string
  warnings: Array<{ code: string; field: string | null; message: string }>
}
export type BiologicalLibraryPatchInput = Partial<BiologicalLibraryDefinitionInput> & { expected_revision: number }
export type BedEqd2CurveInput = {
  mode: 'FIXED_N' | 'FIXED_D'
  dose_min_gy: number
  dose_max_gy: number
  dose_step_gy: number
  fixed_n?: number | null
  fixed_d_gy?: number | null
  alpha_beta_values_gy: number[]
  point_limit: number
}
export type BedEqd2CalculationInput = {
  scenario_revision_id: string
  idempotency_key: string
  total_dose_gy?: number | null
  fractions?: number | null
  dose_per_fraction_gy?: number | null
  consistency_tolerance_gy: number
  alpha_beta_gy: number
  alpha_beta_source_type: 'USER_DEFINED' | 'REFERENCE'
  alpha_beta_source_reference: string
  curve: BedEqd2CurveInput
}
export type BedEqd2ValidationResource = {
  valid: boolean
  errors: Array<{ code: string; field: string | null; message: string }>
  warnings: Array<{ code: string; field: string | null; message: string }>
  normalized_input: Record<string, unknown> | null
  preview: Record<string, unknown> | null
}
export type BedEqd2ChartResource = {
  calculation_id: string
  scenario_id: string
  scenario_revision_id: string
  model_key: string
  model_version: string
  persisted: boolean
  chart_dataset: Record<string, unknown>
  table_rows: Array<Record<string, unknown>>
}
export type PlanComparisonOptionInput = {
  option_id: string
  label: string
  calculation_id: string
}
export type PlanComparisonInput = {
  name: string
  idempotency_key: string
  baseline_option_id: string
  options: PlanComparisonOptionInput[]
}
export type PlanComparisonValidationResource = {
  valid: boolean
  errors: Array<{ code: string; field: string | null; message: string }>
  warnings: Array<{ code: string; field: string | null; message: string }>
  normalized_input: Record<string, unknown> | null
  preview: Record<string, unknown> | null
}
export type PlanComparisonResource = {
  id: string
  organization_id: string
  scenario_id: string
  scenario_revision_id: string
  name: string
  idempotency_key: string
  model_key: string
  model_version: string
  status: string
  input_snapshot: Record<string, unknown>
  result_snapshot: Record<string, unknown>
  warning_snapshot: Array<Record<string, unknown>>
  error_snapshot: Array<Record<string, unknown>>
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
}
export type PlanComparisonChartResource = {
  comparison_id: string
  scenario_id: string
  scenario_revision_id: string
  baseline_option_id: string
  model_key: string
  model_version: string
  persisted: boolean
  option_order: string[]
  chart_dataset: Record<string, unknown>
  table_rows: Array<Record<string, unknown>>
}
export type ReIrradiationTissueDoseInput = {
  tissue_key: string
  dose_metric: string
  dose_unit: 'Gy'
  total_dose_gy?: number | null
  fractions?: number | null
  dose_per_fraction_gy?: number | null
  fraction_doses_gy?: number[] | null
  consistency_tolerance_gy?: number
  alpha_beta_gy: number
  alpha_beta_source_type: 'USER_DEFINED' | 'REFERENCE'
  alpha_beta_source_reference: string
}
export type ReIrradiationCourseInput = {
  course_id: string
  label: string
  is_prior: boolean
  start_date?: string | null
  end_date?: string | null
  tissue_doses: ReIrradiationTissueDoseInput[]
  recovery_fraction?: number | null
  recovery_source_type?: 'USER_DEFINED' | 'REFERENCE' | null
  recovery_source_reference?: string | null
}
export type ReIrradiationInput = {
  scenario_revision_id: string
  name: string
  idempotency_key: string
  courses: ReIrradiationCourseInput[]
  recovery_model: Record<string, unknown>
  sensitivity_recovery_fractions: number[]
  spatial: Record<string, unknown>
}
export type FractionCompensationInput = {
  scenario_revision_id: string
  name: string
  idempotency_key: string
  planned_fraction_doses_gy: number[]
  delivered_fraction_doses_gy: number[]
  consistency_tolerance_gy: number
  alpha_beta_gy: number
  alpha_beta_source_type: 'USER_DEFINED' | 'REFERENCE'
  alpha_beta_source_reference: string
  alternatives: Array<Record<string, unknown>>
  interruptions: Array<Record<string, unknown>>
  time_model: Record<string, unknown>
}
export type P15ValidationResource = {
  valid: boolean
  errors: Array<{ code: string; field: string | null; message: string }>
  warnings: Array<{ code: string; field: string | null; message: string }>
  normalized_input: Record<string, unknown> | null
  preview: Record<string, unknown> | null
}
export type P15RunResource = {
  id: string
  organization_id: string
  scenario_id: string
  scenario_revision_id: string
  operation_type: string
  name: string
  idempotency_key: string
  model_key: string
  model_version: string
  status: string
  input_snapshot: Record<string, unknown>
  result_snapshot: Record<string, unknown>
  warning_snapshot: Array<Record<string, unknown>>
  error_snapshot: Array<Record<string, unknown>>
  created_by_user_identity_id: string | null
  created_at: string
  updated_at: string
}

const qaProtocolRuleSchema = z.object({
  id: z.string().uuid(), metric_key: z.string(), display_name: z.string(), unit: z.string(),
  rule_type: z.string(), target_value: z.number().nullable(), lower_limit: z.number().nullable(),
  upper_limit: z.number().nullable(), tolerance: z.number().nullable(), action_level: z.number().nullable(),
  required: z.boolean(), sort_order: z.number().int(), note: z.string().nullable(), reference: z.string().nullable()
})
const qaProtocolSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), protocol_key: z.string(), name: z.string(),
  qa_type: z.string(), version_number: z.number().int(), status: z.string(), revision: z.number().int(),
  description: z.string().nullable(), effective_note: z.string().nullable(),
  applicability: z.record(z.string(), z.unknown()), source_type: z.string(), source_reference: z.string().nullable(),
  source_protocol_version_id: z.string().uuid().nullable(), created_by_user_identity_id: z.string().uuid().nullable(),
  created_at: z.string(), updated_at: z.string(),
  rules: z.array(qaProtocolRuleSchema)
})
const qaProtocolCollectionSchema = z.object({
  items: z.array(qaProtocolSchema), total: z.number().int(), offset: z.number().int(), limit: z.number().int(), include_archived: z.boolean()
})
const qaProtocolValidationSchema = z.object({
  valid: z.boolean(),
  errors: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  warnings: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() }))
})
const qaProtocolCompareSchema = z.object({
  left: qaProtocolSchema, right: qaProtocolSchema, same_family: z.boolean(),
  metadata_diffs: z.array(z.object({ field: z.string(), left: z.unknown().nullable(), right: z.unknown().nullable() })),
  rule_diffs: z.array(z.object({ field: z.string(), left: z.unknown().nullable(), right: z.unknown().nullable() }))
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
const baselineSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), machine_id: z.string().uuid(),
  metric_key: z.string(), unit: z.string(), name: z.string(), version_number: z.number().int(),
  baseline_value: z.number(), tolerance: z.number().nullable(), action_level: z.number().nullable(),
  effective_from: z.string(), effective_to: z.string().nullable(), status: z.string(),
  source_type: z.string(), source_id: z.string().uuid().nullable(), context: z.record(z.string(), z.unknown()),
  created_at: z.string(), updated_at: z.string()
})
const maintenanceSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), machine_id: z.string().uuid(),
  machine_name: z.string(), event_type: z.string(), title: z.string(), started_at: z.string(),
  ended_at: z.string().nullable(), notes: z.string().nullable(), revision_number: z.number().int(),
  status: z.string(), metadata: z.record(z.string(), z.unknown()), created_at: z.string(), updated_at: z.string()
})
const trendPointSchema = z.object({
  id: z.string().uuid(), machine_id: z.string().uuid(), machine_name: z.string(), qa_case_id: z.string().uuid(),
  source_run_id: z.string().uuid(), metric_key: z.string(), value: z.number(), unit: z.string(), status: z.string(),
  measured_at: z.string(), context: z.record(z.string(), z.unknown()), compatibility_signature: z.string(),
  source_archived: z.boolean(), source_status: z.string(), baseline_value: z.number().nullable(),
  baseline_delta: z.number().nullable(), is_outlier: z.boolean()
})
const trendBucketSchema = z.object({
  start_at: z.string(), end_at: z.string(), count: z.number().int(), mean: z.number(), minimum: z.number(),
  maximum: z.number(), first_value: z.number(), last_value: z.number(), statuses: z.record(z.string(), z.number().int()),
  source_point_ids: z.array(z.string().uuid()), source_run_ids: z.array(z.string().uuid())
})
const trendSeriesSchema = z.object({
  machine_id: z.string().uuid(), machine_name: z.string(), metric_key: z.string(), unit: z.string(),
  context: z.record(z.string(), z.unknown()), compatibility_signature: z.string(), baseline: baselineSchema.nullable(),
  points: z.array(trendPointSchema), buckets: z.array(trendBucketSchema)
})
const trendSchema = z.object({
  organization_id: z.string().uuid(), timezone: z.string(), aggregate: z.enum(['raw', 'day', 'week']),
  from_at: z.string().nullable(), to_at: z.string().nullable(), total_points: z.number().int(),
  series: z.array(trendSeriesSchema), maintenance_events: z.array(maintenanceSchema),
  baselines: z.array(baselineSchema), warnings: z.array(z.string())
})
const biologicalScenarioSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), scenario_key: z.string(),
  name: z.string(), scenario_type: z.string(), tissue_context: z.string(),
  clinical_context: z.string().nullable(), source_type: z.string(), source_reference: z.string().nullable(),
  assumptions: z.record(z.string(), z.unknown()), status: z.string(), revision: z.number().int(),
  source_scenario_revision_id: z.string().uuid().nullable(),
  created_by_user_identity_id: z.string().uuid().nullable(), created_at: z.string(), updated_at: z.string(),
  latest_snapshot: z.record(z.string(), z.unknown()).nullable()
})
const biologicalScenarioCollectionSchema = z.object({
  items: z.array(biologicalScenarioSchema), total: z.number().int(), offset: z.number().int(),
  limit: z.number().int(), include_archived: z.boolean()
})
const biologicalScenarioRevisionSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), scenario_id: z.string().uuid(),
  revision_number: z.number().int(), status: z.string(), snapshot: z.record(z.string(), z.unknown()),
  created_by_user_identity_id: z.string().uuid().nullable(), created_at: z.string()
})
const biologicalCalculationSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), scenario_id: z.string().uuid(),
  scenario_revision_id: z.string().uuid(), calculation_type: z.string(), idempotency_key: z.string().nullable(), model_key: z.string(),
  model_version: z.string(), status: z.string(), input_snapshot: z.record(z.string(), z.unknown()),
  result_snapshot: z.record(z.string(), z.unknown()),
  warning_snapshot: z.array(z.record(z.string(), z.unknown())),
  error_snapshot: z.array(z.record(z.string(), z.unknown())),
  created_by_user_identity_id: z.string().uuid().nullable(), created_at: z.string(), updated_at: z.string()
})
const biologicalCalculationCollectionSchema = z.object({
  items: z.array(biologicalCalculationSchema), total: z.number().int(), offset: z.number().int(), limit: z.number().int()
})
const biologicalToolSchema = z.object({
  tool_key: z.string(), label: z.string(), route: z.string(), phase: z.string(), status: z.string(),
  available: z.boolean(), description: z.string()
})
const biologicalSummarySchema = z.object({
  organization_id: z.string().uuid(), total_scenarios: z.number().int(), draft_scenarios: z.number().int(),
  saved_scenarios: z.number().int(), archived_scenarios: z.number().int(),
  completed_calculations: z.number().int(), exported_reports: z.number().int()
})
const libraryIssueSchema = z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })
const biologicalLibraryEntrySchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(),
  entry_type: z.enum(['DOSE_LIMIT', 'TREATMENT_PROTOCOL', 'KNOWLEDGE', 'ALPHA_BETA']),
  entry_key: z.string(), name: z.string(), version_number: z.number().int(),
  status: z.enum(['DRAFT', 'PUBLISHED', 'ARCHIVED']), revision: z.number().int(),
  description: z.string().nullable(), effective_note: z.string().nullable(),
  disease: z.string().nullable(), disease_subtype: z.string().nullable(), anatomy_site: z.string().nullable(),
  treatment_intent: z.string().nullable(), technique: z.string().nullable(), fractions: z.number().int().nullable(),
  tissue_or_oar: z.string().nullable(), metric_key: z.string().nullable(), operator: z.string().nullable(),
  limit_value: z.number().nullable(), lower_limit: z.number().nullable(), upper_limit: z.number().nullable(),
  unit: z.string().nullable(), volume_cc: z.number().nullable(), metric_parameter: z.number().nullable(),
  alpha_beta_gy: z.number().nullable(), model_key: z.string().nullable(), model_version: z.string().nullable(),
  applicability: z.record(z.string(), z.unknown()), content: z.record(z.string(), z.unknown()),
  source_type: z.enum(['USER_DEFINED', 'REFERENCE', 'INTERNAL', 'SITE_APPROVED']),
  source_reference: z.string().nullable(),
  reference_status: z.enum(['UNVERIFIED', 'AVAILABLE', 'UNAVAILABLE']), source_date: z.string().nullable(),
  evidence_level: z.string().nullable(), citation: z.record(z.string(), z.unknown()), content_sha256: z.string(),
  source_entry_id: z.string().uuid().nullable(), created_by_user_identity_id: z.string().uuid().nullable(),
  created_at: z.string(), updated_at: z.string()
})
const biologicalLibraryCollectionSchema = z.object({
  items: z.array(biologicalLibraryEntrySchema), total: z.number().int(), offset: z.number().int(),
  limit: z.number().int(), include_archived: z.boolean()
})
const biologicalLibraryValidationSchema = z.object({
  valid: z.boolean(), errors: z.array(libraryIssueSchema), warnings: z.array(libraryIssueSchema),
  normalized_entry: z.record(z.string(), z.unknown()).nullable(), content_sha256: z.string().nullable()
})
const biologicalLibraryImportRowSchema = z.object({
  row_number: z.number().int(), valid: z.boolean(), errors: z.array(libraryIssueSchema),
  warnings: z.array(libraryIssueSchema), entry_id: z.string().uuid().nullable()
})
const biologicalLibraryImportSchema = z.object({
  dry_run: z.boolean(), committed_count: z.number().int(), rejected_count: z.number().int(),
  rows: z.array(biologicalLibraryImportRowSchema), entries: z.array(biologicalLibraryEntrySchema)
})
const biologicalLibraryCompareSchema = z.object({
  left: biologicalLibraryEntrySchema, right: biologicalLibraryEntrySchema, same_family: z.boolean(),
  metadata_diffs: z.array(z.object({ field: z.string(), left: z.unknown(), right: z.unknown() })),
  content_diffs: z.array(z.object({ field: z.string(), left: z.unknown(), right: z.unknown() }))
})
const biologicalLibraryUseSchema = z.object({
  schema_version: z.string(), target_tool: z.enum(['P13_BED_EQD2', 'P14_PLAN_COMPARISON', 'P15_REIRRADIATION', 'P15_FRACTION_COMPENSATION', 'P17_DVH', 'KNOWLEDGE_REFERENCE']),
  entry: biologicalLibraryEntrySchema, source_snapshot: z.record(z.string(), z.unknown()),
  effective_values: z.record(z.string(), z.unknown()), override: z.record(z.string(), z.unknown()),
  override_label: z.string().nullable(), snapshot_sha256: z.string(), warnings: z.array(libraryIssueSchema)
})
const biologicalValidationSchema = z.object({
  valid: z.boolean(),
  errors: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  warnings: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() }))
})
const bedEqd2ValidationSchema = z.object({
  valid: z.boolean(),
  errors: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  warnings: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  normalized_input: z.record(z.string(), z.unknown()).nullable(),
  preview: z.record(z.string(), z.unknown()).nullable()
})
const bedEqd2ChartSchema = z.object({
  calculation_id: z.string().uuid(), scenario_id: z.string().uuid(), scenario_revision_id: z.string().uuid(),
  model_key: z.string(), model_version: z.string(), persisted: z.boolean(),
  chart_dataset: z.record(z.string(), z.unknown()), table_rows: z.array(z.record(z.string(), z.unknown()))
})
const planComparisonValidationSchema = z.object({
  valid: z.boolean(),
  errors: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  warnings: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  normalized_input: z.record(z.string(), z.unknown()).nullable(),
  preview: z.record(z.string(), z.unknown()).nullable()
})
const planComparisonSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), scenario_id: z.string().uuid(),
  scenario_revision_id: z.string().uuid(), name: z.string(), idempotency_key: z.string(),
  model_key: z.string(), model_version: z.string(), status: z.string(),
  input_snapshot: z.record(z.string(), z.unknown()), result_snapshot: z.record(z.string(), z.unknown()),
  warning_snapshot: z.array(z.record(z.string(), z.unknown())), error_snapshot: z.array(z.record(z.string(), z.unknown())),
  created_by_user_identity_id: z.string().uuid().nullable(), created_at: z.string(), updated_at: z.string()
})
const planComparisonCollectionSchema = z.object({
  items: z.array(planComparisonSchema), total: z.number().int(), offset: z.number().int(), limit: z.number().int()
})
const planComparisonChartSchema = z.object({
  comparison_id: z.string().uuid(), scenario_id: z.string().uuid(), scenario_revision_id: z.string().uuid(),
  baseline_option_id: z.string(), model_key: z.string(), model_version: z.string(), persisted: z.boolean(),
  option_order: z.array(z.string()), chart_dataset: z.record(z.string(), z.unknown()),
  table_rows: z.array(z.record(z.string(), z.unknown()))
})
const p15ValidationSchema = z.object({
  valid: z.boolean(),
  errors: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  warnings: z.array(z.object({ code: z.string(), field: z.string().nullable(), message: z.string() })),
  normalized_input: z.record(z.string(), z.unknown()).nullable(),
  preview: z.record(z.string(), z.unknown()).nullable()
})
const p15RunSchema = z.object({
  id: z.string().uuid(), organization_id: z.string().uuid(), scenario_id: z.string().uuid(),
  scenario_revision_id: z.string().uuid(), operation_type: z.string(), name: z.string(),
  idempotency_key: z.string(), model_key: z.string(), model_version: z.string(), status: z.string(),
  input_snapshot: z.record(z.string(), z.unknown()), result_snapshot: z.record(z.string(), z.unknown()),
  warning_snapshot: z.array(z.record(z.string(), z.unknown())),
  error_snapshot: z.array(z.record(z.string(), z.unknown())),
  created_by_user_identity_id: z.string().uuid().nullable(), created_at: z.string(), updated_at: z.string()
})
const p15CollectionSchema = z.object({
  items: z.array(p15RunSchema), total: z.number().int(), offset: z.number().int(), limit: z.number().int()
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

  qaProtocols(accessToken: string, organizationId: string, params: {
    q?: string
    status?: 'DRAFT' | 'ACTIVE' | 'ARCHIVED'
    include_archived?: boolean
  } = {}): Promise<{ items: QAProtocolResource[]; total: number; offset: number; limit: number; include_archived: boolean }> {
    const query = new URLSearchParams()
    if (params.q) query.set('q', params.q)
    if (params.status) query.set('status', params.status)
    if (params.include_archived) query.set('include_archived', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return this.get(`/organizations/${organizationId}/qa-protocols${suffix}`, qaProtocolCollectionSchema, accessToken)
  }

  validateQAProtocol(accessToken: string, organizationId: string, body: QAProtocolDefinitionInput): Promise<QAProtocolValidationResource> {
    return this.request(`/organizations/${organizationId}/qa-protocols/validate`, qaProtocolValidationSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  createQAProtocol(accessToken: string, organizationId: string, body: QAProtocolCreateInput): Promise<QAProtocolResource> {
    return this.request(`/organizations/${organizationId}/qa-protocols`, qaProtocolSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  updateQAProtocol(accessToken: string, organizationId: string, protocolId: string, body: {
    expected_revision: number
    protocol_key?: string
    name?: string
    qa_type?: string
    description?: string | null
    effective_note?: string | null
    applicability?: Record<string, unknown>
    source_type?: QAProtocolCreateInput['source_type']
    source_reference?: string | null
    rules?: QAProtocolRuleInput[]
  }): Promise<QAProtocolResource> {
    return this.request(`/organizations/${organizationId}/qa-protocols/${protocolId}`, qaProtocolSchema, accessToken, {
      method: 'PATCH', body: JSON.stringify(body)
    })
  }

  cloneQAProtocol(accessToken: string, organizationId: string, protocolId: string, body: { name?: string; protocol_key?: string; activate?: boolean } = {}): Promise<QAProtocolResource> {
    return this.request(`/organizations/${organizationId}/qa-protocols/${protocolId}/clone`, qaProtocolSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  activateQAProtocol(accessToken: string, organizationId: string, protocolId: string, expectedRevision: number): Promise<QAProtocolResource> {
    return this.request(`/organizations/${organizationId}/qa-protocols/${protocolId}/activate`, qaProtocolSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision })
    })
  }

  archiveQAProtocol(accessToken: string, organizationId: string, protocolId: string, expectedRevision: number): Promise<QAProtocolResource> {
    return this.request(`/organizations/${organizationId}/qa-protocols/${protocolId}/archive`, qaProtocolSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision })
    })
  }

  compareQAProtocols(accessToken: string, organizationId: string, protocolId: string, otherId: string): Promise<QAProtocolCompareResource> {
    return this.get(`/organizations/${organizationId}/qa-protocols/${protocolId}/compare?other_id=${encodeURIComponent(otherId)}`, qaProtocolCompareSchema, accessToken)
  }

  biologicalTools(accessToken: string, organizationId: string): Promise<BiologicalToolResource[]> {
    return this.get(`/organizations/${organizationId}/biological/tools`, z.array(biologicalToolSchema), accessToken)
  }

  biologicalSummary(accessToken: string, organizationId: string): Promise<BiologicalSummaryResource> {
    return this.get(`/organizations/${organizationId}/biological/summary`, biologicalSummarySchema, accessToken)
  }

  biologicalScenarios(accessToken: string, organizationId: string, params: {
    q?: string
    status?: 'DRAFT' | 'SAVED' | 'ARCHIVED'
    include_archived?: boolean
  } = {}): Promise<{ items: BiologicalScenarioResource[]; total: number; offset: number; limit: number; include_archived: boolean }> {
    const query = new URLSearchParams()
    if (params.q) query.set('q', params.q)
    if (params.status) query.set('status', params.status)
    if (params.include_archived || params.status === 'ARCHIVED') query.set('include_archived', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return this.get(`/organizations/${organizationId}/biological/scenarios${suffix}`, biologicalScenarioCollectionSchema, accessToken)
  }

  validateBiologicalScenario(accessToken: string, organizationId: string, body: BiologicalScenarioCreateInput): Promise<{ valid: boolean; errors: Array<{ code: string; field: string | null; message: string }>; warnings: Array<{ code: string; field: string | null; message: string }> }> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/validate`, biologicalValidationSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  createBiologicalScenario(accessToken: string, organizationId: string, body: BiologicalScenarioCreateInput): Promise<BiologicalScenarioResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios`, biologicalScenarioSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  biologicalScenario(accessToken: string, organizationId: string, scenarioId: string): Promise<BiologicalScenarioResource> {
    return this.get(`/organizations/${organizationId}/biological/scenarios/${scenarioId}`, biologicalScenarioSchema, accessToken)
  }

  updateBiologicalScenario(accessToken: string, organizationId: string, scenarioId: string, body: {
    expected_revision: number
    name?: string
    scenario_type?: string
    tissue_context?: string
    clinical_context?: string | null
    source_type?: BiologicalScenarioCreateInput['source_type']
    source_reference?: string | null
    assumptions?: Record<string, unknown>
  }): Promise<BiologicalScenarioResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}`, biologicalScenarioSchema, accessToken, {
      method: 'PATCH', body: JSON.stringify(body)
    })
  }

  saveBiologicalScenario(accessToken: string, organizationId: string, scenarioId: string, expectedRevision: number): Promise<BiologicalScenarioResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/save`, biologicalScenarioSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision })
    })
  }

  cloneBiologicalScenario(accessToken: string, organizationId: string, scenarioId: string, body: { scenario_key?: string; name?: string } = {}): Promise<BiologicalScenarioResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/clone`, biologicalScenarioSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  archiveBiologicalScenario(accessToken: string, organizationId: string, scenarioId: string, expectedRevision: number): Promise<BiologicalScenarioResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/archive`, biologicalScenarioSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision })
    })
  }

  biologicalScenarioRevisions(accessToken: string, organizationId: string, scenarioId: string): Promise<BiologicalScenarioRevisionResource[]> {
    return this.get(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/revisions`, z.array(biologicalScenarioRevisionSchema), accessToken)
  }

  biologicalLibrary(accessToken: string, organizationId: string, params: {
    q?: string
    entry_type?: BiologicalLibraryEntryResource['entry_type']
    status?: BiologicalLibraryEntryResource['status']
    disease?: string
    anatomy_site?: string
    technique?: string
    tissue_or_oar?: string
    metric_key?: string
    fractions?: number
    include_archived?: boolean
  } = {}): Promise<{ items: BiologicalLibraryEntryResource[]; total: number; offset: number; limit: number; include_archived: boolean }> {
    const query = new URLSearchParams()
    for (const key of ['q', 'entry_type', 'status', 'disease', 'anatomy_site', 'technique', 'tissue_or_oar', 'metric_key'] as const) {
      const value = params[key]
      if (value) query.set(key, value)
    }
    if (params.fractions !== undefined) query.set('fractions', String(params.fractions))
    if (params.include_archived || params.status === 'ARCHIVED') query.set('include_archived', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return this.get(`/organizations/${organizationId}/biological/library${suffix}`, biologicalLibraryCollectionSchema, accessToken)
  }

  biologicalLibraryEntry(accessToken: string, organizationId: string, entryId: string): Promise<BiologicalLibraryEntryResource> {
    return this.get(`/organizations/${organizationId}/biological/library/${entryId}`, biologicalLibraryEntrySchema, accessToken)
  }

  validateBiologicalLibraryEntry(accessToken: string, organizationId: string, body: BiologicalLibraryDefinitionInput): Promise<BiologicalLibraryValidationResource> {
    return this.request(`/organizations/${organizationId}/biological/library/validate`, biologicalLibraryValidationSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  createBiologicalLibraryEntry(accessToken: string, organizationId: string, body: BiologicalLibraryDefinitionInput & { publish?: boolean }): Promise<BiologicalLibraryEntryResource> {
    return this.request(`/organizations/${organizationId}/biological/library`, biologicalLibraryEntrySchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  updateBiologicalLibraryEntry(accessToken: string, organizationId: string, entryId: string, body: BiologicalLibraryPatchInput): Promise<BiologicalLibraryEntryResource> {
    return this.request(`/organizations/${organizationId}/biological/library/${entryId}`, biologicalLibraryEntrySchema, accessToken, {
      method: 'PATCH', body: JSON.stringify(body)
    })
  }

  biologicalLibraryRevisions(accessToken: string, organizationId: string, entryId: string): Promise<BiologicalLibraryEntryResource[]> {
    return this.get(`/organizations/${organizationId}/biological/library/${entryId}/revisions`, z.array(biologicalLibraryEntrySchema), accessToken)
  }

  cloneBiologicalLibraryEntry(accessToken: string, organizationId: string, entryId: string, body: { entry_key?: string; name?: string; publish?: boolean } = {}): Promise<BiologicalLibraryEntryResource> {
    return this.request(`/organizations/${organizationId}/biological/library/${entryId}/clone`, biologicalLibraryEntrySchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  publishBiologicalLibraryEntry(accessToken: string, organizationId: string, entryId: string, expectedRevision: number): Promise<BiologicalLibraryEntryResource> {
    return this.request(`/organizations/${organizationId}/biological/library/${entryId}/publish`, biologicalLibraryEntrySchema, accessToken, {
      method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision })
    })
  }

  archiveBiologicalLibraryEntry(accessToken: string, organizationId: string, entryId: string, expectedRevision: number): Promise<BiologicalLibraryEntryResource> {
    return this.request(`/organizations/${organizationId}/biological/library/${entryId}/archive`, biologicalLibraryEntrySchema, accessToken, {
      method: 'POST', body: JSON.stringify({ expected_revision: expectedRevision })
    })
  }

  compareBiologicalLibraryEntries(accessToken: string, organizationId: string, entryId: string, otherId: string): Promise<BiologicalLibraryCompareResource> {
    return this.get(`/organizations/${organizationId}/biological/library/${entryId}/compare?other_id=${encodeURIComponent(otherId)}`, biologicalLibraryCompareSchema, accessToken)
  }

  useBiologicalLibraryEntry(accessToken: string, organizationId: string, entryId: string, body: {
    target_tool: BiologicalLibraryUseResource['target_tool']
    override?: Record<string, unknown>
  }): Promise<BiologicalLibraryUseResource> {
    return this.request(`/organizations/${organizationId}/biological/library/${entryId}/use`, biologicalLibraryUseSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  validateBiologicalLibraryImport(accessToken: string, organizationId: string, rows: BiologicalLibraryDefinitionInput[]): Promise<BiologicalLibraryImportResource> {
    return this.request(`/organizations/${organizationId}/biological/library/import/validate`, biologicalLibraryImportSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ rows })
    })
  }

  importBiologicalLibrary(accessToken: string, organizationId: string, rows: BiologicalLibraryDefinitionInput[], commitValid = true): Promise<BiologicalLibraryImportResource> {
    return this.request(`/organizations/${organizationId}/biological/library/import`, biologicalLibraryImportSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ rows, commit_valid: commitValid })
    })
  }

  async downloadBiologicalLibrary(accessToken: string, organizationId: string, entryId: string, exportFormat: 'JSON' | 'CSV'): Promise<Blob> {
    const correlationId = makeCorrelationId()
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}/organizations/${organizationId}/biological/library/${entryId}/export?export_format=${exportFormat}`, {
        headers: { Accept: exportFormat === 'JSON' ? 'application/json' : 'text/csv', 'X-Correlation-ID': correlationId, Authorization: `Bearer ${accessToken}` }
      })
    } catch {
      throw new ApiClientError('Không thể kết nối tới RT-CONNECT API.', 'NETWORK_ERROR', correlationId)
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => undefined)
      const parsed = errorSchema.safeParse(body)
      if (parsed.success) throw new ApiClientError(parsed.data.message, parsed.data.code, parsed.data.correlation_id)
      throw new ApiClientError('API trả về phản hồi không hợp lệ.', 'INVALID_API_RESPONSE', correlationId)
    }
    return response.blob()
  }

  biologicalCalculations(accessToken: string, organizationId: string, scenarioId?: string): Promise<{ items: BiologicalCalculationResource[]; total: number; offset: number; limit: number }> {
    const suffix = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ''
    return this.get(`/organizations/${organizationId}/biological/calculations${suffix}`, biologicalCalculationCollectionSchema, accessToken)
  }

  biologicalCalculation(accessToken: string, organizationId: string, calculationId: string): Promise<BiologicalCalculationResource> {
    return this.get(`/organizations/${organizationId}/biological/calculations/${calculationId}`, biologicalCalculationSchema, accessToken)
  }

  validateBedEqd2(accessToken: string, organizationId: string, scenarioId: string, body: BedEqd2CalculationInput): Promise<BedEqd2ValidationResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/calculations/validate`, bedEqd2ValidationSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  createBedEqd2Calculation(accessToken: string, organizationId: string, scenarioId: string, body: BedEqd2CalculationInput): Promise<BiologicalCalculationResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/calculations`, biologicalCalculationSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  bedEqd2Chart(accessToken: string, organizationId: string, calculationId: string, curve: BedEqd2CurveInput): Promise<BedEqd2ChartResource> {
    return this.request(`/organizations/${organizationId}/biological/calculations/${calculationId}/charts`, bedEqd2ChartSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ curve })
    })
  }

  async downloadBedEqd2(accessToken: string, organizationId: string, calculationId: string, exportFormat: 'JSON' | 'CSV'): Promise<Blob> {
    const correlationId = makeCorrelationId()
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}/organizations/${organizationId}/biological/calculations/${calculationId}/export?export_format=${exportFormat}`, {
        headers: { Accept: exportFormat === 'JSON' ? 'application/json' : 'text/csv', 'X-Correlation-ID': correlationId, Authorization: `Bearer ${accessToken}` }
      })
    } catch {
      throw new ApiClientError('Không thể kết nối tới RT-CONNECT API.', 'NETWORK_ERROR', correlationId)
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => undefined)
      const parsed = errorSchema.safeParse(body)
      if (parsed.success) throw new ApiClientError(parsed.data.message, parsed.data.code, parsed.data.correlation_id)
      throw new ApiClientError('API trả về phản hồi không hợp lệ.', 'INVALID_API_RESPONSE', correlationId)
    }
    return response.blob()
  }

  planComparisons(accessToken: string, organizationId: string, scenarioId?: string): Promise<{ items: PlanComparisonResource[]; total: number; offset: number; limit: number }> {
    const suffix = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ''
    return this.get(`/organizations/${organizationId}/biological/comparisons${suffix}`, planComparisonCollectionSchema, accessToken)
  }

  validatePlanComparison(accessToken: string, organizationId: string, body: PlanComparisonInput): Promise<PlanComparisonValidationResource> {
    return this.request(`/organizations/${organizationId}/biological/comparisons/validate`, planComparisonValidationSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  createPlanComparison(accessToken: string, organizationId: string, body: PlanComparisonInput): Promise<PlanComparisonResource> {
    return this.request(`/organizations/${organizationId}/biological/comparisons`, planComparisonSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  planComparison(accessToken: string, organizationId: string, comparisonId: string): Promise<PlanComparisonResource> {
    return this.get(`/organizations/${organizationId}/biological/comparisons/${comparisonId}`, planComparisonSchema, accessToken)
  }

  planComparisonChart(accessToken: string, organizationId: string, comparisonId: string, optionOrder?: string[]): Promise<PlanComparisonChartResource> {
    return this.request(`/organizations/${organizationId}/biological/comparisons/${comparisonId}/charts`, planComparisonChartSchema, accessToken, {
      method: 'POST', body: JSON.stringify({ option_order: optionOrder ?? null })
    })
  }

  clonePlanComparison(accessToken: string, organizationId: string, comparisonId: string, body: {
    idempotency_key: string
    name?: string | null
    baseline_option_id?: string | null
    option_order?: string[] | null
  }): Promise<PlanComparisonResource> {
    return this.request(`/organizations/${organizationId}/biological/comparisons/${comparisonId}/clone`, planComparisonSchema, accessToken, {
      method: 'POST', body: JSON.stringify(body)
    })
  }

  async downloadPlanComparison(accessToken: string, organizationId: string, comparisonId: string, exportFormat: 'JSON' | 'CSV'): Promise<Blob> {
    const correlationId = makeCorrelationId()
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}/organizations/${organizationId}/biological/comparisons/${comparisonId}/export?export_format=${exportFormat}`, {
        headers: { Accept: exportFormat === 'JSON' ? 'application/json' : 'text/csv', 'X-Correlation-ID': correlationId, Authorization: `Bearer ${accessToken}` }
      })
    } catch {
      throw new ApiClientError('Không thể kết nối tới RT-CONNECT API.', 'NETWORK_ERROR', correlationId)
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => undefined)
      const parsed = errorSchema.safeParse(body)
      if (parsed.success) throw new ApiClientError(parsed.data.message, parsed.data.code, parsed.data.correlation_id)
      throw new ApiClientError('API trả về phản hồi không hợp lệ.', 'INVALID_API_RESPONSE', correlationId)
    }
    return response.blob()
  }

  reIrradiationRuns(accessToken: string, organizationId: string, scenarioId?: string): Promise<{ items: P15RunResource[]; total: number; offset: number; limit: number }> {
    const suffix = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ''
    return this.get(`/organizations/${organizationId}/biological/re-irradiation${suffix}`, p15CollectionSchema, accessToken)
  }

  validateReIrradiation(accessToken: string, organizationId: string, scenarioId: string, body: ReIrradiationInput): Promise<P15ValidationResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/re-irradiation/validate`, p15ValidationSchema, accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  createReIrradiation(accessToken: string, organizationId: string, scenarioId: string, body: ReIrradiationInput): Promise<P15RunResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/re-irradiation`, p15RunSchema, accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  fractionCompensationRuns(accessToken: string, organizationId: string, scenarioId?: string): Promise<{ items: P15RunResource[]; total: number; offset: number; limit: number }> {
    const suffix = scenarioId ? `?scenario_id=${encodeURIComponent(scenarioId)}` : ''
    return this.get(`/organizations/${organizationId}/biological/fraction-compensation${suffix}`, p15CollectionSchema, accessToken)
  }

  validateFractionCompensation(accessToken: string, organizationId: string, scenarioId: string, body: FractionCompensationInput): Promise<P15ValidationResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/fraction-compensation/validate`, p15ValidationSchema, accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  createFractionCompensation(accessToken: string, organizationId: string, scenarioId: string, body: FractionCompensationInput): Promise<P15RunResource> {
    return this.request(`/organizations/${organizationId}/biological/scenarios/${scenarioId}/fraction-compensation`, p15RunSchema, accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  async downloadP15(accessToken: string, organizationId: string, operation: 're-irradiation' | 'fraction-compensation', runId: string, exportFormat: 'JSON' | 'CSV'): Promise<Blob> {
    const correlationId = makeCorrelationId()
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}/organizations/${organizationId}/biological/${operation}/${runId}/export?export_format=${exportFormat}`, {
        headers: { Accept: exportFormat === 'JSON' ? 'application/json' : 'text/csv', 'X-Correlation-ID': correlationId, Authorization: `Bearer ${accessToken}` }
      })
    } catch {
      throw new ApiClientError('Không thể kết nối tới RT-CONNECT API.', 'NETWORK_ERROR', correlationId)
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => undefined)
      const parsed = errorSchema.safeParse(body)
      if (parsed.success) throw new ApiClientError(parsed.data.message, parsed.data.code, parsed.data.correlation_id)
      throw new ApiClientError('API trả về phản hồi không hợp lệ.', 'INVALID_API_RESPONSE', correlationId)
    }
    return response.blob()
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

  trend(accessToken: string, organizationId: string, params: {
    machine_ids?: string[]
    metric_key?: string
    from?: string
    to?: string
    timezone?: string
    aggregate?: 'raw' | 'day' | 'week'
    unit?: string
    energy?: string
    detector?: string
    phantom?: string
    beam_quality?: string
    acquisition_mode?: string
    protocol_key?: string
    qa_cycle?: string
    include_archived?: boolean
  } = {}): Promise<TrendResource> {
    const query = new URLSearchParams()
    if (params.machine_ids?.length) query.set('machine_ids', params.machine_ids.join(','))
    for (const key of ['metric_key', 'from', 'to', 'timezone', 'aggregate', 'unit', 'energy', 'detector', 'phantom', 'beam_quality', 'acquisition_mode', 'protocol_key', 'qa_cycle'] as const) {
      const value = params[key]
      if (value) query.set(key, value)
    }
    if (params.include_archived) query.set('include_archived', 'true')
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return this.get(`/organizations/${organizationId}/trend${suffix}`, trendSchema, accessToken)
  }

  async exportTrend(accessToken: string, organizationId: string, params: {
    export_format?: 'CSV' | 'JSON'
    machine_ids?: string[]
    metric_key?: string
    from?: string
    to?: string
    timezone?: string
    aggregate?: 'raw' | 'day' | 'week'
    unit?: string
    energy?: string
    detector?: string
    phantom?: string
    beam_quality?: string
    acquisition_mode?: string
    protocol_key?: string
    qa_cycle?: string
    include_archived?: boolean
  } = {}): Promise<Blob> {
    const query = new URLSearchParams({ export_format: params.export_format ?? 'CSV' })
    if (params.machine_ids?.length) query.set('machine_ids', params.machine_ids.join(','))
    for (const key of ['metric_key', 'from', 'to', 'timezone', 'aggregate', 'unit', 'energy', 'detector', 'phantom', 'beam_quality', 'acquisition_mode', 'protocol_key', 'qa_cycle'] as const) {
      const value = params[key]
      if (value) query.set(key, value)
    }
    if (params.include_archived) query.set('include_archived', 'true')
    const correlationId = makeCorrelationId()
    let response: Response
    try {
      response = await fetch(`${this.baseUrl}/organizations/${organizationId}/trend/export?${query.toString()}`, {
        headers: { Accept: 'text/csv, application/json', 'X-Correlation-ID': correlationId, Authorization: `Bearer ${accessToken}` }
      })
    } catch {
      throw new ApiClientError('Không thể kết nối tới RT-CONNECT API.', 'NETWORK_ERROR', correlationId)
    }
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => undefined)
      const parsed = errorSchema.safeParse(body)
      throw new ApiClientError(parsed.success ? parsed.data.message : 'API export trend thất bại.', parsed.success ? parsed.data.code : 'EXPORT_FAILED', parsed.success ? parsed.data.correlation_id : correlationId)
    }
    return response.blob()
  }

  trendBaselines(accessToken: string, organizationId: string, machineId?: string): Promise<BaselineResource[]> {
    const suffix = machineId ? `?machine_id=${encodeURIComponent(machineId)}` : ''
    return this.get(`/organizations/${organizationId}/trend/baselines${suffix}`, z.array(baselineSchema), accessToken)
  }

  createTrendBaseline(accessToken: string, organizationId: string, body: {
    machine_id: string; metric_key: string; unit: string; name: string; baseline_value: number;
    tolerance?: number | null; action_level?: number | null; effective_from: string; effective_to?: string | null; context?: Record<string, string>
  }): Promise<BaselineResource> {
    return this.request(`/organizations/${organizationId}/trend/baselines`, baselineSchema, accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  trendEvents(accessToken: string, organizationId: string, machineId?: string): Promise<MaintenanceEventResource[]> {
    const suffix = machineId ? `?machine_id=${encodeURIComponent(machineId)}` : ''
    return this.get(`/organizations/${organizationId}/trend/events${suffix}`, z.array(maintenanceSchema), accessToken)
  }

  createTrendEvent(accessToken: string, organizationId: string, body: {
    machine_id: string; event_type: string; title: string; started_at: string; ended_at?: string | null;
    notes?: string | null; metadata?: Record<string, string>
  }): Promise<MaintenanceEventResource> {
    return this.request(`/organizations/${organizationId}/trend/events`, maintenanceSchema, accessToken, { method: 'POST', body: JSON.stringify(body) })
  }

  updateTrendEvent(accessToken: string, eventId: string, body: {
    expected_revision: number; event_type?: string; title?: string; started_at?: string; ended_at?: string | null;
    notes?: string | null; metadata?: Record<string, string>; status?: 'ACTIVE' | 'ARCHIVED'
  }): Promise<MaintenanceEventResource> {
    return this.request(`/trend-events/${eventId}`, maintenanceSchema, accessToken, { method: 'PATCH', body: JSON.stringify(body) })
  }

  rebuildTrend(accessToken: string, organizationId: string): Promise<{ organization_id: string; scanned_runs: number; created_points: number; existing_points: number; repaired_context_points: number }> {
    return this.request(`/organizations/${organizationId}/trend/rebuild`, z.object({
      organization_id: z.string().uuid(), scanned_runs: z.number().int(), created_points: z.number().int(),
      existing_points: z.number().int(), repaired_context_points: z.number().int()
    }), accessToken, { method: 'POST' })
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
