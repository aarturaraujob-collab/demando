"""Nome só uma vez (e valendo em outro aparelho), \"Não sou eu\", filtro de pessoa só pra olhar, rodapé fixo ao rolar. App local em http://localhost:8766.
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<..> CODIGO_EQUIPE=<..> python3 tests/identidade_rodape_test.py"""
import asyncio, os, time, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; MG={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda q: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=MG, json={"query":q}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=MG).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}
URL=os.environ.get("APP","http://localhost:8766/index.html"); CODIGO=os.environ["CODIGO_EQUIPE"]; ADMIN=os.environ["ADMIN_SENHA"]; res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:150] if d else ""))
STUB="if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};}"
APP_SCROLL="(y)=>{const a=document.querySelector('.app'); a.scrollTo(0,y==='fim'?a.scrollHeight:y)}"
def nome_eq(u): return sql(f"select nome_equipe from public.pessoas where usuario='{u}'")[0]['nome_equipe']
def espera_nome(u, esperado, s=8):
    for _ in range(s*4):
        if nome_eq(u)==esperado: return True
        time.sleep(0.25)
    return False
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar, #sideViews", state="attached", timeout=30000); await pg.wait_for_timeout(2800)
async def ola(pg):
    await pg.click("#tabbar [data-view=minhas]"); await pg.wait_for_timeout(900); return (await pg.inner_text("#view"))[:60].replace("\n"," | ")
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]; uid=None
    try:
      requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Pessoa Id","usuario":"tst.id","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.id'")[0]['id']
      sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
      print("######## 'QUEM É VOCÊ?' SÓ UMA VEZ (conta nova)")
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
      await entra(pg,"tst.id","SenhaForte123")
      chk("primeira vez: o cartão 'Quem é você?' aparece", await pg.locator("#meHold .who-pick").count()==1)
      await pg.click(".who-b:has-text('Celso')"); await pg.wait_for_timeout(1200)
      chk("escolheu 'Celso': o cartão some e o nome fica gravado no servidor", await pg.locator("#meHold .who-pick").count()==0 and espera_nome("tst.id","Celso"), nome_eq("tst.id"))
      await pg.reload(); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(2500)
      chk("recarregou a página: NÃO pergunta de novo", await pg.locator("#meHold .who-pick").count()==0)
      t=await ola(pg); chk("e a aba Minhas já mostra 'Olá, Celso'", "Olá, Celso" in t, t)
      ctx2=await b.new_context(**dev); await ctx2.add_init_script(STUB); pg2=await ctx2.new_page(); await entra(pg2,"tst.id","SenhaForte123")
      chk("OUTRO aparelho (primeiro acesso nele): NÃO pergunta de novo", await pg2.locator("#meHold .who-pick").count()==0); t=await ola(pg2); chk("e já entra como 'Olá, Celso'", "Olá, Celso" in t, t); await ctx2.close()
      await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(500); await pg.evaluate(APP_SCROLL,'fim'); await pg.wait_for_timeout(400); await pg.click(".sair-b"); await pg.wait_for_selector("#g-usuario", timeout=15000)
      await entra(pg,"tst.id","SenhaForte123"); chk("saiu da conta e entrou de novo: NÃO pergunta de novo", await pg.locator("#meHold .who-pick").count()==0)
      t=await ola(pg); chk("continua 'Olá, Celso'", "Olá, Celso" in t, t)
      print("== trocar de nome de propósito")
      await pg.click("#view .hello-a .lnk-b:has-text('Não sou eu')"); await pg.wait_for_timeout(1000)
      chk("'Não sou eu' limpa o nome no servidor e mostra a escolha", await pg.locator("#view .who-pick").count()==1 and espera_nome("tst.id",None), nome_eq("tst.id"))
      await pg.click(".who-b:has-text('Sara')"); await pg.wait_for_timeout(1200); chk("escolhendo 'Sara', ela vira o nome permanente", espera_nome("tst.id","Sara"), nome_eq("tst.id"))
      ctx3=await b.new_context(**dev); await ctx3.add_init_script(STUB); pg3=await ctx3.new_page(); await entra(pg3,"tst.id","SenhaForte123"); t=await ola(pg3); chk("outro aparelho já entra como 'Olá, Sara' (e não volta pro Celso)", "Olá, Sara" in t, t); await ctx3.close()
      print("== filtro de pessoa: só pra olhar, não muda quem eu sou")
      await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(800); await pg.select_option("#pessoa","Juninho"); await pg.wait_for_timeout(900)
      linhas=await pg.evaluate("[...document.querySelectorAll('#view .rw')].map(r=>((r.querySelector('.avs')||{}).innerText||''))"); chk("escolher 'Juninho' no filtro mostra só as demandas dele", len(linhas)>0 and all('Juninho' in x for x in linhas), len(linhas))
      t=await ola(pg); chk("na aba Minhas aparece 'Escalas de Juninho' com o botão pra voltar", "Escalas de Juninho" in t and await pg.locator("#view .lnk-b:has-text('Voltar às minhas escalas')").count()==1, t)
      chk("quem eu sou continua sendo a Sara no servidor", nome_eq("tst.id")=="Sara")
      await pg.click("#view .lnk-b:has-text('Voltar às minhas escalas')"); await pg.wait_for_timeout(800); chk("'Voltar às minhas escalas' traz de volta 'Olá, Sara'", "Olá, Sara" in (await pg.inner_text("#view")))
      await pg.select_option("#pessoa","Juninho"); await pg.reload(); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(2500)
      chk("o filtro NÃO fica gravado: ao recarregar volta pra 'Toda a equipe'", await pg.evaluate("document.querySelector('#pessoa').value===''")); await ctx.close()
      print("\n######## RODAPÉ FIXO (admin)")
      for nome,eng,d in (("iPhone",p.webkit,dev),("Android",p.chromium,p.devices['Pixel 7'])):
        bb=b if nome=="iPhone" else await p.chromium.launch(); cx=await bb.new_context(**d); await cx.add_init_script(STUB); pq=await cx.new_page(); await entra(pq,"admin",ADMIN)
        r=await pq.evaluate("""(()=>{const t=document.querySelector('#tabbar').getBoundingClientRect(), h=document.querySelector('.mtop').getBoundingClientRect(), a=document.querySelector('.app'); return {barTop:Math.round(t.top), barBottom:Math.round(t.bottom), vh:innerHeight, folga:Math.round(innerHeight-t.bottom), topoCabecalho:Math.round(h.top), rolavel:a.scrollHeight>a.clientHeight, docRola:document.scrollingElement.scrollTop, ov:getComputedStyle(a).overscrollBehaviorY, ovHtml:getComputedStyle(document.documentElement).overscrollBehaviorY}})()""")
        await pq.evaluate(APP_SCROLL,900); await pq.wait_for_timeout(500)
        r2=await pq.evaluate("""(()=>{const t=document.querySelector('#tabbar').getBoundingClientRect(), h=document.querySelector('.mtop').getBoundingClientRect(), a=document.querySelector('.app'); return {barTop:Math.round(t.top), appRolou:Math.round(a.scrollTop), docRola:document.scrollingElement.scrollTop, topoCabecalho:Math.round(h.top)}})()""")
        chk(f"[{nome}] a barra de baixo NÃO se mexe quando rolo a tela (mesma posição antes e depois)", r['barTop']==r2['barTop'] and r2['appRolou']>300, {"antes":r['barTop'],"depois":r2['barTop'],"rolou":r2['appRolou']})
        chk(f"[{nome}] a barra continua flutuando (com folga embaixo, não colada)", r['folga']>=6, r['folga'])
        chk(f"[{nome}] a página em si não rola (só o miolo): sem tremer nem esconder a barra", r['docRola']==0 and r2['docRola']==0 and r['ov']=='contain' and r['ovHtml']=='none', {k:r[k] for k in ('docRola','ov','ovHtml')})
        chk(f"[{nome}] o cabeçalho também fica fixo no topo", r2['topoCabecalho']<=2, r2['topoCabecalho'])
        if nome=="iPhone": await pq.evaluate(APP_SCROLL,0); await pq.wait_for_timeout(300); await pq.screenshot(path="novo_inicio.png")
        await cx.close()
        if nome!="iPhone": await bb.close()
    finally:
      if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
      print("\nerros de JS:", errs, "| usuários:", sql("select string_agg(usuario,',') u from public.pessoas")[0]['u']); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
