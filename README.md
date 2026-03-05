# 🚀 Refactorium — Agentic AI Code Reviewer & Auto-Refactor System

## Python Migration (March 2026)

The backend has been migrated to Python in [`backend_py/`](./backend_py).

Quickstart:

```bash
cd backend_py
PYTHONPATH=. python3 -m unittest discover -s tests -v
PYTHONPATH=. python3 -m cmd.server.main
```

---

# 1️⃣ Project Purpose

This system provides an AI-assisted code review and refactoring workflow for production repositories.

It allows a user to:

1. 🧭 Start a proposal session manually
2. 📦 Index a repository snapshot
3. 🧠 Generate a refactor / bug-fix proposal
4. 🌿 Apply it to a sandbox branch
5. 🧪 Run validation checks (compile / tests / lint / perf)
6. 📊 Score the proposal
7. 👀 Review and approve / reject / regenerate
8. 🗂 Preserve a full immutable audit trail

**Human approval is mandatory. No auto-merge.**

---

# 2️⃣ Core System Capabilities (Scope Map)

| Capability             | Description                      | Milestone |
| ---------------------- | -------------------------------- | --------- |
| 🧬 Session lifecycle   | Create + track proposal session  | M1        |
| 📥 Repo snapshot       | Load repository state            | M2        |
| 🗃 Indexing            | Build per-request index          | M3        |
| 🧠 Proposal generation | Generate patch + explanation     | M4        |
| 🌿 Sandbox branch      | Apply patch in isolation         | M5        |
| 🧪 Validation          | Trigger CI + store results       | M6        |
| 📊 Scoring             | Compute evaluation score         | M7        |
| 📜 Audit               | Immutable proposal versions      | M8        |
| 👀 Review flow         | Approve / reject / regenerate    | M9        |
| ⚙️ Async execution     | Background workers + concurrency | M10       |

---

# 3️⃣ Architecture Overview (V0) 🏗

**Style:** Modular monolith with strict boundaries.

## Modules

* 🌐 api
* 🧭 session
* 📦 repository
* 🗃 indexing
* 🧠 proposal
* 🧪 validation
* 📊 scoring
* 📜 audit
* ⚙️ infrastructure

**Session module = orchestration core.**
All other modules = pure services or adapters.

---

# 4️⃣ Proposal Session Lifecycle 🔁

States:

```
Created
→ SnapshotLoaded
→ Indexed
→ Proposed
→ BranchApplied
→ Validated
→ Scored
→ Reviewed (Approved / Rejected)
```

### Rules

* ⛔ Validation must complete before review
* 📝 Review decision is write-once
* 🔄 Regeneration creates a new proposal version

---

# 5️⃣ Folder Structure 📁

```
/api
/session
/repository
/indexing
/proposal
/validation
/scoring
/audit
/infrastructure
/tests
```

Each module:

* 🧱 Owns its models
* 🔌 Exposes interfaces
* 🚫 Does not mutate another module’s state

---

# 6️⃣ Vertical Build Strategy 🪜

Codex must implement **strictly milestone by milestone**.

Never skip ahead.

Each milestone must:

* ✅ Compile
* ✅ Pass tests
* ✅ Be runnable
* ✅ Preserve modular boundaries

---

# 7️⃣ Extension Points (Must Be Preserved) 🔌

Replaceable without touching session logic:

### 🗃 IndexingStrategy

`BasicFileIndexStrategy (V0)`

### 🧠 ProposalEngine

`LLMBasedProposalEngine (V0)`

### 🧪 ValidationPort

`ExternalCIAdapter (V0)`

### 📊 ScoringPolicy

`SimplePassFailPolicy (V0)`

### 🧵 Middleware Decorators

* Rate limiting
* Logging
* Metrics

All injected via constructor. Never hard-coded.

---

# 8️⃣ Data Ownership Rules 🔐

## 🧭 ProposalSession owns:

* Snapshot reference
* Proposal versions
* Branch reference
* Validation result
* Score
* Review decision
* Audit trail

No other module can modify session state.

## 🧊 Immutable Value Objects

* Snapshot
* CodeIndex
* Patch
* Proposal
* ValidationResult
* Score

No in-place mutation. Ever.

---

# 9️⃣ Testing Requirements 🧪

## Unit Tests

* Session state transitions
* Scoring logic
* Proposal engine contract
* Indexing strategy contract

## Integration Tests

* Session → repo → index → proposal
* Session → validation → scoring
* Regeneration flow

## End-to-End

Full flow:
Create → Propose → Branch → Validate → Score → Review

## Concurrency Tests (M10)

* Multiple sessions
* Idempotent execution
* Worker crash recovery

---

# 🔟 Observability Requirements 📡

Minimum production baseline:

### Structured logs per session

### Metrics

* 📈 Proposal success rate
* 🧪 Validation pass rate
* 🔄 Regeneration count
* 🧠 LLM token usage

### Timeline

* Per-session lifecycle tracking

Audit trail must be **append-only**.

---

# 1️⃣1️⃣ Non-Goals (V0) 🚫

* ❌ No auto-merge
* ❌ No background autonomous scanning
* ❌ No semantic / vector search
* ❌ No multi-agent orchestration
* ❌ No distributed microservices

---

# 1️⃣2️⃣ Development Rules for Codex 🧭

When implementing:

1. Never bypass interfaces
2. Never allow direct cross-module mutation
3. Never embed external system calls inside session logic
4. Never introduce global shared state
5. Every new feature must map to a scoped capability

Before closing a milestone:

* 🧪 Run tests
* 🔄 Validate replaceability (swap one adapter)
* 🔍 Confirm no tight coupling introduced

---

# 1️⃣3️⃣ Definition of Done 🏁

System is complete when:

* ✅ All milestones M1–M10 implemented
* ✅ All scoped features functional
* ✅ Session lifecycle stable
* ✅ Concurrency safe
* ✅ Replaceability validated
* ✅ Observability baseline active
* ✅ Full E2E flow reliable

**No deviation from scope without explicit revision.**
