# Policy Overhead Scenario - Implementation Summary

## 项目完成情况

本次实现根据《Policy复杂度测试指南》（POLICY_COMPLEXITY_TESTING.md）完整实现了EDC政策开销基准测试框架，支持三个政策复杂度级别。

### ✅ 完成项目清单

#### 1. Python脚本代码

**文件**: `scenarios/policy_overhead.py`
- ✅ 实现 `PolicyOverheadScenario` 类
- ✅ 添加 `get_policy_template_path()` 方法 - 动态选择政策模板
- ✅ 添加 `get_negotiation_template_path()` 方法 - 动态选择合同请求模板
- ✅ 完整的 `run_once()` 方法 - 执行四段式测试
- ✅ 详细的中文文档注释

#### 2. 资源文件

**政策定义文件** (Policy JSON):
- ✅ `create-policy-simple.json` - SIMPLE级别：地点约束
- ✅ `create-policy-medium.json` - MEDIUM级别：时间范围约束
- ✅ `create-policy-advanced.json` - ADVANCED级别：数据保护级别约束

**合同请求文件** (Contract Request JSON):
- ✅ `contract-request-simple.json` - SIMPLE级别合同请求
- ✅ `contract-request-medium.json` - MEDIUM级别合同请求
- ✅ `contract-request-advanced.json` - ADVANCED级别合同请求

所有文件位置: `policy/policy-01-policy-enforcement/resources/`

#### 3. 配置文件

**主配置文件**: `configs/policy_overhead.yaml`
- ✅ 支持三种政策模式选择
- ✅ 完整的参数说明注释

**单独测试配置**:
- ✅ `configs/policy_overhead_simple.yaml` - SIMPLE级别专用配置
- ✅ `configs/policy_overhead_medium.yaml` - MEDIUM级别专用配置  
- ✅ `configs/policy_overhead_advanced.yaml` - ADVANCED级别专用配置

#### 4. 批量测试脚本

- ✅ `policy_overhead_test.bat` - Windows批处理脚本
- ✅ `policy_overhead_test.sh` - Linux/macOS Bash脚本
- 可自动运行三个级别的测试并汇总结果

#### 5. 文档

- ✅ `POLICY_OVERHEAD_README.md` - 完整的使用指南（900+行）
- ✅ 各级别政策详细说明
- ✅ 故障排查指南
- ✅ 扩展指南

---

## 快速开始

### 运行单个测试级别

```bash
# 测试SIMPLE级别（地点约束）

python -m scripts.run_experiment --config configs/policy_overhead_simple.yaml

# 测试MEDIUM级别（时间范围约束）
python scripts/run_experiment.py --config configs/policy_overhead_medium.yaml

# 测试ADVANCED级别（数据保护级别约束）
python scripts/run_experiment.py --config configs/policy_overhead_advanced.yaml
```


## 测试架构

### 四段式测试流程

```
┌─────────────────────────────────────────────────────────┐
│ Phase 0: Resource Creation (Setup Only)                 │
│ - Create Asset                                          │
│ - Create Policy (policy_mode dependent)                 │
│ - Create Contract Definition                            │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 1: Catalog Request                                │
│ Consumer → Provider: /catalog/request                   │
│ Metric: catalog_request_latency_s                       │
│ (Includes Policy filtering at Provider)                 │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 2: Contract Offer Negotiation                     │
│ Consumer → Provider: /contractnegotiations (POST)        │
│ Metric: contract_offer_negotiation_latency_s            │
│ (Provider generates Offer with Policy constraints)      │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ Phase 3: Agreement & Policy Evaluation                  │
│ Consumer polls: /contractnegotiations/{id} (GET)         │
│ Metrics:                                                │
│ - contract_agreement_latency_s (polling + evaluation)   │
│ - policy_evaluation_latency_s (approximation)           │
│ (Provider evaluates final Policy constraints)           │
└─────────────────────────────────────────────────────────┘
                         ↓
                    [Result Output]
```

### 关键指标

| 指标 | SIMPLE | MEDIUM | ADVANCED | 用途 |
|------|--------|--------|----------|------|
| `catalog_request_latency_s` | 最快 | 中等 | 最慢 | Catalog性能 |
| `contract_agreement_latency_s` | 最快 | 中等 | 最慢 | Policy评估开销 |
| `policy_evaluation_latency_s` | 最快 | 中等 | 最慢 | 直接展示差异 |
| `negotiation_end_to_end_latency_s` | 最快 | 中等 | 最慢 | 端到端性能 |

---


## 政策模式详解

### SIMPLE - 地点约束 (Location Constraint)

**约束函数**: `LocationConstraintFunction`  
**操作符**: `eq` (相等)  
**复杂度**: ⭐ (最低)

```json
{
  "leftOperand": "location",
  "operator": "odrl:eq",
  "rightOperand": "eu"
}
```

**特点**:
- 最快的Policy评估速度
- 单一维度比对
- 适合基础Policy性能测试

---

### MEDIUM - 时间范围约束 (Time Range Constraint)

**约束函数**: `TimeRangeConstraintFunction`  
**操作符**: `isAnyOf` / `in` (范围检查)  
**复杂度**: ⭐⭐ (中等)

```json
{
  "leftOperand": "https://w3id.org/edc/v0.0.1/ns/timeRange",
  "operator": "odrl:in",
  "rightOperand": [
    "2024-01-01T00:00:00",
    "2027-12-31T23:59:59"
  ]
}
```

**特点**:
- 多值范围验证
- 时间解析和比对
- 展示范围约束的开销

---

### ADVANCED - 多层级保护级别约束 (Data Protection Level Constraint)

**约束函数**: `DataProtectionLevelConstraintFunction`  
**操作符**: `isAnyOf` / `in` (多级检查)  
**复杂度**: ⭐⭐⭐ (最高)  
**保护级别**: 0(NONE) → 1(BASIC) → 2(STANDARD) → 3(ENHANCED) → 4(MAXIMUM)

```json
{
  "leftOperand": "https://w3id.org/edc/v0.0.1/ns/dataProtectionLevel",
  "operator": "odrl:in",
  "rightOperand": ["ENHANCED", "MAXIMUM"]
}
```

**特点**:
- 多级比对判断
- 业务规则评估
- 展示复杂Policy的开销

---

## 测试结果示例

### 运行后生成的文件

```
results/local/exp005_simple/
├── config.yaml           ← 测试配置副本
├── metrics.csv           ← 详细指标数据 (用Excel打开)
├── summary.json          ← 测试摘要
└── run.log              ← 运行日志

results/local/exp006_medium/
└── [相同结构]

results/local/exp007_advanced/
└── [相同结构]
```

### metrics.csv 包含字段示例

```
scenario,run_index,success,policy_mode,
catalog_request_latency_s,
contract_offer_negotiation_latency_s,
contract_agreement_latency_s,
policy_evaluation_latency_s,
negotiation_end_to_end_latency_s,
control_plane_total_latency_s,
error
```

---

## 前提条件

### EDC系统要求

1. **Provider服务器**
   - 已部署三种Constraint函数实现
   - Endpoint: `http://localhost:19193/management`
   - Protocol URL: `http://localhost:19194/protocol`

2. **Consumer服务器**
   - 已部署相同的Constraint函数实现
   - Endpoint: `http://localhost:29193/management`
   - Protocol URL: `http://localhost:29194/protocol`

3. **Mock Claims配置**
   - SIMPLE: `edc.mock.region=eu`
   - MEDIUM: 当前时间在2024-2027范围内
   - ADVANCED: `edc.mock.dataProtectionLevel=MAXIMUM` (或ENHANCED)

### 本地环境要求

- Python 3.7+
- requests 库 (`pip install requests`)
- yaml 库 (`pip install pyyaml`)

---


