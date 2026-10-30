// Demandô · cada pessoa cria o próprio perfil (usuário + senha), com o código da equipe.
// O perfil nasce SEM acesso a nada: um admin libera o papel e as áreas depois.
// O e-mail interno é sempre o da caixa central, com "+usuario" (ex.: demandasbm+juninho@gmail.com).
import { createClient } from "npm:@supabase/supabase-js@2";

const cors = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const json = (corpo: unknown, status = 200) =>
  new Response(JSON.stringify(corpo), { status, headers: { ...cors, "Content-Type": "application/json" } });
const limpa = (s: string) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const RESERVADOS = new Set(["admin", "administrador", "root", "suporte", "demando", "sistema", "equipe"]);
function igual(a: string, b: string) {
  if (a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: cors });
  if (req.method !== "POST") return json({ erro: "Método não permitido." }, 405);
  let b: Record<string, unknown>;
  try { b = await req.json(); } catch { return json({ erro: "Pedido inválido." }, 400); }

  const codigo = String(b.codigo ?? "").trim().toUpperCase();
  const nome = String(b.nome ?? "").trim().replace(/\s+/g, " ").slice(0, 60);
  const usuario = limpa(String(b.usuario ?? ""));
  const senha = String(b.senha ?? "");

  const esperado = (Deno.env.get("CODIGO_EQUIPE") ?? "").trim().toUpperCase();
  if (!esperado || !igual(codigo, esperado)) return json({ erro: "Código da equipe incorreto." }, 403);
  if (!/^[a-z0-9._-]{3,20}$/.test(usuario) || RESERVADOS.has(usuario))
    return json({ erro: "Usuário inválido. Use de 3 a 20 letras minúsculas, números, ponto, traço ou sublinhado." }, 400);
  if (nome.length < 2) return json({ erro: "Escreva o seu nome." }, 400);
  if (senha.length < 8) return json({ erro: "A senha precisa ter pelo menos 8 caracteres." }, 400);

  const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });

  // trava simples contra abuso: no máximo 20 perfis novos por hora
  const { count } = await sb.from("pessoas").select("id", { count: "exact", head: true })
    .gte("criado_em", new Date(Date.now() - 3600_000).toISOString());
  if ((count ?? 0) >= 20) return json({ erro: "Muitos cadastros agora. Tente de novo daqui a pouco." }, 429);

  const [local, dominio] = (Deno.env.get("EMAIL_CENTRAL") ?? "demandasbm@gmail.com").split("@");
  const email = `${local}+${usuario}@${dominio}`;
  const { error } = await sb.auth.admin.createUser({ email, password: senha, email_confirm: true, user_metadata: { nome, usuario } });
  if (error) {
    const repetido = /already|registered|exists|duplicate/i.test(error.message);
    return json({ erro: repetido ? "Esse usuário já existe. Escolha outro." : "Não deu pra criar o perfil agora." }, repetido ? 409 : 500);
  }
  return json({ ok: true, usuario, mensagem: "Perfil criado. Agora é só esperar o admin liberar o seu acesso." });
});
