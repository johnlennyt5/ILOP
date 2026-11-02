"""Round 2 fixes on the live Maestro XML (Process.cloud2.bpmn -> Process.fixed2.bpmn).

1. Rules-based risk score: the script task after the Risk agent scores the record in code;
   routing, queues, the review form and the decision log read vars.riskRules.
2. Error handling: retries on agent and Gmail steps, and error boundary events on every
   agent step plus the score step, which send the case to the Triage queue.
"""
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).parent
out = (HERE / "Process.cloud2.bpmn").read_text(encoding="utf-8")


def replace_once(text, old, new, label):
    n = text.count(old)
    if n != 1:
        sys.exit(f"{label}: expected 1 match, found {n}")
    return text.replace(old, new)


def block(text, tag, el_id):
    start = text.index(f'<bpmn:{tag} id="{el_id}"')
    end = text.index(f"</bpmn:{tag}>", start) + len(f"</bpmn:{tag}>")
    return start, end


def bounds(text, el_id):
    m = re.search(r'bpmnElement="' + el_id + r'">\s*<dc:Bounds x="([-\d.]+)" y="([-\d.]+)" width="([-\d.]+)" height="([-\d.]+)"', text)
    return tuple(float(g) for g in m.groups())


ERR_SCHEMA = '{"type":"object","properties":{"code":{"type":"string"},"message":{"type":"string"},"detail":{"type":"string"},"category":{"type":"string"},"status":{"type":"number"},"element":{"type":"string"}}}'
SCRIPT = "Activity_g73GC7"
RISK, GATE = "Activity_tJyTmM", "Gateway_3bdMPw"

# Drop the sample boundary event placed while learning the format.
s, e = block(out, "boundaryEvent", "Event_hNOBdh")
out = out[:s].rstrip(" ") + out[e:].lstrip("\n")
out = re.sub(r'\s*<uipath:inputOutput id="error21"[^\n]*</uipath:inputOutput>', "", out)
out = re.sub(r'\s*<bpmndi:BPMNShape id="S_Event_hNOBdh".*?</bpmndi:BPMNShape>', "", out, flags=re.S)

# 1. Downstream steps read the rules score instead of the agent's numbers.
for old, new in [
    ("vars.riskScore2", "(vars.riskRules || {}).riskScore"),
    ("vars.riskTier2", "(vars.riskRules || {}).riskTier"),
    ("vars.confidence3", "(vars.riskRules || {}).confidence"),
    ("vars.reasoning2", "(vars.riskRules || {}).reasoning"),
]:
    out = out.replace(old, new)

# Script task: name, output variable, script body.
out = replace_once(out, '<uipath:inputOutput id="scriptResponse" name="scriptResponse" type="jsonSchema" elementId="Activity_g73GC7" />',
                   '<uipath:inputOutput id="riskRules" name="scriptResponse" type="jsonSchema" elementId="Activity_g73GC7" />', "script io")
s, e = block(out, "scriptTask", SCRIPT)
script = (HERE / "risk_rules.js").read_text(encoding="utf-8").strip()
new_task = f'''<bpmn:scriptTask id="{SCRIPT}" name="Rules Risk Score" scriptFormat="JavaScript">
      <bpmn:extensionElements>
        <uipath:mapping version="v1">
          <uipath:type value="BPMN.Variables" version="v1" />
          <uipath:context>
            <uipath:inputSchema type="jsonSchema"><![CDATA[{{"$schema":"http://json-schema.org/draft-07/schema#","type":"object","properties":{{"vars":{{"type":"object"}},"metadata":{{"type":"object"}}}},"required":[]}}]]></uipath:inputSchema>
          </uipath:context>
          <uipath:input name="args" type="json" target="bodyField"><![CDATA[{{"vars":"=vars","metadata":"=metadata"}}]]></uipath:input>
          <uipath:output name="scriptResponse" type="jsonSchema" source="=result.response" var="riskRules" />
          <uipath:output name="Error" type="jsonSchema" source="=Error" var="error20" />
        </uipath:mapping>
        <uipath:scriptVersion value="v3" />
      </bpmn:extensionElements>
      <bpmn:incoming>edge_XNnh6d</bpmn:incoming>
      <bpmn:outgoing>edge_rules2gate</bpmn:outgoing>
      <bpmn:script><![CDATA[{script}]]></bpmn:script>
    </bpmn:scriptTask>'''
out = out[:s] + new_task + out[e:]

# Wire Risk agent -> Rules Risk Score -> Disposition Routing.
out = replace_once(out, f'<bpmn:sequenceFlow id="edge_XNnh6d" sourceRef="{RISK}" targetRef="{GATE}" />',
                   f'<bpmn:sequenceFlow id="edge_XNnh6d" sourceRef="{RISK}" targetRef="{SCRIPT}" />\n'
                   f'    <bpmn:sequenceFlow id="edge_rules2gate" sourceRef="{SCRIPT}" targetRef="{GATE}" />', "risk edge")
s, e = block(out, "exclusiveGateway", GATE)
out = out[:s] + replace_once(out[s:e], "<bpmn:incoming>edge_XNnh6d</bpmn:incoming>",
                             "<bpmn:incoming>edge_rules2gate</bpmn:incoming>", "gate incoming") + out[e:]

rx, ry, rw, rh = bounds(out, RISK)
gx, gy, gw, gh = bounds(out, GATE)
sx, sy = rx, ry - 130
out = re.sub(r'(bpmnElement="' + SCRIPT + r'">\s*<dc:Bounds )x="[-\d.]+" y="[-\d.]+"(.*?<dc:Bounds )x="[-\d.]+" y="[-\d.]+"',
             lambda m: f'{m.group(1)}x="{sx:g}" y="{sy:g}"{m.group(2)}x="{sx:g}" y="{sy + 85:g}"', out, count=1, flags=re.S)
out = re.sub(r'(<bpmndi:BPMNEdge id="BPMNEdge_edge_XNnh6d" bpmnElement="edge_XNnh6d">).*?(</bpmndi:BPMNEdge>)',
             lambda m: (f'{m.group(1)}\n        <di:waypoint x="{rx + rw / 2:g}" y="{ry:g}" />\n'
                        f'        <di:waypoint x="{rx + rw / 2:g}" y="{sy + 80:g}" />\n      {m.group(2)}'), out, count=1, flags=re.S)
mid = (rx + rw + gx) / 2
edge_rules_di = (f'      <bpmndi:BPMNEdge id="BPMNEdge_edge_rules2gate" bpmnElement="edge_rules2gate">\n'
                 f'        <di:waypoint x="{sx + 100:g}" y="{sy + 40:g}" />\n'
                 f'        <di:waypoint x="{mid:g}" y="{sy + 40:g}" />\n'
                 f'        <di:waypoint x="{mid:g}" y="{gy + gh / 2:g}" />\n'
                 f'        <di:waypoint x="{gx:g}" y="{gy + gh / 2:g}" />\n'
                 f'      </bpmndi:BPMNEdge>\n')

# 2a. Retries on agent, PDF and Gmail steps.
RETRY = '<uipath:retry maxRetryCount="2" retryBackoff="PT10S" retryAllErrors="true" retryBackoffType="Static" enforceLimits="true" />'
out = re.sub(r'<uipath:retry [^>]*/>', RETRY, out)
for tag, el in [("serviceTask", "Activity_eOmgXO"), ("serviceTask", "Activity_5L3fM4"), ("serviceTask", "Activity_rAbXYV"),
                ("serviceTask", "Activity_6YxUml"), ("serviceTask", "Activity_xjYUvD"), ("sendTask", "Activity_r27CoR"),
                ("sendTask", "Activity_HKelus"), ("sendTask", "Activity_L48CqE"), ("sendTask", "Activity_60rBjn")]:
    s, e = block(out, tag, el)
    b = out[s:e]
    if "<uipath:retry " not in b:
        b = replace_once(b, "\n      </bpmn:extensionElements>", "\n        " + RETRY + "\n      </bpmn:extensionElements>", el + " retry")
    out = out[:s] + b + out[e:]

# 2b. Error boundary events -> Send to Triage (System Error) -> end.
GUARDED = [
    ("Activity_eOmgXO", "errRouter", "Intake Router Agent"),
    ("Activity_rAbXYV", "errLoanExtract", "Loan Extractor Agent"),
    ("Activity_5L3fM4", "errMortgageExtract", "Mortgage Extractor Agent"),
    ("Activity_6YxUml", "errCompliance", "Compliance Check Agent"),
    (RISK, "errRisk", "Risk Assessment Agent"),
    (SCRIPT, "errRules", "Rules Risk Score"),
]
ERR_TASK, ERR_END = "Activity_ErrTriage", "Event_ErrEnd"

ys = [float(y) for y in re.findall(r'<dc:Bounds x="[-\d.]+" y="([-\d.]+)" width="[-\d.]+" height="([-\d.]+)"', out) for y in [y[0]]]
bottom = max(float(m[0]) + float(m[1]) for m in re.findall(r'<dc:Bounds x="[-\d.]+" y="([-\d.]+)" width="[-\d.]+" height="([-\d.]+)"', out))
ex, ey = 700.0, bottom + 120
lane_y = ey - 40

io, procs, flows, shapes, edges = [], [], [], [], []
failed_step = " : ".join(f'vars.{var} ? "{label}"' for _, var, label in GUARDED) + ' : "Unknown"'
err_msg = "(" + " || ".join(f"vars.{var}" for _, var, _ in GUARDED) + " || {})"
for i, (el, var, label) in enumerate(GUARDED):
    bid, fid = f"Event_Err{i}", f"edge_err{i}"
    io.append(f'        <uipath:inputOutput id="{var}" name="Error" type="jsonSchema" elementId="{bid}"><![CDATA[{ERR_SCHEMA}]]></uipath:inputOutput>')
    procs.append(f'''    <bpmn:boundaryEvent id="{bid}" name="{label} failed" attachedToRef="{el}">
      <bpmn:extensionElements>
        <uipath:activity version="v1">
          <uipath:type value="uipath:Activity" version="v1" />
          <uipath:output name="Error" type="jsonSchema" source="=Error" var="{var}" />
        </uipath:activity>
      </bpmn:extensionElements>
      <bpmn:outgoing>{fid}</bpmn:outgoing>
      <bpmn:errorEventDefinition />
    </bpmn:boundaryEvent>''')
    flows.append(f'    <bpmn:sequenceFlow id="{fid}" sourceRef="{bid}" targetRef="{ERR_TASK}" />')
    x, y, w, h = bounds(out, el)
    bx, by = x + w / 2 - 18, y + h - 18
    shapes.append(f'''      <bpmndi:BPMNShape id="S_{bid}" bpmnElement="{bid}">
        <dc:Bounds x="{bx:g}" y="{by:g}" width="36" height="36" />
      </bpmndi:BPMNShape>''')
    lane = lane_y - 6 * i
    edges.append(f'''      <bpmndi:BPMNEdge id="BPMNEdge_{fid}" bpmnElement="{fid}">
        <di:waypoint x="{bx + 18:g}" y="{by + 36:g}" />
        <di:waypoint x="{bx + 18:g}" y="{lane:g}" />
        <di:waypoint x="{ex + 50:g}" y="{lane:g}" />
        <di:waypoint x="{ex + 50:g}" y="{ey:g}" />
      </bpmndi:BPMNEdge>''')

# Error triage queue step copies the Triage-Queue binding of the existing triage step.
s, e = block(out, "sendTask", "Activity_CNCnJ8")
tri = out[s:e]
content = ('=js:({\\n  \\"EmailID\\": vars.response ? vars.response.ID : null,\\n'
           '  \\"FromEmail\\": vars.response ? vars.response.From.Email : null,\\n'
           '  \\"Subject\\": vars.response ? vars.response.Subject : null,\\n'
           '  \\"Category\\": String(vars.category || \\"\\"),\\n'
           '  \\"Disposition\\": \\"SYSTEM_ERROR\\",\\n'
           f'  \\"FailedStep\\": {failed_step.replace(chr(34), chr(92) + chr(34))},\\n'
           f'  \\"ErrorMessage\\": String({err_msg}.message || \\"\\"),\\n'
           f'  \\"ErrorDetail\\": String({err_msg}.detail || \\"\\")\\n}})')
item = ('{"SpecificContent":"' + content + '","DueDate":null,"DeferDate":null,"Priority":"High",'
        '"Reference":"=js:String(vars.response ? vars.response.ID : \\"no-email\\") + \\"-ERR-\\" + Date.now()"}')
err_task = re.sub(r'<uipath:input name="ItemData" type="json" target="body"><!\[CDATA\[.*?\]\]></uipath:input>',
                  lambda m: f'<uipath:input name="ItemData" type="json" target="body"><![CDATA[{item}]]></uipath:input>', tri, flags=re.S)
err_task = (err_task.replace('id="Activity_CNCnJ8" name="Add to Triage Queue (Not Processed)"',
                             f'id="{ERR_TASK}" name="Send to Triage (System Error)"')
            .replace('var="response8"', 'var="responseErrTriage"').replace('var="error9"', 'var="errorErrTriage"'))
err_task = re.sub(r'<bpmn:incoming>.*</bpmn:outgoing>',
                  "\n".join(f"<bpmn:incoming>edge_err{i}</bpmn:incoming>" for i in range(len(GUARDED))) +
                  "\n      <bpmn:outgoing>edge_errEnd</bpmn:outgoing>", err_task, flags=re.S)
procs.append("    " + err_task)
procs.append(f'''    <bpmn:endEvent id="{ERR_END}" name="Failed - Sent to Triage">
      <bpmn:incoming>edge_errEnd</bpmn:incoming>
    </bpmn:endEvent>''')
flows.append(f'    <bpmn:sequenceFlow id="edge_errEnd" sourceRef="{ERR_TASK}" targetRef="{ERR_END}" />')
for src, new in [("response8", "responseErrTriage"), ("error9", "errorErrTriage")]:
    m = re.search(r'<uipath:inputOutput id="' + src + r'" [^\n]*</uipath:inputOutput>', out)
    io.append("        " + m.group(0).replace(f'id="{src}"', f'id="{new}"').replace('elementId="Activity_CNCnJ8"', f'elementId="{ERR_TASK}"'))
shapes.append(f'''      <bpmndi:BPMNShape id="S_{ERR_TASK}" bpmnElement="{ERR_TASK}">
        <dc:Bounds x="{ex:g}" y="{ey:g}" width="100" height="80" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="{ex:g}" y="{ey + 85:g}" width="100" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>
      <bpmndi:BPMNShape id="S_{ERR_END}" bpmnElement="{ERR_END}">
        <dc:Bounds x="{ex + 160:g}" y="{ey + 22:g}" width="36" height="36" />
        <bpmndi:BPMNLabel>
          <dc:Bounds x="{ex + 130:g}" y="{ey + 63:g}" width="96" height="14" />
        </bpmndi:BPMNLabel>
      </bpmndi:BPMNShape>''')
edges.append(f'''      <bpmndi:BPMNEdge id="BPMNEdge_edge_errEnd" bpmnElement="edge_errEnd">
        <di:waypoint x="{ex + 100:g}" y="{ey + 40:g}" />
        <di:waypoint x="{ex + 160:g}" y="{ey + 40:g}" />
      </bpmndi:BPMNEdge>''')

out = replace_once(out, "      </uipath:variables>", "\n".join(io) + "\n      </uipath:variables>", "variables end")
out = replace_once(out, "  </bpmn:process>", "\n".join(procs + flows) + "\n  </bpmn:process>", "process end")
out = replace_once(out, "    </bpmndi:BPMNPlane>", "\n".join(shapes + edges) + "\n" + edge_rules_di + "    </bpmndi:BPMNPlane>", "plane end")

ET.fromstring(out.encode("utf-8"))
(HERE / "Process.fixed2.bpmn").write_text(out, encoding="utf-8", newline="")
print("ok", len(out))
