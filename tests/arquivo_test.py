"""Arquivar/desarquivar pela ficha, quem pode, arquivo automático após 14 dias (simulação sem rastro) e aviso das 8h ignorando arquivadas. App local em http://localhost:8766.
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<..> CODIGO_EQUIPE=<..> BM_SENHA=<..> PUSH_SECRET=<..> python3 tests/arquivo_test.py"""
import asyncio, os, time, json, base64, secrets, requests
from playwright.async_api import async_playwright
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; MG={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda q: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=MG, json={"query":q}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=MG).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; ANON=[k['api_key'] for k in keys if k['name']=='anon'][0]
SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE,"Content-Type":"application/json","Prefer":"return=minimal"}
URL=os.environ.get("APP","http://localhost:8766/index.html"); ADMIN=os.environ["ADMIN_SENHA"]; CODIGO=os.environ["CODIGO_EQUIPE"]; V={"push_secret": os.environ.get("PUSH_SECRET","")}; res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:160] if d else ""))
STUB="if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};}"
b64u=lambda x: base64.urlsafe_b64encode(x).rstrip(b'=').decode()
def hoje(): return sql("select (now() at time zone 'America/Maceio')::date::text d")[0]['d']
def arq(i): r=sql(f"select arquivada_em is not null a from public.demandas where id='{i}'"); return r[0]['a'] if r else None
def espera_arq(i, v, s=8):
    for _ in range(s*4):
        if arq(i)==v: return True
        time.sleep(0.25)
    return False
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar, #sideViews", state="attached", timeout=30000); await pg.wait_for_timeout(2800); await pg.evaluate("(()=>{const d=document.getElementById('whoDlg'); if(d && d.open) d.close()})()")
def ins(i,t,status,entregue,prazo,por,extra=None):
    d={"id":i,"area_id":"asc","titulo":t,"status":status,"prazo":prazo,"entregue":entregue,"criado_por":por,"criado_em":"2026-01-01T12:00:00+00:00"}; d.update(extra or {})
    return requests.post(f"{BASE}/rest/v1/demandas", headers=SV, json=d)
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]; uid=None
    adm=sql("select id from public.pessoas where usuario='admin'")[0]['id']; bm=sql("select id from public.pessoas where usuario='bm'")[0]['id']; H=hoje()
    try:
      sql("delete from public.demandas where id like 'tst-%'"); sql("delete from public.lixeira where registro_id like 'tst-%'")
      ins("tst-ar1","ARQ teste 1","Entregue",H,H,adm)
      print("######## ARQUIVAR PELA FICHA (admin)")
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e))); await entra(pg,"admin",ADMIN)
      await pg.click("#tabbar [data-view=board]"); await pg.wait_for_timeout(900); await pg.fill("input[type=search]","ARQ teste 1"); await pg.wait_for_timeout(700)
      chk("antes de arquivar: aparece no Quadro (coluna Entregue)", await pg.locator(".lane.asc .col:has(.col-t:has-text('Entregue')) .card:has-text('ARQ teste 1')").count()==1)
      await pg.click(".card:has-text('ARQ teste 1') .tt"); await pg.wait_for_selector("#detArq:not([hidden])", timeout=8000); txt=await pg.inner_text("#detArq"); chk("na ficha de uma concluída aparece o botão 'Arquivar'", txt.strip()=="Arquivar", txt)
      await pg.click("#detArq"); chk("arquivou: fica marcada no banco", espera_arq("tst-ar1",True)); await pg.wait_for_timeout(600)
      chk("e aparece o aviso 'Demanda arquivada' com Desfazer", "arquivada" in (await pg.inner_text("#toast")) and await pg.locator("#toastUndo").is_visible(), await pg.inner_text("#toast"))
      chk("sumiu do Quadro", await pg.locator(".card:has-text('ARQ teste 1')").count()==0)
      await pg.click("#toastUndo"); chk("'Desfazer' desarquiva", espera_arq("tst-ar1",False)); await pg.wait_for_timeout(600); chk("e volta pro Quadro", await pg.locator(".card:has-text('ARQ teste 1')").count()==1)
      await pg.click(".card:has-text('ARQ teste 1') .tt"); await pg.wait_for_selector("#detArq:not([hidden])"); await pg.click("#detArq"); espera_arq("tst-ar1",True); await pg.wait_for_timeout(700)
      print("== arquivada continua no Mês e dá pra desarquivar")
      await pg.click("#tabbar [data-view=month]"); await pg.wait_for_timeout(900); await pg.click("#view .cell.today"); await pg.wait_for_timeout(700)
      chk("no Mês a demanda arquivada ainda aparece (histórico)", await pg.locator("#view .rw:has-text('ARQ teste 1')").count()==1)
      await pg.click("#view .rw:has-text('ARQ teste 1') .body"); await pg.wait_for_selector("#detArq:not([hidden])"); chk("na ficha dela o botão vira 'Desarquivar'", (await pg.inner_text("#detArq")).strip()=="Desarquivar")
      await pg.click("#detArq"); chk("desarquivou pela ficha", espera_arq("tst-ar1",False)); await pg.wait_for_timeout(600)
      await pg.click("#tabbar [data-view=board]"); await pg.wait_for_timeout(800); await pg.fill("input[type=search]","ARQ teste 1"); await pg.wait_for_timeout(600); chk("e ela volta pro Quadro", await pg.locator(".card:has-text('ARQ teste 1')").count()==1)
      await pg.fill("input[type=search]",""); await ctx.close()
      print("\n######## QUEM PODE ARQUIVAR")
      ins("tst-ar2","ARQ teste 2 (do admin)","Entregue",H,H,adm); ins("tst-ar3","ARQ teste 3 (do bm)","Entregue",H,H,bm)
      tok=requests.post(f"{BASE}/auth/v1/token?grant_type=password", headers={"apikey":ANON}, json={"email":"demandasbm+bm@gmail.com","password":os.environ["BM_SENHA"]}).json()["access_token"]; HB={"apikey":ANON,"Authorization":"Bearer "+tok,"Content-Type":"application/json","Prefer":"return=minimal"}
      r=requests.patch(f"{BASE}/rest/v1/demandas?id=eq.tst-ar2", headers=HB, json={"arquivada_em":"2026-10-31T10:00:00Z"}); chk("funcionário NÃO consegue arquivar demanda dos outros", r.status_code>=400 and arq("tst-ar2") is False, (r.status_code, r.text[:90]))
      r=requests.patch(f"{BASE}/rest/v1/demandas?id=eq.tst-ar3", headers=HB, json={"arquivada_em":"2026-10-31T10:00:00Z"}); chk("funcionário consegue arquivar a que ele mesmo criou", r.status_code in (200,204) and arq("tst-ar3") is True, r.status_code)
      r=requests.patch(f"{BASE}/rest/v1/demandas?id=eq.tst-ar2", headers=HB, json={"status":"Postada"}); chk("funcionário continua podendo mudar a etapa da dos outros (até 'Postada')", r.status_code in (200,204), r.status_code)
      print("\n######## ARQUIVA SOZINHA (simulação que não deixa rastro)")
      ct=sql(f"select count(*) n from public.demandas where arquivada_em is not null")[0]['n']
      d=sql(f"""do $$ declare r text; n int; h date := (now() at time zone 'America/Maceio')::date; begin
        insert into public.demandas(id,area_id,titulo,status,entregue,prazo) values
          ('tst-au1','asc','AU1 entregue há 15 dias','Entregue', h-15, h-15),
          ('tst-au2','asc','AU2 postada há 14 dias','Postada', h-14, h-14),
          ('tst-au3','asc','AU3 entregue há 13 dias','Entregue', h-13, h-13),
          ('tst-au4','asc','AU4 aberta antiga','A fazer', null, h-30),
          ('tst-au5','asc','AU5 entregue sem data, prazo há 20 dias','Entregue', null, h-20),
          ('tst-au6','asc','AU6 já arquivada','Entregue', h-40, h-40);
        update public.demandas set arquivada_em = now() - interval '2 days' where id='tst-au6';
        n := public.arquivar_antigas();
        select string_agg(id || '=' || (arquivada_em is not null)::text, ',' order by id) into r from public.demandas where id like 'tst-au%';
        raise exception 'RESULTADO:%', r; end $$;""")
      m=str(d.get('message', d)); r=m.split('RESULTADO:')[1].split('"')[0].strip() if 'RESULTADO:' in m else m[:200]; mapa=dict(x.split('=') for x in r.split(',')) if '=' in r else {}
      chk("entregue há 15 dias: arquiva", mapa.get('tst-au1')=='true', mapa); chk("postada há 14 dias: arquiva", mapa.get('tst-au2')=='true'); chk("entregue há 13 dias: NÃO arquiva ainda", mapa.get('tst-au3')=='false')
      chk("aberta e antiga: NÃO arquiva (só concluídas)", mapa.get('tst-au4')=='false'); chk("concluída sem data de entrega usa o prazo", mapa.get('tst-au5')=='true')
      chk("a simulação não deixou rastro (nem arquivou nada real de verdade)", sql("select count(*) n from public.demandas where id like 'tst-au%'")[0]['n']==0 and sql("select count(*) n from public.demandas where arquivada_em is not null")[0]['n']==ct)
      print("\n######## AVISO DAS 8H IGNORA ARQUIVADAS E POSTADAS")
      requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Celso Teste","usuario":"tst.rs","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.rs'")[0]['id']; sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
      k=ec.generate_private_key(ec.SECP256R1()); pub=b64u(k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)); sql(f"insert into public.push_subs(pessoa_id, endpoint, p256dh, auth) values ('{uid}','https://push.example.invalid/rs','{pub}','{b64u(secrets.token_bytes(16))}')")
      eq="'{Celso}'"
      ins("tst-rs1","RS aberta hoje","A fazer",None,H,adm,{"equipe":["Celso"]}); ins("tst-rs2","RS postada hoje","Postada",H,H,adm,{"equipe":["Celso"]}); ins("tst-rs3","RS entregue hoje","Entregue",H,H,adm,{"equipe":["Celso"]}); ins("tst-rs4","RS aberta mas arquivada","A fazer",None,H,adm,{"equipe":["Celso"],"arquivada_em":"2026-10-30T10:00:00Z"})
      rr=requests.post(f"{BASE}/functions/v1/enviar-push?simulado=1", headers={"x-push-secret":V['push_secret']}, json={"tipo":"resumo"}).json(); it=[x for x in rr.get('itens',[]) if x.get('pessoa')==uid]
      chk("o resumo de hoje lista só 1 demanda (a aberta e não arquivada)", len(it)==1 and it[0]['titulo'].startswith('Hoje: 1 demanda'), it)
      await ctx.close() if False else None
    finally:
      if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE})
      sql("delete from public.demandas where id like 'tst-%'"); sql("delete from public.lixeira where registro_id like 'tst-%'"); sql("delete from public.push_log")
      print("\nerros de JS:", errs, "| restos de teste:", sql("select count(*) n from public.demandas where id like 'tst-%'")[0]['n'], "| usuários:", sql("select string_agg(usuario,',') u from public.pessoas")[0]['u']); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
