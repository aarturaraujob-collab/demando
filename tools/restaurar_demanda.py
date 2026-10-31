#!/usr/bin/env python3
"""Lixeira do Demandô. Sem argumentos: lista o que foi apagado (quem, quando). Com ids: restaura essas demandas.
Uso: SB=<token Supabase> python3 tools/restaurar_demanda.py [id1 id2 ...]"""
import os, sys, requests
SB = os.environ["SB"]; REF = "uaakiytxphmtwsthooih"; M = {"Authorization": "Bearer " + SB, "User-Agent": "demando-lixeira"}
def sql(q): r = requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query": q}); r.raise_for_status(); return r.json()
ids = sys.argv[1:]
if not ids:
    rows = sql("""select l.id, l.registro_id, l.tabela, l.linha->>'titulo' titulo, coalesce(p.usuario,'(servidor)') quem, to_char(l.apagado_em at time zone 'America/Maceio','DD/MM HH24:MI') quando, l.restaurado_em is not null restaurado
                  from public.lixeira l left join public.pessoas p on p.id = l.apagado_por where l.tabela = 'demandas' order by l.id desc limit 50""")
    print(f"{len(rows)} demanda(s) na lixeira:"); [print(f"  {r['registro_id']} · {r['titulo'][:55]} · apagada por {r['quem']} em {r['quando']}" + (" · JÁ RESTAURADA" if r['restaurado'] else "")) for r in rows]
else:
    for i in ids:
        r = sql(f"insert into public.demandas select (jsonb_populate_record(null::public.demandas, l.linha)).* from (select linha from public.lixeira where tabela='demandas' and registro_id='{i}' and restaurado_em is null order by id desc limit 1) l on conflict (id) do nothing returning id")
        if r: sql(f"update public.lixeira set restaurado_em = now() where tabela='demandas' and registro_id='{i}' and restaurado_em is null"); print("restaurada:", i)
        else: print("nada a restaurar para", i, "(não está na lixeira ou já existe)")
