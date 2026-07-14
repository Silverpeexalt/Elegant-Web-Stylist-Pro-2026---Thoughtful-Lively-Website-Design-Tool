"""Дебаг проверки на тень.

Использование:
    python debug_search.py @имя_бота
    python debug_search.py имя_бота другой_бот

Показывает:
- резолвится ли юз
- что вернул contacts.Search по тушке и по полному юзу
- есть ли наш бот в этих списках
- сырые данные (limit, сколько всего пришло)
"""
from __future__ import annotations
import asyncio
import sys

import shadow_user


async def dump(client, query: str, limit: int) -> list[tuple[str, str]]:
    from telethon.tl.functions.contacts import SearchRequest
    try:
        res = await client(SearchRequest(q=query, limit=limit))
    except Exception as e:
        print(f"  [ERR] SearchRequest({query!r}) -> {e}")
        return []
    users = getattr(res, "users", []) or []
    out: list[tuple[str, str]] = []
    for u in users:
        uname = getattr(u, "username", "") or ""
        name = getattr(u, "first_name", "") or ""
        bot = " [BOT]" if getattr(u, "bot", False) else ""
        out.append((uname.lower(), f"@{uname or '(no_username)'} — {name}{bot}"))
    print(f"  SearchRequest(q={query!r}, limit={limit}) -> users={len(users)}")
    for _, line in out:
        print(f"    {line}")
    return out


async def check(client, raw: str) -> None:
    handle = raw.lstrip("@")
    tush = shadow_user._tushka(handle)
    print(f"\n=== {handle}  (тушка: {tush}) ===")

    resolved = await shadow_user._resolve_username(client, handle)
    print(f"resolve @{handle}: {'OK' if resolved else 'NOT FOUND'}")
    if not resolved:
        return

    for limit in (20, 50, 100):
        print(f"\n-- поиск по тушке '{tush}' --")
        hits = await dump(client, tush, limit)
        seen = handle.lower() in {h for h, _ in hits}
        print(f"  >>> '{handle}' в списке: {'ДА' if seen else 'НЕТ'}")
        if seen:
            break

    print(f"\n-- поиск по полному юзу '{handle}' --")
    hits = await dump(client, handle, 50)
    seen = handle.lower() in {h for h, _ in hits}
    print(f"  >>> '{handle}' в списке: {'ДА' if seen else 'НЕТ'}")


async def main() -> None:
    if len(sys.argv) < 2:
        print("Использование: python debug_search.py @имя_бота [ещё_имя]")
        sys.exit(1)

    client = await shadow_user._get_client()
    try:
        me = await client.get_me()
        print(f"Проверяем от имени: @{me.username or me.id}")
        for arg in sys.argv[1:]:
            await check(client, arg)
    finally:
        await shadow_user.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
