"""Confere, pelos pixels, as logos nas imagens e no relatório gerados pelo app (usa as imagens de t_logos_img.py)."""
import os, subprocess, numpy as np
from PIL import Image
OUT=os.environ.get("OUT","/home/claude/logos_img"); res=[]
def chk(n,c,d=""): res.append(bool(c)); print(("  ✅ " if c else "  ❌ ")+n+(" — "+str(d)[:110] if d else ""))
def reg(img,x0,y0,x1,y1): return np.array(img.convert('RGB').crop((x0,y0,x1,y1))).reshape(-1,3).astype(int)
def verde(px): R,G,B=px[:,0],px[:,1],px[:,2]; return ((G>R+35)&(G>B+10)&(G>90)).mean()           # faixa da BM
def vermelho(px): R,G,B=px[:,0],px[:,1],px[:,2]; return ((R>200)&(G<70)&(B<80)).mean()
def azul(px): R,G,B=px[:,0],px[:,1],px[:,2]; return ((B>150)&(R<40)&(G>80)&(G<140)).mean()      # azul da faixa tricolor
def escuro(px): return (px.sum(axis=1)<150).mean()
def titulo_preto(img):
    px=reg(img,56,125,700,190); d=px[px.sum(axis=1)<330]
    if len(d)<500: return False, None
    m=d.mean(axis=0); return bool(m.max()<75 and (m[1]-m[0])<22), tuple(int(v) for v in m)
S=lambda n: Image.open(f"{OUT}/{n}.png")
print("== IMAGEM DA SEMANA")
a=S("semana_asc"); chk("BM: faixa verde com a logo da Prefeitura no canto", verde(reg(a,60,44,240,108))>0.45, f"{verde(reg(a,60,44,240,108)):.0%} verde")
ok,m=titulo_preto(a); chk("BM: título 'Demandas da semana' em preto (não verde)", ok, m)
f=S("semana_fed"); chk("FAF: escudo (escuro, vermelho e azul)", escuro(reg(f,58,300-250+10,132,118))>0.1 and vermelho(reg(f,58,70,132,118))>0.005 and azul(reg(f,58,70,132,118))>0.005)
chk("FAF: título em preto", titulo_preto(f)[0], titulo_preto(f)[1])
t=S("semana_all"); chk("Todas: escudo da FAF + faixa da BM ao lado do Demandô", vermelho(reg(t,350,50,420,118))>0.005 and verde(reg(t,455,50,580,100))>0.4)
chk("Todas: título em preto", titulo_preto(t)[0], titulo_preto(t)[1])
print("== CRONOGRAMA DO MÊS")
m1=S("mes_asc"); chk("BM: faixa verde com a logo", verde(reg(m1,60,44,240,108))>0.45)
m2=S("mes_fed"); chk("FAF: escudo", vermelho(reg(m2,58,60,132,118))>0.005 and azul(reg(m2,58,60,132,118))>0.005)
m3=S("mes_all"); chk("Todas: as duas logos", vermelho(reg(m3,350,50,420,118))>0.005 and verde(reg(m3,455,50,580,100))>0.4)
print("== RELATÓRIO MENSAL (PDF)")
info=subprocess.run(["pdfinfo",f"{OUT}/relatorio_bm.pdf"],capture_output=True,text=True).stdout; pg=int([l for l in info.splitlines() if l.startswith("Pages")][0].split()[1])
subprocess.run(["pdftoppm","-png","-r","60",f"{OUT}/relatorio_bm.pdf",f"{OUT}/rpag"],check=True)
fs=sorted(x for x in os.listdir(OUT) if x.startswith("rpag"))
for k,fn in enumerate(fs,1):
    im=Image.open(f"{OUT}/{fn}"); w,h=im.size; px=reg(im,int(w*0.74),int(h*0.025),int(w*0.93),int(h*0.075))
    chk(f"página {k} de {pg}: logo da Prefeitura no canto direito do topo", verde(px)>0.25, f"{verde(px):.0%} verde")
print(f"RESULTADO: {sum(res)} de {len(res)}")
