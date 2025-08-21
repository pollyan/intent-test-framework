#!/bin/bash

# 修复任何版本的本地代理包依赖问题
# 支持自动检测和修复多个代理包目录

echo "🔧 正在查找并修复本地代理包的依赖问题..."

# 查找所有可能的代理包目录
PROXY_DIRS=(
    "/Users/huian@thoughtworks.com/Downloads/intent-test-proxy"
    "/Users/huian@thoughtworks.com/Downloads/intent-test-proxy 2"
    "/Users/huian@thoughtworks.com/Downloads/intent-test-proxy 3"
    "/Users/huian@thoughtworks.com/Downloads/intent-test-proxy 4"
    "/Users/huian@thoughtworks.com/Downloads/intent-test-proxy 5"
)

FOUND_DIRS=()

# 检查哪些目录存在
for dir in "${PROXY_DIRS[@]}"; do
    if [ -d "$dir" ]; then
        FOUND_DIRS+=("$dir")
    fi
done

if [ ${#FOUND_DIRS[@]} -eq 0 ]; then
    echo "❌ 未找到任何本地代理包目录"
    echo "请确保已下载代理包到 Downloads 目录"
    exit 1
fi

echo "📁 找到以下代理包目录:"
for i in "${!FOUND_DIRS[@]}"; do
    echo "  [$((i+1))] ${FOUND_DIRS[i]}"
done

# 如果只有一个目录，直接修复
if [ ${#FOUND_DIRS[@]} -eq 1 ]; then
    SELECTED_DIR="${FOUND_DIRS[0]}"
    echo ""
    echo "🎯 自动选择: $SELECTED_DIR"
else
    # 多个目录，让用户选择
    echo ""
    echo "请选择要修复的代理包 (1-${#FOUND_DIRS[@]}), 或输入 'a' 修复所有:"
    read -r choice
    
    if [ "$choice" = "a" ] || [ "$choice" = "A" ]; then
        echo "🔄 将修复所有找到的代理包..."
        for dir in "${FOUND_DIRS[@]}"; do
            fix_proxy_directory "$dir"
        done
        exit 0
    elif [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#FOUND_DIRS[@]} ]; then
        SELECTED_DIR="${FOUND_DIRS[$((choice-1))]}"
        echo ""
        echo "🎯 选择修复: $SELECTED_DIR"
    else
        echo "❌ 无效选择"
        exit 1
    fi
fi

# 修复指定目录的函数
fix_proxy_directory() {
    local PROXY_DIR="$1"
    
    echo ""
    echo "🔧 正在修复: $PROXY_DIR"
    echo "=========================="
    
    # 1. 备份原有的 package.json
    echo "📋 备份原有配置..."
    if [ -f "$PROXY_DIR/package.json" ]; then
        cp "$PROXY_DIR/package.json" "$PROXY_DIR/package.json.backup"
    fi
    
    # 2. 更新 package.json 为正确的依赖
    echo "🔧 更新package.json..."
    cat > "$PROXY_DIR/package.json" << 'EOF'
{
  "name": "intent-test-proxy",
  "version": "1.0.0",
  "description": "Intent Test Framework 本地代理服务器",
  "main": "midscene_server.js",
  "scripts": {
    "start": "node midscene_server.js",
    "install-deps": "npm install"
  },
  "dependencies": {
    "@midscene/web": "^0.20.1",
    "@playwright/test": "^1.45.0",
    "axios": "^1.10.0",
    "cors": "^2.8.5",
    "express": "^4.18.2",
    "playwright": "^1.45.0",
    "socket.io": "^4.7.0"
  },
  "devDependencies": {
    "@types/node": "^20.0.0"
  },
  "keywords": ["midscene", "automation", "testing", "ai"],
  "author": "Intent Test Framework",
  "license": "MIT"
}
EOF
    
    # 3. 复制最新的服务器文件
    echo "📄 复制最新的midscene_server.js..."
    cp "/Users/huian@thoughtworks.com/intent-test-framework/midscene_server.js" "$PROXY_DIR/midscene_server.js"
    
    # 4. 更新启动脚本
    echo "🔄 更新启动脚本..."
    cat > "$PROXY_DIR/start.sh" << 'EOF'
#!/bin/bash

# Intent Test Framework 本地代理服务器启动脚本

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo ""
echo "========================================"
echo "  Intent Test Framework 本地代理服务器"
echo "========================================"
echo ""

# 检查Node.js
echo -e "${BLUE}[1/4]${NC} 检查Node.js环境..."
if ! command -v node &> /dev/null; then
    echo -e "${RED}❌ 错误: 未检测到Node.js${NC}"
    echo ""
    echo "请先安装Node.js:"
    echo "https://nodejs.org/"
    echo ""
    echo "建议安装LTS版本 (16.x或更高)"
    exit 1
fi

NODE_VERSION=$(node --version)
echo -e "${GREEN}✅ Node.js版本: $NODE_VERSION${NC}"

# 检查npm
if ! command -v npm &> /dev/null; then
    echo -e "${RED}❌ 错误: npm未找到${NC}"
    exit 1
fi

# 检查和安装依赖
echo ""
echo -e "${BLUE}[2/4]${NC} 检查依赖包..."

# 检查关键依赖是否存在
PLAYWRIGHT_TEST_MISSING=false
AXIOS_MISSING=false

if [ ! -d "node_modules/@playwright/test" ]; then
    PLAYWRIGHT_TEST_MISSING=true
fi

if [ ! -d "node_modules/axios" ]; then
    AXIOS_MISSING=true
fi

# 如果关键依赖缺失或node_modules不存在，则重新安装
if [ ! -d "node_modules" ] || [ "$PLAYWRIGHT_TEST_MISSING" = true ] || [ "$AXIOS_MISSING" = true ]; then
    echo -e "${YELLOW}📦 安装/更新依赖包...${NC}"
    echo "这可能需要几分钟时间，请耐心等待..."
    
    # 清理旧的依赖
    if [ -d "node_modules" ]; then
        echo -e "${YELLOW}🧹 清理旧依赖...${NC}"
        rm -rf node_modules package-lock.json
    fi
    
    # 安装依赖
    npm install
    if [ $? -ne 0 ]; then
        echo -e "${RED}❌ 依赖安装失败${NC}"
        echo ""
        echo "可能的解决方案:"
        echo "1. 检查网络连接"
        echo "2. 清理npm缓存: npm cache clean --force"
        echo "3. 使用国内镜像: npm config set registry https://registry.npmmirror.com"
        exit 1
    fi
    
    # 验证关键依赖
    if [ ! -d "node_modules/@playwright/test" ]; then
        echo -e "${RED}❌ @playwright/test 依赖安装失败${NC}"
        exit 1
    fi
    
    if [ ! -d "node_modules/axios" ]; then
        echo -e "${RED}❌ axios 依赖安装失败${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✅ 依赖安装完成${NC}"
else
    echo -e "${GREEN}✅ 依赖包已存在${NC}"
fi

# 检查配置文件
echo ""
echo -e "${BLUE}[3/4]${NC} 检查配置文件..."
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚙️ 首次运行，创建配置文件...${NC}"
    cp .env.example .env
    echo ""
    echo -e "${YELLOW}⚠️  重要: 请配置AI API密钥${NC}"
    echo ""
    echo "配置文件已创建: .env"
    echo "请编辑此文件，添加您的AI API密钥"
    echo ""
    echo "配置完成后，请重新运行此脚本"
    echo ""
    echo "编辑配置文件: nano .env"
    exit 0
fi

echo -e "${GREEN}✅ 配置文件存在${NC}"

# 启动服务器
echo ""
echo -e "${BLUE}[4/4]${NC} 启动服务器..."
echo ""
echo -e "${GREEN}🚀 正在启动Intent Test Framework本地代理服务器...${NC}"
echo ""
echo "启动成功后，请返回Web界面选择"本地代理模式""
echo "按 Ctrl+C 可停止服务器"
echo ""

node midscene_server.js

echo ""
echo "服务器已停止"
EOF
    
    # 设置执行权限
    chmod +x "$PROXY_DIR/start.sh"
    
    # 5. 确保环境文件存在
    echo "⚙️ 检查环境配置文件..."
    if [ ! -f "$PROXY_DIR/.env.example" ]; then
        cat > "$PROXY_DIR/.env.example" << 'EOF'
# AI API 配置
OPENAI_API_KEY=your-api-key-here
OPENAI_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MIDSCENE_MODEL_NAME=qwen-vl-max-latest

# 数据库配置（可选，本地代理默认连接到主系统）
API_BASE_URL=http://localhost:5001/api
EOF
    fi
    
    # 6. 清理并重新安装依赖
    echo "🧹 清理旧依赖..."
    cd "$PROXY_DIR"
    rm -rf node_modules package-lock.json
    
    echo "📦 重新安装依赖..."
    npm install
    
    if [ $? -eq 0 ]; then
        echo "✅ 依赖安装成功！"
        
        # 7. 验证关键依赖
        echo "🔍 验证关键依赖..."
        
        if [ ! -d "node_modules/@playwright/test" ]; then
            echo "❌ @playwright/test 依赖验证失败"
            return 1
        fi
        
        if [ ! -d "node_modules/axios" ]; then
            echo "❌ axios 依赖验证失败"
            return 1
        fi
        
        echo "✅ 所有依赖验证通过！"
        
        # 8. 测试服务器启动
        echo "🧪 测试服务器启动..."
        timeout 5s node midscene_server.js > /dev/null 2>&1
        if [ $? -eq 124 ]; then
            echo "✅ 服务器启动测试通过！"
        else
            echo "❌ 服务器启动测试失败"
            return 1
        fi
        
        echo ""
        echo "🎉 代理包修复完成: $PROXY_DIR"
        echo ""
        return 0
    else
        echo "❌ 依赖安装失败"
        return 1
    fi
}

# 修复选定的目录
fix_proxy_directory "$SELECTED_DIR"

if [ $? -eq 0 ]; then
    echo ""
    echo "🎯 修复成功！现在可以使用以下命令启动:"
    echo "   cd '$SELECTED_DIR'"
    echo "   ./start.sh"
    echo ""
else
    echo "❌ 修复失败，请检查错误信息"
    exit 1
fi