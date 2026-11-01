"""Funcionário vê a equipe toda; aba Minhas; botão Minhas escalas no Mês; barrinha do admin com logos e divisórias; LIFE sem escudo da BM. App local em http://localhost:8766.
Uso: SB=<token> ADMIN_SENHA=<..> BM_SENHA=<..> python3 tests/funcionario_test.py   (devolve o nome e as preferências da conta bm ao que eram)"""
import asyncio, os, requests
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; MG={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda q: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=MG, json={"query":q}).json()
from playwright.async_api import async_playwright
URL=os.environ.get("APP","http://localhost:8766/index.html"); res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:140] if d else ""))
STUB="if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};}"
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar, #sideViews", state="attached", timeout=30000); await pg.wait_for_timeout(2800)
LINHAS="""(nome) => { const rows=[...document.querySelectorAll('#view .rw')]; const com=rows.filter(r=>((r.querySelector('.avs')||{}).innerText||'').includes(nome)).length; return {total:rows.length, comEle:com, semEle:rows.length-com} }"""
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); dev=p.devices['iPhone 13']; errs=[]
    antes=sql("select nome_equipe from public.pessoas where usuario='bm'")[0]['nome_equipe']; sql("update public.pessoas set nome_equipe=null where usuario='bm'")
    pref=sql("select dados::text d from public.preferencias where pessoa_id=(select id from public.pessoas where usuario='bm')"); pref=pref[0]['d'] if pref else None; sql("delete from public.preferencias where pessoa_id=(select id from public.pessoas where usuario='bm')")
    try:
      print("######## FUNCIONÁRIO DA BM · aparelho que tinha o filtro 'Juninho' gravado")
      ctx=await b.new_context(**dev); await ctx.add_init_script(STUB+"localStorage.setItem('cd-prefs', JSON.stringify({view:'today', show:'asc', pessoa:'Juninho'}));"); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
      await entra(pg,"bm",os.environ["BM_SENHA"])
      chk("o filtro 'Juninho' gravado no aparelho NÃO volta (começa em 'Toda a equipe')", await pg.evaluate("document.querySelector('#pessoa').value===''"))
      chk("sem nome escolhido, o cartão 'Quem é você?' aparece e a lista é a da equipe toda", await pg.locator("#meHold .who-pick").count()==1 and (await pg.evaluate(LINHAS,"Juninho"))['semEle']>0)
      await pg.click(".who-b:has-text('Juninho')"); await pg.wait_for_timeout(1500)
      L=await pg.evaluate(LINHAS,"Juninho"); print("   Início depois de escolher 'Juninho':", L)
      chk("escolhi 'Juninho' e o Início CONTINUA com a equipe toda (tem demandas de outras pessoas)", L['semEle']>0 and L['comEle']>0, L)
      chk("o filtro da equipe segue em 'Toda a equipe' (não foi forçado pro meu nome)", await pg.evaluate("document.querySelector('#pessoa').value===''"))
      chk("o resumo da área (cards com números) continua aparecendo", await pg.evaluate("!document.querySelector('#sum').hidden && document.querySelector('#sum').children.length>0"))
      await pg.screenshot(path="func_inicio.png")
      chk("Quadro mostra a equipe toda", (await pg.evaluate("(async()=>{document.querySelector('#tabbar [data-view=board]').click(); await new Promise(r=>setTimeout(r,900)); const t=[...document.querySelectorAll('#view .card')].map(c=>(c.querySelector('.avs')||{}).innerText||''); return {total:t.length, semJuninho:t.filter(x=>!x.includes('Juninho')).length}})()"))['semJuninho']>0)
      print("== aba MINHAS")
      await pg.click("#tabbar [data-view=minhas]"); await pg.wait_for_timeout(1200); M=await pg.evaluate(LINHAS,"Juninho")
      chk("'Minhas' mostra só as escalas do Juninho (nenhuma de outra pessoa)", M['total']>0 and M['semEle']==0, M)
      chk("com o 'Olá, Juninho' e os números dele", "Olá, Juninho" in await pg.inner_text("#view")); await pg.screenshot(path="func_minhas.png")
      await pg.click("#view .hello-a .lnk-b"); await pg.wait_for_timeout(1000)
      chk("'Ver as demandas de toda a equipe' volta pro Início, sem perder quem eu sou", await pg.evaluate("document.querySelector('#tabbar [aria-current=true]').dataset.view")=="today" and (await pg.evaluate(LINHAS,"Juninho"))['semEle']>0)
      print("== MÊS")
      await pg.click("#tabbar [data-view=month]"); await pg.wait_for_timeout(1200)
      T=await pg.evaluate("(()=>{const bs=[...document.querySelectorAll('#view .mm-seg button')]; return {botoes: bs.map(x=>x.textContent.trim()), pressed: bs.map(x=>x.getAttribute('aria-pressed')), eventos: document.querySelectorAll('#view .cell .ev:not(.more)').length}})()")
      chk("no Mês existe 'Todas as escalas | Minhas escalas', começando em 'Todas'", T['botoes']==['Todas as escalas','Minhas escalas'] and T['pressed']==['true','false'], T)
      await pg.screenshot(path="func_mes_todas.png")
      await pg.click("#view .mm-seg button:nth-child(2)"); await pg.wait_for_timeout(900)
      T2=await pg.evaluate("({pressed:[...document.querySelectorAll('#view .mm-seg button')].map(x=>x.getAttribute('aria-pressed')), eventos: document.querySelectorAll('#view .cell .ev:not(.more)').length})")
      chk("tocando em 'Minhas escalas' o calendário mostra bem menos (só as do Juninho)", T2['pressed']==['false','true'] and 0<T2['eventos']<T['eventos'], {"todas":T['eventos'],"minhas":T2['eventos']}); await pg.screenshot(path="func_mes_minhas.png")
      await pg.click("#view .cell:not(.out) >> nth=0") if False else None
      dias=await pg.evaluate("(()=>{const cs=[...document.querySelectorAll('#view .cell')].filter(c=>c.querySelector('.ev')); return cs.length})()")
      chk("o filtro do Mês não mexeu na equipe do cabeçalho", await pg.evaluate("document.querySelector('#pessoa').value===''"))
      await pg.click("#view .mm-seg button:nth-child(1)"); await pg.wait_for_timeout(700); chk("voltar pra 'Todas as escalas' traz tudo de volta", (await pg.evaluate("document.querySelectorAll('#view .cell .ev:not(.more)').length"))==T['eventos'])
      await ctx.close()
      print("\n######## ADMIN · barrinha Todas / FAF / BM / LIFE")
      for tema in ("light","dark"):
        ctx=await b.new_context(**dev, color_scheme=tema); await ctx.add_init_script(STUB); pg=await ctx.new_page(); await entra(pg,"admin",os.environ["ADMIN_SENHA"])
        info=await pg.evaluate("""(()=>{const bs=[...document.querySelectorAll('#mFr button')]; return bs.map(b=>({k:b.dataset.fr, emb:getComputedStyle(b,'::before').backgroundImage.replace(/url\\(.*\\/(assets\\/[^"')]+)["']?\\)/,'$1'), div:getComputedStyle(b,'::after').content, op:getComputedStyle(b,'::after').opacity, ativo:b.getAttribute('aria-pressed')}))})()""")
        by={x['k']:x for x in info}
        chk(f"[{tema}] FAF com o escudo da FAF, BM com o da BM, e LIFE e Todas SEM escudo (só a bolinha)", 'faf-emblem' in by['fed']['emb'] and 'bm-emblem' in by['asc']['emb'] and 'emblem' not in by['all']['emb'] and 'emblem' not in by['aqutz8ei']['emb'], {k:v['emb'][:30] for k,v in by.items()})
        chk(f"[{tema}] divisórias entre os botões (some só a que encosta no ativo)", by['fed']['div']!='none' and by['asc']['op']=='1' and by['fed']['op']=='0', {k:(v['div'][:4],v['op']) for k,v in by.items()})
        tg=await pg.evaluate("""(()=>{ const mk=(cls,logo)=>{ const t=document.createElement('span'); t.className='tag '+cls; if(logo) t.setAttribute('data-logo',logo); document.querySelector('#view').append(t); const bg=getComputedStyle(t).backgroundImage; t.remove(); return bg.replace(/url\\(.*\\/(assets\\/[^"')]+)["']?\\)/,'$1'); }; return {life: mk('aqutz8ei'), bmSemMarca: mk('asc'), bm: mk('asc','bm'), faf: mk('fed','faf')}; })()""")
        chk(f"[{tema}] etiqueta da LIFE sem escudo; BM e FAF (marcadas) com o escudo certo", tg['life']=='none' and tg['bmSemMarca']=='none' and 'bm-emblem' in tg['bm'] and 'faf-emblem' in tg['faf'], tg)
        await pg.click("#mFr button[data-fr=all]"); await pg.wait_for_timeout(700)
        await pg.screenshot(path=f"func_admin_{tema}.png")
        if tema=="light":
            await pg.click("#mFr button[data-fr=asc]"); await pg.wait_for_timeout(700); await pg.screenshot(path="func_admin_bm.png")
            chk("com BM ativo o escudo continua visível (sem bloco branco atrás)", await pg.evaluate("getComputedStyle(document.querySelector('#mFr button[data-fr=asc]'),'::before').backgroundColor")=="rgba(0, 0, 0, 0)")
            g=await pg.evaluate("[...document.querySelectorAll('#tabbar > *')].filter(e=>!e.hidden).map(e=>e.classList.contains('tab-plus')?'+':e.dataset.view)"); chk("admin segue com Início, Quadro, +, Mês, Mais (sem Minhas)", g==['today','board','+','month','mais'], g)
            await pg.click("#tabbar [data-view=month]"); await pg.wait_for_timeout(800); chk("admin não vê o botão 'Minhas escalas' no Mês", await pg.locator("#view .mm-seg").count()==0)
        await ctx.close()
    finally:
      sql("update public.pessoas set nome_equipe=" + ("'"+antes+"'" if antes else "null") + " where usuario='bm'"); sql("delete from public.preferencias where pessoa_id=(select id from public.pessoas where usuario='bm')")
      if pref: sql("insert into public.preferencias(pessoa_id, dados) select id, $j$"+pref+"$j$::jsonb from public.pessoas where usuario='bm'")
      print("conta bm devolvida ao que era (nome:", antes, "| preferências:", "restauradas" if pref else "vazias", ")")
      print("\nerros de JS:", errs); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
