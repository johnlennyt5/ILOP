# Harborview Mortgage — Agentic Intake & Robot Identity Governance

**Author:** Johnlenny Tejada · Providence, RI
**Platform:** UiPath (Maestro · Document Understanding · Agent Builder · Action Center · Orchestrator · Data Fabric · Apps)
**Status:** In active development — 8-week build (see [Roadmap](#roadmap))

---

## What This Is

A two-pillar UiPath solution built around the two problems that most commonly stall enterprise automation programs in banking:

1. **Mortgage intake and processing** — high-volume, multi-document, compliance-heavy, and still largely manual at most institutions.
2. **Robot identity management** — the operational layer underneath every automation: provisioning robot accounts, folder allocation, machine bindings, credential governance, and access attestation. When this layer is manual, every new process ships late and every audit hurts.

Pillar 1 automates a business process. Pillar 2 automates the automation program itself.

The demo scenario uses **Harborview Financial Group**, a fictional regional bank in Providence, RI. All documents and data are synthetic.

---

## Pillar 1 — Agentic Mortgage Intake Pipeline

A mortgage application isn't one PDF — it's a package: URLA (Form 1003), W-2s, pay stubs, bank statements, and identification. This pipeline ingests the full package and routes every application to a governed disposition.

### Process Flow

```
Intake Folder (Integration Service trigger)
      │
      ▼
Classification Agent ──► splits package by document type (1003 / W-2 / pay stub / bank stmt / ID)
      │
      ▼
Document Understanding ──► field extraction per document type (confidence-scored)
      │
      ▼
Specialist Agents (orchestrated by Maestro BPMN)
      ├── Income Calculation Agent — qualifying income from W-2s + pay stubs
      ├── Completeness Agent — flags missing documents, drafts customer follow-up
      └── Compliance Agent — hard-veto checks, adverse-action readiness
      │
      ▼
Confidence-Gated Gateway
      ├── Auto-Clear        ──► Orchestrator queue: Cleared
      ├── Auto-Decline      ──► Orchestrator queue: Declined (adverse-action record)
      ├── Human Review      ──► Action Center task (SLA timer + escalation)
      └── High-Value Review ──► Action Center task, senior queue
      │
      ▼
Data Fabric entity (full audit trail) ──► Loan Officer Operations App (live dashboard)
```

### Key Design Points

- **Deterministic orchestration, non-deterministic reasoning.** Maestro BPMN owns routing and state; LLM agents own judgment calls — every agent output passes through confidence thresholds and rule-based gates before any disposition.
- **Human-in-the-loop with SLA escalation.** No application is declined or cleared above threshold limits without a reviewer. Action Center tasks carry SLA timers with automatic escalation to a senior queue.
- **Audit-first.** Every extraction, agent decision, confidence score, and human action is persisted to Data Fabric. The operations app surfaces the live record set; the audit trail supports fair-lending and adverse-action review.

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

---

## Repository Contents

| Path | Description |
|---|---|
| `/pillar-1-mortgage-intake/` | Maestro BPMN, DU taxonomy + extractor configs, agent definitions, Action Center app, Data Fabric schema, operations app |
| `/pillar-2-robot-identity/` | Provisioning + pre-flight workflows, Orchestrator API integration, identity inventory app, attestation report templates |
| `/docs/SDD.md` | Solution Design Document — architecture, design decisions, governance model, known limitations |
| `/docs/governance-pack/` | Audit-trail samples, model inventory, prompt register, escalation matrix, adverse-action posture |
| `/test-data/` | Synthetic mortgage packages engineered to exercise each routing path |
| `/demo/` | Demo video + script |

---

## Roadmap

| Weeks | Milestone | Status |
|---|---|---|
| 1–2 | Synthetic mortgage document set; DU classification + extraction models trained | 🔄 In progress |
| 3–4 | Maestro orchestration, three specialist agents, queues, HITL with SLA escalation, Data Fabric + operations app | ⬜ Planned |
| 5–6 | Robot Identity Manager: provisioning workflow, pre-flight check, inventory app, credential rotation demo | ⬜ Planned |
| 7 | Governance pack, SDD, demo video | ⬜ Planned |
| 8 | Hardening, documentation polish, final release | ⬜ Planned |

---

## Background

This project extends my earlier **Meridian Loan Intake** build (Maestro BPMN + Document Understanding + AI agent triage + Action Center + Data Fabric, DU project score 91%) in two directions: from single-document loan intake to multi-document mortgage packages, and downward into the platform-governance layer where automation programs actually scale or stall.

**Johnlenny Tejada** · JohnlennyT@gmail.com · (401) 212-9805 · Providence, RI
