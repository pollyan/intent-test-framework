#!/bin/bash

# Intent Test Framework - 本地测试运行脚本
# 使用方法: ./scripts/test-local.sh [options]

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 默认配置
COVERAGE_THRESHOLD=80
VERBOSE=true
PARALLEL=false
FAST_MODE=false
CLEAN_CACHE=false
OPEN_COVERAGE=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        --parallel|-p)
            PARALLEL=true
            shift
            ;;
        --fast|-f)
            FAST_MODE=true
            shift
            ;;
        --clean|-c)
            CLEAN_CACHE=true
            shift
            ;;
        --quiet|-q)
            VERBOSE=false
            shift
            ;;
        --open-coverage|-o)
            OPEN_COVERAGE=true
            shift
            ;;
        --coverage-threshold)
            COVERAGE_THRESHOLD="$2"
            shift 2
            ;;
        --help|-h)
            echo "用法: $0 [选项]"
            echo ""
            echo "选项:"
            echo "  --parallel, -p           启用并行测试执行"
            echo "  --fast, -f              快速模式（跳过慢测试）"
            echo "  --clean, -c             清理缓存后运行测试"
            echo "  --quiet, -q             静默模式"
            echo "  --open-coverage, -o     测试完成后打开覆盖率报告"
            echo "  --coverage-threshold N  设置覆盖率阈值 (默认: 80)"
            echo "  --help, -h              显示此帮助信息"
            echo ""
            echo "示例:"
            echo "  $0                      # 运行标准测试"
            echo "  $0 --fast --parallel    # 快速并行测试"
            echo "  $0 --clean --open-coverage  # 清理缓存并打开覆盖率报告"
            exit 0
            ;;
        *)
            echo "未知选项: $1"
            echo "使用 --help 查看可用选项"
            exit 1
            ;;
    esac
done

# 打印函数
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

# 检查必要工具
check_requirements() {
    print_header "检查测试环境"
    
    # 检查Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 未找到，请安装 Python 3.8+"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    print_success "Python 版本: $PYTHON_VERSION"
    
    # 检查pytest
    if ! python3 -m pytest --version &> /dev/null; then
        print_warning "pytest 未找到，正在安装..."
        pip install pytest pytest-cov pytest-mock pytest-asyncio
    fi
    
    # 检查Node.js（用于proxy测试）
    if command -v node &> /dev/null; then
        NODE_VERSION=$(node --version)
        print_success "Node.js 版本: $NODE_VERSION"
    else
        print_warning "Node.js 未找到，将跳过proxy测试"
    fi
    
    # 检查项目结构
    if [[ ! -f "web_gui/app_enhanced.py" ]]; then
        print_error "项目结构异常，请在项目根目录运行此脚本"
        exit 1
    fi
    
    print_success "环境检查通过"
}

# 清理缓存
clean_cache() {
    if [[ "$CLEAN_CACHE" == true ]]; then
        print_header "清理测试缓存"
        
        # 清理Python缓存
        find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
        find . -name "*.pyc" -delete 2>/dev/null || true
        
        # 清理pytest缓存
        rm -rf .pytest_cache 2>/dev/null || true
        
        # 清理覆盖率缓存
        rm -rf .coverage htmlcov 2>/dev/null || true
        
        # 清理Node.js缓存
        if [[ -d "node_modules" ]]; then
            rm -rf coverage 2>/dev/null || true
        fi
        
        print_success "缓存清理完成"
    fi
}

# 设置测试环境
setup_test_env() {
    print_header "设置测试环境"
    
    # 创建测试环境配置
    cat << EOF > .env.test
# Local Test Configuration
DATABASE_URL=sqlite:///:memory:
FLASK_ENV=testing
DEBUG=false
SECRET_KEY=local_test_secret_key
TESTING=true

# AI Service Mock Configuration
OPENAI_API_KEY=test_key
OPENAI_BASE_URL=http://mock-ai-service
MIDSCENE_MODEL_NAME=mock-model

# Test Optimization
WTF_CSRF_ENABLED=false
LOGIN_DISABLED=true
LOG_LEVEL=WARNING
EOF

    print_success "测试环境配置完成"
    
    # 设置环境变量
    export $(cat .env.test | grep -v '^#' | xargs)
    export PYTHONPATH="${PYTHONPATH}:$(pwd)"
}

# 运行API测试
run_api_tests() {
    print_header "运行API测试"
    
    # 构建pytest参数
    PYTEST_ARGS="tests/api/"
    
    if [[ "$VERBOSE" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS --verbose"
    else
        PYTEST_ARGS="$PYTEST_ARGS --quiet"
    fi
    
    # 添加覆盖率参数
    PYTEST_ARGS="$PYTEST_ARGS --cov=web_gui --cov-report=html --cov-report=term-missing"
    PYTEST_ARGS="$PYTEST_ARGS --cov-fail-under=$COVERAGE_THRESHOLD"
    
    # 快速模式
    if [[ "$FAST_MODE" == true ]]; then
        PYTEST_ARGS="$PYTEST_ARGS -m 'not slow' --maxfail=5"
        print_info "快速模式：跳过慢测试"
    fi
    
    # 并行执行
    if [[ "$PARALLEL" == true ]]; then
        # 检查是否安装了pytest-xdist
        if python3 -m pytest --help | grep -q "pytest-xdist"; then
            PYTEST_ARGS="$PYTEST_ARGS -n auto"
            print_info "并行模式：自动检测CPU核心数"
        else
            print_warning "pytest-xdist 未安装，跳过并行执行"
            print_info "安装命令: pip install pytest-xdist"
        fi
    fi
    
    # 添加其他有用的参数
    PYTEST_ARGS="$PYTEST_ARGS --tb=short --durations=10 --strict-markers"
    
    print_info "执行命令: python -m pytest $PYTEST_ARGS"
    
    # 运行测试
    if python -m pytest $PYTEST_ARGS; then
        print_success "API测试全部通过！"
        API_TESTS_PASSED=true
    else
        print_error "API测试失败"
        API_TESTS_PASSED=false
    fi
}

# 运行Node.js proxy测试
run_proxy_tests() {
    if command -v npm &> /dev/null && [[ -f "package.json" ]]; then
        print_header "运行Node.js Proxy测试"
        
        if npm test; then
            print_success "Proxy测试全部通过！"
            PROXY_TESTS_PASSED=true
        else
            print_warning "Proxy测试失败"
            PROXY_TESTS_PASSED=false
        fi
    else
        print_info "跳过Node.js Proxy测试（npm或package.json未找到）"
        PROXY_TESTS_PASSED=true
    fi
}

# 生成测试报告
generate_report() {
    print_header "测试报告"
    
    echo "📊 测试结果总结:"
    if [[ "$API_TESTS_PASSED" == true ]]; then
        print_success "API测试: 通过"
    else
        print_error "API测试: 失败"
    fi
    
    if [[ "$PROXY_TESTS_PASSED" == true ]]; then
        print_success "Proxy测试: 通过"
    else
        print_error "Proxy测试: 失败"
    fi
    
    # 显示覆盖率信息
    if [[ -f "htmlcov/index.html" ]]; then
        print_info "HTML覆盖率报告已生成: htmlcov/index.html"
        
        if [[ "$OPEN_COVERAGE" == true ]]; then
            if command -v open &> /dev/null; then
                open htmlcov/index.html
                print_success "已在浏览器中打开覆盖率报告"
            elif command -v xdg-open &> /dev/null; then
                xdg-open htmlcov/index.html
                print_success "已在浏览器中打开覆盖率报告"
            else
                print_info "无法自动打开浏览器，请手动打开: htmlcov/index.html"
            fi
        fi
    fi
    
    # 提供改进建议
    if [[ "$API_TESTS_PASSED" != true || "$PROXY_TESTS_PASSED" != true ]]; then
        echo ""
        print_warning "测试失败，建议操作："
        echo "  1. 检查测试日志中的错误信息"
        echo "  2. 运行 ./scripts/test-local.sh --clean 清理缓存后重试"
        echo "  3. 检查代码变更是否影响了现有功能"
        echo "  4. 查看 tests/README.md 获取更多测试指南"
    else
        echo ""
        print_success "所有测试通过！可以安全提交代码 🚀"
        
        echo ""
        echo "💡 提交代码前建议："
        echo "  1. 运行代码质量检查: python scripts/quality_check.py"
        echo "  2. 检查代码覆盖率是否满足要求"
        echo "  3. 确保所有新功能都有对应的测试"
    fi
}

# 主函数
main() {
    echo -e "${GREEN}🧪 Intent Test Framework - 本地测试套件${NC}"
    echo "开始时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo ""
    
    # 记录开始时间
    START_TIME=$(date +%s)
    
    # 执行测试流程
    check_requirements
    clean_cache
    setup_test_env
    run_api_tests
    run_proxy_tests
    
    # 计算运行时间
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    
    echo ""
    print_info "总耗时: ${DURATION}秒"
    
    generate_report
    
    # 设置退出码
    if [[ "$API_TESTS_PASSED" == true && "$PROXY_TESTS_PASSED" == true ]]; then
        exit 0
    else
        exit 1
    fi
}

# 运行主函数
main "$@"