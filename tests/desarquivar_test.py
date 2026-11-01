"""Desarquivar uma demanda antiga: o arquivo automático não pode arquivar de novo no dia seguinte. App local em http://localhost:8766.
Uso: TZ=America/Maceio SB=<token> ADMIN_SENHA=<senha do admin> python3 tests/desarquivar_test.py   (só mexe numa demanda de teste, apagada no fim)"""
import asyncio, os, requests
from playwright.async_api import async_playwright
SB=os.environ['SB']; REF='uaakiytxphmtwsthooih'; M={"Authorization":"Bearer "+SB,"User-Agent":"demando-test"}
sql=lambda s: requests.post(f"https://api.supabase.com/v1/projects/{REF}/database/query", headers=M, json={"query":s}).json()
URL=os.environ.get("APP","http://localhost:8766/index.html"); res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:120] if d else ""))
async def main():
  async with async_playwright() as p:
    b=await p.webkit.launch(); pg=await (await b.new_context(**p.devices['iPhone 13'])).new_page(); errs=[]; pg.on("pageerror", lambda e: errs.append(str(e)))
    try:
      antes=sql("select count(*) n from public.demandas where arquivada_em is not null")[0]['n']
      sql("delete from public.demandas where id='tst-da1'")
      sql("insert into public.demandas(id, area_id, titulo, status, entregue, prazo) values ('tst-da1','asc','DESARQUIVAR teste','Entregue',(now() at time zone 'America/Maceio')::date - 20,(now() at time zone 'America/Maceio')::date - 25)")
      sql("select public.arquivar_antigas()")
      est=lambda: sql("select arquivada_em is not null arq, desarquivada_em is not null desarq from public.demandas where id='tst-da1'")[0]
      chk("entregue há 20 dias: o robô arquiva", est()['arq'] is True, est())
      await pg.goto(URL); await pg.wait_for_selector("#g-usuario"); await pg.fill("#g-usuario","admin"); await pg.fill("#g-senha",os.environ['ADMIN_SENHA']); await pg.click("#g-entrar"); await pg.wait_for_selector("#tabbar", state="visible", timeout=30000); await pg.wait_for_timeout(2500)
      ok=await pg.evaluate("window.DEMANDO_API.arquivar('tst-da1', false)"); chk("o admin desarquiva (pelo mesmo caminho do botão)", ok is True and est()['arq'] is False and est()['desarq'] is True, est())
      sql("select public.arquivar_antigas()"); chk("o robô roda de novo e NÃO arquiva de novo a desarquivada à mão", est()['arq'] is False, est())
      ok=await pg.evaluate("window.DEMANDO_API.arquivar('tst-da1', true)"); chk("arquivar à mão de novo funciona e limpa a marca de desarquivada", ok is True and est()['arq'] is True and est()['desarq'] is False, est())
      depois=sql("select count(*) n from public.demandas where arquivada_em is not null and id<>'tst-da1'")[0]['n']; chk("nenhuma outra demanda foi arquivada pelo teste", depois==antes, {"antes":antes,"depois":depois})
    finally:
      sql("delete from public.demandas where id='tst-da1'"); print("erros de JS:", errs, "| restos:", sql("select count(*) n from public.demandas where id='tst-da1'")[0]['n']); print(f"RESULTADO: {sum(res)} de {len(res)}"); await b.close()
asyncio.run(main())
