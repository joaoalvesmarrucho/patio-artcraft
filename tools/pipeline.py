#!/usr/bin/env python3
"""Run a Patio plan through pinned, confined official MCP servers; keep a resumable ledger.

Usage: python3 tools/pipeline.py <project> <plan.json> [--dry-run] [--force]
VectorCraft 0.9.0 `run` does not accept automation roots. This runner uses MCP instead.
VectorCraft and PhotoCraft are supported; EffectCraft execution remains unimplemented.
"""
import argparse, datetime, hashlib, json, os, subprocess, sys, time
from pathlib import Path
import xml.etree.ElementTree as ET
import sys as _sys, pathlib as _pl; _sys.path.insert(0, str(_pl.Path(__file__).resolve().parent))
from mcp_session import McpSession

TOOL_HOME = Path(os.environ.get('PATIO_ARTCRAFT_HOME', Path.home()/'.patio-artcraft'))
PINS = Path(__file__).resolve().parent.parent/'pins'
CHECK_EXPORT = Path(__file__).resolve().parent.parent/'skills/patio-vectorcraft/scripts/check_export.py'
DEFAULT_BUDGET = {'secondsPerNode':600, 'secondsTotal':3600, 'attemptsPerNode':2}

def now(): return datetime.datetime.now().astimezone().isoformat(timespec='seconds')
def sha256(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()
def cli_for(app):
    if app not in ('vectorcraft','photocraft'): raise ValueError(f'{app}: no verified pipeline adapter yet')
    pin=json.loads((PINS/f'{app}.lock.json').read_text())
    return TOOL_HOME/app/pin['version']/pin['cliName'],pin

def inside(root, rel, must_be_out=False):
    relative=Path(rel)
    if relative.is_absolute() or '..' in relative.parts: raise ValueError(f'not a project-relative path: {rel}')
    p=root/relative
    # Test the lexical path first: resolve() alone hides symlink components.
    for q in [p,*p.parents]:
        if q==root: break
        if q.is_symlink(): raise ValueError(f'link in project path: {rel}')
    resolved=p.resolve()
    boundary=root/'out' if must_be_out else root
    if boundary not in resolved.parents: raise ValueError(f'path outside {boundary.name}/: {rel}')
    return resolved

def order(nodes):
    ids=[n['id'] for n in nodes]
    if len(set(ids))!=len(ids): raise ValueError('duplicate node ids')
    producers={}
    for n in nodes:
        for output in n.get('outputs',[]):
            if output in producers: raise ValueError(f'duplicate output: {output}')
            producers[output]=n['id']
    by_id={n['id']:n for n in nodes}; done=set(); ordered=[]
    def visit(n,stack=()):
        if n['id'] in done:return
        if n['id'] in stack:raise ValueError(f'cycle at {n["id"]}')
        for source in inputs(n):
            producer=producers.get(source)
            if producer and producer!=n['id']:visit(by_id[producer],stack+(n['id'],))
        done.add(n['id']);ordered.append(n)
    for n in nodes:visit(n)
    return ordered

def inputs(node): return sorted(set(node.get('inputs',[])+([node['open']] if node.get('open') else [])))
def atomic_json(root,relative,data):
    path=inside(root,relative,True); temp=inside(root,relative+'.tmp',True)
    temp.write_text(json.dumps(data,indent=2)+'\n');os.replace(temp,path)

class Ledger:
    def __init__(self,root,plan):
        self.root=root; self.path=inside(root,'out/ledger.json',True); self.running=inside(root,'out/running.json',True)
        self.data=json.loads(self.path.read_text()) if self.path.is_file() else {'schema':'patio-ledger/v2','plan':plan['plan'],'runs':[]}
    def save(self):atomic_json(self.root,'out/ledger.json',self.data)
    def last_ok(self,node):return next((r for r in reversed(self.data['runs']) if r['node']==node and r['status']=='ok'),None)
    def attempts(self,node,key):return sum(r['node']==node and r.get('key')==key and r['status']!='ok' for r in self.data['runs'])
    def begin(self,node):atomic_json(self.root,'out/running.json',{'node':node,'pid':os.getpid(),'started':now()})
    def clear(self):
        if self.running.exists():self.running.unlink()
    def recover(self):
        if not self.running.exists():return
        old=json.loads(self.running.read_text())
        try:os.kill(old['pid'],0)
        except ProcessLookupError:
            self.data['runs'].append({**old,'status':'interrupted'});self.clear();self.save();return
        except PermissionError:pass
        raise RuntimeError('another pipeline may be running; refusing concurrent writes')

def normalize_svg(source,target,width_mm,height_mm):
    """Preserve raw SVG, scale its content into a millimetre viewBox in a separate copy."""
    ns='http://www.w3.org/2000/svg';ET.register_namespace('',ns)
    tree=ET.parse(source);root=tree.getroot();v=list(map(float,root.attrib['viewBox'].replace(',',' ').split()))
    if len(v)!=4 or min(v[2:])<=0 or min(width_mm,height_mm)<=0:raise ValueError('invalid SVG dimensions')
    sx,sy=width_mm/v[2],height_mm/v[3]
    if abs(sx-sy)>1e-5:raise ValueError('SVG aspect ratio differs from the declared millimetre size')
    group=ET.Element('{'+ns+'}g',{'transform':f'scale({sx:.12g} {sy:.12g}) translate({-v[0]:.12g} {-v[1]:.12g})'})
    for child in list(root):root.remove(child);group.append(child)
    root.append(group);root.set('width',f'{width_mm:g}mm');root.set('height',f'{height_mm:g}mm');root.set('viewBox',f'0 0 {width_mm:g} {height_mm:g}')
    target.parent.mkdir(parents=True,exist_ok=True);tree.write(target,encoding='utf-8',xml_declaration=True)

def run_node(root,n,cli,deadline):
    logs=[];checks={};app=n['app']
    def logged(session,tool,args):
        result=session.tool(tool,args);logs.append({'tool':tool,'arguments':args,'result':result});return result
    with McpSession(cli,root,root/'out',deadline) as session:
        open_tool='open_file' if app=='vectorcraft' else 'doc_open'
        if n.get('open'):logged(session,open_tool,{'path':str(inside(root,n['open']))})
        steps=n.get('steps',[])
        tools={x['name'] for x in session.request('tools/list',{}).get('tools',[])}
        if steps and 'command_batch' in tools:
            # One request for the whole node: the official runtimes charge a fixed cost per MCP request,
            # so 480 separate calls take ~0.3 s where one batch takes ~7 ms. Each edit keeps its own undo step.
            batch={'steps':[{'id':s['cmd'],'params':s.get('params',{})} for s in steps],'stop_on_error':True}
            result=session.tool('command_batch',batch)
            logs.append({'tool':'command_batch','arguments':{'steps':len(steps)},'result':result})
            failed=result.get('failed') if isinstance(result,dict) else None
            if failed:raise RuntimeError(f'command_batch stopped at step {failed}: {json.dumps(result)[:400]}')
        else:
            for step in steps:logged(session,'command_run',{'id':step['cmd'],'params':step.get('params',{})})
        for export in n.get('exports',[]):
            path=inside(root,export,True);path.parent.mkdir(parents=True,exist_ok=True)
            options=n.get('exportOptions',{}).get(export,{})
            if app=='vectorcraft':
                tool='save_file' if path.suffix=='.vectorcraft' else 'export'
                args={'path':str(path)}
                if tool=='export':args.update(format=path.suffix[1:],options=options)
            else:tool='doc_save';args={'path':str(path),**options}
            logged(session,tool,args)
        for norm in n.get('normalizeSvg',[]):
            src=inside(root,norm['source'],True);dst=inside(root,norm['target'],True)
            normalize_svg(src,dst,norm['widthMm'],norm['heightMm'])
            logs.append({'operation':'normalize_svg_copy','source':norm['source'],'target':norm['target'],
                         'widthMm':norm['widthMm'],'heightMm':norm['heightMm'],'rawPreserved':True})
        # Reopen through the same confined server, not unrestricted `info`.
        for output in n['outputs']:
            path=inside(root,output,True)
            if not path.is_file():raise RuntimeError(f'missing declared output: {output}')
            opened=logged(session,open_tool,{'path':str(path)})
            inspected=logged(session,'doc_inspect',{})
            checks[output]={'exists':True,'reopens':True,'open':opened,'document':inspected}
            if output in n.get('geometryFiles',[]):
                left=deadline-time.monotonic()
                if left<=0:raise TimeoutError('node budget exhausted before geometry check')
                result=subprocess.run([sys.executable,'-I',str(CHECK_EXPORT),str(path)],capture_output=True,text=True,timeout=min(60,left))
                checks[output].update(geometryOk=result.returncode==0,geometry=result.stdout.strip())
                if result.returncode:raise RuntimeError(f'geometry check failed for {output}: {result.stdout.strip()}')
    return logs,checks

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('project');ap.add_argument('plan');ap.add_argument('--dry-run',action='store_true');ap.add_argument('--force',action='store_true');a=ap.parse_args()
    rawroot=Path(a.project).expanduser()
    if rawroot.is_symlink():raise ValueError('project must not be a symbolic link')
    root=rawroot.resolve();plan=json.loads(Path(a.plan).read_text());budget={**DEFAULT_BUDGET,**plan.get('budget',{})}
    if not(root/'out').is_dir() or (root/'out').is_symlink():raise ValueError('ordinary project out/ folder required; run new-project')
    if any(v<=0 for v in budget.values()):raise ValueError('budgets must be positive')
    ledger=Ledger(root,plan);started=time.monotonic()
    if not a.dry_run:ledger.recover()
    for n in order(plan['nodes']):
        cli,pin=cli_for(n['app'])
        expected=set(n.get('exports',[]))|{v['target'] for v in n.get('normalizeSvg',[])}
        if not n.get('outputs') or not expected.issubset(n['outputs']):raise ValueError('declare all exports and normalized copies in outputs')
        for output in n['outputs']:inside(root,output,True)
        key=hashlib.sha256(json.dumps({'node':n,'revision':plan.get('revision'),'cliSha256':pin['cliSha256'],'runner':{path.name:sha256(path) for path in [Path(__file__), Path(__file__).with_name('mcp_session.py'), CHECK_EXPORT]}},sort_keys=True).encode()).hexdigest()
        hashes={i:sha256(inside(root,i)) for i in inputs(n) if inside(root,i).is_file()}
        if a.dry_run:print(f"[{n['id']}] confined {n['app']} MCP: {len(n.get('steps',[]))} steps -> {', '.join(n['outputs'])}");continue
        missing=set(inputs(n))-hashes.keys()
        if missing:raise ValueError(f'missing inputs: {sorted(missing)}')
        prev=ledger.last_ok(n['id'])
        if prev and not a.force and prev.get('key')==key and prev['inputs']==hashes and set(prev['outputs'])==set(n['outputs']) and all(inside(root,o,True).is_file() and sha256(inside(root,o,True))==h for o,h in prev['outputs'].items()):
            print(f"[{n['id']}] unchanged, skipped");continue
        if ledger.attempts(n['id'],key)>=budget['attemptsPerNode'] and not a.force:raise RuntimeError(f"{n['id']}: attempt limit reached; fix the plan or use --force")
        if not cli.is_file() or sha256(cli)!=pin['cliSha256']:raise RuntimeError(f'{n["app"]} CLI missing or changed; run setup')
        deadline=min(started+budget['secondsTotal'],time.monotonic()+budget['secondsPerNode'])
        if deadline<=time.monotonic():raise TimeoutError('total plan budget exhausted')
        entry={'node':n['id'],'app':n['app'],'transport':'official-mcp','version':pin['version'],'cliSha256':pin['cliSha256'],'key':key,'revision':plan.get('revision'),'inputs':hashes,'started':now()}
        ledger.begin(n['id']);node_started=time.monotonic()
        print(f"[{n['id']}] {n['app']} MCP with project read root and out/ write root",flush=True)
        try:
            logs,checks=run_node(root,n,cli,deadline);entry.update(status='ok',log=logs,checks=checks,outputs={o:sha256(inside(root,o,True)) for o in n['outputs']})
        except Exception as exc:entry.update(status='timeout' if isinstance(exc,TimeoutError) else 'failed',error=str(exc))
        finally:
            entry.update(finished=now(),durationSeconds=round(time.monotonic()-node_started,6));ledger.data['runs'].append(entry);ledger.save();ledger.clear()
        if entry['status']!='ok':raise RuntimeError(f"{n['id']}: {entry['error']}")
        print(f"[{n['id']}] ok; {len(entry['outputs'])} outputs reopened")
    print('done (dry run)' if a.dry_run else f'done; ledger: {ledger.path}')

if __name__=='__main__':
    try:main()
    except (ValueError,RuntimeError,TimeoutError) as exc:sys.exit(str(exc))
