# 股票系统测试套件

这个目录包含了股票分析系统的所有测试脚本，用于验证系统功能的正确性。

## 目录结构

```
tests/
├── run_tests.py              # 测试套件运行器
├── data/                     # 数据相关测试
│   └── test_data_integrity.py   # 数据完整性测试
└── integration/              # 集成测试
    ├── test_api.py              # API集成测试  
    └── test_pipeline.py         # 数据管道测试
```

## 使用方法

### 1. 运行所有测试
```bash
# 从backend目录运行
python tests/run_tests.py
```

### 2. 运行数据测试（不需要API服务器）
```bash
python tests/run_tests.py --data-only
```

### 3. 指定API服务器地址
```bash
python tests/run_tests.py --api-url http://localhost:8080
```

### 4. 运行单个测试
```bash
# 数据完整性测试
python tests/data/test_data_integrity.py

# API测试
python tests/integration/test_api.py --url http://localhost:8080

# 管道测试
python tests/integration/test_pipeline.py
```

## 测试说明

### 数据完整性测试 (test_data_integrity.py)
- 检查价格数据、信号数据、预测数据、报告数据的完整性
- 验证监控列表配置
- 确保数据库中有足够的数据支持系统运行

### API集成测试 (test_api.py)
- 测试健康检查端点
- 测试股票搜索功能
- 测试报告生成API
- 测试监控列表API
- 测试手动训练API

### 数据管道测试 (test_pipeline.py)
- 测试数据源获取功能
- 测试完整的数据处理流程
- 验证价格数据、信号、预测的生成

## 退出代码
- 0: 所有测试通过
- 1: 有测试失败或执行异常

## 注意事项
- 运行API测试前确保后端服务器正在运行
- 数据管道测试会实际执行数据处理，可能需要较长时间
- 测试过程中会在数据库中创建/修改数据，建议在测试环境运行
