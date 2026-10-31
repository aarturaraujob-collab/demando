#!/usr/bin/env python3
"""Painel do Claude → site (Supabase), sem pisar em nada que mudou no site.
Uso:  SB=<token Supabase> python3 tools/sincronizar_painel.py <pasta com os JSON das demandas do painel> [--aplicar] [--semear <pasta>] [--aceitar id1,id2]
  sem --aplicar só MOSTRA o que faria (não altera nada).
  --semear <pasta>   grava a "foto" inicial: considera que o site já tem o conteúdo desses arquivos (use na primeira vez).
  --aceitar ids      depois de resolver um conflito à mão, marca o painel e o site como "já conferidos".
Regra, demanda por demanda (comparando painel, site e a foto da última sincronização):
  só existe no painel  → traz pro site            só o painel mudou → atualiza o site
  só o site mudou      → mantém o site            os dois mudaram   → NÃO mexe, mostra o conflito
  --restaurar ids    traz de volta do painel demandas que foram apagadas no site.
Nunca apaga nada: demandas apagadas no painel só aparecem num aviso; as apagadas no site não voltam sozinhas."""
import os, sys, json, glob, hashlib, tempfile, shutil, subprocess, requests
SB = os.environ["SB"]; REF = "uaakiytxphmtwsthooih"; M = {"Authorization": "Bearer " + SB, "User-Agent": "demando-sync"}
args = sys.argv[1:]; flag = lambda f: f in args
def val(f): return args[args.index(f) + 1] if f in args and args.index(f) + 1 < len(args) else None
pastas = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or args[i-1] not in ("--semear", "--aceitar", "--restaurar"))]
PASTA = pastas[0] if pastas else None; APLICAR = flag("--aplicar"); SEMEAR = val("--semear"); ACEITAR = set(filter(None, (val("--aceitar") or "").split(","))); RESTAURAR = set(filter(None, (val("--restaurar") or "").split(",")))
def sql(q): r = requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query": q}); r.raise_for_status(); return r.json()
sql("create table if not exists public.sync_painel (id text primary key, p text not null, s text not null, em timestamptz not null default now()); alter table public.sync_painel enable row level security;")
nz = lambda v: None if v in ("", None) else v
def canon(d, site=False):
    g = (lambda k: d.get(k)) if not site else (lambda k: d.get({"frente": "area_id"}.get(k, k)))
    return {"area_id": g("frente"), "titulo": (g("titulo") or "")[:140], "tipo": nz(g("tipo")), "prazo": nz(g("prazo")), "hora": (nz(g("hora")) or "")[:5] or None, "local": nz(g("local")),
            "status": "Em produção" if g("status") == "Aprovação" else g("status"), "equipe": g("equipe") or [], "secretaria": nz(g("secretaria")), "perfil": nz(g("perfil")), "obs": nz(g("obs")),
            "solicitante": nz(g("solicitante")), "entregue": nz(g("entregue")), "checklist": [[c.get("t"), bool(c.get("ok"))] for c in (g("checklist") or [])], "anexos": [a.get("nome") for a in (g("anexos") or [])]}
H = lambda c: hashlib.sha1(json.dumps(c, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]
def ler(pasta):
    out = {}
    for f in glob.glob(os.path.join(pasta, "*.json")):
        d = json.load(open(f)); d = d["data"] if isinstance(d, dict) and "data" in d and "titulo" not in d else d; out[d["id"]] = d
    return out
up = lambda i, p, s: sql(f"insert into public.sync_painel(id,p,s) values ('{i}','{p}','{s}') on conflict (id) do update set p=excluded.p, s=excluded.s, em=now()")
if SEMEAR:
    for i, d in ler(SEMEAR).items(): h = H(canon(d)); up(i, h, h)
    print(f"foto inicial gravada para {len(ler(SEMEAR))} demandas"); 
    if not PASTA: sys.exit(0)
painel = ler(PASTA)
site = {r["id"]: r for r in sql("select id, area_id, titulo, tipo, prazo::text prazo, hora::text hora, local, status, equipe, secretaria, perfil, obs, solicitante, entregue::text entregue, checklist, anexos from public.demandas")}
base = {r["id"]: r for r in sql("select id, p, s from public.sync_painel")}
novos, atualizar, manter, conflitos, sem_ref, iguais, apagadas_site = [], [], [], [], [], [], []
for i, d in painel.items():
    P = H(canon(d))
    if i not in site:
        (apagadas_site if (i in base and i not in RESTAURAR) else novos).append(i); continue
    S = H(canon(site[i], True)); b = base.get(i)
    if i in ACEITAR: up(i, P, S); iguais.append(i); continue
    if P == S: iguais.append(i); up(i, P, S); continue
    if not b: sem_ref.append(i); continue
    pm, sm = P != b["p"], S != b["s"]
    (atualizar if pm and not sm else manter if sm and not pm else conflitos if pm and sm else iguais).append(i)
so_site = [i for i in site if i not in painel]; apagadas = [i for i in base if i not in painel]
t = lambda i: (painel.get(i) or site.get(i))["titulo"][:62]
print(f"painel: {len(painel)} demandas | site: {len(site)} demandas\n")
for nome, lst in (("NOVAS no painel → vão pro site", novos), ("PAINEL mudou → site será atualizado", atualizar), ("SITE mudou → mantido como está", manter)):
    print(f"{nome}: {len(lst)}"); [print("   ", i, "·", t(i)) for i in lst]
print(f"CONFLITO (os dois mudaram, nada será alterado): {len(conflitos) + len(sem_ref)}")
for i in conflitos + sem_ref: print("   ", i, "·", t(i), "(sem foto anterior)" if i in sem_ref else "")
print(f"iguais nos dois lados: {len(iguais)}")
if so_site: print(f"\nsó no site (criadas lá): {len(so_site)}"); [print("   ", i, "·", t(i)) for i in so_site]
if apagadas_site:
    quem = {r["registro_id"]: r for r in sql("select l.registro_id, coalesce(p.usuario,'(servidor)') quem, to_char(l.apagado_em at time zone 'America/Maceio','DD/MM HH24:MI') quando from public.lixeira l left join public.pessoas p on p.id = l.apagado_por where l.tabela='demandas' and l.restaurado_em is null order by l.id")}
    print(f"\nAPAGADAS NO SITE (de propósito? NÃO serão trazidas de volta; use --restaurar id se foi engano): {len(apagadas_site)}")
    for i in apagadas_site: q = quem.get(i); print("   ", i, "·", t(i), f"· apagada por {q['quem']} em {q['quando']}" if q else "· (sem registro de quem apagou: foi antes da lixeira)")
if apagadas: print(f"\nAPAGADAS no painel desde a última vez (o site NÃO apaga sozinho): {len(apagadas)}"); [print("   ", i) for i in apagadas]
if APLICAR and (novos or atualizar):
    tmp = tempfile.mkdtemp(); os.makedirs(os.path.join(tmp, "demandas", "demandas"))
    for i in novos + atualizar: shutil.copy(os.path.join(PASTA, i + ".json"), os.path.join(tmp, "demandas", "demandas", i + ".json"))
    for cand in (os.path.join(PASTA, "..", "assets"), os.path.join(PASTA, "assets")):
        if os.path.isdir(cand): os.symlink(os.path.abspath(cand), os.path.join(tmp, "assets")); break
    env = dict(os.environ, SO=",".join(novos + atualizar)); print("\naplicando…")
    subprocess.run([sys.executable, os.path.join(os.path.dirname(__file__), "importar_do_claude.py"), tmp], env=env, check=True)
    for i in novos + atualizar: h = H(canon(painel[i])); up(i, h, h)
elif not APLICAR and (novos or atualizar): print("\n(ensaio: nada foi alterado. Rode de novo com --aplicar)")
print("\nRESULTADO:", "tudo em dia" if not (novos or atualizar or conflitos or sem_ref or apagadas_site) else "há pendências acima")
