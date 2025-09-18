# 前端 API 配置说明

## 配置文件说明

### `vite.config.ts` - Vite 构建工具配置

这是 Vite 构建工具的配置文件，主要作用：

1. **开发服务器配置**
   - 端口：5174
   - 主机绑定：允许外部访问

2. **代理配置**
   ```typescript
   proxy: {
     '/api': {
       target: 'http://localhost:8083',
       changeOrigin: true,
       secure: false
     }
   }
   ```
   - 将所有 `/api/*` 请求代理到后端服务器 `http://localhost:8083`
   - 解决开发环境的跨域问题

3. **插件配置**
   - React 插件支持

### `src/config/api.ts` - 应用 API 配置

这是应用级别的 API 配置文件，主要作用：

1. **智能环境检测**
   - 开发环境：使用相对路径 `''`，依赖 Vite 代理
   - 生产环境：使用完整 URL `http://localhost:8083`

2. **API 端点管理**
   - 统一管理所有 API 端点
   - 提供类型安全的端点常量

3. **灵活配置支持**
   - 支持通过 `window.API_BASE` 动态配置
   - 支持不同环境的自动切换

## 工作原理

### 开发环境
```
前端请求: /api/news/articles
↓ (Vite 代理)
后端请求: http://localhost:8083/api/news/articles
```

### 生产环境
```
前端请求: http://localhost:8083/api/news/articles
↓ (直接请求)
后端请求: http://localhost:8083/api/news/articles
```

## 优势

1. **无缝切换**：开发和生产环境自动切换，无需手动修改
2. **跨域解决**：开发环境通过 Vite 代理解决跨域问题
3. **类型安全**：TypeScript 提供 API 端点的类型检查
4. **集中管理**：所有 API 配置集中在一个文件中
5. **灵活配置**：支持运行时动态配置 API 地址

## 使用方式

```typescript
import { buildApiUrl, API_ENDPOINTS } from '@/config/api';

// 推荐使用方式
const response = await fetch(buildApiUrl(API_ENDPOINTS.NEWS.ARTICLES));

// 动态端点
const response = await fetch(buildApiUrl(API_ENDPOINTS.NEWS.STOCK_NEWS('AAPL')));
```

## 注意事项

1. 确保 `vite.config.ts` 中的代理目标与后端服务器地址一致
2. 生产环境部署时，需要确保 API 地址正确
3. 如需自定义 API 地址，可通过 `window.API_BASE` 设置