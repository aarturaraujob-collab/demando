// Demandô · leitura de foto e texto por IA. A chave da Anthropic fica só aqui, no servidor.
import { createClient } from "npm:@supabase/supabase-js@2";
const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (c: unknown, s = 200) => new Response(JSON.stringify(c), { status: s, headers: { ...cors, "Content-Type": "application/json" } });
const TIPOS = new Set(["image/jpeg", "image/png", "image/webp", "image/gif"]);
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ erro: "Método não permitido." }, 405);
  const token = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  const { data: quem } = await sb.auth.getUser(token);
  if (!quem?.user) return json({ erro: "Entre na sua conta primeiro." }, 401);
  const { data: eu } = await sb.from("pessoas").select("papel, ativo").eq("id", quem.user.id).maybeSingle();
  if (!eu || !eu.ativo || !["admin", "membro"].includes(eu.papel)) return json({ erro: "Sem permissão pra usar a leitura por IA." }, 403);
  const chave = Deno.env.get("ANTHROPIC_API_KEY");
  if (!chave) return json({ erro: "A leitura por IA ainda não foi configurada.", codigo: "not_configured" }, 503);
  let b: { prompt?: string; images?: { media_type: string; data: string }[]; tier?: string };
  try { b = await req.json(); } catch { return json({ erro: "Pedido inválido." }, 400); }
  const prompt = String(b.prompt ?? "").slice(0, 60000), imgs = Array.isArray(b.images) ? b.images.slice(0, 4) : [];
  if (!prompt) return json({ erro: "Pedido vazio." }, 400);
  if (imgs.some((i) => !TIPOS.has(i.media_type) || typeof i.data !== "string" || i.data.length > 7_000_000)) return json({ erro: "Imagem inválida ou grande demais." }, 400);
  const modelo = b.tier === "quick" ? (Deno.env.get("MODELO_RAPIDO") ?? "claude-haiku-5-5") : (Deno.env.get("MODELO_PADRAO") ?? "claude-sonnet-5-5");
  const conteudo = [...imgs.map((i) => ({ type: "image", source: { type: "base64", media_type: i.media_type, data: i.data } })), { type: "text", text: prompt }];
  let r: Response;
  try {
    r = await fetch("https://api.anthropic.com/v1/messages", { method: "POST", headers: { "x-api-key": chave, "anthropic-version": "2023-06-01", "content-type": "application/json" },
      body: JSON.stringify({ model: modelo, max_tokens: 4096, messages: [{ role: "user", content: conteudo }] }) });
  } catch { return json({ erro: "Não deu pra falar com a IA agora.", codigo: "upstream_error" }, 502); }
  const j = await r.json().catch(() => ({}));
  if (!r.ok) return json({ erro: j?.error?.message ?? "A IA recusou o pedido.", codigo: "upstream_error" }, r.status >= 500 ? 502 : 400);
  const texto = (j.content ?? []).filter((c: { type: string }) => c.type === "text").map((c: { text: string }) => c.text).join("");
  if (!texto) return json({ erro: "A IA não devolveu texto.", codigo: "empty_completion" }, 502);
  return json({ text: texto, truncated: j.stop_reason === "max_tokens" });
});
