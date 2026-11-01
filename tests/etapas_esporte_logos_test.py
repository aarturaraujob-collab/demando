"""Fluxo de 5 etapas nos cards, Quadro com 5 colunas, Secretaria de Esporte, logos no resumo do Início. App local em http://localhost:8766.
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<..> python3 tests/etapas_esporte_logos_test.py"""
import asyncio, os, time, json, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; MG={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda q: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=MG, json={"query":q}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=MG).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; ANON=[k['api_key'] for k in keys if k['name']=='anon'][0]
SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE,"Content-Type":"application/json","Prefer":"return=minimal"}
URL=os.environ.get("APP","http://localhost:8766/index.html"); ADMIN=os.environ["ADMIN_SENHA"]; res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:150] if d else ""))
STUB="if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};}"
def hoje(): return sql("select (now() at time zone 'America/Maceio')::date::text d")[0]['d']
def st(i): return sql(f"select status, entregue::text e, arquivada_em is not null a from public.demandas where id='{i}'")[0]
def espera(i, campo, esperado, s=8):
    for _ in range(s*4):
        r=st(i)
        if r[campo]==esperado: return True
        time.sleep(0.25)
    return False
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar, #sideViews", state="attached", timeout=30000); await pg.wait_for_timeout(2800); await pg.evaluate("(()=>{const d=document.getElementById('whoDlg'); if(d && d.open) d.close()})()")
def ins(i, titulo, status="A fazer", entregue=None, prazo=None, por=None, equipe="{}"):
    d={"id":i,"area_id":"asc","titulo":titulo,"status":status,"prazo":prazo,"entregue":entregue,"criado_por":por,"criado_em":"2026-01-01T12:00:00+00:00"}
    return requests.post(f"{BASE}/rest/v1/demandas", headers=SV, json=d)
FLOW="""(t)=>{const r=[...document.querySelectorAll('#view .rw')].find(x=>x.textContent.includes(t)); if(!r) return null; const f=[...r.querySelectorAll('.flow .fs')]; return {n:f.length, cur:f.findIndex(x=>x.classList.contains('cur')), passadas:f.filter(x=>x.classList.contains('past')).length, rotulos:f.map(x=>x.textContent), aria:(r.querySelector('.flow')||{getAttribute:()=>''}).getAttribute('aria-label'), fechada:r.classList.contains('done')}}"""
async def abre_dia(pg):
    await pg.click("#tabbar [data-view=month]"); await pg.wait_for_timeout(900); await pg.click("#view .cell.today"); await pg.wait_for_timeout(700)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]
    adm=sql("select id from public.pessoas where usuario='admin'")[0]['id']; bm=sql("select id from public.pessoas where usuario='bm'")[0]['id']; H=hoje()
    try:
      sql("delete from public.demandas where id like 'tst-%'"); sql("delete from public.lixeira where registro_id like 'tst-%'")
      ins("tst-et1","ETAPAS teste", prazo=H, por=adm)
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); await entra(pg,"admin",ADMIN)
      print("######## FLUXO DE ETAPAS NOS CARDS")
      await abre_dia(pg); f=await pg.evaluate(FLOW,"ETAPAS teste")
      chk("o card já mostra o fluxo inteiro, com a etapa atual destacada (A fazer)", f and f['n']==5 and f['cur']==0 and f['rotulos']==['A fazer','Produção','Ajustes','Entregue','Postada'], f)
      chk("e diz a etapa pra leitor de tela", f and 'A fazer (1 de 5)' in f['aria'], f and f['aria'])
      await pg.screenshot(path="novo_fluxo_afazer.png")
      await pg.click(".rw:has-text('ETAPAS teste') .body"); await pg.wait_for_selector("#detBody .stepper .stp", timeout=8000)
      bt=await pg.evaluate("[...document.querySelectorAll('#detBody .stepper .stp')].map(b=>b.textContent.trim())"); chk("na ficha, as 5 etapas pra escolher", bt==['A fazer','Produção','Ajustes','Entregue','Postada'], bt)
      await pg.click("#detBody .stepper .stp:nth-child(2)"); chk("etapa 'Em produção'", espera("tst-et1","status","Em produção"), st("tst-et1")); await pg.wait_for_timeout(500)
      await pg.keyboard.press("Escape"); await pg.wait_for_timeout(700); f=await pg.evaluate(FLOW,"ETAPAS teste"); chk("o fluxo andou: 'Produção' destacada, 'A fazer' marcada como feita", f['cur']==1 and f['passadas']==1, f)
      await pg.click(".rw:has-text('ETAPAS teste') .body"); await pg.wait_for_selector("#detBody .stepper .stp", timeout=8000)
      await pg.click("#detBody .stepper .stp:nth-child(3)"); chk("etapa 'Ajustes'", espera("tst-et1","status","Ajustes")); await pg.keyboard.press("Escape"); await pg.wait_for_timeout(700)
      f=await pg.evaluate(FLOW,"ETAPAS teste"); chk("'Ajustes' continua em aberto (não vira entregue)", f['cur']==2 and not f['fechada'], f)
      await pg.click(".rw:has-text('ETAPAS teste') .done-b"); chk("o ✓ marca 'Entregue' e grava a data", espera("tst-et1","status","Entregue") and st("tst-et1")['e']==H, st("tst-et1")); await pg.wait_for_timeout(700)
      f=await pg.evaluate(FLOW,"ETAPAS teste"); chk("'Entregue' vira concluída (card esmaecido), 4ª etapa", f['cur']==3 and f['fechada'], f)
      await pg.click(".rw:has-text('ETAPAS teste') .body"); await pg.wait_for_selector("#detBody .stepper .stp"); await pg.click("#detBody .stepper .stp:nth-child(5)"); chk("etapa 'Postada' (banco aceita)", espera("tst-et1","status","Postada")); await pg.keyboard.press("Escape"); await pg.wait_for_timeout(700)
      f=await pg.evaluate(FLOW,"ETAPAS teste"); chk("'Postada': 5ª etapa, concluída, e a data de entrega foi mantida", f['cur']==4 and f['fechada'] and st("tst-et1")['e']==H, f)
      await pg.screenshot(path="novo_fluxo_postada.png")
      await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(900)
      ui=await pg.evaluate("[...document.querySelectorAll('#sum .pane')].map(p=>({s:p.querySelector('.ph b').textContent, k:Object.fromEntries([...p.querySelectorAll('.kpi')].map(k=>[k.querySelector('span').textContent.trim(), k.querySelector('b').textContent.trim()]))}))")
      bmui=[x for x in ui if x['s']=='BM'][0]['k']; esperado=sql(f"select count(*) n from public.demandas where area_id='asc' and status in ('Entregue','Postada') and entregue >= '{H}'::date - 7")[0]['n']
      chk("o resumo da BM conta Entregue + Postada nos últimos 7 dias (igual ao banco)", str(bmui.get('Entregues em 7 dias'))==str(esperado), {"tela":bmui.get('Entregues em 7 dias'),"banco":esperado})
      await pg.click("#tabbar [data-view=board]"); await pg.wait_for_timeout(1000); cols=await pg.evaluate("[...document.querySelectorAll('.lane.asc .col .col-t')].map(c=>c.textContent.trim())"); chk("o Quadro tem as 5 colunas", cols==['A fazer','Em produção','Ajustes','Entregue','Postada'], cols)
      print("\n######## SECRETARIA DE ESPORTE")
      await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(500)
      sec=await pg.evaluate("[...document.querySelector('#secF').options].map(o=>o.textContent)"); chk("no filtro de secretarias aparece 'Esporte'", 'Esporte' in sec, sec[-3:])
      await pg.click(".tab-plus"); await pg.click("#plusMenu .pm-i[data-op=new]"); await pg.wait_for_selector("#dlg[open]"); await pg.wait_for_timeout(400)
      if await pg.locator("#frBtns button:has-text('BM')").count(): await pg.click("#frBtns button:has-text('BM')"); await pg.wait_for_timeout(400)
      sec2=await pg.evaluate("(()=>{const s=document.querySelector('#fSec'); return s? [...s.options].map(o=>o.textContent):[]})()"); chk("no formulário de nova demanda também", 'Esporte' in sec2, sec2[-3:]); await pg.keyboard.press("Escape"); await pg.wait_for_timeout(400)
      print("\n######## LOGOS NO RESUMO DO INÍCIO")
      lg=await pg.evaluate("""[...document.querySelectorAll('#sum .pane')].map(p=>{const b=p.querySelector('.ph b'); return {s:b.textContent, logo:b.getAttribute('data-logo'), img:getComputedStyle(b,'::before').backgroundImage.replace(/url\\(.*\\/(assets\\/[^"')]+)["']?\\)/,'$1')}})""")
      por={x['s']:x for x in lg}
      chk("no cartão da FAF aparece o escudo da FAF", 'faf-emblem' in por['FAF']['img'], por['FAF'])
      chk("no cartão da BM aparece o escudo da BM", 'bm-emblem' in por['BM']['img'], por['BM'])
      chk("o cartão da LIFE continua sem escudo", all('emblem' not in v['img'] for k,v in por.items() if k not in ('FAF','BM')), {k:v['img'] for k,v in por.items()})
      await pg.screenshot(path="novo_resumo.png"); await ctx.close()
    finally:
      sql("delete from public.demandas where id like 'tst-%'"); print("\nerros de JS:", errs, "| restos de teste:", sql("select count(*) n from public.demandas where id like 'tst-%'")[0]['n']); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
