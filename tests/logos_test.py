"""Logos da FAF e da BM nos dois temas. App local em http://localhost:8766.
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<..> CODIGO_EQUIPE=<..> python3 tests/logos_test.py"""
import asyncio, os, json, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}
ADMIN=os.environ['ADMIN_SENHA']; CODIGO=os.environ['CODIGO_EQUIPE']; URL=os.environ.get("APP","http://localhost:8766/index.html")
STUB="if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};}"
res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:120] if d else ""))
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(3000)
BANNER="(()=>{const b=document.querySelector('#areaBanner'); if(!b||b.hidden) return null; const i=b.querySelector('img'); return {classe:b.className, img: !!i && i.complete && i.naturalWidth>0, texto:b.innerText.trim()}})()"
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]; uid=None
    try:
      for tema in ("light","dark"):
        print(f"\n######## tema {tema}")
        ctx=await b.new_context(**dev, color_scheme=tema); await ctx.add_init_script(STUB); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        await entra(pg,"admin",ADMIN)
        await pg.click("#mFr button[data-fr=fed]"); await pg.wait_for_timeout(1200); r=await pg.evaluate(BANNER)
        chk("aba FAF: banner azul com o escudo da FAF (imagem carregada)", r and 'logo-faf' in r['classe'] and r['img'], r)
        g=await pg.evaluate("(()=>{const b=document.querySelector('#areaBanner'), i=b.querySelector('img.abn-emb'); const rb=b.getBoundingClientRect(), ri=i.getBoundingClientRect(); const visivel=[...b.children].filter(e=>!e.classList.contains('abn-sr') && (e.innerText||'').trim()); const sr=b.querySelector('.abn-sr'); return {dx: Math.round((ri.left+ri.right)/2-(rb.left+rb.right)/2), textoVisivel: visivel.length, srEscondido: !sr || sr.getBoundingClientRect().width<=1, altura: Math.round(ri.height)}})()")
        chk("aba FAF: escudo CENTRALIZADO no quadro", abs(g['dx'])<=2, g)
        chk("aba FAF: nenhum nome escrito ao lado (só o escudo)", g['textoVisivel']==0 and g['srEscondido'], g)
        t=await pg.evaluate("(()=>{const tg=document.createElement('span'); tg.className='tag fed'; tg.setAttribute('data-logo','faf'); document.querySelector('#view').append(tg); const ok=getComputedStyle(tg).backgroundImage.includes('faf-emblem.png'); tg.remove(); const reais=[...document.querySelectorAll('#view .tag.fed')]; return {ok, reaisMarcadas: reais.every(x=>x.getAttribute('data-logo')==='faf'), n:reais.length}})()"); chk("etiqueta 'FAF' dos cards leva o escudo (e as etiquetas reais vêm marcadas)", t['ok'] and t['reaisMarcadas'], t)
        await pg.evaluate("(()=>{const a=document.querySelector('.app'); if(a) a.scrollTo(0,0); window.scrollTo(0,0)})()"); await pg.screenshot(path=f"faf_{tema}_fed.png")
        await pg.click("#mFr button[data-fr=asc]"); await pg.wait_for_timeout(1000); r=await pg.evaluate(BANNER)
        chk("aba BM continua com a logo da Prefeitura", r and 'logo-bm' in r['classe'] and r['img'], r['classe'] if r else None)
        await pg.screenshot(path=f"faf_{tema}_bm.png")
        await pg.click("#mFr button[data-fr=all]"); await pg.wait_for_timeout(900); await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(1200); await pg.screenshot(path=f"faf_{tema}_agenda.png")
        chk("sem área escolhida ('Todas'): sem banner", await pg.evaluate("(()=>{const b=document.querySelector('#areaBanner'); return !b || b.hidden})()"))
        await ctx.close()
      print("\n######## ARQUIVO DO ESCUDO")
      import io
      from PIL import Image; import numpy as np
      raw=requests.get(URL.rsplit('/',1)[0]+"/assets/faf-emblem.png").content; A=np.array(Image.open(io.BytesIO(raw)).convert('RGBA')); op=A[:,:,3]>200; pad=np.pad(op,1); viz=pad[:-2,1:-1]&pad[2:,1:-1]&pad[1:-1,:-2]&pad[1:-1,2:]&op; px=A[op&~viz][:,:3].astype(int)
      chk("escudo sem contorno branco (a borda é da cor da logo)", ((px.min(axis=1)>220).mean())<0.02, f"{(px.min(axis=1)>220).mean():.1%} da borda é branca")
      print("\n######## funcionário da FAF")
      requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Func Faf","usuario":"tst.ff","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.ff'")[0]['id']
      sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','fed')")
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); await entra(pg,"tst.ff","SenhaForte123")
      r=await pg.evaluate(BANNER); chk("funcionário da FAF vê o banner com o escudo", r and 'logo-faf' in r['classe'] and r['img'], r)
      chk("e NÃO vê nada da BM (logo da Prefeitura)", await pg.evaluate("!document.querySelector('.abn-logo')"))
      await pg.screenshot(path="faf_func.png")
    finally:
      if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
      print("\nerros de JS:", errs, "| usuários:", sql("select count(*) n from auth.users")[0]['n']); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
