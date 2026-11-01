-- Agenda cancelada: marca a demanda como cancelada (continua guardada, sai das listas de trabalho e a equipe escalada é avisada).
alter table public.demandas add column if not exists cancelada_em timestamptz;

-- Quem não criou a demanda continua só podendo mudar etapa/checklist/anexos (cancelar é de quem criou ou do admin).
create or replace function public.limita_edicao() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.atualizado_em := now();
  if public.eh_admin() or old.criado_por is not distinct from auth.uid() or auth.uid() is null then
    return new;
  end if;
  if (new.area_id, new.titulo, new.tipo, new.prazo, new.hora, new.local, new.prioridade, new.solicitante,
      new.secretaria, new.perfil, new.equipe, new.obs, new.original, new.link, new.arquivada_em, new.desarquivada_em, new.cancelada_em)
     is distinct from
     (old.area_id, old.titulo, old.tipo, old.prazo, old.hora, old.local, old.prioridade, old.solicitante,
      old.secretaria, old.perfil, old.equipe, old.obs, old.original, old.link, old.arquivada_em, old.desarquivada_em, old.cancelada_em) then
    raise exception 'Você só pode mudar etapa, checklist e anexos de demandas de outras pessoas.';
  end if;
  return new;
end $$;

-- Arquivo automático: concluída há 14 dias OU cancelada há 14 dias (a desarquivada à mão nunca volta sozinha).
create or replace function public.arquivar_antigas() returns int
language plpgsql security definer set search_path = public as $$
declare n int; hoje date := (now() at time zone 'America/Maceio')::date;
begin
  update public.demandas set arquivada_em = now()
   where arquivada_em is null and desarquivada_em is null
     and ( (status in ('Entregue', 'Postada') and coalesce(entregue, prazo) is not null and coalesce(entregue, prazo) <= hoje - 14)
        or (cancelada_em is not null and (cancelada_em at time zone 'America/Maceio')::date <= hoje - 14) );
  get diagnostics n = row_count; return n;
end $$;
revoke all on function public.arquivar_antigas() from public, anon, authenticated;

-- Aviso: quando uma agenda é cancelada, quem estava escalado recebe.
create or replace function public.t_demanda_aviso() returns trigger
language plpgsql security definer set search_path = public as $$
declare novos text[];
begin
  if tg_op = 'INSERT' then
    if coalesce(array_length(new.equipe, 1), 0) > 0 and new.recorrente_id is null and new.criado_em > now() - interval '10 minutes' then
      perform public.avisar(jsonb_build_object('tipo', 'nova', 'id', new.id));
    end if;
  else
    if new.equipe is distinct from old.equipe then
      novos := array(select unnest(new.equipe) except select unnest(old.equipe));
      if coalesce(array_length(novos, 1), 0) > 0 then perform public.avisar(jsonb_build_object('tipo', 'escala', 'id', new.id, 'novos', to_jsonb(novos))); end if;
    end if;
    if new.cancelada_em is not null and old.cancelada_em is null then
      perform public.avisar(jsonb_build_object('tipo', 'cancelada', 'id', new.id));
    end if;
  end if;
  return null;
end $$;
