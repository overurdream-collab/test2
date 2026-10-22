#!/usr/bin/env python3
"""Phase 2B static semantic evidence. Never infer RESOLVED solely from previous label.
Consumes existing immutable 1170-match artifact and reads SHA-pinned git file content.
Writes requested review CSV/JSON/MD, keeping every match ID.
"""
import ast,csv,json,collections,re,subprocess,pathlib,sys
SRC=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else "original/matches.csv")
OUT=pathlib.Path(sys.argv[2] if len(sys.argv)>2 else "semantic-evidence");OUT.mkdir(parents=True,exist_ok=True)
rows=list(csv.DictReader(SRC.open(encoding="utf-8")))
assert len(rows)==1170, f"Original corpus mismatch: {len(rows)}"
EXPECTED={"main":255,"pr25":323,"pr28":292,"pr29_baseline":300}
assert dict(collections.Counter(r["ref"] for r in rows))==EXPECTED
CACHE={}
def source(ref,sha,path):
    key=(sha,path)
    if key not in CACHE:
        try: CACHE[key]=subprocess.check_output(["git","show",f"{sha}:{path}"],stderr=subprocess.PIPE).decode("utf-8")
        except (subprocess.CalledProcessError,UnicodeDecodeError): CACHE[key]=None
    return CACHE[key]
def func_node(tree,line):
    nodes=[n for n in ast.walk(tree) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.lineno<=line<=getattr(n,"end_lineno",n.lineno)]
    return min(nodes,key=lambda x:x.end_lineno-x.lineno) if nodes else None
def direct(node):
    if not isinstance(node,ast.Call): return False
    f=node.func
    return isinstance(f,ast.Name) and f.id=="AuditLog"
def desc(path,fn,lines):
    block="\n".join(lines)
    expr=[x.strip() for x in lines if "AuditLog(" in x or "write_event(" in x or "record_outcome_independent(" in x or "audit_writer." in x]
    actions=re.findall(r'action\s*=\s*["\']([^"\']+)["\']',block)
    dyn=bool(re.search(r'action\s*=\s*["\'][^"\']+["\']\s*\+',block))
    tx=re.findall(r'\b(?:db|session|independent)\.(?:flush|commit|rollback)\s*\(',block)
    return actions,dyn,tx,expr
classification=[]
chains={}
filefail=set()
for n,r in enumerate(rows,1):
    ref,sha,path,ln=r["ref"],r["sha"],r["file"],int(r["line"])
    code=source(ref,sha,path)
    mid=f"{ref}:{path}:{ln}:{n}"
    state="UNRESOLVED";why="Requires source-level semantic trace";chain=""
    if code is None:
        filefail.add((ref,path));why="Source file unavailable at pinned SHA"
    else:
        lines=code.splitlines()
        if not 1<=ln<=len(lines) or lines[ln-1].strip()!=r["source"].strip():
            # Original source truncates lines at 240 characters.
            if not 1<=ln<=len(lines) or not lines[ln-1].strip().startswith(r["source"].strip()):
                why="Artifact source line does not match pinned git file"
            else: why="Source line prefix verified, semantic trace pending"
        else: why="Source and pinned line verified"
        if 1<=ln<=len(lines) and lines[ln-1].strip().startswith(r["source"].strip()):
            try: tree=ast.parse(code)
            except SyntaxError: tree=None
            fn=func_node(tree,ln) if tree else None
            fun=fn.name if fn else "<module>"
            start=fn.lineno if fn else ln;end=fn.end_lineno if fn else ln
            body=lines[start-1:end]
            acts,dyn,tx,expr=desc(path,fun,body)
            chain=f"{ref}:{path}:{fun}"
            test=path.startswith("tests/") or path.startswith("test_") or "/test_" in path or path.endswith("conftest.py")
            if test:
                state="RESOLVED_TEST_OR_FIXTURE";why="Source at pinned SHA belongs to test/fixture file; not operational writer"
            elif path.startswith("alembic/") or path.startswith("docs/"):
                state="RESOLVED_REFERENCE_ONLY";why="Migration/declaration reference; not runtime consumer"
            elif fn is None and not re.search(r'\b(?:AuditLog|write_event|record_outcome_independent)\s*\(',lines[ln-1]):
                state="RESOLVED_REFERENCE_ONLY";why="Module import or reference without an executable call at this line"
            elif r["kind"] in ("AuditLog_constructor","write_event","record_outcome_independent") and not lines[ln-1].lstrip().startswith(("def ","async def ")):
                state="RESOLVED_AUDIT_CONSUMER";why=f"Confirmed explicit source audit call in function {fun}; transaction boundaries: {','.join(tx) or 'caller-owned/unknown'}"
            elif r["kind"]=="transaction_boundary" and any(x for x in expr if not x.lstrip().startswith(("def ","async def "))):
                state="RESOLVED_TRANSACTION_OWNER";why=f"Transaction and audit write coexist in same function {fun}; cross-function caller not inferred"
            elif r["kind"] in ("direct_SQL","multiline_SQL"):
                state="UNRESOLVED";why="SQL could touch audit: inspect statement semantics and migration/test context"
            elif r["kind"]=="transaction_boundary":
                # Do not mark unrelated without inspecting transitive helpers.
                state="UNRESOLVED";why="Commit/rollback present, but audit relation cannot be established/ruled out from current function"
            elif r["kind"]=="audit_reference":
                state="RESOLVED_REFERENCE_ONLY" if any(x in lines[ln-1] for x in ("import ","__tablename__","class AuditLog", "# ")) else "UNRESOLVED"
                why="Verified import/declaration/comment" if state!="UNRESOLVED" else "Audit identifier reference needs call path inspection"
    classification.append({**r,"match_id":mid,"final_status":state,"call_chain_id":chain,"source_evidence":f"{sha}:{path}:{ln}","semantic_reason":why,"review_status":"SOURCE_VERIFIED" if state!="UNRESOLVED" else "SOURCE_INSPECTED_UNRESOLVED"})
    if state=="RESOLVED_AUDIT_CONSUMER" and chain:
        chains.setdefault(chain,{"reference":ref,"sha":sha,"path":path,"function":fun,"lines":[],"actions":set(),"tx":set(),"dynamic":False})
        z=chains[chain];z["lines"].append(ln);z["actions"].update(acts);z["tx"].update(tx);z["dynamic"]|=dyn
assert len(classification)==1170
def writecsv(name,records,fields):
    with (OUT/name).open("w",encoding="utf-8",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction="ignore");w.writeheader();w.writerows(records)
writecsv("semantic_match_resolution.csv",classification,list(classification[0]))
matrix=[]
for cid,(key,z) in enumerate(sorted(chains.items()),1):
    kinds=",".join(sorted(z["actions"])) or "dynamic/unknown"
    tx=",".join(sorted(z["tx"])) or "caller-owned/unknown"
    matrix.append({"consumer_id":f"AW-{cid:03d}","reference":z["reference"],"reference_sha":z["sha"],"entry_point":"HTTP/service/CLI: needs external caller validation","file":z["path"],"function":z["function"],"lines":",".join(map(str,sorted(set(z["lines"])))),"call_chain":key,"event_name":kinds,"event_source":"dynamic or not captured" if z["dynamic"] or kinds=="dynamic/unknown" else "literal in function","actor_provenance":"source actor argument, needs authorization confirmation","tenant_provenance":"source actor/session, needs authorization confirmation","business_owner":"session owner, exact entrypoint pending","audit_owner":"function or writer as shown in source","transaction_sequence":tx,"failure_behavior":"caller exception boundaries pending","phase2a_compatibility":"needs field-by-field review","privacy_assessment":"not proved safe","risk":"POTENTIAL","status":"UNRESOLVED" if z["dynamic"] or not z["tx"] else "VERIFIED_FUNCTION_LOCAL","source_evidence":f'{z["sha"]}:{z["path"]}:'+",".join(map(str,sorted(set(z["lines"]))))})
fields=list(matrix[0]) if matrix else ["consumer_id"]
writecsv("audit_consumer_matrix.csv",matrix,fields)
count=collections.Counter(x["final_status"] for x in classification)
summary={"source_artifact_id":12224321555,"source_matches":1170,"processed":len(classification),"resolved":len(classification)-count["UNRESOLVED"],"unresolved":count["UNRESOLVED"],"status_counts":dict(count),"consumer_functions":len(matrix),"verified_function_local":sum(x["status"]=="VERIFIED_FUNCTION_LOCAL" for x in matrix),"source_unavailable_files":sorted([a+":"+b for a,b in filefail]),"counts_by_ref":{ref:dict(collections.Counter(x["final_status"] for x in classification if x["ref"]==ref)) for ref in EXPECTED},"result":"PARTIAL — EXACT UNRESOLVED ITEMS" if count["UNRESOLVED"] else "REQUIRES_INDEPENDENT_REVIEW"}
(OUT/"semantic_closure_summary.json").write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding="utf-8")
with (OUT/"call_path_evidence.md").open("w",encoding="utf-8") as f:
    f.write("# Phase 2B semantic call paths — source-anchored function-level evidence\n\n")
    f.write("This is conservative static source validation. An entry-point marked pending is NOT semantic closure.\n\n")
    f.write("| Ref | SHA | Function | Source audit lines | Commit/rollback tokens in function | Status |\n|---|---|---|---|---|---|\n")
    for row in matrix:
        f.write(f'| {row["reference"]} | `{row["reference_sha"][:12]}` | `{row["file"]}:{row["function"]}` | {row["lines"]} | {row["transaction_sequence"]} | {row["status"]} |\n')
    f.write("\n## Remaining unresolved per source\n")
    unresolved=[x for x in classification if x["final_status"]=="UNRESOLVED"]
    for x in unresolved:
        f.write(f'- `{x["source_evidence"]}` — {x["semantic_reason"]}\n')
print(json.dumps(summary,ensure_ascii=False,indent=2))
