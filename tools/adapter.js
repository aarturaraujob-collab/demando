/* Demandô · ponte do painel com o Supabase.
   Faz o painel (que foi feito pra rodar dentro do Claude) funcionar num servidor próprio:
   login por usuário, dados no Supabase e as mesmas "tomadas" que o painel já usa (db, user, assets, sample, downloads). */
(function(){
"use strict";
const CFG = window.DEMANDO;
const sb = window.supabase.createClient(CFG.url, CFG.anon, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
const API = window.DEMANDO_API = { sb, pessoa: null, acessos: [], areas: [], sair: async () => { try { if (API.sinoSair) await API.sinoSair(); await sb.auth.signOut(); } catch(e){} location.reload(); } };
let UID = null;
API.guardarNomeEquipe = async nome => { try { if (!nome || !UID || (API.pessoa && API.pessoa.nome_equipe === nome)) return; const r = await sb.from("pessoas").update({ nome_equipe:nome }).eq("id", UID); if (!r.error && API.pessoa) API.pessoa.nome_equipe = nome; } catch(e){} };

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
  const ios = /iphone|ipad|ipod/i.test(navigator.userAgent), standalone = window.matchMedia("(display-mode: standalone)").matches || navigator.standalone;
  const temPush = "serviceWorker" in navigator && "PushManager" in window && "Notification" in window && !!CFG.vapid;
  if (!temPush && !ios) return;           // no iPhone o sino aparece sempre: sem o app instalado, ele explica como instalar
  const st = document.createElement("style");
  st.textContent = '#sino{position:absolute;z-index:30;width:40px;height:40px;border-radius:14px;border:0;display:grid;place-items:center;background:var(--surface,#fff);color:var(--muted,#5E6B66);box-shadow:0 1px 2px rgba(18,26,23,.06),0 8px 24px rgba(18,26,23,.06);cursor:pointer}#sino.on{background:var(--ink,#121A17);color:var(--bg,#F3F4F1)}#sino svg{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:1.8;stroke-linecap:round;stroke-linejoin:round}.mtop #sino{left:14px;top:50%;transform:translateY(-50%)}body:not(.sem-voltar) .mtop #sino{left:62px}.side #sino{right:12px;top:22px}#sinoT{position:fixed;left:50%;transform:translateX(-50%);bottom:96px;background:var(--ink,#121A17);color:var(--bg,#F3F4F1);padding:12px 18px;border-radius:14px;font-weight:700;font-size:14px;z-index:99;max-width:88vw;text-align:center}';
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
      if (!temPush){ dica("No iPhone, instale o app (Compartilhar → Adicionar à Tela de Início) e ative por ele."); return; }
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
  if (!temPush){ marca(false); return; }
  (async () => { try { const reg = await navigator.serviceWorker.ready, s = await reg.pushManager.getSubscription(); if (s && Notification.permission === "granted"){ await salvar(s); marca(true); } else marca(false); } catch(e){ marca(false); } })();
}


/* ---------- anexos: visualizador dentro do app (prévia + fechar + baixar) ---------- */
function iniciarAnexos(){
  const st = document.createElement("style");
  st.textContent = 'dialog#axv{position:fixed;inset:0;width:100%;height:100%;max-width:none;max-height:none;margin:0;padding:0;border:0;background:#0b0e0d;color:#fff;overscroll-behavior:contain}dialog#axv[open]{display:flex;flex-direction:column}dialog#axv::backdrop{background:#0b0e0d}dialog#axv :focus,dialog#axv:focus{outline:none}.axv-x:focus-visible,.axv-b:focus-visible{outline:2px solid #fff;outline-offset:2px}.axv-h{display:flex;align-items:center;gap:10px;padding:calc(env(safe-area-inset-top,0px) + 10px) 14px 10px;background:rgba(22,27,25,.98);border-bottom:1px solid rgba(255,255,255,.08)}.axv-x,.axv-b{border:0;border-radius:12px;height:42px;padding:0 14px;font-weight:700;font-size:14.5px;display:inline-flex;align-items:center;gap:7px;cursor:pointer;color:#fff;background:rgba(255,255,255,.14);flex:none}.axv-b{background:#fff;color:#0b0e0d}.axv-b svg,.axv-x svg{width:18px;height:18px;fill:none;stroke:currentColor;stroke-width:2.2;stroke-linecap:round;stroke-linejoin:round}.axv-t{flex:1;min-width:0;display:grid;text-align:center}.axv-n{font-weight:700;font-size:15px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.axv-s{font-size:12px;opacity:.65}.axv-c{flex:1;overflow:auto;-webkit-overflow-scrolling:touch;padding:12px 12px calc(env(safe-area-inset-bottom,0px) + 28px);display:flex;flex-direction:column;align-items:center;gap:12px}.axv-c img{max-width:100%;height:auto;border-radius:10px;touch-action:pinch-zoom pan-x pan-y}.axv-c canvas{background:#fff;border-radius:6px;max-width:100%;flex:none;box-shadow:0 6px 24px rgba(0,0,0,.45)}.axv-c video{max-width:100%;max-height:100%;border-radius:10px}.axv-msg{margin:auto;text-align:center;opacity:.85;font-size:15px;max-width:300px;line-height:1.45}.axv-arq{margin:auto;display:grid;gap:14px;justify-items:center;text-align:center}.axv-arq b{font-size:17px}#axvT{position:absolute;left:50%;transform:translateX(-50%);bottom:calc(env(safe-area-inset-bottom,0px) + 40px);background:#fff;color:#0b0e0d;padding:12px 18px;border-radius:14px;font-weight:700;font-size:14px;z-index:400;max-width:88vw;text-align:center}';
  document.head.append(st);
  const ICO_BAIXAR = '<svg viewBox="0 0 24 24"><path d="M12 4v11"/><path d="m7.5 11 4.5 4.5 4.5-4.5"/><path d="M5 19.5h14"/></svg>', ICO_X = '<svg viewBox="0 0 24 24"><path d="M6 6l12 12M18 6 6 18"/></svg>';
  const nosso = u => /\/storage\/v1\/object\//.test(u || "");
  const dica = t => { let e = document.getElementById("axvT"); if (!e){ e = document.createElement("div"); e.id = "axvT"; } const ds = document.querySelectorAll("dialog[open]"); (ds.length ? ds[ds.length - 1] : document.body).append(e); e.textContent = t; e.hidden = false; clearTimeout(e._x); e._x = setTimeout(() => e.hidden = true, 4200); };
  const cache = new Map();
  const pegarBlob = async url => { if (cache.has(url)) return cache.get(url); const r = await fetch(url); if (!r.ok) throw new Error("http " + r.status); const bl = await r.blob(); cache.set(url, bl); if (cache.size > 6) cache.delete(cache.keys().next().value); return bl; };
  const tipoDe = (nome, mime) => { const m = (mime || "").toLowerCase(), n = (nome || "").toLowerCase(); if (m.startsWith("image/") || /\.(png|jpe?g|gif|webp|heic|avif)$/.test(n)) return "img"; if (m === "application/pdf" || /\.pdf$/.test(n)) return "pdf"; if (m.startsWith("video/") || /\.(mp4|mov|webm|m4v)$/.test(n)) return "vid"; return "arq"; };
  const tam = n => n > 1048576 ? (n / 1048576).toFixed(1).replace(".", ",") + " MB" : Math.max(1, Math.round(n / 1024)) + " KB";
  async function baixar(url, nome, mime){
    try {
      const bl = await pegarBlob(url), file = new File([bl], nome || "arquivo", { type: mime || bl.type || "application/octet-stream" });
      if (navigator.canShare && navigator.canShare({ files:[file] })){
        try { await navigator.share({ files:[file], title:file.name }); return; }
        catch(e){ if (e && e.name === "AbortError") return; if (e && e.name === "NotAllowedError"){ abrir(url, nome, mime); dica("Pronto. Toque em Baixar."); return; } }
      }
      const a = document.createElement("a"); a.href = URL.createObjectURL(bl); a.download = file.name; document.body.append(a); a.click(); setTimeout(() => { URL.revokeObjectURL(a.href); a.remove(); }, 4000);
    } catch(e){ dica("Não consegui baixar agora. Tente de novo."); }
  }
  let pdfP = null;
  const carregarPdf = () => window.pdfjsLib ? Promise.resolve() : (pdfP = pdfP || new Promise((ok, no) => { const s = document.createElement("script"); s.src = "vendor/pdf.min.js"; s.onload = () => { try { window.pdfjsLib.GlobalWorkerOptions.workerSrc = "vendor/pdf.worker.min.js"; ok(); } catch(e){ no(e); } }; s.onerror = () => { pdfP = null; no(new Error("pdfjs")); }; document.head.append(s); }));
  async function mostrarPdf(bl, c, sub){
    await carregarPdf();
    const pdf = await window.pdfjsLib.getDocument({ data: new Uint8Array(await bl.arrayBuffer()) }).promise;
    c.replaceChildren(); sub.textContent = pdf.numPages + (pdf.numPages > 1 ? " páginas" : " página");
    const W = Math.min(c.clientWidth - 24, 920) || 340, dpr = Math.min(window.devicePixelRatio || 1, 2);
    const obs = new IntersectionObserver(es => es.forEach(async en => { if (!en.isIntersecting) return; const cv = en.target; obs.unobserve(cv); if (cv._ok) return; cv._ok = true; try { const pg = await pdf.getPage(cv._n), vp = pg.getViewport({ scale: (W / pg.getViewport({ scale:1 }).width) * dpr }); cv.width = vp.width; cv.height = vp.height; await pg.render({ canvasContext:cv.getContext("2d"), viewport:vp }).promise; cv.setAttribute("data-pronta", "1"); } catch(e){} }), { root:c, rootMargin:"900px 0px" });
    for (let n = 1; n <= pdf.numPages; n++){ const pg = await pdf.getPage(n), v1 = pg.getViewport({ scale:1 }), cv = document.createElement("canvas"); cv._n = n; cv.width = 10; cv.height = 10; cv.style.width = W + "px"; cv.style.height = Math.round(W * v1.height / v1.width) + "px"; c.append(cv); obs.observe(cv); }
  }
  let aberto = null;
  function fechar(){ if (!aberto) return; (aberto.urls || []).forEach(u => URL.revokeObjectURL(u)); try { aberto.box.close(); } catch(e){} aberto.box.remove(); document.body.style.overflow = aberto.ov; aberto = null; }
  async function abrir(url, nome, mime){
    fechar();
    const box = document.createElement("dialog"); box.id = "axv"; box.setAttribute("aria-label", "Anexo " + nome);
    box.innerHTML = '<div class="axv-h"><button type="button" class="axv-x">' + ICO_X + 'Fechar</button><div class="axv-t"><span class="axv-n"></span><span class="axv-s"></span></div><button type="button" class="axv-b">' + ICO_BAIXAR + 'Baixar</button></div><div class="axv-c"><div class="axv-msg">Carregando…</div></div>';
    box.querySelector(".axv-n").textContent = nome || "Anexo"; const c = box.querySelector(".axv-c"), sub = box.querySelector(".axv-s");
    aberto = { box, urls:[], ov:document.body.style.overflow }; document.body.style.overflow = "hidden"; c.tabIndex = -1; c.setAttribute("autofocus", ""); document.body.append(box); box.showModal();
    box.addEventListener("cancel", ev => { ev.preventDefault(); if (history.state && history.state.axv) history.back(); else fechar(); });
    try { history.pushState({ axv:1 }, ""); } catch(e){}
    box.querySelector(".axv-x").addEventListener("click", () => { if (history.state && history.state.axv) history.back(); else fechar(); });
    box.querySelector(".axv-b").addEventListener("click", () => baixar(url, nome, mime));
    let t = tipoDe(nome, mime);
    try {
      if (t === "vid"){ const v = document.createElement("video"); v.src = url; v.controls = true; v.playsInline = true; c.replaceChildren(v); return; }
      const bl = await pegarBlob(url); if (!aberto || aberto.box !== box) return; if (t === "arq") t = tipoDe(nome, bl.type);
      sub.textContent = tam(bl.size);
      if (t === "img"){ const u = URL.createObjectURL(bl); aberto.urls.push(u); const im = document.createElement("img"); im.alt = nome; im.src = u; c.replaceChildren(im); }
      else if (t === "pdf"){ try { await mostrarPdf(bl, c, sub); } catch(e){ c.replaceChildren(Object.assign(document.createElement("div"), { className:"axv-msg", textContent:"Não consegui mostrar a prévia deste PDF. Toque em Baixar pra abrir no seu aparelho." })); } }
      else { const d = document.createElement("div"); d.className = "axv-arq"; d.innerHTML = '<b></b><span>Este tipo de arquivo não tem prévia aqui. Toque em Baixar pra abrir.</span>'; d.querySelector("b").textContent = nome; c.replaceChildren(d); }
    } catch(e){ if (aberto && aberto.box === box) c.replaceChildren(Object.assign(document.createElement("div"), { className:"axv-msg", textContent:"Não consegui carregar o arquivo agora. Feche e tente de novo." })); }
  }
  window.addEventListener("popstate", fechar);
  document.addEventListener("keydown", e => { if (e.key === "Escape" && aberto){ if (history.state && history.state.axv) history.back(); else fechar(); } });
  document.addEventListener("click", e => {
    const dl = e.target.closest && e.target.closest("[data-baixar]");
    if (dl){ e.preventDefault(); e.stopPropagation(); dica("Preparando o arquivo…"); baixar(dl.getAttribute("data-baixar"), dl.getAttribute("data-nome")); return; }
    const a = e.target.closest && e.target.closest("a.ax-img, a.ax-chip");
    if (!a || !nosso(a.href)) return;
    e.preventDefault(); e.stopPropagation();
    abrir(a.href, a.getAttribute("title") || (a.querySelector("span") && a.querySelector("span").textContent) || "arquivo");
  }, true);
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
  try { if (p.data.nome_equipe){ const cur = JSON.parse(localStorage.getItem("cd-me") || "{}"); if (!cur.nome){ cur.nome = p.data.nome_equipe; localStorage.setItem("cd-me", JSON.stringify(cur)); } } } catch(e){}
  document.body.classList.toggle("sem-voltar", admin || visiveis.length < 2); document.body.classList.toggle("e-admin", admin);
  montarClaude(); gate.remove(); document.body.classList.remove("gate");
  const s = document.createElement("script"); s.textContent = document.getElementById("appcode").textContent; document.body.append(s);
  iniciarSino();
  iniciarAnexos();
}
(async () => { const { data: { session } } = await sb.auth.getSession(); if (session) seguir(); else telaEntrar(); })();
})();
