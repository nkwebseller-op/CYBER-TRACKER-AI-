# @cyberai/shared-types

Single source of truth for cross-language contracts. `schemas/*.json` are
JSON Schema documents; `ts/` and `python` consumers hand-map them today
(Phase 1). A future phase can add codegen (e.g. `quicktype` /
`datamodel-code-generator`) — deliberately not added yet to avoid a
build-tool dependency the foundation doesn't need.

- `schemas/policy-decision.schema.json`
- `schemas/planned-action.schema.json`
- `schemas/execution-result.schema.json`

The TypeScript types in `ts/index.ts` and the Python models in
`apps/api/app/schemas/` must stay structurally in sync with these schemas.
