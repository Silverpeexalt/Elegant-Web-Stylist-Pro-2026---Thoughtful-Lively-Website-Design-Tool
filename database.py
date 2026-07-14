from __future__ import annotations
import aiosqlite
from datetime import datetime, timedelta
from typing import Any, Optional

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS templates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_admin_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    first_text TEXT,
    first_photo_path TEXT,
    first_button_text TEXT,
    first_button_url TEXT,
    mailing_enabled INTEGER DEFAULT 0,
    mailing_text TEXT,
    mailing_photo_path TEXT,
    mailing_interval_minutes INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS bots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_admin_id INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    tg_bot_id INTEGER,
    username TEXT,
    full_name TEXT,
    template_id INTEGER NOT NULL,
    is_alive INTEGER DEFAULT 1,
    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    silent_until TIMESTAMP,
    FOREIGN KEY (template_id) REFERENCES templates(id)
);

CREATE TABLE IF NOT EXISTS bot_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bot_id INTEGER NOT NULL,
    tg_user_id INTEGER NOT NULL,
    username TEXT,
    first_name TEXT,
    language_code TEXT,
    geo TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(bot_id, tg_user_id),
    FOREIGN KEY (bot_id) REFERENCES bots(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS report_bots (
    admin_id INTEGER PRIMARY KEY,
    token TEXT NOT NULL,
    chat_id INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_templates_owner ON templates(owner_admin_id);
CREATE INDEX IF NOT EXISTS idx_bots_owner ON bots(owner_admin_id);
CREATE INDEX IF NOT EXISTS idx_bot_users_bot ON bot_users(bot_id);
CREATE INDEX IF NOT EXISTS idx_bot_users_started ON bot_users(bot_id, started_at);
CREATE INDEX IF NOT EXISTS idx_bot_users_geo ON bot_users(bot_id, geo);
"""


SILENT_MINUTES_AFTER_ADD = 40


async def init() -> None:
    async with aiosqlite.connect(config.DB_PATH) as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.executescript(SCHEMA)
        cur = await db.execute("PRAGMA table_info(bots)")
        cols = {row[1] for row in await cur.fetchall()}
        if "silent_until" not in cols:
            await db.execute("ALTER TABLE bots ADD COLUMN silent_until TIMESTAMP")
        await db.commit()


def _conn():
    conn = aiosqlite.connect(config.DB_PATH)
    return conn


async def _open():
    db = await _conn()
    await db.execute("PRAGMA foreign_keys = ON")
    return db


# ---------- templates ----------

async def create_template(
    owner_admin_id: int,
    name: str,
    first_text: Optional[str],
    first_photo_path: Optional[str],
    first_button_text: Optional[str],
    first_button_url: Optional[str],
    mailing_enabled: bool,
    mailing_text: Optional[str],
    mailing_photo_path: Optional[str],
    mailing_interval_minutes: Optional[int],
) -> int:
    async with _conn() as db:
        cur = await db.execute(
            """INSERT INTO templates
               (owner_admin_id, name, first_text, first_photo_path, first_button_text, first_button_url,
                mailing_enabled, mailing_text, mailing_photo_path, mailing_interval_minutes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                owner_admin_id, name, first_text, first_photo_path, first_button_text, first_button_url,
                int(mailing_enabled), mailing_text, mailing_photo_path, mailing_interval_minutes,
            ),
        )
        await db.commit()
        return cur.lastrowid


async def list_templates(owner_admin_id: int) -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM templates WHERE owner_admin_id = ? ORDER BY id DESC",
            (owner_admin_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def get_template(template_id: int) -> Optional[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM templates WHERE id = ?", (template_id,))
        r = await cur.fetchone()
        return dict(r) if r else None


async def bulk_update_button_url(owner_admin_id: int, new_url: str) -> int:
    """Меняет first_button_url во всех шаблонах владельца, у которых уже есть
    кнопка (задан first_button_text). Возвращает число обновлённых строк."""
    async with _conn() as db:
        cur = await db.execute(
            """UPDATE templates
               SET first_button_url = ?
               WHERE owner_admin_id = ?
                 AND first_button_text IS NOT NULL
                 AND first_button_text != ''""",
            (new_url, owner_admin_id),
        )
        await db.commit()
        return cur.rowcount


async def delete_template(template_id: int, owner_admin_id: int) -> None:
    async with _conn() as db:
        await db.execute(
            "DELETE FROM templates WHERE id = ? AND owner_admin_id = ?",
            (template_id, owner_admin_id),
        )
        await db.commit()


async def update_template_fields(template_id: int, owner_admin_id: int, **fields: Any) -> None:
    """Обновляет любые поля шаблона владельца. Ключи — реальные имена колонок."""
    if not fields:
        return
    allowed = {
        "first_text", "first_photo_path", "first_button_text", "first_button_url",
        "mailing_enabled", "mailing_text", "mailing_photo_path", "mailing_interval_minutes",
    }
    safe = {k: v for k, v in fields.items() if k in allowed}
    if not safe:
        return
    sets = ", ".join(f"{k} = ?" for k in safe)
    params = list(safe.values()) + [template_id, owner_admin_id]
    async with _conn() as db:
        await db.execute(
            f"UPDATE templates SET {sets} WHERE id = ? AND owner_admin_id = ?",
            params,
        )
        await db.commit()


async def bots_using_template(template_id: int) -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM bots WHERE template_id = ? AND is_alive = 1",
            (template_id,),
        )
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def update_bot_template(bot_id: int, owner_admin_id: int, template_id: int) -> bool:
    async with _conn() as db:
        cur = await db.execute(
            "UPDATE bots SET template_id = ? WHERE id = ? AND owner_admin_id = ?",
            (template_id, bot_id, owner_admin_id),
        )
        await db.commit()
        return cur.rowcount > 0


# ---------- bots (workers) ----------

async def add_bot(
    owner_admin_id: int,
    token: str,
    tg_bot_id: int,
    username: str,
    full_name: str,
    template_id: int,
    silent_minutes: int = SILENT_MINUTES_AFTER_ADD,
) -> int:
    silent_until = (
        (datetime.utcnow() + timedelta(minutes=silent_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        if silent_minutes > 0
        else None
    )
    async with _conn() as db:
        cur = await db.execute(
            """INSERT INTO bots (owner_admin_id, token, tg_bot_id, username, full_name,
                                 template_id, is_alive, silent_until)
               VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
            (owner_admin_id, token, tg_bot_id, username, full_name, template_id, silent_until),
        )
        await db.commit()
        return cur.lastrowid


async def is_bot_silent(bot_id: int) -> bool:
    async with _conn() as db:
        cur = await db.execute("SELECT silent_until FROM bots WHERE id = ?", (bot_id,))
        row = await cur.fetchone()
    if not row or not row[0]:
        return False
    try:
        until = datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S")
    except (TypeError, ValueError):
        return False
    return datetime.utcnow() < until


async def get_bot(bot_id: int) -> Optional[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM bots WHERE id = ?", (bot_id,))
        r = await cur.fetchone()
        return dict(r) if r else None


async def get_bot_by_tg_id(tg_bot_id: int) -> Optional[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM bots WHERE tg_bot_id = ?", (tg_bot_id,))
        r = await cur.fetchone()
        return dict(r) if r else None


async def get_bot_by_token(token: str) -> Optional[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM bots WHERE token = ?", (token,))
        r = await cur.fetchone()
        return dict(r) if r else None


async def list_bots(
    owner_admin_id: Optional[int] = None,
    alive_only: bool = False,
) -> list[dict[str, Any]]:
    q = "SELECT * FROM bots"
    where = []
    params: list[Any] = []
    if owner_admin_id is not None:
        where.append("owner_admin_id = ?")
        params.append(owner_admin_id)
    if alive_only:
        where.append("is_alive = 1")
    if where:
        q += " WHERE " + " AND ".join(where)
    q += " ORDER BY id DESC"
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(q, params)
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def mark_bot_dead(bot_id: int) -> None:
    async with _conn() as db:
        await db.execute("UPDATE bots SET is_alive = 0 WHERE id = ?", (bot_id,))
        await db.commit()


async def delete_bot(bot_id: int, owner_admin_id: int) -> None:
    async with _conn() as db:
        await db.execute("PRAGMA foreign_keys = ON")
        await db.execute(
            "DELETE FROM bot_users WHERE bot_id = ? AND bot_id IN (SELECT id FROM bots WHERE owner_admin_id = ?)",
            (bot_id, owner_admin_id),
        )
        await db.execute(
            "DELETE FROM bots WHERE id = ? AND owner_admin_id = ?",
            (bot_id, owner_admin_id),
        )
        await db.commit()


async def delete_bot_user(bot_id: int, tg_user_id: int) -> None:
    async with _conn() as db:
        await db.execute(
            "DELETE FROM bot_users WHERE bot_id = ? AND tg_user_id = ?",
            (bot_id, tg_user_id),
        )
        await db.commit()


# ---------- bot_users ----------

async def record_bot_user(
    bot_id: int,
    tg_user_id: int,
    username: Optional[str],
    first_name: Optional[str],
    language_code: Optional[str],
    geo: str,
) -> bool:
    async with _conn() as db:
        cur = await db.execute(
            """INSERT OR IGNORE INTO bot_users
               (bot_id, tg_user_id, username, first_name, language_code, geo)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (bot_id, tg_user_id, username, first_name, language_code, geo),
        )
        await db.commit()
        return cur.rowcount > 0


async def get_bot_users(bot_id: int) -> list[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM bot_users WHERE bot_id = ?", (bot_id,))
        rows = await cur.fetchall()
        return [dict(r) for r in rows]


async def count_bot_users(bot_id: int) -> int:
    async with _conn() as db:
        cur = await db.execute("SELECT COUNT(*) FROM bot_users WHERE bot_id = ?", (bot_id,))
        (n,) = await cur.fetchone()
        return int(n)


async def geo_breakdown_for_bot(bot_id: int) -> list[tuple[str, int]]:
    async with _conn() as db:
        cur = await db.execute(
            "SELECT geo, COUNT(*) FROM bot_users WHERE bot_id = ? GROUP BY geo ORDER BY 2 DESC",
            (bot_id,),
        )
        return [(g, int(c)) for g, c in await cur.fetchall()]


# ---------- per-admin aggregate stats ----------

async def total_users_for_admin(admin_id: int) -> int:
    async with _conn() as db:
        cur = await db.execute(
            """SELECT COUNT(*) FROM bot_users
               WHERE bot_id IN (SELECT id FROM bots WHERE owner_admin_id = ?)""",
            (admin_id,),
        )
        (n,) = await cur.fetchone()
        return int(n)


async def users_since_for_admin(admin_id: int, hours_ago: int) -> int:
    since = (datetime.utcnow() - timedelta(hours=hours_ago)).strftime("%Y-%m-%d %H:%M:%S")
    async with _conn() as db:
        cur = await db.execute(
            """SELECT COUNT(*) FROM bot_users
               WHERE started_at >= ?
                 AND bot_id IN (SELECT id FROM bots WHERE owner_admin_id = ?)""",
            (since, admin_id),
        )
        (n,) = await cur.fetchone()
        return int(n)


async def geo_breakdown_for_admin(admin_id: int) -> list[tuple[str, int]]:
    async with _conn() as db:
        cur = await db.execute(
            """SELECT geo, COUNT(*) FROM bot_users
               WHERE bot_id IN (SELECT id FROM bots WHERE owner_admin_id = ?)
               GROUP BY geo ORDER BY 2 DESC""",
            (admin_id,),
        )
        return [(g, int(c)) for g, c in await cur.fetchall()]


# ---------- report bots (per-admin) ----------

async def set_report_bot(admin_id: int, token: str, chat_id: int) -> None:
    async with _conn() as db:
        await db.execute(
            """INSERT INTO report_bots (admin_id, token, chat_id) VALUES (?, ?, ?)
               ON CONFLICT(admin_id) DO UPDATE SET token=excluded.token, chat_id=excluded.chat_id""",
            (admin_id, token, chat_id),
        )
        await db.commit()


async def get_report_bot(admin_id: int) -> Optional[dict[str, Any]]:
    async with _conn() as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM report_bots WHERE admin_id = ?", (admin_id,))
        r = await cur.fetchone()
        return dict(r) if r else None
