# EDC Benchmark 指标说明

本文档定义 benchmark 平台统一使用的核心指标口径。

---

## 1. 核心控制面指标

### 1.1 catalog_request_latency_s
- 含义：Consumer 发起 Catalog / Dataset 请求，到收到可解析的 dataset / offer 响应的耗时
- 单位：秒（s）
- 说明：用于衡量目录发现阶段的控制面开销

### 1.2 contract_offer_negotiation_latency_s
- 含义：Consumer 发起 Contract Negotiation 请求，到收到 negotiation_id 的耗时
- 单位：秒（s）
- 说明：只表示“协商启动”开销，不包含等待 agreement 的时间

### 1.3 contract_agreement_latency_s
- 含义：从 negotiation_id 已创建开始，到查询到 contract agreement 的耗时
- 单位：秒（s）
- 说明：用于衡量协商状态推进和 agreement 生成的时间

### 1.4 transfer_initiation_latency_s
- 含义：Consumer 发起 Transfer Process 请求，到收到 transfer_process_id 的耗时
- 单位：秒（s）
- 说明：只表示“传输启动”开销，不包含数据真正传完的时间

---

## 2. 补充指标

### 2.1 transfer_completion_latency_s
- 含义：从 transfer_process_id 已创建开始，到 transfer process 进入完成态的耗时
- 单位：秒（s）
- 说明：不属于四段核心控制面指标，但用于分析传输真正完成所需时间

### 2.2 throughput_mb_s
- 含义：传输吞吐量
- 计算方式：data_size_mb / transfer_completion_latency_s
- 单位：MB/s
- 说明：用于数据面性能对比

### 2.3 control_plane_total_latency_s
- 含义：四段核心控制/编排耗时总和
- 计算方式：
  - negotiation 场景：
    - catalog_request_latency_s
    - + contract_offer_negotiation_latency_s
    - + contract_agreement_latency_s
  - transfer 场景：
    - catalog_request_latency_s
    - + contract_offer_negotiation_latency_s
    - + contract_agreement_latency_s
    - + transfer_initiation_latency_s
- 单位：秒（s）

### transfer_end_to_end_latency_s
- 含义：从发起 Transfer Process 请求到传输完成的总耗时
- 计算方式：
  transfer_initiation_latency_s + transfer_completion_latency_s
- 单位：秒（s）
- 说明：用于对比不同数据规模下的整体传输时间

---

## 3. 状态字段

### 3.1 negotiation_state
- 含义：Negotiation 最终状态
- 常见值：
  - FINALIZED
  - CONFIRMED
  - TERMINATED
  - DECLINED

### 3.2 transfer_state
- 含义：Transfer Process 最终状态
- 常见值：
  - COMPLETED
  - FINISHED
  - DEPROVISIONED
  - FAILED
  - TERMINATED

---

## 4. 成功判定

### 4.1 negotiation_baseline
- success = true 条件：
  - contract_agreement_id 非空
  - negotiation_state 属于 FINALIZED / CONFIRMED

### 4.2 transfer_baseline
- success = true 条件：
  - contract_agreement_id 非空
  - transfer_state 属于 COMPLETED / FINISHED / DEPROVISIONED

---

## 5. 输出文件中的对应关系

### metrics.csv
每一行表示一次 run 的原始结果。

### summary.json
聚合字段统一包含：
- *_avg
- *_min
- *_max

聚合对象范围仅包括：
- catalog_request_latency_s
- contract_offer_negotiation_latency_s
- contract_agreement_latency_s
- transfer_initiation_latency_s
- transfer_completion_latency_s
- control_plane_total_latency_s
- throughput_mb_s

# 参数调整与实验设计说明

本文档补充 benchmark 在不同文件规模、不同故障参数下的测试方法与指标解释。

---

## 6. 参数维度说明

### 6.1 文件规模参数

#### data_size_mb
- 含义：测试配置中声明的数据规模
- 单位：MB
- 作用：用于统计吞吐量、区分实验组
- 注意：该字段本身不会改变真实传输数据量

#### asset_base_url
- 含义：资产实际指向的数据源地址
- 作用：决定实际传输的文件内容和真实大小
- 说明：测试不同数据规模时，必须保证 `asset_base_url` 指向不同大小的真实文件

#### 示例
- `data_size_mb: 1` + `asset_base_url: http://localhost:8088/file_1mb.bin`
- `data_size_mb: 10` + `asset_base_url: http://localhost:8088/file_10mb.bin`

---

### 6.2 故障注入时机参数

#### fault_injection_delay_s
- 含义：从 transfer initiation 成功后开始计时，到注入故障之间的延迟
- 单位：秒（s）
- 作用：控制故障发生的时机
- 推荐档位：
  - `0.5`：early
  - `2`：medium
  - `5`：late

#### 解释
- early：更容易打断初始化阶段或刚开始的数据面传输
- medium：更容易观察到成功/失败混合行为
- late：更容易出现故障对本次事务影响较小的情况

---

### 6.3 观察窗口参数

#### post_fault_observation_timeout_s
- 含义：故障注入后，用于观察 transfer 是否恢复的最大时间
- 单位：秒（s）
- 默认建议：`60`
- 大文件场景建议：`120` 或 `180`

---

### 6.4 重试参数

#### retry_attempts
- 含义：故障后用于查询恢复状态的最大重试次数

#### retry_interval_s
- 含义：相邻两次重试之间的间隔
- 单位：秒（s）

---

## 7. 文件规模测试说明

### 7.1 测试目标
比较不同文件大小下的传输耗时与吞吐量差异。

### 7.2 典型实验组
- 1MB
- 10MB
- 50MB
- 100MB

### 7.3 重点指标
- `transfer_initiation_latency_s`
- `transfer_completion_latency_s`
- `transfer_end_to_end_latency_s`
- `throughput_mb_s`

### 7.4 预期规律
- 文件越大，`transfer_completion_latency_s` 通常越大
- 文件越大，`transfer_end_to_end_latency_s` 通常越大
- `catalog_request_latency_s`、`contract_offer_negotiation_latency_s`、`contract_agreement_latency_s` 一般与文件大小关系较弱
- `throughput_mb_s` 反映数据面实际传输效率

---

## 8. 鲁棒性测试说明

### 8.1 测试目标
在故障条件下评估系统的恢复能力和事务完成情况。

### 8.2 当前支持的典型故障
- provider connector restart during transfer
- network delay
- transfer interruption

### 8.3 重点指标
- `recovery_time_s`
- `retry_success_rate`
- `degraded_mode_success_rate`
- `failed_transactions`

### 8.4 结果解释
- 若 transfer 在观察窗口内恢复并进入成功态，则记为成功
- 若 transfer 在观察窗口结束时仍停留在非成功态（如 `STARTED`、`IN_PROGRESS`），则记为失败事务
- 同一场景在不同 `fault_injection_delay_s` 下和不同文件大小可能出现不同结果，这是鲁棒性分析的正常现象
- 分析当故障注入延迟是 2 秒时，成功率多少，当 provider 恢复时间小于 5 秒时，成功率多少，哪些最终停在 STARTED

---

## 9. 推荐实验矩阵

### 9.1 正常性能实验
- `transfer_1mb`
- `transfer_10mb`
- `transfer_50mb`
- `transfer_100mb`

### 9.2 provider restart during transfer
对每种文件大小分别测试：
- early (`fault_injection_delay_s = 0.5`)
- medium (`fault_injection_delay_s = 2`)
- late (`fault_injection_delay_s = 5`)

### 9.3 分析方式
对每个实验组统计：
- `success_rate`
- `transfer_end_to_end_latency_s_avg`
- `recovery_time_s_avg`
- `retry_success_rate_avg`
- `failed_transactions_avg`

---


