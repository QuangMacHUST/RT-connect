# ISSUE: Existing Railway deployment failed before source bootstrap

## Identity

- Project: `prolific-learning` (`339f2c50-ddd7-491f-8c4e-da2a2d169502`).
- Environment: `production` (`910dff25-75b6-42b2-bf6b-e2601ba9d7d2`).
- Service: `RT-connect` (`9544c3e6-c8bd-4c29-b62e-c6172eb51af3`).
- Deployment: `b8037f6c-720c-407c-b5e4-34421358b4a3`.
- Status: `FAILED`, stopped.
- Checked: 2026-09-04.

## Evidence

The latest Railway build log reports:

- Railpack version `0.39.0` analyzed the repository.
- `start.sh` was not found.
- Railpack could not determine a supported build/runtime.
- The deployed tree contained only Markdown/static design artifacts and no runnable Python/Node application manifest or Dockerfile.

## Root cause

The Railway service was connected to the repository before P1 created application source and a build/start contract. The recorded failed deployment used commit `aa5dce6` (`set up enviroment`), which contains only the document tree shown in the log. The current `origin/main` commit is `dc6ee79` and contains the API/web source and deployment files. The new deployment for `dc6ee79` was skipped because the GitHub CI check suite failed in the repository secret guard; API and web jobs passed. This is a source/configuration gate failure, not an intermittent infrastructure failure.

## Control

- Do not redeploy the same document-only commit.
- Do not change production while P1/P2 are incomplete.
- P1 must create the FastAPI/React source, pinned manifests, health/version endpoints and deployment files.
- P2 must create a separate staging environment and deploy the health-only/API shell there first.
- The API Railway service must use monorepo root directory `/apps/api` and config path
  `/apps/api/railway.toml`; otherwise Railway continues analyzing the repository root and will
  not find the API Dockerfile.
- The reviewed source is now committed and pushed to `main`; the CI secret guard must pass
  before Railway will deploy it.
- A regression check must confirm Railpack/Docker can build the selected root and start command before any production promotion.

## Acceptance evidence for closure

1. P1 local build, tests and production bundle pass.
2. Railway staging exists.
3. Staging build identifies the intended runtime or Dockerfile.
4. Staging health/readiness/version endpoints pass over HTTPS.
5. The deployment manifest records commit/image, start command and migration version.
6. No production redeploy occurs until the P19 promotion gate.
