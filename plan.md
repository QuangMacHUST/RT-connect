# KẾ HOẠCH TRIỂN KHAI THEO MODULE

## Dự án RT-CONNECT

- **Tên file:** plan.md
- **Phiên bản:** 1.5
- **Nguồn nghiệp vụ:** business-analysis.md phiên bản 0.6
- **Nguồn kỹ thuật:** technical-specification.md phiên bản 0.8
- **Nguồn thiết kế:** Google Stitch MCP, project RT-connect, project ID 14242591911141046021
- **Hạ tầng mục tiêu:** Supabase Auth; Railway backend và PostgreSQL; object storage bền vững; frontend web truy cập từ xa
- **Mục tiêu:** hoàn thiện từng module thành một vertical slice có thể chạy, kiểm thử, bàn giao và triển khai trên staging trước khi chuyển sang module tiếp theo

Tài liệu này thay thế lộ trình cũ phụ thuộc UI-UX.md. UI-UX.md và DESIGN.md không được tái tạo. Google Stitch là nguồn thiết kế trực quan được đọc hoặc cập nhật qua MCP; business-analysis.md vẫn là nguồn yêu cầu và technical-specification.md vẫn là nguồn hợp đồng kỹ thuật.

---

## 0. Baseline đã kiểm tra

### 0.1. Repository

- Repository hiện đã có backend API trong `apps/api`, frontend web trong `apps/web`, migration Alembic, Dockerfile, test suite và CI.
- `apps/api/railway.toml` chỉ là file tham khảo/legacy; Railway Service Settings và deployment metadata mới là nguồn cấu hình vận hành thật.
- `.env` có thể chứa biến local cho Google Stitch, Supabase và Railway; không ghi giá trị token, password hoặc private URL vào tài liệu hay Git.
- .env đã được Git ignore và không bị Git theo dõi.
- Các file UI-UX.md, DESIGN.md và Biological-toolkit.html đã được user xóa; giữ nguyên trạng thái xóa.

### 0.2. Google Stitch

Project thiết kế hiện tại:

| Thuộc tính | Giá trị |
| :--- | :--- |
| Title | RT-connect |
| Project ID | 14242591911141046021 |
| Visibility | PUBLIC |
| Device baseline | DESKTOP |
| Screen resource đang hoạt động từ `list_screens` | 6 |
| Application screen đang hoạt động | 4 |
| Image asset không phải route | 2 (logo, avatar) |
| Biological legacy instance | 4 instance hidden/deprecated, không dùng làm nguồn thiết kế |

Bốn application screen đang hoạt động:

| UI | Screen | Screen ID | Module |
| :--- | :--- | :--- | :--- |
| UI-01 | Trang chủ - Home Dashboard | 70b9f1d256884221ae20e63b5244db11 | MOD-01 |
| UI-02 | Kho lưu trữ QA & Thư mục | 4c9ec57310fd404cbae3b53b0bab2368 | MOD-03 |
| UI-03 | Phân tích PSQA Gamma Workspace | ffb87901b3194bd3aff8760c54c2f9f4 | MOD-04, MOD-06 |
| UI-04 | Trình biên soạn Báo cáo - Report Builder Studio | a1478466ace843c5aaf9a15dfc58273e | MOD-07 |

Bốn Biological screen cũ đã bị user loại khỏi canvas hoạt động vì lệch phong cách. `get_project` còn trả chúng dưới dạng instance `hidden`, nhưng chúng là legacy/deprecated: không tự khôi phục, không dùng Screen ID cũ trong route mapping và không coi là screen hiện có. P12–P15 phải tạo lại từng screen trong đúng project, dùng Design System `Clinical Precision Interface` và bốn screen đang hoạt động làm chuẩn.

Logo và avatar không phải application route. Vì project Stitch đang public, tất cả prompt, image và screen chỉ dùng dữ liệu synthetic.

### 0.3. Railway

 Project `prolific-learning` (ID `339f2c50-ddd7-491f-8c4e-da2a2d169502`) hiện có:

| Environment | Service API | PostgreSQL | API source | API region | Deployment đã kiểm tra |
| :--- | :--- | :--- | :--- | :--- | :--- |
| staging | `gleaming-cooperation` (`9b35bf0b-0419-4679-8af0-e639e5a84713`) | `Postgres-Q1Hc` (`8fc8201e-417d-4fd7-9a6d-17ad51b72dcf`) | `codex/p2-runtime-resilience` | `us-west2` | `SUCCESS`, commit `9bf96e9`, deployment `2b5270d1-9704-49b3-b3d8-0f8be130d02e` |
| production | `RT-connect` (`9544c3e6-c8bd-4c29-b62e-c6172eb51af3`) | `Postgres` (`5709f18d-c92d-461a-9f73-478dd7748d80`) | `main` | `us-west2` | `SUCCESS`, commit `c52b614`, deployment `ec813793-4e29-4edb-b5d7-f323264da403` |

Environment IDs: production `910dff25-75b6-42b2-bf6b-e2601ba9d7d2`; staging `b0ab34e5-0ff4-479d-8232-659d175e9e2f`. PostgreSQL production và staging hiện vẫn đang chạy bằng volume riêng. Redis/worker/renderer chưa được provision trước phase cần chúng. Ngân sách/credit khởi điểm do user cung cấp là 5 USD; phải theo dõi usage thực tế.

Ngày 2026-09-06 đã xử lý incident deployment: Railway từ chối deployment production vì `multiRegionConfig` dùng alias cũ `sfo`. Hai API service đã được chuyển sang region identifier hợp lệ `us-west2`; sau đó staging và production đều deploy `SUCCESS`. PostgreSQL chưa đổi region để tránh di chuyển volume dữ liệu khi chưa có bằng chứng backup/restore tương ứng.

### 0.3.1. Railway deployment contract — nguồn sự thật duy nhất

Để tránh nhầm giữa repository, Railway dashboard và Config-as-code, mọi deployment phải tuân theo hợp đồng sau:

| Hạng mục | Staging | Production | Quy tắc |
| :--- | :--- | :--- | :--- |
| Railway environment | `staging` | `production` | Không dùng nhầm biến hoặc database giữa hai environment |
| API service | `gleaming-cooperation` | `RT-connect` | Mỗi service có source branch và biến riêng |
| Source branch | `codex/p2-runtime-resilience` trong giai đoạn P2 | `main` sau khi promote release | Staging pass trước rồi mới promote đúng commit/release manifest |
| API deployment region | `us-west2` | `us-west2` | Dùng region identifier đầy đủ; không dùng alias cũ `sfo` |
| Repository root | `/apps/api` | `/apps/api` | Đây là Root Directory của service, không phải path file cấu hình |
| Dockerfile | `/apps/api/Dockerfile` | `/apps/api/Dockerfile` | Dockerfile phải lắng nghe biến `PORT`; không hardcode chỉ một cổng Railway |
| Railway `PORT` | `8000` | `8000` | Phải khớp với Target port của public domain và cổng process bind; khai báo riêng trong từng environment |
| Start command | Từ Dockerfile | Từ Dockerfile | `uvicorn` dùng `${PORT:-8000}`; `8000` chỉ là fallback local |
| `DATABASE_URL` | Reference tới PostgreSQL staging | Reference tới PostgreSQL production | Không copy password hoặc URL giữa environment |
| Pre-deploy command | Service Settings: `alembic upgrade head` | Service Settings: `alembic upgrade head` | Kiểm tra command trong Deployment Details và log migration |
| Healthcheck path | Service Settings: `/api/v1/health` sau khi `$PORT` được sửa | Service Settings: `/api/v1/health` sau khi `$PORT` được sửa | Không dùng `/api/v1/ready` làm healthcheck deployment |
| Readiness smoke test | `GET /api/v1/ready` phải trả HTTP 200 | `GET /api/v1/ready` phải trả HTTP 200 | Đây là kiểm tra database/migration sau deployment, không phải Railway healthcheck |

#### Quy tắc Config-as-code

- Service Settings trên Railway là nguồn cấu hình vận hành hiện tại của RT-CONNECT.
- Không coi ô `Config-as-code path` là bắt buộc đối với hai service hiện tại. Railway đã đánh dấu Config-as-code cũ/deprecated và service mới có thể không giữ path sau deployment.
- File `apps/api/railway.toml` được giữ trong repository như cấu hình tham khảo/legacy; không được coi là bằng chứng rằng Railway đã áp dụng cấu hình đó.
- Bằng chứng cấu hình thật phải đọc từ Deployment Details/metadata của deployment: `rootDirectory`, `dockerfilePath`, `preDeployCommand`, `healthcheckPath`, source branch và commit.
- Nếu `railwayConfigFile = null` nhưng `preDeployCommand` đã xuất hiện trong metadata, đó là cấu hình trực tiếp từ Service Settings, không phải Config-as-code.
- Không chuyển `preDeployCommand` hoặc `healthcheckPath` vào file rồi giả định dashboard sẽ tự cập nhật; phải kiểm tra deployment thực tế.
- Không dùng `apps/api/railway.toml` để sửa region vận hành một cách ngầm định. Nếu đổi region, cập nhật bằng Railway Service Settings/API, ghi region identifier và deployment evidence vào phần snapshot của tài liệu này.

#### Quy tắc cổng và healthcheck

- API phải bind `0.0.0.0:${PORT}`; Dockerfile được phép dùng `PORT=8000` làm giá trị mặc định khi chạy local.
- Khi public domain của Railway dùng Target port `8000`, cả staging và production phải có service variable `PORT=8000`. Không để staging hoặc production dùng `PORT=3000` hay một giá trị khác; `PORT`, Target port và cổng process bind phải cùng một giá trị.
- `EXPOSE 8000` chỉ là metadata/fallback, không phải cổng Railway bắt buộc.
- Healthcheck `/api/v1/health` không truy cập database và phải trả HTTP 200 sau khi process listen đúng `$PORT`.
- `/api/v1/ready` kiểm tra PostgreSQL và Alembic migration; dùng cho smoke/readiness test, không dùng làm healthcheck lúc container mới khởi động.
- Nếu Railway báo `service unavailable`, kiểm tra theo thứ tự: `PORT`, bind address, target port, start command, log process, rồi mới kiểm tra path.
- Không bỏ healthcheck production chỉ vì một deployment healthcheck thất bại; phải ghi nguyên nhân và quyết định trong release evidence. Staging có thể tạm tắt để chẩn đoán, nhưng production phải bật lại trước release clinical.

#### Quy tắc `DATABASE_URL` và PostgreSQL driver

- Railway PostgreSQL có thể cung cấp private URL với hai tiền tố hợp lệ: `postgresql://...` hoặc `postgresql+psycopg://...`. Cả hai đều được backend chấp nhận.
- Backend chuẩn hoá riêng tiền tố `postgresql://` thành `postgresql+psycopg://` trước khi tạo SQLAlchemy engine. Vì vậy staging không còn vô tình phụ thuộc vào driver PostgreSQL mặc định/legacy, còn production dùng sẵn `postgresql+psycopg://` vẫn giữ nguyên.
- Không sửa hostname, port, tên database, user hoặc password bằng code. Mỗi environment phải dùng reference/private URL do **PostgreSQL service cùng environment** cung cấp.
- Không lưu giá trị URL hoặc password trong Git, `plan.md`, log CI hay browser. Chỉ ghi service nguồn và trạng thái kiểm tra `GET /api/v1/ready`.
- Sau mọi thay đổi database variable: redeploy service, xác nhận deployment healthcheck `/api/v1/health` pass, rồi kiểm tra riêng `/api/v1/ready` HTTP 200. Nếu readiness fail, xem log migration/connection; không bỏ healthcheck để che lỗi.

#### Quy tắc Railway region và PostgreSQL volume

- API staging và production hiện dùng `us-west2` — đây là region identifier hợp lệ tương ứng khu vực US West hiện tại.
- Không dùng `sfo` trong `multiRegionConfig`; `sfo` là alias cũ đã từng khiến production deployment bị chặn.
- PostgreSQL staging/production vẫn giữ region key cũ trong deployment metadata trong lúc volume đang hoạt động. Không tự ý đổi PostgreSQL region chỉ để làm đồng nhất với API; trước tiên phải có backup, restore test hoặc kế hoạch di chuyển volume được ghi nhận.
- Mọi thay đổi region phải được kiểm tra theo thứ tự: service vẫn `Online`, deployment status `SUCCESS`, `/api/v1/health` HTTP 200, `/api/v1/ready` HTTP 200, rồi mới ghi nhận là đã hoàn tất.

### 0.4. Supabase

- Đã chọn Supabase làm Auth/Identity/Session.
- Chưa có biến Supabase trong .env tại baseline này.
- Supabase không lưu database nghiệp vụ RT-CONNECT.
- Cần tạo hoặc chọn Supabase project cho development/staging trước MOD-00.

---

## 1. Mô hình release

| Release | Phạm vi | Phase |
| :--- | :--- | :--- |
| R0 — Development Foundation | Repository, CI, staging Railway, PostgreSQL, Supabase Auth, app shell | P0–P3 |
| R1 — Clinical MVP | Organization, archive, artifact validation, Machine QA, Gamma, report, trend, QA protocol | P4–P11 |
| R2 — Biological Toolkit | Biological Hub, BED/EQD2, comparison, re-irradiation, dose-limit/knowledge | P12–P16 |
| R3 — Advanced DICOM | Visual Dose, DVH/Plan Review và structure-level view | P17 |
| R4 — Production Web | Hardening, pilot, production deploy, remote access và vận hành | P18–P20 |

P17 không chặn R1 hoặc R2. Có thể phát hành Clinical MVP và Biological Toolkit trước Visual Dose/DVH nếu các release gate tương ứng đạt.

---

## 2. Definition of Done cho mọi module

Một module chỉ hoàn thành khi đạt tất cả điều kiện áp dụng:

1. Requirement và acceptance criteria được map tới MOD/BR.
2. Screen Stitch hiện có được đọc bằng MCP hoặc screen thiếu đã được bổ sung trong đúng project.
3. Có route, navigation và organization context.
4. Có schema/migration nếu module lưu dữ liệu.
5. Có API contract typed và error contract.
6. Có frontend nối API thật; mock chỉ tồn tại trong fixture/story/test.
7. Có loading, empty, success, warning/invalid và error/retry state.
8. Tác vụ bất đồng bộ có queued/running/succeeded/failed/retry và idempotency.
9. Có provenance/version/revision nếu module tạo kết quả.
10. Có unit/contract/integration/E2E test phù hợp.
11. Có log và correlation ID; không lộ secret hoặc dữ liệu nhạy cảm.
12. Chạy được trên Railway staging qua HTTPS.
13. Refresh hoặc mất kết nối tạm thời không tạo record/job/result trùng.
14. CI pass và migration được kiểm tra.
15. Tài liệu kỹ thuật, OpenAPI và release note được cập nhật.

Ảnh Stitch đẹp, component tĩnh, API riêng lẻ, test unit riêng lẻ hoặc một deployment thành công đều chưa đủ để đóng module.

### 3.1. Deployment gate bổ sung cho mọi release có Railway

1. CI pass trên đúng source branch của environment.
2. Deployment Details khớp Root Directory, Dockerfile, source branch và commit dự kiến.
3. Pre-deploy command `alembic upgrade head` xuất hiện trong metadata/log của deployment.
4. Healthcheck `/api/v1/health` chỉ được bật sau khi process đã bind `$PORT`; nếu bật thì deployment phải pass HTTP 200.
5. `/api/v1/ready` trả HTTP 200 từ mạng ngoài và xác nhận migration đã áp dụng.
6. Chỉ sau khi staging đạt các bước trên mới promote cùng release manifest sang production.
7. Production phải được kiểm tra lại `/api/v1/health` và `/api/v1/ready`; không suy luận production an toàn chỉ từ staging.

---

## 3. Dependency roadmap

~~~text
P0  Baseline + traceability
 |
P1  Repository + local runtime + CI
 |
P2  Railway staging + PostgreSQL + Supabase Auth foundation
 |
P3  App shell + Auth + Home Dashboard
 |
P4  Organization / Site / Machine
 |
P5  QA Archive / Folder / QA Case
 |
P6  Artifact / Upload / DICOM Validation
 |
P7  Machine QA
 |
P8  PSQA Gamma
 |
P9  Report Builder
 |
P10 Trend
 |
P11 QA Protocol Library
 |
+-------------------------------+
|                               |
P12 Biological Hub              P17 Visual Dose / DVH (optional track)
 |
P13 BED & EQD2
 |
P14 Plan Comparison
 |
P15 Re-irradiation + Fraction Compensation
 |
P16 Dose Limit + Treatment Protocol + Knowledge
 |
+-------------------------------+
 |
P18 Integration + Hardening + Pilot
 |
P19 Production Web + Remote Access
 |
P20 Operations + Continuous Improvement
~~~

Thời lượng là ước lượng tham chiếu cho một nhóm nhỏ. Phase có thể chạy song song chỉ khi dependency dữ liệu/API đã ổn định và không làm mất Definition of Done.

---

# PHASE 0 — Baseline, kết nối và traceability

**Thời lượng:** 3–5 ngày
**Phụ thuộc:** Không
**Mục tiêu:** khóa nguồn yêu cầu, nguồn thiết kế và đúng project hạ tầng trước khi code.

## Công việc

- Khóa business-analysis.md 0.4, technical-specification.md 0.6 và plan.md 1.0.
- Lập BR → MOD → screen → route → API → test matrix.
- Xác nhận bốn application screen đang hoạt động bằng project/screen ID.
- Phân loại logo/avatar và các instance hidden/deprecated để không biến thành route.
- Xác nhận Railway project, environment, service và trạng thái deployment.
- Ghi rõ deployment gần nhất đang FAILED; tạo issue điều tra, chưa redeploy production.
- Xác nhận .env chỉ dùng local và bị Git ignore.
- Tạo danh sách secret cần có theo environment nhưng không ghi giá trị.
- Chốt module code MOD-00 đến MOD-16 và metric/error naming convention.

## Deliverables

- Baseline snapshot.
- Traceability matrix.
- Module registry.
- Route registry draft.
- Environment/secret name inventory.
- Issue cho Railway failed deployment.

## Exit criteria

- Không còn nhầm technical.md với technical-specification.md.
- Không còn phụ thuộc UI-UX.md.
- Mọi screen hiện có có module owner.
- Mọi module chưa có screen được đánh dấu design gap.
- Project Railway và Stitch được xác nhận bằng ID, không chỉ bằng tên.

---

# PHASE 1 — Repository, local runtime và CI

**Thời lượng:** 1–2 tuần
**Phụ thuộc:** P0
**Mục tiêu:** có source tree và test pipeline chạy lặp lại được.

## Backend

- Tạo Python/FastAPI/Pydantic project.
- Tạo configuration layer theo environment.
- Tạo health, readiness và version endpoint.
- Tạo error contract và request/correlation ID middleware.
- Tạo structured logging và log redaction.
- Tạo SQLAlchemy session, Alembic baseline và repository pattern.
- Tạo object storage, queue, auth và engine interfaces.
- Tạo pytest, type check, lint và coverage baseline.

## Frontend

- Tạo React + TypeScript + Vite.
- Tạo typed route registry và API client.
- Tạo query/cache layer và form validation.
- Tạo test runner, component test và E2E harness.
- Tạo AppShell placeholder; chưa sao chép nguyên HTML Stitch vào production.

## Local infrastructure

- Docker Compose cho web, API, PostgreSQL, Redis-compatible queue và object storage development.
- Seed synthetic organization/site/machine.
- Env example chỉ có tên biến giả.
- Script migration, seed, test và local startup.

## CI

- Format/lint/type check.
- Backend unit/contract test.
- Frontend unit/component test.
- Migration up/down or forward-check.
- Frontend production build.
- OpenAPI generation/diff.
- Secret scan và dependency inventory.

## Deliverables

- Source tree.
- Local stack.
- CI pipeline.
- Health/version endpoints.
- Migration baseline.
- Setup README.

## Exit criteria

- Một máy mới có thể chạy local theo README.
- API, database và frontend health đều pass.
- Repository sạch không chứa token/credential.
- CI pass trên commit sạch.

---

# PHASE 2 — Railway staging, PostgreSQL và Supabase Auth foundation

**Module:** MOD-00 hạ tầng
**Thời lượng:** 1–2 tuần
**Phụ thuộc:** P1
**Mục tiêu:** có staging URL thật, database thật và auth project tách khỏi production.

## Railway

- Cài hoặc pin Railway CLI; không log token.
- Dùng token phù hợp để link project prolific-learning.
- Tạo environment staging; production token không được dùng thay cho staging credential.
- Điều tra log của deployment FAILED hiện có và ghi nguyên nhân.
- Quyết định giữ service RT-connect làm api-web ban đầu hoặc đổi tên có migration rõ.
- Tạo Railway PostgreSQL cho staging.
- Cấu hình private reference variable cho DATABASE_URL.
- Deploy health-only/API shell lên staging.
- Cấu hình trực tiếp trong Service Settings: pre-deploy `alembic upgrade head`, restart policy và structured logs.
- Sau khi Dockerfile bind `$PORT`, cấu hình trực tiếp healthcheck `/api/v1/health`; nếu healthcheck fail thì kiểm tra cổng và process trước, không chữa theo cảm tính bằng Config-as-code path.
- Chưa tạo worker/Redis/renderer production trước khi phase cần.

## Supabase

- Tạo/chọn Supabase Auth project development/staging.
- Cấu hình site URL, redirect URL và provider.
- Lấy public/publishable configuration cho frontend.
- Cấu hình JWT issuer, audience và JWKS/introspection cho backend.
- Không dùng Supabase database cho entity nghiệp vụ.

## Security và cost gate

- Account/Project token chỉ dùng cho deployment tooling.
- Backend runtime không cần Railway account/project token.
- Không đưa Supabase service-role key vào frontend.
- Kiểm tra Railway usage/cost trước và sau khi tạo PostgreSQL.
- Ghi baseline 5 USD do user cung cấp và xác định service nào tiêu thụ usage; không hứa toàn bộ topology nằm trong ngân sách nếu chưa đo.
- Ghi resource limit, timeout và retention hiện tại.

## Tests

- Railway API health từ mạng ngoài.
- Railway deployment healthcheck pass trên cổng `$PORT`.
- Backend kết nối PostgreSQL qua private/reference variable.
- Alembic migration trên database rỗng.
- Supabase sign-in test account và JWT verification.
- Token sai/hết hạn/sai issuer bị từ chối.
- Secret không xuất hiện trong bundle/log.

## Deliverables

- Staging environment.
- Railway PostgreSQL staging.
- Supabase Auth staging config.
- Deployment manifest đầu tiên.
- Failed-deployment root-cause note.
- Cost/usage snapshot.

## Exit criteria

- Staging health qua HTTPS pass.
- Deployment metadata xác nhận pre-deploy migration và source commit đúng environment.
- Migration baseline pass trên Railway PostgreSQL.
- Supabase access token được API xác minh.
- Production chưa bị thay đổi ngoài thao tác read-only cần thiết.

---

# PHASE 3 — App Shell, Authentication và Home Dashboard

**Module:** MOD-00, MOD-01
**Thời lượng:** 1–2 tuần
**Phụ thuộc:** P2
**Stitch:** UI-01 `70b9f1d256884221ae20e63b5244db11`; Login `3b857ee77e7a434d8cfdcda32fd62cdb`; Recovery `b4fb9071a0614f3a9272d2a8a8b7337c`; Callback `accb55e3ab3e4d718ba3a4407e3f9368`; Session Error `3ee1eb026899432392f40ff945649ac9`
**Mục tiêu:** user đăng nhập và vào được Home Dashboard của đúng organization.

## Stitch/design

- Đọc UI-01 bằng get_screen.
- Tạo screen Login, Password Recovery, Auth Callback và Session Error trong cùng Stitch project.
- Chốt AppShell, sidebar, header, organization selector và responsive behavior.
- Trích design tokens thành source.

## Backend/data

- Tạo UserIdentity và OrganizationMembership.
- Tạo session bootstrap endpoint.
- Tạo dashboard read model: machine count, QA gần đây, warning, job và quick action.
- Seed organization và membership synthetic trong test fixture; không phụ thuộc seed giả để mở staging.
- Cho phép identity đã xác thực nhưng chưa có membership tạo organization đầu tiên qua `POST /organizations`; identity đó được gắn membership đầu tiên.

## Frontend

- Tích hợp Supabase sign-in, refresh, logout và recovery.
- Protected route.
- Organization context.
- Home Dashboard nối API thật.
- Loading/empty/error/offline/session-expired state.
- Session Error có luồng khởi tạo organization cho identity chưa có membership.

## Tests

- Login/logout/refresh.
- Deep-link sau login.
- Membership không hợp lệ.
- Identity chưa có membership có thể tạo organization đầu tiên và mở lại workspace.
- Organization context không bị giả mạo từ client.
- Dashboard empty và populated state.
- Accessibility keyboard/focus/label.

## Deliverables

- Auth screens trên Stitch.
- AppShell component library.
- Home Dashboard.
- Session/bootstrap API.
- First-use organization onboarding trên Session Error.

## Exit criteria

- User test đăng nhập từ staging URL.
- Chỉ thấy organization mình thuộc.
- Refresh browser giữ hoặc phục hồi session đúng.
- UI không chứa mock data trong production path.
- Identity đã xác thực nhưng chưa có membership không bị kẹt ở màn hình lỗi; có thể hoàn tất organization context bằng workflow được kiểm tra.

---

# PHASE 4 — Organization, Site và Machine

**Module:** MOD-02
**Thời lượng:** 1–2 tuần
**Phụ thuộc:** P3
**Stitch:** Chưa có screen riêng
**Mục tiêu:** hoàn thiện hierarchy organization → site → machine.

## Stitch/design

- Tạo Organization/Site/Machine management screens.
- Thiết kế create/edit/detail/search/empty/error states.
- Dùng cùng AppShell và DataTable đã có.

## Backend/data

- Migration Organization, Site, Machine.
- Stable machine ID, display name, code, manufacturer/model và status.
- Organization isolation cho mọi query/mutation.
- Audit event create/update/archive.
- First organization onboarding tạo organization và membership đầu tiên trong một transaction nghiệp vụ.

## API/frontend

- CRUD organization/site/machine.
- Search/filter/pagination.
- Machine detail và lifecycle note.
- Rename machine không tạo machine mới.

## Tests

- Hierarchy constraints.
- Cross-organization access.
- Rename giữ stable ID.
- Duplicate code policy.
- Audit event.

## Exit criteria

- Workflow create organization → site → machine chạy trên staging.
- Machine rename không làm thay identity.
- Screen-to-API traceability hoàn chỉnh.

---

# PHASE 5 — QA Archive, Folder và QA Case

**Module:** MOD-03
**Thời lượng:** 2–3 tuần
**Phụ thuộc:** P4
**Stitch:** UI-02 có sẵn
**Mục tiêu:** kho QA hoạt động giống folder máy tính nhưng vẫn có metadata/search.

## Stitch/design

- Đọc UI-02.
- Bổ sung modal create/rename/move/archive folder.
- Bổ sung QA Case create/detail shell, search, filter, pagination và empty/error state.

## Backend/data

- Folder parent-child/materialized path.
- QACase, primary_folder, qa_type, qa_cycle, performed_at.
- Index organization/site/machine/folder/time/type.
- Archive không hard delete.
- Move/rename không đổi QACase ID.

## API/frontend

- Folder tree CRUD.
- QA case CRUD.
- Search theo site, machine, cycle, type, protocol, time và data status.
- Breadcrumb và deep-link.

## Implementation contract

- `include_archived=false` chỉ trả folder/QA case đang active; `include_archived=true` trả cả active và archived để phục vụ history.
- Archive folder là soft-archive và cascade trạng thái archive xuống subtree; không hard-delete folder hoặc QA case. QA case giữ nguyên ID và vẫn truy xuất được qua history.
- Một tên folder active chỉ được dùng một lần trong cùng parent folder của organization; folder có thể di chuyển về root bằng `parent_folder_id=null`.
- QA case phải tham chiếu site active, machine active thuộc đúng site và folder active thuộc cùng organization tại thời điểm tạo hoặc di chuyển.
- Mọi endpoint nhận resource ID phải resolve organization context từ verified identity trước khi đọc resource; không dùng lookup toàn cục rồi mới kiểm tra membership.
- Không tạo action-level role hierarchy giữa bác sĩ/kỹ sư; audit ghi nhận actor và thay đổi nhưng không thay đổi mô hình quyền ngang hàng trong cùng organization.

## Tests

- Folder nhiều cấp.
- Move subtree.
- Rename/archive không mất case.
- Search combinations.
- Organization isolation.
- Audit history.

## Exit criteria

- User tạo folder con và QA case từ UI-02 trên staging.
- Archive vẫn xem lại được.
- Deep-link và browser reload không lỗi.

---

# PHASE 6 — Artifact, Upload, Input Manifest và DICOM Validation

**Module:** MOD-04
**Thời lượng:** 3–4 tuần
**Phụ thuộc:** P5
**Stitch:** Một phần trong UI-03; cần QA Case Upload/Validation screens chi tiết
**Mục tiêu:** file gốc được lưu nguyên trạng và biết rõ có dùng được cho workflow nào.

## Design

- Tạo QA Case detail/upload queue.
- Tạo Input Manifest, metadata, validation warning/error và lineage views.
- Thiết kế progress, retry, duplicate checksum và interrupted upload.

## Storage/data

- Chọn S3-compatible object storage bền vững.
- Artifact metadata, SHA-256, byte size, media type và object key.
- Original/derived lineage.
- Signed download URL có hạn.
- Không dùng Railway ephemeral filesystem làm kho chính.

## DICOM

- pydicom metadata-first parser.
- CT, RTDOSE, RTSTRUCT, RTPLAN baseline.
- SOP/Study/Series/Frame UIDs.
- Dose scaling/grid/orientation/reference validation.
- gamma.measurement.v1 validator.
- Không ghép bằng filename hoặc PatientID.

## Worker/API/frontend

- Streaming/multipart upload.
- Validation job idempotent.
- Artifact status UPLOADED/VALIDATING/VALID/WARNING/INVALID/ARCHIVED.
- Manifest role selector.
- Download và audit.

## Tests

- Byte-for-byte source integrity.
- Duplicate/retry upload.
- Valid/invalid DICOM fixtures.
- Missing UID/scaling/unit.
- Geometry mismatch.
- Measurement ambiguous/shape mismatch.
- Browser refresh trong upload/job.

## Exit criteria

- Upload trên staging tạo checksum và manifest.
- File tải lại đúng checksum.
- Validation giải thích được từng warning/error.
- Measurement mơ hồ không đi tiếp Gamma.

---

# PHASE 7 — Machine QA

**Module:** MOD-05
**Thời lượng:** 2–3 tuần
**Phụ thuộc:** P6; P7 tạo protocol seed tối thiểu có version, còn thư viện quản trị đầy đủ hoàn thiện ở P11
**Stitch:** Chưa có screen riêng
**Mục tiêu:** hoàn thiện Daily/Monthly/Annual/Custom Machine QA vertical slice.

## Design

- Tạo Machine QA checklist, measurement editor, result summary và history screens.
- Thể hiện actual, unit, baseline, tolerance, action level, margin và status.

## Backend/data

- Tạo QAProtocolVersion/Rule seed tối thiểu và immutable snapshot để Machine QA hoạt động; CRUD/library đầy đủ để P11.
- AnalysisConfiguration, AnalysisRun, MetricResult, Warning.
- Rule engine: <=, >=, range, absolute/percent deviation, N/A và review.
- Immutable completed run; rerun tạo run mới.
- TrendPoint projection.

## API/frontend

- Tạo run từ protocol version.
- Autosave/versioned draft measurement.
- Evaluate và hiển thị result.
- Rerun/compare.
- Gắn artifact và note.

## Tests

- Known rule values.
- Missing/invalid unit.
- Baseline deviation.
- Rerun không xóa run cũ.
- Failed evaluation không tạo valid result.
- Trend source pointer.

## Exit criteria

- Một Machine QA case đi từ checklist tới metric và history.
- Result có actual/limit/margin/status/rule snapshot.
- Staging E2E pass.

---

# PHASE 8 — PSQA Gamma

**Module:** MOD-06
**Thời lượng:** 4–5 tuần
**Phụ thuộc:** P6, P7 analysis foundation
**Stitch:** UI-03 có sẵn
**Mục tiêu:** PSQA Gamma end-to-end bằng test/reference dataset.

## Infrastructure

- Tạo Railway Redis-compatible queue và worker service ở staging.
- API chỉ enqueue; không chạy Gamma lớn trong HTTP request.
- Idempotency, retry, timeout, heartbeat và queue metrics.
- Theo dõi Railway usage/cost sau khi thêm service.

## Engine

- GammaConfiguration đầy đủ.
- Adapter interface và deterministic implementation.
- 2D trước; 3D sau khi cùng contract/golden test đạt.
- Global/local, absolute/relative, threshold, DTA, normalization, alignment và interpolation.
- Map, histogram, pass rate, percentiles, warning và provenance.

## Frontend

- Dùng UI-03: reference/evaluation selection, config, preflight validation, job progress, result và rerun.
- Compare two runs.
- Job survives refresh/reconnect.

## Tests

- Uniform, known shift, scaling, different grid, low-dose cutoff, edge field.
- 2D/3D, global/local, absolute/relative.
- Missing RTDOSE/measurement.
- RTSTRUCT optional cho phantom/plane.
- NaN/invalid data.
- Golden/reference expected result.

## Exit criteria

- RTDOSE + measurement valid chạy end-to-end trên staging worker.
- Missing critical input bị chặn đúng error code.
- Configuration snapshot đủ và run cũ không đổi.
- Golden test pass.

---

# PHASE 9 — Report Builder, Revision và Export

**Module:** MOD-07
**Thời lượng:** 3–4 tuần
**Phụ thuộc:** P7; Gamma blocks cần P8
**Stitch:** UI-04 có sẵn
**Mục tiêu:** report tùy chỉnh toàn diện và tái hiện từ snapshot.

## Design/frontend

- Đọc UI-04.
- Bổ sung Report Viewer, Revision History, Compare Revision và Export Progress.
- Block palette, reorder, hide/show, rename, metric/chart selection và notes.
- Preview responsive/print.

## Backend/data

- ReportTemplate/Version, Report, ReportRevision và ReportBlockConfig.
- Snapshot input manifest, analysis, protocol, config, template và render options.
- Old revision không đọc live state.

## Renderer

- HTML first.
- PDF, PNG, CSV và JSON.
- Vietnamese font và chart assets pinned.
- Renderer ban đầu có thể là worker capability; chỉ tách service sau benchmark.
- Output checksum và render version.

## Tests

- Add/remove/reorder/hide/rename.
- Large metric table.
- Gamma map/chart.
- Old revision repeatability.
- Missing/corrupt artifact.
- PDF visual/snapshot test.

## Exit criteria

- User tạo, sửa và export report trên staging.
- Old revision tái render đúng snapshot.
- Render failure không thay AnalysisRun.

---

# PHASE 10 — Trend

**Module:** MOD-08
**Thời lượng:** 2–3 tuần
**Phụ thuộc:** P7, P8, P9
**Stitch:** Chưa có screen riêng
**Mục tiêu:** biến metric theo thời gian thành trend có drill-down.

## Design

- Tạo Trend Dashboard screen.
- Filter machine, QA type, metric, period, energy, detector, phantom và protocol.
- Baseline/tolerance/action/outlier/maintenance marker.

## Backend/frontend

- TrendPoint read model và indexed query.
- Unit compatibility.
- MaintenanceEvent.
- Drill-down point → case → analysis → report.
- CSV/JSON/chart export.

## Tests

- Không trộn machine.
- Không vẽ chung unit không tương thích.
- Baseline/action/tolerance.
- Outlier không bị xóa.
- Drill-down source đúng.

## Exit criteria

- Trend thực từ Machine QA/Gamma hiển thị trên staging.
- Filter và drill-down pass.
- Screen có empty/large-data/error states.

---

# PHASE 11 — QA Protocol Library

**Module:** MOD-09
**Thời lượng:** 2–3 tuần
**Phụ thuộc:** P7, P9
**Stitch:** Chưa có screen riêng
**Mục tiêu:** protocol/rule/reference có version và dùng lại được.

## Design

- Tạo library, protocol editor, rule editor, reference panel và version comparison.

## Backend/data

- QAProtocol, Version, Rule và Reference.
- Clone, version, changelog và effective note.
- Không update ngược protocol snapshot đã dùng.

## Frontend/API

- Search theo QA type/machine/keyword.
- Create/clone/version.
- Gắn protocol version vào QACase/AnalysisConfiguration.
- Compare versions.

## Tests

- Rule snapshot.
- Protocol cũ giữ report cũ.
- Clone không share mutable child.
- Search/version/audit.

## Exit criteria

- Tạo protocol version và dùng được trong Machine QA/Gamma.
- Report cũ không thay đổi khi có version mới.
- R1 Clinical MVP feature-complete trên staging.

---

# PHASE 12 — Biological Hub

**Module:** MOD-10
**Thời lượng:** 1–2 tuần
**Phụ thuộc:** P3, P9 cho independent report shell
**Stitch:** Chưa có screen hoạt động; UI cũ đã deprecated, phải tạo lại
**Mục tiêu:** tạo bounded context và navigation riêng cho Biological Toolkit.

## Work

- Đọc bốn screen chuẩn và Design System; tạo mới Biological Toolkit Overview trong cùng project.
- Tạo route namespace /app/biological.
- BiologicalScenario và CalculationRun base.
- Calculation history, source, assumption và recent tools.
- Không có QA case/patient selector mặc định.
- Independent report entry point.

## Tests

- No automatic QA/patient linkage.
- Organization scoping cho history.
- Hub empty/populated/error.
- Deep-link tới calculator modules.

## Exit criteria

- Biological Hub hoạt động độc lập trên staging.
- Không có foreign key bắt buộc tới QACase.

---

# PHASE 13 — BED & EQD2

**Module:** MOD-11
**Thời lượng:** 2–3 tuần
**Phụ thuộc:** P12
**Stitch:** Chưa có screen hoạt động; phải tạo lại sau khi P12 design được kiểm tra
**Mục tiêu:** calculator, graph và history hoàn chỉnh.

## Engine/data

- LQ BED/EQD2 model.
- Input D, n, d, alpha/beta, tissue, source và assumptions.
- Consistency validation D = n × d.
- Calculation snapshot và engine version.
- Graph theo D range, step và nhiều alpha/beta.

## Frontend

- Dùng Biological Hub mới và bốn screen chuẩn để tạo BED/EQD2 Calculator mới.
- Calculator, formula explanation, source/assumption panel.
- Chart/table/marker.
- PNG/SVG/CSV và independent report export.

## Tests

- Known-answer formula.
- Invalid n/d/D/alpha-beta.
- D curve values.
- Multiple alpha/beta.
- Snapshot repeatability.

## Exit criteria

- Known-answer suite pass.
- User lưu và mở lại calculation.
- Graph/data/report export đúng snapshot.

---

# PHASE 14 — So sánh phác đồ xạ trị

**Module:** MOD-12
**Thời lượng:** 2 tuần
**Phụ thuộc:** P13
**Stitch:** Chưa có screen hoạt động; phải tạo lại sau P13
**Mục tiêu:** so sánh hai hoặc nhiều fractionation schedules.

## Work

- Tạo mới màn hình so sánh phác đồ, kế thừa AppShell và component language đã khóa.
- Multi-course editor.
- BED/EQD2 per course.
- Absolute/percent difference.
- Context/model mismatch warning.
- Comparison chart/table.
- Save/clone/export scenario.

## Tests

- Two/multi-course known answers.
- Different alpha/beta.
- Inconsistent total dose.
- Context warning.
- Export snapshot.

## Exit criteria

- User so sánh và lưu được nhiều course trên staging.
- Mọi kết quả có source/assumption và engine version.

---

# PHASE 15 — Re-irradiation và bù fraction

**Module:** MOD-13
**Thời lượng:** 3–4 tuần
**Phụ thuộc:** P13, P14
**Stitch:** Re-irradiation screen cũ đã deprecated; phải tạo lại cùng Fraction Compensation
**Mục tiêu:** re-irradiation multi-course và interruption scenarios chi tiết.

## Design

- Tạo mới Re-irradiation Calculator và Fraction Compensation/Interruption screen.
- Hiển thị scalar/spatial mode, recovery/no-recovery và limitations.

## Engine/data

- Course dates/ranges, interval, D/n/d, tissue, alpha/beta và source.
- Recovery assumption model/version.
- Scalar cumulative BED/EQD2.
- Scenario copy/compare.
- Spatial accumulation chỉ khi có geometry/registration contract; không nằm trong bản scalar mặc định.

## Tests

- Multi-course known answers.
- Recovery/no-recovery.
- Missing interval/alpha-beta/source.
- No spatial accumulation without registration.
- Fraction delivered/missing/remaining alternatives.

## Exit criteria

- Multi-course scenario lưu, clone, compare và export được.
- Scalar/spatial mode không bị nhập nhằng.
- Không tự tạo prescription hoặc liên kết treatment case.

---

# PHASE 16 — Dose Limit, Treatment Protocol và Knowledge Library

**Module:** MOD-14
**Thời lượng:** 3–4 tuần
**Phụ thuộc:** P12, P13
**Stitch:** Chưa có screen riêng
**Mục tiêu:** thư viện tra cứu/version độc lập phục vụ công cụ tính toán.

## Design

- Tạo Dose Limit Table.
- Treatment Protocol/Regimen Library.
- Knowledge Article/Formula/Alpha-Beta Library.
- Source/evidence/applicability/version comparison.

## Backend/data

- DoseLimitEntry versioned.
- TreatmentProtocolReference versioned.
- KnowledgeEntry và AlphaBetaEntry versioned.
- Search/index disease, anatomy, OAR, metric, technique và topic.
- Citation/DOI/URL/source type và updated date.

## Frontend/API

- Search/filter/sort.
- Create/clone/version.
- Open source/citation.
- Use entry as calculator input only after user selection.
- Independent export.

## Tests

- Version immutability.
- Search/filter.
- Citation/source presence.
- User override labeling.
- No automatic prescription/QA linkage.

## Exit criteria

- R2 Biological Toolkit feature-complete trên staging.
- Knowledge/version/source workflow pass.

---

# PHASE 17 — Visual Dose và DVH/Plan Review

**Module:** MOD-15
**Thời lượng:** 4–6 tuần
**Phụ thuộc:** P6, P8 analysis worker, P9 report
**Stitch:** Chưa có screen riêng
**Ưu tiên:** Extension; không chặn Clinical MVP/Biological release
**Mục tiêu:** structure-level dose review khi geometry hợp lệ.

## Work

- Tạo Visual Dose/DVH screen trên Stitch.
- RTDOSE + RTSTRUCT linkage; CT khi cần anatomy view.
- Contour rasterization và explicit resampling.
- Dmin/Dmax/Dmean/Dx/Vx baseline.
- Structure mapping manual snapshot.
- Worker execution và plot artifacts.
- Report blocks cho DVH/metrics.

## Tests

- Uniform dose/simple geometry.
- Sphere/box structures.
- Different spacing/orientation.
- Contour outside grid.
- Frame-of-reference mismatch.
- Repeatable DVH metrics.

## Exit criteria

- Known geometry/golden tests pass.
- Missing RTSTRUCT/geometry bị chặn.
- Result có full provenance.

---

# PHASE 18 — Integrated hardening và pilot

**Module:** MOD-16
**Thời lượng:** 3–6 tuần
**Phụ thuộc:** R1; R2 nếu phát hành cùng Biological Toolkit
**Mục tiêu:** kiểm tra sản phẩm như một hệ thống và chạy pilot bằng dataset thật.

## Integrated/E2E

- Auth → organization → machine → folder → case.
- Upload → checksum → validation → analysis.
- Machine QA → trend.
- Gamma → report → revision/export.
- Protocol update không thay report cũ.
- Biological scenario → calculation → graph → report.
- Backup → restore → checksum.

## Reliability/performance

- API p50/p95.
- Upload lớn.
- Gamma 2D/3D time.
- Queue throughput/depth.
- Report render time.
- API/worker/Redis/PostgreSQL/object-storage restart/failure.
- Duplicate job/idempotency.

## Security/data isolation

- Organization A không đọc B.
- Signed URL expiry.
- JWT expiry/issuer/audience/signature.
- Secret scan.
- Public endpoint exposure check.

## Pilot

- Chọn site/machine/workflow.
- Shadow/parallel use.
- Import dataset thật theo phạm vi.
- Mọi bug thực tế thành regression fixture trước hoặc cùng bản sửa.
- Ghi version, limitation và sai khác.

## Exit criteria

- Không còn lỗi P0/P1 chưa có quyết định.
- Golden/contract/integration/E2E pass.
- Backup/restore rehearsal pass.
- Pilot findings và known limitations được ghi.
- Release candidate được khóa bằng manifest.

---

# PHASE 19 — Production Web và Remote Access

**Thời lượng:** 1–2 tuần sau P18
**Phụ thuộc:** P18
**Mục tiêu:** phát hành URL production qua HTTPS, không expose service nội bộ.

## Deployment

- Backup production trước migration.
- Promote exact release manifest từ staging.
- Chạy Alembic migration.
- Kiểm tra Service Settings production: Root Directory `/apps/api`, Dockerfile `/apps/api/Dockerfile`, pre-deploy `alembic upgrade head`, healthcheck `/api/v1/health` và process bind `$PORT`.
- Deploy api-web, Postgres, Redis/worker và renderer theo topology đã benchmark.
- Cấu hình Supabase production site/redirect/JWT.
- Cấu hình domain, DNS, HTTPS, CORS, body limit và timeout.
- Object storage private, signed URL có hạn.
- PostgreSQL/Redis/worker/renderer không public.

## Remote smoke test

- Mạng ngoài hạ tầng, desktop và mobile browser.
- Login/logout/refresh/deep-link.
- Organization isolation.
- Folder/case/upload/validation.
- Machine QA/Gamma job sau refresh.
- Report/revision/export/download.
- Biological Toolkit độc lập.
- Error không lộ stack trace/secret.

## Rollback/monitoring

- Rollback image/version rehearsal.
- Database restore procedure.
- Alert API down, worker backlog, job failure, backup failure và error rate.
- Cost/usage alert phù hợp với Railway budget.

## Exit criteria

- Public URL/HTTPS pass.
- Remote E2E trong phạm vi release pass.
- Backup/restore và rollback có evidence.
- Release version frontend/API/engine/schema/renderer được ghi.

---

# PHASE 20 — Vận hành và cải tiến liên tục

**Thời lượng:** Ongoing
**Phụ thuộc:** P19
**Mục tiêu:** duy trì hệ thống và chuyển case thực tế thành chất lượng sản phẩm.

## Công việc định kỳ

- Theo dõi uptime, error rate, queue, storage, database và cost.
- Kiểm tra backup và restore định kỳ.
- Rotate token/secret theo runbook.
- Cập nhật dependency có test.
- Triage dataset/vendor variation.
- Thêm regression fixture trước khi đóng bug.
- Version engine khi thay đổi kết quả.
- Không sửa ngược AnalysisRun/ReportRevision cũ.
- Đọc lại Stitch screen bằng MCP khi thay UI; ghi screen ID/revision trong issue.
- Tạo screen mới trong đúng Stitch project, không tạo project thiết kế phân tán.

## Exit criteria cho mỗi maintenance release

- Regression/full suite pass.
- Migration/rollback reviewed.
- Release note và known limitations cập nhật.
- Staging smoke test pass trước production.

---

## 4. Screen gap plan

| Module | Screen hiện có | Cần bổ sung bằng Stitch MCP | Phase |
| :--- | :--- | :--- | :--- |
| MOD-00 | Không | Login, recovery, callback, session error | P3 |
| MOD-01 | Home Dashboard | Responsive/empty/error variants | P3 |
| MOD-02 | Không | Organization/Site/Machine management | P4 |
| MOD-03 | QA Archive | QA case create/detail, folder modals | P5 |
| MOD-04 | Một phần Gamma Workspace | Upload queue, manifest, validation detail | P6 |
| MOD-05 | Không | Machine QA checklist/result/history | P7 |
| MOD-06 | Gamma Workspace | Job failure/retry, compare runs | P8 |
| MOD-07 | Report Builder | Viewer, revision history/compare/export progress | P9 |
| MOD-08 | Không | Trend dashboard/drill-down | P10 |
| MOD-09 | Không | Protocol library/editor/version compare | P11 |
| MOD-10 | Không; legacy hidden/deprecated | Tạo lại Biological overview + empty/error/history | P12 |
| MOD-11 | Không; legacy hidden/deprecated | Tạo lại BED/EQD2 + responsive/export/history | P13 |
| MOD-12 | Không; legacy hidden/deprecated | Tạo lại plan comparison + multi-course/error | P14 |
| MOD-13 | Không; legacy hidden/deprecated | Tạo lại Re-irradiation + fraction compensation/interruption | P15 |
| MOD-14 | Không | Dose limit, protocol, knowledge library | P16 |
| MOD-15 | Không | Visual Dose/DVH workspace | P17 |
| MOD-16 | Không bắt buộc | Status/maintenance/diagnostic screens khi cần | P18–P20 |

---

## 5. Railway service evolution

| Phase | Railway topology | Lý do |
| :--- | :--- | :--- |
| P2–P7 | api-web/RT-connect + PostgreSQL | Chi phí thấp, đủ CRUD/auth/QA archive/Machine QA nhẹ |
| P8 | Thêm Redis + worker | Gamma bắt buộc bất đồng bộ |
| P9 | Renderer trong worker trước | Tách service khi benchmark hoặc isolation yêu cầu |
| P17 | Worker pool/resource tuning | DVH/Gamma tải lớn |
| P19 | Topology đã benchmark | Production không dùng cấu hình giả định |

Nguyên tắc:

- Không tạo service chỉ vì có trong sơ đồ kiến trúc.
- Không chạy analysis lớn trong API để tiết kiệm một service.
- Xem Railway usage/cost trước và sau mỗi topology change.
- Có staging trước production.
- Token deploy không đi vào runtime.
- PostgreSQL dùng private/reference variable; browser không nhận DATABASE_URL.

---

## 6. Bộ test theo release

### R0

- Repository/CI.
- Migration.
- Railway staging health.
- PostgreSQL private connection.
- Supabase auth/JWT.
- Secret/bundle scan.

### R1 Clinical MVP

- Organization isolation.
- Folder/archive.
- Artifact checksum/DICOM validation.
- Machine QA known rules.
- Gamma golden suite.
- Report snapshot/render.
- Trend drill-down.
- Protocol version immutability.
- Worker retry/idempotency.

### R2 Biological

- BED/EQD2 known answers.
- D curve.
- Multi-course comparison.
- Recovery/no-recovery.
- Re-irradiation limitations.
- Dose-limit/knowledge version/source.
- No automatic QA/patient linkage.
- Independent report snapshot.

### R3 Advanced DICOM

- Geometry/reference fixtures.
- DVH known geometry.
- Resampling conventions.
- Structure mapping.
- Report blocks/provenance.

### R4 Production

- DNS/TLS/CORS.
- External-network auth/session.
- Upload/job/report/download after refresh.
- Private service exposure.
- Backup/restore/checksum.
- Rollback.
- Monitoring/alert.
- Cost/usage alert.

---

## 7. Rủi ro và kiểm soát

| Rủi ro | Kiểm soát |
| :--- | :--- |
| Stitch project public | Chỉ synthetic data; không token, DICOM thật hoặc PatientID |
| Stitch HTML bị coi là production code | Review, component hóa, typed API và accessibility test |
| Thiếu screen nhưng vẫn code | Screen gap gate ở đầu phase |
| Railway production token bị dùng quá sớm | Tạo staging; production chỉ P19 |
| Deployment hiện tại FAILED | Root-cause ở P2; không lặp deploy mù |
| Chưa có PostgreSQL | Provision staging ở P2, migration trước domain module |
| Chi phí Railway vượt ngân sách | Topology theo phase, usage snapshot/alert, benchmark trước scale |
| Railway filesystem mất file | Object storage persistent từ P6 |
| Gamma làm nghẽn API | Redis/worker từ P8 |
| DICOM vendor variation | Fixture/adapter/regression |
| Report tùy biến khó tái hiện | Snapshot/hash/pinned renderer |
| Protocol update làm đổi report cũ | Version + snapshot |
| Biological bị gắn nhầm ca bệnh | Bounded context và no-link tests |
| Re-irradiation bị hiểu là spatial accumulation | Mode rõ; registration contract bắt buộc |
| Supabase bị dùng làm business database | Railway PostgreSQL là nguồn dữ liệu nghiệp vụ duy nhất |
| Secret lọt Git/frontend/log | Ignore, secret store, bundle/log scan |

---

## 8. Quản lý thay đổi

1. Tạo issue có BR/MOD/phase.
2. Đọc screen Stitch hiện hành qua MCP và ghi screen ID.
3. Xác định ảnh hưởng schema/API/engine/report/test.
4. Viết hoặc cập nhật test.
5. Thực hiện migration và code.
6. Chạy focused test, full suite và staging smoke test.
7. Cập nhật business-analysis.md nếu requirement đổi.
8. Cập nhật technical-specification.md nếu contract/architecture đổi.
9. Cập nhật plan.md nếu dependency/phase/exit criteria đổi.
10. Ghi release note/version.
11. Không sửa ngược dữ liệu/result/report cũ.

Khi thay đổi deployment hoặc biến môi trường, issue/release note bắt buộc ghi riêng:

- Environment và service bị thay đổi.
- Source branch và commit/deployment ID.
- Root Directory và Dockerfile path.
- `DATABASE_URL` là reference tới service PostgreSQL nào; không ghi secret.
- Pre-deploy command thực tế trong Service Settings/metadata.
- Healthcheck path, target port và việc process bind `$PORT`.
- Kết quả `/api/v1/health`, `/api/v1/ready`, migration revision và rollback decision.

---

## 9. Bàn giao cuối cùng

- Source frontend/backend/worker/renderer.
- Database migrations và schema documentation.
- Typed API/OpenAPI contracts.
- Google Stitch project/screen mapping và design-to-code traceability.
- Test suites và fixtures.
- DICOM/Gamma/DVH/Biological golden data.
- Railway service/environment map.
- Supabase Auth configuration checklist.
- Object storage configuration.
- CI/CD và release manifest.
- Staging/production URLs.
- Backup/restore và rollback evidence.
- Monitoring/cost alert checklist.
- User guide, troubleshooting và production runbook.
- Pilot findings, known limitations và post-pilot backlog.
- Không bàn giao secret plaintext trong tài liệu hoặc repository.

---

## 10. Kết luận

RT-CONNECT được triển khai theo từng module hoàn chỉnh, không theo kiểu dựng toàn bộ giao diện rồi mới nối dữ liệu. Staging Railway được thiết lập sớm để mỗi phase đều được kiểm tra trong môi trường gần thực tế. Clinical MVP hoàn tất lần lượt từ Auth/Home, organization/archive, artifact validation, Machine QA, Gamma, report, trend tới QA Protocol Library. Biological Toolkit được tách thành Hub, BED/EQD2, comparison, re-irradiation và knowledge modules độc lập.

Google Stitch MCP thay thế vai trò của UI-UX.md như nguồn thiết kế trực quan, nhưng không thay thế business requirement, API contract hoặc test. Railway là backend/data plane với PostgreSQL; Supabase chỉ là auth/identity plane. Production public release chỉ diễn ra sau integrated test, pilot, backup/restore và rollback evidence.
