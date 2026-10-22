#!/usr/bin/env python3
"""Read-only SHA-pinned audit consumer inventory. Run on a clean git clone.
python scripts/audit_consumer_inventory.py --out audit-inventory
Produces full-file manifest, AST matches, risk call chains, SHA manifest and summaries.
"""
import argparse
import ast
import csv
import json
import pathlib
import re
import subprocess
from collections import Counter

REFS = {
    "main": "b69defa2f621458ef44d790b510840307a81009a",
    "pr25": "a9d23ddcf4b34e5fced4dd6ef50dcee308ee1fc1",
    "pr28": "65bbddc1ae95aed22e157774f600a296a6e43926",
    "pr29_baseline": "f9a0d126f33e8749e333166a2fc6c8d3a176dfc1",
}
TOKENS = re.compile(r"AuditLog|write_event|record_outcome_independent|audit_log|audit_writer|audit_event|audit_denial|commit\s*\(|rollback\s*\(|INSERT\s+INTO\s+audit|UPDATE\s+audit|DELETE\s+FROM\s+audit", re.I)
TARGETS = {"AuditLog", "write_event", "record_outcome_independent"}
SQL = re.compile(r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|SELECT\s+.+?FROM)\s+(?:[\w.]+\.)?audit(?:_log)?\b", re.I | re.S)

def git(*args):
    return subprocess.check_output(["git", *args], stderr=subprocess.PIPE)

def enclosing(tree, number):
    if tree is None:
        return "<parse_failed>"
    found = [n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.lineno <= number <= getattr(n,"end_lineno", n.lineno)]
    return min(found, key=lambda n: n.end_lineno-n.lineno).name if found else "<module>"

def scan(ref, sha):
    entries = git("ls-tree", "-r", "--name-only", sha).decode().splitlines()
    paths = [p for p in entries if p.endswith(".py")]
    manifest, hits = [], []
    for path in paths:
        row = {"ref":ref, "sha":sha, "file":path, "status":"ok", "matches":0}
        try:
            source = git("show", f"{sha}:{path}").decode("utf-8")
            try:
                tree = ast.parse(source,filename=path)
            except SyntaxError as exc:
                tree = None
                row["status"] = f"AST_ERROR:{exc.lineno}"
            for number, line in enumerate(source.splitlines(),1):
                if not TOKENS.search(line): continue
                kind = "token"
                if re.search(r"\bAuditLog\s*\(",line): kind="AuditLog_constructor"
                elif re.search(r"\bwrite_event\s*\(",line): kind="write_event"
                elif re.search(r"\brecord_outcome_independent\s*\(",line): kind="record_outcome_independent"
                elif re.search(r"\b(?:commit|rollback)\s*\(",line): kind="transaction_boundary"
                elif SQL.search(line): kind="direct_SQL"
                elif re.search("audit",line,re.I): kind="audit_reference"
                hits.append({"ref":ref,"sha":sha,"file":path,"function":enclosing(tree,number),"line":number,"kind":kind,"source":line.strip()[:240]})
                row["matches"] += 1
            # Find multiline SQL literal operations, not only single-line SQL matches.
            if tree is not None:
                for node in ast.walk(tree):
                    if isinstance(node,ast.Constant) and isinstance(node.value,str) and SQL.search(node.value):
                        hits.append({"ref":ref,"sha":sha,"file":path,"function":enclosing(tree,node.lineno),"line":node.lineno,"kind":"multiline_SQL","source":node.value[:240].replace("\n"," ")})
                        row["matches"] += 1
        except (UnicodeError, subprocess.CalledProcessError, OSError) as exc:
            row["status"] = "READ_ERROR:" + type(exc).__name__
        manifest.append(row)
    return manifest,hits

def main():
    p=argparse.ArgumentParser();p.add_argument("--out",default="audit-inventory")
    args=p.parse_args(); out=pathlib.Path(args.out);out.mkdir(parents=True,exist_ok=True)
    manifest=[];hits=[]
    for ref,sha in REFS.items():
        # Verify complete objects and pin SHA, never resolve moving refs.
        assert git("rev-parse",sha).decode().strip() == sha, f"SHA unavailable {ref}"
        a,b=scan(ref,sha);manifest+=a;hits+=b
    for filename,rows,fields in [
        ("files.csv",manifest,["ref","sha","file","status","matches"]),
        ("matches.csv",hits,["ref","sha","file","function","line","kind","source"])]:
        with (out/filename).open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    summary={}
    for ref,sha in REFS.items():
        a=[x for x in manifest if x["ref"]==ref];b=[x for x in hits if x["ref"]==ref]
        summary[ref]={"sha":sha,"total":len(a),"read_ok":sum(x["status"]=="ok" for x in a),
                      "failures":[{"file":x["file"],"status":x["status"]} for x in a if x["status"]!="ok"],
                      "hits":len(b),"positive_files":len({x["file"] for x in b}),
                      "kinds":dict(Counter(x["kind"] for x in b))}
    (out/"summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
    with (out/"SUMMARY.md").open("w",encoding="utf-8") as f:
        f.write("# SHA-pinned audit consumer inventory\n\n")
        f.write("Static token/AST survey only; human semantic review remains mandatory.\n\n")
        for ref,s in summary.items():
            f.write(f"## {ref} — {s['sha']}\nFiles: {s['total']}, read OK: {s['read_ok']}, unresolved: {len(s['failures'])}, hits: {s['hits']}, positive files: {s['positive_files']}\n\n")
    print(json.dumps(summary,ensure_ascii=False,indent=2))
    if any(s["failures"] for s in summary.values()):
        raise SystemExit("FAIL CLOSED: some Python files could not be parsed/read")

if __name__=="__main__": main()
