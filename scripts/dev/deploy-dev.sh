#!/bin/bash
set -e

# ========================================
# 本地开发环境增量部署脚本
# ========================================

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$PROJECT_ROOT"

echo "📂 项目根目录: $PROJECT_ROOT"

# ========================================
# 1. 环境检查
# ========================================

# 检查 .env 文件
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "⚠️  未找到 .env，从 .env.example 复制..."
        cp .env.example .env
        echo "✅ .env 已创建，请稍后检查配置"
    else
        echo "❌ 未找到 .env 或 .env.example，无法继续"
        exit 1
    fi
fi

# ========================================
# 2. 启动服务
# ========================================

MODE="incremental"
DOCKER_BUILD_ARGS="--build"

# 解析参数
if [[ "$1" == "full" ]] || [[ "$1" == "--full" ]]; then
    MODE="full-rebuild"
    echo "🧹 检测到全量重建模式，正在清理旧资源..."
    docker-compose -f docker-compose.dev.yml down --rmi local --remove-orphans
    DOCKER_BUILD_ARGS="--build --force-recreate"
    # 这里也可以加上 --no-cache，如果想极致干净，但通常 --force-recreate + down 已经足够
    # 如果用户非常明确要无缓存，可以解开下行注释
    # DOCKER_BUILD_ARGS="--build --no-cache"
fi

echo "🚀 正在启动本地 Docker 环境..."
echo "   配置文件: docker-compose.dev.yml"
echo "   模式: $MODE"

if [[ "$MODE" == "full-rebuild" ]]; then
    echo "   ⚠️ 全量模式下会强制重新构建所有镜像（不使用缓存）"
    # 全量模式我们显式使用 build --no-cache
    docker-compose -f docker-compose.dev.yml build --no-cache
    docker-compose -f docker-compose.dev.yml up -d
else
    # 增量模式
    echo "   (仅在 Dockerfile 变更时重建)"
    docker-compose -f docker-compose.dev.yml up -d --build
fi

# ========================================
# 3. 状态检查
# ========================================

echo ""
echo "⏳ 等待服务健康检查..."
# 简单休眠等待 docker完成启动
sleep 5

docker-compose -f docker-compose.dev.yml ps

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 服务启动完成！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📍 访问入口:"
echo "   🏠 主页: http://localhost"
echo "   🤖 AI 智能体: http://localhost/ai-agents"
echo "   🧪 意图测试: http://localhost/intent-tester"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💡 常用命令:"
echo "   查看日志: docker-compose -f docker-compose.dev.yml logs -f"
echo "   停止服务: docker-compose -f docker-compose.dev.yml down"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
