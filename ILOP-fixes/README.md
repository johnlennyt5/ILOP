# ILOP fix scripts

Reference copies of the scripts used to patch `Maestro BPMN/Process.bpmn` in Studio Web.
The project files in this repo come from the Studio Web solution export; these scripts are not needed to run it.

- `fix_bpmn.py`: round 1. Compliance and risk records read the right extractor, disposition rules, queue item content and references, PDF attachment pick.
- `fix2_bpmn.py`: round 2. Rules Risk Score step after the Risk agent, retries on agent and Gmail steps, error boundaries that send failed cases to the Triage queue.
- `risk_rules.js`: the script inside the Rules Risk Score step (same scoring rules as the Risk agent prompt).
- `body_approval.js`, `body_adverse.js`: HTML bodies of the decision emails.
- `test_exprs.py`: syntax check for the `=js:` expressions.
