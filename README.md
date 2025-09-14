# A-Share AI Assistant (Full Stack, Dockerized)

This project includes:
- **backend/** Python FastAPI service (data ingestion, indicators, forecasts, reports, scheduler)
- **frontend/** Vite + React app (watchlist, charts, reports, backtest of forecasts)
- **PostgreSQL** with init SQL
- **Docker Compose** to run `db`, `api`, and `web` (nginx serving built frontend)

> 📊 **[查看股票预测算法详细规则](./ALGORITHM.md)**

## Quick Start
1. Copy `.env.example` to `.env` and adjust values.
2. Build & start:
   ```bash
   docker compose up -d --build
   ```
3. Open frontend at `http://<server>:8081`.
4. Backend API at `http://<server>:8080`.

> Default timezone: Asia/Taipei. Daily pipeline runs at 16:10 local time (after A-share close).

## Notes
- Data source uses **AkShare** by default (no token). You can switch to **Tushare** by setting `DATA_SOURCE=tushare` and `TUSHARE_TOKEN` in `.env`.
- Forecasts use **SARIMAX** and **Ridge** (simple, educational). Results are for research only, **NOT** investment advice.

# 项目完整说明

## 项目简介
A-Share AI Assistant 是一个面向中国A股市场的全栈智能分析平台，包含数据采集、技术指标、AI预测、自动报告、可视化前端等功能。后端采用 FastAPI，前端采用 React + Vite，支持 Docker 一键部署。

## 目录结构
- `backend/`：Python FastAPI 服务，包含数据源、数据库、预测、信号、报告、调度等模块。
- `frontend/`：React + Vite 前端，支持自选股、图表、AI报告、回测等。
- `initdb/`：PostgreSQL 初始化 SQL。
- `docker-compose.yml`：一键启动所有服务。

---

## 本地开发与调试

### 1. 环境准备
- 安装 Python 3.12+、Node.js 18+、Docker。
- 复制 `.env.example` 为 `.env`，填写数据库、数据源、Azure OpenAI 等配置。

### 2. 后端初始化与启动
```bash
cd backend
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
# 启动 FastAPI
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### 3. 前端初始化与启动
```bash
cd frontend
npm install
npm run dev
```
- 前端默认端口：8081
- 后端默认端口：8080

### 4. 数据库初始化
- 使用 Docker 启动 PostgreSQL：
```bash
docker compose up db
```
- 或手动执行 `initdb/init.sql` 初始化表结构。

---

## 配置说明
- `.env` 文件需配置：
  - 数据库连接信息
  - 数据源类型与 Token（akshare/tushare）
  - Azure OpenAI 相关参数（endpoint、key、deployment、api-version）
- 详见 `.env.example` 注释。

---

## 一键 Docker 启动
```bash
docker compose up -d --build
```
- 启动后，访问前端 `http://localhost:8081`，后端 API `http://localhost:8080`

---

## 生产环境部署与上线流程
1. 服务器需安装 Docker。
2. 配置 `.env`，确保所有生产参数正确（如数据库密码、OpenAI Key、前端域名等）。
3. 构建并启动服务：
   ```bash
   docker compose up -d --build
   ```
4. 检查日志：
   ```bash
   docker compose logs -f
   ```
5. 配置域名与 HTTPS（建议 Nginx 反向代理，见 `frontend/nginx.conf`）。
6. 定期备份数据库。

---

## 其他说明
- 支持自定义调度时间（CRON），默认每日收盘后自动运行。
- 支持切换数据源与模型。
- Azure OpenAI 需提前在 Azure Portal 创建部署并获取相关参数。
- 本项目仅供学习与研究，所有投资决策请谨慎。

---

## 常见问题
- 如遇依赖安装失败，请确认 Python/Node 版本与网络环境。
- Azure OpenAI 报错请检查 endpoint、key、deployment 是否正确。
- 数据源异常可切换 akshare/tushare 并检查 Token。

---

## 联系与反馈
如有问题或建议，请在项目 Issue 区留言。

---

# 功能与架构设计详解

## 主要功能
- **A股行情数据采集**：支持 AkShare/Tushare，自动拉取每日行情、历史数据。
- **技术指标计算**：如均线、RSI、MACD等，自动生成信号。
- **AI预测与报告**：集成 SARIMAX、Ridge 回归等模型，支持 Azure OpenAI 智能摘要。
- **自选股与回测**：前端支持自选股管理、历史回测、预测结果可视化。
- **自动调度与定时任务**：每日收盘后自动运行数据采集、预测、报告生成。
- **多端部署与扩展**：支持本地开发、Docker一键部署、生产环境上线。

## 架构设计

```
+-------------------+      +-------------------+      +-------------------+
|    Frontend (UI)  |<---->|   Backend (API)   |<---->|   PostgreSQL DB   |
|  React + Vite     |      |  FastAPI, Python  |      |  数据存储         |
+-------------------+      +-------------------+      +-------------------+
        |                        |                          |
        |                        |                          |
        |                        |                          |
        |                        |                          |
        |                        |                          |
        |                        |                          |
        |                        |                          |
        v                        v                          v
+-------------------+      +-------------------+      +-------------------+
|   Azure OpenAI    |<-----|   Scheduler/LLM   |<-----|   Data Source     |
|   智能摘要/对话   |      |   定时任务/AI     |      |   AkShare/Tushare |
+-------------------+      +-------------------+      +-------------------+
```

- **前端**：基于 React + Vite，负责页面展示、用户交互、行情与预测图表、AI报告展示。
- **后端**：FastAPI 提供 RESTful API，负责数据采集、指标计算、AI预测、报告生成、调度任务。
- **数据库**：PostgreSQL 存储行情、信号、预测、用户自选股等。
- **数据源**：AkShare/Tushare，支持灵活切换。
- **AI能力**：集成 Azure OpenAI，自动生成投资摘要、智能解读。
- **调度系统**：APScheduler 定时自动运行数据管道。
- **容器化部署**：Docker Compose 管理多服务，支持一键启动、扩展。

## 典型流程
1. 定时任务触发，采集最新行情数据。
2. 计算技术指标，生成买卖信号。
3. 运行AI预测模型，生成未来走势预测。
4. 汇总数据，调用 Azure OpenAI 生成智能报告。
5. 前端展示自选股、预测结果、AI摘要，支持回测与交互。

## 扩展性与安全
- 支持自定义数据源、模型扩展。
- 环境变量集中管理，敏感信息不入库。
- 生产环境建议使用 HTTPS、Nginx 反向代理。
- 数据库定期备份，支持多用户扩展。

## 适用场景
- 个人/团队量化研究、A股行情分析、AI投资辅助。
- 教学演示、数据科学实验、智能报告生成。

---

# 股票预测算法详解

## 预测策略概述
系统采用多层次预测策略，结合技术指标分析和机器学习模型，为用户提供短期价格预测和买卖信号。

## 技术指标计算规则

### 1. 移动平均线 (MA)
- **短期均线**: 10日移动平均线 `ma_short = close.rolling(10).mean()`
- **长期均线**: 30日移动平均线 `ma_long = close.rolling(30).mean()`
- **用途**: 判断价格趋势方向，短均线上穿长均线为看涨信号

### 2. 相对强弱指数 (RSI)
- **计算周期**: 14日
- **公式**: `RSI = 100 - (100 / (1 + RS))`，其中 RS = 上涨平均值 / 下跌平均值
- **信号判断**:
  - RSI > 70：超买区域，可能下跌
  - RSI < 30：超卖区域，可能上涨
  - RSI 接近50：中性区域

### 3. MACD 指标
- **快线**: 12日EMA - 26日EMA
- **慢线**: 9日EMA of MACD
- **信号**: MACD上穿信号线为买入信号

## 综合信号评分系统

### 评分规则 (signal_score)
```
基础分数 = 0
```

#### 1. 均线交叉评分 (±20分)
- **金叉**: 短均线上穿长均线 → +20分
- **死叉**: 短均线下穿长均线 → -20分

#### 2. RSI 评分 (±15分)
- **计算公式**: `min(max(50 - |RSI - 50|, -15), 15)`
- **说明**: RSI越接近50越好，偏离50越远扣分越多

#### 3. MACD 评分 (+10分)
- **条件**: MACD上穿信号线 → +10分
- **其他情况**: 0分

### 最终操作建议
```python
if signal_score >= 15:
    action = "BUY"     # 买入
elif signal_score <= -15:
    action = "TRIM"    # 减仓
else:
    action = "HOLD"    # 持有
```

## 价格预测模型

### 模型选择策略
系统采用多模型备份策略，按优先级依次尝试：

### 1. 特征回归模型 (Ridge Regression) - 首选
**数据要求**: 至少80条历史记录

**特征工程**:
```python
features = [
    "ret1",     # 1日收益率
    "ma5",      # 5日均线
    "ma10",     # 10日均线  
    "ema12",    # 12日指数移动平均
    "ema26",    # 26日指数移动平均
    "vol_z"     # 成交量标准化 (Z-score)
]
```

**预测流程**:
1. **数据预处理**: StandardScaler标准化特征
2. **模型训练**: RidgeCV交叉验证选择最佳正则化参数
3. **置信区间**: 预测值 ± 1.28 × 残差标准差 (80%置信区间)
4. **滚动预测**: 逐日预测未来5个交易日价格

**优势**: 考虑多维度技术指标，预测相对稳定

### 2. SARIMAX 时间序列模型 - 备选
**数据要求**: 至少60条历史记录

**模型参数**:
- **ARIMA阶数**: (1,1,1) - 1阶自回归，1阶差分，1阶移动平均
- **季节性**: (0,0,0,0) - 不考虑季节性
- **约束**: 不强制平稳性和可逆性

**置信区间**: 模型内置的80%置信区间

**优势**: 纯时间序列方法，适合趋势明显的股票

### 3. 线性趋势模型 - 保底
**数据要求**: 至少5条历史记录

**计算方法**:
```python
recent_trend = (close[-1] - close[-5]) / 5  # 最近5日平均变化
predicted_price = last_price + (i + 1) * recent_trend
confidence_interval = predicted_price ± 5%  # 固定5%置信区间
```

**优势**: 简单可靠，任何情况下都能给出预测

## 预测结果输出格式

```json
{
    "symbol": "002594.SZ",
    "method": "feature_regression",  // 使用的模型
    "confidence": 0.8,               // 置信度
    "predictions": [
        {
            "day": 1,
            "predicted_price": 105.63,
            "lower_bound": 103.60,
            "upper_bound": 107.65
        },
        // ... 未来5天预测
    ]
}
```

## 风险提示与免责声明

### ⚠️ 重要提醒
1. **仅供研究学习**: 所有预测结果仅用于技术研究和教学目的
2. **不构成投资建议**: 任何预测都不应作为实际投资决策的唯一依据
3. **市场风险**: 股市有风险，投资需谨慎，过往表现不代表未来结果
4. **模型局限性**: 技术分析无法预测突发事件对股价的影响

### 算法局限性
- **短期预测**: 仅适用于1-5天的短期预测
- **技术面分析**: 主要基于技术指标，未考虑基本面因素
- **市场环境**: 在极端市场条件下预测准确性可能下降

### 使用建议
- 结合其他分析方法使用
- 关注置信区间范围
- 定期回测验证预测效果
- 建立合理的风险管理机制

---
