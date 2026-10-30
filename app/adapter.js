/* Demandô · ponte do painel com o Supabase.
   Faz o painel (que foi feito pra rodar dentro do Claude) funcionar num servidor próprio:
   login por usuário, dados no Supabase e as mesmas "tomadas" que o painel já usa (db, user, assets, sample, downloads). */
(function(){
"use strict";
const CFG = window.DEMANDO;
const sb = window.supabase.createClient(CFG.url, CFG.anon, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
const API = window.DEMANDO_API = { sb, pessoa: null, acessos: [], areas: [], sair: async () => { try { if (API.sinoSair) await API.sinoSair(); await sb.auth.signOut(); } catch(e){} location.reload(); } };
let UID = null;

/* ---------- utilidades ---------- */
const nz = v => (v === "" || v === undefined || v === null) ? null : v;
const sz = v => v == null ? "" : v;
const ms = v => { const t = Date.parse(v); return isNaN(t) ? 0 : t; };
const norm = s => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const emailDe = u => { const [l, d] = CFG.emailCentral.split("@"); return l + "+" + norm(u) + "@" + d; };
const hoje = () => { const d = new Date(); return d.getFullYear() + "-" + String(d.getMonth() + 1).padStart(2, "0") + "-" + String(d.getDate()).padStart(2, "0"); };
function erro(e){ const x = new Error(e && e.message || "erro"); x.code = (e && (e.code === "42501" || e.status === 403)) ? "permission_denied" : (e && e.code) || "error"; return x; }
async function todas(consulta){            // o Supabase devolve no máximo 1000 linhas por vez
  let tudo = [], de = 0;
  for (;;){ const r = await consulta().range(de, de + 999); if (r.error) throw erro(r.error); tudo = tudo.concat(r.data); if (r.data.length < 1000) return tudo; de += 1000; }
}

/* ---------- tradução painel <-> banco ---------- */
const DEM_KEYS = { frente:"area_id", titulo:"titulo", tipo:"tipo", prazo:"prazo", hora:"hora", local:"local", status:"status", prioridade:"prioridade", solicitante:"solicitante",
  secretaria:"secretaria", perfil:"perfil", equipe:"equipe", obs:"obs", original:"original", link:"link", checklist:"checklist", anexos:"anexos", historico:"historico", entregue:"entregue", recorrente:"recorrente_id" };
const NULAVEIS = new Set(["tipo","prazo","hora","local","solicitante","secretaria","perfil","obs","original","link","entregue","recorrente_id"]);
const PRIS = ["Baixa","Média","Alta"];
function demPartial(p){ const row = {}; for (const [k, v] of Object.entries(p || {})){ const c = DEM_KEYS[k]; if (!c) continue;
  row[c] = c === "prioridade" ? (PRIS.includes(v) ? v : "Média") : NULAVEIS.has(c) ? nz(v) : v; } return row; }
const demDe = r => ({ id:r.id, frente:r.area_id, titulo:r.titulo, tipo:sz(r.tipo), prazo:sz(r.prazo), hora:r.hora ? String(r.hora).slice(0, 5) : "", local:sz(r.local), status:r.status,
  prioridade:r.prioridade, solicitante:sz(r.solicitante), secretaria:sz(r.secretaria), perfil:sz(r.perfil), equipe:r.equipe || [], responsavel:(r.equipe || []).join(", "), link:sz(r.link), obs:sz(r.obs),
  original:sz(r.original), checklist:r.checklist || [], anexos:r.anexos || [], historico:r.historico || [], criado:sz(r.criado), criadoEm:ms(r.criado_em), entregue:sz(r.entregue),
  recorrente:sz(r.recorrente_id), nComent:r.n_coment || 0, criadoPor:r.criado_por || "" });
const areaDe = r => r.removida ? null : ({ id:r.id, sigla:r.sigla, nome:r.nome, cor:r.cor, equipe:r.equipe || [], perfis:r.perfis || [], tipos:r.tipos || [], soAdmin:!!r.so_admin, hash:"T", criado:ms(r.criado_em) });
const areaRow = d => ({ sigla:d.sigla, nome:d.nome, cor:d.cor, equipe:d.equipe || [], perfis:d.perfis || [], tipos:d.tipos || [], so_admin:!!d.soAdmin, removida:false });
const recDe = r => ({ id:r.id, ativo:r.ativo, area:r.area_id, titulo:r.titulo, tipo:sz(r.tipo), freq:r.freq, dias:r.dias || [], dia:r.dia, hora:r.hora ? String(r.hora).slice(0, 5) : "", local:sz(r.local),
  prioridade:r.prioridade, equipe:r.equipe || [], secretaria:sz(r.secretaria), perfil:sz(r.perfil), checklist:r.checklist || [], ultimoGerado:sz(r.ultimo_gerado), criado:ms(r.criado_em) });
const recRow = d => ({ area_id:d.area, ativo:d.ativo !== false, titulo:d.titulo, tipo:nz(d.tipo), freq:d.freq === "mensal" ? "mensal" : "semanal", dias:d.dias || [], dia:d.dia || 1, hora:nz(d.hora), local:nz(d.local),
  prioridade:d.prioridade || "Média", equipe:d.equipe || [], secretaria:nz(d.secretaria), perfil:nz(d.perfil), checklist:d.checklist || [], ultimo_gerado:nz(d.ultimoGerado) });
const comDe = r => ({ id:r.id, texto:sz(r.texto), anexos:r.anexos || [], fixado:!!r.fixado, por:r.por || "", autor:sz(r.autor), em:ms(r.em) });
const comRow = (d, demId) => ({ id:d.id, demanda_id:demId, texto:nz(d.texto), anexos:d.anexos || [], fixado:!!d.fixado, por:UID, autor:d.autor || "" });

/* ---------- coleções ---------- */
const ASSINATURAS = new Set();      // tudo que está "ao vivo": se a conexão cair, buscamos os dados de novo
function ao_vivo(tabela, deRow, filtro, cb, errCb){
  const mapa = new Map(); let vivo = true, canal = null, jaConectou = false;
  const emitir = () => cb({ docs: [...mapa.values()].map(d => ({ id:d.id, data:() => d })) });
  const buscar = () => todas(() => { let q = sb.from(tabela).select("*"); if (filtro) q = q.eq(filtro.col, filtro.val); return q; });
  const recarregar = async () => { try { const linhas = await buscar(); if (!vivo) return; mapa.clear(); linhas.forEach(r => { const d = deRow(r); if (d) mapa.set(r.id, d); }); emitir(); } catch(e){} };
  const item = { recarregar, saudavel: () => !canal || canal.state === "joined" };
  ASSINATURAS.add(item);
  (async () => {
    let linhas;
    try { linhas = await buscar(); } catch(e){ if (vivo && errCb) errCb(e); return; }
    if (!vivo) return;
    linhas.forEach(r => { const d = deRow(r); if (d) mapa.set(r.id, d); }); emitir();
    canal = sb.channel(tabela + "-" + Math.random().toString(36).slice(2))
      .on("postgres_changes", { event:"*", schema:"public", table:tabela, ...(filtro ? { filter: filtro.col + "=eq." + filtro.val } : {}) }, p => {
        if (p.eventType === "DELETE") mapa.delete(p.old.id);
        else { const d = deRow(p.new); if (d) mapa.set(p.new.id, d); else mapa.delete(p.new.id); }
        emitir(); })
      .subscribe(status => { if (status === "SUBSCRIBED"){ if (jaConectou) recarregar(); jaConectou = true; } });
  })();
  return () => { vivo = false; ASSINATURAS.delete(item); if (canal) sb.removeChannel(canal); };
}
// rede de segurança: se a conexão ao vivo cair, a cada 10 s o app busca de novo; ao voltar pra tela ou à internet, também
setInterval(() => { if (document.visibilityState === "visible") ASSINATURAS.forEach(a => { if (!a.saudavel()) a.recarregar(); }); }, 10000);
document.addEventListener("visibilitychange", () => { if (document.visibilityState === "visible") ASSINATURAS.forEach(a => a.recarregar()); });
window.addEventListener("online", () => ASSINATURAS.forEach(a => a.recarregar()));
async function atualizaOuInsere(tabela, id, rowUpdate, rowInsert){
  const u = await sb.from(tabela).update(rowUpdate).eq("id", id).select("id");
  if (u.error) throw erro(u.error);
  if (u.data && u.data.length) return;
  const i = await sb.from(tabela).insert(Object.assign({ id }, rowInsert || rowUpdate));
  if (i.error) throw erro(i.error);
}
const DOC_CONFIG = { hash:"ADM", fedHash:"T", ascHash:"T", em:0 };
function colecao(path){
  let m;
  if (path === "demandas") return { onSnapshot:(cb, e) => ao_vivo("demandas", demDe, null, cb, e), doc: id => ({
    async set(d){ await atualizaOuInsere("demandas", id, demPartial(d), Object.assign(demPartial(d), { criado: /^\d{4}-\d{2}-\d{2}$/.test(d.criado || "") ? d.criado : hoje(), criado_por: UID })); },
    async update(p){ const row = demPartial(p); if (!Object.keys(row).length) return; const r = await sb.from("demandas").update(row).eq("id", id); if (r.error) throw erro(r.error); },
    async delete(){ const r = await sb.from("demandas").delete().eq("id", id); if (r.error) throw erro(r.error); } }) };
  if (path === "areas") return { onSnapshot:(cb, e) => ao_vivo("areas", areaDe, null, cb, e), doc: id => ({
    async set(d){ if (id === "fed" || id === "asc"){ const r = await sb.from("areas").update({ equipe:d.equipe || [] }).eq("id", id); if (r.error) throw erro(r.error); return; }
      await atualizaOuInsere("areas", id, areaRow(d)); },
    async delete(){ const r = await sb.from("areas").update({ removida:true }).eq("id", id); if (r.error) throw erro(r.error); } }) };
  if (path === "recorrentes") return { onSnapshot:(cb, e) => ao_vivo("recorrentes", recDe, null, cb, e), doc: id => ({
    async set(d){ await atualizaOuInsere("recorrentes", id, recRow(d)); },
    async delete(){ const r = await sb.from("recorrentes").delete().eq("id", id); if (r.error) throw erro(r.error); } }) };
  if ((m = path.match(/^demandas\/([^/]+)\/comentarios$/))) return { onSnapshot:(cb, e) => ao_vivo("comentarios", comDe, { col:"demanda_id", val:m[1] }, cb, e), doc: id => ({
    async set(d){ const r = await sb.from("comentarios").insert(comRow(Object.assign({}, d, { id }), m[1])); if (r.error && r.error.code !== "23505") throw erro(r.error); },
    async delete(){ const r = await sb.from("comentarios").delete().eq("id", id); if (r.error) throw erro(r.error); } }) };
  if (path === "config") return { doc: () => ({ get: async () => ({ exists:true, data:() => DOC_CONFIG }), set: async () => {}, onSnapshot:(cb) => { cb({ exists:true, data:() => DOC_CONFIG }); return () => {}; } }) };
  if (/^data\/users\//.test(path)) return { doc: () => ({
    async get(){ const r = await sb.from("preferencias").select("dados").eq("pessoa_id", UID).maybeSingle(); return { exists:!!(r.data), data:() => (r.data && r.data.dados) || {} }; },
    async set(d){ const r = await sb.from("preferencias").upsert({ pessoa_id:UID, dados:d, atualizado_em:new Date().toISOString() }); if (r.error) throw erro(r.error); } }) };
  throw new Error("coleção desconhecida: " + path);
}

/* ---------- as "tomadas" que o painel usa ---------- */
const downloads = { save: async ({ filename, data }) => {
  const url = URL.createObjectURL(data), a = document.createElement("a"); a.href = url; a.download = filename; document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 15000); return {}; } };
const assets = { upload: async file => {
  const nome = String(file.name || "arquivo").normalize("NFD").replace(/[\u0300-\u036f]/g, "").replace(/[^A-Za-z0-9._-]+/g, "-").slice(-60);
  const path = UID + "/" + Date.now().toString(36) + "-" + Math.random().toString(36).slice(2, 8) + "-" + nome;
  const up = await sb.storage.from("anexos").upload(path, file, { contentType:file.type || "application/octet-stream", upsert:false });
  if (up.error) throw (/size|large/i.test(up.error.message) ? { code:"too_big" } : /mime|type/i.test(up.error.message) ? { code:"unsupported_type" } : /policy|permission|unauthorized/i.test(up.error.message) ? { code:"not_granted" } : erro(up.error));
  const s = await sb.storage.from("anexos").createSignedUrl(path, 31536000);
  if (s.error) throw erro(s.error);
  return { id:path, url:s.data.signedUrl, contentType:file.type, sizeBytes:file.size };
}, delete: async id => { await sb.storage.from("anexos").remove([id]); } };
async function imagemParaIA(file){
  const bmp = await createImageBitmap(file), k = Math.min(1, 1600 / Math.max(bmp.width, bmp.height));
  const c = document.createElement("canvas"); c.width = Math.round(bmp.width * k); c.height = Math.round(bmp.height * k);
  c.getContext("2d").drawImage(bmp, 0, 0, c.width, c.height);
  return { media_type:"image/jpeg", data: c.toDataURL("image/jpeg", 0.85).split(",")[1] };
}
async function sample(prompt, opts){
  opts = opts || {}; const imagens = []; for (const f of (opts.images || [])) imagens.push(await imagemParaIA(f));
  const sess = (await sb.auth.getSession()).data.session;
  const r = await fetch(CFG.url + "/functions/v1/ler-pedido", { method:"POST", signal:opts.signal,
    headers:{ "Content-Type":"application/json", apikey:CFG.anon, Authorization:"Bearer " + sess.access_token }, body:JSON.stringify({ prompt, images:imagens, tier:opts.modelTier || "default" }) });
  const j = await r.json().catch(() => ({}));
  if (!r.ok){ const e = new Error(j.erro || "erro"); e.code = j.codigo || (r.status >= 500 ? "upstream_error" : "error"); throw e; }
  return { text:j.text || "", truncated:!!j.truncated };
}
sample.limits = async () => ({ images:{ maxCount:4, mediaTypes:["image/jpeg","image/png","image/webp","image/gif"] } });
function montarClaude(){
  const escreve = API.pessoa.papel === "admin" || API.pessoa.papel === "membro";
  const user = {
    me: async () => ({ id:UID, name:API.pessoa.nome }),
    canEdit: async () => API.pessoa.papel === "admin",
    can: async () => escreve,
    profiles: async ids => { const r = await sb.rpc("nomes_pessoas", { ids }); const o = {}; (r.data || []).forEach(p => o[p.id] = { name:p.nome }); return o; }
  };
  window.claude = { use: async nome => ({ db:{ collection:colecao }, user, downloads, assets: escreve ? assets : null, sample: escreve ? sample : null })[nome] || null };
}

/* ---------- tela de entrada ---------- */
const css = document.createElement("style");
css.textContent = `body.gate>*:not(#gate):not(script):not(style){display:none!important}
#gate{min-height:100vh;display:grid;place-items:center;padding:24px;background:var(--bg,#F3F4F1);color:var(--ink,#121A17);font:15px/1.5 Manrope,system-ui,sans-serif}
#gate .gc{width:100%;max-width:400px;background:var(--surface,#fff);border-radius:28px;box-shadow:0 1px 2px rgba(18,26,23,.06),0 8px 24px rgba(18,26,23,.06);padding:28px 24px;display:grid;gap:16px}
#gate .gm{display:flex;align-items:center;justify-content:center;gap:12px}#gate .gm b{font:800 30px/1 Geist,Manrope,sans-serif;letter-spacing:-.04em}#gate .gm svg{width:46px;height:46px}
#gate h2{margin:0;text-align:center;font:700 26px "Barlow Condensed",system-ui,sans-serif}#gate .gs{text-align:center;color:var(--muted,#5E6B66);margin:-8px 0 0}
#gate label{display:grid;gap:6px;font-size:11px;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--muted,#5E6B66)}
#gate input{width:100%;min-height:46px;border:1px solid var(--line,#DDE2DE);background:var(--surface,#fff);border-radius:14px;padding:10px 14px;font:inherit;font-size:15px;color:inherit;text-transform:none;letter-spacing:0;font-weight:500}
#gate button.p{min-height:46px;border:0;border-radius:14px;background:var(--ink,#121A17);color:var(--bg,#F3F4F1);font:inherit;font-weight:700;cursor:pointer}#gate button.p[disabled]{opacity:.5}
#gate button.s{background:none;border:0;color:var(--muted,#5E6B66);font:inherit;font-weight:700;text-decoration:underline;padding:6px;cursor:pointer}
#gate .er{margin:0;color:var(--late,#C4321E);font-weight:700;font-size:13px}`;
document.head.append(css);
let promptInstalar = null;
window.addEventListener("beforeinstallprompt", e => { e.preventDefault(); promptInstalar = e; document.querySelectorAll(".g-inst").forEach(x => x.hidden = false); });
const gate = document.createElement("div"); gate.id = "gate"; document.body.prepend(gate); document.body.classList.add("gate");
const NS = "http://www.w3.org/2000/svg";
const marca = () => { const d = document.createElement("div"); d.className = "gm"; d.innerHTML = '<svg viewBox="0 0 120 120"><rect width="120" height="120" rx="30" fill="#121A17"/><path d="M60 47 A23 23 0 0 0 60 93" fill="none" stroke="#1F4FD1" stroke-width="13"/><path d="M60 47 A23 23 0 0 1 60 93" fill="none" stroke="#0E7A4D" stroke-width="13"/><path d="M41 36 L60 21 L79 36" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/></svg><b>Demandô</b>'; return d; };
function h(tag, props, ...kids){ const e = document.createElement(tag); for (const [k, v] of Object.entries(props || {})){ if (v == null || v === false) continue; if (k.startsWith("on")) e.addEventListener(k.slice(2), v); else e.setAttribute(k, v === true ? "" : v); }
  for (const c of kids.flat()) if (c != null && c !== false) e.append(c.nodeType ? c : document.createTextNode(String(c))); return e; }
const tela = (...nos) => gate.replaceChildren(h("div", { class:"gc" }, marca(), ...nos));
function telaEntrar(aviso){
  const u = h("input", { id:"g-usuario", autocomplete:"username", autocapitalize:"none", spellcheck:"false", placeholder:"ex.: juninho" }), s = h("input", { id:"g-senha", type:"password", autocomplete:"current-password", placeholder:"Sua senha" });
  const e = h("p", { class:"er", id:"g-erro", hidden:!aviso }, aviso || ""), go = h("button", { class:"p", id:"g-entrar", type:"button" }, "Entrar");
  const fazer = async () => { e.hidden = true; if (!u.value.trim() || !s.value){ e.textContent = "Preencha o usuário e a senha."; e.hidden = false; return; }
    go.disabled = true; const r = await entrar(u.value, s.value); go.disabled = false; if (r){ e.textContent = r; e.hidden = false; } };
  go.addEventListener("click", fazer); [u, s].forEach(i => i.addEventListener("keydown", ev => { if (ev.key === "Enter") fazer(); }));
  tela(h("h2", null, "Entrar"), h("label", null, "Usuário", u), h("label", null, "Senha", s), e, go, h("button", { class:"s", id:"g-criar", type:"button", onclick:() => telaCriar() }, "Criar meu perfil"), dicaInstalar());
}
async function entrar(usuario, senha){
  const r = await sb.auth.signInWithPassword({ email:emailDe(usuario), password:senha });
  if (r.error) return /rate|many/i.test(r.error.message) ? "Muitas tentativas. Espere um pouco." : "Usuário ou senha incorretos.";
  await seguir(); return null;
}
function telaCriar(){
  const f = {}, campo = (id, rot, p) => { const i = h("input", Object.assign({ id:"g-" + id }, p)); f[id] = i; return h("label", null, rot, i); };
  const e = h("p", { class:"er", id:"g-erro", hidden:true }), go = h("button", { class:"p", id:"g-enviar", type:"button" }, "Criar perfil");
  go.addEventListener("click", async () => { e.hidden = true; go.disabled = true;
    try {
      const r = await fetch(CFG.url + "/functions/v1/criar-perfil", { method:"POST", headers:{ "Content-Type":"application/json", apikey:CFG.anon }, body:JSON.stringify({ nome:f.nome.value, usuario:f.usuario.value, senha:f.senha.value, codigo:f.codigo.value }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok){ e.textContent = j.erro || "Não deu pra criar o perfil agora."; e.hidden = false; go.disabled = false; return; }
      const x = await entrar(f.usuario.value, f.senha.value); if (x) telaEntrar("Perfil criado. Agora entre com o seu usuário e a senha.");
    } catch(_){ e.textContent = "Sem conexão. Tente de novo."; e.hidden = false; go.disabled = false; } });
  tela(h("h2", null, "Criar perfil"), h("p", { class:"gs" }, "Depois de criar, um admin libera o seu acesso."),
    campo("nome", "Seu nome", { autocomplete:"name", placeholder:"Nome e sobrenome" }), campo("usuario", "Usuário (pra entrar)", { autocapitalize:"none", spellcheck:"false", placeholder:"ex.: juninho" }),
    campo("senha", "Senha (mínimo 8)", { type:"password", autocomplete:"new-password" }), campo("codigo", "Código da equipe", { autocapitalize:"characters", placeholder:"Pergunte ao admin" }),
    e, go, h("button", { class:"s", id:"g-voltar", type:"button", onclick:() => telaEntrar() }, "Já tenho perfil"));
}
function dicaInstalar(){
  if (window.matchMedia("(display-mode: standalone)").matches || navigator.standalone) return null;
  if (/iphone|ipad|ipod/i.test(navigator.userAgent)) return h("p", { class:"gs", style:"font-size:13px" }, "No iPhone: toque em Compartilhar e depois em “Adicionar à Tela de Início”.");
  const b = h("button", { class:"s g-inst", type:"button", hidden:!promptInstalar, onclick:async () => { if (!promptInstalar) return; promptInstalar.prompt(); await promptInstalar.userChoice; promptInstalar = null; b.hidden = true; } }, "Instalar o app no celular");
  return b;
}
function telaAviso(titulo, texto, extra){ tela(h("h2", null, titulo), h("p", { class:"gs" }, texto), ...(extra || []), h("button", { class:"s", id:"g-sair", type:"button", onclick:API.sair }, "Sair")); }


/* ---------- notificações no celular (sininho) ---------- */
function iniciarSino(){
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window) || !CFG.vapid) return;
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent), standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  const st = document.createElement("style");
  st.textContent = '#sino{position:absolute;z-index:30;width:40px;height:40px;border-radius:14px;border:0;display:grid;place-items:center;background:var(--surface,#fff);color:var(--muted,#5E6B66);box-shadow:0 1px 2px rgba(18,26,23,.06),0 8px 24px rgba(18,26,23,.06);cursor:pointer}#sino.on{background:var(--ink,#121A17);color:var(--bg,#F3F4F1)}#sino svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.mtop #sino{right:64px;top:50%;transform:translateY(-50%)}.side #sino{right:12px;top:22px}#sinoT{position:fixed;left:50%;transform:translateX(-50%);bottom:96px;background:var(--ink,#121A17);color:var(--bg,#F3F4F1);padding:12px 18px;border-radius:14px;font-weight:700;font-size:14px;z-index:99;max-width:88vw;text-align:center}';
  document.head.append(st);
  const b = document.createElement("button"); b.id = "sino"; b.type = "button"; b.setAttribute("aria-label", "Notificações neste aparelho");
  b.innerHTML = '<svg viewBox="0 0 24 24"><path d="M6 16V11a6 6 0 0 1 12 0v5l1.5 2h-15z"/><path d="M10 21h4"/></svg>';
  const dica = txt => { let t = document.getElementById("sinoT"); if (!t){ t = document.createElement("div"); t.id = "sinoT"; document.body.append(t); } t.textContent = txt; t.hidden = false; clearTimeout(t._x); t._x = setTimeout(() => t.hidden = true, 4200); };
  const alvo = () => (window.innerWidth <= 860 ? document.querySelector(".mtop") : document.querySelector(".side")) || document.body;
  const pos = () => { const t = alvo(); if (b.parentNode !== t) t.append(b); };
  const urlB64 = s => { const p = "=".repeat((4 - s.length % 4) % 4), r = atob((s + p).replace(/-/g, "+").replace(/_/g, "/")); return Uint8Array.from([...r].map(c => c.charCodeAt(0))); };
  const marca = on => { b.classList.toggle("on", on); b.title = on ? "Notificações ligadas neste aparelho (toque pra desligar)" : "Ligar notificações neste aparelho"; };
  const salvar = async s => { const j = s.toJSON(); const r = await sb.from("push_subs").upsert({ pessoa_id:UID, endpoint:j.endpoint, p256dh:j.keys.p256dh, auth:j.keys.auth }, { onConflict:"endpoint" }); if (r.error) throw r.error; };
  API.sinoSair = async () => { try { const reg = await navigator.serviceWorker.ready, s = await reg.pushManager.getSubscription(); if (s){ await sb.from("push_subs").delete().eq("endpoint", s.endpoint); } } catch(e){} };
  b.addEventListener("click", async () => {
    try {
      const reg = await navigator.serviceWorker.ready, atual = await reg.pushManager.getSubscription();
      if (atual){ await sb.from("push_subs").delete().eq("endpoint", atual.endpoint); await atual.unsubscribe(); marca(false); dica("Notificações desligadas neste aparelho"); return; }
      if (ios && !standalone){ dica("No iPhone, instale o app (Compartilhar → Adicionar à Tela de Início) e ative por ele."); return; }
      const perm = await Notification.requestPermission();
      if (perm !== "granted"){ dica("As notificações estão bloqueadas. Libere nas configurações do navegador."); return; }
      const s = await reg.pushManager.subscribe({ userVisibleOnly:true, applicationServerKey:urlB64(CFG.vapid) });
      await salvar(s); marca(true); dica("Notificações ativadas. Já já chega um aviso de teste."); sb.rpc("testar_aviso").then(() => {}, () => {});
    } catch(e){ dica("Não deu pra ativar as notificações agora."); }
  });
  pos(); window.addEventListener("resize", pos); setTimeout(pos, 800);
  (async () => { try { const reg = await navigator.serviceWorker.ready, s = await reg.pushManager.getSubscription(); if (s && Notification.permission === "granted"){ await salvar(s); marca(true); } else marca(false); } catch(e){ marca(false); } })();
}

/* ---------- depois de entrar ---------- */
async function seguir(){
  tela(h("p", { class:"gs" }, "Carregando…"));
  const { data: { session } } = await sb.auth.getSession(); if (!session) return telaEntrar();
  UID = session.user.id;
  const [p, a, ac] = await Promise.all([ sb.from("pessoas").select("*").eq("id", UID).maybeSingle(), sb.from("areas").select("id,removida,so_admin").order("ordem"), sb.from("acessos").select("area_id").eq("pessoa_id", UID) ]);
  if (p.error || !p.data) return telaAviso("Não deu pra carregar", "Tente de novo em instantes.", [h("button", { class:"p", onclick:seguir }, "Tentar de novo")]);
  API.pessoa = p.data; const visiveis = (a.data || []).filter(x => !x.removida).map(x => x.id); API.areas = visiveis;
  API.acessos = (ac.data || []).map(x => x.area_id);
  if (!p.data.ativo) return telaAviso("Acesso desativado", "Fale com o admin pra voltar a usar o Demandô.");
  const admin = p.data.papel === "admin";
  if (!admin && !visiveis.length) return telaAviso("Aguardando liberação", "Seu perfil foi criado. Assim que um admin liberar as suas áreas, elas aparecem aqui.", [h("button", { class:"p", id:"g-atualizar", onclick:seguir }, "Já liberaram? Atualizar")]);
  // o painel decide quem é admin e qual área mostrar pelo que está guardado no aparelho: deixamos isso coerente com a conta
  try {
    localStorage.setItem("cd-admhash", "ADM"); localStorage.setItem("cd-cfg", JSON.stringify(DOC_CONFIG));
    if (admin){ localStorage.setItem("cd-adm", "ADM"); localStorage.removeItem("cd-fr"); localStorage.removeItem("cd-frh"); }
    else { localStorage.removeItem("cd-adm"); const atual = localStorage.getItem("cd-fr"); const fr = visiveis.includes(atual) ? atual : visiveis[0]; localStorage.setItem("cd-fr", fr); localStorage.setItem("cd-frh", "T"); }
  } catch(e){}
  document.body.classList.toggle("sem-voltar", admin || visiveis.length < 2); document.body.classList.toggle("e-admin", admin);
  montarClaude(); gate.remove(); document.body.classList.remove("gate");
  const s = document.createElement("script"); s.textContent = document.getElementById("appcode").textContent; document.body.append(s);
  iniciarSino();
}
(async () => { const { data: { session } } = await sb.auth.getSession(); if (session) seguir(); else telaEntrar(); })();
})();
