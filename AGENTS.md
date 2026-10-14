# Project Guidelines

## Documentation Updates

Before any implementation work, read `docs/roadmap.md` and the documentation
for the affected subsystem. Use those documents to understand intended
behavior, constraints, and current status before planning or editing code. If
the relevant design or behavior is undocumented, identify that gap and resolve
the documentation as part of the implementation. Update all affected
documentation in the same change as the implementation; do not defer it.

Use these references as applicable:

- `docs/api.md` for endpoint paths, request/response shapes, and API behavior.
- `docs/architecture.md` and subsystem design documents for component behavior,
  boundaries, safety constraints, and implementation status.
- `docs/roadmap.md` for completed work, remaining work, and the next suggested
  steps. Keep status explicit: distinguish implemented, partial, planned, and
  unverified behavior.
- `README.md` for current project capabilities, setup, and high-level status.
- `CHANGELOG.md` for a concise entry describing meaningful user-visible or
  operational changes.
- Other focused guides (for example authentication, configuration, frontend,
  testing, and deployment docs) when their subject is affected.

Not every change requires editing every document. Update all documents whose
claims are affected, and keep cross-document status and terminology consistent.
For documentation-only changes, validate links and claims against the code
where practical; for code changes, include documentation in the same review
and validation pass.
