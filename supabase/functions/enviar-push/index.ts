// Demandô · envia as notificações no celular (Web Push). Só o banco chama esta função, com o segredo interno.
// tipos: nova (demanda nova com equipe), escala (alguém foi escalado), direcionamento (comentário fixado) e resumo (todo dia às 8h).
import { createClient } from "npm:@supabase/supabase-js@2";
import webpush from "npm:web-push@3.6.7";

const json = (c: unknown, s = 200) => new Response(JSON.stringify(c), { status: s, headers: { "Content-Type": "application/json" } });
const norm = (s: unknown) => String(s ?? "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const MES = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"];
const fmt = (d?: string | null) => d ? `${Number(d.slice(8, 10))} ${MES[Number(d.slice(5, 7)) - 1]}` : "";

Deno.serve(async (req) => {
  const seg = Deno.env.get("PUSH_SECRET");
  if (!seg || req.headers.get("x-push-secret") !== seg) return json({ erro: "não autorizado" }, 401);
  const simulado = new URL(req.url).searchParams.get("simulado") === "1";
  let b: { tipo?: string; id?: string; novos?: string[]; autor?: string };
  try { b = await req.json(); } catch { return json({ erro: "pedido inválido" }, 400); }
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  webpush.setVapidDetails(Deno.env.get("VAPID_SUBJECT")!, Deno.env.get("VAPID_PUBLIC")!, Deno.env.get("VAPID_PRIVATE")!);

  const { data: pessoas } = await sb.from("pessoas").select("id, nome, nome_equipe, papel").eq("ativo", true);
  const { data: acessos } = await sb.from("acessos").select("pessoa_id, area_id");
  const nomeEq = (p: { nome: string; nome_equipe: string | null }) => norm(p.nome_equipe) || norm(String(p.nome).split(/\s+/)[0]);
  const vê = (p: { id: string; papel: string }, area: string) => p.papel === "admin" || (acessos ?? []).some((a) => a.pessoa_id === p.id && a.area_id === area);
  const alvos = (nomes: string[], area: string, fora?: string) => (pessoas ?? []).filter((p) => nomes.map(norm).includes(nomeEq(p)) && vê(p, area) && p.id !== fora);

  const envios: { pessoa_id: string; payload: Record<string, string> }[] = [];
  let demandaId: string | null = b.id ?? null;
  if (b.tipo === "resumo") {
    const hoje = new Date(Date.now() - 3 * 3600_000).toISOString().slice(0, 10);   // data em Maceió (UTC-3)
    const { data: dem } = await sb.from("demandas").select("id, titulo, area_id, equipe, hora").eq("prazo", hoje).neq("status", "Entregue");
    for (const p of pessoas ?? []) {
      const minhas = (dem ?? []).filter((d) => (d.equipe ?? []).map(norm).includes(nomeEq(p)) && vê(p, d.area_id));
      if (!minhas.length) continue;
      const lista = minhas.slice(0, 3).map((d) => d.titulo).join(" · ") + (minhas.length > 3 ? ` e mais ${minhas.length - 3}` : "");
      envios.push({ pessoa_id: p.id, payload: { title: `Hoje: ${minhas.length} ${minhas.length > 1 ? "demandas" : "demanda"} pra você`, body: lista, tag: "resumo-" + hoje, url: "./" } });
    }
    demandaId = null;
  } else {
    const { data: d } = await sb.from("demandas").select("id, titulo, area_id, equipe, prazo, criado_por").eq("id", b.id ?? "").maybeSingle();
    if (!d) return json({ erro: "demanda não encontrada" }, 404);
    const quando = fmt(d.prazo) ? ` · ${fmt(d.prazo)}` : "";
    const monta = (title: string, alvo: { id: string }[]) => alvo.forEach((p) => envios.push({ pessoa_id: p.id, payload: { title, body: d.titulo + quando, tag: `${b.tipo}-${d.id}`, url: "./" } }));
    if (b.tipo === "nova") monta("Nova escala", alvos(d.equipe ?? [], d.area_id, d.criado_por ?? undefined));
    else if (b.tipo === "escala") monta("Você foi escalado", alvos(b.novos ?? [], d.area_id));
    else if (b.tipo === "direcionamento") monta("Direcionamento novo", alvos(d.equipe ?? [], d.area_id, b.autor));
    else return json({ erro: "tipo desconhecido" }, 400);
  }

  let enviados = 0; const itens: unknown[] = [];
  for (const e of envios) {
    const { data: subs } = await sb.from("push_subs").select("id, endpoint, p256dh, auth").eq("pessoa_id", e.pessoa_id);
    for (const s of subs ?? []) {
      const sub = { endpoint: s.endpoint, keys: { p256dh: s.p256dh, auth: s.auth } };
      try {
        if (simulado) { const r = webpush.generateRequestDetails(sub, JSON.stringify(e.payload)); itens.push({ pessoa: e.pessoa_id, titulo: e.payload.title, criptografado: r.body instanceof Uint8Array || (r.body as { length?: number })?.length > 0, endpoint: r.endpoint }); enviados++; }
        else { await webpush.sendNotification(sub, JSON.stringify(e.payload), { TTL: 86400 }); enviados++; }
      } catch (err) {
        const st = (err as { statusCode?: number }).statusCode;
        if (st === 404 || st === 410) await sb.from("push_subs").delete().eq("id", s.id);   // aparelho que desinstalou o app
        itens.push({ pessoa: e.pessoa_id, erro: st ?? String(err).slice(0, 80) });
      }
    }
  }
  await sb.from("push_log").insert({ tipo: b.tipo ?? "?", demanda_id: demandaId, destinatarios: envios.length, enviados, simulado, detalhe: itens.length ? itens : null });
  return json({ ok: true, destinatarios: envios.length, enviados, simulado, itens: simulado ? itens : undefined });
});
