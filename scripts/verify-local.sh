#!/bin/bash
# 验证部署脚本 - 检查部署是否成功

set -e

echo "========================================"
echo "  验证本地 Docker 环境"
echo "========================================"
echo ""

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

PASSED=0
FAILED=0

# 测试 1: 容器运行状态
echo -e "${YELLOW}[测试 1]${NC} 检查容器状态..."
if docker ps | grep -q "intent-test-web.*healthy"; then
    echo -e "${GREEN}✓${NC} Web 容器运行正常"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Web 容器异常"
    ((FAILED++))
fi

if docker ps | grep -q "intent-test-db.*healthy"; then
    echo -e "${GREEN}✓${NC} 数据库容器运行正常"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} 数据库容器异常"
    ((FAILED++))
fi
echo ""

# 测试 2: Web 服务响应
echo -e "${YELLOW}[测试 2]${NC} 检查 Web 服务..."
if curl -s http://localhost:5001/health | grep -q "ok"; then
    echo -e "${GREEN}✓${NC} Health 端点响应正常"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Health 端点无响应"
    ((FAILED++))
fi
echo ""

# 测试 3: Lisa 模块加载
echo -e "${YELLOW}[测试 3]${NC} 检查 Lisa 模块..."
if docker exec intent-test-web python3 -c "
from web_gui.services.langgraph_agents.lisa_v2.graph import create_lisa_v2_graph
create_lisa_v2_graph()
print('OK')
" 2>&1 | grep -q "OK"; then
    echo -e "${GREEN}✓${NC} Lisa 模块加载成功"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} Lisa 模块加载失败"
    echo "错误详情："
    docker exec intent-test-web python3 -c "
from web_gui.services.langgraph_agents.lisa_v2.graph import create_lisa_v2_graph
create_lisa_v2_graph()
" 2>&1 || true
    ((FAILED++))
fi
echo ""

# 测试 4: 数据库连接
echo -e "${YELLOW}[测试 4]${NC} 检查数据库连接..."
if docker exec intent-test-db psql -U postgres -d test_intent -c "SELECT 1;" >/dev/null 2>&1; then
    echo -e "${GREEN}✓${NC} 数据库连接正常"
    ((PASSED++))
else
    echo -e "${RED}✗${NC} 数据库连接失败"
    ((FAILED++))
fi
echo ""

# 总结
echo "========================================"
if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ 所有测试通过 ($PASSED/$((PASSED+FAILED)))${NC}"
    echo "========================================"
    exit 0
else
    echo -e "${RED}✗ 部分测试失败 (通过: $PASSED, 失败: $FAILED)${NC}"
    echo "========================================"
    echo ""
    echo "调试建议："
    echo "  1. 查看容器日志: docker logs intent-test-web --tail=100"
    echo "  2. 检查容器状态: docker ps -a"
    echo "  3. 重新部署: ./scripts/deploy-local.sh"
    exit 1
fi
