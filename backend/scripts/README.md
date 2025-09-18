# 后端脚本目录

这个目录包含了用于开发和管理的脚本文件。

## 脚本说明

### 🚀 dev_server.py - 开发服务器
统一的开发服务器启动脚本，整合了原来分散的多个启动文件。

**用法**:
```bash
# 启动主API服务器 (默认端口8080)
python scripts/dev_server.py

# 启动简化测试服务器 (默认端口8083)
python scripts/dev_server.py --mode simple

# 启动新闻搜索测试服务器 (默认端口8082)
python scripts/dev_server.py --mode news

# 自定义端口
python scripts/dev_server.py --mode main --port 9000

# 禁用自动重载
python scripts/dev_server.py --no-reload
```

**模式说明**:
- **main**: 完整的主API服务器，包含所有功能
- **simple**: 简化的测试服务器，只提供基本股票信息API
- **news**: 新闻搜索测试服务器，用于测试新闻功能

### 🛠️ manage.py - 项目管理
提供常用的开发和维护命令。

**用法**:
```bash
# 显示项目信息
python scripts/manage.py info

# 运行所有测试
python scripts/manage.py test

# 运行特定类型的测试
python scripts/manage.py test --type unit
python scripts/manage.py test --type integration

# 检查服务状态
python scripts/manage.py check

# 启动开发服务器
python scripts/manage.py server --mode main
python scripts/manage.py server --mode simple --port 9000
```

## 整合说明

这些脚本整合了原来backend根目录下的以下文件：
- `start_server.py` → 整合到 `dev_server.py` (main模式)
- `simple_api.py` → 整合到 `dev_server.py` (simple模式)  
- `minimal_api.py` → 整合到 `dev_server.py` (news模式)

## 优势

1. **统一管理**: 所有开发脚本集中在scripts目录
2. **功能整合**: 减少重复代码，统一接口
3. **易于维护**: 单一入口点，便于修改和扩展
4. **清晰结构**: 项目根目录更加整洁
5. **灵活配置**: 支持多种模式和自定义参数

## 开发工作流

1. **开发阶段**: 使用 `dev_server.py --mode main` 启动完整服务器
2. **功能测试**: 使用 `dev_server.py --mode simple` 进行快速测试
3. **新闻测试**: 使用 `dev_server.py --mode news` 测试新闻功能
4. **运行测试**: 使用 `manage.py test` 执行测试套件
5. **状态检查**: 使用 `manage.py check` 验证服务状态