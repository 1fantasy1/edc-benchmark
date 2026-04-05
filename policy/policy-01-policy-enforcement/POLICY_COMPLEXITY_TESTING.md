# Policy Complexity Testing Guide

本指南说明如何使用不同复杂度级别的policy进行测试。系统支持三个不同的复杂度级别：

## Policy复杂度级别

### 1. 简单级别 (SIMPLE) - 单个条件约束
**约束函数**: `LocationConstraintFunction`  
**测试场景**: 基于地理位置的访问控制  
**复杂度指标**: 单一OperatorSingle operator, 一维数据  

**使用配置**:
- 提供者: `config-simple.properties`
- 消费者: `config-simple.properties`
- Policy定义: `create-policy-simple.json`

**测试步骤**:

```powershell
# 1. 构建并启动提供者（简单）
./gradlew policy:policy-01-policy-enforcement:policy-enforcement-provider:build
java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-provider\config-simple.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-provider\build\libs\provider.jar"

# 2. 构建并启动消费者（简单）- 在另一个终端
./gradlew policy:policy-01-policy-enforcement:policy-enforcement-consumer:build
java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-consumer\config-simple.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-consumer\build\libs\consumer.jar"

# 3. 创建资源
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" -d "@policy\policy-01-policy-enforcement\resources\create-asset.json" "http://localhost:19193/management/v3/assets"

# 4. 创建简单Policy
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password"  -d "@policy\policy-01-policy-enforcement\resources\create-policy-simple.json" "http://localhost:19193/management/v3/policydefinitions"

# 5. 创建Contract定义
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" -d "@policy\policy-01-policy-enforcement\resources\create-contract-definition.json"  "http://localhost:19193/management/v3/contractdefinitions"

# 6. 请求Catalog（确认供应商offers已准备好）
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" -d "@policy\policy-01-policy-enforcement\resources\catalog-request.json" "http://localhost:29193/management/v3/catalog/request"

# 7. 发起Contract谈判
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" -d "@policy\policy-01-policy-enforcement\resources\contract-request.json" "http://localhost:29193/management/v3/contractnegotiations"

# 8. 检查谈判状态
curl.exe -X GET -H "X-Api-Key: password" "http://localhost:29193/management/v3/contractnegotiations/{UUID}"
```

**预期结果**:

✅ **成功场景** (Consumer 配置 `edc.mock.region=eu`)：
- 谈判状态进陷: REQUESTED → OFFERED → ACCEPTED → FINALIZED
- Consumer 能看到 Provider 的 Asset 和 Policy
- Contract 协议成功达成

❌ **失败场景** (Consumer 配置 `edc.mock.region=us`)：
- **Catalog 阶段**: Asset 不会出现（Policy 已在 Catalog 评估时过滤）
- **如果跳过 Catalog 直接谈判**: 状态→TERMINATED
- 错误信息: `Policy not fulfilled: [Permission constraints: [Constraint 'location' EQ 'eu']]`
- Provider 日志显示: `Evaluating constraint: location EQ eu` + 评估失败

---

### 2. 中等及程度 (MEDIUM) - 多条件/范围约束
**约束函数**: `TimeRangeConstraintFunction`  
**测试场景**: 基于时间范围的访问控制  
**复杂度指标**: 支持多个操作符(EQ, GT, LT, isAnyOf)，范围验证  

**使用配置**:
- 提供者: `config-medium.properties`
- 消费者: `config-medium.properties`
- Policy定义: `create-policy-medium.json`

**时间约束操作符**:
- `EQ`: 精确时间匹配
- `GT`: 当前时间在给定时间之后
- `LT`: 当前时间在给定时间之前
- `isAnyOf`: 当前时间在允许的时间范围内（通常为[start, end]）

**关键变更**：
1. **Provider 启动配置**: 使用 `config-medium.properties` 替换 `config-simple.properties`
   - 修改：`java -Dedc.fs.config=policy/policy-01-policy-enforcement/policy-enforcement-provider/config-medium.properties`
2. **Consumer 启动配置**: 使用 `config-medium.properties` 替换 `config-simple.properties`
   - 修改：`java -Dedc.fs.config=policy/policy-01-policy-enforcement/policy-enforcement-consumer/config-medium.properties`
3. **create-contract-definition.json**: 更新 Policy ID
   ```json
   "accessPolicyId": "medium-timerange-policy",
   "contractPolicyId": "medium-timerange-policy"
   ```
4. **contract-request.json**: 更新 Provider 标识和 Policy 约束
   ```json
   "odrl:assigner": { "@id": "provider-medium" },
   "odrl:constraint": {
     "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/timeRange",
     "odrl:operator": { "@id": "odrl:in" },
     "odrl:rightOperand": ["2024-01-01T00:00:00", "2027-12-31T23:59:59"]
   }
   ```

**测试步骤**:

```powershell
# 1. 启动中等级别的提供者和消费者
java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-provider\config-medium.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-provider\build\libs\provider.jar"

java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-consumer\config-medium.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-consumer\build\libs\consumer.jar"

# 2. 创建资源（使用中等级别的 Policy）
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\create-asset.json" `
  "http://localhost:19193/management/v3/assets"

curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\create-policy-medium.json" `
  "http://localhost:19193/management/v3/policydefinitions"

# 3. 创建 Contract 定义（使用 medium 级别的专用文件）
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\create-contract-definition-medium.json" `
  "http://localhost:19193/management/v3/contractdefinitions"

# 4. 请求 Catalog
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\catalog-request.json" `
  "http://localhost:29193/management/v3/catalog/request"

# 5. 发起 Contract 谈判（使用 medium 级别的专用文件）
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\contract-request-medium.json" `
  "http://localhost:29193/management/v3/contractnegotiations"

# 6. 检查谈判状态
curl.exe -X GET -H "X-Api-Key: password" "http://localhost:29193/management/v3/contractnegotiations/{UUID}"
```

**预期结果**:
- Policy定义了时间范围约束 (2024-01-01 到 2027-12-31)
- 当前时间应该在范围内
- 谈判应该成功，状态为FINALIZED
- 会在日志中看到: `Evaluating time constraint: isAnyOf [2024-01-01T00:00:00, 2027-12-31T23:59:59]`

---

### 3. 高级级别 (ADVANCED) - 多层级/组合约束
**约束函数**: `DataProtectionLevelConstraintFunction`  
**测试场景**: 基于数据保护级别的多层级访问控制  
**复杂度指标**: 多层级验证(0-4)，支持组合约束，复杂的业务逻辑  

**数据保护级别**:
- **0 (NONE)**: 无保护
- **1 (BASIC)**: 基础保护 - 传输加密
- **2 (STANDARD)**: 标准保护 - 传输+存储加密
- **3 (ENHANCED)**: 增强保护 - 加密+访问控制
- **4 (MAXIMUM)**: 最高保护 - 加密+访问控制+审计日志

**支持的操作符**:
- `EQ`: 保护级别必须相等
- `GT`: 消费者保护级别大于要求
- `LT`: 消费者保护级别小于指定值
- `NEQ`: 消费者保护级别不等于指定值
- `isAnyOf`: 消费者保护级别在允许列表中（推荐用于多级别）**[注: 已替换之前的 IN 操作符]**

**使用配置**:
- 提供者: `config-advanced.properties`
- 消费者: `config-advanced.properties`
- Policy定义: `create-policy-advanced.json`

**关键变更**：
1. **Provider 启动配置**: 使用 `config-advanced.properties`
   - 修改：`java -Dedc.fs.config=policy/policy-01-policy-enforcement/policy-enforcement-provider/config-advanced.properties`
   - 添加 claim: `edc.mock.dataProtectionLevel=MAXIMUM`
2. **Consumer 启动配置**: 使用 `config-advanced.properties`
   - 修改：`java -Dedc.fs.config=policy/policy-01-policy-enforcement/policy-enforcement-consumer/config-advanced.properties`
   - 添加 claim: `edc.mock.dataProtectionLevel=MAXIMUM`（或其他测试级别）
3. **create-contract-definition.json**: 更新 Policy ID
   ```json
   "accessPolicyId": "advanced-dataprotection-policy",
   "contractPolicyId": "advanced-dataprotection-policy"
   ```
4. **contract-request.json**: 更新 Provider 标识和 Policy 约束
   ```json
   "odrl:assigner": { "@id": "provider-advanced" },
   "odrl:constraint": {
     "odrl:leftOperand": "https://w3id.org/edc/v0.0.1/ns/dataProtectionLevel",
     "odrl:operator": { "@id": "odrl:in" },
     "odrl:rightOperand": ["ENHANCED", "MAXIMUM"]
   }
   ```

**测试步骤**:

```powershell
# 1. 启动高级别的提供者和消费者
java -Dedc.fs.config=policy/policy-01-policy-enforcement/policy-enforcement-provider/config-advanced.properties `
  -jar policy/policy-01-policy-enforcement/policy-enforcement-provider/build/libs/provider.jar

java -Dedc.fs.config=policy/policy-01-policy-enforcement/policy-enforcement-consumer/config-advanced.properties `
  -jar policy/policy-01-policy-enforcement/policy-enforcement-consumer/build/libs/consumer.jar

# 2. 创建资源（使用高级别的 Policy）
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\create-asset.json" `
  "http://localhost:19193/management/v3/assets"

curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\create-policy-advanced.json" `
  "http://localhost:19193/management/v3/policydefinitions"

# 3. 创建 Contract 定义（使用 advanced 级别的专用文件）
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\create-contract-definition-advanced.json" `
  "http://localhost:19193/management/v3/contractdefinitions"

# 4. 请求 Catalog
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\catalog-request.json" `
  "http://localhost:29193/management/v3/catalog/request"

# 5. 发起 Contract 谈判（使用 advanced 级别的专用文件）
curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
  -d "@policy\policy-01-policy-enforcement\resources\contract-request-advanced.json" `
  "http://localhost:29193/management/v3/contractnegotiations"

# 6. 检查谈判状态
curl.exe -X GET -H "X-Api-Key: password" "http://localhost:29193/management/v3/contractnegotiations/{UUID}"
```

**测试变种** - 修改消费者config-advanced.properties中的dataProtectionLevel来测试不同场景:

```properties
# 测试场景1: 消费者保护级别充足 - 成功✓
edc.mock.dataProtectionLevel=MAXIMUM  # 4
# Policy 允许: [ENHANCED, MAXIMUM]
# 结果: 谈判成功→FINALIZED

# 测试场景2: 消费者保护级别足够但不是最高 - 成功✓
edc.mock.dataProtectionLevel=ENHANCED  # 3
# Policy 允许: [ENHANCED, MAXIMUM]
# 结果: 谈判成功→FINALIZED

# 测试场景3: 消费者保护级别不足 - 失败✗
edc.mock.dataProtectionLevel=STANDARD  # 2
# Policy 允许: [ENHANCED, MAXIMUM]
# 结果: 谈判失败→TERMINATED

# 测试场景4: 消费者无保护 - 失败✗
edc.mock.dataProtectionLevel=NONE  # 0
# Policy 允许: [ENHANCED, MAXIMUM]
# 结果: 谈判拒绝→TERMINATED

# 测试使用数值代替字符串
edc.mock.dataProtectionLevel=3  # ENHANCED level
# 结果: 与场景2相同
```

**修改步骤**：
1. 编辑 Consumer 配置文件，修改 `edc.mock.dataProtectionLevel` 值
2. **重启 Consumer** 服务器以加载新配置
3. 重新发起 Contract Negotiation
4. 观察谈判结果

**预期结果**:
- **场景1/2**: 状态→FINALIZED ✅
  - 会在日志中看到: `Evaluating data protection level constraint: consumer level=X, operator=isAnyOf, required=[ENHANCED, MAXIMUM]`
  - dataProtectionLevel 在允许列表中
- **场景3/4**: 状态→TERMINATED ❌
  - 错误: `Policy not fulfilled: [Permission constraints: [Constraint 'dataProtectionLevel' isAnyOf '[ENHANCED, MAXIMUM]']]`
  - dataProtectionLevel 不在允许列表中

---

## 测试矩阵

| 复杂度  | 约束类型 | 操作符 | 验证复杂度 | 应用场景 |
|--------|---------|--------|----------|----------|
| SIMPLE | 地点    | EQ, NEQ, IN | 单值比对 | 地理区域限制 |
| MEDIUM | 时间范围 | EQ, GT, LT, isAnyOf | 范围验证 | 时间窗口限制，营业时间 |
| ADVANCED | 多层级保护 | EQ, GT, LT, NEQ, isAnyOf | 多级比对，业务规则 | 数据敏感度分级，合规要求 |

---

## 关键配置变更总结

### 文件修改清单

| 复杂度 | 需要修改的文件 | 关键修改项 |
|--------|---------------|----------|
| SIMPLE | config-simple.properties | `edc.participant.id`, `edc.mock.region=eu` |
| | create-contract-definition.json | `accessPolicyId`, `contractPolicyId` → `simple-location-policy` |
| | contract-request.json | ✅ 使用 `contract-request.json`（已配置） |
| MEDIUM | config-medium.properties | `edc.participant.id=provider-medium`, 启动时使用 |
| | create-contract-definition-medium.json | ✅ **使用专用文件**（`medium-timerange-policy`） |
| | contract-request-medium.json | ✅ **使用专用文件**（Provider ID: `provider-medium`, isAnyOf 操作符） |
| ADVANCED | config-advanced.properties | `edc.participant.id=provider-advanced`, `edc.mock.dataProtectionLevel=MAXIMUM` |
| | create-contract-definition-advanced.json | ✅ **使用专用文件**（`advanced-dataprotection-policy`） |
| | contract-request-advanced.json | ✅ **使用专用文件**（Provider ID: `provider-advanced`, isAnyOf 操作符） |

### 资源文件说明

已为每个复杂度级别创建专用资源文件，避免参数混淆：

- **SIMPLE**: 使用 `contract-request.json` 和 `create-contract-definition.json`
- **MEDIUM**: 使用 `contract-request-medium.json` 和 `create-contract-definition-medium.json`
- **ADVANCED**: 使用 `contract-request-advanced.json` 和 `create-contract-definition-advanced.json`

所有专用文件均已配置正确的 Provider ID、Policy ID 和 ODRL 操作符（isAnyOf）。

### 动态修改约束条件的方法

**方式1: 直接编辑 JSON 文件** (推荐开发测试)
```powershell
# 编辑对应级别的 contract-request-*.json 文件
# 修改 odrl:constraint 中的 odrl:operator 和 odrl:rightOperand
# 保存后重新发起谈判
```

**方式2: 修改 Consumer 配置中的 Mock Claims**
```powershell
# 编辑相应的 config-*.properties 文件
# 修改 edc.mock.* 参数
# 重启服务
# 重新发起谈判
```

## 故障排查

### 场景0: Policy 序列化不一致 - Agreement 验证失败
**症状**:
```
Contract agreement received. Validation failed: Policy in the contract agreement is not equal to the one in the contract offer
```

**原因**:
- Provider 的 Offer 中的 Policy 和 Consumer 返回的 Agreement 中的 Policy 序列化格式不一致
- 通常是因为 `odrl:rightOperand` 中的值被转换成了不同的格式（例如从数组变成了单个值，或者 `@value` 包装发生了变化）

**解决步骤**:

1. **检查 Consumer 端日志**，查看是否显示 Policy 被评估通过

2. **验证 Contract Negotiation 状态**
   ```powershell
   # 获取完整的 negotiation 对象
   curl.exe -X GET -H "X-Api-Key: password" "http://localhost:29193/management/v3/contractnegotiations/{UUID}"
   ```
   查看返回的 JSON 中：
   - `lastOffer` 中的 Policy
   - `lastAgreement` 中的 Policy
   
   使用 VS Code 或 JSON 格式化工具比较两者的差异

3. **常见的序列化差异**：
   ```json
   // Offer 中可能是
   "odrl:rightOperand": [
     {"@value":"2024-01-01T00:00:00"},
     {"@value":"2027-12-31T23:59:59"}
   ]
   
   // Agreement 中可能变成了
   "odrl:rightOperand": [
     "2024-01-01T00:00:00",
     "2027-12-31T23:59:59"
   ]
   
   // 或者 @context 信息丢失
   ```

4. **临时解决方案** - 禁用严格的 Policy 验证（仅用于测试）：
   - 这需要在 EDC 配置中调整，通常不推荐在生产环境使用
   - 咨询 EDC 文档或 Provider 的启动配置

5. **根本解决方案** - 确保 Policy 序列化一致性：
   - 确保 `TimeRangeConstraintFunction` 返回的结果与原始 Policy 格式相同
   - 避免在评估过程中修改 Policy 对象本身
   - 检查约束函数中是否有任何会改变 Policy 结构的操作

**调试技巧**:
- 在 Provider 端 `PolicyFunctionsExtension` 中添加日志，记录接受到的 Policy 和返回的 Policy
- 比较 Offer 和 Agreement 的序列化 JSON，找出差异点
- 若差异是在 `rightOperand` 值被解析后，需要确保解析过程是幂等的

---

### 场景1: TimeRange 约束持续失败
**症状**: 
```
Policy in scope contract.negotiation not fulfilled: [Permission constraints: [Constraint 'timeRange' IS_ANY_OF '...']]
```

**原因**:
- Consumer 进程使用的是旧版本的 JAR，未包含最新的约束函数优化
- Policy JSON 中的时间范围已过期（日期早于当前时间）

**解决步骤**:
1. **终止所有运行中的 provider 和 consumer 进程**
   ```powershell
   # 在两个终端中按 Ctrl+C 停止运行的 Java 进程
   ```

2. **完全重新构建项目**
   ```powershell
   cd E:\edc\Samples\policy
   ./gradlew clean policy:policy-01-policy-enforcement:build -x test
   ```

3. **重新启动 Provider 和 Consumer**
   ```powershell
   # 终端 1: Provider
   java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-provider\config-medium.properties" `
     -jar "policy\policy-01-policy-enforcement\policy-enforcement-provider\build\libs\provider.jar"
   
   # 终端 2: Consumer
   java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-consumer\config-medium.properties" `
     -jar "policy\policy-01-policy-enforcement\policy-enforcement-consumer\build\libs\consumer.jar"
   ```

4. **重新创建所有资源**
   ```powershell
   # Asset
   curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
     -d "@policy\policy-01-policy-enforcement\resources\create-asset.json" `
     "http://localhost:19193/management/v3/assets"
   
   # Policy (已更新的时间范围)
   curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
     -d "@policy\policy-01-policy-enforcement\resources\create-policy-medium.json" `
     "http://localhost:19193/management/v3/policydefinitions"
   
   # Contract Definition
   curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
     -d "@policy\policy-01-policy-enforcement\resources\create-contract-definition-medium.json" `
     "http://localhost:19193/management/v3/contractdefinitions"
   ```

5. **重新发起 Contract Negotiation**
   ```powershell
   # Catalog request
   curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
     -d "@policy\policy-01-policy-enforcement\resources\catalog-request.json" `
     "http://localhost:29193/management/v3/catalog/request"
   
   # Contract negotiation
   curl.exe -X POST -H "Content-Type: application/json" -H "X-Api-Key: password" `
     -d "@policy\policy-01-policy-enforcement\resources\contract-request-medium.json" `
     "http://localhost:29193/management/v3/contractnegotiations"
   ```

**验证步骤**:
- 查看 Provider 日志：应该显示 `Evaluating time constraint: isAnyOf [...]`
- 查看 Consumer 日志：应该显示 Policy 评估成功
- Contract 状态应该转变为 FINALIZED

**关键检查点**:
1. 确认编译后的 JAR 文件时间戳是最新的（检查 build/libs/ 目录）
2. 确认 Policy JSON 文件中的时间范围已更新为 2027-12-31
3. 确认使用了正确的配置文件（config-medium.properties）

---

### 场景2: Policy未被评估 - Catalog 为空
**原因**: 
- 缺少RuleBindingRegistry绑定，或
- Policy 在 Catalog 阶段已被评估并过滤

**解决**:
- 检查PolicyFunctionsExtension中是否调用了`ruleBindingRegistry.bind()`
- 确保constraint key与policy JSON中的leftOperand匹配
- **修改 Consumer 配置中的 mock claims 以满足 Policy 要求**
- 重启 Consumer，再次请求 Catalog

**示例**: 地点限制→Consumer 改为 EU 区域
```properties
edc.mock.region=eu  # 改为 eu 而非 us
```

### 场景3: 不支持的操作符错误
**症状**: 日志显示"default -> false"

**解决**:
- 检查约束函数是否实现了所需的操作符
- 查看TimeRangeConstraintFunction和DataProtectionLevelConstraintFunction中的switch语句
- 确认 ODRL Policy 中使用的操作符在 JSON 中正确指定 (如 `odrl:eq`, `odrl:in`)

### 场景4: 身份验证失败 - Invalid counter-party identity
**症状**: 错误 `Invalid client credentials: Invalid counter-party identity`

**解决**:
- **contract-request.json** 中的 `odrl:assigner` 必须与 Provider 配置的 `edc.participant.id` 完全匹配
- 检查配置文件中是否使用了错误的 participant ID
- 示例修正：
  ```json
  "odrl:assigner": { "@id": "provider-simple" }  // ← 而非 "provider"
  ```

### 场景5: Claims信息丢失
**症状**: 无法获取消费者声明信息

**解决**:
- 验证iam-mock扩展是否已加载
- 检查 config.properties 中是否设置了必要的 mock claims
  - 位置约束: `edc.mock.region=eu`
  - 保护级别: `edc.mock.dataProtectionLevel=MAXIMUM`
- 修改后**必须重启服务**使新配置生效

---

## 扩展性

要添加新的复杂度级别：

1. **创建新的约束函数类**继承`AtomicConstraintRuleFunction<Permission, ContractNegotiationPolicyContext>`
2. **在PolicyFunctionsExtension中注册**:
   ```java
   ruleBindingRegistry.bind(YOUR_CONSTRAINT_KEY, NEGOTIATION_SCOPE);
   policyEngine.registerFunction(ContractNegotiationPolicyContext.class, Permission.class, 
       YOUR_CONSTRAINT_KEY, new YourConstraintFunction(monitor));
   ```
3. **创建对应的配置文件和Policy JSON定义**
4. **编写curl命令进行端到端测试**
