-- Cada pessoa só pode mudar o próprio NOME e o próprio "nome na equipe" (que tem de existir na equipe de uma área dela).
-- Papel, acesso ativo, usuário e e-mail só o admin muda. (Antes, uma pessoa desativada conseguia se reativar sozinha.)
create or replace function public.limita_pessoa() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null or public.eh_admin() then return new; end if;     -- admin e servidor mudam tudo
  new.id := old.id; new.papel := old.papel; new.ativo := old.ativo; new.email := old.email; new.usuario := old.usuario; new.criado_em := old.criado_em;
  new.nome := left(btrim(coalesce(nullif(new.nome, ''), old.nome)), 60);
  if new.nome_equipe is distinct from old.nome_equipe and new.nome_equipe is not null then
    if not exists (select 1 from public.acessos x join public.areas a on a.id = x.area_id where x.pessoa_id = old.id and new.nome_equipe = any(a.equipe)) then
      raise exception 'Escolha um nome da equipe da sua área.' using errcode = 'P0001';
    end if;
  end if;
  return new;
end $$;
drop trigger if exists pessoas_limita on public.pessoas;
create trigger pessoas_limita before update on public.pessoas for each row execute function public.limita_pessoa();
