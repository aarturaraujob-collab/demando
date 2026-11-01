"""Sininho, inscrição do aparelho e nome na equipe. Precisa do app local em http://localhost:8766.
Uso: SB=<token> PUSH_SECRET=<segredo> ADMIN_SENHA=<senha> CODIGO_EQUIPE=<código> python3 tests/sino_test.py"""
import asyncio, os, json, time, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}
ADMIN=os.environ['ADMIN_SENHA']; CODIGO=os.environ['CODIGO_EQUIPE']; V={'push_secret': os.environ['PUSH_SECRET']}
URL="http://localhost:8766/index.html"; res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:130] if d else ""))
STUB="""(() => { let sub = null; const make = () => ({ endpoint: 'https://push.example.invalid/fake-' + Math.random().toString(36).slice(2),
  toJSON(){ return { endpoint:this.endpoint, keys:{ p256dh:'BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U', auth:'tBHItJI5svbpez7KI4CCXg' } }; },
  async unsubscribe(){ sub = null; return true; } });
  PushManager.prototype.subscribe = async function(){ sub = make(); return sub; }; PushManager.prototype.getSubscription = async function(){ return sub; }; })();"""
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={"width":390,"height":844}, permissions=["notifications"]); await ctx.add_init_script(STUB); pg=await ctx.new_page(); errs=[]
    pg.on("pageerror", lambda e: errs.append(str(e))); uid=None
    try:
        sql("delete from public.push_subs where endpoint like 'https://push.example.invalid%'"); adm=sql("select id from public.pessoas where usuario='admin'")[0]['id']
        await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario","admin"); await pg.fill("#g-senha",ADMIN); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=25000); await pg.wait_for_timeout(2500)
        print("== SININHO")
        chk("sininho aparece no topo (celular), desligado", await pg.locator(".mtop #sino").count()==1 and not await pg.evaluate("document.querySelector('#sino').classList.contains('on')"))
        await pg.screenshot(path="sino_off.png")
        await pg.click("#sino"); await pg.wait_for_timeout(2500)
        r=sql(f"select endpoint, p256dh, auth from public.push_subs where pessoa_id='{adm}'")
        chk("ativar: o aparelho é guardado no banco, no nome da pessoa", len(r)==1 and r[0]['endpoint'].startswith('https://push.example.invalid/'), r[0]['endpoint'] if r else None)
        chk("sininho fica ligado", await pg.evaluate("document.querySelector('#sino').classList.contains('on')")); await pg.screenshot(path="sino_on.png")
        await pg.click("#sino"); await pg.wait_for_timeout(2000)
        chk("desligar: remove o aparelho do banco", sql(f"select count(*) n from public.push_subs where pessoa_id='{adm}'")[0]['n']==0 and not await pg.evaluate("document.querySelector('#sino').classList.contains('on')"))
        await pg.click("#sino"); await pg.wait_for_timeout(2000)
        await pg.evaluate("window.DEMANDO_API.sair()"); await pg.wait_for_timeout(3000)
        chk("sair da conta limpa o aparelho (não sobra aviso pro próximo usuário)", sql("select count(*) n from public.push_subs")[0]['n']==0)
        print("== NOME NA EQUIPE (tela de pessoas)")
        requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Maria Souza","usuario":"tst.eq","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.eq'")[0]['id']
        await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario","admin"); await pg.fill("#g-senha",ADMIN); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=25000); await pg.wait_for_timeout(2000)
        await pg.click("#tabbar [data-view=mais]"); await pg.click(".mtabs button:has-text('Pessoas')"); await pg.wait_for_selector("[data-pessoa='tst.eq']")
        await pg.select_option("[data-papel='tst.eq']","membro"); await pg.check("[data-pessoa='tst.eq'] input[data-area=asc]"); await pg.fill("[data-nomeeq='tst.eq']","Mauro"); await pg.click("[data-salvar='tst.eq']"); await pg.wait_for_timeout(2000)
        chk("'Nome na equipe' salvo", sql("select nome_equipe from public.pessoas where usuario='tst.eq'")[0]['nome_equipe']=='Mauro'); await pg.screenshot(path="sino_pessoas.png")
        sql(f"insert into public.push_subs(pessoa_id, endpoint, p256dh, auth) values ('{uid}','https://push.example.invalid/eq','BEl62iUYgUivxIkv69yViEuiBIa-Ib9-SkvMeAtA3LFgDzkrxZJjSgSnfckjBJuBkr3qBUYIHBQFLXYp5Nksh8U','tBHItJI5svbpez7KI4CCXg')")
        sql(f"insert into public.demandas(id, area_id, titulo, equipe, criado_por, criado_em) values ('pe1','asc','PUSH-nome na equipe','{{Mauro}}','{adm}','2026-01-01T12:00:00+00:00')")
        rr=requests.post(f"{BASE}/functions/v1/enviar-push?simulado=1", headers={"x-push-secret":V['push_secret']}, json={"tipo":"nova","id":"pe1"}).json()
        chk("a 'Maria Souza' (nome na equipe = Mauro) recebe a escala do 'Mauro'", rr.get('destinatarios')==1, rr)
        print("== SERVICE WORKER RECEBE A MENSAGEM")
        cdp=await ctx.new_cdp_session(pg); regs=[]; cdp.on("ServiceWorker.workerRegistrationUpdated", lambda e: regs.extend(e.get('registrations',[]))); await cdp.send("ServiceWorker.enable"); await pg.wait_for_timeout(1500)
        reg=next((r for r in regs if 'localhost:8766' in r['scopeURL']), None)
        if reg:
            await cdp.send("ServiceWorker.deliverPushMessage", {"origin":"http://localhost:8766","registrationId":reg['registrationId'],"data":json.dumps({"title":"Nova escala","body":"Teste de aviso · 30 out","tag":"t1","url":"./"})}); await pg.wait_for_timeout(1500)
            ns=await pg.evaluate("navigator.serviceWorker.ready.then(r => r.getNotifications()).then(l => l.map(n => [n.title, n.body, n.tag]))")
            chk("o celular mostra a notificação (título e texto certos)", ns==[["Nova escala","Teste de aviso · 30 out","t1"]], ns)
        else: print("  ⚠ não consegui pegar o service worker pelo CDP; teste da exibição não executado")
    finally:
        sql("delete from public.demandas where titulo like 'PUSH-%'"); sql("delete from public.push_subs where endpoint like 'https://push.example.invalid%'"); sql("delete from public.push_log")
        if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
        print("limpeza →", sql("select (select count(*) from auth.users) users, (select count(*) from public.push_subs) subs, (select count(*) from public.demandas where titulo like 'PUSH-%') push"), "| erros de JS:", errs)
        print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
