"""Lixeira: apagar pelo app guarda a demanda (com quem apagou), restaurar traz de volta, apagar direto no servidor não entra.
Uso: SB=<token Supabase> ADMIN_SENHA=<senha do admin> python3 tests/lixeira_test.py   (rode da raiz do repositório)"""
import os, subprocess, sys, requests
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); ANON=[k['api_key'] for k in keys if k['name']=='anon'][0]
ADMIN=os.environ['ADMIN_SENHA']; res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:100] if d else ""))
adm=sql("select id from public.pessoas where usuario='admin'")[0]['id']
tok=requests.post(f"{BASE}/auth/v1/token?grant_type=password", headers={"apikey":ANON}, json={"email":"demandasbm+admin@gmail.com","password":ADMIN}).json()["access_token"]
H={"apikey":ANON,"Authorization":"Bearer "+tok,"Content-Type":"application/json","Prefer":"return=minimal"}
run=lambda *a: subprocess.run([sys.executable,*a],capture_output=True,text=True,env=dict(os.environ))
try:
    for i in ("tst-lx1","tst-lx2"): requests.post(f"{BASE}/rest/v1/demandas", headers=H, json={"id":i,"area_id":"asc","titulo":"LIXEIRA teste "+i,"status":"A fazer","equipe":["Celso"],"criado_por":adm,"criado_em":"2026-01-01T12:00:00+00:00"})
    chk("apagar pelo app funciona", requests.delete(f"{BASE}/rest/v1/demandas?id=eq.tst-lx1", headers=H).status_code in (200,204))
    L=sql("select linha->>'titulo' t, apagado_por::text por from public.lixeira where registro_id='tst-lx1'"); chk("a demanda foi parar na lixeira, com quem apagou", len(L)==1 and L[0]['por']==adm, L)
    sql("delete from public.demandas where id='tst-lx2'"); chk("apagar direto no servidor NÃO entra na lixeira", sql("select count(*) n from public.lixeira where registro_id='tst-lx2'")[0]['n']==0)
    o=run("tools/restaurar_demanda.py","tst-lx1").stdout; D=sql("select equipe from public.demandas where id='tst-lx1'"); chk("restaurar traz a demanda de volta, igual", "restaurada" in o and D and D[0]['equipe']==['Celso'], o.strip())
    o2=run("tools/restaurar_demanda.py","tst-lx1"); chk("restaurar de novo avisa e não duplica nem quebra", o2.returncode==0 and "nada a restaurar" in o2.stdout)
    chk("anônimo não lê a lixeira", requests.get(f"{BASE}/rest/v1/lixeira?select=id", headers={"apikey":ANON,"Authorization":"Bearer "+ANON}).json()==[])
finally:
    sql("delete from public.demandas where id like 'tst-lx%'"); sql("delete from public.lixeira where registro_id like 'tst-lx%'")
print(f"RESULTADO: {sum(res)} de {len(res)}")
