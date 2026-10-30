-- Ponte do painel completo: áreas removidas (com desfazer), preferências por pessoa e nomes no histórico.
alter table public.areas add column if not exists removida boolean not null default false;

create table if not exists public.preferencias (
  pessoa_id      uuid primary key references public.pessoas(id) on delete cascade,
  dados          jsonb not null default '{}'::jsonb,
  atualizado_em  timestamptz not null default now()
);
alter table public.preferencias enable row level security;
drop policy if exists prefs_dono on public.preferencias;
create policy prefs_dono on public.preferencias for all to authenticated using (pessoa_id = auth.uid()) with check (pessoa_id = auth.uid());

-- Qualquer pessoa ativa vê o NOME (só o nome) de quem aparece no histórico.
create or replace function public.nomes_pessoas(ids uuid[]) returns table(id uuid, nome text)
language sql stable security definer set search_path = public as $$
  select p.id, p.nome from public.pessoas p
  where p.id = any(ids) and exists (select 1 from public.pessoas me where me.id = auth.uid() and me.ativo);
$$;
revoke all on function public.nomes_pessoas(uuid[]) from public, anon;
grant execute on function public.nomes_pessoas(uuid[]) to authenticated;
