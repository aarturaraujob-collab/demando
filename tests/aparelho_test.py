"""Conta compartilhada (como a BM): "quem sou eu" vale por APARELHO. Pergunta ao entrar, lembra, o outro aparelho é perguntado de novo,
avisos vão pro aparelho certo, nome de quem criou, checklist/original/progresso fora da tela, logos do resumo sem deformar, atualização automática.
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<..> PUSH_SECRET=<..> BM_SENHA=<..> python3 tests/aparelho_test.py   (usa só contas e demandas de teste, apagadas no fim)"""
import asyncio, os, json, time, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE,"Content-Type":"application/json"}
URL=os.environ.get("APP","http://localhost:8766/index.html"); SENHA="SenhaForte123"; FN=f"{BASE}/functions/v1/enviar-push"; SEG={"x-push-secret":os.environ["PUSH_SECRET"]}; res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:150] if d else ""))
def stub(ep): return "try{Object.defineProperty(Notification,'permission',{get:()=>'granted',configurable:true})}catch(e){} window.__EP='%s'; if(!('PushManager' in window)){window.PushManager=function(){};} PushManager.prototype.getSubscription=async function(){return {endpoint:window.__EP, toJSON(){return {endpoint:window.__EP, keys:{p256dh:'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U',auth:'tBHItJI5svbpez7KI4CCXg'}}}, unsubscribe:async()=>true}};" % ep
async def entra(pg,u="tst.sh",s=SENHA):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(2600)
POP="(()=>{const d=document.getElementById('whoDlg'); return !!d && d.open})()"
async def main():
  async with async_playwright() as p:
    wk=await p.webkit.launch(); ch=await p.chromium.launch(); errs=[]; uid=None
    try:
      r=requests.post(f"{BASE}/auth/v1/admin/users", headers=SV, json={"email":"demandasbm+tst.sh@gmail.com","password":SENHA,"email_confirm":True,"user_metadata":{"nome":"Compartilhada Teste","usuario":"tst.sh"}}); uid=r.json()['id']
      sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
      sql(f"insert into public.push_subs(pessoa_id, endpoint, p256dh, auth) values ('{uid}','https://push.example.invalid/dev1','BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U','tBHItJI5svbpez7KI4CCXg'),('{uid}','https://push.example.invalid/dev2','BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U','tBHItJI5svbpez7KI4CCXg')")
      print("######## APARELHO 1 (conta compartilhada, primeira vez)")
      c1=await ch.new_context(viewport={'width':412,'height':915}, permissions=['notifications']); await c1.add_init_script(stub("https://push.example.invalid/dev1")); pg1=await c1.new_page(); pg1.on("pageerror", lambda e: errs.append(str(e))); await entra(pg1)
      chk("ao entrar, a janela 'Quem é você?' aparece sozinha", await pg1.evaluate(POP))
      nomes=await pg1.evaluate("[...document.querySelectorAll('#whoDlg .who-b')].map(b=>b.textContent.trim().slice(1))"); chk("com os nomes da equipe da BM (e só)", sorted(nomes)==sorted(['Juninho','Leopoldo','Celso','Sara','Arthur','Mauro']), nomes)
      await pg1.screenshot(path="ap_pergunta.png")
      await pg1.click("#whoDlg .who-b:has-text('Celso')"); await pg1.wait_for_timeout(1500)
      chk("escolheu 'Celso': a janela fecha", not await pg1.evaluate(POP))
      eu=await pg1.evaluate(f"localStorage.getItem('cd-eu@{uid}')"); chk("o nome fica gravado NO APARELHO", eu=="Celso", eu)
      chk("e NÃO é gravado na conta (a conta é de várias pessoas)", sql(f"select nome_equipe from public.pessoas where id='{uid}'")[0]['nome_equipe'] is None)
      chk("o aparelho avisa em nome do Celso", sql("select nome_equipe from public.push_subs where endpoint='https://push.example.invalid/dev1'")[0]['nome_equipe']=="Celso")
      await pg1.reload(); await pg1.wait_for_selector("#tabbar", state="visible"); await pg1.wait_for_timeout(2500); chk("recarregou: NÃO pergunta de novo", not await pg1.evaluate(POP))
      await pg1.evaluate("window.DEMANDO_API.sair()"); await pg1.wait_for_selector("#g-usuario", timeout=20000); await pg1.fill("#g-usuario","tst.sh"); await pg1.fill("#g-senha",SENHA); await pg1.click("#g-entrar"); await pg1.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg1.wait_for_timeout(2600)
      chk("saiu e entrou de novo neste aparelho: NÃO pergunta (já sabe que é o Celso)", not await pg1.evaluate(POP))
      chk("e o aparelho volta a avisar em nome do Celso", (sql("select nome_equipe from public.push_subs where endpoint='https://push.example.invalid/dev1'") or [{}])[0].get('nome_equipe')=="Celso")
      await pg1.click("#tabbar [data-view=minhas]"); await pg1.wait_for_timeout(1000); chk("'Minhas' mostra só as escalas do Celso", "Olá, Celso" in await pg1.inner_text("#view"))
      await pg1.click("#tabbar [data-view=today]"); await pg1.wait_for_timeout(900)
      ini=await pg1.evaluate("(()=>{const r=[...document.querySelectorAll('#view .rw')]; return {t:r.length, sem:r.filter(x=>!((x.querySelector('.avs')||{}).innerText||'').includes('Celso')).length}})()")
      chk("Início mostra a equipe toda (tem demandas de outras pessoas, não só do Celso)", ini['sem']>0, ini)
      print("\n######## APARELHO 2 (outra pessoa, mesma conta)")
      c2=await ch.new_context(viewport={'width':412,'height':915}, permissions=['notifications']); await c2.add_init_script(stub("https://push.example.invalid/dev2")); pg2=await c2.new_page(); await entra(pg2)
      chk("em OUTRO aparelho, com a mesma conta, PERGUNTA de novo", await pg2.evaluate(POP))
      await pg2.click("#whoDlg .who-b:has-text('Juninho')"); await pg2.wait_for_timeout(1500)
      await pg2.click("#tabbar [data-view=minhas]"); await pg2.wait_for_timeout(900); chk("este aparelho é o Juninho", "Olá, Juninho" in await pg2.inner_text("#view"))
      chk("o outro aparelho CONTINUA sendo o Celso (um não atropela o outro)", (await pg1.evaluate(f"localStorage.getItem('cd-eu@{uid}')"))=="Celso" and sql("select nome_equipe from public.push_subs where endpoint='https://push.example.invalid/dev1'")[0]['nome_equipe']=="Celso" and sql("select nome_equipe from public.push_subs where endpoint='https://push.example.invalid/dev2'")[0]['nome_equipe']=="Juninho")
      print("\n######## 'AGORA NÃO' e 'NÃO SOU EU'")
      c3=await ch.new_context(viewport={'width':412,'height':915}); pg3=await c3.new_page(); await entra(pg3); await pg3.click("#whoDlg .mvd-no"); await pg3.wait_for_timeout(800)
      chk("'Agora não' fecha e não insiste nesta visita", not await pg3.evaluate(POP)); await pg3.evaluate("window.scrollTo(0,0)")
      chk("o cartão 'Quem é você?' continua à mão no Início", await pg3.locator("#meHold .who-pick").count()==1)
      await pg2.click("#view .hello-a .lnk-b:has-text('Não sou eu')"); await pg2.wait_for_timeout(1200); chk("'Não sou eu' pergunta de novo", await pg2.evaluate(POP))
      await pg2.click("#whoDlg .who-b:has-text('Sara')"); await pg2.wait_for_timeout(1200); chk("e a Sara vira o nome deste aparelho", (await pg2.evaluate(f"localStorage.getItem('cd-eu@{uid}')"))=="Sara" and sql("select nome_equipe from public.push_subs where endpoint='https://push.example.invalid/dev2'")[0]['nome_equipe']=="Sara")
      print("\n######## NOME DE QUEM CRIOU + LIMPEZA DA FICHA")
      hoje=sql("select (now() at time zone 'America/Maceio')::date::text d")[0]['d']
      await pg1.click(".tab-plus"); await pg1.click("#plusMenu .pm-i[data-op=new]"); await pg1.wait_for_selector("#fTitulo"); await pg1.fill("#fTitulo","TST-criada pelo Celso"); await pg1.fill("#fPrazo",hoje); await pg1.click("#saveBtn"); await pg1.wait_for_timeout(2500)
      row=sql("select criado_por_nome, criado_por::text c from public.demandas where titulo='TST-criada pelo Celso'")
      chk("a demanda guarda o NOME de quem criou (Celso), não só a conta", row and row[0]['criado_por_nome']=="Celso" and row[0]['c']==uid, row)
      sql(f"update public.demandas set checklist='[{{\"t\":\"Item 1\",\"ok\":false}},{{\"t\":\"Item 2\",\"ok\":true}}]'::jsonb, original='Texto do pedido original', obs='Observação visível' where titulo='TST-criada pelo Celso'")
      await pg1.reload(); await pg1.wait_for_selector("#tabbar", state="visible"); await pg1.wait_for_timeout(2500)
      chk("no card não aparece mais o '0/4' (progresso do checklist)", await pg1.locator("#view .rw .prog, #view .card .prog").count()==0)
      await pg1.click("#view .rw:has-text('TST-criada pelo Celso') .body"); await pg1.wait_for_selector("#detBody", state="visible"); await pg1.wait_for_timeout(900); txt=await pg1.inner_text("#detBody")
      chk("na ficha não aparece 'Checklist' nem 'Pedido original'", "Checklist" not in txt and "Pedido original" not in txt and "Item 1" not in txt and "Texto do pedido" not in txt, txt[:90].replace("\n"," | "))
      chk("mas as Observações continuam", "Observação visível" in txt); await pg1.keyboard.press("Escape"); await pg1.wait_for_timeout(500)
      print("\n######## LOGOS DO RESUMO SEM DEFORMAR (admin)")
      ca=await ch.new_context(viewport={'width':412,'height':915}); pga=await ca.new_page(); await entra(pga,"admin",os.environ['ADMIN_SENHA'])
      lg=await pga.evaluate("""(()=>{ const o={}; for (const k of ['faf','bm']){ const b=document.querySelector('.pane .ph b[data-logo="'+k+'"]'); if(!b){o[k]=null; continue;} const c=getComputedStyle(b,'::before'); o[k]={w:c.width,h:c.height,raio:c.borderTopLeftRadius,sombra:c.boxShadow,fundo:c.backgroundColor}; } return o; })()""")
      chk("escudo da FAF no resumo: reto (sem recorte redondo nem anel)", lg['faf'] and lg['faf']['raio']=='0px' and lg['faf']['sombra']=='none' and lg['faf']['fundo']=='rgba(0, 0, 0, 0)', lg['faf'])
      chk("escudo da BM no resumo: reto (sem recorte redondo nem anel)", lg['bm'] and lg['bm']['raio']=='0px' and lg['bm']['sombra']=='none' and lg['bm']['fundo']=='rgba(0, 0, 0, 0)', lg['bm'])
      await pga.locator("#sum .pane").first.screenshot(path="ap_resumo.png")
      print("\n######## ATUALIZAÇÃO AUTOMÁTICA")
      cu=await ch.new_context(viewport={'width':412,'height':915}, service_workers='block'); pgu=await cu.new_page(); navs=[]; pgu.on("framenavigated", lambda f: navs.append(f.url) if f==pgu.main_frame else None)
      await pgu.route("**/versao.json*", lambda r: r.fulfill(status=200, content_type="application/json", body='{"v":"versao-nova-teste"}'))
      await entra(pgu,"admin",os.environ['ADMIN_SENHA']); n0=len(navs); await pgu.wait_for_timeout(9000)
      chk("quando sai versão nova, o app se atualiza sozinho (recarrega uma vez)", len(navs)-n0==1, {"recargas":len(navs)-n0})
      await pgu.wait_for_timeout(8000); chk("e não entra em laço de recarregar", len(navs)-n0==1, {"recargas":len(navs)-n0})
      print("\n######## AVISOS VÃO PRO APARELHO CERTO (função, em ensaio)")
      def chamar(corpo): return requests.post(FN+"?simulado=1", headers=SEG, json=corpo).json()
      nomes_de=lambda r: sorted(str(i.get('nome') or ('ERRO:'+str(i.get('erro')))) for i in (r.get('itens') or []))
      def dem(i, equipe, **kw):
          sql(f"delete from public.demandas where id='{i}'"); cols={"id":i,"area_id":"asc","titulo":"TST-"+i,"equipe":"{"+",".join(equipe)+"}","criado_em":"2026-01-01T12:00:00+00:00",**kw}
          sql("insert into public.demandas(%s) values (%s)" % (",".join(cols), ",".join("'"+str(v)+"'" for v in cols.values())))
      dem("tst-n1",["Celso"]); r=chamar({"tipo":"nova","id":"tst-n1"}); chk("escala do Celso → só o aparelho do Celso é avisado (não o do Sara/Juninho)", nomes_de(r)==['celso'], nomes_de(r))
      dem("tst-n2",["Celso","Sara"]); r=chamar({"tipo":"nova","id":"tst-n2"}); chk("escala de Celso e Sara → os dois aparelhos", nomes_de(r)==['celso','sara'], nomes_de(r))
      dem("tst-n3",["Celso","Sara"], criado_por_nome="Celso"); r=chamar({"tipo":"nova","id":"tst-n3"}); chk("o Celso criou e se escalou: NÃO recebe aviso do que ele mesmo fez (só a Sara)", nomes_de(r)==['sara'], nomes_de(r))
      r=chamar({"tipo":"escala","id":"tst-n1","novos":["Sara"]}); chk("'escalaram a Sara depois' → só o aparelho da Sara", nomes_de(r)==['sara'], nomes_de(r))
      r=chamar({"tipo":"direcionamento","id":"tst-n2","autor":uid,"autor_nome":"Celso"}); chk("direcionamento escrito pelo Celso → avisa a Sara, não o Celso", nomes_de(r)==['sara'], nomes_de(r))
      dem("tst-n4",["Celso"], prazo=hoje); r=chamar({"tipo":"resumo"}); chk("resumo das 8h: só o aparelho de quem tem demanda hoje", nomes_de(r)==['celso'], nomes_de(r))
      r=chamar({"tipo":"teste","pessoa":uid,"endpoint":"https://push.example.invalid/dev2"}); chk("aviso de teste vai só pro aparelho que ligou o sininho", r.get('destinatarios')==1 and nomes_de(r)==['sara'], nomes_de(r))
      sql("update public.push_subs set nome_equipe=null where endpoint='https://push.example.invalid/dev1'"); r=chamar({"tipo":"nova","id":"tst-n1"}); chk("aparelho sem nome escolhido não recebe aviso de ninguém (conta compartilhada)", r.get('destinatarios')==0, r)
    finally:
      sql("delete from public.demandas where id like 'tst-n%' or titulo like 'TST-%'"); sql("delete from public.push_subs where endpoint like 'https://push.example.invalid%'")
      if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
      print("\nerros de JS:", errs, "| restos:", sql("select (select count(*) from public.demandas where titulo like 'TST-%') d, (select count(*) from auth.users where email like '%tst.sh%') u"))
      print(f"RESULTADO: {sum(res)} de {len(res)}"); await wk.close(); await ch.close()
asyncio.run(main())
