# 前端构建指南

新版知识库编辑器位于 `frontend/`，基于 React 19.2 + Vite 8.1 + BlockNote 0.51 + Mantine 9 构建。

## 环境要求

- Node.js 18+（推荐 LTS）
- npm 或兼容包管理器

## 构建步骤

```bash
cd frontend
npm install
npm run build
cd ..
```

## 构建产物

- 输出目录：`static/frontend/`
- 清单文件：`static/frontend/.vite/manifest.json`
- Flask 通过 `backend/app.py` 中的 `vite_asset()` 辅助函数读取清单，向模板注入正确的 JS/CSS 路径。

## 开发模式

```bash
cd frontend
npm run dev
```

开发服务器默认在 `http://localhost:5173` 运行，与 Flask 后端独立。

## 常见问题

### 页面加载后编辑器空白

1. 确认已执行 `npm run build`
2. 检查 `static/frontend/.vite/manifest.json` 是否存在
3. 查看浏览器控制台是否有 404 错误
4. 查看 `logs/error.log` 是否有 Flask 模板渲染异常

### 静态资源 404

```bash
python3 scripts/generate_manifest.py
# 然后重启 Flask 应用
```

### 构建失败

1. 删除 `frontend/node_modules` 和 `package-lock.json` 后重新 `npm install`
2. 确认 Node.js 版本 >= 18
3. 检查 `frontend/vite.config.ts` 中的 `base` 和 `outDir` 配置
