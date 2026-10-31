#!/usr/bin/env python3
"""Leva os dados do painel do Claude pro Supabase (demandas, áreas extras e anexos). Pode rodar de novo: atualiza o que já veio.
Uso: SB=<token do Supabase> [SO=id1,id2] python3 tools/importar_do_claude.py <pasta do export>   (SO traz só as demandas citadas)
A pasta do export tem: demandas/demandas/*.json, areas/areas/*.json, assets/<id>.<ext> (arquivos dos anexos)."""
import os, sys, json, glob, re, datetime, unicodedata, mimetypes, requests
SB = os.environ["SB"]; ONLY = set(filter(None, os.environ.get("SO", "").split(","))); REF = "uaakiytxphmtwsthooih"; BASE = f"https://{REF}.supabase.co"; EXP = sys.argv[1]
M = {"Authorization": "Bearer " + SB, "User-Agent": "demando-import"}
keys = requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json()
SERVICE = [k["api_key"] for k in keys if k["name"] == "service_role"][0]
SV = {"apikey": SERVICE, "Authorization": "Bearer " + SERVICE}
def ler(pat):
    out = []
    for f in sorted(glob.glob(os.path.join(EXP, pat))):
        d = json.load(open(f)); out.append(d["data"] if isinstance(d, dict) and "data" in d and "id" not in d else d)
    return out
nz = lambda v: None if v in ("", None) else v
def iso_ms(ms): return datetime.datetime.fromtimestamp(ms / 1000, datetime.timezone.utc).isoformat() if ms else None
def slug(s): s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode(); return re.sub(r"[^A-Za-z0-9._-]+", "-", s).strip("-")[-60:] or "arquivo"

# 1) áreas extras (a FAF e a BM já existem no banco)
for a in ler("areas/areas/*.json"):
    if a["id"] in ("fed", "asc") or ONLY: continue
    row = {"id": a["id"], "sigla": a["sigla"], "nome": a["nome"], "cor": a["cor"], "equipe": a.get("equipe") or [], "perfis": a.get("perfis") or [], "tipos": a.get("tipos") or [], "so_admin": bool(a.get("soAdmin")), "ordem": 3, "criado_em": iso_ms(a.get("criado")), "removida": False}
    r = requests.post(f"{BASE}/rest/v1/areas", headers=dict(SV, **{"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates"}), json=[row]); print("área", a["id"], a["nome"], "→", r.status_code)

# 2) anexos: reenvia os arquivos pro Storage do Supabase e troca o link
def novo_anexo(a):
    if not a.get("id") or a.get("tipo") == "link": return a
    cand = glob.glob(os.path.join(EXP, "assets", a["id"] + ".*"))
    if not cand: print("   ⚠ arquivo não encontrado:", a.get("nome")); return a
    nome = a.get("nome") or "arquivo"; path = f"migracao/{a['id'][:8]}-{slug(nome)}"; mime = a.get("mime") or mimetypes.guess_type(cand[0])[0] or "application/octet-stream"
    up = requests.post(f"{BASE}/storage/v1/object/anexos/{path}", headers=dict(SV, **{"Content-Type": mime, "x-upsert": "true"}), data=open(cand[0], "rb").read())
    if up.status_code not in (200, 201): print("   ⚠ falhou o envio de", nome, up.status_code, up.text[:100]); return a
    sg = requests.post(f"{BASE}/storage/v1/object/sign/anexos/{path}", headers=dict(SV, **{"Content-Type": "application/json"}), json={"expiresIn": 31536000}).json()
    print("   anexo enviado:", nome, f"({os.path.getsize(cand[0])//1024} KB)")
    return {"tipo": "arquivo", "nome": nome, "url": BASE + "/storage/v1" + sg["signedURL"], "id": path, "mime": mime, "tam": a.get("tam")}

# 3) demandas
linhas = []
for d in ler("demandas/demandas/*.json"):
    if ONLY and d["id"] not in ONLY: continue          # SO=id1,id2 → traz só essas demandas
    linhas.append({"id": d["id"], "area_id": d["frente"], "titulo": d["titulo"][:140], "tipo": nz(d.get("tipo")), "prazo": nz(d.get("prazo")), "hora": nz(d.get("hora")), "local": nz(d.get("local")),
        "status": "Em produção" if d.get("status") == "Aprovação" else d["status"], "prioridade": d.get("prioridade") if d.get("prioridade") in ("Baixa", "Média", "Alta") else "Média",
        "solicitante": nz(d.get("solicitante")), "secretaria": nz(d.get("secretaria")), "perfil": nz(d.get("perfil")), "equipe": d.get("equipe") or [], "obs": nz(d.get("obs")), "original": nz(d.get("original")), "link": nz(d.get("link")),
        "checklist": d.get("checklist") or [], "anexos": [novo_anexo(a) for a in (d.get("anexos") or [])], "historico": d.get("historico") or [], "criado": nz(d.get("criado")) or datetime.date.today().isoformat(),
        "entregue": nz(d.get("entregue")), "recorrente_id": nz(d.get("recorrente")), "n_coment": 0, "criado_por": None, "criado_em": iso_ms(d.get("criadoEm")) or ((nz(d.get("criado")) or datetime.date.today().isoformat()) + "T12:00:00+00:00")})
r = requests.post(f"{BASE}/rest/v1/demandas", headers=dict(SV, **{"Content-Type": "application/json", "Prefer": "resolution=merge-duplicates,return=minimal,missing=default"}), json=linhas)
print(f"demandas: {len(linhas)} enviadas → HTTP {r.status_code}", r.text[:200])
