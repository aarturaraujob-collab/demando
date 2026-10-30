-- Ao ligar o sininho, a pessoa recebe uma notificação de teste (só pros aparelhos dela).
create or replace function public.testar_aviso() returns void
language plpgsql security definer set search_path = public as $$
begin
  if auth.uid() is null then return; end if;
  perform public.avisar(jsonb_build_object('tipo', 'teste', 'pessoa', auth.uid()));
end $$;
revoke all on function public.testar_aviso() from public, anon;
grant execute on function public.testar_aviso() to authenticated;
