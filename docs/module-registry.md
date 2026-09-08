# MODULE REGISTRY

| Module | Name | Frontend boundary | Backend/domain boundary | Engine/worker | Primary phase |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MOD-00 | Identity and organization context | Auth routes, session bootstrap, organization selector | Token verifier, UserIdentity, OrganizationMembership | None | P2–P3 |
| MOD-01 | Home Dashboard | Dashboard widgets and quick actions | Dashboard read model | Job status aggregation only | P3 |
| MOD-02 | Organization, Site and Machine | Management pages and forms | Organization/Site/Machine services | None | P4 |
| MOD-03 | QA Archive, Folder and QA Case | Folder tree, search, case list/detail | Folder/QACase/search services | None | P5 |
| MOD-04 | Artifact, Upload and Validation | Upload, manifest, validation views | Artifact/ValidationRun/InputManifest | Ingestion/validation job | P6 |
| MOD-05 | Machine QA | Checklist, editor, result/history | Protocol application and rule evaluation | Analysis contract | P7 |
| MOD-06 | PSQA Gamma | Gamma workspace and run comparison | AnalysisRun/GammaConfiguration | Gamma worker | P8 |
| MOD-07 | Report Builder | Builder, viewer, revisions, export | Report snapshots/templates/revisions | Renderer/export worker | P9 |
| MOD-08 | Trend | Filters, charts and drill-down | TrendPoint/read model | Projection/rebuild when needed | P10 |
| MOD-09 | QA Protocol Library | Library, rule editor, version comparison | Versioned protocol repositories | None | P11 |
| MOD-10 | Biological Hub | Hub/history/report entry | BiologicalScenario/read model | None | P12 |
| MOD-11 | BED/EQD2 | Calculator, curves and history | BiologicalCalculationRun | Biological engine | P13 |
| MOD-12 | Plan Comparison | Multi-course editor and charts | Comparison service | Biological engine | P14 |
| MOD-13 | Re-irradiation | Course/scenario/recovery UI | Re-irradiation scenario service | Biological engine; spatial worker only with valid contract | P15 |
| MOD-14 | Biological Knowledge | Dose-limit/protocol/knowledge pages | Versioned knowledge repositories | Import/index when needed | P16 |
| MOD-15 | Visual Dose and DVH | Dose viewer/DVH workspace | DICOM linkage and physical-dose DVH contracts | Synchronous DVH engine now; async/large-workload worker is P17-W06 | P17 |
| MOD-16 | Audit and Operations | Status/history/diagnostics as needed | AuditEvent, health and backup manifest | Monitoring/maintenance jobs | P18–P20 |

## Naming conventions

### Metric keys

- Stable lowercase namespace with dot-separated segments and snake_case leaves.
- Examples: `gamma.pass_rate_pct`, `gamma.mean_index`, `machine_qa.output.deviation_pct`, `dvh.ptv.d95_gy`, `biological.bed_gy`, `biological.eqd2_gy`.
- Unit is stored separately; the key does not change when the display label is customized.
- Display labels are snapshots and may be renamed in reports without changing metric identity.

### Error codes

- Stable `UPPER_SNAKE_CASE` identifiers returned in the shared API error contract.
- Validation errors describe the missing/invalid contract, not a guessed correction.
- Initial registry (legacy names remain for compatibility): `ORGANIZATION_NOT_FOUND`, `MEMBERSHIP_REQUIRED`, `MACHINE_NOT_FOUND`, `FOLDER_NOT_FOUND`, `ARTIFACT_NOT_FOUND`, `UNSUPPORTED_MODALITY`, `INVALID_DICOM`, `GEOMETRY_MISMATCH`, `UNIT_MISSING`, `RTDOSE_REQUIRED`, `COMPARE_DATASET_REQUIRED`, `MEASUREMENT_REQUIRED`, `DVH_INPUT_REQUIRED`, `GAMMA_CONFIG_INVALID`, `BIOLOGICAL_INPUT_INVALID`, `CALCULATION_FAILED`, `REPORT_RENDER_FAILED`, `EXPORT_FAILED`.
- P17 concrete codes: `DVH_INPUT_MANIFEST_REQUIRED`, `DVH_INPUT_NOT_VALIDATED`, `DVH_INPUT_MANIFEST_INVALID`, `DVH_INPUT_SCOPE_MISMATCH`, `DVH_INPUTS_MUST_DIFFER`, `DVH_DOSE_ARTIFACT_INVALID`, `DVH_STRUCTURE_ARTIFACT_INVALID`, `DVH_ANATOMY_ARTIFACT_INVALID`, `DICOM_GEOMETRY_INVALID`, `DICOM_CAPABILITY_UNSUPPORTED`, `DICOM_FRAME_MISMATCH`, `DVH_DOSE_UNITS_UNSUPPORTED`, `DVH_DOSE_VALUES_INVALID`, `DVH_ROI_INVALID`, `CONTOUR_GEOMETRY_INVALID`, `DVH_EMPTY_STRUCTURE`, `DVH_INCOMPLETE_COVERAGE`, `DVH_PARTIAL_COVERAGE`, `DVH_COVERAGE_POLICY_INVALID`, `DVH_METRIC_INVALID`, `DVH_RESOURCE_LIMIT`, `DVH_SOURCE_CHANGED`, `DVH_IDEMPOTENCY_CONFLICT`, `DVH_STORAGE_UNAVAILABLE`, `DVH_EXECUTION_FAILED`, `DVH_PERSISTENCE_FAILED`, `DVH_RUN_NOT_FOUND`. `DVH_DOSE_ONLY_MODE` is a warning, not an error.

### Event types

- Stable uppercase event family and action: `FOLDER_CREATED`, `ARTIFACT_UPLOADED`, `VALIDATION_COMPLETED`, `ANALYSIS_SUCCEEDED`, `REPORT_REVISION_CREATED`, `BIOLOGICAL_CALCULATION_COMPLETED`.
- Events remain append-only and include request/correlation ID, actor and organization context.
