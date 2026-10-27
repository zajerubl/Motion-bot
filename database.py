import os
import json
import base64
import logging
import aiohttp
import aiosqlite
from typing import Optional, List, Dict, Any

from config import config

logger = logging.getLogger(__name__)

DB_PATH = "bot_database.sqlite3"
BACKUP_FILE = "portfolio.json"

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
                order_index INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Ensure order_index column exists for existing dbs
        try:
            await db.execute("ALTER TABLE portfolio ADD COLUMN order_index INTEGER DEFAULT 0")
        except Exception:
            pass
        await db.commit()

    # Try restoring works from backup if DB is empty
    count = await get_works_count()
    if count == 0:
        logger.info("Database is empty, attempting to restore from backup...")
        restored = await restore_from_backup()
        if not restored and config.GITHUB_TOKEN:
            await fetch_and_restore_from_github()

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
        # Determine next order index
        async with db.execute("SELECT COALESCE(MAX(order_index), -1) + 1 FROM portfolio") as cursor:
            row = await cursor.fetchone()
            next_order = row[0] if row else 0

        cursor = await db.execute("""
            INSERT INTO portfolio (file_id, media_type, caption, order_index)
            VALUES (?, ?, ?, ?)
        """, (file_id, media_type, caption, next_order))
        await db.commit()
        work_id = cursor.lastrowid

    await save_and_sync_backup()
    return work_id

async def get_works_count() -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT COUNT(*) FROM portfolio") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

async def get_work_by_index(index: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, file_id, media_type, caption, order_index, created_at
            FROM portfolio
            ORDER BY order_index ASC, id ASC
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
            SELECT id, file_id, media_type, caption, order_index, created_at
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
            SELECT id, file_id, media_type, caption, order_index, created_at
            FROM portfolio
            ORDER BY order_index ASC, id ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def delete_work(work_id: int) -> bool:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM portfolio WHERE id = ?", (work_id,))
        await db.commit()
        deleted = cursor.rowcount > 0

    if deleted:
        await normalize_order_indices()
        await save_and_sync_backup()
    return deleted

async def normalize_order_indices():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id FROM portfolio ORDER BY order_index ASC, id ASC") as cursor:
            rows = await cursor.fetchall()
        for idx, r in enumerate(rows):
            await db.execute("UPDATE portfolio SET order_index = ? WHERE id = ?", (idx, r["id"]))
        await db.commit()

async def move_work_up(work_id: int) -> bool:
    works = await get_all_works()
    idx = next((i for i, w in enumerate(works) if w["id"] == work_id), None)
    if idx is None or idx == 0:
        return False
    prev_work = works[idx - 1]
    curr_work = works[idx]
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE portfolio SET order_index = ? WHERE id = ?", (idx - 1, curr_work["id"]))
        await db.execute("UPDATE portfolio SET order_index = ? WHERE id = ?", (idx, prev_work["id"]))
        await db.commit()
    await normalize_order_indices()
    await save_and_sync_backup()
    return True

async def move_work_down(work_id: int) -> bool:
    works = await get_all_works()
    idx = next((i for i, w in enumerate(works) if w["id"] == work_id), None)
    if idx is None or idx >= len(works) - 1:
        return False
    next_work = works[idx + 1]
    curr_work = works[idx]
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE portfolio SET order_index = ? WHERE id = ?", (idx + 1, curr_work["id"]))
        await db.execute("UPDATE portfolio SET order_index = ? WHERE id = ?", (idx, next_work["id"]))
        await db.commit()
    await normalize_order_indices()
    await save_and_sync_backup()
    return True

async def move_work_to_top(work_id: int) -> bool:
    works = await get_all_works()
    idx = next((i for i, w in enumerate(works) if w["id"] == work_id), None)
    if idx is None or idx == 0:
        return False
    target = works.pop(idx)
    works.insert(0, target)
    async with aiosqlite.connect(DB_PATH) as db:
        for i, w in enumerate(works):
            await db.execute("UPDATE portfolio SET order_index = ? WHERE id = ?", (i, w["id"]))
        await db.commit()
    await save_and_sync_backup()
    return True

async def move_work_to_bottom(work_id: int) -> bool:
    works = await get_all_works()
    idx = next((i for i, w in enumerate(works) if w["id"] == work_id), None)
    if idx is None or idx == len(works) - 1:
        return False
    target = works.pop(idx)
    works.append(target)
    async with aiosqlite.connect(DB_PATH) as db:
        for i, w in enumerate(works):
            await db.execute("UPDATE portfolio SET order_index = ? WHERE id = ?", (i, w["id"]))
        await db.commit()
    await save_and_sync_backup()
    return True

# --- Persistence and Backup ---

async def save_and_sync_backup():
    works = await get_all_works()
    data = []
    for w in works:
        data.append({
            "id": w["id"],
            "file_id": w["file_id"],
            "media_type": w["media_type"],
            "caption": w["caption"],
            "order_index": w["order_index"]
        })
    content_str = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        with open(BACKUP_FILE, "w", encoding="utf-8") as f:
            f.write(content_str)
    except Exception as e:
        logger.error(f"Error saving local backup: {e}")

    # If GitHub token is configured, sync to GitHub repository
    if config.GITHUB_TOKEN and config.GITHUB_REPO:
        try:
            await push_backup_to_github(content_str)
        except Exception as e:
            logger.error(f"Error pushing backup to GitHub: {e}")

async def restore_from_backup() -> bool:
    if not os.path.exists(BACKUP_FILE):
        return False
    try:
        with open(BACKUP_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not data:
            return False
        async with aiosqlite.connect(DB_PATH) as db:
            for item in data:
                await db.execute("""
                    INSERT INTO portfolio (id, file_id, media_type, caption, order_index)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                        file_id=excluded.file_id,
                        media_type=excluded.media_type,
                        caption=excluded.caption,
                        order_index=excluded.order_index
                """, (item["id"], item["file_id"], item["media_type"], item.get("caption", ""), item.get("order_index", 0)))
            await db.commit()
        logger.info(f"Restored {len(data)} works from local backup.")
        return True
    except Exception as e:
        logger.error(f"Failed to restore from local backup: {e}")
        return False

async def fetch_and_restore_from_github() -> bool:
    if not config.GITHUB_TOKEN or not config.GITHUB_REPO:
        return False
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/contents/{BACKUP_FILE}"
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as resp:
                if resp.status == 200:
                    info = await resp.json()
                    content_b64 = info.get("content", "")
                    content_bytes = base64.b64decode(content_b64)
                    data = json.loads(content_bytes.decode("utf-8"))
                    async with aiosqlite.connect(DB_PATH) as db:
                        for item in data:
                            await db.execute("""
                                INSERT INTO portfolio (id, file_id, media_type, caption, order_index)
                                VALUES (?, ?, ?, ?, ?)
                                ON CONFLICT(id) DO UPDATE SET
                                    file_id=excluded.file_id,
                                    media_type=excluded.media_type,
                                    caption=excluded.caption,
                                    order_index=excluded.order_index
                            """, (item["id"], item["file_id"], item["media_type"], item.get("caption", ""), item.get("order_index", 0)))
                        await db.commit()
                    logger.info(f"Restored {len(data)} works from GitHub repo backup.")
                    return True
                else:
                    logger.warning(f"GitHub backup file not found (status {resp.status}).")
    except Exception as e:
        logger.error(f"Failed to fetch backup from GitHub: {e}")
    return False

async def push_backup_to_github(content_str: str):
    url = f"https://api.github.com/repos/{config.GITHUB_REPO}/contents/{BACKUP_FILE}"
    headers = {
        "Authorization": f"Bearer {config.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json"
    }
    encoded = base64.b64encode(content_str.encode("utf-8")).decode("ascii")
    
    async with aiohttp.ClientSession() as session:
        sha = None
        # Check if file exists to get its SHA
        async with session.get(url, headers=headers) as resp:
            if resp.status == 200:
                data = await resp.json()
                sha = data.get("sha")
        
        payload = {
            "message": "Auto-sync portfolio backup [skip ci]",
            "content": encoded
        }
        if sha:
            payload["sha"] = sha
            
        async with session.put(url, headers=headers, json=payload) as resp:
            if resp.status in (200, 210, 201):
                logger.info("Successfully synced portfolio backup to GitHub.")
            else:
                text = await resp.text()
                logger.warning(f"Failed to push backup to GitHub: {resp.status} - {text}")
