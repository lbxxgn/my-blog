# Safari Extension - 知识库快速捕获

Safari 浏览器扩展，用于快速保存网页内容到个人知识库。

> **代码同步说明**：本扩展的 `popup/`、`content/`、`background/` 与 `browser-extension/` 完全相同，
> 权威源在 `browser-extension/`。修改共享文件后请运行 `../scripts/sync-extensions.sh` 同步到本目录；
> 本目录只需维护 `manifest.json`、`icons/` 与本 README。

## 系统要求

- **Safari 14+** (macOS Big Sur 11.0+ 或 iOS 14+)
- 本地后端服务运行在 `http://localhost:5001`

## 安装步骤

### 在 macOS Safari 上安装

1. **启用开发者菜单**
   - 打开 Safari
   - 菜单栏选择 `Safari > 设置` (或 `Preferences`)
   - 点击 `高级` 标签
   - 勾选 `在菜单栏中显示开发菜单`

2. **加载扩展**
   - 菜单栏选择 `开发 > 允许未签名的扩展` (可选，首次使用需要)
   - 菜单栏选择 `开发 > Web 扩展 > 显示网页检查器`
   - 或者直接打开 `Safari > 偏好设置 > 扩展`
   - 点击左下角的 `+` 号或勾选 `知识库快速捕获`

3. **验证安装**
   - 浏览器工具栏应该出现扩展图标
   - 点击图标确认可以打开设置面板

### 在 iOS Safari 上安装 (可选)

iOS 上安装稍微复杂一些，需要：
- 使用 Safari Web Extension Converter 转换为 iOS 应用
- 在 Xcode 中编译并安装到设备

**建议：主要在 macOS 上使用，iOS 上可以直接用浏览器添加到主屏幕的方式访问你的知识库 Web 界面**

## 配置

### 生成 API 密钥

在 `browser-extension/` 目录下运行（Safari 与 Chrome 共用同一套 API 密钥）：

```bash
cd browser-extension
python3 generate-api-key.py
# 输入你的用户名（如 admin）
```

### 配置扩展

1. 点击 Safari 工具栏中的扩展图标
2. 点击设置 (齿轮图标 ⚙️)
3. 输入你的 API 密钥
4. 确认 API URL 为 `http://localhost:5001/knowledge_base`（本地开发）或远程服务器地址加 `/knowledge_base`
5. 保存设置

## 使用方法

### 快速捕获

1. 在任何网页上选中文字
2. 点击浮动工具栏中的 📌 按钮
3. 内容自动保存到知识库！

### 添加标签

1. 选中文字
2. 点击 🏷️ 按钮
3. 输入标签 (用逗号分隔，如 `python, 教程, 重要`)
4. 点击确认保存

### 添加笔记

1. 选中文字
2. 点击 ✏️ 按钮
3. 输入笔记内容
4. 保存时笔记会附加到捕获内容上

## 与 Chrome 版本的区别

Safari 版本与 Chrome 版本**功能完全相同**，代码复用率 95%+：

- ✅ 相同的浮动工具栏
- ✅ 相同的快捷捕获功能
- ✅ 相同的 API 通信
- ✅ 相同的标签和笔记支持

唯一的区别是 `manifest.json` 中添加了 Safari 特定配置：

```json
"browser_specific_settings": {
  "safari": {
    "strict_site_minification": false
  }
}
```

**注意**：插件 API 的实际路径为 `/knowledge_base/api/plugin/*`，因此本地默认 API URL 是 `http://localhost:5001/knowledge_base`。

## 故障排除

### 扩展无法加载？

**检查 Safari 版本：**
- 打开 `Safari > 关于 Safari`
- 确保版本 >= 14.0

**启用开发者模式：**
- `Safari > 偏好设置 > 高级`
- 勾选 `在菜单栏中显示开发菜单`

### 工具栏不显示？

**确认扩展已启用：**
- `Safari > 偏好设置 > 扩展`
- 确保 `知识库快速捕获` 已勾选

**检查权限：**
- 确保扩展有访问当前网站的权限
- 在地址栏左侧点击扩展图标确认

### 保存失败？

**确认后端服务运行中：**
```bash
source .venv/bin/activate
python backend/app.py
```

**验证 API URL：**
- 本地开发应为 `http://localhost:5001/knowledge_base`
- 远程服务器应为 `https://your-domain.com/knowledge_base`

**验证 API 密钥：**
- 打开扩展设置
- 重新输入 API 密钥
- 点击 `测试连接`

**查看错误日志：**
- 打开 `开发 > Web 扩展 > [扩展名称]`
- 查看控制台错误信息

## 更新扩展

当你修改代码后：

1. 在 Safari 中打开 `Safari > 偏好设置 > 扩展`
2. 取消勾选扩展
3. 重新勾选扩展
4. 或者点击 `开发 > Web 扩展 > 重新加载 [扩展名称]`

## 开发说明

### 文件结构

```
safari-extension/
├── manifest.json          # 扩展配置 (包含 Safari 特定设置)
├── background/
│   ├── api-client.js      # API 客户端
│   ├── auth-manager.js    # 认证管理
│   └── service-worker.js  # 后台服务工作
├── content/
│   ├── content-bundle.js  # 注入到网页的脚本
│   ├── content.css        # 样式
│   ├── content.js
│   ├── selector.js
│   └── toolbar.js         # 浮动工具栏
├── popup/
│   ├── popup.html         # 弹出页面
│   ├── popup.js
│   └── popup.css
└── icons/                 # 图标资源
```

### 与 Chrome 版本同步

当你修改 Chrome 版本时，只需要：

1. **JavaScript/CSS 文件** - 直接复制到 safari-extension 对应目录
2. **manifest.json** - 合并修改，保留 `browser_specific_settings` 字段

快速同步命令：
```bash
# 复制更新的文件
cp browser-extension/background/*.js safari-extension/background/
cp browser-extension/content/*.* safari-extension/content/
cp browser-extension/popup/*.* safari-extension/popup/

# 然后手动合并 manifest.json 的修改
```

## 发布到 App Store (可选)

如果你想公开发布：

1. **注册 Apple Developer 账号** ($99/年)
2. **使用 Safari Extension Converter 转换**
   ```bash
   xcrun safari-web-extension-converter /path/to/safari-extension
   ```
3. **在 Xcode 中配置应用信息**
4. **上传到 App Store Connect**
5. **等待审核**

**注意：个人使用不需要以上步骤，直接加载未签名扩展即可**

## 技术支持

遇到问题？

1. 查看主项目的 `browser-extension/README.md` 获取更多 API 文档
2. 检查 `browser-extension/TESTING.md` 了解测试方法
3. 查看浏览器控制台的错误日志

## 许可证

MIT
