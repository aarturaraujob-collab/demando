#!/usr/bin/env python3
"""Gera app2/index.html a partir do painel do Claude (central-demandas.html):
troca só o que depende do Claude (login, senhas, dados) pela ponte com o Supabase.
Uso: python3 tools/build_app.py <central-demandas.html> <pasta-de-saida>"""
import re, sys, os, shutil
src, out = sys.argv[1], sys.argv[2]
aqui = os.path.dirname(os.path.abspath(__file__))
h = open(src, encoding="utf-8").read()
m = re.search(r"<script>\n(.*)</script>\n</body>", h, re.S); assert m, "script principal não encontrado"
app = m.group(1)

def rep(a, b, c=1):
    global app
    assert app.count(a) == c, (app.count(a), a[:90]); app = app.replace(a, b)
def cut(ini, fim, novo):
    global app
    i = app.index(ini); j = app.index(fim, i); app = app[:i] + novo + app[j:]

# 1) escolha de área: sem senha, só as áreas da conta
cut("  function frPicker(){", "  function renderAreaBanner(){", '''  function frPicker(){
    const permitidas = (window.DEMANDO_API && window.DEMANDO_API.areas) || [];
    const b = (f) => el("button",{type:"button", class:"fr-pick " + f, onclick:() => setStaffFr(f, "T")},
      el("span",{class:"fr-dot"}), el("span",{class:"fr-pt"}, el("b",null, LBL[f]), el("small",null, NOME_FR[f])));
    const hb = $(".side .brand").cloneNode(true);
    return el("div",{class:"pick-wrap"}, el("div",{class:"hero"}, hb),
      el("section",{class:"who-pick"}, el("b",null,"Qual é a sua área?"), el("p",{class:"hint"},"Escolha a área que você quer ver."),
        el("div",{class:"fr-g"}, ...areaIds().filter(k => permitidas.includes(k)).map(b)),
        el("button",{type:"button", class:"fr-add", onclick:() => window.DEMANDO_API.sair()}, "Sair da conta")));
  }
''')
# 2) o botão "Admin" vira "Sair da conta"
rep('function openAdm(){\n', 'function openAdm(){\n    window.DEMANDO_API.sair(); return;\n')
rep('b.replaceChildren(icon(role === "admin" ? "unlock" : "lock"), el("span",{class:"al"}, role === "admin" ? "Sair do admin" : "Admin"));', 'b.replaceChildren(icon("lock"), el("span",{class:"al"}, "Sair da conta"));')
# 3) formulário de área sem senha
rep('''      el("label",{class:"fl"}, cur ? "Nova senha (deixe vazio pra manter)" : "Senha da área", p1),
      el("label",{class:"fl"}, "Repita a senha", p2), err, go);''', '      err, go);')
rep('''      if (!cur && p1.value.length < 4) return bad("A senha precisa de pelo menos 4 caracteres.");
      if (p1.value && p1.value.length < 4) return bad("A senha precisa de pelo menos 4 caracteres.");
      if (p1.value !== p2.value) return bad("As senhas não são iguais.");
''', '')
rep('hash: p1.value ? await sha(id + ":" + p1.value) : cur.hash,', 'hash: "T",')
rep('nome, cor e senha ficam como estão.', 'nome e cor ficam como estão.')
# 4) aba Mais: Pessoas no lugar de Senhas
rep('["area","Áreas"],["senha","Senhas"]];', '["area","Áreas"],["pessoas","Pessoas"]];')
rep('area:panelArea, senha:panelSenha})[maisTab](box);', 'area:panelArea, pessoas:panelPessoas})[maisTab](box);')
rep('  function panelSenha(box){', open(os.path.join(aqui, "pessoas_panel.js"), encoding="utf-8").read() + '  function panelSenha(box){')

# 6) leitura por IA: mensagens próprias do servidor (o painel original fala em "Claude")
rep('    not_granted: "Sem permissão pra ler a foto. Libere o acesso ao Claude no menu do painel e tente de novo.",', '    not_configured: "A leitura por foto e texto ainda não foi ativada neste servidor. Falta a chave da Anthropic: fale com o admin.",\n    not_granted: "Sem permissão pra usar a leitura por IA. Fale com o admin.",')


# 7) "Quem é você?": só nomes da equipe das áreas da pessoa, e o nome escolhido vira o "nome na equipe" (é ele que recebe as notificações)
rep('  function chooser(){', '  function nomesDoUsuario(){ const ks = (window.DEMANDO_API && window.DEMANDO_API.areas) || []; const l = Array.from(new Set(ks.flatMap(k => EQUIPES[k] || []))); return l.length ? l : TODOS; }\n  function chooser(){')
rep('guess = TODOS.find(n => norm(n) === nm) || "";', 'guess = nomesDoUsuario().find(n => norm(n) === nm) || "";')
rep('...TODOS.map(n => el("button",{type:"button", class:"who-b"', '...nomesDoUsuario().map(n => el("button",{type:"button", class:"who-b"')
rep('saveT = setTimeout(() => { if (perfilRef) perfilRef.set(data).catch(() => {}); }, 400);', 'saveT = setTimeout(() => { if (perfilRef) perfilRef.set(data).catch(() => {}); if (meNome && window.DEMANDO_API) window.DEMANDO_API.guardarNomeEquipe(meNome); }, 400);')
rep('onclick:async e => { try { await Notification.requestPermission(); } catch(_){} e.currentTarget.remove(); }', 'onclick:e => { const s = document.getElementById("sino"); if (s) s.click(); e.currentTarget.remove(); }')


# 8) o funcionário que ainda não escolheu o nome vê o cartão "Quem é você?" logo no topo do Início
rep('    $("#meHold").replaceChildren(); renderAreaBanner();', '    $("#meHold").replaceChildren(); renderAreaBanner();\n    if (view === "today" && role === "staff" && !meNome && !(PERFIS[staffFr] || []).length && nomesDoUsuario().length) $("#meHold").append(chooser());')


# 9) anexos: botão de baixar ao lado de cada arquivo guardado no servidor (abrir/prévia é feito pelo visualizador do adapter)
rep(r"""const anexosGrid = list => { const nodes = (list || []).map(anexoEl).filter(Boolean);""", r"""const comBaixar = (n, a) => { if (!n || !a || !/\/storage\/v1\/object\//.test(a.url || "")) return n; const w = n.classList && n.classList.contains("ax-chip"); return el("div",{class:"ax-w" + (w ? " wide" : "")}, n, el("button",{type:"button", class:"ax-dl", "data-baixar":a.url, "data-nome":a.nome || "arquivo", "aria-label":"Baixar " + (a.nome || "arquivo"), title:"Baixar"}, icon("baixar"))); };
  const anexosGrid = list => { const nodes = (list || []).map(a => comBaixar(anexoEl(a), a)).filter(Boolean);""")
# 10) botão "Sair da conta" no fim do Início e do Mais (no app instalado não há outro jeito de voltar pro login)
rep(r"""baixar:'<path d="M12 4v11"/>""", r"""sair:'<path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><path d="m16 17 5-5-5-5"/><path d="M21 12H9"/>',
  baixar:'<path d="M12 4v11"/>""")
rep(r"""mais:renderMais})[view](); }""", r"""mais:renderMais})[view](); if (window.DEMANDO_API && (view === "today" || view === "mais")) $("#view").append(el("div",{class:"sair-box"}, el("button",{type:"button", class:"sair-b", onclick:() => { if (confirm("Sair da conta?")) window.DEMANDO_API.sair(); }}, icon("sair"), "Sair da conta"))); }""")
# 11) logo da Prefeitura de Boca da Mata no banner da área BM
rep(r"""    ab.replaceChildren(el("span",{class:"abn-s"}, LBL[k]), el("b",{class:"abn-n"}, NOME_FR[k] || SUB[k] || ""));""", r"""    ab.classList.toggle("logo", k === "asc" || k === "fed"); ab.classList.toggle("logo-bm", k === "asc"); ab.classList.toggle("logo-faf", k === "fed");
    if (k === "asc") ab.replaceChildren(el("img",{class:"abn-logo", src:"assets/bm-logo.png", alt:"", draggable:"false"}), el("span",{class:"abn-sr"}, NOME_FR[k] || "Boca da Mata"));
    else if (k === "fed") ab.replaceChildren(el("img",{class:"abn-emb", src:"assets/faf-emblem.png", alt:"", draggable:"false"}), el("span",{class:"abn-sr"}, "Federação Alagoana de Futebol"));
    else ab.replaceChildren(el("span",{class:"abn-s"}, LBL[k]), el("b",{class:"abn-n"}, NOME_FR[k] || SUB[k] || ""));""")


# 12) barra de baixo: sai a "Agenda" (o Início já mostra a agenda) e entra o "+" em destaque no meio, com as 3 opções de criar
rep(r"""  const VIEWS = [["today","Início"],["board","Quadro"],["agenda","Agenda"],["month","Mês"]];""", r"""  const VIEWS = [["today","Início"],["board","Quadro"],["month","Mês"]];""")
rep(r"""  function buildNav(){""", r"""  /* menu do "+": nova demanda, por texto, por foto (usa os mesmos botões que já existiam, agora escondidos) */
  let plusM = null;
  function closePlus(){ if (!plusM) return; plusM.remove(); plusM = null; document.body.classList.remove("pm-open"); const b = document.querySelector(".tab-plus"); if (b){ b.setAttribute("aria-expanded", "false"); b.classList.remove("open"); } }
  function togglePlus(){
    if (plusM) return closePlus();
    const fab = document.getElementById("fab"), orig = k => fab && fab.querySelector('[data-act="' + k + '"]');
    const op = (k, tit, sub, ic) => { const o = orig(k); if (!o || o.hidden) return null; return el("button",{type:"button", role:"menuitem", class:"pm-i", "data-op":k, onclick:() => { closePlus(); o.click(); }}, el("span",{class:"pm-ic"}, icon(ic)), el("span",{class:"pm-t"}, el("b",null,tit), el("small",null,sub))); };
    const itens = [op("new","Nova demanda","do zero","plus"), op("paste","Por texto","copiar e colar","paste"), op("photo","Por foto","tirar ou escolher","cam")].filter(Boolean);
    if (!itens.length) return;
    plusM = el("div",{class:"pm", id:"plusMenu"}, el("div",{class:"pm-scrim", onclick:closePlus}), el("div",{class:"pm-box", role:"menu", "aria-label":"Criar demanda"}, ...itens));
    document.body.append(plusM); document.body.classList.add("pm-open");
    const b = document.querySelector(".tab-plus"); if (b){ b.setAttribute("aria-expanded", "true"); b.classList.add("open"); }
  }
  document.addEventListener("keydown", e => { if (e.key === "Escape") closePlus(); });
  function buildNav(){""")
rep(r"""    tb.style.gridTemplateColumns = "repeat(" + list.length + ", minmax(0, 1fr))";""", r"""    const pl = el("button",{type:"button", class:"tab-plus", "data-act":"plus", "aria-label":"Criar demanda", "aria-haspopup":"menu", "aria-expanded":"false", onclick:togglePlus}, el("span",{class:"tp-i"}, icon("plus")));
    pl.hidden = !canWrite; tb.insertBefore(pl, tb.children[2] || null);
    tb.style.gridTemplateColumns = "none";""")
rep(r"""    $$('[data-act="new"]').forEach(b => b.hidden = !canWrite);""", r"""    $$('[data-act="new"]').forEach(b => b.hidden = !canWrite);
    $$('[data-act="plus"]').forEach(b => b.hidden = !canWrite); if (!canWrite) closePlus();""")


# 13) funcionário: o nome escolhido NÃO esconde mais a equipe. Todas as telas mostram tudo; a aba "Minhas" mostra só as escalas dele.
rep(r"""      if (meNome && pessoa !== meNome && EQUIPES[staffFr].includes(meNome) && !(PERFIS[staffFr] || []).length){ pessoa = meNome; fillPessoa(); }
""", "")
rep(r"""      if (role === "staff"){ if (pessoa){ savePrefs(); setMe(pessoa); return; } meNome = ""; saveMe(); notified = null; }
""", "")
rep(r"""    if (meNome && role === "staff" && !(PERFIS[staffFr] || []).length){ renderMinhas(v); return; }
""", "")
rep(r"""    box.hidden = view !== "today" || (role === "staff" && !!meNome) || (role === "staff" && !frOk());""", r"""    box.hidden = view !== "today" || (role === "staff" && !frOk());""")
rep(r"""$("#shotBtn").hidden = view !== "today" || (role === "staff" && !!meNome);""", r"""$("#shotBtn").hidden = view !== "today";""")
rep(r"""      if (typeof p.pessoa === "string" && EQUIPE.includes(p.pessoa)) pessoa = p.pessoa;
""", "")
rep(r"""  const VIEWS_STAFF = VIEWS;""", r"""  const VIEWS_STAFF = VIEWS.concat([["minhas","Minhas"]]);""")
rep(r"""  const ALL_VIEWS = VIEWS.concat(ADMIN_VIEWS);""", r"""  const ALL_VIEWS = VIEWS.concat(ADMIN_VIEWS, [["minhas","Minhas"]]);""")
rep(r"""    if (role === "staff" && view === "mais") view = "today";""", r"""    if (role === "staff" && view === "mais") view = "today";
    if (role !== "staff" && view === "minhas") view = "today";""")
rep(r"""minhas:renderMinhas, escala:renderEscala""", r"""minhas:renderMinhasPage, escala:renderEscala""")
rep(r"""  function renderMinhas(v){""", r"""  function renderMinhasPage(){ const v = $("#view"); v.replaceChildren(); const who = (pessoa && TODOS.includes(pessoa)) ? pessoa : meNome; if (!who){ v.append(chooser()); return; } renderMinhas(v, who); }
  function renderMinhas(v){""")
rep(r"""onclick:() => { meNome = ""; saveMe(); notified = null; render(); }}, "Ver todas as demandas")""", r"""onclick:() => setView("today")}, "Ver as demandas de toda a equipe")""")
rep(r'''minhas:"Minhas demandas"''', r'''minhas:"Minhas escalas"''')
rep(r"""icon(k), l, k === "today" ? bd() : null));""", r"""icon(k), l, k === "minhas" ? bd() : null));""")
rep(r"""el("span",{class:"tbi"}, icon(k), k === "today" ? bd() : null), l));""", r"""el("span",{class:"tbi"}, icon(k), k === "minhas" ? bd() : null), l));""")
rep(r'''"Escolha seu nome pra ver as demandas em que você foi escalado. Isso fica salvo só pra você."''', r'''"Escolha seu nome pra ver as suas escalas na aba Minhas e receber o aviso quando te escalarem. As demandas de toda a equipe continuam à vista."''')
# mês: alternar entre todas as escalas e só as minhas
rep(r"""  function renderMonth(){""", r"""  let mesMinhas = false;
  function renderMonth(){""")
rep(r"""    v.append(el("button",{type:"button", class:"shotb", onclick:() => openShot("mes")}, el("span",{class:"sq"}, icon("baixar")), el("span",{class:"tx"}, "Baixar cronograma do mês")));""", r"""    if (mesMinhas && !meNome) mesMinhas = false;
    if (role === "staff") v.append(el("div",{class:"mm-seg", role:"group", "aria-label":"Quais escalas mostrar"},
      el("button",{type:"button", "aria-pressed":String(!mesMinhas), onclick:() => { mesMinhas = false; renderMonth(); }}, "Todas as escalas"),
      el("button",{type:"button", "aria-pressed":String(mesMinhas), onclick:() => { if (!meNome){ setView("minhas"); return; } mesMinhas = true; renderMonth(); }}, icon("minhas"), "Minhas escalas")));
    v.append(el("button",{type:"button", class:"shotb", onclick:() => openShot("mes")}, el("span",{class:"sq"}, icon("baixar")), el("span",{class:"tx"}, "Baixar cronograma do mês")));""")
rep(r"""const vis = items.filter(i => i.prazo && i.prazo.startsWith(calMonth) && inFr(i) && match(i)).sort(order);""", r"""const vis = items.filter(i => i.prazo && i.prazo.startsWith(calMonth) && inFr(i) && match(i) && (!mesMinhas || role !== "staff" || (meNome && team(i).includes(meNome)))).sort(order);""")


# 14) os escudos da FAF/BM são marcados por atributo próprio (data-logo): o app copia pra áreas extras (LIFE) toda regra que cita ".asc"
rep(r"""el("span",{class:"tag "+it.frente}, LBL[it.frente])""", r"""el("span",{class:"tag "+it.frente, "data-logo":({fed:"faf", asc:"bm"})[it.frente] || false}, LBL[it.frente])""")
rep(r"""el("span",{class:"tag " + r.area}, LBL[r.area])""", r"""el("span",{class:"tag " + r.area, "data-logo":({fed:"faf", asc:"bm"})[r.area] || false}, LBL[r.area])""")
rep(r"""mf.append(el("button",{"data-fr":k, onclick:()=>setShow(k)}, l));""", r"""mf.append(el("button",{"data-fr":k, "data-logo":({fed:"faf", asc:"bm"})[k] || false, onclick:()=>setShow(k)}, l));""")


# 15) identidade permanente ("Quem é você?" só uma vez), Minhas com a pessoa escolhida, arquivo, etapas com o fluxo no card
rep(r"""      if (pd && TODOS.includes(pd.nome)){ meNome = pd.nome; vistos = new Set(Array.isArray(pd.vistos) ? pd.vistos : []); render(); }
      else if (meNome) saveMe();""", r"""      if (pd && Array.isArray(pd.vistos) && pd.vistos.length){ pd.vistos.forEach(x => vistos.add(x)); render(); }
      if (meNome) saveMe();""")
rep(r"""  function saveMe(){
""", r"""  function saveMe(){
    if (meNome && window.DEMANDO_API) window.DEMANDO_API.guardarNomeEquipe(meNome);
""")
cut("  function hello(open){", "  function nomesDoUsuario(){", r"""  function hello(open, who){
    who = who || meNome; const eu = who === meNome;
    const n = eu ? unseenList().length : 0, stats = [];
    if (eu) stats.push(el("div",{class:"hs" + (n ? " hot" : "")}, el("b",null,n), el("span",null,"Novas escalas")));
    stats.push(el("div",{class:"hs"}, el("b",null, open.filter(i => i.prazo === todayStr()).length), el("span",null,"Para hoje")), el("div",{class:"hs"}, el("b",null, open.filter(isLate).length), el("span",null,"Atrasadas")));
    const acoes = eu ? [
      ("Notification" in window && Notification.permission === "default") ? el("button",{type:"button", class:"btn", onclick:e => { const s = document.getElementById("sino"); if (s) s.click(); e.currentTarget.remove(); }}, icon("bell"), "Ativar alertas") : null,
      el("button",{type:"button", class:"lnk-b", onclick:() => setView("today")}, "Ver as demandas de toda a equipe"),
      el("button",{type:"button", class:"lnk-b", onclick:() => { meNome = ""; saveMe(); notified = null; if (window.DEMANDO_API) window.DEMANDO_API.limparNomeEquipe(); render(); }}, "Não sou eu")
    ] : [el("button",{type:"button", class:"lnk-b", onclick:() => { pessoa = ""; fillPessoa(); savePrefs(); render(); }}, "Voltar às minhas escalas")];
    return el("section",{class:"hello"},
      el("div",{class:"hello-t"}, el("span",{class:"hello-av av " + avColor(who)}, ini(who)),
        el("div",null, el("b",null, eu ? "Olá, " + who : "Escalas de " + who), el("span",null, open.length ? plural(open.length, eu ? "demanda em aberto com você" : "demanda em aberto", eu ? "demandas em aberto com você" : "demandas em aberto") : (eu ? "Nada em aberto com você agora" : "Nada em aberto agora")))),
      el("div",{class:"hello-s"}, ...stats),
      el("div",{class:"hello-a"}, ...acoes));
  }
""")
rep(r"""  function renderMinhas(v){""", r"""  function renderMinhas(v, who){ who = who || meNome; const eu = who === meNome;""")
rep(r"""    const mine = mineOf(meNome).filter(match).sort(order), open = mine.filter(isOpen);
    v.append(hello(open));
    const novas = open.filter(naoVisto), rest = open.filter(i => !naoVisto(i));""", r"""    const mine = mineOf(who).filter(match).sort(order), open = mine.filter(isOpen);
    v.append(hello(open, who));
    const novas = eu ? open.filter(naoVisto) : [], rest = eu ? open.filter(i => !naoVisto(i)) : open;""")
# arquivo: botão na ficha, e as arquivadas saem das listas do dia a dia (continuam no Mês e nos relatórios)
rep(r"""    $("#detDel").hidden = !adm;""", r"""    $("#detDel").hidden = !adm;
    const _arq = !!(window.DEMANDO_API && window.DEMANDO_API.arquivar); $("#detArq").hidden = !(adm && _arq && (it.arquivadaEm || !isOpen(it))); $("#detArq").textContent = it.arquivadaEm ? "Desarquivar" : "Arquivar";""")
rep(r"""  $("#detDel").addEventListener("click", () => {""", r"""  $("#detArq").addEventListener("click", async () => {
    const it = detItem; if (!it || !window.DEMANDO_API) return;
    const voltar = !!it.arquivadaEm;
    det.close();
    if (await window.DEMANDO_API.arquivar(it.id, !voltar)) toast(voltar ? "Demanda desarquivada" : "Demanda arquivada", () => window.DEMANDO_API.arquivar(it.id, voltar));
    else toast(voltar ? "Não deu pra desarquivar agora." : "Não deu pra arquivar agora.");
  });
  $("#detDel").addEventListener("click", () => {""")
rep(r"""        let list = mine.filter(i => i.status === s).sort(order);
        if (s === "Entregue") list = list.sort((a,b) => (b.entregue||"").localeCompare(a.entregue||"")).slice(0,40);""", r"""        let list = mine.filter(i => i.status === s && !i.arquivadaEm).sort(order);
        if (s === "Entregue" || s === "Postada") list = list.sort((a,b) => (b.entregue||"").localeCompare(a.entregue||"")).slice(0,40);""")
rep(r"""el("span",{class:"n"}, mine.filter(i=>i.status===s).length)""", r"""el("span",{class:"n"}, mine.filter(i=>i.status===s && !i.arquivadaEm).length)""")
rep(r"""const feitas = mine.filter(i => !isOpen(i) && (i.entregue || "") >= addDays(t,-7));""", r"""const feitas = mine.filter(i => !isOpen(i) && !i.arquivadaEm && (i.entregue || "") >= addDays(t,-7));""")
# etapas: A fazer, Em produção, Ajustes, Entregue, Postada
rep(r"""  const STATUS = ["A fazer","Em produção","Entregue"];""", r"""  const STATUS = ["A fazer","Em produção","Ajustes","Entregue","Postada"];""")
rep(r"""  const isOpen = it => it.status !== "Entregue";""", r"""  const isOpen = it => it.status !== "Entregue" && it.status !== "Postada";""")
rep(r"""mine.filter(i => i.status === "Entregue" && (i.entregue||"") >= weekAgo).length""", r"""mine.filter(i => !isOpen(i) && (i.entregue||"") >= weekAgo).length""")
rep(r"""const stKey = st => ({"A fazer":"s0","Em produção":"s1","Entregue":"s3"})[st] || "s0";""", r"""const stKey = st => ({"A fazer":"s0","Em produção":"s1","Ajustes":"s2","Entregue":"s3","Postada":"s4"})[st] || "s0";""")
rep(r"""it.status === "Entregue" ? icon("check") : el("i",{class:"ring"}), it.status)""", r"""!isOpen(it) ? icon("check") : el("i",{class:"ring"}), it.status)""")
rep(r"""    const si = STATUS.indexOf(it.status), next = STATUS[si+1];
    const hasSt = !!(canWrite && isOpen(it) && next && next !== "Entregue");""", r"""    const next = it.status === "A fazer" ? "Em produção" : null;
    const hasSt = !!(canWrite && next);""")
rep(r"""if (s === "Entregue") n.entregue = it.status === "Entregue" && it.entregue ? it.entregue : todayStr(); else delete n.entregue;""", r"""if (s === "Entregue" || s === "Postada") n.entregue = it.entregue || todayStr(); else delete n.entregue;""")
rep(r"""n.historico = hist(it, s === "Entregue" ? "Marcada como entregue" : "Movida para " + s);
    if (await write(n)) toast(s === "Entregue" ? "Entregue! Boa." : "Movida para " + s, () => write(prev));""", r"""n.historico = hist(it, s === "Entregue" ? "Marcada como entregue" : s === "Postada" ? "Marcada como postada" : "Movida para " + s);
    if (await write(n)) toast(s === "Entregue" ? "Entregue! Boa." : s === "Postada" ? "Postada! Missão cumprida." : "Movida para " + s, () => write(prev));""")
rep(r"""...(r.status === "Entregue" ? {entregue: t} : {})""", r"""...(r.status === "Entregue" || r.status === "Postada" ? {entregue: t} : {})""")
rep(r"""if (off) sp("✓ ENTREGUE", "#E3E7E4", SH.muted);""", r"""if (off) sp(it.status === "Postada" ? "✓ POSTADA" : "✓ ENTREGUE", "#E3E7E4", SH.muted);""")
rep(r"""el("i",{class:"stp-d"}), s))));""", r"""el("i",{class:"stp-d"}), s === "Em produção" ? "Produção" : s))));""")
# o fluxo da demanda aparece direto no card (a etapa atual destacada)
rep(r"""  function row(it, opts){""", r"""  const fluxoEl = it => { const cur = STATUS.indexOf(it.status); return el("span",{class:"flow", role:"img", "aria-label":"Etapa: " + it.status + " (" + (cur + 1) + " de " + STATUS.length + ")"}, ...STATUS.map((s, i) => el("span",{class:"fs " + stKey(s) + (i < cur ? " past" : i === cur ? " cur" : "")}, el("i"), el("b", null, s === "Em produção" ? "Produção" : s)))); };
  function row(it, opts){""")
rep(r"""el("span",{class:"tt"}, it.titulo),""", r"""el("span",{class:"tt"}, it.titulo),
        fluxoEl(it),""")
# Secretaria de Esporte
rep(r"""["Gabinete Civil","Mariana Feijó"]
  ];""", r"""["Gabinete Civil","Mariana Feijó"],["Esporte","Secretário de Esporte"]
  ];""")
# logos da FAF e da BM no resumo do Início
rep(r"""el("div",{class:"ph"}, el("b",null,LBL[f]), el("span",null,SUB[f]))""", r"""el("div",{class:"ph"}, el("b",{"data-logo":({fed:"faf", asc:"bm"})[f] || false}, LBL[f]), el("span",null,SUB[f]))""")
# rodapé fixo: no celular só o miolo rola; quem sobe ao topo agora é o .app
rep(r"""window.scrollTo({top:0})""", r"""scrollTopApp()""", 3)
rep(r"""  function setView(v){""", r"""  function scrollTopApp(){ const a = document.querySelector(".app"); if (a && a.scrollTo) a.scrollTo({top:0}); window.scrollTo({top:0}); }
  function setView(v){""")

# 5) monta a página
css_extra = "\n.sem-voltar #backTop,.sem-voltar #backD{display:none!important}\n@media (max-width:860px){.mtop .back-top{grid-column:1;grid-row:1}.mtop .brand{grid-column:2;grid-row:1}.mtop .mpage{grid-column:3;grid-row:1}}\n"

css_extra += """
@media (max-width:860px){
.tabbar{grid-template-columns:none!important;grid-auto-flow:column;grid-auto-columns:minmax(0,1fr)}
.fab{display:none!important}
.tabbar .tab-plus{padding:0;justify-content:center;align-items:center}
.tab-plus .tp-i{width:56px;height:42px;border-radius:16px;display:grid;place-items:center;background:linear-gradient(135deg,var(--ink),color-mix(in srgb,var(--ink) 78%,var(--fed)));color:var(--surface);box-shadow:0 8px 20px -8px color-mix(in srgb,var(--ink) 70%,transparent);transition:transform .22s cubic-bezier(.3,1.4,.4,1)}
.tabbar .tab-plus svg{width:24px;height:24px;transition:transform .25s cubic-bezier(.3,1.4,.4,1)}
.tabbar .tab-plus:active .tp-i{transform:scale(.94)}
.tabbar .tab-plus.open svg{transform:rotate(45deg)}
.pm{position:fixed;inset:0;z-index:55}
body.pm-open .tabbar{z-index:60}
.pm-scrim{position:absolute;inset:0;background:rgba(10,14,12,.36);backdrop-filter:blur(3px);-webkit-backdrop-filter:blur(3px);animation:pmFade .16s ease-out}
.pm-box{position:absolute;left:50%;transform:translateX(-50%);bottom:calc(env(safe-area-inset-bottom,0px) + 84px);width:min(88vw,340px);background:var(--surface);border-radius:24px;padding:8px;box-shadow:0 24px 60px -12px rgba(0,0,0,.5);display:grid;gap:2px;animation:pmIn .18s cubic-bezier(.3,1.2,.4,1)}
.pm-i{display:flex;align-items:center;gap:14px;border:0;background:none;color:var(--ink);text-align:left;padding:11px 12px;border-radius:17px;width:100%;cursor:pointer}
.pm-i:active{background:color-mix(in srgb,var(--ink) 8%,transparent)}
.pm-ic{width:44px;height:44px;border-radius:15px;display:grid;place-items:center;flex:none;background:color-mix(in srgb,var(--ink) 8%,transparent)}
.pm-ic svg{width:22px;height:22px}
.pm-t{display:grid;gap:1px}.pm-t b{font-size:16px;font-weight:700}.pm-t small{color:var(--muted);font-size:13px}
@keyframes pmIn{from{transform:translateX(-50%) translateY(14px) scale(.97)}}
@keyframes pmFade{from{opacity:.55}}
}
"""
css_extra += """
#mFr button{position:relative}
#mFr button + button::after{content:"";position:absolute;left:-3px;top:24%;bottom:24%;width:1.5px;border-radius:2px;background:color-mix(in srgb,var(--ink) 24%,transparent);transition:opacity .2s}
#mFr button[aria-pressed="true"]::after,#mFr button[aria-pressed="true"] + button::after{opacity:0}
#mFr button[data-logo="faf"]::before{width:22px;height:18px;border-radius:0;background:url(assets/faf-emblem.png) center/contain no-repeat}
#mFr button[data-logo="bm"]::before{width:15px;height:19px;border-radius:0;background:url(assets/bm-emblem.png) center/contain no-repeat}
#mFr button[aria-pressed="true"][data-logo="faf"]::before{background:url(assets/faf-emblem.png) center/contain no-repeat;box-shadow:none}
#mFr button[aria-pressed="true"][data-logo="bm"]::before{background:url(assets/bm-emblem.png) center/contain no-repeat;box-shadow:none}
.mm-seg{display:flex;gap:4px;padding:4px;margin:0 0 12px;background:var(--surface);border-radius:16px;box-shadow:var(--shadow),var(--ring)}
.mm-seg button{position:relative;flex:1;border:0;background:none;border-radius:12px;padding:10px 6px;font-weight:600;font-size:14px;color:var(--muted);display:flex;align-items:center;justify-content:center;gap:7px;cursor:pointer;transition:background .2s,color .2s}
.mm-seg button svg{width:17px;height:17px}
.mm-seg button[aria-pressed="true"]{background:var(--ink);color:var(--surface);box-shadow:0 6px 14px -6px rgba(0,0,0,.35)}
.mm-seg button + button::after{content:"";position:absolute;left:-3px;top:24%;bottom:24%;width:1.5px;border-radius:2px;background:color-mix(in srgb,var(--ink) 24%,transparent);transition:opacity .2s}
.mm-seg button[aria-pressed="true"]::after,.mm-seg button[aria-pressed="true"] + button::after{opacity:0}
"""
css_extra += """
:root{--s4:#0891B2}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--s4:#38BDF8}}
:root[data-theme="dark"]{--s4:#38BDF8}
.sc.s4{--sc:var(--s4)} .col.s4{--c:var(--s4)} .stp.s4{--sc:var(--s4)}
.stepper{grid-template-columns:repeat(5,minmax(0,1fr))}
.stp{font-size:11px;padding:10px 0 9px}
.cols{grid-auto-columns:minmax(232px,1fr)}
.flow{display:flex;width:100%;margin-top:9px}
.flow .fs{--c:var(--s0);flex:1;min-width:0;display:flex;flex-direction:column;align-items:center;gap:5px;position:relative;font-size:10px;font-weight:600;color:var(--faint);line-height:1}
.flow .fs.s1{--c:var(--s1)} .flow .fs.s2{--c:var(--s2)} .flow .fs.s3{--c:var(--s3)} .flow .fs.s4{--c:var(--s4)}
.flow .fs i{width:9px;height:9px;border-radius:50%;background:color-mix(in srgb,var(--ink) 18%,transparent);position:relative;z-index:1}
.flow .fs::before{content:"";position:absolute;top:4px;left:-50%;right:50%;height:2px;background:color-mix(in srgb,var(--ink) 13%,transparent)}
.flow .fs:first-child::before{display:none}
.flow .fs.past i,.flow .fs.cur i{background:var(--c)}
.flow .fs.past::before,.flow .fs.cur::before{background:var(--c)}
.flow .fs.cur i{box-shadow:0 0 0 3px color-mix(in srgb,var(--c) 26%,transparent)}
.flow .fs.cur b{color:var(--c);font-weight:800}
.flow .fs.past b{color:var(--muted)}
.pane .ph b[data-logo="faf"]::before{content:"";display:inline-block;width:27px;height:21px;margin-right:9px;vertical-align:-4px;background:url(assets/faf-emblem.png) center/contain no-repeat}
.pane .ph b[data-logo="bm"]::before{content:"";display:inline-block;width:19px;height:24px;margin-right:9px;vertical-align:-5px;background:url(assets/bm-emblem.png) center/contain no-repeat}
@media (max-width:860px){
html,body{height:100%;overflow:hidden;overscroll-behavior:none}
.app{height:100%;height:100dvh;overflow-y:auto;overflow-x:hidden;-webkit-overflow-scrolling:touch;overscroll-behavior-y:contain}
}
"""
css_extra += """
.ax-w{position:relative;border-radius:12px;overflow:hidden}.ax-w.wide{grid-column:1 / -1}.ax-w.wide .ax-chip{padding-right:56px}
.ax-dl{position:absolute;right:8px;top:8px;width:36px;height:36px;border-radius:50%;border:0;display:grid;place-items:center;padding:0;cursor:pointer;background:color-mix(in srgb,var(--surface) 92%,transparent);color:var(--ink);box-shadow:var(--ring)}
.ax-w.wide .ax-dl{top:50%;transform:translateY(-50%)}.ax-dl svg{width:17px;height:17px}
.sair-box{display:flex;justify-content:center;padding:28px 0 12px}
.sair-b{display:inline-flex;align-items:center;gap:8px;border:0;cursor:pointer;background:var(--surface);color:var(--muted);font-weight:700;font-size:14.5px;padding:12px 22px;border-radius:14px;box-shadow:var(--ring)}.sair-b svg{width:18px;height:18px}
.tag[data-logo="bm"]{background-image:url(assets/bm-emblem.png);background-repeat:no-repeat;background-position:6px 50%;background-size:auto 14px;padding-left:25px}
.abn.logo{padding:14px 18px}
.abn.logo-bm{background:linear-gradient(135deg,#0B5E3B,#0E7A4D 70%,#12935C);box-shadow:0 10px 28px -14px rgba(14,122,77,.7)}
.abn.logo-faf{background:linear-gradient(135deg,#2346C9,#2F5BEA 70%,#4F78F0);box-shadow:0 10px 28px -14px rgba(47,91,234,.7);gap:14px}
.abn-emb{height:56px;width:auto;display:block;flex:none;margin:0 auto}
.abn-fn{color:#fff;font:700 18px/1.15 var(--display);letter-spacing:-.01em;text-align:left}
.tag[data-logo="faf"]{background-image:url(assets/faf-emblem.png);background-repeat:no-repeat;background-position:6px 50%;background-size:auto 14px;padding-left:29px}
.abn-logo{height:46px;width:auto;max-width:100%;display:block}
.abn-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.abn{position:relative}
"""
h2 = h.replace(m.group(0), '<script type="text/plain" id="appcode">\n' + app + '</script>\n</body>')
h2 = h2.replace("</style>", css_extra + "</style>", 1)
_dup = '      <span class="sp"></span>\n      <button type="button" class="btn" id="detDup" hidden>Duplicar</button>'
assert h2.count(_dup) == 1, "botão Duplicar não encontrado no HTML"
h2 = h2.replace(_dup, '      <span class="sp"></span>\n      <button type="button" class="btn" id="detArq" hidden>Arquivar</button>\n      <button type="button" class="btn" id="detDup" hidden>Duplicar</button>')
libs = '<script src="https://cdn.jsdelivr.net/npm/@supabase/supabase-js@2.117.3/dist/umd/supabase.js"></script>\n<script src="config.js"></script>\n<script src="adapter.js"></script>\n'
h2 = h2.replace('<script type="text/plain" id="appcode">', libs + '<script type="text/plain" id="appcode">', 1)
pwa_head = '<link rel="manifest" href="manifest.webmanifest">\n<link rel="icon" href="icons/icon-192.png">\n<link rel="apple-touch-icon" href="icons/apple-touch-icon.png">\n<meta name="mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-capable" content="yes">\n<meta name="apple-mobile-web-app-title" content="Demandô">\n<meta name="apple-mobile-web-app-status-bar-style" content="default">\n'
assert "<title>Demandô</title>" in h2; h2 = h2.replace("<title>Demandô</title>", "<title>Demandô</title>\n" + pwa_head, 1)
h2 = h2.replace("</body>", '<script>if ("serviceWorker" in navigator) navigator.serviceWorker.register("sw.js").catch(function(){});</script>\n</body>')
os.makedirs(out, exist_ok=True)
open(os.path.join(out, "index.html"), "w", encoding="utf-8").write(h2)
for f in ("adapter.js", "config.js"): shutil.copy(os.path.join(aqui, f), os.path.join(out, f))
for f in ("manifest.webmanifest", "sw.js"): shutil.copy(os.path.join(aqui, "pwa", f), os.path.join(out, f))
for d in ("icons", "vendor", "assets"):
    shutil.rmtree(os.path.join(out, d), ignore_errors=True); shutil.copytree(os.path.join(aqui, "pwa", d), os.path.join(out, d))
print("gerado:", os.path.join(out, "index.html"), len(h2), "bytes")
