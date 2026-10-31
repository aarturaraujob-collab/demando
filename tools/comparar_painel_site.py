#!/usr/bin/env python3
"""Compara as demandas do painel do Claude (export mais recente) com as do site (Supabase): novas, alteradas e só-no-site.
Uso: SB=<token Supabase> python3 tools/comparar_painel_site.py <pasta do export, com demandas/*.json>   (não altera nada)"""
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-diff"}
q=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
EXP=sys.argv[1] if len(sys.argv)>1 else '/mnt/user-data/outputs/export_novo'
def ler(sub):
    out={}
    for f in glob.glob(f"{EXP}/{sub}/*.json"):
        d=json.load(open(f)); meta={k:d.get(k) for k in ('version','updatedAt')}; dd=d['data'] if isinstance(d,dict) and 'data' in d else d; dd['_meta']=meta; out[dd.get('id') or os.path.basename(f)[:-5]]=dd
    return out
cl=ler('demandas')
db={r['id']:r for r in q("select id, area_id, titulo, tipo, prazo::text prazo, hora::text hora, local, status, equipe, secretaria, perfil, obs, entregue::text entregue, checklist, anexos, n_coment, atualizado_em::text atualizado from public.demandas")}
nz=lambda v: None if v in ("",None) else v
def norm_cl(d): return {"area_id":d.get("frente"),"titulo":d.get("titulo"),"tipo":nz(d.get("tipo")),"prazo":nz(d.get("prazo")),"hora":(nz(d.get("hora")) or None),"local":nz(d.get("local")),"status":"Em produção" if d.get("status")=="Aprovação" else d.get("status"),"equipe":d.get("equipe") or [],"secretaria":nz(d.get("secretaria")),"perfil":nz(d.get("perfil")),"obs":nz(d.get("obs")),"entregue":nz(d.get("entregue")),"checklist":d.get("checklist") or [],"n_anexos":len(d.get("anexos") or [])}
def norm_db(r): 
    h=r['hora']; h=h[:5] if h else None
    return {"area_id":r['area_id'],"titulo":r['titulo'],"tipo":r['tipo'],"prazo":r['prazo'],"hora":h,"local":r['local'],"status":r['status'],"equipe":r['equipe'] or [],"secretaria":r['secretaria'],"perfil":r['perfil'],"obs":r['obs'],"entregue":r['entregue'],"checklist":r['checklist'] or [],"n_anexos":len(r['anexos'] or [])}
novos=[i for i in cl if i not in db]; so_site=[i for i in db if i not in cl]; mudou={}
for i in cl:
    if i in db:
        a,b=norm_cl(cl[i]),norm_db(db[i]); dif={k:(a[k],b[k]) for k in a if a[k]!=b[k] and not (k=='hora' and (a[k] or '')[:5]==(b[k] or '')[:5])}
        if dif: mudou[i]=dif
print(f"painel do Claude: {len(cl)} | site (Supabase): {len(db)}")
print(f"\nNOVAS no painel e AUSENTES no site: {len(novos)}")
for i in sorted(novos, key=lambda x: cl[x].get('prazo') or ''): d=cl[i]; print(f"  {i}  [{d.get('frente')}] {d.get('prazo') or 'sem prazo'} · {d.get('status')} · {d['titulo'][:60]}  (nComent={d.get('nComent',0)}, anexos={len(d.get('anexos') or [])}, v{d['_meta']['version']})")
print(f"\nMUDARAM no painel (mesmo id, conteúdo diferente do site): {len(mudou)}")
for i,dif in mudou.items(): print(f"  {i} {cl[i]['titulo'][:45]}: " + "; ".join(f"{k}: site={str(b)[:30]!r} → painel={str(a)[:30]!r}" for k,(a,b) in dif.items()))
print(f"\nSÓ NO SITE (não existem no painel): {len(so_site)}")
for i in so_site: print(f"  {i} · {db[i]['titulo'][:60]} · {db[i]['area_id']} · {db[i]['status']}")
print("\ncom comentários no painel:", [(i, cl[i].get('nComent')) for i in cl if cl[i].get('nComent')])
json.dump({"novos":novos,"mudou":list(mudou),"so_site":so_site}, open('/tmp/diff.json','w'))
