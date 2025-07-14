#!/bin/bash
"""
Git Hooks 设置脚本
用于设置项目的Git钩子，确保代码质量

使用方法:
    chmod +x scripts/setup_git_hooks.sh
    ./scripts/setup_git_hooks.sh
"""

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="$PROJECT_ROOT/.git/hooks"

echo "🔧 设置Git Hooks..."

# 创建pre-commit钩子
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook for code quality checks

echo "🔍 运行代码质量检查..."

# 运行质量检查脚本
python scripts/quality_check.py

if [ $? -ne 0 ]; then
    echo "❌ 代码质量检查失败，请修复问题后再提交"
    echo "💡 提示: 可以运行 'python scripts/quality_check.py --fix' 自动修复部分问题"
    exit 1
fi

echo "✅ 代码质量检查通过"

# 检查提交信息格式（在commit-msg钩子中处理）
exit 0
EOF

# 创建commit-msg钩子
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
# Commit message format checker

commit_regex='^(feat|fix|docs|style|refactor|test|chore)(\(.+\))?: .{1,50}'

if ! grep -qE "$commit_regex" "$1"; then
    echo "❌ 提交信息格式不正确"
    echo "📋 正确格式: <type>(<scope>): <subject>"
    echo "📋 类型: feat, fix, docs, style, refactor, test, chore"
    echo "📋 示例: feat(webui): 添加截图历史功能"
    echo "📋 示例: fix(api): 修复测试用例删除接口错误"
    exit 1
fi

echo "✅ 提交信息格式正确"
exit 0
EOF

# 创建pre-push钩子
cat > "$HOOKS_DIR/pre-push" << 'EOF'
#!/bin/bash
# Pre-push hook for additional checks

echo "🚀 运行推送前检查..."

# 运行测试
if [ -f "tests/run_tests.py" ]; then
    echo "🧪 运行测试套件..."
    python tests/run_tests.py
    if [ $? -ne 0 ]; then
        echo "❌ 测试失败，请修复后再推送"
        exit 1
    fi
    echo "✅ 测试通过"
fi

# 检查敏感信息
echo "🔒 检查敏感信息..."
if git diff --cached --name-only | xargs grep -l "password\|api_key\|secret" 2>/dev/null; then
    echo "⚠️ 警告: 检测到可能的敏感信息，请确认是否安全"
    echo "如果确认安全，请使用 git push --no-verify 跳过检查"
    # 不阻止推送，只是警告
fi

echo "✅ 推送前检查完成"
exit 0
EOF

# 设置钩子文件为可执行
chmod +x "$HOOKS_DIR/pre-commit"
chmod +x "$HOOKS_DIR/commit-msg"
chmod +x "$HOOKS_DIR/pre-push"

echo "✅ Git Hooks 设置完成！"
echo ""
echo "📋 已设置的钩子:"
echo "  - pre-commit: 代码质量检查"
echo "  - commit-msg: 提交信息格式检查"
echo "  - pre-push: 推送前测试和安全检查"
echo ""
echo "💡 提示:"
echo "  - 使用 'git commit --no-verify' 可以跳过pre-commit检查"
echo "  - 使用 'git push --no-verify' 可以跳过pre-push检查"
echo "  - 建议在开发过程中定期运行 'python scripts/quality_check.py'"
