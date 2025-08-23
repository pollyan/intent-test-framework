#!/bin/bash

# Intent Test Framework - 测试依赖安装脚本
# 自动安装Python和Node.js测试依赖

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# 检查并安装Python测试依赖
install_python_test_deps() {
    print_header "安装Python测试依赖"
    
    # 基础测试框架
    print_info "安装pytest相关包..."
    pip install pytest pytest-cov pytest-mock pytest-asyncio pytest-html
    
    # 性能测试
    print_info "安装性能测试包..."
    pip install pytest-benchmark pytest-xdist
    
    # 测试数据工厂
    print_info "安装测试数据工厂..."
    pip install factory-boy faker
    
    # Flask测试支持
    print_info "安装Flask测试支持..."
    pip install pytest-flask
    
    # 覆盖率配置
    print_info "安装覆盖率工具..."
    pip install coverage[toml]
    
    print_success "Python测试依赖安装完成"
}

# 检查并安装Node.js测试依赖
install_nodejs_test_deps() {
    print_header "安装Node.js测试依赖"
    
    if ! command -v npm &> /dev/null; then
        print_warning "npm未找到，跳过Node.js依赖安装"
        return
    fi
    
    # 安装测试依赖
    print_info "安装Jest测试框架..."
    npm install --save-dev jest jest-environment-node
    
    print_info "安装HTTP测试工具..."
    npm install --save-dev supertest superagent
    
    print_info "安装测试报告工具..."
    npm install --save-dev jest-junit
    
    print_info "安装WebSocket测试工具..."
    npm install --save-dev ws socket.io-client
    
    print_success "Node.js测试依赖安装完成"
}

# 安装系统级测试工具
install_system_test_tools() {
    print_header "检查系统测试工具"
    
    # 检查PostgreSQL客户端（用于CI测试）
    if ! command -v psql &> /dev/null; then
        print_warning "PostgreSQL客户端未找到"
        print_info "在CI环境中会自动安装"
    else
        print_success "PostgreSQL客户端已安装"
    fi
    
    # 检查Playwright浏览器
    print_info "检查Playwright浏览器..."
    if npx playwright --help &> /dev/null; then
        npx playwright install chromium --with-deps
        print_success "Playwright浏览器安装完成"
    else
        print_warning "Playwright未找到，请运行: npm install"
    fi
}

# 创建测试配置文件
setup_test_config() {
    print_header "设置测试配置"
    
    # 创建pytest配置（如果不存在）
    if [[ ! -f "tests/pytest.ini" ]]; then
        print_info "创建pytest.ini配置文件..."
        cat << 'EOF' > tests/pytest.ini
[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts = 
    --verbose
    --tb=short
    --strict-markers
    --disable-warnings
markers =
    api: API集成测试
    unit: 单元测试
    slow: 慢速测试
    integration: 集成测试
    smoke: 冒烟测试
filterwarnings =
    ignore::DeprecationWarning
    ignore::PendingDeprecationWarning
EOF
        print_success "pytest配置文件已创建"
    fi
    
    # 创建覆盖率配置
    if [[ ! -f ".coveragerc" ]]; then
        print_info "创建覆盖率配置文件..."
        cat << 'EOF' > .coveragerc
[run]
source = web_gui
omit = 
    */tests/*
    */venv/*
    */site-packages/*
    web_gui/run_enhanced.py
    web_gui/wsgi.py

[report]
exclude_lines =
    pragma: no cover
    def __repr__
    if self.debug:
    if settings.DEBUG
    raise AssertionError
    raise NotImplementedError
    if 0:
    if __name__ == .__main__.:
    class .*\bProtocol\):
    @(abc\.)?abstractmethod

[html]
directory = htmlcov
EOF
        print_success "覆盖率配置文件已创建"
    fi
}

# 验证安装
verify_installation() {
    print_header "验证测试环境"
    
    # 验证Python测试工具
    print_info "验证pytest..."
    if python -m pytest --version; then
        print_success "pytest验证通过"
    else
        print_error "pytest验证失败"
        exit 1
    fi
    
    # 验证覆盖率工具
    print_info "验证coverage..."
    if python -m coverage --version; then
        print_success "coverage验证通过"
    else
        print_error "coverage验证失败"
        exit 1
    fi
    
    # 验证Node.js测试工具
    if command -v npm &> /dev/null; then
        print_info "验证jest..."
        if npx jest --version; then
            print_success "jest验证通过"
        else
            print_warning "jest验证失败（可能需要运行npm install）"
        fi
    fi
    
    print_success "测试环境验证完成"
}

# 主函数
main() {
    echo -e "${GREEN}🔧 Intent Test Framework - 测试依赖安装器${NC}"
    echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 检查Python环境
    if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
        print_error "Python未找到，请先安装Python 3.8+"
        exit 1
    fi
    
    # 检查pip
    if ! command -v pip &> /dev/null; then
        print_error "pip未找到，请先安装pip"
        exit 1
    fi
    
    # 执行安装流程
    install_python_test_deps
    install_nodejs_test_deps  
    install_system_test_tools
    setup_test_config
    verify_installation
    
    echo ""
    print_success "测试环境配置完成！"
    echo ""
    echo "💡 下一步："
    echo "  1. 复制 .env.example 到 .env 并配置"
    echo "  2. 运行测试: ./scripts/test-local.sh"
    echo "  3. 查看覆盖率报告: ./scripts/test-local.sh --open-coverage"
}

# 运行主函数
main "$@"