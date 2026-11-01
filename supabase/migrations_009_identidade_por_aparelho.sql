-- A conta BM/FAF é compartilhada: "quem sou eu" vale por APARELHO, não por conta.
-- Cada aparelho que liga os avisos guarda o nome de quem o usa; e a demanda guarda o NOME de quem criou.
alter table public.push_subs add column if not exists nome_equipe text;
alter table public.demandas add column if not exists criado_por_nome text;

create or replace function public.t_comentario_aviso() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.fixado then
    perform public.avisar(jsonb_build_object('tipo', 'direcionamento', 'id', new.demanda_id, 'autor', new.por, 'autor_nome', new.autor));
  end if;
  return null;
end $$;

-- O aviso de teste vai só pro aparelho que acabou de ligar o sininho (e não pra todos da conta).
drop function if exists public.testar_aviso();
create or replace function public.testar_aviso(p_endpoint text default null) returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then return; end if;
  perform public.avisar(jsonb_build_object('tipo', 'teste', 'pessoa', auth.uid(), 'endpoint', p_endpoint));
end $$;
revoke all on function public.testar_aviso(text) from public, anon;
grant execute on function public.testar_aviso(text) to authenticated;
