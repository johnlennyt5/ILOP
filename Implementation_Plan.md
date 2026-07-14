# Implementation Plan — Harborview Mortgage Intake & Robot Identity Governance

**Author:** Johnlenny Tejada
**Duration:** 8 weeks · 8 one-week sprints
**Platform:** UiPath — Maestro, Document Understanding, Agent Builder, Action Center, Orchestrator, Data Fabric, Apps, Integration Service
**Method:** Solo-developer Scrum. Weekly sprints, each ending with a working increment and a short demo clip (these clips become raw footage for the final video).

---

## Story Point Scale

| Points | Meaning |
|---|---|
| 1 | Under an hour, no unknowns |
| 2 | Half a day |
| 3 | A full day |
| 5 | 2–3 days, some unknowns |
| 8 | Most of a week, real risk — must be split or de-risked early |

Capacity assumption: ~20 points per weekly sprint (part-time build alongside other commitments). Total plan: ~160 points.

---

# EPICS

## EPIC 1 — Platform Foundation & Environment (Sprint 1)
*Goal: a correctly provisioned UiPath tenant where unattended execution verifiably works — before any business logic exists.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E1-S1 | As the developer, I need to verify tenant licensing supports unattended triggers, DU, Agent Builder, Data Fabric, and Apps | Written checklist of each capability tested with a trivial workflow; any licensing gaps documented with workaround (e.g., manual Start Job fallback for demo) | 3 |
| E1-S2 | As the developer, I need a clean folder structure (`Harborview-Mortgage-Prod`) with an unattended robot correctly allocated | Folder shows robot account with Robot Type = Unattended, role = Automation User; machine template bound; test job runs unattended end to end | 3 |
| E1-S3 | As the developer, I need Integration Service connections (Google Drive or SharePoint intake, email) established and stored as governed connections | Connections authenticated; a trigger fires on file drop into `Mortgage-Inbox`; trigger history shows success | 2 |
| E1-S4 | As the developer, I need a Git repo with the folder structure, README, and CI-free export discipline | Repo public; README (already drafted) committed; export convention documented (project JSONs/XAML exported per sprint) | 2 |
| E1-S5 | As the developer, I need to document every manual provisioning step performed in E1-S2 | A numbered log of every admin click — this becomes the requirements spec for Pillar 2's provisioning automation | 2 |

**Epic 1 total: 12 pts.** Note: E1-S5 is the quiet keystone — Pillar 2 automates exactly this log.

---

## EPIC 2 — Synthetic Mortgage Document Set (Sprint 1–2)
*Goal: realistic, varied test data that exercises every routing path.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E2-S1 | As the developer, I need 6 synthetic borrower profiles spanning the disposition matrix | Profiles defined in a spreadsheet: strong W-2 borrower (auto-clear), thin-file (decline), self-employed (manual review), high-value >$750K (senior review), incomplete package (completeness path), borderline DTI (agent judgment case) | 3 |
| E2-S2 | As the developer, I need filled URLA Form 1003 PDFs for each profile | 6 completed 1003s, visually realistic, fictional PII only | 3 |
| E2-S3 | As the developer, I need supporting documents per profile (W-2s, pay stubs, bank statements, ID) | Each package contains 3–5 supporting docs; at least one package deliberately missing a document | 3 |
| E2-S4 | As the developer, I need packages assembled as multi-document uploads | 6 packages staged; naming convention documented; one "mixed scan" PDF combining several doc types in one file (the classification stress test) | 2 |

**Epic 2 total: 11 pts.**

---

## EPIC 3 — Document Understanding: Classification & Extraction (Sprint 2)
*Goal: every incoming document is identified and its fields extracted with confidence scores.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E3-S1 | As the pipeline, I need a DU taxonomy covering 5 document types (1003, W-2, pay stub, bank statement, ID) | Taxonomy created in DU project; document types defined with target fields per type | 2 |
| E3-S2 | As the pipeline, I need a classifier that splits a mixed package by document type | Mixed-scan test PDF correctly split and typed; classification confidence surfaced per page range | 5 |
| E3-S3 | As the pipeline, I need extractors for the 1003 (9+ fields: borrower, income, loan amount, property, DTI inputs) | Extraction validated on all 6 profiles; project score ≥ 85%; low-confidence fields flagged, not silently accepted | 5 |
| E3-S4 | As the pipeline, I need extractors for W-2 and pay stub income fields | Wages, employer, pay period extracted; results feed the income agent's input schema | 3 |
| E3-S5 | As a reviewer, I need Validation Station wired for low-confidence extractions | Extractions below threshold route to human validation before downstream agents run | 3 |

**Epic 3 total: 18 pts.**

---

## EPIC 4 — Maestro Orchestration & Routing (Sprint 3)
*Goal: the BPMN spine — deterministic state, gates, and queues.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E4-S1 | As the system, I need a Maestro BPMN process modeling the full lifecycle (intake → classify → extract → agents → gateway → disposition) | Process.bpmn committed; every path reachable; variables scoped per stage | 5 |
| E4-S2 | As the system, I need a confidence-gated 4-way gateway (auto-clear / auto-decline / manual review / high-value review) | Rules documented and priority-ordered; each of the 6 test packages lands on its intended path | 5 |
| E4-S3 | As operations, I need 4 Orchestrator queues (Cleared, Declined, Review, HighValue) with transactions carrying full context | Queue items include extraction payload, agent outputs, confidence scores, and audit reference | 3 |
| E4-S4 | As the system, I need failure handling: DU errors, agent timeouts, and malformed packages route to an Exceptions queue, never silently drop | Kill a dependency mid-run in test; item lands in Exceptions with error context | 3 |

**Epic 4 total: 16 pts.**

---

## EPIC 5 — Specialist AI Agents (Sprint 3–4)
*Goal: three Agent Builder agents, each with a narrow contract, structured output, and logged prompts.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E5-S1 | As underwriting, I need an Income Calculation Agent that computes qualifying monthly income from W-2 + pay stub extractions | Structured JSON output (income, method, confidence, caveats); output schema-validated before use; self-employed profile correctly flagged as "cannot auto-calculate" | 5 |
| E5-S2 | As intake, I need a Completeness Agent that checks the package against a required-documents matrix and drafts a customer follow-up | Missing-document package produces an itemized gap list + drafted email placed in review (never auto-sent) | 3 |
| E5-S3 | As compliance, I need a Compliance Agent with hard-veto rules that override any other disposition | Hard vetoes (e.g., ID mismatch, ineligible property type) force manual review regardless of scores; veto reasons persisted | 5 |
| E5-S4 | As governance, I need every agent invocation logged: prompt version, model, input hash, output, latency | Log entries queryable in Data Fabric; prompt register document lists every prompt with version history | 3 |
| E5-S5 | As the system, I need agents orchestrated by Maestro with per-agent timeout and retry policy | Agent failure triggers retry then Exceptions path; no infinite waits | 2 |

**Epic 5 total: 18 pts.**

---

## EPIC 6 — Human-in-the-Loop & SLA Escalation (Sprint 4)
*Goal: no consequential decision without a governed human gate.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E6-S1 | As a reviewer, I need an Action Center task app showing extraction, agent reasoning, and confidence in one screen | Task renders full context; Approve/Decline/Request-Docs actions write back to the BPMN flow | 5 |
| E6-S2 | As a manager, I need SLA timers on review tasks with automatic escalation | Task idle past SLA (demo: 10 min) escalates to senior queue and fires a notification | 5 |
| E6-S3 | As a senior reviewer, I need high-value (> $750K) applications routed to a distinct queue with an enriched task view | High-value test package lands in senior queue; task shows income agent detail and compliance summary | 3 |
| E6-S4 | As compliance, I need every human action recorded (who, what, when, stated reason) | Reviewer decision with reason code persisted to Data Fabric alongside the automated trail | 2 |

**Epic 6 total: 15 pts.**

---

## EPIC 7 — Data Fabric & Operations App (Sprint 4–5)
*Goal: one source of truth and a live window into it.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E7-S1 | As the system, I need a MortgageApplication entity capturing lifecycle state, all decisions, and all scores | Entity schema committed; every pipeline stage writes to it; no state lives only in queue items | 3 |
| E7-S2 | As a loan officer, I need an operations app: live application list, status filters, drill-down to full audit trail | App published in-tenant; all 6 test applications visible with correct states after an end-to-end run | 5 |
| E7-S3 | As a manager, I need summary tiles: volume by disposition, average cycle time, SLA breaches, agent auto-clear rate | Tiles compute from entity data; refresh reflects new runs | 3 |

**Epic 7 total: 11 pts.**

---

## EPIC 8 — Robot Identity Lifecycle Manager (Sprints 5–6)
*Goal: Pillar 2 — automate and govern the provisioning layer, using the Epic 1 manual log as the spec.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E8-S1 | As the developer, I need an authenticated Orchestrator REST API client (external app / OAuth) with least-privilege scopes | Token flow works; scopes documented; credentials stored as Orchestrator assets, never in code | 3 |
| E8-S2 | As an automation admin, I need a provisioning workflow: create robot account → allocate to folder (Automation User role) → bind machine template → verify | One governed request replaces the full manual sequence from the E1-S5 log; run against a fresh test folder succeeds end to end | 8 |
| E8-S3 | As a release manager, I need a pre-flight check workflow that audits any folder for deployment readiness | Checks: unattended robot allocated, machine bound, credentials present, trigger runnable; outputs pass/fail report with the exact missing item named; validated by deliberately breaking a folder | 5 |
| E8-S4 | As IAM/audit, I need a Robot Identity Inventory app: every digital worker, folder access, roles, machine bindings, credential age | App lists identities pulled live via API; sortable; flags credentials older than policy threshold | 5 |
| E8-S5 | As IAM, I need credential rotation tracking with a rotation workflow demo | Rotating a credential asset updates last-rotated metadata; inventory app reflects it; CyberArk noted as the enterprise vault path in docs | 3 |
| E8-S6 | As internal audit, I need an exportable attestation report per robot identity | One-click export (PDF/CSV): identity, access, roles, last rotation, last review date — the access-review artifact | 3 |

**Epic 8 total: 27 pts.** E8-S2 is the riskiest story in the plan — start Sprint 5 with it.

---

## EPIC 9 — Governance Pack & Documentation (Sprint 7)
*Goal: the artifacts that make this read like an enterprise delivery, not a demo.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E9-S1 | Solution Design Document | 8 sections: business context, architecture, component inventory, design decisions, agent contracts, governance model, validation results, known limitations | 5 |
| E9-S2 | Governance pack | Data-flow diagram, model inventory, prompt register, sample audit trail (one application end to end), escalation matrix, adverse-action/fair-lending posture note | 5 |
| E9-S3 | Test evidence pack | All 6 packages run end to end; per-path evidence table (screenshots + entity records); DU project score recorded | 3 |
| E9-S4 | README finalization | Roadmap statuses flipped to ✅; architecture diagram image embedded; quick-start section for reviewers | 2 |

**Epic 9 total: 15 pts.**

---

## EPIC 10 — Demo Video & Release (Sprint 8)
*Goal: a tight, professional walkthrough — the artifact most interviewers will actually consume.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E10-S1 | Record fresh end-to-end runs for all key paths | Clean screen recordings: auto-clear, decline, review + SLA escalation, high-value; plus Pillar 2 provisioning and pre-flight demo | 3 |
| E10-S2 | Record and edit the final video against the script below | ≤ 7 minutes; voiceover; chapter markers; uploaded (YouTube unlisted) and linked in README | 5 |
| E10-S3 | Final repo hardening | Dead links checked, exports current, synthetic-data disclaimer present, license file added | 2 |
| E10-S4 | Send the follow-up email with the live repo + video | Email (already drafted) updated with links and sent to recruiter | 1 |

**Epic 10 total: 11 pts.**

---

# SPRINT PLAN

| Sprint | Week | Sprint Goal | Stories | Pts |
|---|---|---|---|---|
| **1** | 1 | Unattended execution verifiably works; test data underway | E1-S1…S5, E2-S1, E2-S2 | 18 |
| **2** | 2 | Every document type classified and extracted with confidence | E2-S3, E2-S4, E3-S1…S5 | 23 |
| **3** | 3 | BPMN spine routes all 6 packages to correct queues; first agent live | E4-S1…S4, E5-S1 | 21 |
| **4** | 4 | All agents live; HITL with SLA escalation working | E5-S2…S5, E6-S1…S4 | 28 * |
| **5** | 5 | Pillar 1 complete with dashboard; provisioning workflow starts | E7-S1…S3, E8-S1, E8-S2 (start) | 22 |
| **6** | 6 | Robot Identity Manager complete | E8-S2 (finish), E8-S3…S6 | 24 |
| **7** | 7 | Documentation & governance pack complete; full regression run | E9-S1…S4 | 15 |
| **8** | 8 | Demo video shipped; email sent | E10-S1…S4 + buffer | 11 |

\* Sprint 4 is deliberately overloaded — it's the mid-project crunch. Pressure valve: E5-S2 (Completeness Agent) can slip to Sprint 5 without breaking the critical path.

**Standing weekly ritual (every sprint):** 30-minute review — record a 1–2 minute clip of the increment (raw footage bank for Epic 10), update README roadmap statuses, commit exports, write 3-line retro (what worked / what didn't / next risk).

---

# RISK REGISTER

| Risk | Likelihood | Mitigation |
|---|---|---|
| Free/trial tenant blocks unattended triggers or Agent Builder | Medium | E1-S1 tests this in the first two days; fallback = manual Start Job for demo + documented note (worked for Meridian) |
| DU accuracy below 85% on synthetic docs | Medium | Increase training samples per doc type; simplify field set; Validation Station absorbs the gap honestly |
| Orchestrator API scopes unavailable on tenant tier | Medium | E8-S1 tests early in Sprint 5; fallback = provisioning against a personal-workspace folder + full API design documented |
| Sprint 4 overload | High | Pre-identified slip candidate (E5-S2); no new scope enters Sprints 7–8 |
| Scope creep (new agent ideas mid-build) | High | Parking-lot file in repo; nothing added without removing equal points |

---

# DEMO VIDEO SCRIPT (~6:30)

**Format:** screen recording + voiceover. One take per chapter, edited together. Show real runs — no slides except the two title cards.

| Time | Chapter | On screen | Voiceover beats |
|---|---|---|---|
| 0:00–0:25 | Cold open | Title card: project name, your name. Cut to the architecture diagram | "Two problems stall automation programs in banking: document-heavy intake, and the identity layer under the robots themselves. This project takes on both — entirely in UiPath." |
| 0:25–1:15 | The scenario | Drop a full mortgage package into the intake folder; show the trigger firing in Orchestrator | "A complete mortgage package — 1003, W-2s, pay stubs, bank statement. One file drop. Watch what happens." |
| 1:15–2:15 | Classification & extraction | DU splitting the mixed package; extraction results with confidence scores; one low-confidence field hitting Validation Station | "Document Understanding classifies every page, extracts fields with confidence scores — and anything below threshold goes to a human, not into a decision." |
| 2:15–3:15 | Agents & routing | Maestro BPMN view lighting up; Income Agent JSON output; the 4-way gateway routing to a queue | "Three specialist agents — income, completeness, compliance — each with a narrow contract and structured output. Maestro owns the routing; the agents only advise. Compliance carries a hard veto." |
| 3:15–4:05 | Human in the loop | Action Center task with full context; let the SLA timer expire; escalation to senior queue fires | "Nothing consequential ships without a human. Tasks carry SLA timers — this one just breached, and escalated automatically." |
| 4:05–4:35 | Audit & operations | Operations app: live applications, drill into one full audit trail | "Every extraction, every agent call, every human action — one entity, one audit trail, one dashboard." |
| 4:35–5:45 | Pillar 2 | Run pre-flight check against a broken folder → fail report names the missing unattended allocation → run provisioning workflow → re-run pre-flight → pass → trigger executes | "Now the layer underneath. This folder can't run unattended jobs — the pre-flight check says exactly why. One governed provisioning request fixes it: robot account, least-privilege role, machine binding. Re-check: green. This is the difference between a deployment that ships and a week of admin-console archaeology." |
| 5:45–6:10 | Identity governance | Inventory app; credential-age flag; export the attestation report | "Every digital worker, its access, its credential age — and the attestation report an auditor actually asks for." |
| 6:10–6:30 | Close | Title card: repo URL + contact | "Built in eight weeks, documented like a delivery. The SDD, governance pack, and full test evidence are in the repo. Thanks for watching." |

**Recording tips:** 1080p minimum, hide bookmarks bar, use a clean demo browser profile, speed up any wait longer than 5 seconds with a timestamp overlay ("+4 min"), and record voiceover separately from screen capture — it's far easier to edit.

---

# DEFINITION OF DONE (every story)

1. Works end to end on the tenant, not just in Studio
2. Exported and committed to the repo
3. Referenced in the SDD or governance pack where applicable
4. Demo-able in under 2 minutes without setup
