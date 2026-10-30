// Demandô · o admin redefine a senha de outra pessoa (quem esqueceu a senha pede ao admin).
import { createClient } from "npm:@supabase/supabase-js@2";
const cors = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type", "Access-Control-Allow-Methods": "POST, OPTIONS" };
const json = (c: unknown, s = 200) => new Response(JSON.stringify(c), { status: s, headers: { ...cors, "Content-Type": "application/json" } });
Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ erro: "Método não permitido." }, 405);
  const token = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
  if (!token) return json({ erro: "Entre na sua conta primeiro." }, 401);
  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
  const { data: quem, error: e1 } = await sb.auth.getUser(token);
  if (e1 || !quem.user) return json({ erro: "Sessão inválida." }, 401);
  const { data: eu } = await sb.from("pessoas").select("papel, ativo").eq("id", quem.user.id).maybeSingle();
  if (!eu || eu.papel !== "admin" || !eu.ativo) return json({ erro: "Só admin pode redefinir senhas." }, 403);
  let b: Record<string, unknown>; try { b = await req.json(); } catch { return json({ erro: "Pedido inválido." }, 400); }
  const alvo = String(b.pessoa_id ?? ""), senha = String(b.senha ?? "");
  if (!/^[0-9a-f-]{36}$/i.test(alvo)) return json({ erro: "Pessoa inválida." }, 400);
  if (senha.length < 8) return json({ erro: "A senha precisa ter pelo menos 8 caracteres." }, 400);
  const { error } = await sb.auth.admin.updateUserById(alvo, { password: senha });
  if (error) return json({ erro: "Não deu pra trocar a senha agora." }, 500);
  return json({ ok: true });
});
