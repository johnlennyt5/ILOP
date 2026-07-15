# Harborview Lending — Agentic Loan & Mortgage Intake + Robot Identity Governance

**Author:** Johnlenny Tejada · Providence, RI
**Platform:** UiPath (Maestro · Agent Builder · Document Understanding · Action Center · Orchestrator · Data Fabric · Apps · Integration Service)
**Status:** In active development — 8-week build (see [Roadmap](#roadmap))

---

## What This Is

A two-pillar UiPath solution built around the two problems that most commonly stall enterprise automation programs in banking:

1. **Loan and mortgage intake and processing** — high-volume, document-heavy, compliance-bound, and still largely manual at most institutions. Requests arrive by email in every imaginable shape: prose, PDFs, CSVs, JSON exports from partner systems.
2. **Robot identity management** — the operational layer underneath every automation: provisioning robot accounts, folder allocation, machine bindings, credential governance, and access attestation. When this layer is manual, every new process ships late and every audit hurts.

Pillar 1 automates a business process. Pillar 2 automates the automation program itself.

The demo scenario uses **Harborview Financial Group**, a fictional regional bank in Providence, RI. All documents, borrowers, and data are synthetic.

---

## Pillar 1 — Agentic Intake Pipeline (Loans & Mortgages)

A single email-driven front door, an AI intake router, and **two parallel product pipelines** — loans and mortgages are classified, extracted, and evaluated as distinct products with distinct document sets and rules, then converge on a shared, governed disposition and notification stage.

### End-to-End Process Flow (as built in Maestro BPMN)

```
Gmail Inbox (EMAIL_RECEIVED trigger — Integration Service, polling)
      │
      ▼
Email Queue ── every message logged to Intake-Raw queue
      │        (unique reference = Gmail Message ID → duplicate delivery rejected)
      ▼
Intake Router Agent ── classifies request from a normalized JSON envelope
      │                (email body + extracted attachment content: PDF / CSV / JSON)
      ▼
◇ Document Type Routing
      ├── MORTGAGE ──► Extract Mortgage Details ─┐
      ├── LOAN ──────► Extract Loan Details ─────┤
      └── OTHER (default) ──► Triage Queue ──► ⊙ Not Applicable
                                                 │
      ┌──────────────────────────────────────────┘
      ▼ ◇ Unified Pipeline (branches converge)
Compliance Check Agent ── hard-veto rules; a veto can never be outvoted into auto-approve
      │
      ▼
Risk Assessment Agent ── scored evaluation with confidence
      │
      ▼
◇ Disposition Routing
      ├── auto-approve ──► Auto-Approved Queue ──────────────────┐
      ├── auto-deny ─────► Auto-Denied Queue ────────────────────┤
      └── review (default) ──► Human-Review Queue                │
                                   │                             │
                                   ▼                             │
                     Human Review (Action Center User Task)      │
                     — process suspends until a reviewer acts    │
                                   │                             │
                                   ▼                             │
                     ◇ Human Disposition Routing                 │
                        ├── APPROVED ──► Human-Approved ─────────┤
                        └── DECLINED ──► Human-Denied ───────────┤
                                                                 ▼
                                              ◇ Notification Routing
                                                (single variable: finalDecision)
                        ┌────────────────────────────┴───────────────────────┐
                        ▼                                                    ▼
          Compose & Send Approval Email                    Compose & Send Adverse-Action Email
          (AGENT — personalized, next steps)               (TEMPLATE — deterministic reason codes,
                        │                                   pre-approved language; no LLM authorship)
                        └────────────► Log Final Record ◄────────────────────┘
                                       (Data Fabric entity — full audit trail)
                                              │
                                              ▼
                                       ⊙ Decision Complete
```

### The Two Product Pipelines

| | **Loan Pipeline** | **Mortgage Pipeline** |
|---|---|---|
| **Products** | Personal, auto, and small-business lending | Home purchase, refinance, home equity |
| **Typical package** | Application details, W-2s, pay stubs, bank statements | URLA (Form 1003), W-2s, pay stubs, bank statements, ID |
| **Extraction stage** | `Extract Loan Details` — income, requested amount, term, purpose, DTI inputs | `Extract Mortgage Details` — borrower, property, loan amount, income, DTI inputs from the 1003 |
| **Risk emphasis** | Income verification, DTI vs. product policy | DTI, property/loan profile, documentation completeness |
| **Regulatory surface** | ECOA/Reg B adverse-action requirements | ECOA/Reg B adverse-action requirements + mortgage-specific disclosure posture |

Both products share the compliance → risk → disposition → notification backbone, so governance is enforced once, identically — while extraction and evaluation stay product-specific. Adding a third product (e.g., HELOC) means adding one routing edge and one extraction task, not a new pipeline.

### Format-Flexible Intake, Schema-Strict Agents

Requests arrive as free-text email, PDF attachments, CSV rows, or JSON payloads. The pipeline **normalizes every format into one JSON envelope** (source, sender, subject, body text, extracted attachment text) *before* any agent runs. Agents always receive the same strict shape and return schema-enforced structured output:

```json
{ "category": "LOAN | MORTGAGE | OTHER", "confidence": 0.0–1.0, "reasoning": "...", "signalsFound": [] }
```

Flexibility lives in the pipeline; strictness lives at the agent boundary. That is what makes agent behavior testable and auditable.

### The Agents

| Agent | Role | Guardrail |
|---|---|---|
| **Intake Router Agent** | Classifies each normalized envelope as LOAN / MORTGAGE / OTHER | Conflicting or absent signals → OTHER with low confidence; never guesses |
| **Compliance Check Agent** | Policy and eligibility screening | Hard veto: can force review or denial, can never be overridden into auto-approve |
| **Risk Assessment Agent** | Scored risk evaluation with confidence | Low confidence routes to human review by default-flow design |
| **Approval Email Composer** | Drafts personalized approval notifications | Approval only — the lowest-risk message in the process |

### Where AI Deliberately Is Not

The **adverse-action (denial) notice is not agent-written.** Under ECOA/Reg B a denial must state specific, accurate reasons. Denial emails are generated from **deterministic templates populated with reason codes** produced by the compliance/risk logic (e.g., `DTI_EXCEEDS_POLICY`) and mapped to pre-approved plain-language sentences. Every sentence in a denial existed before the pipeline ran; the pipeline only selects and fills. Knowing where *not* to put an LLM is a design feature of this project, not a gap.

### Key Design Points

- **Deterministic orchestration, non-deterministic reasoning.** Maestro BPMN owns routing and state; agents advise through confidence-scored structured output. Ambiguity always falls to the default flow — human review — never to auto-disposition.
- **Human-in-the-loop as a real BPMN suspension.** Review items stop at an Action Center User Task until a reviewer acts; the reviewer's verdict sets the same `finalDecision` variable the auto paths set, so human and automated decisions are downstream-identical and equally audited. SLA timers with escalation attach to this task (in progress — see roadmap).
- **Audit-first.** Every email is queued to `Intake-Raw` before any AI touches it; every decision, score, veto, and human action lands in one Data Fabric record per application.
- **Nothing drops silently.** Non-lending email exits through a Triage queue with its own end state; failures route to an Exceptions queue (in progress).

### Orchestrator Queues

| Queue | Purpose |
|---|---|
| `Intake-Raw` | Every inbound email, logged pre-classification (unique ref: Gmail Message ID) |
| `Auto-Approved` / `Auto-Denied` | Automated dispositions with full context payload |
| `Human-Review` | Ambiguous, low-confidence, or compliance-flagged applications |
| `Triage` | Non-lending email — acknowledged, not processed |
| `Exceptions` | Agent errors, timeouts, malformed payloads — nothing fails invisibly |

---

## Pillar 2 — Robot Identity Lifecycle Manager

Every unattended automation depends on a correctly provisioned digital worker: a robot account, a folder allocation with the right role, a machine binding, and credentials. In regulated environments these identities must be governed like human identities — least-privilege access, rotation, and periodic attestation. Done manually, this is slow and error-prone; the classic failure ("no user with unattended robot permissions in this folder") blocks deployments for reasons invisible to most developers.

This pillar is a UiPath solution *for* the UiPath platform, built on the **Orchestrator REST API**:

| Component | What it does |
|---|---|
| **Provisioning workflow** | Creates a robot account, assigns it to a target folder with the Automation User role (least privilege), binds a machine template, and verifies the full execution chain — one governed request instead of five manual admin screens |
| **Pre-flight check** | Audits any folder before go-live: unattended robot allocated? machine bound? credentials present? trigger runnable? Returns a pass/fail report so deployments never fail on identity misconfiguration |
| **Identity inventory app** | UiPath App listing every digital worker: folder access, roles, machine bindings, credential age, last attestation date |
| **Credential governance** | Credential assets with rotation tracking; designed for enterprise vault integration (CyberArk) via Orchestrator's native credential store support |
| **Attestation report** | Exportable access-review packet per robot identity — the artifact an internal audit or SOX review asks for |

The requirements for this pillar are being captured live: every manual provisioning action performed while building Pillar 1 is logged in [`/docs/provisioning-log.md`](docs/provisioning-log.md) — that log is the spec the provisioning workflow automates.

---

## Repository Contents

| Path | Description |
|---|---|
| `/pillar-1-lending-intake/` | Maestro BPMN (`Process.bpmn`), solution package (`.ius`), agent definitions & prompts, queue configs, Action Center task app |
| `/pillar-2-robot-identity/` | Provisioning + pre-flight workflows, Orchestrator API integration, identity inventory app, attestation report templates |
| `/docs/SDD.md` | Solution Design Document — architecture, design decisions, governance model, known limitations |
| `/docs/provisioning-log.md` | Numbered log of every manual admin action — the living spec for Pillar 2 |
| `/docs/governance-pack/` | Audit-trail samples, prompt register, escalation matrix, adverse-action posture |
| `/docs/images/` | Pipeline architecture diagram (exported from Maestro) |
| `/test-data/` | Synthetic loan and mortgage requests (email, PDF, CSV, JSON) engineered to exercise every routing path |
| `/demo/` | Demo video + script |

![Pipeline Architecture](docs/images/pipeline-architecture.png)

---

## Roadmap

| Weeks | Milestone | Status |
|---|---|---|
| 1 | Tenant foundation: folder, unattended robot, machine binding, Gmail connection, queues | ✅ Complete |
| 2–3 | End-to-end Maestro BPMN: dual-pipeline routing, HITL, notification split, audit path | ✅ Complete (diagram); node-by-node wiring 🔄 In progress |
| 3–4 | Agents live (router, compliance, risk, approval composer); queue wiring; attachment normalization (PDF/CSV/JSON) | 🔄 In progress |
| 4–5 | Action Center review task + SLA escalation; adverse-action template engine; Data Fabric entity + operations app | ⬜ Planned |
| 5–6 | Robot Identity Manager: provisioning workflow, pre-flight check, inventory app, credential rotation | ⬜ Planned |
| 7 | Governance pack, SDD, test evidence, demo video | ⬜ Planned |
| 8 | Hardening, documentation polish, final release | ⬜ Planned |

---

## Background

This project extends my earlier **Meridian Loan Intake** build (Maestro BPMN + Document Understanding + AI agent triage + Action Center + Data Fabric, DU project score 91%) in three directions: from a single product to a dual-product routed pipeline, from file-drop intake to format-flexible email intake, and downward into the platform-governance layer where automation programs actually scale or stall.