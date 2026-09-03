#!/usr/bin/env python3
"""Static checks for the canvas-app screen YAML.

Catches the classes of damage that a text-level edit can do and that neither
`yaml.safe_load` nor a balance check will notice - notably a doubled '='
prefix, which Studio reports as four unrelated syntax errors.
"""
import yaml, glob, io, re, sys, collections

# Property keys under Properties: that are NOT Power Fx formulas.
NON_FX = {"Control", "Variant", "Layout", "MetadataKey"}
# A formula may not begin with a binary operator or a closing token.
BAD_START = re.compile(r"^=\s*([=*&+,)\]}]|<>|<=|>=)")

def props_of(node):
    """Yield (control_name, prop, value) for every control, recursively."""
    for child in node or []:
        name = list(child.keys())[0]
        body = child[name] or {}
        for k, v in (body.get("Properties") or {}).items():
            yield name, k, v
        for x in props_of(body.get("Children")):
            yield x

def names_of(node, acc):
    for child in node or []:
        name = list(child.keys())[0]
        acc.append(name)
        names_of((child[name] or {}).get("Children"), acc)
    return acc

findings = []
for f in sorted(glob.glob("scr*.yaml")):
    raw = io.open(f, encoding="utf-8").read()

    # 1. raw-text check: a doubled '=' never survives into the parsed value
    for i, line in enumerate(raw.split("\n"), 1):
        if re.match(r"^\s+\w+: ==", line):
            findings.append((f, i, "doubled '=' prefix", line.strip()[:70]))

    doc = yaml.safe_load(raw)
    screen, body = list(doc["Screens"].items())[0]

    # 2. duplicate control names on one screen -> Studio renames on paste
    dupes = [n for n, c in collections.Counter(names_of(body.get("Children"), [])).items() if c > 1]
    for d in dupes:
        findings.append((f, 0, "duplicate control name", d))

    # 3. per-formula checks
    for ctrl, prop, val in props_of(body.get("Children")):
        if prop in NON_FX or not isinstance(val, str):
            continue
        if not val.startswith("="):
            findings.append((f, 0, "value does not start with '='", "%s.%s = %s" % (ctrl, prop, val[:40])))
            continue
        if BAD_START.match(val):
            findings.append((f, 0, "formula starts with an operator", "%s.%s = %s" % (ctrl, prop, val[:50])))
        if val.strip() == "=":
            findings.append((f, 0, "empty formula", "%s.%s" % (ctrl, prop)))
        if val.replace('""', "").count('"') % 2:
            findings.append((f, 0, "unbalanced quotes", "%s.%s" % (ctrl, prop)))
        for o, c in (("(", ")"), ("[", "]"), ("{", "}")):
            if val.count(o) != val.count(c):
                findings.append((f, 0, "unbalanced %s%s" % (o, c), "%s.%s" % (ctrl, prop)))

    # 4. screen properties get the same treatment
    for prop, val in (body.get("Properties") or {}).items():
        if isinstance(val, str) and val.startswith("=") and BAD_START.match(val):
            findings.append((f, 0, "screen formula starts with an operator", prop))

if findings:
    print("%d problem(s):\n" % len(findings))
    for f, line, kind, detail in findings:
        loc = "%s:%d" % (f, line) if line else f
        print("  %-26s %-34s %s" % (loc, kind, detail))
    sys.exit(1)
print("clean: %d screens, no malformed formulas" % len(glob.glob("scr*.yaml")))
