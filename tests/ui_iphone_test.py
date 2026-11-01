"""Cabeçalho, ordem dos dados no card e \"Quem é você?\" no iPhone simulado. App local em http://localhost:8766.
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<..> CODIGO_EQUIPE=<..> python3 tests/ui_iphone_test.py"""
import asyncio, os, json, time, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}
ADMIN=os.environ['ADMIN_SENHA']; CODIGO=os.environ['CODIGO_EQUIPE']; V={}
URL="http://localhost:8766/index.html"; res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:140] if d else ""))
GEO="""() => { const r = s => { const e = document.querySelector(s); if (!e || !e.offsetParent && getComputedStyle(e).position!=='fixed') return null; const b = e.getBoundingClientRect(); return {l:Math.round(b.left), r:Math.round(b.right), cx:Math.round((b.left+b.right)/2), y:Math.round(b.top)}; };
  return { W: window.innerWidth, brand: r('.mtop .brand'), sino: r('#sino'), data: r('.mtop .mpage'), voltar: r('#backTop') }; }"""
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(3000); await pg.evaluate("(()=>{const d=document.getElementById('whoDlg'); if(d && d.open) d.close()})()")
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]; uid=None
    try:
        sql("delete from public.push_log"); sql("delete from public.push_subs where endpoint like 'https://push.example.invalid%'")
        ctxA=await b.new_context(**dev); await ctxA.add_init_script("if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};} if(!('Notification' in window)){window.Notification={permission:'default',requestPermission:async()=>'default'};}"); A=await ctxA.new_page(); A.on("pageerror", lambda e: errs.append(str(e)))
        await entra(A,"admin",ADMIN)
        print("== CABEÇALHO (iPhone, admin)")
        g=await A.evaluate(GEO); br=g['brand']
        chk("'Demandô' no CENTRO da tela", br and abs(br['cx']-g['W']/2)<=3, f"centro do nome = {br['cx'] if br else None}, centro da tela = {g['W']/2:.0f}")
        chk("sininho à ESQUERDA do nome", g['sino'] and g['sino']['r'] < br['l'], f"sino {g['sino']}")
        chk("data à DIREITA do nome", g['data'] and g['data']['l'] > br['r'], f"data {g['data']}")
        chk("sino, nome e data na mesma altura", g['sino'] and abs(g['sino']['y']-br['y'])<=14 and abs(g['data']['y']-br['y'])<=14)
        await A.screenshot(path="ui2_topo.png")
        print("== ORDEM DOS DADOS NO CARD (Agenda)")
        await A.click("#tabbar [data-view=today]"); await A.wait_for_timeout(1200)
        r=await A.evaluate("""() => { const row=[...document.querySelectorAll('.rw')].find(r=>r.querySelector('.when')&&r.querySelector('.avs')); if(!row) return null;
          const y=s=>Math.round(row.querySelector(s).getBoundingClientRect().top), x=s=>Math.round(row.querySelector(s).getBoundingClientRect().left);
          return {titulo: row.querySelector('.tt').textContent.slice(0,40), yStatus:y('.sc'), yWhen:y('.when'), yEquipe:y('.avs'), xStatus:x('.sc'), linhas:row.querySelectorAll('.body > .meta').length}; }""")
        chk("achei um card com status, local e equipe", r is not None, r)
        if r:
            chk("o card NÃO tem mais o '0/4' do checklist", await A.locator("#view .rw .prog").count()==0)
            chk("ordem de cima pra baixo: status/0-4 → local → equipe", r['yStatus'] < r['yWhen'] < r['yEquipe'], f"status {r['yStatus']} < local {r['yWhen']} < equipe {r['yEquipe']}")
        await A.evaluate("(()=>{const a=document.querySelector('.app'); if(a) a.scrollTo(0,0); window.scrollTo(0,0)})()"); await A.screenshot(path="ui2_card.png")
        print("== 'QUEM É VOCÊ?' → NOTIFICAÇÃO")
        requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Fulano Qualquer","usuario":"tst.q","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.q'")[0]['id']
        sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
        sql(f"insert into public.push_subs(pessoa_id, endpoint, p256dh, auth) values ('{uid}','https://push.example.invalid/q','BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U','tBHItJI5svbpez7KI4CCXg')")
        Bp=await (await b.new_context(**dev)).new_page(); Bp.on("pageerror", lambda e: errs.append(str(e))); await entra(Bp,"tst.q","SenhaForte123")
        chk("funcionário vê o cartão 'Quem é você?' logo no topo (antes do resumo)", await Bp.evaluate("(()=>{const c=document.querySelector('#meHold .who-pick'), s=document.querySelector('#sum'); return !!c && c.getBoundingClientRect().top < s.getBoundingClientRect().top + 1})()"))
        nomes=await Bp.evaluate("[...document.querySelectorAll('.who-b')].map(b=>b.textContent.replace('é você?','').trim().slice(1))")
        chk("com os nomes da equipe DA ÁREA dele (BM) e só", sorted(nomes)==sorted(['Juninho','Leopoldo','Celso','Sara','Arthur','Mauro']), nomes)
        await Bp.screenshot(path="ui2_quem.png")
        await Bp.click(".who-b:has-text('Celso')"); await Bp.wait_for_timeout(2500)
        chk("escolheu 'Celso': o Início segue mostrando a equipe toda (sem 'Olá, Celso')", "Olá, Celso" not in await Bp.inner_text("body")); await Bp.click("#tabbar [data-view=minhas]"); await Bp.wait_for_timeout(900); chk("na aba Minhas aparece 'Olá, Celso'", "Olá, Celso" in await Bp.inner_text("body"))
        chk("o nome fica guardado NO APARELHO (e não na conta, que é compartilhada)", (await Bp.evaluate(f"localStorage.getItem('cd-eu@{uid}')"))=='Celso' and sql(f"select nome_equipe from public.pessoas where id='{uid}'")[0]['nome_equipe'] is None)
        await Bp.screenshot(path="ui2_ola.png")
        C=await (await b.new_context(**dev)).new_page(); await C.goto(URL); await C.wait_for_selector("#g-usuario"); await C.fill("#g-usuario","tst.q"); await C.fill("#g-senha","SenhaForte123"); await C.click("#g-entrar"); await C.wait_for_selector("#tabbar", state="visible", timeout=30000); await C.wait_for_timeout(3000)
        chk("em OUTRO aparelho, com a mesma conta, PERGUNTA 'Quem é você?' de novo (a conta é de várias pessoas)", await C.evaluate("(()=>{const d=document.getElementById('whoDlg'); return !!d && d.open})()"))
        sql(f"insert into public.push_subs(pessoa_id, endpoint, p256dh, auth, nome_equipe) values ('{uid}','https://push.example.invalid/q2','BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U','tBHItJI5svbpez7KI4CCXg','Celso')"); sql("delete from public.push_subs where endpoint='https://push.example.invalid/q'")   # o aparelho avisa em nome de quem usa
        sql("update public.config_interna set valor = valor || '?simulado=1' where chave='push_url' and valor not like '%simulado%'"); n=sql("select count(*) n from public.push_log")[0]['n']
        sql(f"insert into public.demandas(id, area_id, titulo, tipo, equipe, criado_por) values ('tst-q1','asc','TESTE escala do Celso','Arte','{{Celso}}','{sql(chr(115)+'elect id from public.pessoas where usuario='+chr(39)+'admin'+chr(39))[0]['id']}')")
        for _ in range(20):
            L=sql("select tipo, destinatarios, enviados, detalhe from public.push_log order by id desc limit 1")
            if L and sql("select count(*) n from public.push_log")[0]['n']>n: break
            time.sleep(0.5)
        chk("o admin escala o Celso → o aparelho do funcionário é avisado", L and L[0]['tipo']=='nova' and L[0]['destinatarios']==1 and L[0]['enviados']==1, L[0] if L else None)
    finally:
        sql("update public.config_interna set valor = replace(valor, '?simulado=1', '') where chave='push_url'"); sql("delete from public.demandas where id like 'tst-q%'"); sql("delete from public.push_log"); sql("delete from public.push_subs where endpoint like 'https://push.example.invalid%'")
        if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
        print("limpeza →", sql("select (select count(*) from auth.users) users, (select valor like '%simulado%' from public.config_interna where chave='push_url') ensaio_ligado"), "| erros de JS:", errs)
        print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
