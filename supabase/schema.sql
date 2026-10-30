-- =====================================================================
-- Demandô · esquema do banco (Supabase / Postgres)
-- Rodar uma vez, no SQL Editor do projeto.
-- Rascunho v1: a sintaxe foi validada; a primeira execução real ajusta o que precisar.
-- =====================================================================

create extension if not exists pgcrypto;

-- ---------------------------------------------------------------------
-- 1. Áreas (FAF, BM, Life e as que forem criadas)
-- ---------------------------------------------------------------------
create table if not exists public.areas (
  id         text primary key,                                  -- 'fed', 'asc', 'aqutz8ei'...
  sigla      text not null,
  nome       text not null,
  cor        text not null check (cor ~ '^#[0-9A-Fa-f]{6}$'),
  equipe     text[] not null default '{}',                      -- quem produz
  perfis     text[] not null default '{}',                      -- pessoas atendidas (ex.: Life)
  tipos      text[] not null default '{}',                      -- tipos de peça próprios (vazio = lista padrão)
  so_admin   boolean not null default false,
  padrao     boolean not null default false,                    -- FAF e BM não podem ser removidas
  ordem      int not null default 0,
  criado_em  timestamptz not null default now()
);

create table if not exists public.secretarias (
  nome         text primary key,
  responsavel  text,                                            -- ajuda a leitura por IA ("a Deca pediu" = Saúde)
  ordem        int not null default 0
);

-- ---------------------------------------------------------------------
-- 2. Pessoas, papéis e acesso por área (substitui as senhas compartilhadas)
-- ---------------------------------------------------------------------
create table if not exists public.pessoas (
  id           uuid primary key references auth.users(id) on delete cascade,
  nome         text not null,
  email        text unique,
  usuario      text unique,                                     -- o que a pessoa digita no login
  papel        text not null default 'leitor' check (papel in ('admin','membro','leitor')),
  nome_equipe  text,                                            -- como aparece nas escalas (ex.: "Celso")
  ativo        boolean not null default true,
  criado_em    timestamptz not null default now()
);

create table if not exists public.acessos (
  pessoa_id  uuid not null references public.pessoas(id) on delete cascade,
  area_id    text not null references public.areas(id) on delete cascade,
  primary key (pessoa_id, area_id)
);

-- Quem se cadastra entra como "leitor", sem acesso a nada, até um admin liberar.
create or replace function public.novo_usuario() returns trigger
language plpgsql security definer set search_path = public as $$
declare
  loc text := split_part(new.email, '@', 1);
  u   text := coalesce(new.raw_user_meta_data->>'usuario',
                       case when position('+' in loc) > 0 then substring(loc from position('+' in loc) + 1) else loc end);
begin
  insert into public.pessoas (id, nome, email, usuario)
  values (new.id, coalesce(new.raw_user_meta_data->>'nome', u), new.email, u)
  on conflict (id) do nothing;
  return new;
end $$;

drop trigger if exists ao_criar_usuario on auth.users;
create trigger ao_criar_usuario after insert on auth.users
  for each row execute function public.novo_usuario();

-- ---------------------------------------------------------------------
-- 3. Demandas, comentários e recorrentes
-- ---------------------------------------------------------------------
create table if not exists public.demandas (
  id            text primary key,
  area_id       text not null references public.areas(id),
  titulo        text not null,
  tipo          text,
  prazo         date,
  hora          time,
  local         text,
  status        text not null default 'A fazer' check (status in ('A fazer','Em produção','Entregue')),
  prioridade    text not null default 'Média' check (prioridade in ('Baixa','Média','Alta')),
  solicitante   text,
  secretaria    text,
  perfil        text,
  equipe        text[] not null default '{}',
  obs           text,
  original      text,                                           -- pedido como chegou (leitura por IA)
  link          text,
  checklist     jsonb not null default '[]',
  anexos        jsonb not null default '[]',
  historico     jsonb not null default '[]',
  criado        date not null default current_date,
  entregue      date,
  recorrente_id text,
  n_coment      int not null default 0,
  criado_por    uuid references auth.users(id),
  criado_em     timestamptz not null default now(),
  atualizado_em timestamptz not null default now()
);
create index if not exists demandas_area_prazo on public.demandas (area_id, prazo);
create index if not exists demandas_status on public.demandas (status);
create index if not exists demandas_equipe on public.demandas using gin (equipe);

create table if not exists public.comentarios (
  id          text primary key,
  demanda_id  text not null references public.demandas(id) on delete cascade,
  texto       text,
  anexos      jsonb not null default '[]',
  fixado      boolean not null default false,                   -- "direcionamento / roteiro"
  por         uuid references auth.users(id),
  autor       text,
  em          timestamptz not null default now()
);
create index if not exists comentarios_demanda on public.comentarios (demanda_id, em);

create table if not exists public.recorrentes (
  id             text primary key,
  area_id        text not null references public.areas(id),
  ativo          boolean not null default true,
  titulo         text not null,
  tipo           text,
  freq           text not null default 'semanal' check (freq in ('semanal','mensal')),
  dias           int[] not null default '{}',                   -- 0 = domingo ... 6 = sábado
  dia            int not null default 1 check (dia between 1 and 31),
  hora           time,
  local          text,
  prioridade     text not null default 'Média',
  equipe         text[] not null default '{}',
  secretaria     text,
  perfil         text,
  checklist      jsonb not null default '[]',
  ultimo_gerado  date,
  criado_em      timestamptz not null default now()
);

-- ---------------------------------------------------------------------
-- 4. Notificações e preferências de cada pessoa
-- ---------------------------------------------------------------------
create table if not exists public.push_subs (
  id         uuid primary key default gen_random_uuid(),
  pessoa_id  uuid not null references public.pessoas(id) on delete cascade,
  endpoint   text not null unique,
  p256dh     text not null,
  auth       text not null,
  criado_em  timestamptz not null default now()
);

create table if not exists public.vistos (                      -- "novas escalas" já vistas
  pessoa_id  uuid not null references public.pessoas(id) on delete cascade,
  chave      text not null,
  primary key (pessoa_id, chave)
);

-- ---------------------------------------------------------------------
-- 5. Funções de segurança
-- ---------------------------------------------------------------------
create or replace function public.eh_admin() returns boolean
language sql stable security definer set search_path = public as $$
  select exists (select 1 from public.pessoas p where p.id = auth.uid() and p.papel = 'admin' and p.ativo);
$$;

create or replace function public.tem_acesso(a text) returns boolean
language sql stable security definer set search_path = public as $$
  select public.eh_admin() or exists (
    select 1 from public.acessos x join public.pessoas p on p.id = x.pessoa_id
    where x.pessoa_id = auth.uid() and x.area_id = a and p.ativo);
$$;

create or replace function public.pode_escrever(a text) returns boolean
language sql stable security definer set search_path = public as $$
  select public.eh_admin() or exists (
    select 1 from public.acessos x join public.pessoas p on p.id = x.pessoa_id
    where x.pessoa_id = auth.uid() and x.area_id = a and p.ativo and p.papel = 'membro');
$$;

-- Membro só muda etapa, checklist, anexos e histórico de demandas de outras pessoas.
-- Admin e quem criou a demanda editam tudo.
create or replace function public.limita_edicao() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.atualizado_em := now();
  if public.eh_admin() or old.criado_por is not distinct from auth.uid() or auth.uid() is null then
    return new;
  end if;
  if (new.area_id, new.titulo, new.tipo, new.prazo, new.hora, new.local, new.prioridade, new.solicitante,
      new.secretaria, new.perfil, new.equipe, new.obs, new.original, new.link)
     is distinct from
     (old.area_id, old.titulo, old.tipo, old.prazo, old.hora, old.local, old.prioridade, old.solicitante,
      old.secretaria, old.perfil, old.equipe, old.obs, old.original, old.link) then
    raise exception 'Você só pode mudar etapa, checklist e anexos de demandas de outras pessoas.';
  end if;
  return new;
end $$;

drop trigger if exists demandas_limita_edicao on public.demandas;
create trigger demandas_limita_edicao before update on public.demandas
  for each row execute function public.limita_edicao();

-- Mantém o contador de comentários da demanda.
create or replace function public.conta_comentarios() returns trigger
language plpgsql security definer set search_path = public as $$
declare d text := coalesce(new.demanda_id, old.demanda_id);
begin
  update public.demandas set n_coment = (select count(*) from public.comentarios where demanda_id = d) where id = d;
  return null;
end $$;

drop trigger if exists comentarios_conta on public.comentarios;
create trigger comentarios_conta after insert or delete on public.comentarios
  for each row execute function public.conta_comentarios();

-- ---------------------------------------------------------------------
-- 6. Permissões (RLS): ninguém lê nem escreve nada sem entrar e sem ter acesso
-- ---------------------------------------------------------------------
alter table public.areas        enable row level security;
alter table public.secretarias  enable row level security;
alter table public.pessoas      enable row level security;
alter table public.acessos      enable row level security;
alter table public.demandas     enable row level security;
alter table public.comentarios  enable row level security;
alter table public.recorrentes  enable row level security;
alter table public.push_subs    enable row level security;
alter table public.vistos       enable row level security;

-- áreas: lê quem tem acesso; só admin mexe
create policy areas_ler    on public.areas for select to authenticated using (public.tem_acesso(id) and (not so_admin or public.eh_admin()));
create policy areas_admin  on public.areas for all    to authenticated using (public.eh_admin()) with check (public.eh_admin());

create policy secretarias_ler   on public.secretarias for select to authenticated using (true);
create policy secretarias_admin on public.secretarias for all    to authenticated using (public.eh_admin()) with check (public.eh_admin());

-- pessoas e acessos: cada um vê o próprio; admin vê e muda tudo
create policy pessoas_ler    on public.pessoas for select to authenticated using (id = auth.uid() or public.eh_admin());
create policy pessoas_nome   on public.pessoas for update to authenticated using (id = auth.uid()) with check (id = auth.uid() and papel = (select papel from public.pessoas where id = auth.uid()));
create policy pessoas_admin  on public.pessoas for all    to authenticated using (public.eh_admin()) with check (public.eh_admin());
create policy acessos_ler    on public.acessos for select to authenticated using (pessoa_id = auth.uid() or public.eh_admin());
create policy acessos_admin  on public.acessos for all    to authenticated using (public.eh_admin()) with check (public.eh_admin());

-- demandas
create policy demandas_ler    on public.demandas for select to authenticated using (public.tem_acesso(area_id));
create policy demandas_criar  on public.demandas for insert to authenticated with check (public.pode_escrever(area_id) and criado_por = auth.uid());
create policy demandas_mudar  on public.demandas for update to authenticated using (public.pode_escrever(area_id)) with check (public.pode_escrever(area_id));
create policy demandas_apagar on public.demandas for delete to authenticated using (public.eh_admin() or (criado_por = auth.uid() and public.pode_escrever(area_id)));

-- comentários
create policy coment_ler    on public.comentarios for select to authenticated using (exists (select 1 from public.demandas d where d.id = demanda_id and public.tem_acesso(d.area_id)));
create policy coment_criar  on public.comentarios for insert to authenticated with check (por = auth.uid() and exists (select 1 from public.demandas d where d.id = demanda_id and public.pode_escrever(d.area_id)));
create policy coment_apagar on public.comentarios for delete to authenticated using (por = auth.uid() or public.eh_admin());

-- recorrentes: só admin
create policy recorrentes_admin on public.recorrentes for all to authenticated using (public.eh_admin()) with check (public.eh_admin());

-- notificações e "vistos": só o próprio dono
create policy push_dono   on public.push_subs for all to authenticated using (pessoa_id = auth.uid()) with check (pessoa_id = auth.uid());
create policy vistos_dono on public.vistos    for all to authenticated using (pessoa_id = auth.uid()) with check (pessoa_id = auth.uid());

-- ---------------------------------------------------------------------
-- 7. Anexos (imagens, PDF e vídeo): bucket privado
-- ---------------------------------------------------------------------
insert into storage.buckets (id, name, public, file_size_limit)
values ('anexos', 'anexos', false, 52428800)                    -- 50 MB por arquivo
on conflict (id) do nothing;

create policy anexos_ler    on storage.objects for select to authenticated using (bucket_id = 'anexos');
create policy anexos_enviar on storage.objects for insert to authenticated with check (bucket_id = 'anexos' and exists (select 1 from public.pessoas p where p.id = auth.uid() and p.papel in ('admin','membro') and p.ativo));
create policy anexos_apagar on storage.objects for delete to authenticated using (bucket_id = 'anexos' and (owner = auth.uid() or public.eh_admin()));

-- ---------------------------------------------------------------------
-- 8. Tempo real (as telas atualizam sozinhas quando alguém muda algo)
-- ---------------------------------------------------------------------
do $$ begin alter publication supabase_realtime add table public.demandas;    exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.comentarios; exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.areas;       exception when duplicate_object then null; end $$;
do $$ begin alter publication supabase_realtime add table public.recorrentes; exception when duplicate_object then null; end $$;

-- ---------------------------------------------------------------------
-- 9. Dados iniciais (áreas padrão e secretarias)
-- ---------------------------------------------------------------------
insert into public.areas (id, sigla, nome, cor, equipe, padrao, ordem) values
  ('fed', 'FAF', 'Federação Alagoana de Futebol', '#2F5BEA', array['Juninho','Arthur','Malu','Cadu','Ester'], true, 1),
  ('asc', 'BM',  'Boca da Mata',                  '#10A36A', array['Juninho','Leopoldo','Celso','Sara','Arthur','Mauro'], true, 2)
on conflict (id) do nothing;

insert into public.secretarias (nome, responsavel, ordem) values
  ('Previdência (PREV)','Marx',1), ('Cultura','Júnior',2), ('Transporte','Marcelo',3), ('Infraestrutura','Ricardo',4),
  ('Saúde','Deca',5), ('Educação','Maria Izaura',6), ('Assistência Social','Adriano',7), ('SAAE','Vaninho',8),
  ('Finanças','Aliny',9), ('Obras','Amando',10), ('Gestão e Patrimônio','Luana',11), ('Agricultura','Luiz Lula',12),
  ('Gabinete Civil','Mariana Feijó',13)
on conflict (nome) do nothing;

-- Depois de criar a conta do primeiro admin, rodar (trocando o e-mail):
--   update public.pessoas set papel = 'admin' where email = 'SEU-EMAIL@exemplo.com';
