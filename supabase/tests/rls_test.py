import os, json, secrets, urllib.request, urllib.error
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"
def http(method, url, headers=None, body=None):
    h={"User-Agent":"demando-test"}; h.update(headers or {})
    data=json.dumps(body).encode() if body is not None else None
    if data: h.setdefault("Content-Type","application/json")
    req=urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        r=urllib.request.urlopen(req, timeout=60); txt=r.read().decode(); st=r.status
    except urllib.error.HTTPError as e:
        txt=e.read().decode(); st=e.code
    try: return st, json.loads(txt) if txt else None
    except Exception: return st, txt
def mgmt(sql):
    st,b=http("POST", f"https://api.supabase.com/v1/projects/{REF}/database/query", {"Authorization":"Bearer "+SB}, {"query":sql}); return b
# chaves (não são impressas)
st,keys=http("GET", f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", {"Authorization":"Bearer "+SB})
ANON=[k['api_key'] for k in keys if k.get('name')=='anon'][0]; SERVICE=[k['api_key'] for k in keys if k.get('name')=='service_role'][0]
def rest(method, path, tok=None, body=None, prefer="return=representation"):
    h={"apikey":ANON, "Authorization":"Bearer "+(tok or ANON), "Prefer":prefer}
    return http(method, f"{BASE}/rest/v1/{path}", h, body)
def auth_admin(method, path, body=None):
    return http(method, f"{BASE}/auth/v1/admin/{path}", {"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}, body)
res=[]
def check(nome, ok, detalhe=""):
    res.append(ok); print(("  ✅ " if ok else "  ❌ ")+nome+(" — "+str(detalhe) if detalhe else ""))
users={}
try:
    mgmt("delete from public.demandas where id like 'tst-%'")
    for papel in ("admin","membro","leitor"):
        em=f"teste-{papel}-{secrets.token_hex(3)}@example.com"; pw=secrets.token_urlsafe(18)
        st,u=auth_admin("POST","users",{"email":em,"password":pw,"email_confirm":True})
        assert st in (200,201), (st,u)
        users[papel]={"id":u["id"],"email":em,"pw":pw}
    print("Usuários de teste criados:", {k:v["email"].split("@")[0] for k,v in users.items()})
    print("Gatilho de novo usuário (todos entram como leitor, sem acesso):", [(r['email'].split('@')[0], r['papel']) for r in mgmt("select email, papel from public.pessoas where email like 'teste-%' order by 1")])
    mgmt(f"update public.pessoas set papel='admin' where id='{users['admin']['id']}'")
    mgmt(f"update public.pessoas set papel='membro' where id='{users['membro']['id']}'")
    mgmt(f"insert into public.acessos(pessoa_id, area_id) values ('{users['membro']['id']}','asc')")
    for papel,u in users.items():
        st,t=http("POST", f"{BASE}/auth/v1/token?grant_type=password", {"apikey":ANON}, {"email":u["email"],"password":u["pw"]})
        assert st==200, (papel, st, t); u["tok"]=t["access_token"]
    A,M,L=users["admin"],users["membro"],users["leitor"]
    print("\n== SEM LOGIN (anônimo)")
    st,b=rest("GET","demandas"); check("não lê demandas", st in (200,401,403) and (b==[] or st!=200), f"HTTP {st} {b if b!=[] else '[] (vazio)'}")
    st,b=rest("POST","demandas",None,{"id":"tst-anon","area_id":"fed","titulo":"x"}); check("não cria demanda", st in (401,403), f"HTTP {st}")
    st,b=rest("GET","areas"); check("não vê áreas", st!=200 or b==[], f"HTTP {st}")
    print("\n== ADMIN")
    st,b=rest("POST","demandas",A["tok"],{"id":"tst-fed-1","area_id":"fed","titulo":"Teste FAF","criado_por":A["id"]}); check("cria demanda na FAF", st==201, f"HTTP {st}")
    st,b=rest("POST","demandas",A["tok"],{"id":"tst-asc-1","area_id":"asc","titulo":"Teste BM do admin","criado_por":A["id"],"status":"A fazer"}); check("cria demanda na BM", st==201, f"HTTP {st}")
    st,b=rest("GET","demandas?id=like.tst-*",A["tok"]); check("vê as duas", st==200 and len(b)==2, f"{len(b) if isinstance(b,list) else b} demandas")
    print("\n== MEMBRO (só BM)")
    st,b=rest("GET","demandas?id=like.tst-*",M["tok"]); check("vê só as da BM", st==200 and [x['id'] for x in b]==['tst-asc-1'], [x['id'] for x in b] if isinstance(b,list) else b)
    st,b=rest("GET","areas",M["tok"]); check("vê só a área BM", st==200 and [x['id'] for x in b]==['asc'], [x['id'] for x in b] if isinstance(b,list) else b)
    st,b=rest("POST","demandas",M["tok"],{"id":"tst-fed-2","area_id":"fed","titulo":"Invasão","criado_por":M["id"]}); check("NÃO cria na FAF", st in (401,403), f"HTTP {st}")
    st,b=rest("POST","demandas",M["tok"],{"id":"tst-asc-2","area_id":"asc","titulo":"Criada pelo membro","criado_por":M["id"]}); check("cria na BM", st==201, f"HTTP {st}")
    st,b=rest("POST","demandas",M["tok"],{"id":"tst-asc-3","area_id":"asc","titulo":"Falsa autoria","criado_por":A["id"]}); check("NÃO cria em nome de outra pessoa", st in (401,403), f"HTTP {st}")
    st,b=rest("PATCH","demandas?id=eq.tst-asc-1",M["tok"],{"status":"Em produção"}); check("muda a etapa de demanda de outro", st==200 and b and b[0]['status']=='Em produção', f"HTTP {st}")
    st,b=rest("PATCH","demandas?id=eq.tst-asc-1",M["tok"],{"titulo":"Mudei o título dos outros"}); check("NÃO edita o título de demanda de outro", st>=400, f"HTTP {st} {str(b)[:80]}")
    st,b=rest("PATCH","demandas?id=eq.tst-asc-2",M["tok"],{"titulo":"Editei a minha"}); check("edita a própria", st==200 and b and b[0]['titulo']=='Editei a minha', f"HTTP {st}")
    st,b=rest("DELETE","demandas?id=eq.tst-asc-1",M["tok"]); check("NÃO apaga demanda de outro", st==200 and b==[], f"HTTP {st} apagou {len(b) if isinstance(b,list) else b}")
    st,b=rest("POST","comentarios",M["tok"],{"id":"tst-c1","demanda_id":"tst-asc-1","texto":"Comentário de teste","por":M["id"],"autor":"Teste"}); check("comenta em demanda da BM", st==201, f"HTTP {st}")
    st,b=rest("GET","demandas?id=eq.tst-asc-1&select=n_coment",A["tok"]); check("contador de comentários atualizou", st==200 and b[0]['n_coment']==1, b)
    st,b=rest("PATCH",f"pessoas?id=eq.{M['id']}",M["tok"],{"papel":"admin"}); check("NÃO vira admin sozinho", st>=400 or b==[], f"HTTP {st} {str(b)[:60]}")
    st,b=rest("POST","areas",M["tok"],{"id":"xx","sigla":"XX","nome":"Invasão","cor":"#000000"}); check("NÃO cria área", st in (401,403), f"HTTP {st}")
    st,b=rest("GET","pessoas",M["tok"]); check("vê só a si mesmo em pessoas", st==200 and len(b)==1, f"{len(b) if isinstance(b,list) else b} linha")
    st,b=rest("DELETE","demandas?id=eq.tst-asc-2",M["tok"]); check("apaga a própria", st==200 and len(b)==1, f"HTTP {st}")
    print("\n== LEITOR (sem acesso a nenhuma área)")
    st,b=rest("GET","demandas?id=like.tst-*",L["tok"]); check("não vê demandas", st==200 and b==[], f"{len(b) if isinstance(b,list) else b}")
    st,b=rest("GET","areas",L["tok"]); check("não vê áreas", st==200 and b==[], f"{len(b) if isinstance(b,list) else b}")
    st,b=rest("POST","demandas",L["tok"],{"id":"tst-l","area_id":"asc","titulo":"x","criado_por":L["id"]}); check("não cria demanda", st in (401,403), f"HTTP {st}")
finally:
    mgmt("delete from public.demandas where id like 'tst-%'")
    for papel,u in users.items(): auth_admin("DELETE", f"users/{u['id']}")
    print("\nLimpeza: demandas de teste e usuários removidos →", mgmt("select (select count(*) from public.demandas) as demandas, (select count(*) from public.pessoas) as pessoas, (select count(*) from public.acessos) as acessos"))
print(f"\nRESULTADO: {sum(res)} de {len(res)} verificações passaram")
