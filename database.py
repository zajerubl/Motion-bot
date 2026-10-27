import aiosqlite
from typing import Optional, List, Dict, Any

DB_PATH = "bot_database.sqlite3"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS portfolio (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                file_id TEXT NOT NULL,
                media_type TEXT NOT NULL,
                caption TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def add_user(user_id: int, username: Optional[str], first_name: Optional[str]):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO users (user_id, username, first_name)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                first_name=excluded.first_name
        """, (user_id, username, first_name))
        await db.commit()

async def get_users_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM users") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def add_work(file_id: str, media_type: str, caption: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO portfolio (file_id, media_type, caption)
            VALUES (?, ?, ?)
        """, (file_id, media_type, caption))
        await db.commit()
        return cursor.lastrowid

async def get_works_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM portfolio") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_work_by_index(index: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, file_id, media_type, caption, created_at
            FROM portfolio
            ORDER BY id ASC
            LIMIT 1 OFFSET ?
        """, (index,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def get_work_by_id(work_id: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, file_id, media_type, caption, created_at
            FROM portfolio
            WHERE id = ?
        """, (work_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return dict(row)
            return None

async def get_all_works() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, file_id, media_type, caption, created_at
            FROM portfolio
            ORDER BY id ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def delete_work(work_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM portfolio WHERE id = ?", (work_id,))
        await db.commit()
        return cursor.rowcount > 0
