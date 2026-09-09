# RT-CONNECT — Gói vận hành ban đầu P20

- **Trạng thái:** DRAFT / LOCAL_SUPPORT_ONLY
- **Phạm vi:** vận hành staging, pilot và production theo đúng release manifest
- **Nguồn:** `business-analysis.md` v0.22, `specification.md` v1.17,
  `technical-specification.md` v1.15, `plan.md` v4.2
- **Không phải:** bằng chứng đã cấu hình alert thật, provider backup/restore thật,
  RPO/RTO đã đạt hoặc tuyên bố production clinical readiness

Tài liệu này là runbook thao tác ban đầu cho P20. Mọi giá trị dạng `<...>` phải được
điền bằng thông tin của môi trường đang vận hành trước khi bàn giao. Không đưa password,
JWT, service key, database URL đầy đủ, token Railway hoặc dữ liệu bệnh nhân vào tài liệu,
issue, ảnh chụp màn hình hay log hỗ trợ.

## 1. Nguyên tắc vận hành

1. Chỉ thao tác trên đúng `environment`, `service`, `release SHA` và `schema revision`
   đã ghi trong release manifest.
2. `HTTP 200`, huy hiệu `Online` hoặc dashboard màu xanh không tự chứng minh workflow
   nghiệp vụ, worker, database, object storage hay Auth hoạt động.
3. PostgreSQL là nguồn sự thật cho trạng thái run, attempt, result, provenance và audit;
   Redis chỉ dispatch/đo queue; object storage giữ bytes artifact/report.
4. Không sửa trực tiếp result, snapshot, migration history hoặc object bytes để làm mất
   dấu vết. Mọi sửa nghiệp vụ đi qua API và tạo revision/run mới theo contract.
5. Khi chưa biết request đã commit hay chưa, query operation/idempotency/status trước khi
   retry. Không bấm retry vô hạn và không tạo key mới để né một trạng thái chưa rõ.
6. Khi một gate fail, giữ last-good release và evidence; không đổi expected hoặc xóa log
   để biến failure thành PASS.

## 2. Topology và dữ liệu cần theo dõi

| Thành phần | Public/private | Nhiệm vụ | Kiểm tra tối thiểu |
| :--- | :--- | :--- | :--- |
| Frontend web | Public HTTPS | App shell, Auth callback, UI | URL, TLS, build label, API base |
| API | Public HTTPS | Auth verify, scope, CRUD, validation, enqueue/export | health, ready/schema, version, logs redacted |
| Gamma worker | Private | Redis claim, Gamma execution, PostgreSQL commit | process alive, consumer group, queued→terminal |
| Railway PostgreSQL | Private | Business rows, snapshots, audit, migrations | connection, schema revision, backup point |
| Redis | Private | Streams, pending/reclaim, metrics | ping, stream/group, pending count |
| S3-compatible bucket | Private | Artifact/report bytes | bucket private, object count/checksum, signed URL |
| Supabase Auth | External Auth plane | Identity/session/refresh | issuer/audience/JWKS, redirect, expiry |

Mỗi lần kiểm tra phải ghi tối thiểu: `captured_at_utc`, environment, service IDs,
release SHA hoặc build label, schema revision, correlation/request ID, testcase, expected,
observed, người thực hiện và đường dẫn evidence. Không ghi secret hoặc PatientID.

## 3. Bảng chỉ số và ngưỡng cảnh báo ban đầu

Đây là ngưỡng khởi đầu để cấu hình và đo; không được coi là SLO đã đạt trước khi có
workload thực tế. Giá trị cuối cùng phải được chốt cùng cấu hình tài nguyên và evidence.

| Alert | Điều kiện kích hoạt | Mức ban đầu | Hành động đầu tiên | Evidence |
| :--- | :--- | :--- | :--- | :--- |
| API unavailable | health lỗi hoặc timeout liên tiếp | 2 lần / 2 phút | kiểm domain, deployment, logs, dependency | request IDs + response |
| API not ready | `ready != ready` hoặc schema lệch | 1 lần sau deploy, hoặc 2 phút | dừng promote; đối chiếu migration/release | ready/version |
| Error spike | HTTP 5xx tăng liên tục | cần chốt sau baseline | phân nhóm route/correlation, giữ input | metric + sample redacted |
| Worker backlog | pending/queued tăng và không giảm | cần đo theo workload | kiểm worker, Redis group, lease/reclaim | queue metrics |
| Job failure | retry exhausted/dead-letter hoặc execution error | mỗi event | giữ run, đọc error snapshot, retry allowlist | run/attempt ID |
| Storage failure | upload/download/checksum/signed URL lỗi | mỗi event | không tạo VALID giả; kiểm bucket/object | artifact checksum |
| Auth failure | issuer/JWKS/refresh/callback lỗi | theo burst | kiểm URL/config/clock, không mở anonymous | browser/request ID |
| Backup overdue | không có backup point trong retention window | trước hạn | giữ last-good, chạy backup/reconcile | provider backup ID |
| Resource/cost | CPU/RAM/disk/egress vượt budget | cần chốt theo plan | giảm workload có kiểm soát hoặc scale; không mất data | usage snapshot |

Kênh cảnh báo thật chưa được điền trong bản này: `<on-call channel>`, `<email/group>`,
`<Railway alert destination>`. Không đánh dấu `TC-P20-S01` PASS cho đến khi một cảnh báo
synthetic được gửi tới kênh thật và có người nhận được.

## 4. Kiểm tra thường ngày

### 4.1. Readiness và version parity

1. Mở đúng URL của environment.
2. Gọi `GET /api/v1/health`, `GET /api/v1/ready`, `GET /api/v1/version`.
3. Đối chiếu `environment`, `version`, `schema_revision` với manifest.
4. Kiểm tra frontend build label và `VITE_API_BASE_URL` đã trỏ đúng environment.
5. Kiểm tra worker là đúng release và không có public domain.
6. Ghi kết quả vào evidence; nếu lệch version/schema, dừng release hoặc mở incident.

### 4.2. Queue và job

1. Kiểm queue metrics bằng identity đã xác thực; không dùng thông tin do browser tự gửi
   làm nguồn scope.
2. Nếu có `QUEUED` lâu hơn execution policy, kiểm pending count, consumer group, lease,
   retry và dead-letter.
3. Không reset pending hoặc xóa run bằng SQL trực tiếp.
4. Với unknown outcome, query run theo idempotency key trước khi gửi lại.
5. Đảm bảo worker chỉ commit result sau khi kiểm source checksum và fencing/attempt.

### 4.3. Dữ liệu và storage

1. Kiểm object bucket còn private và signed URL vẫn có TTL.
2. Không kiểm file bằng filename đơn lẻ; dùng artifact ID, manifest ID và SHA-256.
3. Nếu manifest/DB/object lệch, dừng engine ở input đó, mở issue và chạy reconciliation
   theo hướng dẫn; không đổi trạng thái thành `VALID` thủ công.
4. Kiểm audit/correlation log không có Authorization header, cookie, password, database
   URL, service key hoặc nội dung nhạy cảm.

## 5. Quy trình backup và restore

### 5.1. Backup point bắt buộc trước release

Trước migration hoặc thay đổi không dễ đảo ngược, lưu các thông tin sau trong release
evidence:

- provider backup/snapshot ID của Railway PostgreSQL;
- thời điểm backup theo UTC và schema revision;
- inventory object storage gồm object key nội bộ, byte size và SHA-256 đã redacted;
- release/source/schema/engine/renderer version;
- người thực hiện và thời gian hết hạn retention;
- xác nhận backup không chứa plaintext secret trong log.

Không xóa backup cũ cho đến khi backup mới đã hoàn tất và có thể truy vấn được.

### 5.2. Isolated restore drill

1. Chọn backup point và xác định database/bucket đích tạm, không dùng production live
   resource làm nơi thử nghiệm.
2. Restore PostgreSQL vào tài nguyên cô lập.
3. Restore/copy object theo inventory, không chỉ restore row metadata.
4. Đối chiếu row counts, canonical row fingerprints, object counts, byte size và SHA-256.
5. Kiểm source references, report download, input manifest và old result vẫn đọc được.
6. Đo `restore_started_at`, `restore_completed_at`, dữ liệu mất tối đa và tính RPO/RTO.
7. Dọn tài nguyên tạm sau khi evidence được ghi; xác nhận cleanup.

Harness local hiện có tại `scripts/verify-local-backup-restore.py` và evidence
`docs/evidence/p18-local-backup-restore-20260909.json`. Đây là support evidence trên
Docker Compose local; nó không thay provider restore, staging RPO/RTO hoặc production
backup drill.

### 5.3. Khi restore không khớp

- Nếu thiếu row/object: đánh `RESTORE_INCOMPLETE`, giữ backup và inventory, không tiếp tục
  promote.
- Nếu checksum khác: giữ object/source snapshot, kiểm storage/version và mở RCA.
- Nếu restore chạy được nhưng report/history sai: không tuyên bố RTO đạt; phục hồi lại
  từ last-good và đóng issue sau regression.
- Không downgrade migration destructive tự động để chữa một release lỗi.

## 6. Incident taxonomy và phản hồi

| Mức | Ví dụ | Phản hồi bắt buộc |
| :--- | :--- | :--- |
| SEV0 | mất dữ liệu, lộ secret/PHI, cross-organization data, result sai hàng loạt | cô lập truy cập/release, giữ evidence, gọi người chịu trách nhiệm, không xóa dấu vết |
| SEV1 | production workflow chính không dùng được, worker mất result, restore fail | giữ last-good, incident owner, rollback/restore theo runbook, cập nhật định kỳ |
| SEV2 | một module hoặc nhóm dataset lỗi nhưng có workaround | mở issue gắn input/hash/version, retry/fix bounded, regression trước close |
| SEV3 | UI copy, layout, warning hoặc hiệu năng nhỏ không chặn dữ liệu | backlog có priority, sửa qua release bình thường |

Mỗi incident record phải có:

```text
incident_id: INC-<date>-<sequence>
started_at_utc:
detected_at_utc:
environment:
release_sha:
schema_revision:
service_ids:
symptom:
scope_of_impact:
correlation_ids:
affected_run_or_artifact_ids:
expected:
observed:
containment:
recovery_action:
data_integrity_check:
root_cause:
regression_test:
owner:
closed_at_utc:
```

Không chép stack trace có secret hoặc dữ liệu bệnh nhân vào incident record.

## 7. Maintenance và release regression

1. Mọi update dependency, engine, renderer, migration, Auth config hoặc public build tạo
   impact set theo module/FR/testcase.
2. Chạy local focused test và full suite trên candidate.
3. Deploy staging cùng release manifest; chạy public smoke và authenticated workflow phù hợp.
4. So sánh golden/reference output, checksum, report render và old-history access.
5. Chỉ promote sau khi failure matrix và rollback point đã có evidence.
6. Ghi release note: thay đổi, migration, config names, engine/renderer version, known
   limitations, rollback condition và người bàn giao.

Maintenance không rewrite history. Result cũ vẫn phải mở được bằng snapshot/version cũ;
result mới dùng operation/run mới, trừ exact idempotent replay.

## 8. Bằng chứng P20 cần thu

| Test | Evidence cần có | Trạng thái hiện tại |
| :--- | :--- | :--- |
| TC-P20-S01 | Alert synthetic đến kênh thật, thời điểm nhận và hành động xử lý | NOT_RUN |
| TC-P20-S02 | Provider backup, isolated restore, counts/checksums và RPO/RTO | LOCAL_SUPPORT_ONLY |
| TC-P20-S03 | Maintenance candidate, regression, old result/history và release note | NOT_RUN |
| TC-P20-S04 | Người vận hành khác thực hiện runbook độc lập và ký handoff | NOT_RUN |
| TC-P20-E01 | Backup failure/retention alert và last-good preservation | NOT_RUN |
| TC-P20-E02 | Alert delivery failure và kênh dự phòng | NOT_RUN |
| TC-P20-E03 | Capacity threshold, usage snapshot và remediation | NOT_RUN |
| TC-P20-E04 | Engine change golden diff, versioned result và rollback | NOT_RUN |
| TC-P20-E05 | Incident lặp lại → RCA + regression + runbook revision | NOT_RUN |

## 9. Điều kiện bàn giao gói ban đầu

P20 chỉ được nâng lên `DONE-v2` khi tất cả điều kiện sau có evidence trên đúng release và
environment:

- dashboard/metrics và alert destination được cấu hình thật;
- ít nhất một alert synthetic đã đến kênh và có người nhận;
- backup retention được chốt, backup point truy vấn được;
- isolated restore đã đối chiếu DB + objects + manifest và đo RPO/RTO;
- production/pilot owner và kênh escalation được điền;
- user guide, incident template, maintenance/release checklist được bàn giao;
- P20 S/E tests, regression và cleanup đều có observed result;
- không còn SEV0/SEV1 hoặc evidence mismatch.

Tài liệu này hiện mới hoàn thành phần runbook/support artifact. Các mục chưa có evidence
thật vẫn phải giữ `NOT_RUN` hoặc `LOCAL_SUPPORT_ONLY` trong `plan.md`.
