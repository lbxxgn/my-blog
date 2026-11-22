/**
 * 备份任务进度轮询（原 templates/admin/backup.html 内联脚本）
 *
 * 页面带上 ?job_id=xxx 时轮询任务状态，成功后提示并给出刷新入口。
 */
(function () {
    'use strict';

    var POLL_INTERVAL = 2000;

    var params = new URLSearchParams(window.location.search);
    var jobId = params.get('job_id');
    var box = document.getElementById('backupJobStatus');
    if (!jobId || !box) return;

    box.style.display = 'block';
    var timer = setInterval(async function () {
        try {
            var data = await AppHttp.json('/admin/backup/job/' + encodeURIComponent(jobId), {
                headers: { 'Accept': 'application/json' },
                silent: true
            });
            if (!data || !data.success) throw new Error((data && data.error) || '任务不存在');
            var job = data.job;
            if (job.state === 'running') {
                box.textContent = '正在创建备份，请稍候...';
            } else if (job.state === 'success') {
                clearInterval(timer);
                box.textContent = '✅ 备份完成：' + job.archive_name + '（' + job.size_mb + ' MB，' + job.file_count + ' 个附件）';
                var link = document.createElement('a');
                link.href = window.location.pathname;
                link.className = 'backup-job-refresh';
                link.textContent = '刷新列表';
                box.appendChild(link);
            } else {
                clearInterval(timer);
                box.textContent = '❌ 备份失败：' + (job.message || '未知错误');
            }
        } catch (e) {
            clearInterval(timer);
            box.textContent = '备份任务状态读取失败：' + AppHttp.describe(e);
        }
    }, POLL_INTERVAL);

    window.addEventListener('pagehide', function () { clearInterval(timer); });
})();
