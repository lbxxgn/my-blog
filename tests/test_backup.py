"""全量备份与恢复功能测试。"""

import io
import re
import sqlite3
import zipfile
from pathlib import Path

import pytest

import backend.config as config
from backend.services import backup as backup_service


@pytest.fixture
def backup_env(tmp_path, monkeypatch, temp_db):
    """把备份目录和附件目录指向临时路径，避免污染真实数据。"""
    uploads = tmp_path / 'uploads'
    (uploads / 'images').mkdir(parents=True)
    (uploads / 'images' / 'sample.jpg').write_bytes(b'jpeg-data')

    backups = tmp_path / 'backups'
    backups.mkdir()

    monkeypatch.setattr(config, 'UPLOAD_FOLDER', uploads)
    monkeypatch.setattr(config, 'BACKUP_DIR', backups)
    monkeypatch.setattr(
        backup_service,
        '_apply_migrations',
        lambda: {'applied': 0, 'skipped': 0, 'failed': []},
    )

    return {
        'db_path': Path(config.get_db_path()),
        'uploads': uploads,
        'backups': backups,
    }


def _login(client, user):
    return client.post('/login', data={
        'username': user['username'],
        'password': user['password'],
    })


def test_backup_page_requires_admin(client, test_user):
    response = _login(client, test_user)
    assert response.status_code in (302, 303)

    response = client.get('/admin/backup')
    assert response.status_code in (302, 303)


def test_create_download_and_delete_backup(client, test_admin_user, backup_env):
    _login(client, test_admin_user)

    response = client.get('/admin/backup')
    assert response.status_code == 200
    assert '备份与恢复' in response.get_data(as_text=True)

    response = client.post('/admin/backup/create', follow_redirects=True)
    assert response.status_code == 200

    archives = list(backup_env['backups'].glob('blog_backup_*.zip'))
    assert len(archives) == 1
    archive = archives[0]

    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert 'manifest.json' in names
    assert 'db/simple_blog.db' in names
    assert 'static/uploads/images/sample.jpg' in names

    response = client.get(f'/admin/backup/download/{archive.name}')
    assert response.status_code == 200
    assert response.data[:2] == b'PK'

    response = client.post('/admin/backup/delete', data={'name': archive.name},
                           follow_redirects=True)
    assert response.status_code == 200
    assert not archive.exists()


def test_restore_uploaded_backup(client, test_admin_user, backup_env):
    _login(client, test_admin_user)

    archive, _ = backup_service.create_backup_archive()

    conn = sqlite3.connect(backup_env['db_path'])
    conn.execute(
        "INSERT INTO posts (title, content, is_published) VALUES (?, ?, 1)",
        ('after backup', 'should be removed'),
    )
    conn.commit()
    conn.close()
    (backup_env['uploads'] / 'images' / 'later.jpg').write_bytes(b'later')

    archive_bytes = archive.read_bytes()
    response = client.post(
        '/admin/backup/restore',
        data={
            'confirm': 'RESTORE',
            'backup_file': (io.BytesIO(archive_bytes), 'restore.zip'),
        },
        content_type='multipart/form-data',
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert '恢复完成' in response.get_data(as_text=True)

    conn = sqlite3.connect(backup_env['db_path'])
    try:
        rows = conn.execute('SELECT title FROM posts').fetchall()
    finally:
        conn.close()
    assert all(row[0] != 'after backup' for row in rows)

    assert not (backup_env['uploads'] / 'images' / 'later.jpg').exists()
    assert (backup_env['uploads'] / 'images' / 'sample.jpg').exists()

    safety = list(backup_env['backups'].glob('pre_restore_*.zip'))
    assert safety


def test_restore_requires_confirmation(client, test_admin_user, backup_env):
    _login(client, test_admin_user)
    archive, _ = backup_service.create_backup_archive()

    response = client.post(
        '/admin/backup/restore',
        data={'backup_name': archive.name, 'confirm': 'nope'},
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert '请输入 RESTORE' in response.get_data(as_text=True)


def test_restore_endpoint_manually_validates_csrf(csrf_client, test_admin_user, backup_env):
    login_page = csrf_client.get('/login')
    token = re.search(
        r'name="csrf_token" value="([^"]+)"',
        login_page.get_data(as_text=True),
    ).group(1)
    csrf_client.post('/login', data={
        'username': test_admin_user['username'],
        'password': test_admin_user['password'],
        'csrf_token': token,
    })

    archive, _ = backup_service.create_backup_archive()
    response = csrf_client.post(
        '/admin/backup/restore',
        data={'backup_name': archive.name, 'confirm': 'RESTORE'},
    )
    assert response.status_code == 302

    page = csrf_client.get('/admin/backup')
    assert 'CSRF 校验失败' in page.get_data(as_text=True)
    assert archive.exists()

    token = re.search(
        r'name="csrf_token" value="([^"]+)"',
        page.get_data(as_text=True),
    ).group(1)
    response = csrf_client.post(
        '/admin/backup/restore',
        data={
            'backup_name': archive.name,
            'confirm': 'RESTORE',
            'csrf_token': token,
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert '恢复完成' in response.get_data(as_text=True)


def test_archive_rejects_path_traversal(tmp_path):
    bad_archive = tmp_path / 'bad.zip'
    with zipfile.ZipFile(bad_archive, 'w') as zf:
        zf.writestr('../evil.txt', 'x')

    with pytest.raises(backup_service.BackupError):
        backup_service.inspect_archive(bad_archive)


def test_archive_rejects_active_content_uploads(tmp_path):
    bad_archive = tmp_path / 'bad.html.zip'
    with zipfile.ZipFile(bad_archive, 'w') as zf:
        zf.writestr(
            'manifest.json',
            '{"format": "simple-blog-backup", "format_version": 1}',
        )
        zf.writestr('db/simple_blog.db', b'not-a-db')
        zf.writestr('static/uploads/evil.html', '<script>alert(1)</script>')

    with pytest.raises(backup_service.BackupError):
        backup_service.inspect_archive(bad_archive)


def test_restore_rejects_database_without_required_tables(tmp_path):
    archive = tmp_path / 'empty-db.zip'
    db_path = tmp_path / 'empty.db'
    conn = sqlite3.connect(db_path)
    conn.execute('CREATE TABLE something (id INTEGER)')
    conn.commit()
    conn.close()

    with zipfile.ZipFile(archive, 'w') as zf:
        zf.writestr(
            'manifest.json',
            '{"format": "simple-blog-backup", "format_version": 1}',
        )
        zf.write(db_path, 'db/simple_blog.db')

    with pytest.raises(backup_service.BackupError):
        backup_service.restore_backup_archive(archive, create_safety_backup=False)
