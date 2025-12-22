# 本地 Docker 部署脚本使用指南

## 脚本说明

本目录包含管理本地 Docker 环境的实用脚本：

### 1. `deploy-local.sh` - 完整部署
**用途：** 完全重新构建和部署 Docker 环境，确保所有代码更改生效

**何时使用：**
- 修改了 Python 代码
- 修改了配置文件
- 遇到代码不同步问题
- 首次部署项目

**运行：**
```bash
./scripts/deploy-local.sh
```

**步骤：**
1. 停止现有容器
2. 强制重新构建镜像（不使用缓存）
3. 启动新容器
4. 健康检查
5. 验证代码已更新
6. 测试 Lisa 模块加载

**预计时间：** 2-3 分钟

---

### 2. `restart-local.sh` - 快速重启
**用途：** 仅重启容器，不重新构建镜像

**何时使用：**
- 仅修改了环境变量
- 容器意外停止
- 需要快速重启服务

**运行：**
```bash
./scripts/restart-local.sh
```

**预计时间：** 10-15 秒

---

### 3. `verify-local.sh` - 验证部署
**用途：** 检查 Docker 环境是否正常运行

**何时使用：**
- 部署后验证
- 诊断问题
- 健康检查

**运行：**
```bash
./scripts/verify-local.sh
```

**测试项：**
- ✓ 容器运行状态
- ✓ Web 服务响应
- ✓ Lisa 模块加载
- ✓ 数据库连接

**预计时间：** 5-10 秒

---

## 常见问题

### Q: 代码修改后容器没有更新？
**A:** 使用 `deploy-local.sh` 而不是 `docker-compose restart`

### Q: 部署失败怎么办？
**A:** 
1. 查看错误信息
2. 运行 `docker logs intent-test-web --tail=50`
3. 检查代码语法错误
4. 重新运行 `deploy-local.sh`

### Q: 如何查看实时日志？
**A:** `docker logs intent-test-web -f`

### Q: 如何完全清理环境？
**A:** 
```bash
docker-compose down -v  # 删除容器和数据卷
docker system prune -af  # 清理所有未使用的镜像
./scripts/deploy-local.sh  # 重新部署
```

---

## 最佳实践

1. **代码修改后始终使用 `deploy-local.sh`**
   - ❌ `docker-compose restart`
   - ✅ `./scripts/deploy-local.sh`

2. **部署后运行验证**
   ```bash
   ./scripts/deploy-local.sh && ./scripts/verify-local.sh
   ```

3. **出现问题时先查看日志**
   ```bash
   docker logs intent-test-web --tail=100
   ```

4. **定期清理容器和镜像**
   ```bash
   docker system df  # 查看空间使用
   docker system prune -a  # 清理（谨慎使用）
   ```

---

## 脚本权限

首次使用前需要添加执行权限：

```bash
chmod +x scripts/*.sh
```

---

## 服务信息

部署成功后可访问：
- **Web UI:** http://localhost:5001
- **数据库:** localhost:5432
  - 用户: postgres
  - 密码: postgres
  - 数据库: test_intent
