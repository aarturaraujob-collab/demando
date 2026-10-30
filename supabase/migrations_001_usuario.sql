-- Guarda o "usuário" (o que a pessoa digita no login) e preenche sozinho ao criar a conta.
alter table public.pessoas add column if not exists usuario text;
create unique index if not exists pessoas_usuario_key on public.pessoas (usuario);

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
