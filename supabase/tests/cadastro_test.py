"""Teste do cadastro pelo próprio perfil. Uso: SB=<token do Supabase> CODIGO_EQUIPE=<código> python3 cadastro_test.py"""
import os, requests
SB=os.environ['SB']; CODIGO=os.environ['CODIGO_EQUIPE']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB}
sql=lambda q: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":q}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json()
ANON=[k['api_key'] for k in keys if k['name']=='anon'][0]
FN=f"{BASE}/functions/v1/criar-perfil"; res=[]
def chk(n,c): res.append(bool(c)); print(("OK   " if c else "FALHOU ")+n)
def cria(**kw):
    b={"codigo":CODIGO,"nome":"Pessoa de Teste","usuario":"x","senha":"SenhaForte123"}; b.update(kw); return requests.post(FN, json=b, timeout=60)
try:
    chk("código errado recusado", cria(usuario="teste1", codigo="ERRADO99").status_code==403)
    chk("usuário inválido recusado", cria(usuario="a b").status_code==400)
    chk("senha curta recusada", cria(usuario="teste1", senha="1234567").status_code==400)
    chk("cria perfil (normaliza acento e maiúscula)", cria(usuario="João.Teste", nome="João de Teste").json().get("usuario")=="joao.teste")
    chk("usuário repetido recusado", cria(usuario="joao.teste").status_code==409)
    chk("e-mail interno na caixa central", sql("select email from public.pessoas where usuario='joao.teste'")[0]['email']=='demandasbm+joao.teste@gmail.com')
    chk("nasce como leitor, sem acesso", sql("select papel from public.pessoas where usuario='joao.teste'")[0]['papel']=='leitor')
    t=requests.post(f"{BASE}/auth/v1/token?grant_type=password", headers={"apikey":ANON}, json={"email":"demandasbm+joao.teste@gmail.com","password":"SenhaForte123"})
    chk("entra com a senha", t.status_code==200)
    chk("sem acesso, não vê áreas", requests.get(f"{BASE}/rest/v1/areas", headers={"apikey":ANON,"Authorization":"Bearer "+t.json()["access_token"]}).json()==[])
finally:
    sql("delete from auth.users where email like 'demandasbm+%.teste@gmail.com'")
print(f"{sum(res)} de {len(res)} verificações passaram")
