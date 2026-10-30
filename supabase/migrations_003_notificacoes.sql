-- Notificações no celular + recorrentes criadas no servidor (sem ninguém abrir o app).
create extension if not exists pg_net;
create extension if not exists pg_cron;

-- Guarda o endereço e o segredo da função de avisos (inseridos fora do repositório). Ninguém lê pela API.
create table if not exists public.config_interna (chave text primary key, valor text not null);
alter table public.config_interna enable row level security;
revoke all on public.config_interna from anon, authenticated;

-- Registro dos avisos enviados (o admin consegue conferir o que saiu).
create table if not exists public.push_log (
  id bigserial primary key, em timestamptz not null default now(), tipo text not null, demanda_id text,
  destinatarios int not null default 0, enviados int not null default 0, simulado boolean not null default false, detalhe jsonb
);
alter table public.push_log enable row level security;
drop policy if exists push_log_admin on public.push_log;
create policy push_log_admin on public.push_log for select to authenticated using (public.eh_admin());

-- Chama a função de avisos. Se der qualquer erro, a gravação da demanda NÃO é afetada.
create or replace function public.avisar(payload jsonb) returns void
language plpgsql security definer set search_path = public as $$
declare u text; s text;
begin
  select valor into u from public.config_interna where chave = 'push_url';
  select valor into s from public.config_interna where chave = 'push_secret';
  if u is null or s is null then return; end if;
  perform net.http_post(url := u, headers := jsonb_build_object('Content-Type', 'application/json', 'x-push-secret', s), body := payload);
exception when others then null;
end $$;
revoke all on function public.avisar(jsonb) from public, anon, authenticated;

create or replace function public.t_demanda_aviso() returns trigger
language plpgsql security definer set search_path = public as $$
declare novos text[];
begin
  if tg_op = 'INSERT' then
    -- só demandas novas de verdade (dados importados e recorrentes não geram aviso: as recorrentes entram no resumo do dia)
    if coalesce(array_length(new.equipe, 1), 0) > 0 and new.recorrente_id is null and new.criado_em > now() - interval '10 minutes' then
      perform public.avisar(jsonb_build_object('tipo', 'nova', 'id', new.id));
    end if;
  elsif new.equipe is distinct from old.equipe then
    novos := array(select unnest(new.equipe) except select unnest(old.equipe));
    if coalesce(array_length(novos, 1), 0) > 0 then perform public.avisar(jsonb_build_object('tipo', 'escala', 'id', new.id, 'novos', to_jsonb(novos))); end if;
  end if;
  return null;
end $$;
drop trigger if exists demandas_aviso on public.demandas;
create trigger demandas_aviso after insert or update on public.demandas for each row execute function public.t_demanda_aviso();

create or replace function public.t_comentario_aviso() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if new.fixado then perform public.avisar(jsonb_build_object('tipo', 'direcionamento', 'id', new.demanda_id, 'autor', new.por)); end if;
  return null;
end $$;
drop trigger if exists comentarios_aviso on public.comentarios;
create trigger comentarios_aviso after insert on public.comentarios for each row execute function public.t_comentario_aviso();

-- Cria as demandas das recorrentes dos próximos 7 dias (mesma regra do painel; não duplica).
create or replace function public.gerar_recorrentes() returns int
language plpgsql security definer set search_path = public as $$
declare r record; d date; hoje date := (now() at time zone 'America/Maceio')::date; fim date := hoje + 7; ini date; n int := 0; novo int;
begin
  for r in select * from public.recorrentes where ativo loop
    ini := case when r.ultimo_gerado is not null and r.ultimo_gerado >= hoje then r.ultimo_gerado + 1 else hoje end;
    if ini > fim then continue; end if;
    for d in select g::date from generate_series(ini, fim, interval '1 day') g loop
      if (r.freq = 'semanal' and extract(dow from d)::int = any(r.dias))
         or (r.freq = 'mensal' and extract(day from d)::int = least(r.dia, extract(day from (date_trunc('month', d) + interval '1 month' - interval '1 day'))::int)) then
        insert into public.demandas (id, area_id, titulo, tipo, prazo, hora, local, status, prioridade, secretaria, perfil, equipe, checklist, criado, recorrente_id, historico)
        values ('r' || r.id || to_char(d, 'YYYYMMDD'), r.area_id, r.titulo, coalesce(r.tipo, 'Outro'), d, r.hora, r.local, 'A fazer',
                case when r.prioridade in ('Baixa', 'Média', 'Alta') then r.prioridade else 'Média' end, r.secretaria, r.perfil, r.equipe,
                (select coalesce(jsonb_agg(jsonb_build_object('t', c, 'ok', false)), '[]'::jsonb) from jsonb_array_elements_text(r.checklist) c), hoje, r.id,
                jsonb_build_array(jsonb_build_object('em', (extract(epoch from now()) * 1000)::bigint, 'txt', 'Criada automaticamente (recorrente)')))
        on conflict (id) do nothing;
        get diagnostics novo = row_count; n := n + novo;
      end if;
    end loop;
    update public.recorrentes set ultimo_gerado = fim where id = r.id;
  end loop;
  return n;
end $$;
revoke all on function public.gerar_recorrentes() from public, anon, authenticated;

-- Agenda diária (horário de Maceió = UTC-3): 05h cria as recorrentes, 08h manda o resumo do dia.
select cron.unschedule(jobid) from cron.job where jobname in ('demando-recorrentes', 'demando-resumo');
select cron.schedule('demando-recorrentes', '0 8 * * *', $$select public.gerar_recorrentes()$$);
select cron.schedule('demando-resumo', '0 11 * * *', $$select public.avisar(jsonb_build_object('tipo', 'resumo'))$$);
