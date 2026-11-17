#!/usr/bin/env python3
"""生成 tests/schema_snapshot.json（init_db + 全部迁移）。"""
import contextlib
import importlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.schema_snapshot_utils import dump_schema  # noqa: E402

tmpdir = tempfile.mkdtemp(prefix='schema-snapshot-')
db_path = Path(tmpdir) / 'schema.db'
os.environ['TESTING'] = '1'
os.environ['SKIP_SECRET_KEY_CHECK'] = '1'
os.environ['DATABASE_URL'] = f'sqlite:///{db_path}'

import backend.config as config  # noqa: E402
import backend.models as models  # noqa: E402

importlib.reload(config)
importlib.reload(models)

with contextlib.redirect_stdout(io.StringIO()):
    models.init_db()
    from backend.migrations import apply_migrations

    _, _, failed = apply_migrations(verbose=False)
    if failed:
        raise SystemExit(f'migrations failed: {failed}')

snapshot = dump_schema(db_path)
out = ROOT / 'tests' / 'schema_snapshot.json'
out.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(f'wrote {out} ({len(snapshot)} objects)')
