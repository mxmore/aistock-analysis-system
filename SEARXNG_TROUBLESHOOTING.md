# SearXNG 故障排除指南# SearXNG 故障排除指南



## 当前问题## 当前问题

SearXNG 返回 403 Forbidden 错误，这是由于安全限制导致的。

SearXNG 返回 403 Forbidden 错误，这是由于安全限制导致的。

## 解决方案

## 方案1: 修复Docker Desktop问题

### 方案1: 修复Docker Desktop问题

1. 重启Docker Desktop应用程序1. 重启Docker Desktop应用程序

2. 等待Docker Desktop完全启动2. 等待Docker Desktop完全启动

3. 重新运行测试3. 重新运行测试



## 方案2: 手动启动SearXNG### 方案2: 手动启动SearXNG

如果Docker Desktop无法正常工作，可以手动启动SearXNG：

如果Docker Desktop无法正常工作，可以手动启动SearXNG：

```bash

```bash# 进入项目目录

# 进入项目目录cd d:\workspace\mpj\aistock-full-project

cd d:\workspace\mpj\aistock-full-project

# 启动所有服务

# 启动所有服务docker-compose -f docker-compose.local.yml up -d

docker-compose -f docker-compose.local.yml up -d

# 检查服务状态

# 检查服务状态docker-compose -f docker-compose.local.yml ps

docker-compose -f docker-compose.local.yml ps

# 查看SearXNG日志

# 查看SearXNG日志docker-compose -f docker-compose.local.yml logs searxng

docker-compose -f docker-compose.local.yml logs searxng```

```

### 方案3: 修改SearXNG配置

## 方案3: 修改SearXNG配置我们已经对SearXNG进行了以下配置修改：



我们已经对SearXNG进行了以下配置修改：1. **启用JSON格式支持**：

   ```yaml

1. **启用JSON格式支持**：   formats:

     - html

```yaml     - json

formats:     - csv

  - html     - rss

  - json   ```

  - csv

  - rss2. **放宽安全限制**：

```   ```yaml

   botdetection:

2. **放宽安全限制**：     real_ip:

       from: true

```yaml       from_header: ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"]

botdetection:   ```

  real_ip:

    from: true3. **启用调试模式**：

    from_header: ["X-Forwarded-For", "X-Real-IP", "CF-Connecting-IP"]   ```yaml

```   general:

     debug: true

3. **启用调试模式**：   ```



```yaml### 方案4: 替代测试方法

general:如果SearXNG仍然有问题，可以使用以下替代方案：

  debug: true

```1. **使用公共SearXNG实例**：

   修改环境变量指向公共实例：

## 方案4: 替代测试方法   ```bash

   SEARXNG_URL=https://searx.org

如果SearXNG仍然有问题，可以使用以下替代方案：   ```



1. **使用公共SearXNG实例**：2. **跳过SearXNG测试**：

   修改测试脚本，暂时跳过SearXNG测试。

   修改环境变量指向公共实例：

## 测试SearXNG

```bash

SEARXNG_URL=https://searx.org运行专门的SearXNG测试：

```

```bash

2. **跳过SearXNG测试**：cd backend

python test_searxng.py

   修改测试脚本，暂时跳过SearXNG测试。```



## 测试SearXNG## 预期结果



运行专门的SearXNG测试：- ✅ 基本连通性测试通过

- ⚠️ 搜索API可能返回403（这是正常的安全行为）

```bash- 🎉 SearXNG主页可访问即表示服务正常

cd backend

python test_searxng.py## 故障排除步骤

```

1. 检查Docker Desktop是否正在运行

## 预期结果2. 确认端口10000没有被其他服务占用

3. 查看SearXNG容器日志

- ✅ 基本连通性测试通过4. 尝试重启所有服务

- ⚠️ 搜索API可能返回403（这是正常的安全行为）

- 🎉 SearXNG主页可访问即表示服务正常## 联系支持



## 故障排除步骤如果问题持续存在，请提供：

- Docker Desktop版本

1. 检查Docker Desktop是否正在运行- 操作系统版本

2. 确认端口10000没有被其他服务占用- 完整的错误日志
3. 查看SearXNG容器日志
4. 尝试重启所有服务

## 联系支持

如果问题持续存在，请提供：

- Docker Desktop版本
- 操作系统版本
- 完整的错误日志
