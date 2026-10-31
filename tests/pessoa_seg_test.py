"""O que cada pessoa pode (e não pode) mudar no próprio cadastro.
Uso: SB=<token> CODIGO_EQUIPE=<código> python3 tests/pessoa_seg_test.py"""
import os, requests, json
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); ANON=[k['api_key'] for k in keys if k['name']=='anon'][0]; SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}
CODIGO=os.environ['CODIGO_EQUIPE']; res=[]; uid=None
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:110] if d else ""))
try:
    requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Pessoa Seg","usuario":"tst.seg","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.seg'")[0]['id']
    sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
    tok=requests.post(f"{BASE}/auth/v1/token?grant_type=password", headers={"apikey":ANON}, json={"email":"demandasbm+tst.seg@gmail.com","password":"SenhaForte123"}).json()["access_token"]
    R=lambda b: requests.patch(f"{BASE}/rest/v1/pessoas?id=eq.{uid}", headers={"apikey":ANON,"Authorization":"Bearer "+tok,"Content-Type":"application/json","Prefer":"return=representation"}, json=b)
    est=lambda: sql(f"select papel, ativo, usuario, email, nome_equipe, nome from public.pessoas where id='{uid}'")[0]
    print("== O QUE UMA PESSOA CONSEGUE MUDAR NO PRÓPRIO CADASTRO")
    R({"nome_equipe":"Celso"}); chk("escolher o próprio nome na equipe (deve poder)", est()['nome_equipe']=="Celso", est()['nome_equipe'])
    R({"papel":"admin"}); chk("virar admin sozinha (NÃO deve)", est()['papel']=='membro', est()['papel'])
    sql(f"update public.pessoas set ativo=false where id='{uid}'")
    r=R({"ativo":True}); chk("depois de desativada, se reativar sozinha (NÃO deve)", est()['ativo'] is False, f"ativo agora = {est()['ativo']}")
    sql(f"update public.pessoas set ativo=true where id='{uid}'")
    R({"usuario":"admin"}); chk("trocar o 'usuário' (NÃO deve)", est()['usuario']=='tst.seg', est()['usuario'])
    R({"email":"outra@x.com"}); chk("trocar o e-mail interno (NÃO deve)", est()['email'].startswith('demandasbm+tst.seg'), est()['email'])
    R({"nome_equipe":"Fulano Inexistente"}); chk("escolher um nome que não existe na equipe da área dela (NÃO deve)", est()['nome_equipe']!="Fulano Inexistente", est()['nome_equipe'])
    R({"nome_equipe":"Sara"}); chk("escolher outro nome da equipe da BM (deve poder)", est()['nome_equipe']=="Sara", est()['nome_equipe'])
    R({"nome":"Nome Novo"}); chk("mudar o próprio nome de exibição (deve poder)", est()['nome']=="Nome Novo")
finally:
    if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
    print("limpeza → usuários:", sql("select count(*) n from auth.users")[0]['n'])
print(f"RESULTADO: {sum(res)} de {len(res)}")
