# 云主机部署指南

本文档提供在Ubuntu Server 24.04 LTS上部署AI4SE工具集的完整步骤。

## 前置要求

- Ubuntu Server 24.04 LTS 64bit
- root或sudo权限
- 域名 www.datou212.tech 已解析到服务器IP

## 部署步骤

### 1. 服务器环境准备

```bash
# 上传部署脚本到服务器（或直接在服务器上克隆仓库）
git clone https://github.com/pollyan/intent-test-framework.git
cd intent-test-framework

# 运行环境准备脚本
sudo bash scripts/deployment/setup-server.sh
```

此脚本将安装：
- Python 3.11+
- Node.js 20+
- PostgreSQL
- Nginx
- Git
- 其他必要工具

### 2. 数据库配置

```bash
# 运行数据库配置脚本
sudo bash scripts/deployment/setup-database.sh
```

按提示输入：
- 数据库名称（默认：intent_test_framework）
- 数据库用户名（默认：intent_user）
- 数据库密码

**重要**：请保存数据库连接字符串，格式：
```
postgresql://用户名:密码@localhost:5432/数据库名
```

### 3. 应用代码部署

```bash
# 运行应用部署脚本
sudo bash scripts/deployment/deploy-app.sh
```

此脚本将：
- 克隆/更新代码到 `/opt/intent-test-framework`
- 创建Python虚拟环境
- 安装Python依赖

### 4. 环境变量配置

```bash
# 创建.env文件
sudo -u appuser cp scripts/deployment/.env.production.example /opt/intent-test-framework/.env
sudo -u appuser nano /opt/intent-test-framework/.env
```

**必须配置的变量**：
- `DATABASE_URL`: PostgreSQL连接字符串
- `SECRET_KEY`: 强随机密钥（生产环境必须修改）
- `OPENAI_API_KEY`: AI API密钥
- `OPENAI_BASE_URL`: AI API基础URL
- `MIDSCENE_MODEL_NAME`: AI模型名称

**示例配置**：
```env
DATABASE_URL=postgresql://intent_user:your_password@localhost:5432/intent_test_framework
SECRET_KEY=your-very-strong-secret-key-here
OPENAI_API_KEY=sk-your-dashscope-api-key
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest
HOST=127.0.0.1
PORT=5001
FLASK_ENV=production
FLASK_DEBUG=False
```

### 5. 数据库初始化

```bash
# 运行数据库初始化脚本
sudo bash scripts/deployment/init-database.sh
```

此脚本将创建所有必要的数据库表。

### 6. Systemd服务配置

```bash
# 运行systemd配置脚本
sudo bash scripts/deployment/setup-systemd.sh
```

此脚本将：
- 创建systemd服务文件
- 启用服务自动启动
- 启动应用服务

### 7. Nginx反向代理配置

```bash
# 运行Nginx配置脚本
sudo bash scripts/deployment/setup-nginx.sh
```

此脚本将：
- 创建Nginx配置文件
- 配置反向代理（80端口 -> 5001端口）
- 配置静态文件服务
- 重启Nginx

### 8. 防火墙配置

```bash
# 运行防火墙配置脚本
sudo bash scripts/deployment/setup-firewall.sh
```

此脚本将：
- 开放80端口（HTTP）
- 开放443端口（HTTPS，为将来SSL证书准备）
- 开放22端口（SSH）
- 5001端口仅本地访问，不对外开放

### 9. 验证部署

```bash
# 检查服务状态
sudo systemctl status intent-test-framework
sudo systemctl status nginx

# 查看应用日志
sudo journalctl -u intent-test-framework -f

# 查看Nginx日志
sudo tail -f /var/log/nginx/intent-test-framework-access.log
sudo tail -f /var/log/nginx/intent-test-framework-error.log

# 测试应用访问
curl http://localhost:5001/health
curl http://www.datou212.tech/health
```

## 服务管理

### 应用服务管理

```bash
# 启动服务
sudo systemctl start intent-test-framework

# 停止服务
sudo systemctl stop intent-test-framework

# 重启服务
sudo systemctl restart intent-test-framework

# 查看状态
sudo systemctl status intent-test-framework

# 查看日志
sudo journalctl -u intent-test-framework -f
```

### Nginx服务管理

```bash
# 重启Nginx
sudo systemctl restart nginx

# 重新加载配置（不中断服务）
sudo systemctl reload nginx

# 测试配置
sudo nginx -t
```

## 故障排查

### 应用无法启动

1. 检查日志：
```bash
sudo journalctl -u intent-test-framework -n 50
```

2. 检查环境变量：
```bash
sudo -u appuser cat /opt/intent-test-framework/.env
```

3. 检查数据库连接：
```bash
sudo -u postgres psql -U intent_user -d intent_test_framework
```

### Nginx无法访问

1. 检查Nginx状态：
```bash
sudo systemctl status nginx
```

2. 检查Nginx配置：
```bash
sudo nginx -t
```

3. 检查端口占用：
```bash
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :5001
```

### 数据库连接问题

1. 检查PostgreSQL服务：
```bash
sudo systemctl status postgresql
```

2. 测试数据库连接：
```bash
psql -U intent_user -d intent_test_framework -h localhost
```

3. 检查数据库配置：
```bash
sudo -u postgres psql -c "\l"
```

## 更新应用

```bash
# 1. 停止服务
sudo systemctl stop intent-test-framework

# 2. 更新代码
cd /opt/intent-test-framework
sudo -u appuser git pull

# 3. 更新依赖（如有需要）
sudo -u appuser /opt/intent-test-framework/venv/bin/pip install -r requirements.txt

# 4. 运行数据库迁移（如有需要）
sudo bash scripts/deployment/init-database.sh

# 5. 重启服务
sudo systemctl start intent-test-framework
```

## 安全建议

1. **修改SECRET_KEY**：生产环境必须使用强随机密钥
2. **数据库密码**：使用强密码
3. **防火墙**：仅开放必要端口
4. **SSL证书**：建议配置HTTPS（使用Let's Encrypt）
5. **定期备份**：配置数据库自动备份
6. **日志轮转**：配置日志轮转避免磁盘空间问题

## 后续优化

- 配置HTTPS（Let's Encrypt SSL证书）
- 配置日志轮转
- 配置数据库自动备份
- 配置监控和告警
- 使用Gunicorn替代Flask内置服务器（提高性能）


