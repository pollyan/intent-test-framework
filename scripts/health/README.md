# 部署后健康检查脚本

## 概述

此脚本用于验证系统部署后的健康状态，包括本地 Docker 环境和腾讯云生产环境。

## 用法

```bash
# 本地环境检查
./scripts/health/health_check.sh local

# 生产环境检查
./scripts/health/health_check.sh production
```

## 检查项目

### 1. Docker 容器状态
- ai4se-db (PostgreSQL 数据库)
- ai4se-intent-tester (意图测试工具)
- ai4se-agents (AI 智能体)
- ai4se-gateway (Nginx 网关)

### 2. 数据库连通性
- 验证 PostgreSQL 服务可用性
- 确认数据库接受连接

### 3. 页面 HTTP 访问 (8 个页面)
| 路径 | 说明 |
|------|------|
| `/` | 首页 |
| `/profile` | 个人资料页 |
| `/intent-tester/` | 意图测试首页 |
| `/intent-tester/testcases` | 测试用例列表 |
| `/intent-tester/execution` | 执行控制台 |
| `/intent-tester/local-proxy` | 本地代理页 |
| `/ai-agents/` | AI 智能体首页 |
| `/ai-agents/config` | AI 配置页面 |

### 4. 核心 API 端点 (5 个端点)
| 端点 | 说明 |
|------|------|
| `/health` | Nginx 网关健康检查 |
| `/intent-tester/health` | Intent Tester 健康检查 |
| `/ai-agents/health` | AI Agents 健康检查 |
| `/intent-tester/api/testcases` | 测试用例 API |
| `/ai-agents/api/ai-configs/test` | AI 配置测试 API |

## 退出码

- `0`: 所有检查通过
- `1`: 有检查项失败

## 集成

该脚本已集成到：
- `scripts/dev/deploy-dev.sh` - 本地部署
- `scripts/ci/deploy.sh` - 生产部署
- `.github/workflows/deploy.yml` - CI/CD 流水线
