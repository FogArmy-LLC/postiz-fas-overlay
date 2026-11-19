# Build reproduction — Postiz `AuthService` corresponding source

This document explains how `auth.service.ts` in this repository relates to the
Postiz backend FogArmy LLC operates as a network service, and how to rebuild it,
per the AGPL-3.0 corresponding-source obligation (license section 13).

## What is published here

- `auth.service.ts` — human-editable TypeScript source for
  `apps/backend/src/services/auth/auth.service.ts`, as actually deployed
  (modified from upstream).
- `upstream.diff` — unified diff of `auth.service.ts` against the pristine
  upstream file at the revision identified below.
- This file — reproduction steps.

The only functional deviation from upstream is an **email-fallback account
link** for OAuth sign-in: if a user authenticates via a third-party provider
and no account is yet linked to that provider, the service now also checks for
an existing account with the same email (in `loginOrRegisterProvider` and
`checkExists`) before creating a new organization. This avoids duplicate
accounts/orgs when a user later links a second OAuth provider, or an
OAuth provider, to an account that already exists locally. No other FAS
business logic, branding, or private code is contained in or linked from this
file.

## Upstream provenance

- Upstream project: [`gitroomhq/postiz-app`](https://github.com/gitroomhq/postiz-app)
  (AGPL-3.0-only).
- Deployed container: `ghcr.io/gitroomhq/postiz-app`, pinned in FAS's internal
  deployment lockfile by digest
  `sha256:875e61ac5d0ac43c3dec78a78a7032dfb03d9a8c6d4936ebb18adb606cc207c5`.
- **Provenance caveat (flagged, not resolved here):** that lockfile entry pins
  the digest under the `latest` tag
  (`ghcr.io/gitroomhq/postiz-app:latest@sha256:875e61ac...`), not an immutable
  version tag. The GHCR image config for that digest carries no
  `org.opencontainers.image.revision` (or similar) label, so the exact
  upstream git commit baked into that specific image cannot be verified
  cryptographically from registry metadata alone. This also means the pin
  does not satisfy the stated internal policy of "immutable sha256 digests
  only; floating tags forbidden" (the digest is immutable, but it is
  resolved from a floating tag, which can start pointing elsewhere on a new
  push). **Recommendation:** FAS DevOps should re-pin this image against an
  explicit upstream release tag (e.g. `v2.26.0`, the latest tag as of this
  writing) and record that tag alongside the digest, so future corresponding-
  source work can cite an exact, re-fetchable commit.
- Given that caveat, `upstream.diff` in this repo is generated against
  upstream commit `c92d58be17da1a9bfd8de02bb703c783bf4e5d1b` (`gitroomhq/postiz-app`
  default branch HEAD as of 2026-11-17, the date this corresponding source was
  prepared). That file (`apps/backend/src/services/auth/auth.service.ts`) was
  byte-for-byte identical in content to the file compiled into the currently
  running service except for the two email-fallback changes captured in
  `upstream.diff`, so this is a faithful base for the diff even though the
  exact commit cannot be tied to the image digest above.

## Reproducing the build

```bash
# 1. Clone upstream at the revision used for this diff
git clone https://github.com/gitroomhq/postiz-app.git
cd postiz-app
git checkout c92d58be17da1a9bfd8de02bb703c783bf4e5d1b

# 2. Apply the FAS modification
git apply /path/to/postiz-fas-overlay/upstream.diff

# 3. Install dependencies and build the backend app
#    (matches package.json's "build:backend" script)
pnpm install
rm -rf apps/backend/dist
pnpm --filter ./apps/backend run build

# 4. The compiled output equivalent to the deployed postiz-auth.service.js
#    is emitted at:
#    apps/backend/dist/services/auth/auth.service.js
```

No FAS-internal build steps, secrets, environment values, or private
repositories are required to reproduce this file — only the public upstream
repository and the diff published alongside this document.
