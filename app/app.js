/* Demandô · app próprio (Supabase). Sem build: HTML + JS + CSS. */
(() => {
"use strict";
const CFG = window.DEMANDO;
const sb = window.supabase.createClient(CFG.url, CFG.anon, { auth: { persistSession: true, autoRefreshToken: true, detectSessionInUrl: false } });
const root = document.getElementById("root");

/* ---------- utilidades ---------- */
function h(tag, props, ...kids){
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(props || {})){
    if (v == null || v === false) continue;
    if (k === "class") e.className = v;
    else if (k.startsWith("on")) e.addEventListener(k.slice(2), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  for (const c of kids.flat(Infinity)){ if (c == null || c === false) continue; e.append(c.nodeType ? c : document.createTextNode(String(c))); }
  return e;
}
const IC = {
  plus:'<path d="M12 5v14M5 12h14"/>', check:'<path d="M5 12.5l4.5 4.5L19 7.5"/>', x:'<path d="M6 6l12 12M18 6L6 18"/>',
  out:'<path d="M9 4H5v16h4"/><path d="M16 8l4 4-4 4M20 12H9"/>', users:'<circle cx="9" cy="8" r="3.5"/><path d="M2.5 20a6.5 6.5 0 0 1 13 0"/><path d="M16 4.6a3.5 3.5 0 0 1 0 6.8M18 14.3a6.5 6.5 0 0 1 3.5 5.7"/>',
  play:'<path d="M8 5.5v13l11-6.5z"/>', clock:'<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>', back:'<path d="M15 5l-7 7 7 7"/>',
  t_arte:'<path d="M12 3a9 9 0 1 0 0 18c1.7 0 2-1.2 1.4-2.1-.7-1.1.1-2.4 1.4-2.4H17a4 4 0 0 0 4-4C21 6.9 17 3 12 3z"/><circle cx="7.6" cy="11.4" r=".6"/><circle cx="10.6" cy="7.4" r=".6"/><circle cx="15.2" cy="7.4" r=".6"/>',
  t_video:'<rect x="3" y="5" width="18" height="14" rx="3.5"/><path d="M10.5 9.4v5.2l4.3-2.6z"/>',
  t_post:'<rect x="4" y="4" width="16" height="16" rx="4"/><circle cx="9" cy="9.5" r="1.5"/><path d="M4.5 17l4.5-4.5 3.5 3.5 2.5-2.5 4.5 4.5"/>',
  t_stories:'<circle cx="12" cy="12" r="9"/><path d="M12 8v8M8 12h8"/>', t_cob:'<path d="M4 8h3l2-3h6l2 3h3v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
  t_release:'<rect x="4" y="5" width="16" height="14" rx="2.5"/><path d="M8 9h8M8 12.5h8M8 16h5"/>', t_camp:'<path d="M4 10v4l4 .6L17 19V5L8 9.4z"/><path d="M20.5 9.5v5"/>',
  t_pat:'<path d="M12 3.5l2.6 5.3 5.9.8-4.3 4.1 1 5.8L12 16.8 6.8 19.5l1-5.8L3.5 9.6l5.9-.8z"/>', t_out:'<path d="M13 3L5 13.5h6L10 21l8-10.5h-6z"/>'
};
function icon(n){ const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("class", "i"); s.innerHTML = IC[n] || ""; return s; }
const norm = s => String(s || "").normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
const TIPO_IC = [["video","t_video"],["arte","t_arte"],["stories","t_stories"],["post","t_post"],["release","t_release"],["campanha","t_camp"],["patroc","t_pat"],["cobertura","t_cob"]];
const tipoIcon = t => { const x = norm(t); const f = TIPO_IC.find(([k]) => x.includes(k)); return f ? f[1] : "t_out"; };
const TIPOS_PADRAO = {
  fed: ["Arte","Vídeo","Post","Stories","Cobertura de jogo","Patrocinador","Release","Outro"],
  asc: ["Arte","Vídeo","Post","Stories","Release","Cobertura de evento","Campanha","Outro"],
  outras: ["Arte","Vídeo","Post","Stories","Release","Cobertura","Campanha","Outro"]
};
const tiposDe = a => (a.tipos && a.tipos.length) ? a.tipos : (TIPOS_PADRAO[a.id] || TIPOS_PADRAO.outras);
const PERFIL_CORES = ["#2563EB","#DB2777","#EA580C","#7C3AED","#0891B2","#CA8A04","#059669","#DC2626"];
const STATUS = ["A fazer","Em produção","Entregue"], STK = {"A fazer":"s0","Em produção":"s1","Entregue":"s3"};
const pad = n => String(n).padStart(2, "0");
const iso = d => d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate());
const hoje = () => iso(new Date());
const addDias = (s, n) => { const [y, m, d] = s.split("-").map(Number); return iso(new Date(y, m - 1, d + n)); };
const MES = ["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"];
const fmtData = s => s ? Number(s.slice(8, 10)) + " de " + MES[Number(s.slice(5, 7)) - 1] : "";
const fmtHora = s => { if (!s) return ""; const [a, m] = s.split(":"); return m === "00" ? Number(a) + "h" : Number(a) + "h" + m; };
const primeiro = n => String(n || "").trim().split(/\s+/)[0];
const novoId = () => "d" + Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
const emailDe = u => { const [l, d] = CFG.emailCentral.split("@"); return l + "+" + norm(u) + "@" + d; };
let toastT = null;
function toast(msg){ const t = document.getElementById("toast"); t.textContent = msg; t.hidden = false; clearTimeout(toastT); toastT = setTimeout(() => t.hidden = true, 3200); }

/* ---------- estado ---------- */
const S = { user: null, pessoa: null, areas: [], secretarias: [], demandas: [], meusAcessos: [], filtro: "all", busca: "", view: "lista", canal: null, pessoas: [], todosAcessos: [] };
const ehAdmin = () => !!S.pessoa && S.pessoa.papel === "admin";
const areaDe = id => S.areas.find(a => a.id === id);
const podeEscrever = areaId => ehAdmin() || (S.pessoa && S.pessoa.papel === "membro" && S.meusAcessos.includes(areaId));
const podeEditar = d => ehAdmin() || (d.criado_por === S.user.id && podeEscrever(d.area_id));
const corDe = d => { const a = areaDe(d.area_id); if (!a) return "#6B7B75"; const i = d.perfil ? (a.perfis || []).indexOf(d.perfil) : -1; return i >= 0 ? PERFIL_CORES[i % PERFIL_CORES.length] : a.cor; };

/* ---------- telas de entrada ---------- */
const MARCA = () => { const s = document.createElementNS("http://www.w3.org/2000/svg", "svg"); s.setAttribute("viewBox", "0 0 120 120");
  s.innerHTML = '<rect width="120" height="120" rx="30" fill="#121A17"/><path d="M60 47 A23 23 0 0 0 60 93" fill="none" stroke="#1F4FD1" stroke-width="13"/><path d="M60 47 A23 23 0 0 1 60 93" fill="none" stroke="#0E7A4D" stroke-width="13"/><path d="M41 36 L60 21 L79 36" fill="none" stroke="#fff" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>'; return s; };
const marca = () => h("div", {class: "marca"}, MARCA(), h("b", null, "Demandô"));
function montar(...nos){ root.replaceChildren(...nos.filter(Boolean)); }
function telaCarregando(){ montar(h("div", {class: "entrada"}, h("div", {class: "cartao"}, marca(), h("p", {class: "sub"}, "Carregando…")))); }

function telaEntrar(aviso){
  const u = h("input", {id: "usuario", autocomplete: "username", autocapitalize: "none", spellcheck: "false", placeholder: "ex.: juninho"});
  const s = h("input", {id: "senha", type: "password", autocomplete: "current-password", placeholder: "Sua senha"});
  const e = h("p", {class: "err", id: "erro", hidden: !aviso}, aviso || "");
  const go = h("button", {class: "btn pri", id: "entrar", type: "button"}, "Entrar");
  async function fazer(){
    e.hidden = true;
    if (!u.value.trim() || !s.value){ e.textContent = "Preencha o usuário e a senha."; e.hidden = false; return; }
    go.disabled = true;
    const r = await entrar(u.value, s.value);
    go.disabled = false;
    if (r) { e.textContent = r; e.hidden = false; }
  }
  go.addEventListener("click", fazer);
  [u, s].forEach(i => i.addEventListener("keydown", ev => { if (ev.key === "Enter") fazer(); }));
  montar(h("div", {class: "entrada"}, h("div", {class: "cartao"}, marca(), h("h2", null, "Entrar"),
    h("label", {class: "fl"}, h("span", null, "Usuário"), u), h("label", {class: "fl"}, h("span", null, "Senha"), s), e, go,
    h("button", {class: "trocar", id: "criar", type: "button", onclick: () => telaCriar()}, "Criar meu perfil"))));
}
async function entrar(usuario, senha){
  const { data, error } = await sb.auth.signInWithPassword({ email: emailDe(usuario), password: senha });
  if (error) return /rate|many/i.test(error.message) ? "Muitas tentativas. Espere um pouco." : "Usuário ou senha incorretos.";
  S.user = data.user; await carregar(); return null;
}
function telaCriar(){
  const f = {};
  const campo = (id, rot, props) => { const i = h("input", Object.assign({id}, props)); f[id] = i; return h("label", {class: "fl"}, h("span", null, rot), i); };
  const e = h("p", {class: "err", id: "erro", hidden: true});
  const go = h("button", {class: "btn pri", id: "enviar", type: "button"}, "Criar perfil");
  go.addEventListener("click", async () => {
    e.hidden = true; go.disabled = true;
    try {
      const r = await fetch(CFG.url + "/functions/v1/criar-perfil", { method: "POST", headers: {"Content-Type": "application/json", apikey: CFG.anon},
        body: JSON.stringify({ nome: f.nome.value, usuario: f.usuario.value, senha: f.senha.value, codigo: f.codigo.value }) });
      const j = await r.json().catch(() => ({}));
      if (!r.ok){ e.textContent = j.erro || "Não deu pra criar o perfil agora."; e.hidden = false; go.disabled = false; return; }
      const erro = await entrar(f.usuario.value, f.senha.value);
      if (erro) telaEntrar("Perfil criado. Agora entre com o seu usuário e a senha.");
    } catch(_){ e.textContent = "Sem conexão. Tente de novo."; e.hidden = false; go.disabled = false; }
  });
  montar(h("div", {class: "entrada"}, h("div", {class: "cartao"}, marca(), h("h2", null, "Criar perfil"),
    h("p", {class: "sub"}, "Depois de criar, um admin libera o seu acesso."),
    campo("nome", "Seu nome", {autocomplete: "name", placeholder: "Nome e sobrenome"}),
    campo("usuario", "Usuário (pra entrar)", {autocapitalize: "none", spellcheck: "false", placeholder: "ex.: juninho"}),
    campo("senha", "Senha (mínimo 8)", {type: "password", autocomplete: "new-password"}),
    campo("codigo", "Código da equipe", {autocapitalize: "characters", placeholder: "Pergunte ao admin"}),
    e, go, h("button", {class: "trocar", id: "voltar", type: "button", onclick: () => telaEntrar()}, "Já tenho perfil"))));
}
async function sair(){ if (S.canal) { sb.removeChannel(S.canal); S.canal = null; } await sb.auth.signOut(); limpar(); telaEntrar(); }
function limpar(){ Object.assign(S, { user: null, pessoa: null, areas: [], secretarias: [], demandas: [], meusAcessos: [], filtro: "all", busca: "", view: "lista", pessoas: [], todosAcessos: [] }); }
function telaAviso(titulo, texto, extra){
  montar(h("div", {class: "entrada"}, h("div", {class: "cartao"}, marca(), h("h2", null, titulo), h("p", {class: "sub"}, texto),
    ...(extra || []), h("button", {class: "trocar", id: "sair", type: "button", onclick: sair}, "Sair"))));
}

/* ---------- dados ---------- */
async function carregar(){
  telaCarregando();
  const [p, a, s, d, ac] = await Promise.all([
    sb.from("pessoas").select("*").eq("id", S.user.id).maybeSingle(),
    sb.from("areas").select("*").order("ordem"),
    sb.from("secretarias").select("*").order("ordem"),
    sb.from("demandas").select("*").order("prazo", {nullsFirst: false}),
    sb.from("acessos").select("area_id").eq("pessoa_id", S.user.id)
  ]);
  if (p.error || !p.data) return telaAviso("Não deu pra carregar", "Tente de novo em instantes.", [h("button", {class: "btn", onclick: carregar}, "Tentar de novo")]);
  S.pessoa = p.data; S.areas = a.data || []; S.secretarias = s.data || []; S.demandas = d.data || []; S.meusAcessos = (ac.data || []).map(x => x.area_id);
  if (!S.pessoa.ativo) return telaAviso("Acesso desativado", "Fale com o admin pra voltar a usar o Demandô.");
  if (!S.areas.length) return telaAviso("Aguardando liberação", "Seu perfil foi criado. Assim que um admin liberar as suas áreas, elas aparecem aqui.",
    [h("button", {class: "btn", id: "atualizar", onclick: carregar}, "Já liberaram? Atualizar")]);
  assinar(); telaApp();
}
function assinar(){
  if (S.canal) sb.removeChannel(S.canal);
  S.canal = sb.channel("demando")
    .on("postgres_changes", {event: "*", schema: "public", table: "demandas"}, p => {
      if (p.eventType === "DELETE") S.demandas = S.demandas.filter(x => x.id !== p.old.id);
      else { const i = S.demandas.findIndex(x => x.id === p.new.id); if (i >= 0) S.demandas[i] = p.new; else S.demandas.push(p.new); }
      renderLista(); if (aberta && aberta.tipo === "detalhe" && aberta.dialog.open) abrirDetalhe(aberta.id, true);
    })
    .on("postgres_changes", {event: "*", schema: "public", table: "areas"}, async () => { const r = await sb.from("areas").select("*").order("ordem"); if (r.data){ S.areas = r.data; renderChips(); renderLista(); } })
    .subscribe();
}

/* ---------- tela principal ---------- */
let listaEl, chipsEl;
function telaApp(){
  S.view = "lista";
  listaEl = h("div", {id: "lista"}); chipsEl = h("div", {class: "chips", id: "chips"});
  const busca = h("input", {class: "busca", id: "busca", type: "search", placeholder: "Buscar demanda…"});
  busca.addEventListener("input", () => { S.busca = busca.value; renderLista(); });
  const podeCriar = S.areas.some(a => podeEscrever(a.id));
  montar(
    h("div", {class: "top"}, marca(),
      h("div", {class: "quem"}, primeiro(S.pessoa.nome), h("br"), ehAdmin() ? "admin" : (S.pessoa.papel === "leitor" ? "só acompanha" : "equipe")),
      ehAdmin() ? h("button", {class: "ic", id: "bt-pessoas", "aria-label": "Pessoas", onclick: abrirPessoas}, icon("users")) : null,
      h("button", {class: "ic", id: "bt-sair", "aria-label": "Sair", onclick: sair}, icon("out"))),
    h("div", {class: "wrap"}, chipsEl, busca, listaEl),
    podeCriar ? h("button", {class: "fab", id: "fab", "aria-label": "Nova demanda", onclick: () => abrirForm(null)}, icon("plus")) : null);
  renderChips(); renderLista();
}
function renderChips(){
  if (!chipsEl) return;
  const itens = [["all", "Todas", null]].concat(S.areas.map(a => [a.id, a.sigla, a.cor]));
  chipsEl.replaceChildren(...itens.map(([id, nome, cor]) => h("button", {class: "chip", "data-a": id, "aria-pressed": String(S.filtro === id),
    style: cor ? "--c:" + cor : null, onclick: () => { S.filtro = id; renderChips(); renderLista(); }}, cor ? h("i") : null, nome)));
}
const ordem = (a, b) => (a.prazo || "9999").localeCompare(b.prazo || "9999") || (a.hora || "").localeCompare(b.hora || "") || a.titulo.localeCompare(b.titulo);
function renderLista(){
  if (!listaEl) return;
  const q = norm(S.busca), t = hoje(), em7 = addDias(t, 7), sem = addDias(t, -7);
  const vis = S.demandas.filter(d => (S.filtro === "all" || d.area_id === S.filtro) && (!q || norm([d.titulo, d.tipo, d.local, d.perfil, d.secretaria, (d.equipe || []).join(" ")].join(" ")).includes(q)));
  const abertas = vis.filter(d => d.status !== "Entregue");
  const grupos = [
    ["Atrasadas", abertas.filter(d => d.prazo && d.prazo < t), true], ["Hoje", abertas.filter(d => d.prazo === t)],
    ["Próximos 7 dias", abertas.filter(d => d.prazo > t && d.prazo <= em7)], ["Depois", abertas.filter(d => d.prazo > em7)],
    ["Sem prazo", abertas.filter(d => !d.prazo)], ["Entregues na última semana", vis.filter(d => d.status === "Entregue" && (d.entregue || d.prazo || "") >= sem)]
  ].filter(g => g[1].length);
  if (!grupos.length){ listaEl.replaceChildren(h("div", {class: "vazio", id: "vazio"}, S.demandas.length ? "Nada por aqui com esse filtro." : "Nenhuma demanda ainda.")); return; }
  listaEl.replaceChildren(...grupos.map(([nome, lista, late]) => h("section", null,
    h("div", {class: "gh" + (late ? " late" : "")}, h("h3", null, nome), h("span", {class: "n"}, lista.length)),
    h("div", {class: "lista"}, ...lista.sort(ordem).map(linha)))));
}
function chipsDemanda(d, comArea){
  const a = areaDe(d.area_id), t = hoje(), aberta = d.status !== "Entregue";
  const prazoCls = aberta && d.prazo && d.prazo < t ? " late" : (aberta && d.prazo === t ? " today" : "");
  const prazoTxt = d.prazo ? (prazoCls === " late" ? "Atrasada · " + fmtData(d.prazo) : prazoCls === " today" ? "Hoje" : fmtData(d.prazo)) : "";
  return [
    comArea && a ? h("span", {class: "tag"}, a.sigla) : null, d.tipo ? h("span", null, d.tipo) : null,
    h("span", {class: "sc " + STK[d.status]}, h("i"), d.status),
    prazoTxt ? h("span", {class: "pill" + prazoCls}, prazoTxt) : null,
    d.hora ? h("span", {class: "pill"}, icon("clock"), fmtHora(d.hora)) : null,
    d.perfil ? h("span", {class: "tag"}, primeiro(d.perfil)) : null,
    (d.equipe || []).length ? h("span", {class: "pill"}, h("b", null, d.equipe.length > 3 ? d.equipe.slice(0, 3).map(primeiro).join(", ") + " +" + (d.equipe.length - 3) : d.equipe.map(primeiro).join(", "))) : null
  ];
}
function linha(d){
  const atras = d.status !== "Entregue" && d.prazo && d.prazo < hoje();
  const prox = d.status === "A fazer" ? "Em produção" : d.status === "Em produção" ? "Entregue" : null;
  return h("div", {class: "rw" + (atras ? " late" : "") + (d.status === "Entregue" ? " done" : ""), "data-id": d.id, style: "--a:" + corDe(d), onclick: () => abrirDetalhe(d.id)},
    h("span", {class: "tile"}, icon(tipoIcon(d.tipo))),
    h("div", {class: "body"}, h("div", {class: "tt"}, d.titulo), h("div", {class: "meta"}, ...chipsDemanda(d, S.filtro === "all"))),
    prox && podeEscrever(d.area_id) ? h("button", {class: "avan" + (prox === "Entregue" ? " ok" : ""), "data-avanca": d.id, title: "Mover para " + prox, "aria-label": "Mover para " + prox,
      onclick: ev => { ev.stopPropagation(); mudarStatus(d, prox); }}, icon(prox === "Entregue" ? "check" : "play")) : null);
}
async function mudarStatus(d, novo){
  const antes = {status: d.status, entregue: d.entregue, historico: d.historico};
  const upd = { status: novo, entregue: novo === "Entregue" ? hoje() : null, historico: (d.historico || []).concat([{em: Date.now(), txt: "Etapa: " + d.status + " → " + novo, por: S.user.id}]) };
  Object.assign(d, upd); renderLista();
  const { error } = await sb.from("demandas").update(upd).eq("id", d.id);
  if (error){ Object.assign(d, antes); renderLista(); toast("Não deu pra salvar a mudança."); }
}

/* ---------- folhas: detalhe e formulário ---------- */
let aberta = null;
function folha(titulo, corpo, rodape){
  const dlg = h("dialog", null, h("div", {class: "sh"},
    h("div", {class: "sh-h"}, h("h2", null, titulo), h("button", {class: "ic", "aria-label": "Fechar", onclick: () => dlg.close()}, icon("x"))),
    h("div", {class: "sh-b"}, corpo), rodape ? h("div", {class: "sh-f"}, rodape) : null));
  dlg.addEventListener("close", () => { dlg.remove(); if (aberta && aberta.dialog === dlg) aberta = null; });
  dlg.addEventListener("click", e => { if (e.target === dlg) dlg.close(); });
  document.body.append(dlg); dlg.showModal(); return dlg;
}
function abrirDetalhe(id, refresh){
  const d = S.demandas.find(x => x.id === id); if (!d) { if (aberta) aberta.dialog.close(); return; }
  if (aberta && refresh) aberta.dialog.remove(); else if (aberta) aberta.dialog.close();
  const a = areaDe(d.area_id), escreve = podeEscrever(d.area_id);
  const info = [["Prazo", d.prazo ? fmtData(d.prazo) : "Sem prazo", true]];
  if (d.hora) info.push(["Horário", fmtHora(d.hora)]);
  if (d.local) info.push(["Local", d.local]);
  if (d.perfil) info.push(["Perfil", d.perfil]);
  if (d.secretaria) info.push(["Secretaria", d.secretaria]);
  if ((d.equipe || []).length) info.push(["Equipe", d.equipe.join(", "), true]);
  info.push(["Criada em", fmtData(d.criado)]); if (d.entregue) info.push(["Entregue em", fmtData(d.entregue)]);
  const corpo = [
    h("div", {class: "hero", style: "--a:" + corDe(d)}, h("span", {class: "tile big"}, icon(tipoIcon(d.tipo))),
      h("div", null, h("h2", null, d.titulo), h("div", {class: "meta"}, a ? h("span", {class: "tag"}, a.sigla) : null, d.tipo ? h("span", null, d.tipo) : null))),
    escreve ? h("div", {class: "stepper", role: "group"}, ...STATUS.map(s => h("button", {type: "button", "data-s": s, "aria-pressed": String(d.status === s),
      onclick: () => { if (d.status !== s) mudarStatus(d, s); }}, s))) : h("div", null, h("span", {class: "sc " + STK[d.status]}, h("i"), d.status)),
    h("div", {class: "it-g"}, ...info.map(([k, v, full]) => h("div", {class: "it" + (full ? " full" : "")}, h("small", null, k), h("b", null, v)))),
    d.obs ? h("div", null, h("p", {class: "sec-l"}, "Observações"), h("div", {class: "it full"}, h("b", {style: "font-weight:500;white-space:pre-wrap"}, d.obs))) : null,
    (d.historico || []).length ? h("div", null, h("p", {class: "sec-l"}, "Histórico"), h("ul", {class: "hist"},
      ...(d.historico || []).slice().reverse().slice(0, 8).map(x => h("li", null, x.txt + " · " + new Date(x.em).toLocaleDateString("pt-BR", {day: "2-digit", month: "2-digit"}))))) : null
  ];
  const rod = podeEditar(d) ? [h("button", {class: "btn bad", id: "excluir", onclick: () => apagar(d)}, "Excluir"), h("span", {class: "sp"}), h("button", {class: "btn pri", id: "editar", onclick: () => abrirForm(d)}, "Editar")] : null;
  const dialog = folha("Demanda", corpo, rod); aberta = {id, dialog, tipo: "detalhe"};
}
async function apagar(d){
  if (!confirm("Apagar esta demanda?")) return;
  const { error } = await sb.from("demandas").delete().eq("id", d.id);
  if (error) return toast("Não deu pra apagar.");
  S.demandas = S.demandas.filter(x => x.id !== d.id); if (aberta) aberta.dialog.close(); renderLista(); toast("Demanda apagada");
}
function abrirForm(d){
  const escreve = S.areas.filter(a => podeEscrever(a.id));
  if (!escreve.length) return toast("Você só acompanha as demandas.");
  if (aberta) aberta.dialog.close();
  const st = { area_id: d ? d.area_id : (escreve.find(a => a.id === S.filtro) || escreve[0]).id, titulo: d ? d.titulo : "", tipo: d ? (d.tipo || "") : "", prazo: d ? (d.prazo || "") : "",
    hora: d && d.hora ? d.hora.slice(0, 5) : "", local: d ? (d.local || "") : "", perfil: d ? (d.perfil || "") : "", secretaria: d ? (d.secretaria || "") : "",
    equipe: d ? (d.equipe || []).slice() : [], obs: d ? (d.obs || "") : "", status: d ? d.status : "A fazer" };
  const corpo = h("div", {class: "form"});
  const campo = (rot, el) => h("label", {class: "fl"}, h("span", null, rot), el);
  const entrada = (k, props) => { const i = h("input", props || {}); i.value = st[k]; i.addEventListener("input", () => st[k] = i.value); return i; };
  const pills = (lista, ativo, clica, id) => h("div", {class: "pills", id}, ...lista.map(n => h("button", {type: "button", "aria-pressed": String(ativo(n)), onclick: () => clica(n)}, n)));
  function desenha(){
    const a = areaDe(st.area_id), tipos = tiposDe(a); if (st.tipo && !tipos.includes(st.tipo)) st.tipo = "";
    if (!st.tipo) st.tipo = tipos[0];
    const sel = h("select", {id: "f-tipo"}, ...tipos.map(t => h("option", {value: t}, t))); sel.value = st.tipo; sel.addEventListener("change", () => st.tipo = sel.value);
    const obs = h("textarea", {maxlength: "2000", id: "f-obs"}); obs.value = st.obs; obs.addEventListener("input", () => st.obs = obs.value);
    const ss = h("select", {id: "f-sec"}, h("option", {value: ""}, "—"), ...S.secretarias.map(x => h("option", {value: x.nome}, x.nome))); ss.value = st.secretaria; ss.addEventListener("change", () => st.secretaria = ss.value);
    corpo.replaceChildren(...[
      campo("O que precisa ser feito", entrada("titulo", {id: "f-titulo", maxlength: "140", placeholder: "Ex.: arte da 5ª rodada"})),
      escreve.length > 1 ? campo("Área", h("div", {class: "pills", id: "f-area"}, ...escreve.map(x => h("button", {type: "button", "data-a": x.id, "aria-pressed": String(st.area_id === x.id),
        onclick: () => { st.area_id = x.id; st.perfil = ""; st.secretaria = ""; st.equipe = []; st.tipo = ""; desenha(); }}, x.sigla)))) : null,
      d ? campo("Etapa", pills(STATUS, s => st.status === s, s => { st.status = s; desenha(); }, "f-status")) : null,
      campo("Tipo", sel),
      h("div", {class: "row2"}, campo("Prazo", entrada("prazo", {type: "date", id: "f-prazo"})), campo("Horário", entrada("hora", {type: "time", id: "f-hora"}))),
      campo("Local", entrada("local", {id: "f-local", maxlength: "120", placeholder: "Ex.: Escola Maria Neuza"})),
      (a.perfis || []).length ? campo("Perfil", pills(a.perfis, n => st.perfil === n, n => { st.perfil = st.perfil === n ? "" : n; desenha(); }, "f-perfil")) : null,
      a.id === "asc" && S.secretarias.length ? campo("Secretaria", ss) : null,
      (a.equipe || []).length ? campo("Equipe", pills(a.equipe, n => st.equipe.includes(n), n => { st.equipe = st.equipe.includes(n) ? st.equipe.filter(x => x !== n) : st.equipe.concat(n); desenha(); }, "f-equipe")) : null,
      campo("Observações", obs)].filter(Boolean));
  }
  desenha();
  const erro = h("p", {class: "err", hidden: true, id: "f-erro"});
  const salvar = h("button", {class: "btn pri", id: "salvar"}, "Salvar");
  salvar.addEventListener("click", async () => {
    erro.hidden = true;
    if (st.titulo.trim().length < 2){ erro.textContent = "Escreva o que precisa ser feito."; erro.hidden = false; return; }
    salvar.disabled = true;
    const row = { area_id: st.area_id, titulo: st.titulo.trim(), tipo: st.tipo || null, prazo: st.prazo || null, hora: st.hora || null, local: st.local.trim() || null,
      perfil: st.perfil || null, secretaria: st.area_id === "asc" ? (st.secretaria || null) : null, equipe: st.equipe, obs: st.obs.trim() || null, status: st.status };
    let r;
    if (d){
      if (row.status !== d.status) { row.entregue = row.status === "Entregue" ? hoje() : null; row.historico = (d.historico || []).concat([{em: Date.now(), txt: "Etapa: " + d.status + " → " + row.status, por: S.user.id}]); }
      r = await sb.from("demandas").update(row).eq("id", d.id).select().single();
    } else {
      r = await sb.from("demandas").insert(Object.assign({ id: novoId(), criado_por: S.user.id, entregue: row.status === "Entregue" ? hoje() : null, historico: [{em: Date.now(), txt: "Criada", por: S.user.id}] }, row)).select().single();
    }
    salvar.disabled = false;
    if (r.error){ erro.textContent = r.error.code === "42501" || r.error.code === "P0001" ? "Você não tem permissão pra isso." : "Não deu pra salvar agora."; erro.hidden = false; return; }
    const i = S.demandas.findIndex(x => x.id === r.data.id); if (i >= 0) S.demandas[i] = r.data; else S.demandas.push(r.data);
    dlg.close(); renderLista(); toast(d ? "Demanda atualizada" : "Demanda criada");
  });
  const dlg = folha(d ? "Editar demanda" : "Nova demanda", [corpo, erro], [h("button", {class: "btn", onclick: () => dlg.close()}, "Cancelar"), h("span", {class: "sp"}), salvar]);
  aberta = {id: d ? d.id : null, dialog: dlg, tipo: "form"};
}

/* ---------- pessoas (admin) ---------- */
async function abrirPessoas(){
  S.view = "pessoas";
  const [p, ac] = await Promise.all([sb.from("pessoas").select("*").order("criado_em", {ascending: false}), sb.from("acessos").select("*")]);
  S.pessoas = p.data || []; S.todosAcessos = ac.data || [];
  const lista = h("div", {class: "pes", id: "pessoas"});
  const desenhar = () => lista.replaceChildren(...S.pessoas.map(cartaoPessoa));
  desenhar();
  montar(h("div", {class: "top"}, h("button", {class: "ic", id: "bt-voltar", "aria-label": "Voltar", onclick: () => { S.view = "lista"; telaApp(); }}, icon("back")), h("div", {class: "marca"}, h("b", null, "Pessoas"))),
    h("div", {class: "wrap"}, h("p", {class: "hint", style: "margin:4px 0 14px"}, "Quem cria um perfil aparece aqui sem acesso. Escolha o papel e as áreas e salve."), lista));
}
function cartaoPessoa(p){
  const eu = p.id === S.user.id, tem = S.todosAcessos.filter(x => x.pessoa_id === p.id).map(x => x.area_id);
  const pend = p.papel !== "admin" && !tem.length;
  const st = { papel: p.papel, ativo: p.ativo, areas: new Set(tem) };
  const papel = h("select", {"data-papel": p.usuario, disabled: eu}, ...[["admin", "Admin"], ["membro", "Membro (cria e muda)"], ["leitor", "Leitor (só acompanha)"]].map(([v, t]) => h("option", {value: v}, t)));
  papel.value = p.papel; papel.addEventListener("change", () => st.papel = papel.value);
  const ativo = h("input", {type: "checkbox", disabled: eu, "data-ativo": p.usuario}); ativo.checked = p.ativo; ativo.addEventListener("change", () => st.ativo = ativo.checked);
  const btn = h("button", {class: "btn pri sm", "data-salvar": p.usuario}, "Salvar");
  btn.addEventListener("click", async () => {
    btn.disabled = true;
    const e1 = await sb.from("pessoas").update({papel: st.papel, ativo: st.ativo}).eq("id", p.id);
    const novas = [...st.areas].filter(a => !tem.includes(a)), tiradas = tem.filter(a => !st.areas.has(a));
    const e2 = novas.length ? await sb.from("acessos").insert(novas.map(a => ({pessoa_id: p.id, area_id: a}))) : {};
    const e3 = tiradas.length ? await sb.from("acessos").delete().eq("pessoa_id", p.id).in("area_id", tiradas) : {};
    btn.disabled = false;
    if (e1.error || e2.error || e3.error) return toast("Não deu pra salvar.");
    p.papel = st.papel; p.ativo = st.ativo; S.todosAcessos = S.todosAcessos.filter(x => x.pessoa_id !== p.id).concat([...st.areas].map(a => ({pessoa_id: p.id, area_id: a})));
    toast("Salvo: " + primeiro(p.nome)); abrirPessoas();
  });
  return h("div", {class: "pc" + (pend ? " pend" : ""), "data-pessoa": p.usuario},
    h("div", null, h("h3", null, p.nome, pend ? h("span", {class: "badge"}, "Aguardando") : null), h("div", {class: "u"}, "@" + p.usuario)),
    h("label", {class: "fl"}, h("span", null, "Papel"), papel),
    h("div", null, h("p", {class: "sec-l"}, "Áreas"), h("div", {class: "pills", style: "gap:10px"}, ...S.areas.map(a => {
      const c = h("input", {type: "checkbox", "data-area": a.id}); c.checked = st.areas.has(a.id); c.addEventListener("change", () => c.checked ? st.areas.add(a.id) : st.areas.delete(a.id));
      return h("label", {class: "ck"}, c, a.sigla); }))),
    h("label", {class: "ck"}, ativo, "Acesso ativo"), btn);
}

/* ---------- início ---------- */
(async () => {
  telaCarregando();
  sb.auth.onAuthStateChange(ev => { if (ev === "SIGNED_OUT" && S.user){ limpar(); telaEntrar(); } });
  const { data: { session } } = await sb.auth.getSession();
  if (session){ S.user = session.user; await carregar(); } else telaEntrar();
})();
})();
