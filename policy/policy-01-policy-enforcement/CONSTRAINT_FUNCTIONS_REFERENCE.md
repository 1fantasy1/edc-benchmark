# 约束函数速查表 (Constraint Functions Reference)

## 系统概览

该系统实现了三层Policy复杂度支持，每层都提供了相应的约束函数来评估Policy条件。

---

## Level 1: LocationConstraintFunction (简单)

### 功能
地理位置约束 - 基于消费者的地理区域限制数据访问

### 关键特性
- **Claims来源**: `region` (来自IAM mock声明)
- **支持的操作符**: EQ, NEQ, IN
- **验证复杂度**: O(1) - 单值比对

### 配置
```properties
edc.mock.region=eu      # EU地区
edc.mock.region=us      # US地区
```

### Policy示例
```json
{
  "odrl:constraint": {
    "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/location",
    "odrl:operator": {"@id": "odrl:eq"},
    "odrl:rightOperand": "eu"
  }
}
```

### 日志输出
```
Evaluating constraint: location EQ eu
```

---

## Level 2: TimeRangeConstraintFunction (中等)

### 功能
时间范围约束 - 限制数据访问的时间窗口

### 关键特性
- **Claims来源**: 系统当前时间 (LocalDateTime.now())
- **时间格式**: ISO 8601 (`yyyy-MM-ddTHH:mm:ss`)
- **支持的操作符**: EQ, GT, LT, GEQ, LEQ
- **验证复杂度**: O(1) - 时间解析和单值比对

### 时间操作符详解

| 操作符 | 含义 | rightValue | 示例 | 说明 |
|--------|------|-----------|------|------|
| EQ | 精确时间 | 单个时间戳 | "2024-12-25T10:00:00" | 当前时间必须精确匹配 |
| GT | 在时间之后 | 单个时间戳 | "2024-01-01T00:00:00" | 当前时间必须晚于指定时间 |
| LT | 在时间之前 | 单个时间戳 | "2025-12-31T23:59:59" | 当前时间必须早于指定时间 |
| GEQ | 大于等于 | 单个时间戳 | "2024-01-01T00:00:00" | 当前时间≥指定时间（范围下界） |
| LEQ | 小于等于 | 单个时间戳 | "2027-12-31T23:59:59" | 当前时间≤指定时间（范围上界） |

### 配置
```properties
# 时间相关配置（可选，系统使用当前本地时间）
edc.mock.accessTime=business-hours
```

### Policy示例 - 时间范围内（使用GEQ/LEQ约束）
```json
{
  "odrl:constraint": [
    {
      "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/timeRange",
      "odrl:operator": {"@id": "odrl:gteq"},
      "odrl:rightOperand": "2024-01-01T00:00:00"
    },
    {
      "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/timeRange",
      "odrl:operator": {"@id": "odrl:leq"},
      "odrl:rightOperand": "2027-12-31T23:59:59"
    }
  ]
}
```

### Policy示例 - 在指定时间之后
```json
{
  "odrl:constraint": {
    "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/timeRange",
    "odrl:operator": {"@id": "odrl:gt"},
    "odrl:rightOperand": "2024-01-01T00:00:00"
  }
}
```

### 日志输出
```
Evaluating time constraint: IN [2024-01-01T00:00:00, 2025-12-31T23:59:59] at 2024-04-04T14:30:00
Evaluating time constraint: GT 2024-01-01T00:00:00 at 2024-04-04T14:30:00
```

---

## Level 3: DataProtectionLevelConstraintFunction (高级)

### 功能
数据保护级别约束 - 基于消费者的合规和安全能力限制原始数据访问

### 关键特性
- **Claims来源**: `dataProtectionLevel` (来自IAM mock声明)
- **支持的操作符**: EQ, GT, GTE, LT, LTE, NEQ, IN
- **保护级别范围**: 0-4 (可用字符串或数值)
- **验证复杂度**: O(log n)或O(n) - 级别比对和集合验证

### 保护级别定义

```
级别    名称        特性                              应用
────────────────────────────────────────────────────────────
0      NONE         无加密/保护                        测试/公开数据
1      BASIC        传输加密 (TLS)                    非敏感数据
2      STANDARD     传输+存储加密                      一般数据
3      ENHANCED     加密+访问控制+身份验证             敏感数据
4      MAXIMUM      加密+访问控制+审计日志+签名        高度机密数据
```

### 配置
```properties
# 字符串格式（推荐）
edc.mock.dataProtectionLevel=MAXIMUM   # 4级
edc.mock.dataProtectionLevel=ENHANCED  # 3级
edc.mock.dataProtectionLevel=STANDARD  # 2级

# 或数值格式
edc.mock.dataProtectionLevel=4
edc.mock.dataProtectionLevel=3
```

### 操作符详解

| 操作符 | 含义 | 消费者级别要求 | 示例 |
|--------|------|---------------|-----|
| EQ | 等于 | 必须等于指定值 | rightValue: "STANDARD" |
| GT | 大于 | 必须高于指定值 | rightValue: "BASIC" → 需2-4级 |
| GTE | 大于等于 | 必须不低于指定值 **(最常用)** | rightValue: "ENHANCED" → 需3-4级 |
| LT | 小于 | 必须低于指定值 | rightValue: "MAXIMUM" → 最多3级 |
| LTE | 小于等于 | 必须不高于指定值 | rightValue: "ENHANCED" → 最多3级 |
| NEQ | 不等于 | 级别任意但不能等于 | rightValue: "NONE" → 需1-4级 |
| IN | 包含在集合中 | 必须在允许列表中 | rightValue: ["STANDARD", "ENHANCED", "MAXIMUM"] |

### Policy示例 - 要求最低保护级别

```json
{
  "odrl:constraint": {
    "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/dataProtectionLevel",
    "odrl:operator": {"@id": "odrl:gte"},
    "odrl:rightOperand": "ENHANCED"
  }
}
```

此Policy要求消费者保护级别 ≥ ENHANCED(3)  
✅ 接受: ENHANCED(3), MAXIMUM(4)  
❌ 拒绝: NONE(0), BASIC(1), STANDARD(2)

### Policy示例 - 精确级别要求

```json
{
  "odrl:constraint": {
    "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/dataProtectionLevel",
    "odrl:operator": {"@id": "odrl:eq"},
    "odrl:rightOperand": "MAXIMUM"
  }
}
```

此Policy仅接受MAXIMUM级别消费者

### Policy示例 - 允许列表

```json
{
  "odrl:constraint": {
    "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/dataProtectionLevel",
    "odrl:operator": {"@id": "odrl:in"},
    "odrl:rightOperand": ["ENHANCED", "MAXIMUM"]
  }
}
```

此Policy仅接受ENHANCED或MAXIMUM级别消费者

### 日志输出
```
Evaluating data protection level constraint: consumer level=4, operator=gte, required=3

✅ 成功评估: [Permission constraints evaluated successfully]
❌ 失败评估: [Constraint 'dataProtectionLevel' GTE 'ENHANCED' with consumer level 2]
```

### 测试场景

```bash
# 场景1: 消费者级别足够 → 谈判成功
edc.mock.dataProtectionLevel=MAXIMUM
# Policy需求: GTE ENHANCED
# 结果: ✅ 合格

# 场景2: 消费者级别不足 → 谈判失败
edc.mock.dataProtectionLevel=STANDARD
# Policy需求: GTE ENHANCED  
# 结果: ❌ 被拒绝

# 场景3: 消费者没有设置 → 使用默认值 STANDARD
# Policy需求: GTE MAXIMUM
# 结果: ❌ 被拒绝

# 场景4: 测试NEQ操作符
edc.mock.dataProtectionLevel=BASIC
# Policy需求: NEQ NONE
# 结果: ✅ 合格（任何非NONE的级别都满足）
```

---

## 三层架构对比

| 维度 | SIMPLE | MEDIUM | ADVANCED |
|-------|--------|--------|---------|
| **约束类型** | 单值判等 | 时间范围（双约束） | 多级比对 |
| **操作符数** | 3个 | 5个 | 7个 |
| **数据源** | Claims(region) | 系统时间 | Claims(级别) |
| **业务复杂度** | 低 | 中 | 高 |
| **典型用途** | 地域限制 | 访问窗口 | 合规要求 |
| **性能开销** | 最小 | 低 | 中等 |
| **脚本示例数** | 1 | 2 | 4+ |

---

## 组合约束策略

### 集合操作示例

定义一个Policy同时包含多个约束（Permission中）：

```json
"odrl:permission": [
  {
    "odrl:action": {"@id": "odrl:use"},
    "odrl:constraint": [
      {
        "odrl:leftOperand": "location",
        "odrl:operator": {"@id": "odrl:eq"},
        "odrl:rightOperand": "eu"
      },
      {
        "odrl:leftOperand": "timeRange",
        "odrl:operator": {"@id": "odrl:in"},
        "odrl:rightOperand": ["2024-01-01T00:00:00", "2025-12-31T23:59:59"]
      },
      {
        "odrl:leftOperand": "dataProtectionLevel",
        "odrl:operator": {"@id": "odrl:gte"},
        "odrl:rightOperand": "ENHANCED"
      }
    ]
  }
]
```

所有约束必须同时满足才能通过评估。

---

## 快速测试命令

### 创建简单Policy
```bash
curl -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" \
  -d @create-policy-simple.json "http://localhost:19193/management/v3/policydefinitions" | jq
```

### 创建中等Policy
```bash
curl -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" \
  -d @create-policy-medium.json "http://localhost:19193/management/v3/policydefinitions" | jq
```

### 创建高级Policy
```bash
curl -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" \
  -d @create-policy-advanced.json "http://localhost:19193/management/v3/policydefinitions" | jq
```
