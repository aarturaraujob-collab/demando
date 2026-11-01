"""Barra de baixo: sem Agenda, + em destaque no meio com 3 opções; admin, funcionário (5 abas, com Minhas), leitor e desktop. App local em http://localhost:8766.
Uso: SB=<token> CODIGO_EQUIPE=<código> ADMIN_SENHA=<..> python3 tests/barra_test.py"""
import asyncio, os, json, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}
URL=os.environ.get("APP","http://localhost:8766/index.html"); CODIGO=os.environ['CODIGO_EQUIPE']
CRED={"admin":os.environ['ADMIN_SENHA']}; res=[]
def cria_func(usuario):   # conta descartável: os testes nunca mexem nas contas bm e faf
    r=requests.post(f"{BASE}/auth/v1/admin/users", headers=SV, json={"email":f"demandasbm+{usuario}@gmail.com","password":"SenhaForte123","email_confirm":True,"user_metadata":{"nome":"Teste Barra","usuario":usuario}}); u=r.json()['id']
    sql(f"update public.pessoas set papel='membro' where id='{u}'"); sql(f"insert into public.acessos values ('{u}','asc')"); return u
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:130] if d else ""))
STUB="if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};}"
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar, #sideViews", state="attached", timeout=30000); await pg.wait_for_timeout(2500); await pg.evaluate("(()=>{const d=document.getElementById('whoDlg'); if(d && d.open) d.close()})()")
BAR="""() => { const tb=document.querySelector('#tabbar'); const kids=[...tb.children].filter(e=>!e.hidden && e.offsetParent!==null); const pl=tb.querySelector('.tab-plus'); const r=tb.getBoundingClientRect(), rp=pl&&pl.getBoundingClientRect();
  return { abas: kids.map(e=>e.classList.contains('tab-plus')?'+':(e.dataset.view||'?')), semAgenda: !tb.querySelector('[data-view=agenda]') && !document.querySelector('#sideViews [data-view=agenda]'), fab: getComputedStyle(document.querySelector('#fab')).display,
    dx: rp && rp.width ? Math.round((rp.left+rp.right)/2 - (r.left+r.right)/2) : null, plusVisivel: !!rp && rp.width>0, destaque: pl ? getComputedStyle(pl.querySelector('.tp-i')).backgroundImage.includes('gradient') : false, ativa: (tb.querySelector('[aria-current=true]')||{dataset:{}}).dataset.view } }"""
async def menu(pg):
    await pg.click(".tab-plus"); await pg.wait_for_selector("#plusMenu .pm-i", timeout=5000); await pg.wait_for_timeout(350)
    return await pg.evaluate("(()=>{const m=document.querySelector('#plusMenu .pm-box').getBoundingClientRect(), t=document.querySelector('#tabbar').getBoundingClientRect(), p=document.querySelector('.tab-plus'); return {itens:[...document.querySelectorAll('#plusMenu .pm-i b')].map(b=>b.textContent), acimaDaBarra: m.bottom <= t.top+1, dentro: m.left>=0 && m.right<=innerWidth && m.top>=0, aberto: p.classList.contains('open') && p.getAttribute('aria-expanded')==='true'}})()")
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]; uid=None
    try:
      for tema in ("light","dark"):
        ctx=await b.new_context(**dev, color_scheme=tema); await ctx.add_init_script(STUB); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        await entra(pg,"admin",CRED["admin"]); print(f"\n######## ADMIN · tema {tema}")
        g=await pg.evaluate(BAR)
        chk("abas: Início, Quadro, + (no meio), Mês, Mais", g['abas']==['today','board','+','month','mais'], g['abas'])
        chk("a Agenda saiu da barra e do menu lateral", g['semAgenda'])
        chk("o botão '+' flutuante antigo está escondido", g['fab']=='none', g['fab'])
        chk("o '+' fica no CENTRO da barra e em destaque", g['plusVisivel'] and abs(g['dx'])<=3 and g['destaque'], {"dx":g['dx'],"destaque":g['destaque']})
        await pg.screenshot(path=f"barra_{tema}_fechada.png")
        m=await menu(pg); chk("tocar no '+' abre as 3 opções, em cima da barra, dentro da tela", m['itens']==["Nova demanda","Por texto","Por foto"] and m['acimaDaBarra'] and m['dentro'], m)
        chk("o '+' vira '×' enquanto o menu está aberto", m['aberto']); await pg.screenshot(path=f"barra_{tema}_menu.png")
        if tema=="light":
            await pg.click("#plusMenu .pm-scrim", position={"x":20,"y":120}); await pg.wait_for_timeout(300); chk("tocar fora fecha o menu", await pg.locator("#plusMenu").count()==0)
            await menu(pg); await pg.keyboard.press("Escape"); await pg.wait_for_timeout(300); chk("Esc fecha o menu", await pg.locator("#plusMenu").count()==0)
            await menu(pg); await pg.click("#plusMenu .pm-i[data-op=new]"); await pg.wait_for_selector("#dlg[open]", timeout=5000); chk("'Nova demanda' abre o formulário em branco", await pg.locator("#plusMenu").count()==0 and await pg.evaluate("document.querySelector('#dlg').open && !document.querySelector('#fTitulo, #fTit, input[name=titulo]').value"))
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
            await menu(pg); await pg.click("#plusMenu .pm-i[data-op=paste]"); await pg.wait_for_selector("#batTxt", state="visible", timeout=5000); chk("'Por texto' abre a janela de colar o texto", True)
            await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
            await menu(pg)
            async with pg.expect_file_chooser(timeout=6000) as fc: await pg.click("#plusMenu .pm-i[data-op=photo]")
            chk("'Por foto' abre a escolha de foto do aparelho", fc.value is not None)
        await ctx.close()
      print("\n######## FUNCIONÁRIO DA BM (conta descartável)")
      uid_bx=cria_func("tst.bx")
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); await entra(pg,"tst.bx","SenhaForte123"); g=await pg.evaluate(BAR)
      chk("funcionário: Início, Quadro, + (no meio), Mês, Minhas (igual ao admin, sem Mais)", g['abas']==['today','board','+','month','minhas'], g['abas']); chk("funcionário: o '+' fica no CENTRO da barra, igual ao admin", g['dx'] is not None and abs(g['dx'])<=3, g['dx'])
      m=await menu(pg); chk("as 3 opções aparecem pro funcionário", m['itens']==["Nova demanda","Por texto","Por foto"], m['itens']); await pg.keyboard.press("Escape")
      await ctx.close()
      print("\n######## LEITOR (só visualiza)")
      requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Leitor Barra","usuario":"tst.lb","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.lb'")[0]['id']; sql(f"insert into public.acessos values ('{uid}','asc')")
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); await entra(pg,"tst.lb","SenhaForte123"); g=await pg.evaluate(BAR)
      chk("leitor NÃO tem o '+' (Início, Quadro, Mês, Minhas)", g['abas']==['today','board','month','minhas'], g['abas']); await ctx.close()
      print("\n######## QUEM TINHA A AGENDA SALVA")
      bm_id=uid_bx; sql(f"insert into public.preferencias(pessoa_id, dados) values ('{bm_id}', '{{\"view\":\"agenda\"}}'::jsonb) on conflict (pessoa_id) do update set dados='{{\"view\":\"agenda\"}}'::jsonb")
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); await entra(pg,"tst.bx","SenhaForte123"); g=await pg.evaluate(BAR); chk("com a Agenda salva como última tela, abre no Início", g['ativa']=='today', g['ativa']); await ctx.close()
      print("\n######## DESKTOP")
      ctx=await b.new_context(viewport={"width":1280,"height":800}); await ctx.add_init_script(STUB); pg=await ctx.new_page(); await entra(pg,"admin",CRED["admin"])
      d=await pg.evaluate("({lateral:[...document.querySelectorAll('#sideViews [data-view]')].map(e=>e.dataset.view), barra: getComputedStyle(document.querySelector('#tabbar')).display, novo: !!document.querySelector('[data-act=new]:not(.f1)') && document.querySelector('[data-act=new]:not(.f1)').offsetParent!==null})")
      chk("desktop: menu lateral sem Agenda (Início, Quadro, Mês, Mais)", d['lateral']==['today','board','month','mais'], d['lateral']); chk("desktop: sem barra de baixo e com o botão 'Nova demanda'", d['barra']=='none' and d['novo'], d); await ctx.close()
    finally:
      if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
      if 'uid_bx' in dir(): requests.delete(f"{BASE}/auth/v1/admin/users/{uid_bx}", headers=SV)
      print("\nerros de JS:", errs, "| usuários:", sql("select string_agg(usuario,',') u from public.pessoas")[0]['u']); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
