# Architecture

## Initial service boundaries

- `apps/web`: user interface and authenticated dashboard.
- `apps/api`: authentication, projects, source registration and job orchestration.
- `apps/worker`: asynchronous media processing jobs.
- `packages`: shared contracts and utilities as the codebase grows.

## Media processing lifecycle

1. User uploads a file or registers a source they are authorized to access.
2. API validates ownership/authorization, file type, size and source policy.
3. Media is stored in private object storage; the API creates a processing job.
4. Worker probes media metadata, extracts audio, transcribes speech and runs configured visual/audio analysis.
5. Candidate moments are scored with explainable signals and returned for user review.
6. User approves edits; FFmpeg renders requested aspect ratios and subtitles.
7. Exports are stored privately and made available through short-lived signed URLs.

## Safety and reliability requirements

- Treat all user-provided URLs and media as untrusted.
- Defend against SSRF at DNS resolution and connection time, including redirects and IPv4/IPv6 edge cases. Prefer an egress proxy/allowlist for external fetchers.
- Do not bypass login, DRM, paywalls, private content controls or platform restrictions. Prefer official APIs and explicit user uploads.
- Run FFmpeg and media parsers in isolated, resource-limited workers; enforce duration, size, codec and timeout limits.
- Keep secrets outside git. Encrypt sensitive tokens and use least-privilege access.
- Make jobs idempotent, retryable and observable; persist state transitions and failure reasons.
- Require explicit user approval before publishing content to a social account.

## Current implementation status

This document is a target architecture, not a claim that these processing capabilities are already implemented. The repository currently contains only the initial project documentation and configuration templates.
