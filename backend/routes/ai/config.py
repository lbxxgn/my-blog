"""AI 配置、测试与用量（ai 蓝图子模块）。"""


from flask import render_template, request, session, jsonify

from ai_services import TagGenerator
from ai_services.embeddings import (
    DEFAULT_BASE_URL as EMBEDDING_DEFAULT_BASE_URL,
    DEFAULT_MODEL as EMBEDDING_DEFAULT_MODEL,
    get_embedding_config, update_embedding_config, test_embedding_connection,
)
from models import (
    get_db_connection,
    get_user_ai_config, update_user_ai_config,
    get_ai_tag_history,
    get_ai_usage_stats
)
from auth_decorators import login_required, admin_required
from logger import log_operation, log_error





from . import ai_bp, logger, _heuristic_title, _heuristic_summary, _heuristic_type, _heuristic_tags, _pick_category, _run_structured_prompt, _parse_json_block  # noqa: F401


@ai_bp.route('/configure', methods=['GET', 'POST'])
@login_required
def ai_settings():
    """
    AI设置页面和API
    GET: 显示设置页面
    POST: 更新AI配置
    """
    user_id = session.get('user_id')

    if request.method == 'GET':
        # 获取用户当前AI配置
        ai_config = get_user_ai_config(user_id)
        embedding_config = get_embedding_config(user_id)
        supported_providers = TagGenerator.get_supported_providers()

        # 获取使用统计
        stats = get_ai_usage_stats(user_id)

        return render_template('admin/ai_settings.html',
                             ai_config=ai_config,
                             embedding_config=embedding_config,
                             embedding_default_base_url=EMBEDDING_DEFAULT_BASE_URL,
                             embedding_default_model=EMBEDDING_DEFAULT_MODEL,
                             supported_providers=supported_providers,
                             stats=stats)

    else:  # POST
        try:
            # 更新AI配置
            data = request.get_json()

            # 验证数据
            ai_config = {}

            if 'ai_tag_generation_enabled' in data:
                ai_config['ai_tag_generation_enabled'] = bool(data['ai_tag_generation_enabled'])

            if 'ai_provider' in data:
                provider = data['ai_provider']
                # 验证提供商是否支持
                supported = [p['id'] for p in TagGenerator.get_supported_providers()]
                if provider not in supported:
                    return jsonify({
                        'success': False,
                        'error': f'不支持的AI提供商: {provider}'
                    }), 400
                ai_config['ai_provider'] = provider

            if 'ai_api_key' in data:
                api_key = data['ai_api_key'].strip()
                if api_key:
                    ai_config['ai_api_key'] = api_key

            if 'ai_model' in data:
                model = data['ai_model'].strip()
                if model:
                    ai_config['ai_model'] = model

            if 'ai_base_url' in data:
                base_url = (data['ai_base_url'] or '').strip()
                ai_config['ai_base_url'] = base_url or None

            # 自定义提供商必须填写 Base URL
            if ai_config.get('ai_provider') == 'custom' and not ai_config.get('ai_base_url'):
                return jsonify({
                    'success': False,
                    'error': '自定义提供商需要填写 Base URL'
                }), 400

            # Embedding 服务配置（独立于对话类 AI 配置）
            embedding_data = {}
            if 'ai_embedding_enabled' in data:
                embedding_data['ai_embedding_enabled'] = bool(data['ai_embedding_enabled'])
            for key in ('ai_embedding_base_url', 'ai_embedding_api_key', 'ai_embedding_model'):
                if key in data:
                    embedding_data[key] = data[key]

            # 更新配置
            success = True
            if ai_config:
                success = update_user_ai_config(user_id, ai_config)
            if success and embedding_data:
                success = update_embedding_config(user_id, embedding_data)

            if not ai_config and not embedding_data:
                return jsonify({
                    'success': False,
                    'error': '没有需要更新的配置'
                }), 400

            if success:
                log_operation(session.get('user_id'), session.get('username'),
                             '更新AI配置')
                return jsonify({
                    'success': True,
                    'message': 'AI配置已更新'
                })
            else:
                return jsonify({
                    'success': False,
                    'error': '配置更新失败'
                }), 500

        except Exception as e:
            log_error(e, context='更新AI配置失败')
            return jsonify({
                'success': False,
                'error': '配置更新失败，请稍后重试'
            }), 500

@ai_bp.route('/test', methods=['POST'])
@login_required
def test_ai_config():
    """
    测试AI配置API

    支持两种模式：
    1. 测试表单中的配置（POST请求体中提供）
    2. 测试数据库中保存的配置
    """
    try:
        user_id = session.get('user_id')

        # 尝试从请求体获取配置（表单中的值）
        form_config = request.get_json()

        if form_config and form_config.get('ai_api_key'):
            # 使用表单中的配置进行测试
            ai_config = {
                'ai_tag_generation_enabled': True,
                'ai_provider': form_config.get('ai_provider', 'dashscope'),
                'ai_api_key': form_config.get('ai_api_key'),
                'ai_model': form_config.get('ai_model'),
                'ai_base_url': form_config.get('ai_base_url')
            }
        else:
            # 使用数据库中保存的配置
            ai_config = get_user_ai_config(user_id)

            if not ai_config:
                return jsonify({
                    'success': False,
                    'message': '未配置API密钥，请先在下方输入密钥'
                })

        # 测试配置
        result = TagGenerator.test_user_config(ai_config)

        return jsonify(result)

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        })

@ai_bp.route('/embedding/test', methods=['POST'])
@login_required
def test_embedding():
    """
    测试 Embedding 服务连通性

    优先使用表单中填写的配置，未填写密钥时回退到数据库中已保存的配置。
    """
    try:
        user_id = session.get('user_id')
        form = request.get_json(silent=True) or {}

        if form.get('ai_embedding_api_key'):
            config = {
                'enabled': True,
                'api_key': form['ai_embedding_api_key'].strip(),
                'base_url': (form.get('ai_embedding_base_url') or '').strip() or EMBEDDING_DEFAULT_BASE_URL,
                'model': (form.get('ai_embedding_model') or '').strip() or EMBEDDING_DEFAULT_MODEL,
            }
        else:
            config = get_embedding_config(user_id)
            if not config or not config.get('api_key'):
                return jsonify({
                    'success': False,
                    'message': '未配置 Embedding API 密钥，请先输入密钥'
                })

        return jsonify(test_embedding_connection(config))

    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'测试失败: {str(e)}'
        })

@ai_bp.route('/embeddings/rebuild', methods=['POST'])
@admin_required
def rebuild_embeddings():
    """
    重建向量索引（仅管理员）：遍历全部文章/知识库文档/卡片入队回填。

    未启用 Embedding 的用户名下的实体会被 worker 静默跳过；
    全局无用户启用时入队数为 0。
    """
    try:
        from tasks.embedding_task import enqueue_embedding

        enqueued = 0
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id, post_type FROM posts')
            for row in cursor.fetchall():
                source_type = 'doc' if row['post_type'] == 'knowledge' else 'post'
                if enqueue_embedding(source_type, row['id']) is not None:
                    enqueued += 1
            cursor.execute('SELECT id FROM cards')
            for row in cursor.fetchall():
                if enqueue_embedding('card', row['id']) is not None:
                    enqueued += 1
        finally:
            conn.close()

        if enqueued:
            message = f'已入队 {enqueued} 条内容，向量正在后台生成'
        else:
            message = '没有可回填的内容（或尚未有任何用户启用 Embedding 服务）'

        log_operation(session.get('user_id'), session.get('username'),
                      f'重建向量索引: 入队 {enqueued} 条')

        return jsonify({
            'success': True,
            'enqueued': enqueued,
            'message': message
        })

    except Exception as e:
        log_error(e, context='重建向量索引失败')
        return jsonify({
            'success': False,
            'error': '重建向量索引失败，请稍后重试'
        }), 500

@ai_bp.route('/history')
@login_required
def ai_history():
    """
    AI生成历史页面
    """
    import json

    user_id = session.get('user_id')
    history = get_ai_tag_history(user_id=user_id, limit=50)
    stats = get_ai_usage_stats(user_id)

    # Parse generated_tags JSON for each record
    for record in history:
        if record.get('generated_tags'):
            try:
                parsed = json.loads(record['generated_tags'])

                # If it's a list (old format), keep it as is
                # If it's a dict (new format), use it as parsed_data
                if isinstance(parsed, dict):
                    record['parsed_data'] = parsed
                else:
                    record['parsed_data'] = None
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Failed to parse AI history JSON: {e}")
                record['parsed_data'] = None
        else:
            record['parsed_data'] = None

    return render_template('admin/ai_history.html',
                         history=history,
                         stats=stats)

@ai_bp.route('/status')
@login_required
def ai_status():
    """
    获取AI功能启用状态API

    返回当前用户的AI功能是否启用，用于前端控制AI功能的显示/隐藏
    """
    user_id = session.get('user_id')
    ai_config = get_user_ai_config(user_id)

    ai_enabled = False
    if ai_config:
        ai_enabled = ai_config.get('ai_tag_generation_enabled', False)

    return jsonify({
        'ai_enabled': ai_enabled
    })
