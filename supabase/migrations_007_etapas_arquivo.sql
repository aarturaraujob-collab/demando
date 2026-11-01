-- Novas etapas (Ajustes e Postada) e arquivo das demandas concluídas.
alter table public.demandas drop constraint if exists demandas_status_check;
alter table public.demandas add constraint demandas_status_check
  check (status in ('A fazer', 'Em produção', 'Ajustes', 'Entregue', 'Postada'));

-- Arquivada = concluída que saiu do dia a dia (continua no banco, no calendário e nos relatórios).
alter table public.demandas add column if not exists arquivada_em timestamptz;
create index if not exists demandas_arquivada on public.demandas (arquivada_em) where arquivada_em is not null;

-- Só admin ou quem criou a demanda arquiva/desarquiva (os demais só mudam etapa, checklist e anexos).
create or replace function public.limita_edicao() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  new.atualizado_em := now();
  if public.eh_admin() or old.criado_por is not distinct from auth.uid() or auth.uid() is null then
    return new;
  end if;
  if (new.area_id, new.titulo, new.tipo, new.prazo, new.hora, new.local, new.prioridade, new.solicitante,
      new.secretaria, new.perfil, new.equipe, new.obs, new.original, new.link, new.arquivada_em)
     is distinct from
     (old.area_id, old.titulo, old.tipo, old.prazo, old.hora, old.local, old.prioridade, old.solicitante,
      old.secretaria, old.perfil, old.equipe, old.obs, old.original, old.link, old.arquivada_em) then
    raise exception 'Você só pode mudar etapa, checklist e anexos de demandas de outras pessoas.';
  end if;
  return new;
end $$;

-- Arquiva sozinha: concluída (Entregue ou Postada) há 14 dias ou mais. Roda todo dia às 5h30 de Maceió.
create or replace function public.arquivar_antigas() returns int
language plpgsql security definer set search_path = public as $$
declare n int;
begin
  update public.demandas set arquivada_em = now()
   where arquivada_em is null and status in ('Entregue', 'Postada') and coalesce(entregue, prazo) is not null
     and coalesce(entregue, prazo) <= (now() at time zone 'America/Maceio')::date - 14;
  get diagnostics n = row_count; return n;
end $$;
revoke all on function public.arquivar_antigas() from public, anon, authenticated;
select cron.unschedule(jobid) from cron.job where jobname = 'demando-arquivar';
select cron.schedule('demando-arquivar', '30 8 * * *', $$select public.arquivar_antigas()$$);
