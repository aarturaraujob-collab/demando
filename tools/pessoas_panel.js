  /* ---------- Pessoas (só admin): liberar acessos, papéis e redefinir senha ---------- */
  let acessosTodos = [];
  async function panelPessoas(box){
    const API = window.DEMANDO_API, sbc = API.sb;
    box.append(el("p",{class:"hint", style:"margin-bottom:12px"},"Quem cria um perfil aparece aqui sem acesso. Escolha o papel e as áreas e salve."));
    const lista = el("div",{class:"list dml", id:"pessoasLista"}); box.append(lista);
    const [p, ac] = await Promise.all([sbc.from("pessoas").select("*").order("criado_em",{ascending:false}), sbc.from("acessos").select("*")]);
    if (p.error){ lista.append(el("p",{class:"hint"},"Não deu pra carregar agora.")); return; }
    acessosTodos = ac.data || [];
    p.data.forEach(pe => lista.append(cartaoPessoa(pe)));
  }
  function cartaoPessoa(pe){
    const API = window.DEMANDO_API, sbc = API.sb;
    const eu = pe.id === API.pessoa.id, tem = acessosTodos.filter(x => x.pessoa_id === pe.id).map(x => x.area_id);
    const pend = pe.papel !== "admin" && !tem.length;
    const st = {papel:pe.papel, ativo:pe.ativo, areas:new Set(tem)};
    const papel = el("select",{"data-papel":pe.usuario, disabled: eu ? "" : false}, ...[["admin","Admin"],["membro","Membro (cria e muda)"],["leitor","Leitor (só acompanha)"]].map(([v,t]) => el("option",{value:v}, t)));
    papel.value = pe.papel; papel.addEventListener("change", () => st.papel = papel.value);
    const ativo = el("input",{type:"checkbox", "data-ativo":pe.usuario, disabled: eu ? "" : false}); ativo.checked = pe.ativo; ativo.addEventListener("change", () => st.ativo = ativo.checked);
    const salvar = el("button",{type:"button", class:"btn pri", "data-salvar":pe.usuario}, "Salvar");
    salvar.addEventListener("click", async () => {
      salvar.disabled = true;
      const e1 = await sbc.from("pessoas").update({papel:st.papel, ativo:st.ativo}).eq("id", pe.id);
      const novas = [...st.areas].filter(a => !tem.includes(a)), tiradas = tem.filter(a => !st.areas.has(a));
      const e2 = novas.length ? await sbc.from("acessos").insert(novas.map(a => ({pessoa_id:pe.id, area_id:a}))) : {};
      const e3 = tiradas.length ? await sbc.from("acessos").delete().eq("pessoa_id", pe.id).in("area_id", tiradas) : {};
      salvar.disabled = false;
      if (e1.error || e2.error || e3.error) return toast("Não deu pra salvar.");
      toast("Salvo: " + String(pe.nome).split(" ")[0]); renderMais();
    });
    const nova = el("input",{type:"text", placeholder:"Nova senha (mín. 8)", autocomplete:"off", "data-senha":pe.usuario});
    const bsenha = el("button",{type:"button", class:"btn", "data-redefinir":pe.usuario}, "Redefinir senha");
    bsenha.addEventListener("click", async () => {
      if (nova.value.length < 8) return toast("A senha precisa ter pelo menos 8 caracteres.");
      bsenha.disabled = true;
      try {
        const tk = (await sbc.auth.getSession()).data.session.access_token;
        const r = await fetch(window.DEMANDO.url + "/functions/v1/redefinir-senha", {method:"POST", headers:{"Content-Type":"application/json", apikey:window.DEMANDO.anon, Authorization:"Bearer " + tk}, body:JSON.stringify({pessoa_id:pe.id, senha:nova.value})});
        const j = await r.json().catch(() => ({}));
        toast(r.ok ? "Senha de " + String(pe.nome).split(" ")[0] + " redefinida" : (j.erro || "Não deu pra trocar a senha.")); if (r.ok) nova.value = "";
      } catch(e){ toast("Sem conexão."); }
      bsenha.disabled = false;
    });
    return el("div",{class:"rw dm" + (pend ? " today" : ""), style:"flex-direction:column;align-items:stretch;gap:12px;cursor:default", "data-pessoa":pe.usuario},
      el("div",null, el("b",{style:"font-size:16px"}, pe.nome, pend ? el("span",{class:"novo", style:"margin-left:8px"}, "Aguardando") : null), el("div",{class:"hint"}, "@" + pe.usuario)),
      el("label",{class:"fl"}, "Papel", papel),
      el("div",null, el("p",{class:"sec-l"}, "Áreas"), el("div",{class:"pills", style:"gap:10px"}, ...areaIds().map(k => {
        const c = el("input",{type:"checkbox", "data-area":k, style:"width:22px;height:22px;min-height:0"}); c.checked = st.areas.has(k);
        c.addEventListener("change", () => c.checked ? st.areas.add(k) : st.areas.delete(k));
        return el("label",{style:"display:flex;align-items:center;gap:8px;font-weight:600"}, c, LBL[k]); }))),
      el("label",{style:"display:flex;align-items:center;gap:10px;font-weight:600"}, ativo, "Acesso ativo"),
      el("div",{style:"display:flex;gap:10px;flex-wrap:wrap"}, salvar),
      el("label",{class:"fl"}, "Redefinir senha", el("div",{style:"display:flex;gap:8px"}, nova, bsenha)));
  }

