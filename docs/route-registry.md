# ROUTE REGISTRY DRAFT

All routes are typed in source during P1. This registry is the P0 contract draft; routes without an active Stitch screen are explicit design gaps rather than omitted features.

| Route | Module | Active Stitch source | Main API boundary | Phase |
| :--- | :--- | :--- | :--- | :--- |
| `/auth/login` | MOD-00 | Login `3b857ee77e7a434d8cfdcda32fd62cdb` | Supabase Auth + `/api/v1/session/bootstrap` | P3 |
| `/auth/recovery` | MOD-00 | Recovery `b4fb9071a0614f3a9272d2a8a8b7337c` | Supabase Auth recovery | P3 |
| `/auth/callback` | MOD-00 | Callback `accb55e3ab3e4d718ba3a4407e3f9368` | Supabase Auth callback | P3 |
| `/auth/session-error` | MOD-00 | Session error `3ee1eb026899432392f40ff945649ac9` | Shared auth error contract | P3 |
| `/app` | MOD-01 | Home `70b9f1d256884221ae20e63b5244db11` | `/api/v1/organizations/{id}/dashboard` | P3 |
| `/app/organization` | MOD-02 | Missing | `/api/v1/organizations` | P4 |
| `/app/sites/:siteId` | MOD-02 | Missing | `/api/v1/organizations/{id}/sites` | P4 |
| `/app/machines/:machineId` | MOD-02 | Missing | `/api/v1/sites/{id}/machines` | P4 |
| `/app/qa` | MOD-03 | QA Archive `4c9ec57310fd404cbae3b53b0bab2368` | folders tree + QA case search | P5 |
| `/app/qa/cases/new` | MOD-03 | Missing | `POST /api/v1/organizations/{id}/qa-cases` | P5 |
| `/app/qa/cases/:caseId` | MOD-03/MOD-04 | Missing | QA case detail/history/artifacts | P5–P6 |
| `/app/qa/cases/:caseId/validation` | MOD-04 | Missing | artifact validation/manifest | P6 |
| `/app/qa/cases/:caseId/machine-qa` | MOD-05 | Missing | machine QA run APIs | P7 |
| `/app/qa/cases/:caseId/gamma` | MOD-04/MOD-06 | Gamma `ffb87901b3194bd3aff8760c54c2f9f4` | analysis run APIs | P8 |
| `/app/reports/:reportId` | MOD-07 | Missing viewer | report/revision APIs | P9 |
| `/app/reports/:reportId/edit` | MOD-07 | Builder `a1478466ace843c5aaf9a15dfc58273e` | report template/revision APIs | P9 |
| `/app/trend` | MOD-08 | Missing | `/api/v1/trend` | P10 |
| `/app/qa-protocols` | MOD-09 | Missing | `/api/v1/qa-protocols` | P11 |
| `/app/biological` | MOD-10 | Missing; regenerate | `/api/v1/biological/scenarios` | P12 |
| `/app/biological/bed-eqd2` | MOD-11 | Missing; regenerate | biological calculation/chart APIs | P13 |
| `/app/biological/compare` | MOD-12 | Missing; regenerate | `/api/v1/biological/comparisons` | P14 |
| `/app/biological/re-irradiation` | MOD-13 | Missing; regenerate | re-irradiation API | P15 |
| `/app/biological/fraction-compensation` | MOD-13 | Missing | fraction-compensation API | P15 |
| `/app/biological/dose-limits` | MOD-14 | Missing | dose-limit APIs | P16 |
| `/app/biological/protocols` | MOD-14 | Missing | treatment-protocol APIs | P16 |
| `/app/biological/knowledge` | MOD-14 | Missing | knowledge APIs | P16 |
| `/app/dose-review/:analysisId` | MOD-15 | Missing | DVH/dose review APIs | P17 |
| `/app/system/status` | MOD-16 | Optional gap | health/readiness/job summaries | P18–P20 |
