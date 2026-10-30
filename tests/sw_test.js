const vm = require("vm"), fs = require("fs");
const ouvintes = {}, mostradas = [], aberturas = [], focos = [];
const self_ = {
  addEventListener: (n, f) => { ouvintes[n] = f; }, skipWaiting: () => {}, clients: { claim: () => {}, matchAll: async () => (self_._janelas || []), openWindow: async u => { aberturas.push(u); } },
  registration: { showNotification: async (t, o) => { mostradas.push([t, o]); } }
};
vm.runInNewContext(fs.readFileSync("app/sw.js", "utf8"), { self: self_, caches: { open: async () => ({ addAll: async () => {}, put: async () => {} }), keys: async () => [], delete: async () => {}, match: async () => null }, fetch: async () => ({ clone: () => ({}) }), URL, location: { origin: "http://x" } });
const rodar = async (nome, ev) => { let p; ev.waitUntil = x => { p = x; }; ouvintes[nome](ev); await p; };
(async () => {
  let ok = 0, tot = 0; const t = (n, c) => { tot++; if (c) ok++; console.log((c ? "  ✅ " : "  ❌ ") + n); };
  await rodar("push", { data: { json: () => ({ title: "Nova escala", body: "Arte da rodada · 30 out", tag: "nova-p1", url: "./" }) } });
  t("push com JSON: mostra título, texto e etiqueta certos", mostradas[0][0] === "Nova escala" && mostradas[0][1].body === "Arte da rodada · 30 out" && mostradas[0][1].tag === "nova-p1");
  t("usa o ícone do Demandô", mostradas[0][1].icon === "icons/icon-192.png");
  await rodar("push", { data: { json: () => { throw new Error("x"); }, text: () => "texto solto" } });
  t("push com texto simples (sem JSON): não quebra e usa o título 'Demandô'", mostradas[1][0] === "Demandô" && mostradas[1][1].body === "texto solto");
  await rodar("push", { data: null });
  t("push sem conteúdo: ainda mostra algo", mostradas[2][0] === "Demandô");
  let fechou = false; self_._janelas = []; await rodar("notificationclick", { notification: { close: () => { fechou = true; }, data: { url: "./" } } });
  t("tocar na notificação sem o app aberto: abre o app", fechou && aberturas[0] === "./");
  let focou = false; self_._janelas = [{ focus: async () => { focou = true; } }]; await rodar("notificationclick", { notification: { close: () => {}, data: {} } });
  t("tocar com o app já aberto: só traz pra frente (não abre outra janela)", focou && aberturas.length === 1);
  console.log(`RESULTADO: ${ok} de ${tot}`);
})();
