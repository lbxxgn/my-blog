"""
知识库 BlockNote 编辑器后端 API 测试

覆盖：
- POST /knowledge/doc/upload-image
- POST /knowledge/doc/<id>/autosave
- GET  /knowledge/doc/<id>/draft
"""

import io
import json

import pytest
from PIL import Image

from backend.models import create_kb_category, create_knowledge_doc, get_kb_categories


@pytest.mark.usefixtures("client", "test_admin_user")
class TestKbImageUpload:
    """编辑器图片上传接口测试"""

    def _make_png_bytes(self) -> bytes:
        img = Image.new("RGB", (60, 40), color=(66, 133, 244))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    def _login(self, client, user):
        resp = client.post("/login", data={
            "username": user["username"],
            "password": user["password"],
        })
        assert resp.status_code == 302

    def test_upload_image_success(self, client, test_admin_user, tmp_path, monkeypatch):
        """上传合法图片应返回可访问 URL"""
        self._login(client, test_admin_user)
        # The blueprint is imported as ``routes.knowledge`` at runtime.
        monkeypatch.setattr(
            "routes.knowledge.UPLOAD_FOLDER", tmp_path / "uploads"
        )

        resp = client.post(
            "/knowledge/doc/upload-image",
            data={"file": (io.BytesIO(self._make_png_bytes()), "test.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["url"].startswith("/static/uploads/images/")
        assert data["filename"]

        saved = (tmp_path / "uploads" / "images" / data["filename"])
        assert saved.exists()
        with open(saved, "rb") as f:
            Image.open(io.BytesIO(f.read())).verify()

    def test_upload_image_missing_file(self, client, test_admin_user):
        """缺少 file 字段应返回 400"""
        self._login(client, test_admin_user)
        resp = client.post("/knowledge/doc/upload-image")
        assert resp.status_code == 400
        assert "没有文件上传" in resp.get_json()["error"]

    def test_upload_image_invalid_extension(self, client, test_admin_user):
        """非图片扩展名应返回 400"""
        self._login(client, test_admin_user)
        resp = client.post(
            "/knowledge/doc/upload-image",
            data={"file": (io.BytesIO(b"not an image"), "payload.txt")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 400
        assert "不支持" in resp.get_json()["error"]

    def test_upload_image_requires_login(self, client):
        """未登录应被重定向到登录页"""
        resp = client.post(
            "/knowledge/doc/upload-image",
            data={"file": (io.BytesIO(self._make_png_bytes()), "test.png")},
            content_type="multipart/form-data",
        )
        assert resp.status_code == 302
        assert "/login" in resp.headers.get("Location", "")


@pytest.mark.usefixtures("client", "test_admin_user")
class TestKbAutosave:
    """编辑器自动保存接口测试"""

    def _login(self, client, user):
        resp = client.post("/login", data={
            "username": user["username"],
            "password": user["password"],
        })
        assert resp.status_code == 302

    def _create_doc(self, user_id: int) -> int:
        cat_id = create_kb_category("AutoSave Test Cat")
        return create_knowledge_doc(
            title="Autosave Target",
            content="original content",
            category_id=cat_id,
            author_id=user_id,
            is_published=True,
        )

    def test_autosave_success(self, client, test_admin_user):
        """自动保存应为文档创建/更新草稿"""
        self._login(client, test_admin_user)
        doc_id = self._create_doc(test_admin_user["id"])

        payload = {"title": "Autosave Target Updated", "content": "autosaved markdown"}
        resp = client.post(
            f"/knowledge/doc/{doc_id}/autosave",
            data=json.dumps(payload),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["saved_at"]

    def test_autosave_missing_doc(self, client, test_admin_user):
        """不存在的文档应返回 404"""
        self._login(client, test_admin_user)
        resp = client.post(
            "/knowledge/doc/99999/autosave",
            data=json.dumps({"content": "x"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_autosave_requires_login(self, client):
        """未登录的 JSON 请求应返回 401，页面请求仍重定向到登录页"""
        resp = client.post(
            "/knowledge/doc/1/autosave",
            data=json.dumps({"content": "x"}),
            content_type="application/json",
        )
        assert resp.status_code == 401
        assert resp.get_json()["success"] is False

        resp_form = client.post(
            "/knowledge/doc/1/autosave",
            data={"content": "x"},
        )
        assert resp_form.status_code == 302
        assert "/login" in resp_form.headers.get("Location", "")

    def test_draft_endpoint_returns_saved_draft(self, client, test_admin_user):
        """自动保存后可通过 draft 接口取回草稿"""
        self._login(client, test_admin_user)
        doc_id = self._create_doc(test_admin_user["id"])

        client.post(
            f"/knowledge/doc/{doc_id}/autosave",
            data=json.dumps({"title": "Draft Title", "content": "draft content"}),
            content_type="application/json",
        )

        resp = client.get(f"/knowledge/doc/{doc_id}/draft")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["draft"]["title"] == "Draft Title"
        assert data["draft"]["content"] == "draft content"


@pytest.mark.usefixtures("client", "test_admin_user")
class TestKbCategoryReorder:
    """目录拖拽排序 API 测试"""

    def _login(self, client, user):
        resp = client.post("/login", data={
            "username": user["username"],
            "password": user["password"],
        })
        assert resp.status_code == 302

    def test_reorder_category_move_to_root(self, client, test_admin_user):
        """将子目录移回根节点"""
        self._login(client, test_admin_user)
        parent_id = create_kb_category("Reorder Parent", sort_order=100)
        child_id = create_kb_category("Reorder Child", parent_id=parent_id, sort_order=200)

        resp = client.post("/knowledge/reorder", data={
            "type": "category",
            "id": child_id,
            "parent_id": "",
            "sort_order": "50",
        })
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        cats = {c["id"]: c for c in get_kb_categories()}
        assert cats[child_id]["parent_id"] is None
        assert cats[child_id]["sort_order"] == 50

    def test_reorder_category_move_under_sibling(self, client, test_admin_user):
        """将目录移动为另一目录的子目录"""
        self._login(client, test_admin_user)
        cat_a = create_kb_category("Reorder A", sort_order=100)
        cat_b = create_kb_category("Reorder B", sort_order=200)

        resp = client.post("/knowledge/reorder", data={
            "type": "category",
            "id": cat_a,
            "parent_id": str(cat_b),
            "sort_order": "10",
        })
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        cats = {c["id"]: c for c in get_kb_categories()}
        assert cats[cat_a]["parent_id"] == cat_b
        assert cats[cat_a]["sort_order"] == 10

    def test_reorder_category_prevent_cycle(self, client, test_admin_user):
        """禁止将父目录移动到自身子目录下形成环"""
        self._login(client, test_admin_user)
        parent_id = create_kb_category("Cycle Parent", sort_order=100)
        child_id = create_kb_category("Cycle Child", parent_id=parent_id, sort_order=200)

        resp = client.post("/knowledge/reorder", data={
            "type": "category",
            "id": parent_id,
            "parent_id": str(child_id),
            "sort_order": "0",
        })
        assert resp.status_code == 200
        assert resp.get_json()["success"] is False

    def test_reorder_category_treats_none_string_as_root(self, client, test_admin_user):
        """前端误传字符串 'None' 时应视为根节点，而不是抛 500"""
        self._login(client, test_admin_user)
        parent_id = create_kb_category("Root-ish Parent", sort_order=100)
        child_id = create_kb_category("Root-ish Child", parent_id=parent_id, sort_order=200)

        resp = client.post("/knowledge/reorder", data={
            "type": "category",
            "id": child_id,
            "parent_id": "None",
            "sort_order": "75",
        })
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        cats = {c["id"]: c for c in get_kb_categories()}
        assert cats[child_id]["parent_id"] is None
        assert cats[child_id]["sort_order"] == 75
