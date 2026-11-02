"""Apply the ILOP review fixes to a copy of the Maestro Process.bpmn.

Reads Process.original.bpmn, writes Process.fixed.bpmn. Every edit is an exact
text replacement that must match once, so nothing else in the file changes.
"""
import json
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent
src = (HERE / "Process.original.bpmn").read_text(encoding="utf-8")
out = src

# Fields the Loan Extractor writes to variables ending in 2.
LOAN_SUFFIXED = {
    "applicantName", "coApplicantName", "applicantEmail", "applicantPhone", "loanPurpose",
    "purchasePrice", "downPayment", "requestedLoanAmount", "requestedTermMonths",
    "grossAnnualIncome", "employer", "jobTitle", "employmentStatus", "yearsEmployed",
    "creditScore", "totalMonthlyDebts", "notes", "missingFields", "extractionConfidence",
    "dateOfBirth", "taxpayerId", "currentAddress",
}
IS_LOAN = 'vars.category == "LOAN"'


def pick(field):
    """Value from whichever extractor ran."""
    if field in LOAN_SUFFIXED:
        return f"({IS_LOAN} ? vars.{field}2 : vars.{field})"
    return f"vars.{field}"


def record(pairs):
    """JSON.stringify of a record; undefined becomes null, real zeros stay zeros."""
    body = ",\n".join(f"  {key}: {expr}" for key, expr in pairs)
    return ("JSON.stringify({\n" + body +
            "\n}, function (k, v) { return v === undefined ? null : v; })")


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit(f"{label}: expected 1 match, found {n}")
    return text.replace(old, new)


def cdata_json(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


# 1. Compliance and Risk records read the loan variables on the LOAN path,
#    keep zeros, and Risk no longer receives marital status.
compliance_fields = [
    "applicantName", "coApplicantName", "applicantEmail", "applicantPhone", "maritalStatus",
    "citizenshipStatus", "loanPurpose", "loanCategory", "itemDescription", "propertyAddress",
    "propertyCity", "propertyState", "propertyZipCode", "propertyType", "occupancyType",
    "estimatedPropertyValue", "currentMortgageBalance", "purchasePrice", "downPayment",
    "requestedLoanAmount", "requestedTermMonths", "grossAnnualIncome", "monthlyIncome",
    "employer", "jobTitle", "employmentStatus", "yearsEmployed", "creditScore",
    "totalMonthlyDebts", "extractionConfidence",
]
compliance = [("productType", "vars.category")] + [(f, pick(f)) for f in compliance_fields] + [
    ("extractorNotes", pick("notes")),
    ("missingFields", pick("missingFields") + " || []"),
    ("dateOfBirth", pick("dateOfBirth")),
    ("taxpayerId", pick("taxpayerId")),
    ("currentAddress", pick("currentAddress")),
]
risk_fields = [
    "applicantName", "applicantEmail", "applicantPhone", "loanPurpose", "loanCategory",
    "itemDescription", "propertyAddress", "propertyState", "propertyType", "occupancyType",
    "estimatedPropertyValue", "currentMortgageBalance", "purchasePrice", "downPayment",
    "requestedLoanAmount", "requestedTermMonths", "grossAnnualIncome", "monthlyIncome",
    "employer", "employmentStatus", "yearsEmployed", "creditScore", "totalMonthlyDebts",
    "extractionConfidence",
]
risk = [("productType", "vars.category")] + [(f, pick(f)) for f in risk_fields] + [
    ("missingFields", pick("missingFields") + " || []"),
    ("complianceStatus", "vars.complianceStatus2"),
    ("vetoCodes", "vars.vetoCodes2 || []"),
    ("flagCodes", "vars.flagCodes2 || []"),
    ("dtiRatio", "vars.dtiRatio2"),
]

m = re.search(r'<!\[CDATA\[(\{"complianceRecord":.*?)\]\]>', out, re.S)
out = replace_once(out, m.group(1), cdata_json({"complianceRecord": "=js:" + record(compliance)}), "compliance record")
m = re.search(r'<!\[CDATA\[(\{"riskRecord":.*?)\]\]>', out, re.S)
out = replace_once(out, m.group(1), cdata_json({"riskRecord": "=js:" + record(risk)}), "risk record")

# 2. Disposition rules: auto-approve also needs the risk agent's own confidence;
#    deny on any veto, even if the codes list comes back empty.
out = replace_once(
    out,
    "=js:vars.complianceStatus2 == \"PASS\" &amp;&amp; vars.riskScore2 &gt;= 70 &amp;&amp; vars.confidence &gt;= 0.75",
    "=js:vars.complianceStatus2 == \"PASS\" &amp;&amp; vars.riskScore2 &gt;= 70 &amp;&amp; vars.confidence3 &gt;= 0.9 &amp;&amp; vars.confidence &gt;= 0.75",
    "auto-approve rule")
out = replace_once(
    out,
    "=js:vars.vetoCodes2.length &gt; 0",
    "=js:vars.complianceStatus2 == \"VETO\" || (vars.vetoCodes2 || []).length &gt; 0",
    "auto-deny rule")


# 3. Turn the two APPROVED branches back on.
def set_condition(text, edge_id, expr):
    pat = re.compile(r'(<bpmn:sequenceFlow id="' + edge_id + r'"[^>]*>\s*<bpmn:conditionExpression[^>]*>)=1 == 2(</bpmn:conditionExpression>)')
    new, n = pat.subn(lambda mm: mm.group(1) + expr + mm.group(2), text)
    if n != 1:
        sys.exit(f"{edge_id}: expected 1 match, found {n}")
    return new


# Human review: approved when the Action Center outcome (mapped to reviewDecision) starts with "Approv".
# Human review approval stays off until the Action Center task is configured and its outcome is mapped.
# Notification: approved when the case went through Auto-Approved or Human-Approved.
out = set_condition(out, "edge_JE8FmZ",
                    "=js:!!((vars.response4 &amp;&amp; vars.response4.Id) || (vars.response7 &amp;&amp; vars.response7.Id))")

# 4. Outcome queue items carry the case data and the Gmail message ID as Reference.
EMPTY_ITEM = '{"SpecificContent":{},"DueDate":null,"DeferDate":null,"Priority":null,"Reference":null}'


def decision_content(disposition, extra=()):
    pairs = [
        ("EmailID", "vars.response.ID"),
        ("FromEmail", "vars.response.From.Email"),
        ("Subject", "vars.response.Subject"),
        ("Product", "vars.category"),
        ("ApplicantName", f"String({pick('applicantName')} || \"\")"),
        ("RequestedAmount", f"Number({pick('requestedLoanAmount')} || 0)"),
        ("ComplianceStatus", "String(vars.complianceStatus2 || \"\")"),
        ("VetoCodes", "(vars.vetoCodes2 || []).join(\", \")"),
        ("FlagCodes", "(vars.flagCodes2 || []).join(\", \")"),
        ("RiskScore", "Number(vars.riskScore2 || 0)"),
        ("RiskTier", "String(vars.riskTier2 || \"\")"),
        ("RiskConfidence", "Number(vars.confidence3 || 0)"),
        ("RouterConfidence", "Number(vars.confidence || 0)"),
        ("Disposition", json.dumps(disposition)),
    ] + list(extra)
    return "=js:({\n" + ",\n".join(f"  {json.dumps(k)}: {v}" for k, v in pairs) + "\n})"


review_extra = [
    ("ComplianceNotes", "String(vars.notes4 || \"\")"),
    ("ComplianceReasoning", "String(vars.reasoning3 || \"\")"),
    ("RiskReasoning", "String(vars.reasoning2 || \"\")"),
]
triage = "=js:({\n" + ",\n".join(f"  {json.dumps(k)}: {v}" for k, v in [
    ("EmailID", "vars.response.ID"),
    ("FromEmail", "vars.response.From.Email"),
    ("Subject", "vars.response.Subject"),
    ("Category", "String(vars.category || \"\")"),
    ("RouterConfidence", "Number(vars.confidence || 0)"),
    ("RouterReasoning", "String(vars.reasoning || \"\")"),
    ("Signals", "(vars.signalsFound || []).join(\", \")"),
]) + "\n})"

queues = {
    "Activity_JOFEik": decision_content("AUTO_DENIED"),
    "Activity_Qjnsuy": decision_content("AUTO_APPROVED"),
    "Activity_VX8tS0": decision_content("HUMAN_REVIEW", review_extra),
    "Activity_8CsSkN": decision_content("HUMAN_APPROVED"),
    "Activity_0lZ4sh": decision_content("HUMAN_DENIED"),
    "Activity_CNCnJ8": triage,
}
for task_id, content in queues.items():
    start = out.index(f'<bpmn:sendTask id="{task_id}"')
    end = out.index("</bpmn:sendTask>", start)
    block = out[start:end]
    item = cdata_json({"SpecificContent": content, "DueDate": None, "DeferDate": None,
                       "Priority": None, "Reference": "=vars.response.ID"})
    if block.count(EMPTY_ITEM) != 1:
        sys.exit(f"{task_id}: empty queue item not found")
    out = out[:start] + block.replace(EMPTY_ITEM, item) + out[end:]

# 5. Download the first PDF attachment, not just the first attachment.
out = replace_once(
    out,
    '{"id":"=js:((vars.response10.Attachments[0].ID))"}',
    cdata_json({"id": "=js:((vars.response10.Attachments.filter(function (a) { "
                      "return /pdf/i.test(a.MIMEType || \"\") || /\\.pdf$/i.test(a.Name || \"\"); "
                      "})[0] || vars.response10.Attachments[0]).ID)"}),
    "attachment pick")

ET.fromstring(out.encode("utf-8"))  # still well-formed XML
(HERE / "Process.fixed.bpmn").write_text(out, encoding="utf-8", newline="")
print("wrote Process.fixed.bpmn", len(src), "->", len(out), "chars")
