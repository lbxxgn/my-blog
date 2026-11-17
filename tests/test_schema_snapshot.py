"""迁移后的数据库 schema 必须与快照一致；新增迁移需同步更新快照。"""
import json
from pathlib import Path

from tests.schema_snapshot_utils import dump_schema

SNAPSHOT = Path(__file__).resolve().parent / 'schema_snapshot.json'


def test_schema_matches_snapshot(schema_template):
    expected = json.loads(SNAPSHOT.read_text(encoding='utf-8'))
    assert dump_schema(schema_template) == expected
