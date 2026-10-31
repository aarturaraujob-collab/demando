# Precisa do arquivo de apoio com o painel simulado (t25_base.py); roda o aviso de mudança do painel do Claude.
exec(open('/home/claude/t25_base.py').read())
import hashlib
ADMH = hashlib.sha256(b'demando:1234').hexdigest(); res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:100] if d else ""))
SRC=open('/mnt/user-data/outputs/central-demandas.html',encoding='utf8').read()
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); errs=[]
    for nome,host in (("painel do Claude (endereço de verdade)","http://painel.exemplo.test/"),("teste local","http://localhost:9/")):
        ctx=await b.new_context(viewport={"width":390,"height":860}); pg=await ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
        await pg.route(host+"**", lambda r: r.fulfill(status=200, content_type="text/html; charset=utf-8", body=SRC))
        await pg.add_init_script("localStorage.clear();localStorage.setItem('cd-admhash','%s');localStorage.setItem('cd-adm','%s');" % (ADMH, ADMH) + mock)
        await pg.goto(host); await pg.wait_for_timeout(2200)
        aberto=await pg.evaluate("document.getElementById('movedDlg').open")
        print(f"== {nome}")
        if "Claude" in nome:
            chk("o aviso de mudança aparece sozinho", aberto)
            link=await pg.evaluate("(()=>{const a=document.getElementById('movedGo'); return {href:a.href, alvo:a.target, rel:a.rel}})()"); chk("o botão leva pro app novo (abre em outra aba)", link['href']=="https://aarturaraujob-collab.github.io/demando/app/" and link['alvo']=="_blank" and 'noopener' in link['rel'], link)
            txt=await pg.inner_text("#movedDlg"); chk("explica os passos (criar perfil, código da equipe, liberação)", all(x in txt for x in ("Criar meu perfil","código da equipe","liberar")))
            g=await pg.evaluate("(()=>{const r=document.getElementById('movedDlg').getBoundingClientRect(), a=document.querySelector('.mvd-a').getBoundingClientRect(), n=document.getElementById('movedNo').getBoundingClientRect(); return {dx: Math.round((r.left+r.right)/2 - innerWidth/2), dy: Math.round((r.top+r.bottom)/2 - innerHeight/2), cabe: r.left>=0 && r.right<=innerWidth && r.top>=0 && r.bottom<=innerHeight, botoesDentro: n.right<=r.right && a.right<=r.right+1, altura: Math.round(r.height)}})()")
            chk("o cartão fica CENTRALIZADO e cabe inteiro na tela", abs(g['dx'])<=2 and abs(g['dy'])<=2 and g['cabe'], g)
            bt=await pg.evaluate("(()=>{const d=document.getElementById('movedDlg').getBoundingClientRect(), a=document.getElementById('movedGo'), n=document.getElementById('movedNo'); const ra=a.getBoundingClientRect(), rn=n.getBoundingClientRect(); return {dentro: ra.left>=d.left && ra.right<=d.right && rn.left>=d.left && rn.right<=d.right, textoCabe: n.scrollWidth<=n.clientWidth+1 && a.scrollWidth<=a.clientWidth+1, larguraNao: Math.round(rn.width)}})()"); chk("os dois botões ficam dentro do cartão, com o texto inteiro dentro de cada um", bt['dentro'] and bt['textoCabe'], bt)
            await pg.screenshot(path="aviso_painel.png")
            await pg.click("#movedNo"); await pg.wait_for_timeout(400); chk("'Agora não' fecha e o painel segue funcionando", not await pg.evaluate("document.getElementById('movedDlg').open") and await pg.locator("#tabbar").is_visible())
        else: chk("em teste local o aviso NÃO aparece", not aberto)
        await ctx.close()
    print("erros de JS:", errs); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
