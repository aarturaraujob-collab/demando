-- Lixeira: toda demanda/comentário/recorrente apagado PELO APP (ou pela API) é guardado, com quem apagou e quando. O admin pode restaurar.
-- (Apagamentos feitos direto no painel SQL do servidor, como a limpeza dos testes, não entram.)
create table if not exists public.lixeira (
  id bigserial primary key, tabela text not null, registro_id text, linha jsonb not null,
  apagado_por uuid, apagado_em timestamptz not null default now(), restaurado_em timestamptz
);
alter table public.lixeira enable row level security;
drop policy if exists lixeira_admin on public.lixeira;
create policy lixeira_admin on public.lixeira for select to authenticated using (public.eh_admin());

create or replace function public.t_guarda_lixeira() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if session_user not in ('postgres', 'supabase_admin') then
    insert into public.lixeira(tabela, registro_id, linha, apagado_por) values (tg_table_name, old.id::text, to_jsonb(old), auth.uid());
  end if;
  return old;
end $$;
drop trigger if exists demandas_lixeira on public.demandas;
create trigger demandas_lixeira before delete on public.demandas for each row execute function public.t_guarda_lixeira();
drop trigger if exists comentarios_lixeira on public.comentarios;
create trigger comentarios_lixeira before delete on public.comentarios for each row execute function public.t_guarda_lixeira();
drop trigger if exists recorrentes_lixeira on public.recorrentes;
create trigger recorrentes_lixeira before delete on public.recorrentes for each row execute function public.t_guarda_lixeira();
