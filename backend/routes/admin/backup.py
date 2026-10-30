"""全量备份与恢复（admin 蓝图子模块）。"""

import logging
import os
import shlex
import subprocess
import tempfile
from pathlib import Path

from flask import (
    abort,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_wtf.csrf import validate_csrf
from werkzeug.exceptions import RequestEntityTooLarge
from wtforms.validators import ValidationError

from auth_decorators import admin_required
from logger import log_error, log_operation
from backend.services import backup as backup_service

from . import admin_bp

logger = logging.getLogger(__name__)


@admin_bp.route('/backup')
@admin_required
def backup_page():
    """备份与恢复页面。"""
    try:
        stats = backup_service.get_backup_stats()
        backups = backup_service.list_backups()
        schedule = backup_service.get_schedule_status()
    except Exception as exc:  # noqa: BLE001 - 页面仍应可打开
        logger.exception('读取备份信息失败')
        log_error(exc, context='读取备份信息', user_id=session.get('user_id'))
        stats = {
            'db_size': 0,
            'upload_files': 0,
            'upload_bytes': 0,
            'backup_count': 0,
            'backup_bytes': 0,
            'disk_free': 0,
            'disk_total': 0,
            'backup_dir': '',
        }
        backups = []
        schedule = {
            'enabled': False,
            'interval_days': 7,
            'retention_count': 5,
            'scheduled_count': 0,
            'last_backup_at': None,
            'next_due_at': None,
            'is_due': False,
        }

    return render_template(
        'admin/backup.html',
        stats=stats,
        backups=backups,
        schedule=schedule,
        max_restore_mb=backup_service.MAX_ARCHIVE_BYTES // 1024 // 1024,
    )


@admin_bp.route('/backup/create', methods=['POST'])
@admin_required
def create_backup():
    """在后台线程创建全量备份，避免同步请求被 nginx 超时。"""
    try:
        job_id = backup_service.start_backup_job()
        log_operation(
            session.get('user_id'),
            session.get('username'),
            '创建全量备份',
            f'后台任务 {job_id}',
        )
        flash('备份任务已开始，页面会自动显示进度。', 'success')
        return redirect(url_for('admin.backup_page', job_id=job_id))
    except Exception as exc:  # noqa: BLE001
        logger.exception('启动备份任务失败')
        flash(f'备份失败：{exc}', 'error')
        log_error(exc, context='创建全量备份', user_id=session.get('user_id'))
        return redirect(url_for('admin.backup_page'))


@admin_bp.route('/backup/job/<job_id>')
@admin_required
def backup_job_status(job_id):
    job = backup_service.get_backup_job(job_id)
    if not job:
        return {'success': False, 'error': '任务不存在'}, 404
    return {'success': True, 'job': job}


@admin_bp.route('/backup/download/<name>')
@admin_required
def download_backup(name):
    """下载指定备份文件。"""
    try:
        archive_path = backup_service.resolve_backup(name)
    except backup_service.BackupError:
        abort(404)

    log_operation(
        session.get('user_id'),
        session.get('username'),
        '下载全量备份',
        archive_path.name,
    )
    return send_file(
        str(archive_path),
        mimetype='application/zip',
        as_attachment=True,
        download_name=archive_path.name,
    )


@admin_bp.route('/backup/delete', methods=['POST'])
@admin_required
def delete_backup():
    """删除指定备份文件。"""
    name = (request.form.get('name') or '').strip()
    try:
        deleted = backup_service.delete_backup(name)
        log_operation(
            session.get('user_id'),
            session.get('username'),
            '删除全量备份',
            deleted,
        )
        flash(f'已删除备份：{deleted}', 'success')
    except backup_service.BackupError as exc:
        flash(f'删除失败：{exc}', 'error')
    except Exception as exc:  # noqa: BLE001
        logger.exception('删除备份失败')
        flash(f'删除失败：{exc}', 'error')
        log_error(exc, context='删除全量备份', user_id=session.get('user_id'))

    return redirect(url_for('admin.backup_page'))


@admin_bp.route('/backup/restore', methods=['POST'])
@admin_required
def restore_backup():
    """从服务器已有备份或上传的 ZIP 恢复数据库与附件。"""
    # 恢复包通常远大于图片上传限制，临时提高本次请求的 body 上限。
    # 必须放在访问 request.form / request.files 之前生效。
    old_limit = current_app.config.get('MAX_CONTENT_LENGTH')
    current_app.config['MAX_CONTENT_LENGTH'] = backup_service.MAX_ARCHIVE_BYTES

    uploaded_path: Path | None = None
    try:
        # 该端点已在 app.py 中豁免全局 CSRF 检查（否则大文件会先被全局
        # MAX_CONTENT_LENGTH 拦截）；这里在提高上限后再手动校验。
        if current_app.config.get('WTF_CSRF_ENABLED', True):
            csrf_token = (
                request.form.get('csrf_token')
                or request.headers.get('X-CSRFToken')
                or request.headers.get('X-CSRF-Token')
            )
            try:
                validate_csrf(csrf_token)
            except ValidationError as exc:
                flash(f'CSRF 校验失败，请刷新页面后重试：{exc}', 'error')
                return redirect(url_for('admin.backup_page'))

        confirm = (request.form.get('confirm') or '').strip()
        if confirm != 'RESTORE':
            flash('请输入 RESTORE 以确认恢复操作', 'error')
            return redirect(url_for('admin.backup_page'))

        selected_name = (request.form.get('backup_name') or '').strip()
        upload = request.files.get('backup_file')

        if selected_name:
            archive_path = backup_service.resolve_backup(selected_name)
        elif upload and upload.filename:
            if not upload.filename.lower().endswith('.zip'):
                flash('只支持 ZIP 格式的全量备份文件', 'error')
                return redirect(url_for('admin.backup_page'))

            backup_dir = backup_service.get_backup_dir()
            fd, temp_name = tempfile.mkstemp(
                prefix='restore_upload_', suffix='.zip', dir=str(backup_dir)
            )
            os.close(fd)
            uploaded_path = Path(temp_name)
            upload.save(uploaded_path)
            archive_path = uploaded_path
        else:
            flash('请选择要恢复的备份文件', 'error')
            return redirect(url_for('admin.backup_page'))

        archive_info = backup_service.inspect_archive(archive_path)
        result = backup_service.restore_backup_archive(archive_path)

        # 数据库已替换，清空进程内缓存，避免返回旧数据
        cache = getattr(current_app, 'cache', None)
        if cache is not None:
            try:
                cache.clear()
            except Exception:  # noqa: BLE001
                logger.warning('恢复后清空缓存失败', exc_info=True)

        log_operation(
            session.get('user_id'),
            session.get('username'),
            '从全量备份恢复',
            f'{archive_path.name}（附件 {result["upload_files"]} 个）',
        )

        message = (
            f'恢复完成：数据库已还原，{result["upload_files"]} 个附件已还原'
        )
        if result.get('safety_backup'):
            message += f'；恢复前数据已自动备份为 {result["safety_backup"]}'
        flash(message, 'success')

        migration_result = result.get('migrations') or {}
        if migration_result.get('failed'):
            flash(
                '数据库迁移未完全成功，请检查日志：'
                + '；'.join(migration_result['failed']),
                'warning',
            )
        elif migration_result.get('applied'):
            flash(
                f'已自动应用 {migration_result["applied"]} 个数据库迁移',
                'info',
            )

        restart_command = (os.environ.get('BACKUP_RESTART_COMMAND') or '').strip()
        if restart_command:
            try:
                subprocess.Popen(shlex.split(restart_command))
                flash('已触发服务重启，请稍候刷新页面。', 'info')
            except Exception as exc:  # noqa: BLE001
                logger.warning('自动重启失败：%s', exc)
                flash(f'恢复完成，但自动重启失败：{exc}，请手动重启服务。', 'warning')
        else:
            flash('恢复完成，请立即重启 Web 服务，避免其他 worker 继续使用旧数据库。', 'warning')

        logger.info(
            '用户 %s 恢复全量备份 %s（格式版本 %s）',
            session.get('username'),
            archive_path.name,
            archive_info['manifest'].get('format_version'),
        )
    except RequestEntityTooLarge:
        limit_mb = backup_service.MAX_ARCHIVE_BYTES // 1024 // 1024
        flash(f'备份文件过大，当前上限为 {limit_mb} MB', 'error')
    except backup_service.BackupError as exc:
        flash(f'恢复失败：{exc}', 'error')
        log_error(exc, context='从全量备份恢复', user_id=session.get('user_id'))
    except Exception as exc:  # noqa: BLE001 - 统一提示并记录
        logger.exception('从全量备份恢复失败')
        flash(f'恢复失败：{exc}', 'error')
        log_error(exc, context='从全量备份恢复', user_id=session.get('user_id'))
    finally:
        current_app.config['MAX_CONTENT_LENGTH'] = old_limit
        if uploaded_path is not None:
            try:
                uploaded_path.unlink(missing_ok=True)
            except OSError:
                logger.warning('清理上传的临时备份文件失败：%s', uploaded_path)

    return redirect(url_for('admin.backup_page'))
