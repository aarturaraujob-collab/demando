"""Rodapé da ficha (Excluir, Arquivar, Cancelar | Duplicar, Editar), agenda cancelada de ponta a ponta, e funcionário (sem lista de nomes, nome fixo).
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<..> PUSH_SECRET=<..> python3 tests/cancelada_test.py   (só usa demandas/contas de teste, apagadas no fim)"""
import asyncio, os, time, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE,"Content-Type":"application/json"}
URL=os.environ.get("APP","http://localhost:8766/index.html"); ADMIN=os.environ['ADMIN_SENHA']; res=[]
VK="BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U"; VA="tBHItJI5svbpez7KI4CCXg"
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:140] if d else ""))
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(2800)
    await pg.evaluate("(()=>{const d=document.getElementById('whoDlg'); if(d && d.open) d.close()})()")
RODAPE="(()=>[...document.querySelectorAll('#det .sh-f button')].filter(b=>!b.hidden && b.offsetParent!==null).map(b=>[b.textContent.trim(), Math.round(b.getBoundingClientRect().top), Math.round(b.getBoundingClientRect().left), Math.round(b.getBoundingClientRect().right)]))()"
EM_ABERTO="(()=>{const p=[...document.querySelectorAll('#sum .pane')].find(x=>x.classList.contains('asc')); return p? Number(p.querySelector('.kpi b').textContent) : null})()"
async def abre(pg, titulo):
    await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(600); await pg.fill("input[type=search]", titulo); await pg.wait_for_timeout(700)
    await pg.click(f"#view .rw:has-text('{titulo}') .body >> nth=0"); await pg.wait_for_selector("#detBody", state="visible"); await pg.wait_for_timeout(700)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]; uid=None; ensaio=False
    try:
      hoje=sql("select (now() at time zone 'America/Maceio')::date::text d")[0]['d']; adm=sql("select id from public.pessoas where usuario='admin'")[0]['id']
      sql("delete from public.demandas where id like 'tst-c%'")
      sql(f"insert into public.demandas(id, area_id, titulo, tipo, status, prazo, equipe, criado_por, criado_em) values ('tst-c1','asc','TSTCANC jogo de teste','Cobertura','A fazer','{hoje}','{{Celso}}','{adm}','2026-01-01T12:00:00+00:00'), ('tst-c2','asc','TSTCANC entregue','Arte','Entregue','{hoje}','{{}}','{adm}','2026-01-01T12:00:00+00:00')")
      sql("update public.config_interna set valor = valor || '?simulado=1' where chave='push_url' and valor not like '%simulado%'"); ensaio=True
      sql(f"insert into public.push_subs(pessoa_id, endpoint, p256dh, auth, nome_equipe) values ('{adm}','https://push.example.invalid/c1','{VK}','{VA}','Celso')")
      print("######## RODAPÉ DA FICHA (admin)")
      for tema in ("light","dark"):
        ctx=await b.new_context(**dev, color_scheme=tema); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: asyncio.ensure_future(d.accept())); await entra(pg,"admin",ADMIN)
        await abre(pg,"TSTCANC jogo"); r=await pg.evaluate(RODAPE); nomes=[x[0] for x in r]
        chk(f"[{tema}] demanda aberta: Excluir, Cancelar | Duplicar, Editar (sem Fechar)", nomes==['Excluir','Cancelar','Duplicar','Editar'], nomes)
        chk(f"[{tema}] cabem numa linha só e dentro da tela", len({x[1] for x in r})<=1 or max(x[1] for x in r)-min(x[1] for x in r)<=3, r)
        await pg.screenshot(path=f"canc_rodape_{tema}.png")
        if tema=="light":
            n0=await pg.evaluate(EM_ABERTO)
            await pg.click("#detCanc"); await pg.wait_for_timeout(2500)
            row=sql("select cancelada_em is not null c, historico->-1->>'txt' h from public.demandas where id='tst-c1'")[0]
            chk("Cancelar: a demanda fica marcada como cancelada, com registro no histórico", row['c'] and row['h']=="Agenda cancelada", row)
            await pg.wait_for_timeout(500); await pg.fill("input[type=search]",""); await pg.wait_for_timeout(600)
            g=await pg.evaluate("(()=>{const gs=[...document.querySelectorAll('#view .grp')]; const g=gs.find(x=>x.querySelector('h3').textContent.trim()==='Agenda cancelada'); if(!g) return null; const r=g.querySelector('.rw'); return {titulo: r.querySelector('.tt').textContent, chip: (r.querySelector('.sc.canc')||{}).textContent, riscado: getComputedStyle(r.querySelector('.tt')).textDecorationLine}})()")
            chk("Início: aparece no grupo 'Agenda cancelada', com a etiqueta e o título riscado", g and 'TSTCANC jogo' in g['titulo'] and g['chip']=="Agenda cancelada" and 'line-through' in g['riscado'], g)
            chk("e saiu das demandas em aberto (o número do resumo cai 1)", (await pg.evaluate(EM_ABERTO))==n0-1, {"antes":n0,"depois":await pg.evaluate(EM_ABERTO)})
            await pg.click("#tabbar [data-view=board]"); await pg.wait_for_timeout(900); chk("Quadro: não aparece em nenhuma coluna", await pg.locator("#view .card:has-text('TSTCANC jogo')").count()==0)
            await pg.click("#tabbar [data-view=month]"); await pg.wait_for_timeout(900); chk("Mês: continua no calendário, riscada", await pg.locator("#view .ev.canc").count()>=1)
            log=sql("select tipo, destinatarios, simulado from public.push_log where tipo='cancelada' order by id desc limit 1"); chk("a equipe escalada é avisada ('Agenda cancelada')", log and log[0]['destinatarios']>=1 and log[0]['simulado'], log)
            await abre(pg,"TSTCANC jogo"); txt=await pg.inner_text("#detBody"); r=[x[0] for x in await pg.evaluate(RODAPE)]
            chk("ficha da cancelada: aviso 'Agenda cancelada em…' e botões com Arquivar e Reativar", "Agenda cancelada em" in txt and r==['Excluir','Arquivar','Reativar','Duplicar','Editar'], r)
            await pg.click("#detCanc"); await pg.wait_for_timeout(2200)
            chk("Reativar: volta pras demandas em aberto", sql("select cancelada_em is null a from public.demandas where id='tst-c1'")[0]['a'] and (await pg.evaluate(EM_ABERTO))==n0, await pg.evaluate(EM_ABERTO))
        await ctx.close()
      print("\n######## ARQUIVO AUTOMÁTICO E RESUMO")
      sql("update public.demandas set cancelada_em = now() - interval '20 days' where id='tst-c1'"); sql("insert into public.demandas(id, area_id, titulo, status, cancelada_em, criado_por) values ('tst-c3','asc','TSTCANC recente','A fazer', now() - interval '3 days', '"+adm+"')")
      sql("select public.arquivar_antigas()"); e=lambda i: sql(f"select arquivada_em is not null a from public.demandas where id='{i}'")[0]['a']
      chk("cancelada há 20 dias é arquivada pelo robô; a de 3 dias não", e('tst-c1') and not e('tst-c3'))
      sql("update public.demandas set cancelada_em = now(), arquivada_em = null where id='tst-c1'")
      r=requests.post(BASE+"/functions/v1/enviar-push?simulado=1", headers={"x-push-secret":os.environ['PUSH_SECRET']}, json={"tipo":"resumo"}).json()
      chk("o resumo das 8h não inclui agenda cancelada", not any('TSTCANC' in str(i) for i in (r.get('itens') or [])), r.get('itens'))
      print("\n######## FUNCIONÁRIO (conta compartilhada de teste)")
      rr=requests.post(f"{BASE}/auth/v1/admin/users", headers=SV, json={"email":"demandasbm+tst.cn@gmail.com","password":"SenhaForte123","email_confirm":True,"user_metadata":{"nome":"Func Cancel","usuario":"tst.cn"}}); uid=rr.json()['id']
      sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
      sql("update public.demandas set cancelada_em=null, arquivada_em=null where id='tst-c1'")
      ctx=await b.new_context(**dev); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); rec={"msgs":[], "ok":False}
      def tratar(d): rec["msgs"].append(d.message); asyncio.ensure_future(d.accept() if rec["ok"] else d.dismiss())
      pg.on("dialog", tratar); await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario","tst.cn"); await pg.fill("#g-senha","SenhaForte123"); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(2800)
      await pg.click("#whoDlg .who-b:has-text('Celso')"); await pg.wait_for_timeout(1200)
      chk("escolher o nome pede confirmação ('não dá pra trocar')", len(rec["msgs"])==1 and "não dá pra trocar" in rec["msgs"][0], rec["msgs"])
      chk("se a pessoa responde 'não', nada é gravado e a pergunta continua", (await pg.evaluate(f"localStorage.getItem('cd-eu@{uid}')")) is None and await pg.evaluate("!!document.getElementById('whoDlg')"))
      rec["ok"]=True; await pg.click("#whoDlg .who-b:has-text('Celso')"); await pg.wait_for_timeout(1500)
      chk("confirmando, o nome fica fixo neste aparelho", (await pg.evaluate(f"localStorage.getItem('cd-eu@{uid}')"))=="Celso")
      vis=[]
      for aba in ("today","board","month","minhas"):
          await pg.click(f"#tabbar [data-view={aba}]"); await pg.wait_for_timeout(800); vis.append((aba, await pg.locator("#pessoa").is_visible()))
      chk("funcionário: a lista de nomes (filtro de pessoa) não aparece em nenhuma tela", not any(v for _,v in vis), vis)
      await pg.click("#tabbar [data-view=minhas]"); await pg.wait_for_timeout(800); links=await pg.evaluate("[...document.querySelectorAll('#view .hello .lnk-b')].map(x=>x.textContent.trim())")
      chk("em Minhas não há 'Não sou eu' nem 'Ver as demandas de toda a equipe'", links==[], links)
      await abre(pg,"TSTCANC jogo"); r=[x[0] for x in await pg.evaluate(RODAPE)]; chk("funcionário vê a ficha de outra pessoa só com 'Fechar' (não pode cancelar nem excluir)", r==['Fechar'], r)
      await ctx.close()
    finally:
      if ensaio: sql("update public.config_interna set valor = replace(valor, '?simulado=1', '') where chave='push_url'")
      sql("delete from public.demandas where id like 'tst-c%'"); sql("delete from public.push_subs where endpoint like 'https://push.example.invalid%'")
      if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
      print("\nerros de JS:", errs, "| restos:", sql("select (select count(*) from public.demandas where id like 'tst-c%') d, (select valor like '%simulado%' from public.config_interna where chave='push_url') ensaio"))
      print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
