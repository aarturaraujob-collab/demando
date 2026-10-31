"""Gera de verdade as imagens da semana/mês e o relatório PDF (admin) e salva em $OUT. App local em http://localhost:8766.
Uso: ADMIN_SENHA=<senha> OUT=/tmp/img python3 tests/imagens_gerar.py   (depois: OUT=/tmp/img python3 tests/imagens_logos_test.py)"""
import asyncio, os, subprocess
from playwright.async_api import async_playwright
ADMIN=os.environ['ADMIN_SENHA']; URL=os.environ.get("APP","http://localhost:8766/index.html"); OUT=os.environ.get("OUT","/home/claude/logos_img"); os.makedirs(OUT, exist_ok=True)
async def main():
  async with async_playwright() as p:
    b=await p.chromium.launch(); ctx=await b.new_context(viewport={"width":390,"height":844}, accept_downloads=True); pg=await ctx.new_page(); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario","admin"); await pg.fill("#g-senha",ADMIN); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(3000)
    logos=await pg.evaluate("Object.keys(window.DEMANDO_LOGOS||{})"); print("logos carregadas na página:", logos)
    for area in ("all","fed","asc"):
        await pg.click("#tabbar [data-view=today]"); await pg.click(f"#mFr button[data-fr={area}]"); await pg.wait_for_timeout(1000)
        await pg.click("#shotBtn"); await pg.wait_for_selector("#shotBody img", timeout=20000)
        async with pg.expect_download() as d: await pg.click("#shotSave")
        dd=await d.value; await dd.save_as(f"{OUT}/semana_{area}.png"); await pg.wait_for_timeout(2500); await pg.evaluate("(()=>{const d=document.querySelector('#shot'); if (d && d.open) document.querySelector('#shotClose').click()})()"); await pg.wait_for_function("!document.querySelector('#shot') || !document.querySelector('#shot').open", timeout=10000); await pg.wait_for_timeout(400)
        await pg.click("#tabbar [data-view=month]"); await pg.wait_for_timeout(900); await pg.click("#view .shotb"); await pg.wait_for_selector("#shotBody img", timeout=20000)
        async with pg.expect_download() as d: await pg.click("#shotSave")
        dd=await d.value; await dd.save_as(f"{OUT}/mes_{area}.png"); await pg.wait_for_timeout(2500); await pg.evaluate("(()=>{const d=document.querySelector('#shot'); if (d && d.open) document.querySelector('#shotClose').click()})()"); await pg.wait_for_function("!document.querySelector('#shot') || !document.querySelector('#shot').open", timeout=10000); await pg.wait_for_timeout(400)
    await pg.click("#mFr button[data-fr=all]"); await pg.click("#tabbar [data-view=mais]"); await pg.click(".mtabs button:has-text('Relatório')"); await pg.wait_for_timeout(600)
    await pg.click(".mbox .adm-go"); await pg.wait_for_selector("#repBody img", timeout=25000)
    async with pg.expect_download() as d: await pg.click("#repPdf")
    dd=await d.value; await dd.save_as(f"{OUT}/relatorio_bm.pdf"); print("relatório:", dd.suggested_filename)
    subprocess.run(["pdftoppm","-png","-r","60","-f","1","-l","1",f"{OUT}/relatorio_bm.pdf",f"{OUT}/relatorio_bm"], check=True)
    print("erros de JS:", errs); await b.close()
asyncio.run(main())
