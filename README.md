# EDC Benchmark

一个最小可运行的 EDC benchmark 骨架，面向本科生批量执行实验。

## 当前已实现

- 统一仓库骨架

- `scripts/run_experiment.py` 单实验入口

- 统一输出四件套：
  - `config.yaml`
  - `metrics.csv`
  - `summary.json`
  - `run.log`
  
- 控制面性能测评
  •	Catalog Request
	•	Contract Offer Negotiation
	•	Contract Agreement
	•	Transfer Initiation
	
- 数据面性能评测
  •	小文件传输
	•	中等文件传输
	•	大文件传输
	•	并发传输
	
- 鲁棒性与异常场景评测
	•	provider connector 重启
	•	consumer connector 重启
	•	network delay
	
	•	packet-loss
	
	•	transfer-interruption

## 依赖
## 构建
```bash

./gradlew transfer:transfer-00-prerequisites:connector:build

run connectors：

provider：
java -Dedc.fs.config=transfer/transfer-00-prerequisites/resources/configuration/provider-configuration.properties -jar transfer/transfer-00-prerequisites/connector/build/libs/connector.jar

 java "-Dedc.fs.config=transfer/transfer-00-prerequisites/resources/configuration/provider-configuration.properties" -jar transfer/transfer-00-prerequisites/connector/build/libs/connector.jar
-------
consumer：
java -Dedc.fs.config=transfer/transfer-00-prerequisites/resources/configuration/consumer-configuration.properties -jar transfer/transfer-00-prerequisites/connector/build/libs/connector.jar

 java "-Dedc.fs.config=transfer/transfer-00-prerequisites/resources/configuration/consumer-configuration.properties" -jar transfer/transfer-00-prerequisites/connector/build/libs/connector.jar


```
## 启动 HTTP 服务器
```
docker build -t http-request-logger util/http-request-logger
docker run -p 4000:4000 http-request-logger
```


## 运行


```bash
1、合同协商
python -m scripts.run_experiment --config configs/negotiation_baseline.yaml
2、基本传输
python -m scripts.run_experiment --config configs/transfer_baseline.yaml
3、不同数据规模传输
python -m scripts.run_experiment --config configs/transfer_dataSize.yaml
4、并发传输
 python -m scripts.run_experiment --config configs/concurrent_transfer.yaml
5、provider中断鲁棒
python -m scripts.run_experiment --config configs/provider_restart_during_transfer.yaml
6、consumer中断鲁棒（transfer process 的状态存在 内存 store 里，consumer 重启后，transfer 状态上下文丢失了）
python -m scripts.run_experiment --config configs/consumer_restart_during_transfer.yaml 
7、网络延迟
 python -m scripts.run_experiment --config configs/network_delay_transfer.yaml
8、传输超时
 python -m scripts.run_experiment --config configs/transfer_interruption.yaml
 9、链路抖动
  python -m scripts.run_experiment --config configs/packet_loss_transfer.yaml

10、政策执行开销测试
 python -m scripts.run_experiment --config configs/policy_overhead_simple.yaml
 python -m scripts.run_experiment --config configs/policy_overhead_medium.yaml
 python -m scripts.run_experiment --config configs/policy_overhead_advanced.yaml
```


## 目录

```text
edc-benchmark/
  docker/
  configs/
  scenarios/
  scripts/
  metrics/
  results/
  docs/
  report_template/
```
## 生成不同文件大小

```
fsutil file createnew file_1mb.bin 1048576

fsutil file createnew file_10mb.bin 10485760

fsutil file createnew file_100mb.bin 104857600

然后在那个目录下启动 HTTP 服务：
python -m http.server 8088
```

## 加网络时延，Toxiproxy容器部署

```
docker run -d --name toxiproxy -p 8474:8474 -p 30001:30001 -p 30002:30002 ghcr.io/shopify/toxiproxy

docker ps
```

添加protocol代理在（docs目录下运行）：

```
curl.exe -X POST "http://localhost:8474/proxies" -H "Content-Type: application/json" --data-binary "@provider_protocol_proxy.json"
```

添加public代理：

```
curl.exe -X POST "http://localhost:8474/proxies" -H "Content-Type: application/json" --data-binary "@provider_public_proxy.json"
```

查看所有代理：

```
curl.exe "http://localhost:8474/proxies"
```

加protocol时延：

```
curl.exe -X POST "http://localhost:8474/proxies/provider_protocol_proxy/toxics" -H "Content-Type: application/json" --data-binary "@latency.json" 
```

加public超时：

```
curl.exe -X POST "http://localhost:8474/proxies/provider_public_proxy/toxics" -H "Content-Type: application/json" --data-binary "@timeout.json"
```


改latency(200,500,1000,2000)和flitter,timeout（10000，30000）同时 文件大小，中断注入时间也会影响

运行：

```
 python -m scripts.run_experiment --config configs/network_delay_transfer.yaml

 python -m scripts.run_experiment --config configs/transfer_interruption.yaml
```

 删除时延：

```
 curl.exe -X DELETE "http://localhost:8474/proxies/provider_protocol_proxy/toxics/latency"

  curl.exe -X DELETE "http://localhost:8474/proxies/provider_public_proxy/toxics/timeout"
```

验证是否加上时延或者删掉：

```
 curl.exe "http://localhost:8474/proxies/provider_protocol_proxy/toxics"

  curl.exe "http://localhost:8474/proxies/provider_public_proxy/toxics"
```

 主要看 catalog latency 和 contract-agreement-latency

 删除容器：

```
 docker rm -f toxiproxy
```



# 实验指南

## 链路抖动测试

1. 构建，建议先执行一次transfer_baseline测试是否正常运行

2. 部署Toxiproxy容器，添加protocol代理，添加public代理，

3. 打开packet_loss_transfer.yaml文件，修改experiment_id和output_dir，后面加上自己的学号，

4. 修改repeat次数（3、5、10、20）

   修改data_size_mb ,以及asset_base_url（文件大小，直接改file_10mb或者file_100mb,或者其他大小的文件1、10、50、100、200)，二者相对应，

5. 修改packet_slicer_average_size

   packet_slicer_size_variation

   packet_slicer_delay_u

   本实验的实验矩阵是对不同大小的文件在不同链路抖动的情况，测试成功率和延迟

6. 执行： python -m scripts.run_experiment --config configs/packet_loss_transfer.yaml

| 测试等级 | average_size | size_variation | delay_us | 说明                                 |
| -------- | ------------ | -------------- | -------- | ------------------------------------ |
| 轻度     | 1024         | 64             | 0        | 数据大块传输，抖动小                 |
| 中度     | 512          | 128            | 50       | 中等分片 + 小延迟                    |
| 重度     | 256          | 256            | 200      | 小分片 + 高抖动，网络不稳定          |
| 极端     | 128          | 512            | 500      | 非常碎 + 高延迟，模拟高丢包/网络抖动 |

**单因素测试**：先固定两个参数，只调整一个，观察对传输时间和失败率的影响。

**全组合测试**：结合不同级别参数，做压力矩阵。

## 8、实验八、政策执行开销测试
1.在samples目录下的policy-01-policy-enforcement文件夹里，已经准备好了政策执行开销测试所需的资源文件，分为三个级别：
- SIMPLE级别：地点约束  


- MEDIUM级别：时间范围约束
- ADVANCED级别：数据保护级别约束

把policy.zip里的文件添加或替换在samples的policy目录下，正确目录如下，主要是consumer和provider的config文件，以及四个java文件

```
policy-01-policy-enforcement/
├─ policy-enforcement-consumer/
│  ├─ build/
│  ├─ build.gradle.kts
│  ├─ config-advanced.properties
│  ├─ config-medium.properties
│  ├─ config-simple.properties
│  └─ config.properties
├─ policy-enforcement-provider/
│  ├─ build/
│  ├─ build.gradle.kts
│  ├─ config-advanced.properties
│  ├─ config-medium.properties
│  ├─ config-simple.properties
│  └─ config.properties
├─ policy-functions/
│  ├─ bin/
│  ├─ build/
│  ├─ src/
│  │  └─ main/
│  │     ├─ java/
│  │     │  └─ org/eclipse/edc/sample/extension/policy/
│  │     │     ├─ DataProtectionLevelConstraintFunction.java
│  │     │     ├─ LocationConstraintFunction.java
│  │     │     ├─ PolicyFunctionsExtension.java
│  │     │     └─ TimeRangeConstraintFunction.java
│  │     └─ resources/
│  │        └─ META-INF/
│  │           └─ services/
│  │              └─ org.eclipse.edc.spi.system.ServiceExtension
│  └─ build.gradle.kts
├─ resources/
```

在samples目录下构建：

```
./gradlew policy:policy-01-policy-enforcement:policy-enforcement-provider:build

（在另一个终端）
./gradlew policy:policy-01-policy-enforcement:policy-enforcement-consumer:build
```

2、simple级别测试：

构建后启动提供者（简单）：

```

java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-provider\config-simple.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-provider\build\libs\provider.jar"
```

构建后启动消费者（简单）- 在另一个终端

```

java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-consumer\config-simple.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-consumer\build\libs\consumer.jar"
```

打开policy_overhead_simple.yaml文件，修改experiment_id和output_dir，后面加上自己的学号

修改repeat次数（3、5、10、20）

执行：

```
python -m scripts.run_experiment --config configs/policy_overhead_simple.yaml
```

3、medium级别测试

构建后启动中等级别的提供者和消费者

```
java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-provider\config-medium.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-provider\build\libs\provider.jar"

java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-consumer\config-medium.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-consumer\build\libs\consumer.jar"
```

打开policy_overhead_medium.yaml文件，修改experiment_id和output_dir，后面加上自己的学号

修改repeat次数（3、5、10、20）

执行：

```
python -m scripts.run_experiment --config configs/policy_overhead_medium.yaml
```

4、advanced级别测试

构建后启动高级别的提供者和消费者

```
java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-provider\config-advanced.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-provider\build\libs\provider.jar"

java "-Dedc.fs.config=policy\policy-01-policy-enforcement\policy-enforcement-consumer\config-advanced.properties" -jar "policy\policy-01-policy-enforcement\policy-enforcement-consumer\build\libs\consumer.jar"
```

打开policy_overhead_advanced.yaml文件，修改experiment_id和output_dir，后面加上自己的学号

修改repeat次数（3、5、10、20）

执行：

```
python -m scripts.run_experiment --config configs/policy_overhead_advanced.yaml
```

