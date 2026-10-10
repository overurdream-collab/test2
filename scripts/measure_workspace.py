"""Synthetic browser timing and shipped-asset size evidence, not an SLA claim."""
import argparse,json,os,platform
from datetime import datetime,timezone
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--base-url',default='http://127.0.0.1:8000');p.add_argument('--chromium',default=os.getenv('MCIAS_CHROMIUM'));args=p.parse_args()
samples=[]
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path=args.chromium,args=['--no-sandbox'] if args.chromium else [])
 for index in range(3):
  context=b.new_context(viewport={'width':1440,'height':1000});page=context.new_page()
  page.goto(args.base_url+'/institution/dashboard?demo=1');page.wait_for_selector('.kpi');page.evaluate('()=>document.fonts.ready');page.wait_for_timeout(150)
  samples.append(page.evaluate('''()=>({navigation_ms:performance.getEntriesByType('navigation')[0].loadEventEnd,dom_content_loaded_ms:performance.getEntriesByType('navigation')[0].domContentLoadedEventEnd,first_contentful_paint_ms:performance.getEntriesByName('first-contentful-paint')[0]?.startTime??null,resource_count:performance.getEntriesByType('resource').length,resource_encoded_bytes:performance.getEntriesByType('resource').reduce((sum,item)=>sum+item.encodedBodySize,0)})'''))
  context.close()
 version=b.version;b.close()
assets=ROOT/'mcias/web_workspace'
result={'timestamp_utc':datetime.now(timezone.utc).isoformat(),'platform':platform.platform(),'chromium':version,'viewport':[1440,1000],'synthetic_data':True,'not_production_sla_evidence':True,'cold_browser_samples':samples,'asset_bytes':{suffix:sum(f.stat().st_size for f in assets.rglob('*') if f.is_file() and f.suffix==suffix) for suffix in ['.js','.css','.svg','.woff2']}}
output=ROOT/'docs/evidence/workspace-performance.json';output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
