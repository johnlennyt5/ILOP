# Implementation Plan — Harborview Lending Intake & Robot Identity Governance

**Author:** Johnlenny Tejada
**Plan date:** July 14, 2026 · replaces v1 (archived)
**Status:** Sprint 1 complete. BPMN diagram complete end to end. Current work: node-by-node wiring, front of pipeline first.
**Platform:** UiPath — Maestro (BPMN), Agent Builder, Document Understanding, Action Center, Orchestrator, Data Fabric, Apps, Integration Service (Gmail)

---

## Why this plan

The project pivoted from the original mortgage-only, file-drop design to a stronger architecture built in Sprint 1: **email-driven intake with an AI router feeding two parallel product pipelines (loans and mortgages)** that converge on a shared compliance → risk → disposition → notification backbone. This plan matches the BPMN as actually built and re-sequences all remaining work around it.

**Build principle for everything below: wire the pipeline front-to-back, one node at a time, testing each node before moving to the next.** The diagram is the map; every sprint makes a contiguous stretch of it real.

---

## ✅ Completed (Sprint 1, Week 1)

| Item | Evidence |
|---|---|
| Tenant verified: unattended execution, Agent Builder, Maestro, Integration Service | Smoke test job ran unattended |
| Folder `Harborview-Mortgage-Prod` with unattended robot (Automation User role) + machine binding | Manage Access + Jobs history |
| Gmail connection + `EMAIL_RECEIVED` trigger (polling, INBOX) | Trigger fires on inbound mail |
| Queues created: `Intake-Raw`, `Loan-Queue`, `Mortgage-Queue`, `Auto-Approved`, `Auto-Denied`, `Human-Review`, `Triage`, `Exceptions` | Orchestrator Queues view |
| **Full BPMN diagram, end to end** — dual-pipeline routing, OTHER/triage default exit, 3-way disposition, Action Center user task, human disposition, notification split (agent vs. template), merge → log → single end | `Process.bpmn` in repo + architecture image |
| Provisioning log started (`/docs/provisioning-log.md`) — every manual admin action recorded | The living spec for Pillar 2 |
| Repo live: README (aligned), BPMN, `.ius` solution package, diagram image | GitHub |

Validation issues remaining in Studio (~12) are the expected unwired conditions/agents — they are the to-do list this plan burns down.

---

## The Wiring Map

Node numbers below refer to the diagram, front to back. Each epic owns a contiguous stretch.

```
[1] Email trigger → [2] Email Queue task → [3] Intake Router Agent → [4] Document Type Routing
→ [5a] Extract Loan Details / [5b] Extract Mortgage Details / [5c] Triage exit
→ [6] Unified Pipeline merge → [7] Compliance Check Agent → [8] Risk Assessment Agent
→ [9] Disposition Routing → [10a/b] Auto queues / [10c] Human-Review queue
→ [11] Human Review (Action Center) → [12] Human Disposition Routing → [13] Notification Routing
→ [14a] Approval Email Agent / [14b] Adverse-Action Template → [15] Log Final Record → [16] End
```

---

# EPICS

## EPIC A — Front of Pipeline: Intake, Router, Routing (nodes 2–5c) — *current sprint*

*Goal: a loan email, a mortgage email, and a junk email each land in the correct queue with an auditable agent decision.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| A1 | Wire `Email Queue` task as **Add Queue Item → `Intake-Raw`** | Reference = Gmail Message ID from trigger response; SpecificContent carries From.Email, Subject, HasAttachments, ThreadID, attachment names; duplicate delivery of same message is rejected by unique reference (verify by re-sending) | 3 |
| A2 | Build **Intake Router Agent** in Agent Builder | Input: single string `intakePayload` (JSON envelope). Output schema enforced: `{category: LOAN\|MORTGAGE\|OTHER, confidence: 0–1, reasoning, signalsFound[]}`. System prompt: classify only from envelope content; conflicting/absent signals → OTHER low-confidence; never guess. Published to folder | 5 |
| A3 | Map trigger output → envelope and wire agent input (MVP: no attachments yet) | Envelope built from Subject + Body + From + attachment names via expression; agent binding points at published agent (placeholder replaced); agent returns parseable JSON for 5 test emails | 3 |
| A4 | Wire **Document Type Routing** conditions | MORTGAGE edge: `category=="MORTGAGE" && confidence>=0.8`; LOAN edge: same for LOAN; default flow (slash) → Triage. Low-confidence LOAN/MORTGAGE goes to Triage for now (until Human Review is wired, then revisit) — documented as interim rule | 3 |
| A5 | Wire `Add to Triage Queue` task + `Not Applicable` end | Junk email ends cleanly with a Triage queue item; no stuck instances | 2 |
| A6 | **Front-of-pipeline test matrix** | 6 emails run live: clear loan, clear mortgage, junk/newsletter, ambiguous ("need money for a house project"), empty body, duplicate resend. Each lands per expectation; results table screenshotted for test evidence pack | 3 |

**Epic A: 19 pts.** Exit criterion: the pink path in Studio debug reaches the correct branch for all six test emails.

## EPIC B — Format-Flexible Intake: Attachment Normalization (feeds node 3)

*Goal: PDF, CSV, and JSON attachments become text inside the same envelope — agents never see raw files.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| B1 | Download attachments via Gmail Integration Service activity | Attachment files retrieved by ID from trigger metadata; skipped gracefully when none | 3 |
| B2 | Route by MIMEType | PDF → B3 path; text/csv and application/json → B4 path; unknown types logged and skipped with note in envelope | 2 |
| B3 | PDF text extraction (Document Understanding) | Extracted text appended to envelope `attachments[].extractedText`; scanned-image PDF degrades gracefully (empty text + flag) | 5 |
| B4 | CSV/JSON ingestion with size guard | CSV truncated to first 50 rows as text; JSON pretty-printed; per-attachment cap (~10k chars) so envelope can't blow agent context | 3 |
| B5 | Regression: attachment-bearing test emails | Loan CSV, mortgage PDF, JSON payload emails all classify correctly; envelope inspected in debug for correct structure | 3 |

**Epic B: 16 pts.**

## EPIC C — Product Extraction Stages (nodes 5a/5b) + Shared Data Contract

*Goal: each branch produces the same-shaped `applicationRecord` so everything downstream is product-agnostic.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| C1 | Define the shared **applicationRecord** contract | One JSON schema: applicant, product (LOAN/MORTGAGE), amounts, income, term/property fields (nullable per product), sourceMessageId, extraction confidences. Committed to `/docs` — this is the variable every downstream node reads | 3 |
| C2 | Wire **Extract Loan Details** | Populates applicationRecord from envelope (income, requested amount, term, purpose); missing fields null + flagged, never invented | 5 |
| C3 | Wire **Extract Mortgage Details** | Same contract; adds property, loan amount, 1003-style fields when a 1003 PDF is present (uses B3 text) | 5 |
| C4 | Unified Pipeline merge verified | Both branches arrive at node 6 with valid applicationRecord; schema-validate before Compliance | 2 |

**Epic C: 15 pts.**

## EPIC D — Compliance, Risk & Disposition (nodes 7–10)

*Goal: three-way disposition driven by scored, veto-aware logic; ambiguity always defaults to review.*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| D1 | Build **Compliance Check Agent** | Output: `{complianceStatus: PASS\|VETO\|FLAG, reasonCodes[], reasoning}`. Reason codes from a fixed enum committed to `/docs/reason-codes.md` (this table later drives adverse-action templates). VETO can never route to auto-approve — encoded in gateway conditions, not just prompt | 5 |
| D2 | Build **Risk Assessment Agent** | Output: `{riskScore: 0–100, confidence, factors[], reasonCodes[]}`; deterministic inputs only (applicationRecord); prompt versioned in prompt register | 5 |
| D3 | Wire **Disposition Routing** | auto-approve: `PASS && riskScore>=70 && confidence>=0.8`; auto-deny: `VETO \|\| riskScore<30` (with confidence floor); default flow → Human-Review. Thresholds stored as Orchestrator assets, not hardcoded — one-line change to retune | 3 |
| D4 | Wire the three queue tasks (nodes 10a–c) | Queue items carry full applicationRecord + agent outputs + reasonCodes; `finalDecision` set to APPROVED/DECLINED on the auto paths | 3 |
| D5 | Revisit A4 interim rule | Low-confidence router results now route to Human-Review instead of Triage; test matrix re-run | 2 |

**Epic D: 18 pts.**

## EPIC E — Human in the Loop (nodes 11–12)

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| E1 | Build the Action Center **review task form** | Shows applicant summary, product, extracted fields, both agents' reasoning + reason codes, confidence; actions: Approve / Decline (+ required reason-code pick on decline) | 5 |
| E2 | Wire the **User Task** suspension | Process suspends at node 11; task appears in Action Center; completing it resumes the flow with `finalDecision` set to the same APPROVED/DECLINED values as auto paths | 5 |
| E3 | Wire Human Disposition Routing + Human-Approved/Denied tasks | Both edges labeled and conditioned on finalDecision; human decisions downstream-identical to auto decisions | 2 |
| E4 | **SLA timer + escalation** (boundary timer on node 11) | Task idle past SLA (demo: 10 min, asset-configurable) fires escalation: item flagged/reassigned + notification; demoable on camera | 5 |

**Epic E: 17 pts.**

## EPIC F — Notification Stage (nodes 13–14)

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| F1 | Build **Approval Email Composer** agent | Input: applicationRecord + decision context; output: subject + body; warm, personalized, next steps; sent via Gmail connection to the original sender | 5 |
| F2 | Build the **adverse-action template engine** (NOT an agent) | Reason-code → pre-approved sentence lookup (from D1's enum); template merge fills applicant/product/reasons; every sentence pre-exists in the committed table; unit-tested per reason code | 5 |
| F3 | Wire Notification Routing conditions + both send tasks | `finalDecision=="APPROVED"` → agent path; `=="DECLINED"` → template path; all four upstream routes verified to arrive correctly | 3 |
| F4 | (Stretch) Compliance-checker agent on denial output | Agent validates the *finished* template email (reasons stated, nothing extra) YES/NO — checker, never writer. Documented in SDD either way | 3 |

**Epic F: 16 pts.**

## EPIC G — Audit Record & Operations App (node 15)

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| G1 | Data Fabric entity `LendingApplication` | Full lifecycle per application: envelope ref, router result, extraction, compliance, risk, disposition path (auto vs. human + reviewer), notification sent, timestamps | 3 |
| G2 | Wire **Log Final Record** task | One entity record per completed instance; Triage exits also logged (separate status) so nothing is invisible | 3 |
| G3 | **Operations app** | Live application list, status filters, drill-down to full audit trail; tiles: volume by disposition, auto-clear rate, SLA breaches | 5 |

**Epic G: 11 pts.**

## EPIC H — Exceptions & Hardening

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| H1 | Boundary error events on all four agent tasks → Exceptions queue | Kill/timeout an agent in test; item lands in Exceptions with error context; instance ends cleanly | 5 |
| H2 | Timeout + retry policy per agent task | Documented values; no infinite waits anywhere in the flow | 2 |

**Epic H: 7 pts.**

## EPIC I — Pillar 2: Robot Identity Lifecycle Manager

*Unchanged in scope from v1; requirements now grounded in the real provisioning log. Add queue creation to the provisioning scope (the tool stands up robot + machine + queues).*

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| I1 | Orchestrator REST API client (external app, OAuth, least-privilege scopes) | Token flow works; scopes documented; secrets in credential assets | 3 |
| I2 | **Provisioning workflow** — robot account → folder allocation (Automation User) → machine binding → queue set → verify | Replays the provisioning log against a fresh test folder in one governed run | 8 |
| I3 | **Pre-flight check** — folder deployment-readiness audit | Detects and names the exact missing item (validated by deliberately breaking a folder); pass/fail report | 5 |
| I4 | **Identity inventory app** | All digital workers: folder access, roles, machines, credential age; stale-credential flag | 5 |
| I5 | Credential rotation tracking + demo | Rotation updates metadata; inventory reflects it; CyberArk documented as enterprise path | 3 |
| I6 | Attestation report export | Per-identity access-review packet (PDF/CSV) | 3 |

**Epic I: 27 pts.** I2 remains the riskiest story in the plan — it opens its sprint.

## EPIC J — Governance Pack, SDD & Test Evidence

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| J1 | SDD | Architecture, the v1→v2 pivot rationale, agent contracts, veto precedence, adverse-action design, known limitations | 5 |
| J2 | Governance pack | Prompt register (all four agents, versioned), reason-code table, escalation matrix, sample end-to-end audit trail, adverse-action posture note | 5 |
| J3 | Full regression + test evidence pack | Entire A6/B5/D-matrix re-run on the finished pipeline; per-path evidence table with screenshots | 3 |
| J4 | README/roadmap finalization | Statuses flipped; diagram image current; quick-start for reviewers | 2 |

**Epic J: 15 pts.**

## EPIC K — Demo Video & Release

| ID | Story | Acceptance Criteria | Pts |
|---|---|---|---|
| K1 | Record fresh runs of every demo beat (script below) | Clean captures: loan auto-approve, mortgage → human review → SLA escalation, auto-deny + adverse-action email, junk email triage, Pillar 2 broken-folder→provision→pass sequence | 3 |
| K2 | Edit final video ≤ 7 min, voiceover, chapters; upload + link in README | Done = watchable by a stranger with zero context | 5 |
| K3 | Final repo hardening + send follow-up email with links | Dead links checked; synthetic-data disclaimer; email (drafted) sent to recruiter | 2 |

**Epic K: 10 pts.**

---

# SPRINT PLAN (remaining 7 weeks)

| Sprint | Week | Sprint Goal | Epics/Stories | Pts |
|---|---|---|---|---|
| **2** *(current)* | 2 | Front of pipeline live: 3 email types → 3 correct destinations | Epic A (all) | 19 |
| **3** | 3 | Attachments normalized; both extraction branches emit the shared contract | Epic B + C1–C2 | 24 |
| **4** | 4 | Full auto path live: email → agents → auto queues, `finalDecision` set | C3–C4, Epic D | 25 |
| **5** | 5 | Human loop + notifications: review task, SLA escalation, both email types sending | Epic E + F1–F3 | 25 * |
| **6** | 6 | Audit record + app; exceptions hardened; Pillar 2 API + provisioning core | Epic G, H, I1–I2 | 29 ** |
| **7** | 7 | Pillar 2 complete; governance pack + SDD + regression | I3–I6, Epic J | 31 ** |
| **8** | 8 | Demo video shipped; email sent | Epic K + F4 stretch + buffer | 13 |

\* Sprint 5 pressure valve: E4 (SLA escalation) slips to Sprint 6 if needed — it bolts onto an existing node.
\** Sprints 6–7 are heavy. Pre-decided cuts, in order: G3 tiles reduced to list-only app; I5 demo simplified to metadata-only; F4 dropped. **Pillar 2 stories I2–I4 and the governance pack are never cut** — they're the differentiators.

**Standing weekly ritual (unchanged):** 30-min review — record a 1–2 min clip of the increment (footage bank for the video), re-export `Process.bpmn` + commit, update README statuses, 3-line retro.

---

# RISK REGISTER (v2)

| Risk | Likelihood | Mitigation |
|---|---|---|
| Agent output arrives wrapped in prose/markdown instead of clean JSON | High | Enforce output schema in Agent Builder; strip-and-parse guard at every gateway; test in A3 before anything depends on it |
| Gmail polling trigger re-fires on same message | Medium | Already mitigated: Intake-Raw unique reference = Message ID (verified in A1/A6) |
| Action Center user task suspension behaves differently than expected in Maestro | Medium | E2 scheduled early in its sprint; fallback = queue-based manual review with documented note |
| Orchestrator API scopes unavailable on tenant tier | Medium | I1 opens Sprint 6; fallback = personal-workspace demo + full API design documented |
| Sprints 6–7 overload | High | Pre-decided cut list above; no new scope after Sprint 5 |
| Scope creep (new agent ideas) | High | Parking-lot file; nothing added without removing equal points |

---

# DEMO VIDEO SCRIPT v2 (~6:45)

| Time | Chapter | On screen | Beats |
|---|---|---|---|
| 0:00–0:25 | Cold open | Title card → the BPMN full canvas | "Loan and mortgage requests arrive by email in every format imaginable. And underneath every automation is an identity layer that can silently block deployment. This project takes on both — entirely in UiPath." |
| 0:25–1:10 | The front door | Send a real email ("I'd like to refinance my home") → trigger fires → Intake-Raw queue item appears | "Every message is on the audit record before any AI touches it. Duplicates bounce off the Message ID." |
| 1:10–2:00 | The router | Agent output JSON on screen → Document Type Routing → mortgage branch lights up. Then send a newsletter → Triage exit | "One classifier, strict schema, never guesses — and junk mail exits gracefully instead of jamming the pipeline." |
| 2:00–2:50 | Dual pipeline + agents | Loan email with CSV attachment → normalized envelope in debug → extraction → compliance PASS → risk score → auto-approve queue | "Loans and mortgages are separate products on a shared governance backbone. Formats vary; the agent contract never does." |
| 2:50–3:50 | Human loop | Borderline mortgage → Human-Review → Action Center task with both agents' reasoning → let SLA breach → escalation fires → reviewer approves | "Ambiguity never auto-disposes — it defaults to a person. And a person who doesn't act triggers escalation." |
| 3:50–4:30 | The two emails | Approval email (agent-drafted, personalized) vs. adverse-action email (template) side by side + the reason-code table | "The denial is the one message regulation cares about — so no LLM writes it. Deterministic reason codes, pre-approved language. Knowing where *not* to put AI is the design." |
| 4:30–5:00 | Audit | Operations app: the day's applications, drill into one full trail | "Every decision — machine or human — one record, one trail." |
| 5:00–6:10 | Pillar 2 | Pre-flight check on broken folder → names the missing unattended allocation → provisioning workflow → re-check green → trigger runs. Inventory app + attestation export | "This failure blocks real deployments and the reason is invisible to most developers. One governed request fixes it — and every digital worker is inventoried, rotated, attestable." |
| 6:10–6:45 | Close | Title card: repo URL + contact | "Eight weeks, documented like a delivery. SDD, governance pack, and full test evidence in the repo." |

---

# DEFINITION OF DONE (every story)

1. Works end to end on the tenant, not just in the designer
2. `Process.bpmn` re-exported and committed with the change
3. Referenced in SDD / governance pack where applicable
4. Demo-able in under 2 minutes without setup