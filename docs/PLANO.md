# Demandô no ar 100% · plano de ataque

Objetivo: o Demandô funcionar inteiro num servidor próprio, sem depender do Claude, com login individual,
notificações no celular e instalação como app (iPhone e Android) pelo navegador, sem App Store.

## Arquitetura

| Peça | O que usa | Por quê |
|---|---|---|
| Telas | Arquivos estáticos (HTML, JS, CSS) no GitHub Pages | De graça, sem servidor pra cuidar |
| Banco, login, tempo real, arquivos | **Supabase** (Postgres, Auth, Realtime, Storage) | Tudo num lugar só, com plano gratuito |
| Leitura de foto e texto por IA | Função no Supabase que chama a API da Anthropic | A chave fica no servidor, nunca no celular |
| Recorrentes e avisos de prazo | Tarefa agendada no Supabase (todo dia) | Cria os cards sozinha, sem ninguém abrir o app |
| Notificação no celular | Web Push (PWA) | Chega com o celular bloqueado |
| Instalação | PWA (manifesto, ícone do "ô", service worker) | Instala pelo navegador |

**Quem entra:** cada pessoa com um **usuário e senha** (ex.: `juninho`). Por trás, o app converte o usuário num e-mail interno
(`juninho@usuarios.demando.app`), que nunca recebe mensagem. Só o admin cria contas (cadastro livre fechado, senha mínima de 8).
Quem esquecer a senha pede ao admin, que redefine. Três papéis: `admin`, `membro` e `leitor`
(ex.: Gustavo, Júnior e Mariana acompanhando o Life). O acesso é por área. Acabam as senhas compartilhadas.

## Fases

- [x] **0. Preparação:** plano e esquema do banco (`supabase/schema.sql`, sintaxe validada).
- [x] **1. Projeto Supabase:** criado (São Paulo, plano gratuito), com acesso por token restrito ao projeto.
- [ ] **1b. Chave da Anthropic (você):** conta, chave de API e limite de gasto (só será preciso na fase da leitura por IA).
- [x] **2. Banco:** esquema rodado e testado (`supabase/tests/rls_test.py`): 9 tabelas com RLS, papéis admin, membro e leitor, e anexos privados.
- [ ] **2b. Login e primeiros usuários (eu):** método de login, cadastro só por convite, contas dos admins e da equipe.
- [ ] **3. Porte do app (eu):** trocar a camada de dados do Claude pela do Supabase, login, papéis, tela de pessoas e acessos, tempo real, anexos.
- [ ] **4. Servidor (eu):** funções `ler-pedido` (IA), `gerar-recorrentes` (diária) e `enviar-push`.
- [ ] **5. App no celular (eu):** manifesto, ícones, service worker, tela de "instalar".
- [ ] **6. Migração (eu):** exportar as demandas, áreas, recorrentes e comentários do painel atual e importar, conferindo as contagens.
- [ ] **7. Teste com a equipe (todos):** uso real por alguns dias, ajustes.
- [ ] **8. Virada:** o link novo vira o oficial, o painel do Claude fica só como cópia de segurança. Domínio próprio, se quiserem.

Estimativa: cerca de 2 semanas depois que as contas e chaves estiverem prontas.

## O que cada um faz

**Eu faço sozinho:** o esquema do banco, o porte do app, as funções do servidor, o PWA e os ícones, a migração dos dados,
os testes automáticos e as publicações no GitHub. Com um token do Supabase, também crio o projeto, rodo o SQL,
subo as funções e configuro o que for preciso.

**Preciso de você:**
1. Conta no Supabase (supabase.com, entrando com o GitHub) e, se quiser que eu configure tudo, um token de acesso.
2. Conta na Anthropic (console.anthropic.com), uma chave de API e um limite de gasto mensal.
3. Lista de quem entra: e-mail, papel (admin, membro, leitor) e áreas de cada um.
4. Decisão do endereço (o gratuito do GitHub ou um domínio próprio).
5. Testar com a equipe e dizer o que incomoda.

## Custos (estimativa)

- GitHub Pages: R$ 0.
- Supabase gratuito: serve pro tamanho de vocês, mas **pausa depois de 7 dias sem uso** e não tem backup diário.
  O plano Pro (cerca de US$ 25 por mês) tira a pausa e inclui backups.
- Anthropic: paga por uso, centavos por leitura de foto ou texto, com limite que vocês definem.
- Domínio próprio (opcional): cerca de R$ 40 por ano.

## Segurança

- O repositório é público: **nenhuma chave secreta entra nele**. Segredos ficam só no Supabase.
- A chave pública (`anon`) do Supabase pode aparecer no app, porque quem protege os dados são as regras do banco (RLS), já escritas no esquema.
- A chave de serviço (`service_role`) e a da Anthropic nunca vão pro celular nem pro GitHub.
- Tokens que passam pelo chat são apagados depois do uso.

## Decisões em aberto

- Login: decidido, usuário e senha. Google pode ser somado depois.
- Endereço: GitHub Pages ou domínio próprio?
- Supabase: gratuito no começo ou já o Pro?
- Life: Gustavo, Júnior e Mariana entram como `leitor` (só acompanham)?
