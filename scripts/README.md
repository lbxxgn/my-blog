# 项目脚本

此目录包含项目维护和部署相关的脚本。

## 📋 脚本说明

### 🚀 启动和安装

#### start.sh
快速启动开发服务器
```bash
./scripts/start.sh
```

#### install-service.sh
安装systemd服务（需要sudo权限）
```bash
sudo ./scripts/install-service.sh
```

### 🔄 升级和维护

#### upgrade.sh
系统升级脚本，自动执行：
- 数据库备份
- 代码更新
- 依赖安装
- 数据库迁移
- 服务重启
```bash
./scripts/upgrade.sh
```

#### rollback.sh
回滚到上一版本（紧急情况使用）
```bash
./scripts/rollback.sh backups/timestamp
```

#### verify_upgrade.sh
验证升级是否成功
```bash
./scripts/verify_upgrade.sh
```

### 🔧 工具脚本

#### generate_manifest.py
生成静态资源版本manifest
```bash
python3 scripts/generate_manifest.py
```

### 🧪 诊断脚本

诊断和性能分析脚本统一放在 `scripts/diagnostics/`：

- `performance-test.py` - 后端接口性能检查
- `performance_test.py` - 静态资源体积与 bundle 检查
- `test-lazyload.js` - 懒加载行为测试
- `test_asset_optimizer.py` - 资源路径映射检查

## 📚 使用文档

详细使用方法请参考：
- [部署指南](../DEPLOYMENT.md)
- [启动指南](../docs/startup.md)
- [升级指南](../docs/upgrade.md)

## ⚠️ 注意事项

1. **权限**: 大部分脚本需要执行权限（`chmod +x`）
2. **备份**: 升级脚本会自动备份，但建议手动备份重要数据
3. **测试**: 建议先在测试环境验证升级脚本
4. **日志**: 升级过程会输出详细日志，请检查是否有错误

## 🔍 故障排查

如果脚本执行失败：
1. 检查文件权限：`ls -l scripts/`
2. 查看错误日志：`tail -f logs/app.log`
3. 手动测试：直接运行脚本中的命令
