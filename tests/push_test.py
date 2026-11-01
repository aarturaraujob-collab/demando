"""Avisos no celular em ensaio (não envia de verdade): gatilhos, quem recebe e criptografia.
Uso: SB=<token> PUSH_SECRET=<segredo interno> CODIGO_EQUIPE=<código> python3 tests/push_test.py"""
import os, json, base64, secrets, time, requests
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]
SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}; V={"push_secret": os.environ.get("PUSH_SECRET","")}; CODIGO=os.environ["CODIGO_EQUIPE"]
b64u=lambda b: base64.urlsafe_b64encode(b).rstrip(b'=').decode(); FN=f"{BASE}/functions/v1/enviar-push"
res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:130] if d else ""))
def espera(n_antes, s=10):
    for _ in range(s*2):
        n=sql("select count(*) n from public.push_log")[0]['n']
        if n>n_antes: time.sleep(0.5); return sql("select tipo, demanda_id, destinatarios, enviados, simulado, detalhe from public.push_log order by id desc limit 1")[0]
        time.sleep(0.5)
    return None
def sem_aviso(n_antes, s=4): time.sleep(s); return sql("select count(*) n from public.push_log")[0]['n']==n_antes
def ins(id, area, eq, **kw):
    cols={"id":id,"area_id":area,"titulo":"PUSH-"+id,"prazo":kw.get("prazo",None),"status":kw.get("status","A fazer"),"equipe":eq,"criado_por":kw.get("por"),**({"criado_em":kw["criado_em"]} if "criado_em" in kw else {})}
    return requests.post(f"{BASE}/rest/v1/demandas", headers=dict(SV,**{"Content-Type":"application/json","Prefer":"return=minimal"}), json=cols)
uid=None
try:
    sql("delete from public.demandas where titulo like 'PUSH-%'"); sql("delete from public.push_log")
    print("== SEGURANÇA DA FUNÇÃO")
    chk("sem o segredo interno: recusa (401)", requests.post(FN, json={"tipo":"resumo"}).status_code==401)
    chk("com segredo errado: recusa (401)", requests.post(FN, headers={"x-push-secret":"errado"}, json={"tipo":"resumo"}).status_code==401)
    requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Celso Teste","usuario":"tst.push","senha":"SenhaForte123"})
    uid=sql("select id from public.pessoas where usuario='tst.push'")[0]['id']; adm=sql("select id from public.pessoas where usuario='admin'")[0]['id']
    sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
    k=ec.generate_private_key(ec.SECP256R1()); p256=b64u(k.public_key().public_bytes(serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint)); auth=b64u(secrets.token_bytes(16))
    sql(f"insert into public.push_subs(pessoa_id, endpoint, p256dh, auth) values ('{uid}','https://push.example.invalid/teste','{p256}','{auth}')")
    sql(f"update public.config_interna set valor = valor || '?simulado=1' where chave='push_url' and valor not like '%simulado%'")   # ensaio: não envia de verdade
    print("== GATILHOS (ensaio, sem enviar de verdade)")
    n=sql("select count(*) n from public.push_log")[0]['n']
    ins("p1","asc",["Celso"], prazo=None, por=adm); r=espera(n)
    chk("demanda nova com 'Celso' na equipe → avisa o Celso", r and r['tipo']=='nova' and r['destinatarios']==1 and r['enviados']==1 and r['simulado'], r)
    chk("a mensagem foi criptografada pro aparelho", r and r['detalhe'] and r['detalhe'][0].get('criptografado') is True and r['detalhe'][0]['titulo']=='Nova escala', r['detalhe'] if r else None)
    n=sql("select count(*) n from public.push_log")[0]['n']; ins("p2","fed",["Celso"], por=adm); r=espera(n)
    chk("demanda da FAF (ele só tem a BM) → ninguém é avisado", r and r['destinatarios']==0, r)
    n=sql("select count(*) n from public.push_log")[0]['n']; ins("p3","asc",["Celso"], por=uid); r=espera(n)
    chk("quem criou a própria demanda NÃO é avisado", r and r['destinatarios']==0, r)
    n=sql("select count(*) n from public.push_log")[0]['n']; ins("p4","asc",["Celso"], por=adm, criado_em="2026-01-01T12:00:00+00:00")
    chk("dado antigo importado NÃO gera aviso", sem_aviso(n))
    n=sql("select count(*) n from public.push_log")[0]['n']; ins("p5","asc",[], por=adm); time.sleep(1)
    chk("demanda sem equipe NÃO gera aviso", sem_aviso(n, 3))
    n=sql("select count(*) n from public.push_log")[0]['n']; sql("update public.demandas set equipe='{Celso,Sara}' where id='p5'"); r=espera(n)
    chk("escalar o Celso depois → 'Você foi escalado'", r and r['tipo']=='escala' and r['destinatarios']==1 and r['detalhe'][0]['titulo']=='Você foi escalado', r and r['tipo'])
    n=sql("select count(*) n from public.push_log")[0]['n']; sql("update public.demandas set equipe='{Celso,Sara,Mauro}' where id='p5'"); r=espera(n)
    chk("escalar outra pessoa NÃO avisa quem já estava", r and r['destinatarios']==0, r)
    n=sql("select count(*) n from public.push_log")[0]['n']; sql("update public.demandas set titulo='PUSH-p5 editado' where id='p5'")
    chk("editar o título NÃO gera aviso", sem_aviso(n, 3))
    n=sql("select count(*) n from public.push_log")[0]['n']
    requests.post(f"{BASE}/rest/v1/comentarios", headers=dict(SV,**{"Content-Type":"application/json","Prefer":"return=minimal"}), json={"id":"pc1","demanda_id":"p1","texto":"Direcionamento de teste","fixado":True,"por":adm,"autor":"Admin"}); r=espera(n)
    chk("comentário fixado (direcionamento) → avisa a equipe", r and r['tipo']=='direcionamento' and r['destinatarios']==1, r)
    n=sql("select count(*) n from public.push_log")[0]['n']
    requests.post(f"{BASE}/rest/v1/comentarios", headers=dict(SV,**{"Content-Type":"application/json","Prefer":"return=minimal"}), json={"id":"pc2","demanda_id":"p1","texto":"Comentário comum","fixado":False,"por":adm,"autor":"Admin"})
    chk("comentário comum NÃO gera aviso", sem_aviso(n, 3))
    n=sql("select count(*) n from public.push_log")[0]['n']
    requests.post(f"{BASE}/rest/v1/comentarios", headers=dict(SV,**{"Content-Type":"application/json","Prefer":"return=minimal"}), json={"id":"pc3","demanda_id":"p1","texto":"Eu mesmo direcionei","fixado":True,"por":uid,"autor":"Celso"}); r=espera(n)
    chk("o autor do direcionamento NÃO é avisado", r and r['destinatarios']==0, r)
    print("== RESUMO DO DIA")
    hoje=sql("select (now() at time zone 'America/Maceio')::date::text d")[0]['d']
    ins("p6","asc",["Celso"], prazo=hoje, por=uid); ins("p7","asc",["Celso"], prazo=hoje, status="Entregue", por=uid); ins("p8","asc",["Mauro"], prazo=hoje, por=uid)
    time.sleep(3); n=sql("select count(*) n from public.push_log")[0]['n']
    rr=requests.post(FN+"?simulado=1", headers={"x-push-secret":V['push_secret']}, json={"tipo":"resumo"}).json()
    chk("resumo: avisa quem tem demanda aberta pra hoje (e só as abertas)", rr.get('destinatarios')==1 and rr['itens'][0]['titulo'].startswith('Hoje: 1 demanda'), rr.get('itens'))
    sql(f"update public.pessoas set ativo=false where id='{uid}'"); rr=requests.post(FN+"?simulado=1", headers={"x-push-secret":V['push_secret']}, json={"tipo":"resumo"}).json()
    chk("pessoa desativada NÃO recebe", rr.get('destinatarios')==0, rr)
    print("== AGENDA")
    chk("tarefas diárias agendadas (arquivar 5h30, recorrentes 5h e resumo 8h de Maceió)", [x['jobname'] for x in sql("select jobname from cron.job order by 1")]==['demando-arquivar','demando-recorrentes','demando-resumo'])
finally:
    sql("update public.config_interna set valor = replace(valor, '?simulado=1', '') where chave='push_url'")
    sql("delete from public.comentarios where id like 'pc%'"); sql("delete from public.demandas where titulo like 'PUSH-%'"); sql("delete from public.push_log")
    if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
    print("\nrestaurado: endereço real dos avisos (sem ensaio) →", sql("select valor like '%simulado%' as ensaio_ligado from public.config_interna where chave='push_url'"))
    print("limpeza →", sql("select (select count(*) from auth.users) users, (select string_agg(usuario,',') from public.pessoas) pessoas, (select count(*) from public.demandas where titulo like 'PUSH-%') push, (select count(*) from public.push_subs) subs"))
print(f"RESULTADO: {sum(res)} de {len(res)}")
