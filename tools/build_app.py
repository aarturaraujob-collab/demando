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

# 5) monta a página
css_extra = "\n.sem-voltar #backTop,.sem-voltar #backD{display:none!important}\n@media (max-width:860px){.mtop .back-top{grid-column:1;grid-row:1}.mtop .brand{grid-column:2;grid-row:1}.mtop .mpage{grid-column:3;grid-row:1}}\n"

css_extra += """
.ax-w{position:relative;border-radius:12px;overflow:hidden}.ax-w.wide{grid-column:1 / -1}.ax-w.wide .ax-chip{padding-right:56px}
.ax-dl{position:absolute;right:8px;top:8px;width:36px;height:36px;border-radius:50%;border:0;display:grid;place-items:center;padding:0;cursor:pointer;background:color-mix(in srgb,var(--surface) 92%,transparent);color:var(--ink);box-shadow:var(--ring)}
.ax-w.wide .ax-dl{top:50%;transform:translateY(-50%)}.ax-dl svg{width:17px;height:17px}
.sair-box{display:flex;justify-content:center;padding:28px 0 12px}
.sair-b{display:inline-flex;align-items:center;gap:8px;border:0;cursor:pointer;background:var(--surface);color:var(--muted);font-weight:700;font-size:14.5px;padding:12px 22px;border-radius:14px;box-shadow:var(--ring)}.sair-b svg{width:18px;height:18px}
.tag.asc{background-image:url(assets/bm-emblem.png);background-repeat:no-repeat;background-position:6px 50%;background-size:auto 14px;padding-left:25px}
.abn.logo{padding:14px 18px}
.abn.logo-bm{background:linear-gradient(135deg,#0B5E3B,#0E7A4D 70%,#12935C);box-shadow:0 10px 28px -14px rgba(14,122,77,.7)}
.abn.logo-faf{background:linear-gradient(135deg,#2346C9,#2F5BEA 70%,#4F78F0);box-shadow:0 10px 28px -14px rgba(47,91,234,.7);gap:14px}
.abn-emb{height:56px;width:auto;display:block;flex:none;margin:0 auto}
.abn-fn{color:#fff;font:700 18px/1.15 var(--display);letter-spacing:-.01em;text-align:left}
.tag.fed{background-image:url(assets/faf-emblem.png);background-repeat:no-repeat;background-position:6px 50%;background-size:auto 14px;padding-left:29px}
.abn-logo{height:46px;width:auto;max-width:100%;display:block}
.abn-sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.abn{position:relative}
"""
h2 = h.replace(m.group(0), '<script type="text/plain" id="appcode">\n' + app + '</script>\n</body>')
h2 = h2.replace("</style>", css_extra + "</style>", 1)
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
