"""
全量备份与恢复服务

备份内容：
- SQLite 数据库一致性快照（默认 db/simple_blog.db）
- 全部上传附件（static/uploads，含原图、优化图和站点图标）

备份文件格式（ZIP）：
    manifest.json
    db/simple_blog.db
    static/uploads/...

恢复时会先校验 ZIP 结构与数据库完整性，并自动生成一份恢复前的安全备份。
"""

from __future__ import annotations

import errno
import json
import logging
import os
import shutil
import sqlite3
import stat
import tempfile
import zipfile
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import quote

import backend.config as config

logger = logging.getLogger(__name__)

BACKUP_FORMAT = 'simple-blog-backup'
BACKUP_FORMAT_VERSION = 1

MANIFEST_NAME = 'manifest.json'
DATABASE_ARCHIVE_PATH = 'db/simple_blog.db'
UPLOADS_ARCHIVE_ROOT = 'static/uploads'

BACKUP_PREFIX = 'blog_backup_'
SAFETY_PREFIX = 'pre_restore_'

# 备份/恢复 ZIP 的最大体积（同时限制解压后的总大小），默认 4GB
MAX_ARCHIVE_BYTES = int(os.environ.get('BACKUP_MAX_RESTORE_MB', '4096')) * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 200_000

_REQUIRED_TABLES = {'posts', 'users'}
_STORED_SUFFIXES = {
    '.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic', '.heif', '.ico',
}
# static/uploads 下不允许恢复的「可执行/可渲染」文件类型，避免同源 XSS
_FORBIDDEN_UPLOAD_SUFFIXES = {
    '.html', '.htm', '.xhtml', '.js', '.mjs', '.cjs', '.css', '.xml',
    '.svg', '.php', '.py', '.sh', '.bash', '.pl', '.cgi', '.exe', '.bat',
    '.cmd', '.ps1', '.jar', '.war',
}


class BackupError(RuntimeError):
    """备份或恢复过程中的可预期错误。"""


# =============================================================================
# 路径与统计
# =============================================================================

def get_backup_dir() -> Path:
    """返回备份目录（按需创建）。"""
    path = Path(config.BACKUP_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_database_path() -> Path:
    """当前数据库文件路径。"""
    return Path(config.get_db_path())


def get_uploads_dir() -> Path:
    """当前附件目录。"""
    return Path(config.UPLOAD_FOLDER)


def _dir_stats(path: Path) -> tuple[int, int]:
    """返回目录内文件数量与总字节数（忽略符号链接）。"""
    file_count = 0
    total_bytes = 0
    if not path.exists():
        return file_count, total_bytes

    for item in path.rglob('*'):
        if item.is_symlink() or not item.is_file():
            continue
        try:
            total_bytes += item.stat().st_size
        except OSError:
            continue
        file_count += 1
    return file_count, total_bytes


def get_backup_stats() -> dict[str, Any]:
    """汇总当前数据规模与备份目录状态，供后台页面展示。"""
    db_path = get_database_path()
    db_size = 0
    for candidate in (db_path, Path(f'{db_path}-wal')):
        try:
            if candidate.exists():
                db_size += candidate.stat().st_size
        except OSError:
            continue

    upload_files, upload_bytes = _dir_stats(get_uploads_dir())
    backups = list_backups()
    backup_dir = get_backup_dir()

    try:
        disk = shutil.disk_usage(backup_dir)
        disk_free = disk.free
        disk_total = disk.total
    except OSError:
        disk_free = disk_total = 0

    return {
        'db_size': db_size,
        'upload_files': upload_files,
        'upload_bytes': upload_bytes,
        'backup_count': len(backups),
        'backup_bytes': sum(item['size'] for item in backups),
        'disk_free': disk_free,
        'disk_total': disk_total,
        'backup_dir': str(backup_dir),
    }


# =============================================================================
# 备份
# =============================================================================

def _unique_archive_path(backup_dir: Path, prefix: str, timestamp: str) -> Path:
    base = f'{prefix}{timestamp}'
    candidate = backup_dir / f'{base}.zip'
    index = 1
    while candidate.exists():
        candidate = backup_dir / f'{base}_{index}.zip'
        index += 1
    return candidate


def _snapshot_database(destination: Path) -> None:
    """使用 SQLite backup API 生成一致性快照（包含 WAL 中的已提交数据）。"""
    db_path = get_database_path()
    if not db_path.exists():
        raise BackupError(f'数据库文件不存在：{db_path}')

    destination.parent.mkdir(parents=True, exist_ok=True)
    source_conn = sqlite3.connect(str(db_path), timeout=30.0)
    dest_conn = sqlite3.connect(str(destination))
    try:
        source_conn.backup(dest_conn)
        dest_conn.commit()
    except sqlite3.DatabaseError as exc:
        raise BackupError(f'数据库快照创建失败：{exc}') from exc
    finally:
        dest_conn.close()
        source_conn.close()


def _open_readonly(db_path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f'file:{quote(db_path.as_posix())}?mode=ro', uri=True)


def _database_summary(db_path: Path) -> dict[str, Any]:
    """读取快照数据库的表与迁移信息，写入 manifest 方便排查。"""
    conn = _open_readonly(db_path)
    conn.row_factory = sqlite3.Row
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name"
            )
        ]
        counts: dict[str, int] = {}
        for table in ('posts', 'users', 'categories', 'tags', 'comments'):
            if table not in tables:
                continue
            try:
                safe_table = table.replace('"', '""')
                counts[table] = conn.execute(
                    f'SELECT COUNT(*) FROM "{safe_table}"'
                ).fetchone()[0]
            except sqlite3.DatabaseError:
                continue

        migrations = []
        if 'schema_migrations' in tables:
            migrations = [
                row[0]
                for row in conn.execute(
                    'SELECT version FROM schema_migrations ORDER BY version'
                )
            ]

        info = conn.execute('PRAGMA journal_mode').fetchone()
        return {
            'tables': tables,
            'counts': counts,
            'migrations': migrations,
            'journal_mode': info[0] if info else None,
        }
    finally:
        conn.close()


def _add_uploads_to_zip(zf: zipfile.ZipFile, uploads_dir: Path) -> tuple[int, int]:
    file_count = 0
    total_bytes = 0
    if not uploads_dir.exists():
        return file_count, total_bytes

    for path in sorted(uploads_dir.rglob('*')):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue

        arcname = f'{UPLOADS_ARCHIVE_ROOT}/{path.relative_to(uploads_dir).as_posix()}'
        compress_type = (
            zipfile.ZIP_STORED
            if path.suffix.lower() in _STORED_SUFFIXES
            else zipfile.ZIP_DEFLATED
        )
        try:
            zf.write(path, arcname, compress_type=compress_type)
        except FileNotFoundError:
            # 备份期间文件被清理，跳过即可
            continue

        file_count += 1
        total_bytes += size

    return file_count, total_bytes


def create_backup_archive(prefix: str = BACKUP_PREFIX) -> tuple[Path, dict[str, Any]]:
    """
    创建全量备份 ZIP。

    Returns:
        (备份文件路径, manifest 字典)
    """
    backup_dir = get_backup_dir()
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    archive_path = _unique_archive_path(backup_dir, prefix, timestamp)

    working_dir = Path(tempfile.mkdtemp(prefix='.backup_', dir=str(backup_dir)))
    try:
        snapshot_path = working_dir / 'simple_blog.db'
        _snapshot_database(snapshot_path)
        database_summary = _database_summary(snapshot_path)

        uploads_dir = get_uploads_dir()
        upload_files, upload_bytes = _dir_stats(uploads_dir)
        manifest = {
            'format': BACKUP_FORMAT,
            'format_version': BACKUP_FORMAT_VERSION,
            'created_at': datetime.now().isoformat(timespec='seconds'),
            'site_name': config.SITE_NAME,
            'database': {
                'path': DATABASE_ARCHIVE_PATH,
                'size': snapshot_path.stat().st_size,
                **database_summary,
            },
            'uploads': {
                'path': UPLOADS_ARCHIVE_ROOT,
                'file_count': upload_files,
                'total_bytes': upload_bytes,
            },
        }

        with zipfile.ZipFile(
            archive_path,
            'w',
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
            allowZip64=True,
        ) as zf:
            zf.writestr(
                MANIFEST_NAME,
                json.dumps(manifest, ensure_ascii=False, indent=2),
                compress_type=zipfile.ZIP_DEFLATED,
            )
            zf.write(
                snapshot_path,
                DATABASE_ARCHIVE_PATH,
                compress_type=zipfile.ZIP_DEFLATED,
            )
            written_files, written_bytes = _add_uploads_to_zip(zf, uploads_dir)

        if written_files != upload_files or written_bytes != upload_bytes:
            logger.info(
                '备份期间附件目录发生变化：manifest=%s/%s，实际写入=%s/%s',
                upload_files, upload_bytes, written_files, written_bytes,
            )

        logger.info('全量备份创建成功：%s（%.2f MB）',
                    archive_path, archive_path.stat().st_size / 1024 / 1024)
        return archive_path, manifest
    except Exception:
        try:
            archive_path.unlink(missing_ok=True)
        except OSError:
            pass
        raise
    finally:
        shutil.rmtree(working_dir, ignore_errors=True)


def list_backups() -> list[dict[str, Any]]:
    """列出备份目录中由本功能生成的备份文件。"""
    backup_dir = get_backup_dir()
    items: list[dict[str, Any]] = []

    for path in backup_dir.glob('*.zip'):
        name = path.name
        if not (name.startswith(BACKUP_PREFIX) or name.startswith(SAFETY_PREFIX)):
            continue
        try:
            file_stat = path.stat()
        except OSError:
            continue
        items.append({
            'name': name,
            'size': file_stat.st_size,
            'created_at': datetime.fromtimestamp(file_stat.st_mtime),
            'kind': 'safety' if name.startswith(SAFETY_PREFIX) else 'backup',
        })

    items.sort(key=lambda item: item['created_at'], reverse=True)
    return items


def resolve_backup(name: str) -> Path:
    """根据文件名解析备份路径，拒绝目录穿越和未知文件。"""
    if not name or Path(name).name != name or not name.endswith('.zip'):
        raise BackupError('无效的备份文件名')
    if not (name.startswith(BACKUP_PREFIX) or name.startswith(SAFETY_PREFIX)):
        raise BackupError('无效的备份文件名')

    path = get_backup_dir() / name
    if not path.is_file():
        raise BackupError('备份文件不存在')
    return path


def delete_backup(name: str) -> str:
    """删除指定备份，返回文件名。"""
    path = resolve_backup(name)
    try:
        path.unlink()
    except OSError as exc:
        raise BackupError(f'删除备份失败：{exc}') from exc
    return path.name


# =============================================================================
# 恢复
# =============================================================================

def _validate_member_name(name: str, is_dir: bool = False) -> str:
    """校验 ZIP 内条目路径，并返回规范化后的路径。"""
    if not name or name.startswith('/') or '\\' in name:
        raise BackupError(f'备份包含非法路径：{name}')

    parts = PurePosixPath(name.rstrip('/')).parts
    if not parts or any(part in ('', '.', '..') for part in parts):
        raise BackupError(f'备份包含非法路径：{name}')

    normalized = '/'.join(parts)
    if normalized == MANIFEST_NAME or normalized == DATABASE_ARCHIVE_PATH:
        return normalized

    if normalized == UPLOADS_ARCHIVE_ROOT or normalized.startswith(f'{UPLOADS_ARCHIVE_ROOT}/'):
        relative = normalized[len(UPLOADS_ARCHIVE_ROOT):].lstrip('/')
        if relative and not is_dir:
            suffix = PurePosixPath(relative).suffix.lower()
            if suffix in _FORBIDDEN_UPLOAD_SUFFIXES:
                raise BackupError(f'备份包含不允许的文件类型：{name}')
        return normalized

    raise BackupError(f'备份包含未知路径：{name}')


def inspect_archive(archive_path: Path) -> dict[str, Any]:
    """校验备份 ZIP 的结构与 manifest，不写入任何数据。"""
    archive_path = Path(archive_path)
    if not archive_path.is_file():
        raise BackupError('备份文件不存在')

    size = archive_path.stat().st_size
    if size <= 0:
        raise BackupError('备份文件为空')
    if size > MAX_ARCHIVE_BYTES:
        limit_mb = MAX_ARCHIVE_BYTES // 1024 // 1024
        raise BackupError(f'备份文件过大（上限 {limit_mb} MB）')

    try:
        with zipfile.ZipFile(archive_path) as zf:
            infos = zf.infolist()
            if len(infos) > MAX_ARCHIVE_ENTRIES:
                raise BackupError('备份文件条目过多，已拒绝处理')

            total_uncompressed = 0
            names: set[str] = set()
            for info in infos:
                is_dir = info.is_dir()
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise BackupError(f'备份包含符号链接：{info.filename}')
                normalized = _validate_member_name(info.filename, is_dir=is_dir)
                total_uncompressed += info.file_size
                if is_dir:
                    continue
                if normalized in names:
                    raise BackupError(f'备份包含重复条目：{info.filename}')
                names.add(normalized)

            if total_uncompressed > MAX_ARCHIVE_BYTES:
                limit_mb = MAX_ARCHIVE_BYTES // 1024 // 1024
                raise BackupError(f'备份解压后过大（上限 {limit_mb} MB）')

            if MANIFEST_NAME not in names:
                raise BackupError('备份缺少 manifest.json，无法确认为本系统备份')
            if DATABASE_ARCHIVE_PATH not in names:
                raise BackupError('备份缺少数据库文件')

            try:
                manifest = json.loads(zf.read(MANIFEST_NAME).decode('utf-8'))
            except (ValueError, UnicodeDecodeError) as exc:
                raise BackupError('备份 manifest.json 格式错误') from exc

            if not isinstance(manifest, dict) or manifest.get('format') != BACKUP_FORMAT:
                raise BackupError('不是本系统生成的全量备份文件')
            try:
                format_version = int(manifest.get('format_version', 0))
            except (TypeError, ValueError) as exc:
                raise BackupError('备份 manifest.json 版本错误') from exc
            if format_version > BACKUP_FORMAT_VERSION:
                raise BackupError('备份版本高于当前程序，请升级后再恢复')

            upload_infos = [
                info for info in infos
                if info.filename.startswith(f'{UPLOADS_ARCHIVE_ROOT}/') and not info.is_dir()
            ]
            database_info = next(
                info for info in infos
                if not info.is_dir()
                and info.filename.rstrip('/') == DATABASE_ARCHIVE_PATH
            )
    except zipfile.BadZipFile as exc:
        raise BackupError('不是有效的 ZIP 文件') from exc
    except OSError as exc:
        raise BackupError(f'读取备份文件失败：{exc}') from exc

    return {
        'manifest': manifest,
        'size': size,
        'database_size': database_info.file_size,
        'upload_count': len(upload_infos),
        'upload_bytes': sum(info.file_size for info in upload_infos),
    }


def _validate_database_file(db_path: Path) -> None:
    """校验恢复的数据库是否完整、可读且包含必要数据表。"""
    if not db_path.exists() or db_path.stat().st_size == 0:
        raise BackupError('备份中的数据库文件为空')

    try:
        conn = _open_readonly(db_path)
    except sqlite3.DatabaseError as exc:
        raise BackupError(f'无法打开备份数据库：{exc}') from exc

    try:
        result = conn.execute('PRAGMA integrity_check').fetchone()
        if not result or result[0] != 'ok':
            detail = result[0] if result else 'unknown'
            raise BackupError(f'数据库完整性校验失败：{detail}')

        tables = {
            row[0]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
        missing = _REQUIRED_TABLES - tables
        if missing:
            raise BackupError(f'数据库缺少必要数据表：{", ".join(sorted(missing))}')
    except sqlite3.DatabaseError as exc:
        raise BackupError(f'读取备份数据库失败：{exc}') from exc
    finally:
        conn.close()


def _extract_uploads(zf: zipfile.ZipFile, destination: Path) -> int:
    """把 ZIP 中的附件安全解压到 destination。"""
    file_count = 0
    for info in zf.infolist():
        if info.filename == MANIFEST_NAME or info.filename.rstrip('/') == DATABASE_ARCHIVE_PATH:
            continue
        if info.is_dir():
            continue
        if not info.filename.startswith(f'{UPLOADS_ARCHIVE_ROOT}/'):
            continue

        relative = info.filename[len(UPLOADS_ARCHIVE_ROOT) + 1:]
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        with zf.open(info) as source, open(target, 'wb') as output:
            shutil.copyfileobj(source, output, length=1024 * 1024)
        file_count += 1
    return file_count


def _checkpoint_database(db_path: Path) -> None:
    """尽量把 WAL 写入主库，失败不影响后续恢复。"""
    try:
        conn = sqlite3.connect(str(db_path), timeout=30.0)
        try:
            conn.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        finally:
            conn.close()
    except sqlite3.DatabaseError as exc:
        logger.warning('恢复前数据库 checkpoint 失败（继续恢复）：%s', exc)


def _replace_path(source: Path, destination: Path) -> None:
    """替换文件/目录，跨文件系统时降级为复制后删除。"""
    try:
        os.replace(source, destination)
        return
    except OSError as exc:
        if exc.errno != errno.EXDEV:
            raise

    if source.is_dir():
        shutil.copytree(source, destination)
        shutil.rmtree(source, ignore_errors=True)
    else:
        shutil.copy2(source, destination)
        source.unlink()


def _remove_sqlite_sidecars(db_path: Path) -> None:
    for suffix in ('-wal', '-shm'):
        try:
            Path(f'{db_path}{suffix}').unlink()
        except FileNotFoundError:
            continue
        except OSError as exc:
            logger.warning('清理 SQLite 临时文件失败 %s：%s', suffix, exc)


def _apply_migrations() -> dict[str, Any]:
    """恢复后补齐数据库迁移，失败只记录不中断恢复。"""
    try:
        from backend.migrations import apply_migrations

        applied, skipped, failed = apply_migrations(verbose=False)
        return {
            'applied': applied,
            'skipped': skipped,
            'failed': [str(item) for item in failed],
        }
    except Exception as exc:  # noqa: BLE001 - 迁移失败需向调用方报告
        logger.exception('恢复后执行数据库迁移失败')
        return {'applied': 0, 'skipped': 0, 'failed': [str(exc)]}


def restore_backup_archive(
    archive_path: Path,
    *,
    create_safety_backup: bool = True,
) -> dict[str, Any]:
    """
    从全量备份 ZIP 恢复数据库与附件。

    恢复前会自动生成 pre_restore_*.zip 安全备份；恢复失败时尽量回滚。
    """
    archive_path = Path(archive_path)
    archive_info = inspect_archive(archive_path)

    # 工作目录放在项目根目录，通常与 db、static/uploads 在同一文件系统，
    # 这样替换目录/文件可以保持原子性；跨文件系统时自动降级为复制。
    working_dir = Path(tempfile.mkdtemp(prefix='.restore_', dir=str(config.BASE_DIR)))
    safety_backup: Path | None = None
    db_replaced = False
    uploads_dir = get_uploads_dir()
    old_uploads = working_dir / 'uploads_old'
    had_uploads = uploads_dir.exists()

    try:
        restored_db = working_dir / 'simple_blog.db'
        restored_db_size = 0
        with zipfile.ZipFile(archive_path) as zf:
            with zf.open(DATABASE_ARCHIVE_PATH) as source, open(restored_db, 'wb') as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            restored_db_size = restored_db.stat().st_size
            _validate_database_file(restored_db)

            extracted_uploads = working_dir / 'uploads'
            extracted_uploads.mkdir(parents=True, exist_ok=True)
            upload_files = _extract_uploads(zf, extracted_uploads)

        if create_safety_backup:
            safety_backup, _ = create_backup_archive(prefix=SAFETY_PREFIX)

        # 1) 替换数据库
        db_path = get_database_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        _checkpoint_database(db_path)
        _replace_path(restored_db, db_path)
        db_replaced = True
        _remove_sqlite_sidecars(db_path)

        # 2) 替换附件目录
        uploads_dir.parent.mkdir(parents=True, exist_ok=True)
        if had_uploads:
            _replace_path(uploads_dir, old_uploads)
        try:
            _replace_path(extracted_uploads, uploads_dir)
        except Exception:
            if had_uploads and old_uploads.exists():
                _replace_path(old_uploads, uploads_dir)
            if db_replaced and safety_backup:
                _rollback_database(safety_backup, db_path, working_dir)
            raise

        migrations = _apply_migrations()
        logger.info(
            '全量恢复完成：%s（附件 %s 个，大小 %.2f MB）',
            archive_path.name, upload_files, restored_db_size / 1024 / 1024,
        )
        return {
            'manifest': archive_info['manifest'],
            'database_size': restored_db_size,
            'upload_files': upload_files,
            'safety_backup': safety_backup.name if safety_backup else None,
            'migrations': migrations,
        }
    finally:
        shutil.rmtree(working_dir, ignore_errors=True)


def _rollback_database(safety_backup: Path, db_path: Path, working_dir: Path) -> None:
    """附件替换失败时，用恢复前安全备份回滚数据库。"""
    try:
        rollback_db = working_dir / 'rollback_simple_blog.db'
        with zipfile.ZipFile(safety_backup) as zf:
            with zf.open(DATABASE_ARCHIVE_PATH) as source, open(rollback_db, 'wb') as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)

        _validate_database_file(rollback_db)
        _checkpoint_database(db_path)
        _replace_path(rollback_db, db_path)
        _remove_sqlite_sidecars(db_path)
        logger.warning('附件恢复失败，数据库已从安全备份回滚：%s', safety_backup.name)
    except Exception:  # noqa: BLE001 - 回滚失败只能记录
        logger.exception('数据库回滚失败，请手动使用安全备份恢复')
