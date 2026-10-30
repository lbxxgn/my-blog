"""
知识库路由（独立空间）

提供结构化知识库的浏览与管理功能（登录后内嵌管理）：
- GET  /knowledge                       首页（目录树 + 最近文档）
- GET  /knowledge/category/<id>         目录页
- GET  /knowledge/doc/<id>              文档详情
- GET  /knowledge/search                知识库内搜索
- GET/POST /knowledge/doc/new           新建文档
- GET/POST /knowledge/doc/<id>/edit     编辑文档
- POST /knowledge/doc/<id>/delete       删除文档
- POST /knowledge/category/new          新建目录
- POST /knowledge/category/<id>/delete  删除目录
- POST /knowledge/reorder               拖拽排序/移动
- POST /knowledge/doc/upload-image      上传图片
- POST /knowledge/doc/<id>/autosave     自动保存
- GET  /knowledge/doc/<id>/draft        草稿
"""

from flask import Blueprint, request, redirect, url_for, render_template, abort, session, jsonify, flash
from werkzeug.utils import secure_filename
from datetime import datetime
from pathlib import Path
import os
import re

from auth_decorators import login_required
from logger import api_internal_error
from models import (
    get_category_tree, get_category_path, get_subcategories,
    get_doc_count_by_category, get_knowledge_doc, get_knowledge_docs_by_category, get_recent_knowledge_docs,
    get_knowledge_docs_for_tree, get_all_knowledge_docs, search_knowledge_docs,
    get_post_tags, search_posts, get_category_by_id,
    create_kb_category, move_kb_category, delete_kb_category, update_kb_category,
    create_knowledge_doc, update_knowledge_doc, reorder_knowledge_doc, delete_knowledge_doc,
    soft_delete_post,
)
from backend.config import UPLOAD_FOLDER, ALLOWED_EXTENSIONS
from models.draft import save_draft, get_drafts, delete_drafts_for_post
from utils.markdown_renderer import render_content

knowledge_bp = Blueprint('knowledge', __name__)


def _flatten_tree(tree, depth=0):
    """将分类树扁平化为带缩进提示的列表（供下拉选择用）"""
    result = []
    for node in tree:
        result.append({'id': node['id'], 'name': node['name'],
                       'indent': '　' * depth + ('└ ' if depth > 0 else '')})
        if node.get('children'):
            result.extend(_flatten_tree(node['children'], depth + 1))
    return result


def _is_logged_in():
    return session.get('user_id') is not None


def _is_manager():
    """目录管理权限：管理员/编辑。"""
    return session.get('role') in ('admin', 'editor')


def _can_edit_doc(doc):
    """文档编辑权限：作者本人或管理员/编辑。"""
    if not doc:
        return False
    if session.get('role') in ('admin', 'editor'):
        return True
    return session.get('user_id') == doc.get('author_id')


def _highlight_excerpt(content, query, limit=180):
    """生成带 <mark> 的搜索摘要，转义 HTML 后只高亮关键词。"""
    import html as html_module
    text = html_module.unescape(str(content or ''))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    if not text:
        return ''
    q = str(query or '').strip()
    idx = text.lower().find(q.lower()) if q else -1
    start = max(0, idx - 60) if idx >= 0 else 0
    snippet = text[start:start + limit]
    escaped = html_module.escape(snippet)
    if q:
        pattern = re.escape(html_module.escape(q))
        escaped = re.sub(pattern, lambda m: f'<mark>{m.group(0)}</mark>', escaped, flags=re.IGNORECASE)
    return ('…' if start > 0 else '') + escaped + ('…' if start + limit < len(text) else '')


def _wants_json():
    """判断当前请求是否期望 JSON 响应（编辑器 fetch 保存）"""
    return (request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            or request.accept_mimetypes.best == 'application/json')


# =============================================================================
# 浏览
# =============================================================================

@knowledge_bp.route('/')
@login_required
def index():
    """知识库首页：左侧目录树 + 右侧最近文档"""
    tree = get_category_tree('knowledge')
    recent_docs = get_recent_knowledge_docs(limit=10, include_drafts=True,
                                            viewer_id=session.get('user_id'),
                                            viewer_role=session.get('role'))
    tree_docs = get_knowledge_docs_for_tree(session.get('user_id'), session.get('role'))
    return render_template('knowledge/index.html', tree=tree, tree_docs=tree_docs, recent_docs=recent_docs,
                           can_manage=_is_manager())


@knowledge_bp.route('/category/<int:category_id>')
@login_required
def view_category(category_id):
    """目录页：子目录 + 文档列表 + 面包屑"""
    category = get_category_by_id(category_id)
    if not category or category.get('space') != 'knowledge':
        abort(404)

    breadcrumb = get_category_path(category_id)
    subcategories = get_subcategories(category_id, space='knowledge')
    docs = get_knowledge_docs_by_category(category_id, include_subcategories=False, include_drafts=True,
                                          viewer_id=session.get('user_id'), viewer_role=session.get('role'))

    for sub in subcategories:
        sub['doc_count'] = get_doc_count_by_category(sub['id'])

    tree = get_category_tree('knowledge')
    return render_template(
        'knowledge/category.html',
        category=category, breadcrumb=breadcrumb,
        subcategories=subcategories, docs=docs, tree=tree,
        tree_docs=get_knowledge_docs_for_tree(session.get('user_id'), session.get('role')),
        tree_flattened=_flatten_tree(tree),
        can_manage=_is_manager(),
    )


@knowledge_bp.route('/doc/<int:doc_id>')
@login_required
def view_doc(doc_id):
    """文档详情：面包屑 + Markdown 渲染 + TOC"""
    doc = get_knowledge_doc(doc_id)
    if not doc:
        abort(404)
    if not doc.get('is_published') and not _can_edit_doc(doc):
        abort(404)

    doc['content_html'] = render_content(doc['content'], doc.get('content_format'), with_header_ids=True)
    tags = get_post_tags(doc_id)

    breadcrumb = []
    if doc.get('category_id'):
        breadcrumb = get_category_path(doc['category_id'])

    tree = get_category_tree('knowledge')
    return render_template(
        'knowledge/doc.html', doc=doc, tags=tags,
        breadcrumb=breadcrumb, tree=tree,
        tree_docs=get_knowledge_docs_for_tree(session.get('user_id'), session.get('role')),
        can_manage=_is_manager(), can_edit=_can_edit_doc(doc), active_doc_id=doc_id,
    )


@knowledge_bp.route('/search')
@login_required
def search():
    """知识库内搜索"""
    q = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)

    if not q:
        tree = get_category_tree('knowledge')
        return render_template('knowledge/search.html', query='', posts=[], total=0,
                               page=1, total_pages=1, tree=tree,
                               tree_docs=get_knowledge_docs_for_tree(session.get('user_id'), session.get('role')),
                               tree_flattened=_flatten_tree(tree),
                               can_manage=_is_manager(), category_id=None, status=None)

    category_id = request.args.get('category_id', type=int)
    status = request.args.get('status') or None
    result = search_knowledge_docs(q, viewer_id=session.get('user_id'), viewer_role=session.get('role'),
                                   page=page, per_page=per_page, category_id=category_id, status=status)
    for post in result['posts']:
        post['excerpt_html'] = _highlight_excerpt(post.get('content'), q)
    tree = get_category_tree('knowledge')
    return render_template('knowledge/search.html', query=q, tree=tree,
                           tree_docs=get_knowledge_docs_for_tree(session.get('user_id'), session.get('role')),
                           tree_flattened=_flatten_tree(tree),
                           can_manage=_is_manager(), category_id=category_id, status=status, **result)


# =============================================================================
# 管理（内嵌在知识库空间内）
# =============================================================================

@knowledge_bp.route('/category/new', methods=['POST'])
@login_required
def new_category():
    """创建子目录"""
    if not _is_manager():
        return jsonify({'success': False, 'error': '权限不足'}), 403
    name = request.form.get('name', '').strip()
    parent_id = request.form.get('parent_id', type=int)
    icon = request.form.get('icon', '').strip() or None
    description = request.form.get('description', '').strip() or None
    if not name:
        return jsonify({'success': False, 'error': '名称不能为空'}), 400
    category_id = create_kb_category(name, parent_id=parent_id, space='knowledge',
                                      icon=icon, description=description)
    if category_id:
        return jsonify({'success': True, 'id': category_id})
    return jsonify({'success': False, 'error': '名称已存在'}), 400


@knowledge_bp.route('/category/<int:category_id>/delete', methods=['POST'])
@login_required
def delete_category(category_id):
    """删除目录"""
    if not _is_manager():
        abort(403)
    delete_kb_category(category_id)
    if _wants_json():
        return jsonify({'success': True})
    flash('目录已删除，原目录下的文档已移入未分类', 'success')
    return redirect(url_for('knowledge.index'))


@knowledge_bp.route('/reorder', methods=['POST'])
@login_required
def reorder():
    """拖拽排序/移动 API（分类或文档）"""
    data = request.get_json(silent=True) or request.form.to_dict()
    item_type = data.get('type')
    try:
        item_id = int(data.get('id'))
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '缺少或无效的 id'}), 400
    parent_id_raw = data.get('parent_id')
    new_parent_id = int(parent_id_raw) if parent_id_raw and str(parent_id_raw).lower() not in ('', 'none', 'null') else None
    try:
        new_sort_order = int(data.get('sort_order', 0))
    except (TypeError, ValueError):
        new_sort_order = 0
    try:
        if item_type == 'category':
            if not _is_manager():
                return jsonify({'success': False, 'error': '权限不足'}), 403
            success = move_kb_category(item_id, new_parent_id, new_sort_order)
        elif item_type == 'doc':
            doc = get_knowledge_doc(item_id)
            if not doc or not _can_edit_doc(doc):
                return jsonify({'success': False, 'error': '权限不足'}), 403
            success = reorder_knowledge_doc(item_id, new_sort_order, category_id=new_parent_id)
        else:
            return jsonify({'success': False, 'error': '未知类型'}), 400
        return jsonify({'success': success})
    except Exception as e:
        return api_internal_error(e)


@knowledge_bp.route('/doc/new', methods=['GET', 'POST'])
@login_required
def new_doc():
    """新建文档"""
    tree = get_category_tree('knowledge')
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        category_id = request.form.get('category_id', type=int)
        is_published = request.form.get('is_published') is not None
        tags = request.form.get('tags', '').strip()
        tag_names = [t.strip() for t in re.split(r'[,，]', tags) if t.strip()] if tags else []
        sort_order = request.form.get('sort_order', type=int, default=0)
        if not title or not category_id:
            if _wants_json():
                return jsonify({'success': False, 'error': '标题和目录不能为空'}), 400
            return render_template('knowledge/editor.html', tree=tree,
                                   tree_flattened=_flatten_tree(tree), doc=None,
                                   error='标题和目录不能为空')
        doc_id = create_knowledge_doc(title, content, category_id,
                                      tag_names=tag_names, sort_order=sort_order,
                                      is_published=is_published, author_id=session['user_id'])
        if _wants_json():
            return jsonify({
                'success': True,
                'doc_id': doc_id,
                'redirect': url_for('knowledge.view_doc', doc_id=doc_id),
                'edit_url': url_for('knowledge.edit_doc', doc_id=doc_id),
                'autosave_url': url_for('knowledge.autosave_doc', doc_id=doc_id),
                'draft_url': url_for('knowledge.draft_doc', doc_id=doc_id),
            })
        return redirect(url_for('knowledge.view_doc', doc_id=doc_id))
    # 预选目录
    preselect_cat = request.args.get('cat', type=int)
    return render_template('knowledge/editor.html', tree=tree,
                           tree_flattened=_flatten_tree(tree), doc=None, preselect_cat=preselect_cat)


@knowledge_bp.route('/doc/<int:doc_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_doc(doc_id):
    """编辑文档"""
    tree = get_category_tree('knowledge')
    existing_doc = get_knowledge_doc(doc_id)
    if not existing_doc:
        abort(404)
    if not _can_edit_doc(existing_doc):
        abort(403)
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        content = request.form.get('content', '')
        category_id = request.form.get('category_id', type=int)
        is_published = request.form.get('is_published') is not None
        tags = request.form.get('tags', '').strip()
        tag_names = [t.strip() for t in re.split(r'[,，]', tags) if t.strip()] if tags else []
        sort_order = request.form.get('sort_order', type=int)
        if not title or not category_id:
            if _wants_json():
                return jsonify({'success': False, 'error': '标题和目录不能为空'}), 400
            return render_template('knowledge/editor.html', tree=tree,
                                   tree_flattened=_flatten_tree(tree), doc=get_knowledge_doc(doc_id),
                                   error='标题和目录不能为空')
        updated = update_knowledge_doc(doc_id, title, content, category_id, is_published,
                                       tag_names=tag_names, sort_order=sort_order)
        if not updated:
            if _wants_json():
                return jsonify({'success': False, 'error': '文档不存在或保存失败'}), 404
            abort(404)
        # 正文已落库，清理自动保存草稿，避免下次打开时旧草稿覆盖新内容
        delete_drafts_for_post(session['user_id'], doc_id)
        if _wants_json():
            return jsonify({
                'success': True,
                'doc_id': doc_id,
                'is_published': is_published,
                'redirect': url_for('knowledge.view_doc', doc_id=doc_id),
            })
        return redirect(url_for('knowledge.view_doc', doc_id=doc_id))
    doc = get_knowledge_doc(doc_id)
    if not doc:
        abort(404)
    tags = get_post_tags(doc_id)
    return render_template('knowledge/editor.html', tree=tree,
                           tree_flattened=_flatten_tree(tree), doc=doc, tags=tags)


@knowledge_bp.route('/doc/<int:doc_id>/delete', methods=['POST'])
@login_required
def delete_doc(doc_id):
    """删除文档（软删除，可在管理后台回收站恢复）"""
    doc = get_knowledge_doc(doc_id)
    if not doc:
        abort(404)
    if not _can_edit_doc(doc):
        abort(403)
    soft_delete_post(doc_id)
    flash('文档已移入回收站', 'success')
    return redirect(url_for('knowledge.index'))


# =============================================================================
# 编辑器辅助 API
# =============================================================================

def _allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@knowledge_bp.route('/doc/upload-image', methods=['POST'])
@login_required
def upload_image():
    """知识库编辑器图片上传"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件上传'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': '未选择文件'}), 400

    if not _allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400

    file_content = file.read()
    file.seek(0)
    file_size = len(file_content)
    max_file_size = 50 * 1024 * 1024
    if file_size > max_file_size:
        return jsonify({'success': False, 'error': f'文件大小超过限制（最大{max_file_size//1024//1024}MB）'}), 400

    try:
        from PIL import Image
        import io
        img = Image.open(io.BytesIO(file_content))
        detected_type = img.format.lower() if img.format else None
        allowed_types = ['jpeg', 'jpg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'mpo', 'heic', 'heif']
        if detected_type not in allowed_types:
            return jsonify({'success': False, 'error': f'无效的图片文件类型: {detected_type}'}), 400
        width, height = img.size
        if width > 8192 or height > 8192:
            return jsonify({'success': False, 'error': '图片尺寸过大'}), 400
        if detected_type in ['mpo', 'heic', 'heif']:
            if img.mode in ('RGBA', 'P', 'LA'):
                img = img.convert('RGB')
            elif img.mode != 'RGB':
                img = img.convert('RGB')
            jpeg_buffer = io.BytesIO()
            img.save(jpeg_buffer, format='JPEG', quality=95)
            file_content = jpeg_buffer.getvalue()
            file_type = 'jpg'
        else:
            file_type = 'jpg' if detected_type == 'jpeg' else detected_type
    except ImportError:
        file_type = secure_filename(file.filename).rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
    except Exception:
        return jsonify({'success': False, 'error': '图片文件损坏或格式错误'}), 400

    # 连字符命名，避免下划线在 Markdown 中被解析成斜体而破坏 URL
    timestamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    ext = file_type or 'png'
    random_suffix = os.urandom(4).hex()
    base_filename = f"{timestamp}-{random_suffix}"
    images_dir = Path(UPLOAD_FOLDER) / 'images'
    images_dir.mkdir(parents=True, exist_ok=True)
    original_path = images_dir / f"{base_filename}.{ext}"

    try:
        with open(original_path, 'wb') as f:
            f.write(file_content)
    except Exception as e:
        return jsonify({'success': False, 'error': f'文件保存失败: {str(e)}'}), 500

    image_url = f"/static/uploads/images/{original_path.name}"
    return jsonify({
        'success': True,
        'url': image_url,
        'filename': original_path.name
    })


@knowledge_bp.route('/doc/<int:doc_id>/autosave', methods=['POST'])
@login_required
def autosave_doc(doc_id):
    """自动保存知识库文档草稿"""
    data = request.get_json(silent=True) or {}
    title = (data.get('title') or '').strip()
    content = data.get('content', '')

    doc = get_knowledge_doc(doc_id)
    if not doc:
        return jsonify({'success': False, 'error': '文档不存在'}), 404
    if not _can_edit_doc(doc):
        return jsonify({'success': False, 'error': '无权编辑此文档'}), 403

    result = save_draft(
        user_id=session['user_id'],
        post_id=doc_id,
        title=title or doc['title'],
        content=content,
        category_id=doc.get('category_id'),
        tags=[],
        device_info=data.get('device_info') or 'kb-editor',
        content_format='markdown',
        device_token=data.get('device_token') or ''
    )

    if result.get('success'):
        return jsonify({
            'success': True,
            'saved_at': result.get('updated_at'),
            'status': result.get('status'),
            'other_drafts': result.get('other_drafts', []),
        })
    return jsonify({'success': False, 'error': result.get('error', '保存失败')}), 500


@knowledge_bp.route('/doc/<int:doc_id>/draft', methods=['GET'])
@login_required
def draft_doc(doc_id):
    """获取知识库文档草稿"""
    drafts = get_drafts(user_id=session['user_id'], post_id=doc_id)
    if drafts:
        latest = drafts[0]
        return jsonify({
            'success': True,
            'draft': {
                'title': latest.get('title'),
                'content': latest.get('content'),
                'content_format': latest.get('content_format', 'markdown'),
                'saved_at': latest.get('updated_at')
            }
        })
    return jsonify({'success': True, 'draft': None})


@knowledge_bp.route('/documents')
@login_required
def all_documents():
    """全部文档 / 未分类文档。"""
    scope = request.args.get('scope', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    if per_page not in (20, 50, 100):
        per_page = 50
    result = get_all_knowledge_docs(session.get('user_id'), session.get('role'),
                                    scope=scope, page=page, per_page=per_page)
    tree = get_category_tree('knowledge')
    return render_template('knowledge/documents.html', scope=scope, tree=tree,
                           tree_docs=get_knowledge_docs_for_tree(session.get('user_id'), session.get('role')),
                           can_manage=_is_manager(), **result)


@knowledge_bp.route('/category/<int:category_id>/rename', methods=['POST'])
@login_required
def rename_category(category_id):
    if not _is_manager():
        return jsonify({'success': False, 'error': '权限不足'}), 403
    data = request.get_json(silent=True) or request.form
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'success': False, 'error': '名称不能为空'}), 400
    if update_kb_category(category_id, name=name):
        if _wants_json():
            return jsonify({'success': True, 'name': name})
        flash('目录已重命名', 'success')
        return redirect(url_for('knowledge.view_category', category_id=category_id))
    return jsonify({'success': False, 'error': '重命名失败，名称可能已存在'}), 400


@knowledge_bp.route('/docs/move', methods=['POST'])
@login_required
def batch_move_docs():
    """批量移动文档到目标目录。"""
    data = request.get_json(silent=True) or request.form
    raw_ids = data.get('doc_ids') or []
    if isinstance(raw_ids, str):
        raw_ids = [part for part in re.split(r'[,，\s]+', raw_ids) if part]
    target_id = data.get('category_id')
    try:
        target_id = int(target_id)
    except (TypeError, ValueError):
        return jsonify({'success': False, 'error': '请选择目标目录'}), 400
    moved = 0
    for raw_id in raw_ids:
        try:
            doc_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        doc = get_knowledge_doc(doc_id)
        if doc and _can_edit_doc(doc):
            if reorder_knowledge_doc(doc_id, doc.get('sort_order') or 0, category_id=target_id):
                moved += 1
    return jsonify({'success': moved > 0, 'moved': moved})
