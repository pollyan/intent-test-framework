# 快速部署指南

## 前提条件

- Ubuntu Server 24.04 LTS
- root或sudo权限
- 域名 www.datou212.tech 已解析到服务器IP (120.53.220.231)

## 一键部署

```bash
# 1. 克隆仓库
git clone https://github.com/pollyan/intent-test-framework.git
cd intent-test-framework

# 2. 运行一键部署脚本
sudo bash scripts/deployment/deploy-all.sh
```

部署脚本将自动完成：
- ✅ 安装Python 3.11、Node.js、PostgreSQL、Nginx
- ✅ 配置PostgreSQL数据库
- ✅ 部署应用代码
- ✅ 配置环境变量（需要手动编辑）
- ✅ 初始化数据库
- ✅ 配置systemd服务
- ✅ 配置Nginx反向代理
- ✅ 配置防火墙

## 关键配置步骤

### 1. 环境变量配置

部署过程中会提示编辑 `.env` 文件：

```bash
sudo -u appuser nano /opt/intent-test-framework/.env
```

**必须配置**：
- `DATABASE_URL`: 使用数据库配置脚本生成的连接字符串
- `SECRET_KEY`: 生成强随机密钥（可使用：`openssl rand -hex 32`）
- `OPENAI_API_KEY`: 你的AI API密钥
- `OPENAI_BASE_URL`: AI API基础URL
- `MIDSCENE_MODEL_NAME`: AI模型名称

### 2. 生成SECRET_KEY

```bash
openssl rand -hex 32
```

将生成的密钥填入 `.env` 文件的 `SECRET_KEY`。

## 验证部署

```bash
# 检查服务状态
sudo systemctl status intent-test-framework
sudo systemctl status nginx

# 测试访问
curl http://www.datou212.tech/health
curl http://localhost:5001/health

# 查看日志
sudo journalctl -u intent-test-framework -f
```

## 访问应用

部署成功后，通过以下地址访问：
- **生产地址**: http://www.datou212.tech
- **本地地址**: http://localhost:5001 (仅服务器本地)

## 服务管理

```bash
# 启动/停止/重启
sudo systemctl start intent-test-framework
sudo systemctl stop intent-test-framework
sudo systemctl restart intent-test-framework

# 查看状态
sudo systemctl status intent-test-framework

# 查看日志
sudo journalctl -u intent-test-framework -f
```

## 常见问题

### 服务无法启动
```bash
# 查看详细日志
sudo journalctl -u intent-test-framework -n 100

# 检查环境变量
sudo -u appuser cat /opt/intent-test-framework/.env
```

### 无法访问网站
```bash
# 检查Nginx状态
sudo systemctl status nginx
sudo nginx -t

# 检查端口
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :5001
```

### 数据库连接失败
```bash
# 检查PostgreSQL
sudo systemctl status postgresql

# 测试连接
psql -U intent_user -d intent_test_framework -h localhost
```

## 详细文档

更多信息请参考：
- `DEPLOYMENT.md` - 详细部署文档
- `README.md` - 脚本说明


