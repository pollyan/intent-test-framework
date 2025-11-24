# 部署脚本说明

本目录包含在Ubuntu Server 24.04 LTS上部署AI4SE工具集的所有脚本和配置文件。

## 快速开始

### 方式一：一键部署（推荐）

```bash
# 在服务器上克隆仓库
git clone https://github.com/pollyan/intent-test-framework.git
cd intent-test-framework

# 运行一键部署脚本
sudo bash scripts/deployment/deploy-all.sh
```

### 方式二：分步部署

按照 `DEPLOYMENT.md` 文档中的步骤逐步执行。

## 文件说明

### 部署脚本

- `deploy-all.sh` - 一键部署脚本（执行所有步骤）
- `setup-server.sh` - 服务器环境准备（安装Python、Node.js、PostgreSQL、Nginx等）
- `setup-database.sh` - PostgreSQL数据库配置
- `deploy-app.sh` - 应用代码部署
- `init-database.sh` - 数据库初始化
- `setup-systemd.sh` - Systemd服务配置
- `setup-nginx.sh` - Nginx反向代理配置
- `setup-firewall.sh` - 防火墙配置

### 配置文件

- `intent-test-framework.service` - Systemd服务文件
- `nginx-intent-test-framework.conf` - Nginx配置文件
- `start-production.py` - 生产环境启动脚本
- `.env.production.example` - 环境变量配置模板

### 文档

- `DEPLOYMENT.md` - 详细部署文档
- `README.md` - 本文件

## 部署流程

```
1. setup-server.sh          → 安装系统依赖
2. setup-database.sh       → 配置PostgreSQL
3. deploy-app.sh           → 部署应用代码
4. 手动编辑 .env            → 配置环境变量
5. init-database.sh        → 初始化数据库
6. setup-systemd.sh        → 配置系统服务
7. setup-nginx.sh          → 配置反向代理
8. setup-firewall.sh       → 配置防火墙
```

## 注意事项

1. **所有脚本需要root权限**：使用 `sudo` 运行
2. **环境变量配置**：必须手动编辑 `.env` 文件
3. **数据库密码**：请妥善保存数据库连接字符串
4. **SECRET_KEY**：生产环境必须使用强随机密钥
5. **域名解析**：确保 www.datou212.tech 已解析到服务器IP

## 故障排查

如遇问题，请查看：
- `DEPLOYMENT.md` 中的故障排查章节
- 应用日志：`sudo journalctl -u intent-test-framework -f`
- Nginx日志：`/var/log/nginx/intent-test-framework-*.log`

## 更新应用

```bash
cd /opt/intent-test-framework
sudo systemctl stop intent-test-framework
sudo -u appuser git pull
sudo -u appuser /opt/intent-test-framework/venv/bin/pip install -r requirements.txt
sudo bash scripts/deployment/init-database.sh  # 如有数据库迁移
sudo systemctl start intent-test-framework
```


