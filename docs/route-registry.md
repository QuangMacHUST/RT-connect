# ROUTE REGISTRY DRAFT

All routes are typed in source during P1. This registry is the P0 contract draft; routes without an active Stitch screen are explicit design gaps rather than omitted features.

| Route | Module | Active Stitch source | Main API boundary | Phase |
| :--- | :--- | :--- | :--- | :--- |
| `/auth/login` | MOD-00 | Login `3b857ee77e7a434d8cfdcda32fd62cdb` | Supabase Auth + `/api/v1/session/bootstrap` | P3 |
| `/auth/recovery` | MOD-00 | Recovery `b4fb9071a0614f3a9272d2a8a8b7337c` | Supabase Auth recovery | P3 |
| `/auth/callback` | MOD-00 | Callback `accb55e3ab3e4d718ba3a4407e3f9368` | Supabase Auth callback | P3 |
| `/auth/session-error` | MOD-00 | Session error `3ee1eb026899432392f40ff945649ac9` | Shared auth error contract | P3 |
| `/app` | MOD-01 | Home `70b9f1d256884221ae20e63b5244db11` | `/api/v1/organizations/{id}/dashboard` | P3 |
| `/app/organization` | MOD-02 | Local P4 management screen; Stitch screen still missing | `/api/v1/organizations`, `/api/v1/organizations/{id}/sites`, `/api/v1/organizations/{id}/sites/{siteId}/machines` | P4 |
| `/app/sites/:siteId` | MOD-02 | Embedded in `/app/organization` | `/api/v1/organizations/{id}/sites/{siteId}` | P4 |
| `/app/machines/:machineId` | MOD-02 | Embedded in `/app/organization` | `/api/v1/organizations/{id}/sites/{siteId}/machines/{machineId}` | P4 |
| `/app/qa` | MOD-03 | QA Archive `4c9ec57310fd404cbae3b53b0bab2368`; local P5 implementation | folders tree + QA case CRUD/search | P5 |
| `/app/qa/cases/new` | MOD-03 | Missing | `POST /api/v1/organizations/{id}/qa-cases` | P5 |
| `/app/qa/cases/:caseId` | MOD-03/MOD-04 | Missing | QA case detail/history/artifacts | P5–P6 |
| `/app/qa/cases/:caseId/validation` | MOD-04 | Missing | artifact validation/manifest | P6 |
| `/app/qa/cases/:caseId/machine-qa` | MOD-05 | Local P7 implementation; no dedicated Stitch screen | protocol, measurement, evaluation, history and compare APIs | P7 |
| `/app/qa/cases/:caseId/gamma` | MOD-04/MOD-06 | Gamma `ffb87901b3194bd3aff8760c54c2f9f4` | analysis run APIs | P8 |
| `/app/reports/:reportId` | MOD-07 | Missing viewer | report/revision APIs | P9 |
| `/app/reports/:reportId/edit` | MOD-07 | Builder `a1478466ace843c5aaf9a15dfc58273e` | report template/revision APIs | P9 |
| `/app/trend` | MOD-08 | Missing | `/api/v1/trend` | P10 |
| `/app/qa-protocols` | MOD-09 | Local P11 implementation; dedicated Stitch screen still optional | `/api/v1/organizations/{id}/qa-protocols` | P11 |
| `/app/biological` | MOD-10 | Stitch Biological Hub `b32ef9de691f48449ec23e491a6b634d`; P12 implementation | `/api/v1/organizations/{id}/biological/tools`, `/summary`, `/scenarios`, `/calculations` | P12 |
| `/app/biological/bed-eqd2` | MOD-11 | P13 implementation using Clinical Precision Interface tokens; Stitch generation attempted but service unavailable, so existing design system is used | `/api/v1/organizations/{id}/biological/scenarios/{scenario_id}/calculations/validate`, `/calculations`, `/calculations/{id}/charts`, `/calculations/{id}/export` | P13 |
| `/app/biological/compare` | MOD-12 | Implemented and staging-smoke verified on candidate `31a5900`; final DB/scope/release evidence pending | `/api/v1/organizations/{id}/biological/comparisons` and child validate/detail/chart/clone/export routes | P14 |
| `/app/biological/re-irradiation` | MOD-13 | Implemented with Clinical Precision Interface tokens; dedicated Stitch screen optional | re-irradiation validate/create/list/detail/export API | P15 |
| `/app/biological/fraction-compensation` | MOD-13 | Implemented with shared P15 workspace; dedicated Stitch screen optional | fraction-compensation validate/create/list/detail/export API | P15 |
| `/app/biological/knowledge` | MOD-14 | Local P16 implementation; independent Knowledge Library page | `/api/v1/organizations/{id}/biological/library` validate/list/create/patch/clone/publish/archive/compare/use/import/export | P16 |
| `/app/qa/cases/:caseId/dvh` | MOD-15 | Local P17 Visual Dose / DVH workspace; case-specific route hidden from global sidebar | `/api/v1/organizations/{organization_id}/qa-cases/{case_id}/dvh/inputs`, `/validate`, `/runs`, `/runs/{run_id}`, `/export` | P17 |
| `/app/system/status` | MOD-16 | Optional gap | health/readiness/job summaries | P18–P20 |
