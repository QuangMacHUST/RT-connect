# BR → MODULE → SCREEN → ROUTE → API → TEST TRACEABILITY

This P0 matrix defines the minimum traceability spine. Detailed endpoint and test case IDs are extended in each implementation phase without changing the business requirement identity.

| Module | Business rules | Active screen or design gap | Route family | API boundary | Required evidence |
| :--- | :--- | :--- | :--- | :--- | :--- |
| MOD-00 | BR-001, BR-002, BR-026, BR-029, BR-030, BR-031 | Auth screens missing | `/auth/*`, `/app` bootstrap | session/bootstrap, Supabase token verifier, memberships | valid/expired/wrong JWT; membership isolation; login/refresh/deep-link E2E |
| MOD-01 | BR-001, BR-026, BR-031, BR-032 | Home active | `/app` | organization dashboard read model | empty/populated/error; organization scoping; staging visual/E2E |
| MOD-02 | BR-003, BR-004, BR-019 | P4 management screen implemented locally; Stitch source still missing | `/app/organization` (site/machine embedded) | organization/site/machine CRUD, archive lifecycle, audit events | hierarchy, stable machine ID, cross-organization rejection, duplicate policy, audit, staging E2E |
| MOD-03 | BR-005, BR-006, BR-019, BR-020 | P5 QA Archive implemented locally; Stitch UI-02 is the visual source | `/app/qa` | folder tree, folder lifecycle, QA case CRUD/search | nested folder, move/archive/rename, organization isolation, search combinations, history, reload, staging E2E |
| MOD-04 | BR-007, BR-008, BR-009, BR-022, BR-023, BR-031 | Upload/validation gaps; Gamma partial | QA case artifact/validation routes | artifact, manifest and validation APIs | byte integrity, duplicate retry, DICOM/measurement invalid cases, checksum |
| MOD-05 | BR-003, BR-004, BR-021, BR-023, BR-025 | Machine QA screens missing | machine QA route | machine QA run/evaluate APIs | known rules, unit/baseline errors, immutable rerun, trend source |
| MOD-06 | BR-007, BR-008, BR-010, BR-021, BR-022, BR-023, BR-025 | Gamma active | Gamma workspace | analysis run APIs | 2D/3D, global/local, absolute/relative, shift/grid/edge/error golden tests |
| MOD-07 | BR-011, BR-012, BR-013, BR-019, BR-020, BR-031 | Builder active; viewer/history gaps | report routes | template/revision/export APIs | full customization, immutable snapshots, repeatable render, failure isolation |
| MOD-08 | BR-004, BR-019, BR-031 | Trend screen missing | `/app/trend` | trend query/events | unit isolation, machine isolation, outlier preservation, drill-down |
| MOD-09 | BR-011, BR-013, BR-019, BR-020 | Protocol screens missing | `/app/qa-protocols` | protocol/version APIs | clone independence, version immutability, report snapshot preservation |
| MOD-10 | BR-017, BR-024, BR-026, BR-031 | Must regenerate Biological Hub | `/app/biological` | scenario/history APIs | no automatic patient/QA link, organization history scope, deep-link |
| MOD-11 | BR-014, BR-024, BR-025 | Must regenerate BED/EQD2 | BED/EQD2 route | calculation/chart APIs | known-answer formulas, D curves, invalid input, snapshot repeatability |
| MOD-12 | BR-014, BR-016, BR-024, BR-025 | Must regenerate comparison | comparison route | comparison API | two/multi-course known answers, context warning, export snapshot |
| MOD-13 | BR-015, BR-016, BR-017, BR-018, BR-024, BR-025 | Must regenerate Re-irradiation and compensation | re-irradiation/compensation routes | scenario calculation APIs | recovery/no-recovery, interval/source errors, scalar/spatial guard, alternatives |
| MOD-14 | BR-014, BR-017, BR-024 | Knowledge screens missing | biological library routes | dose-limit/protocol/knowledge APIs | version/source/citation, search/filter, user override label, no auto prescription |
| MOD-15 | BR-009, BR-022, BR-023, BR-025 | Visual Dose/DVH screen missing | dose review route | DVH/dose APIs | known geometry, spacing/orientation, outside-grid, Frame mismatch, provenance |
| MOD-16 | BR-001, BR-019, BR-020, BR-026, BR-029–BR-033 | Operational screens as needed | status/diagnostic routes | audit/health/backup manifests | remote E2E, backup/restore, rollback, exposure scan, monitoring/cost evidence |
