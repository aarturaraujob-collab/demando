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

**Quem entra:** cada pessoa com um **usuário e senha** (ex.: `juninho`). Por trás, o app converte o usuário num e-mail interno da caixa central,
com "+usuário" (`demandasbm+juninho@gmail.com`), então tudo cai numa caixa só. **Cada pessoa cria o próprio perfil** com o código da equipe
(função `criar-perfil`); o perfil nasce sem acesso e o admin libera papel e áreas. O cadastro direto no Supabase fica fechado.
Quem esquecer a senha pede ao admin, que redefine. Três papéis: `admin`, `membro` e `leitor`
(ex.: Gustavo, Júnior e Mariana acompanhando o Life). O acesso é por área. Acabam as senhas compartilhadas.

## Fases

- [x] **0. Preparação:** plano e esquema do banco (`supabase/schema.sql`, sintaxe validada).
- [x] **1. Projeto Supabase:** criado (São Paulo, plano gratuito), com acesso por token restrito ao projeto.
- [ ] **1b. Chave da Anthropic (você):** conta, chave de API e limite de gasto (só será preciso na fase da leitura por IA).
- [x] **2. Banco:** esquema rodado e testado (`supabase/tests/rls_test.py`): 9 tabelas com RLS, papéis admin, membro e leitor, e anexos privados.
- [x] **2b. Login:** usuário e senha, cadastro fechado no Supabase, função `criar-perfil` publicada e testada (`supabase/tests/cadastro_test.py`).
- [ ] **2c. Primeiros admins (eu):** criar as contas de admin e liberar a equipe conforme os perfis forem criados.
- [x] **3. Painel completo no Supabase (`/app`):** o painel inteiro (Início, Quadro, Agenda, Mês, comentários, anexos, imagens da semana e do mês, relatório em PDF, recorrentes, áreas e perfis) roda com login por usuário. Gerado por `tools/build_app.py` a partir do painel do Claude. Testado de ponta a ponta (`tests/app_full_test.py`, 27 verificações).
- [x] **3b. Ajustes de tela e de acesso:** cabeçalho do celular (nome no centro, sino à esquerda, data à direita), card da demanda com a ordem status/progresso, prazo e local, equipe; cartão "Quem é você?" no topo pro funcionário, que liga o nome dele às notificações; cadastro de cada pessoa protegido (migração 005).
- [x] **3c. Sair, logos e anexos:** botão "Sair da conta" no fim do Início e do Mais; logo da Prefeitura de Boca da Mata no banner e escudo nas etiquetas da BM e escudo da FAF (sem contorno, centralizado e sem nome escrito) no banner azul e nas etiquetas da FAF (a logo completa da FAF, com o texto, fica guardada em `app/assets`, só pra fundo claro); anexos abrem dentro do app com prévia (PDF e foto), botão Fechar e Baixar (pdf.js junto no repositório, em `app/vendor`).
- [x] **3d. Logos nas imagens e no relatório:** a logo da Prefeitura (faixa verde) e o escudo da FAF aparecem na imagem da semana, no cronograma do mês e em todas as páginas do relatório mensal. O painel do Claude fica como era (as logos só existem no site).
- [x] **3e. Sincronizar o painel do Claude com o site:** `tools/sincronizar_painel.py` compara demanda por demanda, traz o que é novo, atualiza o que só o painel mudou, mantém o que só o site mudou e mostra os conflitos. Nunca apaga. Enquanto a equipe usar o painel, rodar antes de qualquer conferência; na virada, rodar uma última vez.
- [x] **3f. Virada:** sincronização final feita (painel 44 × site em dia); aviso "O Demandô mudou de casa" publicado no painel do Claude, com link e passos; lixeira no servidor (`tools/restaurar_demanda.py` lista e restaura o que o app apagou, com quem e quando). A sincronização passou a respeitar o que for apagado no site de propósito. Falta: a equipe criar os perfis, o admin liberar cada um (Mais, Pessoas) e, quando todos estiverem dentro, congelar o painel.
- [x] **3g. Barra de baixo nova:** a Agenda saiu (o Início já mostra a agenda); no lugar entrou o "+" em destaque no meio da barra, que abre 3 opções: nova demanda, por texto (colar) e por foto. Contas de teste do admin: `admin`, `bm` (só BM) e `faf` (só FAF). O aviso "mudou de casa" do painel do Claude fica DESLIGADO (chave `AVISO_MUDANCA`) até a virada de verdade.
- [x] **3h. Funcionário vê a equipe toda:** escolher "Quem é você?" não esconde mais ninguém. Início, Quadro e Mês mostram todas as demandas; a aba **Minhas** (5ª da barra, no lugar do Mais) mostra só as escalas da pessoa; o Mês tem o botão "Todas as escalas / Minhas escalas". A barrinha Todas/FAF/BM/LIFE do admin ganhou os escudos da FAF e da BM e divisórias entre os botões. Atenção: o app copia pra áreas extras (LIFE) toda regra de estilo que cita `.asc`, então os escudos usam o atributo `data-logo`.
- [x] **3i. Nome só uma vez, etapas, arquivo e rodapé fixo.** (a) "Quem é você?" aparece uma vez por conta e fica no servidor (vale em qualquer aparelho); "Não sou eu", na aba Minhas, troca de propósito; o filtro de pessoa só serve pra olhar ("Escalas de fulano") e não é gravado. (b) Etapas: A fazer, Em produção, Ajustes, Entregue, Postada, com o fluxo visível em todo card. (c) Arquivo: concluídas (Entregue/Postada) há 14 dias ou mais são arquivadas sozinhas às 5h30 (migração 007); dá pra arquivar/desarquivar pela ficha; arquivadas saem do Quadro e da aba Minhas, mas continuam no Mês e nos relatórios. A tela de ver arquivadas fica pra quando houver configurações do admin. (d) Rodapé fixo: no celular só o miolo (`.app`) rola; a página não rola, então a barra não se mexe. (e) Secretaria de Esporte e logos da FAF/BM no resumo do Início.
- [x] **5. App no celular:** manifesto, ícones, service worker e dica de instalação.
- [x] **4a. Funções:** `criar-perfil`, `redefinir-senha` e `ler-pedido` publicadas. Os botões de foto e colar texto já aparecem no app; a leitura só passa a funcionar quando a chave da Anthropic entrar (até lá o app avisa).
- [x] **4b. Servidor:** recorrentes criadas todo dia às 5h (Maceió) direto no banco, sem ninguém abrir o app (mesma regra do painel, testada), e notificações no celular (`enviar-push`): nova escala, escalado depois, direcionamento e resumo das 8h. Testado em ensaio, sem entrega real num aparelho.
- [x] **6. Migração:** 39 demandas, a área Life e 4 anexos levados do painel do Claude (`tools/importar_do_claude.py`, pode rodar de novo na virada).
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
