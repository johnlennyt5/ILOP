import json, re, sys, subprocess, html
import xml.etree.ElementTree as ET
def exprs(path):
    root = ET.parse(path).getroot()
    found = {}
    for e in root.iter():
        tag = e.tag.split('}')[1]
        if tag == "conditionExpression" and (e.text or "").startswith("=js:"):
            found["cond:" + e.text[:40]] = e.text[4:]
        if tag == "input" and e.text and e.text.strip().startswith("{") and "=js:" in e.text:
            for k, v in json.loads(e.text).items():
                if isinstance(v, str) and v.startswith("=js:"):
                    owner = e.get("name")
                    found[f"{owner}.{k}#{len(found)}"] = v[4:]
    return found
fixed = exprs("Process.fixed.bpmn"); orig = exprs("Process.original.bpmn")
json.dump({"fixed": fixed, "orig": orig}, open("exprs.json", "w"))
print(len(fixed), "fixed expressions,", len(orig), "original")
