"""Sair da conta, logo da BM e visualizador de anexos (PDF/foto) no iPhone e no Android simulados. App local em http://localhost:8766.
Uso: SB=<token> ADMIN_SENHA=<senha> CODIGO_EQUIPE=<código> python3 tests/anexos_test.py [so-webkit]"""
import asyncio, os, json, requests, sys
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; BASE=f"https://{REF}.supabase.co"; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
keys=requests.get(f"https://api.supabase.com/v1/projects/{REF}/api-keys?reveal=true", headers=M).json(); SERVICE=[k['api_key'] for k in keys if k['name']=='service_role'][0]; SV={"apikey":SERVICE,"Authorization":"Bearer "+SERVICE}
ADMIN=os.environ['ADMIN_SENHA']; CODIGO=os.environ['CODIGO_EQUIPE']; URL=os.environ.get("APP","http://localhost:8766/index.html")
STUB="Object.defineProperty(navigator,'canShare',{value:()=>true,configurable:true});Object.defineProperty(navigator,'share',{value:async d=>{window.__shared=(window.__shared||[]).concat([[d.files[0].name,d.files[0].size,d.files[0].type]])},configurable:true});if(!('PushManager' in window)){window.PushManager=function(){};PushManager.prototype.getSubscription=async function(){return null};}"
res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:130] if d else ""))
async def entra(pg,u,s):
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario",u); await pg.fill("#g-senha",s); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(3000)
async def abre(pg, titulo):
    await pg.click("#tabbar [data-view=board]"); await pg.wait_for_timeout(700); await pg.fill("input[type=search]", titulo); await pg.wait_for_timeout(800)
    await pg.click(f".card:has-text('{titulo}') .tt >> nth=0"); await pg.wait_for_selector("#detBody .ax-w", timeout=15000)
async def rodar(nome, eng, dev):
    print(f"\n######## {nome}"); b=await eng.launch(); ctx=await b.new_context(**dev); await ctx.add_init_script(STUB); pg=await ctx.new_page(); errs=[]; uid=None
    pg.on("pageerror", lambda e: errs.append(str(e))); pg.on("dialog", lambda d: asyncio.ensure_future(d.accept()))
    try:
        await entra(pg,"admin",ADMIN)
        print("== SAIR")
        await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.wait_for_timeout(600)
        r=await pg.evaluate("(()=>{const s=document.querySelector('.sair-b'), t=document.querySelector('#tabbar'); if(!s) return null; const a=s.getBoundingClientRect(), c=t.getBoundingClientRect(); return {visivel:a.width>0, acimaDaBarra: a.bottom <= c.top+2, bottom:Math.round(a.bottom), barraTop:Math.round(c.top)}})()")
        chk("fim do Início: botão 'Sair da conta' aparece, acima da barra de baixo", r and r['visivel'] and r['acimaDaBarra'], r)
        await pg.screenshot(path=f"anx_{nome[:3]}_sair.png")
        await pg.click("#tabbar [data-view=mais]"); await pg.wait_for_timeout(900); await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.wait_for_timeout(400)
        chk("fim do Mais: botão 'Sair da conta'", await pg.locator("#view .sair-b").count()==1)
        await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(700)
        print("== LOGO DA BM")
        await pg.click("#tabbar [data-view=today]"); await pg.click("#mFr button[data-fr=asc]"); await pg.wait_for_timeout(1200)
        r=await pg.evaluate("(()=>{const i=document.querySelector('#areaBanner.logo img.abn-logo'); const tg=document.querySelector('.rw .tag.asc'); return {banner: !!i && i.complete && i.naturalWidth>0, etiqueta: !!tg && getComputedStyle(tg).backgroundImage.includes('bm-emblem.png')}})()")
        chk("banner da BM mostra a logo da Prefeitura (imagem carregada)", r['banner'], r)
        chk("etiqueta 'BM' dos cards leva o escudo", r['etiqueta'])
        await pg.screenshot(path=f"anx_{nome[:3]}_bm.png")
        print("== ANEXO PDF")
        await pg.click("#tabbar [data-view=today]"); await abre(pg,"Avalia Boca da Mata")
        chk("na ficha: botão de baixar ao lado do arquivo", await pg.locator("#detBody .ax-w .ax-dl").count()>=1)
        await pg.screenshot(path=f"anx_{nome[:3]}_ficha.png")
        await pg.click("#detBody .ax-chip"); await pg.wait_for_selector("#axv", timeout=10000)
        await pg.wait_for_selector("#axv canvas[data-pronta]", timeout=30000)
        info=await pg.evaluate("({nome:document.querySelector('.axv-n').textContent, sub:document.querySelector('.axv-s').textContent, paginas:document.querySelectorAll('#axv canvas').length, pronta:document.querySelectorAll('#axv canvas[data-pronta]').length, branco: (()=>{const c=document.querySelector('#axv canvas[data-pronta]'); const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data; let n=0; for(let i=0;i<d.length;i+=4*97) if(d[i]<200) n++; return n>20})()})")
        chk("PDF abre DENTRO do app, com prévia desenhada (página com conteúdo)", info['pronta']>=1 and info['branco'], info)
        chk("mostra o nome e o nº de páginas", info['nome']=="AVALIA BM.pdf" and "página" in info['sub'], info)
        topo=await pg.evaluate("(()=>{const e=document.elementFromPoint(innerWidth/2, 160); return !!e && !!e.closest('#axv')})()"); chk("o visualizador está POR CIMA da ficha (dá pra tocar nele)", topo)
        await pg.screenshot(path=f"anx_{nome[:3]}_pdf.png")
        await pg.click(".axv-b"); await pg.wait_for_timeout(1500)
        sh=await pg.evaluate("window.__shared||[]")
        chk("'Baixar' entrega o arquivo certo (nome, tamanho, tipo)", sh and sh[-1]==["AVALIA BM.pdf",220025,"application/pdf"], sh)
        await pg.click(".axv-x"); await pg.wait_for_timeout(700)
        chk("'Fechar' volta pro app (nada de tela presa)", await pg.locator("#axv").count()==0 and await pg.locator("#tabbar").is_visible() and "localhost" in pg.url or "github.io" in pg.url)
        await pg.evaluate("window.__shared=[]"); await pg.click("#detBody .ax-dl"); await pg.wait_for_timeout(2500)
        sh=await pg.evaluate("window.__shared||[]"); chk("botão de baixar da ficha também entrega o arquivo", sh and sh[-1][0]=="AVALIA BM.pdf", sh)
        await pg.keyboard.press("Escape"); await pg.wait_for_timeout(500)
        print("== ANEXO FOTO (15 MB)")
        await pg.evaluate("document.querySelector('#det').open && document.querySelector('#det').close && document.querySelector('#det').close()"); await pg.wait_for_timeout(300)
        await abre(pg,"POST SESU - MANUTENÇÃO"); await pg.click("#detBody a.ax-img"); await pg.wait_for_selector("#axv", timeout=10000)
        await pg.wait_for_function("(()=>{const i=document.querySelector('#axv img'); return i && i.complete && i.naturalWidth>0})()", timeout=90000)
        chk("foto abre em tela cheia dentro do app", True); await pg.screenshot(path=f"anx_{nome[:3]}_foto.png")
        await pg.evaluate("window.__shared=[]"); await pg.click(".axv-b"); await pg.wait_for_timeout(2000)
        sh=await pg.evaluate("window.__shared||[]"); chk("'Baixar' a foto entrega o arquivo com o nome certo e tamanho grande", sh and sh[-1][2].startswith("image/") and sh[-1][1]>5_000_000, sh)
        await pg.click(".axv-x"); await pg.wait_for_timeout(500)
        print("== SAIR FUNCIONA")
        await pg.evaluate("document.querySelector('#det').open && document.querySelector('#det').close && document.querySelector('#det').close()")
        await pg.click("#tabbar [data-view=today]"); await pg.wait_for_timeout(600); await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.click(".sair-b"); await pg.wait_for_selector("#g-usuario", timeout=15000)
        chk("tocar em 'Sair da conta' volta pra tela de login", await pg.locator("#g-usuario").is_visible())
        await pg.reload(); await pg.wait_for_selector("#g-usuario", timeout=15000); chk("e continua deslogado depois de reabrir", await pg.locator("#g-usuario").is_visible())
        if nome.startswith("WebKit"):
            print("== FUNCIONÁRIO (BM)")
            requests.post(f"{BASE}/functions/v1/criar-perfil", json={"codigo":CODIGO,"nome":"Func Teste","usuario":"tst.fn","senha":"SenhaForte123"}); uid=sql("select id from public.pessoas where usuario='tst.fn'")[0]['id']
            sql(f"update public.pessoas set papel='membro' where id='{uid}'"); sql(f"insert into public.acessos values ('{uid}','asc')")
            await entra(pg,"tst.fn","SenhaForte123"); await pg.evaluate("window.scrollTo(0, document.body.scrollHeight)"); await pg.wait_for_timeout(500)
            chk("funcionário também tem 'Sair da conta' no fim do Início", await pg.locator(".sair-b").count()==1)
            chk("funcionário vê a logo da BM no topo", await pg.evaluate("(()=>{const i=document.querySelector('#areaBanner img.abn-logo'); return !!i && i.complete && i.naturalWidth>0})()"))
            await pg.evaluate("window.scrollTo(0,0)"); await pg.screenshot(path="anx_func.png")
    except Exception as e: chk("execução sem travar", False, repr(e)[:200])
    finally:
        if uid: requests.delete(f"{BASE}/auth/v1/admin/users/{uid}", headers=SV)
        print("erros de JS:", errs); await b.close()
async def main():
    async with async_playwright() as p:
        await rodar("WebKit (iPhone)", p.webkit, p.devices['iPhone 13'])
        if "so-webkit" not in sys.argv: await rodar("Chromium (Android)", p.chromium, p.devices['Pixel 7'])
    print(f"\nRESULTADO: {sum(res)} de {len(res)}")
asyncio.run(main())
