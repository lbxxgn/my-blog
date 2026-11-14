#!/bin/bash
#
# SQLite 一致性备份脚本（使用 sqlite3 backup API，兼容 WAL 模式）
#
# 用法:
#   ./scripts/backup.sh
#   BACKUP_DIR=/path/to/backups RETENTION_DAYS=30 ./scripts/backup.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

PYTHON="${PYTHON:-python3}"
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
    PYTHON="$PROJECT_DIR/.venv/bin/python"
fi

DB_PATH="${DB_PATH:-$PROJECT_DIR/db/simple_blog.db}"
if [ -n "${DATABASE_URL:-}" ]; then
    DB_PATH="${DATABASE_URL#sqlite:///}"
fi
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUT="$BACKUP_DIR/simple_blog_${STAMP}.db"

if [ ! -f "$DB_PATH" ]; then
    echo "错误: 数据库不存在: $DB_PATH" >&2
    exit 1
fi

mkdir -p "$BACKUP_DIR"

"$PYTHON" - "$DB_PATH" "$OUT" <<'PY'
import sqlite3
import sys

source_path, target_path = sys.argv[1], sys.argv[2]
source = sqlite3.connect(source_path)
target = sqlite3.connect(target_path)
try:
    source.backup(target)
    result = target.execute('PRAGMA integrity_check').fetchone()[0]
    if result != 'ok':
        raise SystemExit(f'integrity_check failed: {result}')
finally:
    target.close()
    source.close()
PY

echo "数据库已备份: $OUT"
echo "校验通过: PRAGMA integrity_check = ok"

if [ -d "$PROJECT_DIR/static/uploads" ]; then
    UPLOADS_ARCHIVE="$BACKUP_DIR/uploads_${STAMP}.tar.gz"
    tar -czf "$UPLOADS_ARCHIVE" -C "$PROJECT_DIR/static" uploads
    echo "上传文件已备份: $UPLOADS_ARCHIVE"
fi

if [ "$RETENTION_DAYS" -gt 0 ] 2>/dev/null; then
    find "$BACKUP_DIR" -maxdepth 1 -type f \
        \( -name 'simple_blog_*.db' -o -name 'uploads_*.tar.gz' \) \
        -mtime "+$RETENTION_DAYS" -delete
    echo "已清理 $RETENTION_DAYS 天前的备份"
fi
