---
trigger: always_on
---

# 规则
- 应该遵循良好的 devops 实践，本地环境与云端环境保持一致的部署方式。云端环境通过 github action 来实现部署，不要直连云端服务器来完成部署。
- 永远不要用关键词的方法来做智能体的逻辑判断，要根据上下文与语义综合判断。


# 架构
- MidScene Server代理服务器是启动在客户端本地的，配合服务器端的web系统来实现自动化测试，驱动客户端浏览器运行。
- 启动和更新本地 Docker 测试环境的时候要用 scripts 文件夹下的部署脚本来做，不要直接操作 docker。
- 模块化单体: 项目采用模块化结构，核心业务逻辑应封装在 tools/ 下的独立模块中（如 intent-tester, ai-agents）。
- 共享代码: 通用工具类、基类应放置在 tools/shared 或根目录的通用 backend/utils 中，避免代码复制。
