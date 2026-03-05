# Implementation Handoff - Milestone 3 (Proposal Generation)

Date: 2026-03-03  
Scope covered: M3.1 (RefactorCategory), M3.2 (Proposal model), and proposal engine contract + duplicate-logic V0 flow.

## 1. Implemented Milestone Status

### M3.1 - RefactorCategory
- Implemented `RefactorCategory` enum with V0-only category:
  - `DUPLICATE_LOGIC`
  - File: `backend/core/refactor_category.py`
- Added parsing helper:
  - `parse_refactor_category(value: str) -> RefactorCategory`
- Session now stores category end-to-end:
  - `ProposalSession._category`
  - Constructor + validators enforce valid category
  - Files: `backend/core/session/proposal_session.py`
- API accepts/returns category:
  - `POST /sessions` accepts optional `category` (defaults to `DUPLICATE_LOGIC`)
  - `GET /sessions/{id}` returns `category`
  - File: `backend/core/api/server.py`
- Worker passes session category into proposal generation:
  - `self._proposal_engine.generate(code_index, found.category(), GenerationContext(...))`
  - File: `backend/core/worker/service.py`

### M3.2 - Proposal Model
- Implemented proposal aggregate with required fields:
  - `version`
  - `category`
  - `affected_files` (`Path` list externally, tuple internally)
  - `unified_diff`
  - `explanation`
  - `created_at`
  - File: `backend/core/proposal/proposal.py`
- Implemented invariants:
  - `unified_diff` must be non-empty (`EmptyUnifiedDiffError`)
  - `affected_files` must be non-empty (`EmptyAffectedFilesError`)
  - `version` must be `> 0` and sequential (`InvalidVersionError`, `NonSequentialVersionError`)
  - `category` must be valid (`InvalidCategoryError`)
  - `created_at` must be valid and normalized to UTC (`InvalidTimestampError`)
- Version auto-increment behavior:
  - `new_proposal(..., previous_version=0)` creates proposal with `version = previous_version + 1`
- Immutability model:
  - No mutator/setter methods are exposed on `Proposal`.
  - Internal data stored in private attributes and exposed through read accessors.
  - `affected_files()` returns a copy.

## 2. Proposal Engine Contract

- Added `ProposalEngine` protocol/interface:
  - `generate(index, category, context) -> Proposal`
  - File: `backend/core/proposal/engine.py`
- Added contract-level rules in docstring + tests:
  - Must not mutate session
  - Must not create branches
  - Must not call validation execution
  - Must return `Proposal` or raise structured `ProposalGenerationError`
- Added structured error model:
  - `ProposalGenerationError`
  - Codes: `INVALID_INPUT`, `UNSUPPORTED_CATEGORY`, `EMPTY_INDEX`, `INTERNAL_ERROR`
- Added `GenerationContext` + validation:
  - `repo_id`, `session_id`, `previous_version`
  - Validates non-empty IDs and non-negative `previous_version`
- Added contract tests with mock implementation:
  - File: `backend/tests/test_proposal_engine_contract.py`

## 3. Duplicate Logic V0 Engine

- Implemented bounded duplicate-logic engine:
  - `DuplicateLogicProposalEngine`
  - File: `backend/core/proposal/duplicate_logic_engine.py`
- Bounded exploration parameters:
  - `ExplorationBounds(max_files, max_lines_per_file, min_block_lines, max_candidates)`
- Behavior:
  - Validates generation input/category/context
  - Requires `BasicCodeIndex` input
  - Scans normalized windows across files for duplicate blocks
  - On hit: emits targeted unified diff by inserting extraction markers in target file
  - On no hit: emits fallback proposal with marker in first file
  - Always returns non-empty `unified_diff` + `affected_files`
- Category support:
  - V0 explicitly supports only `DUPLICATE_LOGIC` (structured unsupported-category error otherwise)

## 4. Session + Lifecycle Integration

- `ProposalSession` now stores:
  - category
  - ordered tuple of proposals
- Proposal attach rules:
  - Allowed states: `INDEXED` or `COMPLETED`
  - Proposal category must match session category
  - Proposal version must be next sequential version
  - File: `backend/core/session/proposal_session.py`
- Worker lifecycle pipeline now:
  1. `CREATED -> RUNNING`
  2. capture snapshot + attach metadata (`SNAPSHOT_READY`)
  3. build code index
  4. transition to `INDEXED`
  5. generate proposal with session category/context
  6. attach proposal
  7. transition to `COMPLETED`
  8. persist

## 5. API Surface Updates

- `POST /sessions`:
  - accepts `repoId`, optional `ref`, optional `category`
  - defaults category to `DUPLICATE_LOGIC`
  - validates category with `parse_refactor_category`
  - returns `{ sessionId, category }`
- `GET /sessions/{id}`:
  - includes top-level `category`
  - includes latest `proposal` with:
    - `version`
    - `category`
    - `affectedFiles`
    - `unifiedDiff`
    - `explanation`
    - `createdAt`

## 6. Tests Added/Updated (Relevant to M3)

- Category:
  - `backend/tests/test_refactor_category.py`
- Proposal model invariants:
  - `backend/tests/test_proposal.py`
- Engine input/context behavior:
  - `backend/tests/test_engine.py`
- Engine interface/contract with mock implementation:
  - `backend/tests/test_proposal_engine_contract.py`
- Duplicate logic engine:
  - `backend/tests/test_duplicate_logic_engine.py`
- Session category/proposal sequencing:
  - `backend/tests/test_session_proposal_session.py`
  - `backend/tests/test_session_store.py`
- API category/proposal response:
  - `backend/tests/test_api_server.py`
- Worker integration proposal generation:
  - `backend/tests/test_worker_service.py`
- End-to-end smoke path:
  - `backend/tests/test_e2e_session_snapshot_smoke.py`

## 7. Verification Run Notes

- Executed successfully in this workspace:
  - `PYTHONPATH=backend python3 -m unittest -v backend.tests.test_proposal backend.tests.test_worker_service`
  - Result: OK (13 tests)
- Attempted broader M3 test run hit import-path mismatch for modules importing `refactorium.*` (environment currently only resolvable under `core.*` path usage without additional package setup).

## 8. Known Gaps / Follow-ups for Next Agent

1. Normalize Python package namespace usage:
   - Codebase currently mixes `core.*` and `refactorium.*` imports.
   - Several tests expect `refactorium` package resolution.
   - Decide and standardize package path strategy (`src/refactorium` layout or import aliasing/install step).
2. Duplicate-logic patch quality (V0 limitation):
   - Current patch inserts markers/comments, not full helper extraction.
   - If required by milestone acceptance, implement real extraction diff synthesis.
3. Optional cleanup:
   - `InvalidContextCategoryError` and `NilCodeIndexError` are exported but not actively raised by current context/index validation path; review if legacy compatibility or dead API.

## 9. Quick File Map

- Category enum/parser: `backend/core/refactor_category.py`
- Proposal model/invariants: `backend/core/proposal/proposal.py`
- Engine contract/errors/context: `backend/core/proposal/engine.py`
- Duplicate logic implementation: `backend/core/proposal/duplicate_logic_engine.py`
- Session aggregate/lifecycle: `backend/core/session/proposal_session.py`
- API endpoints: `backend/core/api/server.py`
- Worker orchestration: `backend/core/worker/service.py`

