from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STUDENT_ID = "32264700042"

@dataclass(frozen=True)
class MatrixEntry:
    group: str
    size_mb: int
    jitter: str
    avg_size: int
    size_var: int
    delay_us: int
    poll_timeout_s: int


MATRIX: list[MatrixEntry] = [
    MatrixEntry("M01", 1, "轻度", 1024, 64, 0, 240),
    MatrixEntry("M02", 1, "中度", 512, 128, 50, 240),
    MatrixEntry("M03", 1, "重度", 256, 256, 200, 240),
    MatrixEntry("M04", 1, "极端", 128, 512, 500, 360),
    MatrixEntry("M05", 10, "轻度", 1024, 64, 0, 240),
    MatrixEntry("M06", 10, "中度", 512, 128, 50, 240),
    MatrixEntry("M07", 10, "重度", 256, 256, 200, 360),
    MatrixEntry("M08", 10, "极端", 128, 512, 500, 480),
    MatrixEntry("M09", 100, "轻度", 1024, 64, 0, 360),
    MatrixEntry("M10", 100, "中度", 512, 128, 50, 480),
    MatrixEntry("M11", 100, "重度", 256, 256, 200, 600),
    MatrixEntry("M12", 100, "极端", 128, 512, 500, 900),
]

REPEAT = 5
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_DIR = SCRIPT_DIR / "configs" / "jitter_matrix"
SUMMARY_DIR = SCRIPT_DIR / "results" / "local" / f"{STUDENT_ID}_jitter_matrix_{TIMESTAMP}"
# ↑ 合并掉了 SUMMARY_DIR_REL，因为只在 generate_config_text 中需要相对路径


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="链路抖动压力矩阵批量实验")
    parser.add_argument("groups", nargs="*", help="可选：只运行指定组（例如 M01 M05）")
    return parser.parse_args()


def generate_config_text(entry: MatrixEntry) -> str:
    # 用相对于 SCRIPT_DIR 的路径
    output_dir = SUMMARY_DIR.relative_to(SCRIPT_DIR) / entry.group
    return f"""\
experiment_id: {STUDENT_ID}_{entry.group}_{TIMESTAMP}
scenario: packet_loss_transfer
repeat: {REPEAT}
output_dir: {output_dir.as_posix()}

provider_management_url: http://localhost:19193/management
consumer_management_url: http://localhost:29193/management
provider_protocol_url: http://localhost:30001/protocol
consumer_protocol_url: http://localhost:29194/protocol
provider_public_url: http://localhost:30002/public

api_key: password
request_timeout_s: 30
poll_interval_s: 0.2
poll_timeout_s: {entry.poll_timeout_s}

data_size_mb: {entry.size_mb}
asset_base_url: http://localhost:8088/file_{entry.size_mb}mb.bin

asset_template_path: transfer/transfer-01-negotiation/resources/create-asset.json
policy_template_path: transfer/transfer-01-negotiation/resources/create-policy.json
contract_definition_template_path: transfer/transfer-01-negotiation/resources/create-contract-definition.json
dataset_request_template_path: transfer/transfer-01-negotiation/resources/get-dataset.json
negotiation_template_path: transfer/transfer-01-negotiation/resources/negotiate-contract.json
transfer_template_path: transfer/transfer-02-provider-push/resources/start-transfer.json

toxiproxy_base_url: http://localhost:8474
toxiproxy_protocol_proxy_name: provider_protocol_proxy
toxiproxy_public_proxy_name: provider_public_proxy

packet_slicer_average_size: {entry.avg_size}
packet_slicer_size_variation: {entry.size_var}
packet_slicer_delay_us: {entry.delay_us}

retry_attempts: 3
retry_interval_s: 5
"""


def generate_configs() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    for entry in MATRIX:
        cfg = CONFIG_DIR / f"{entry.group}.yaml"
        cfg.write_text(generate_config_text(entry), encoding="utf-8")
        print(f"[生成] {cfg.name}  ({entry.size_mb}MB / {entry.jitter}: "
              f"avg={entry.avg_size} var={entry.size_var} delay={entry.delay_us}us)")


def run_group(entry: MatrixEntry) -> bool:
    cfg = CONFIG_DIR / f"{entry.group}.yaml"

    print(f"\n{'=' * 64}")
    print(f"  {entry.group}  |  {entry.size_mb}MB  |  {entry.jitter}  |  "
          f"avg={entry.avg_size} var={entry.size_var} delay={entry.delay_us}us")
    print(f"  repeat={REPEAT}  poll_timeout={entry.poll_timeout_s}s")
    print('=' * 64)

    ret = subprocess.run(
        [sys.executable, "-m", "scripts.run_experiment", "--config", str(cfg)],
        cwd=SCRIPT_DIR, check=False,
    ).returncode

    ok = ret == 0
    print(f"[{'完成' if ok else '失败'}] {entry.group} {'成功' if ok else '出错，继续下一组...'}")
    return ok


def generate_summary() -> None:
    print(f"\n{'=' * 64}\n  汇总所有实验结果\n{'=' * 64}")

    summary_csv = SUMMARY_DIR / "all_metrics.csv"
    summary_csv.parent.mkdir(parents=True, exist_ok=True)
    total = 0

    with summary_csv.open("w", encoding="utf-8", newline="") as out:
        writer = None

        for entry in MATRIX:
            metrics_csv = SUMMARY_DIR / entry.group / "metrics.csv"
            if not metrics_csv.is_file():
                print(f"[警告] {entry.group}: metrics.csv 不存在，跳过")
                continue

            with metrics_csv.open("r", encoding="utf-8", newline="") as f:
                rows = list(csv.reader(f))

            if len(rows) < 2:  # 空文件或只有表头
                print(f"[警告] {entry.group}: metrics.csv 无数据，跳过")
                continue

            header, data_rows = rows[0], rows[1:]

            if writer is None:
                writer = csv.writer(out)
                writer.writerow(header + ["student_id", "group", "file_size_mb", "jitter_level"])

            for row in data_rows:
                writer.writerow(row + [STUDENT_ID, entry.group, str(entry.size_mb), entry.jitter])

            print(f"[汇总] {entry.group}: {len(data_rows)} 条记录")
            total += len(data_rows)

    if total:
        print(f"\n汇总文件: {summary_csv}\n总记录数: {total}")
    else:
        summary_csv.unlink(missing_ok=True)  # 没数据就删掉空文件
        print("[警告] 无任何有效数据，未生成汇总文件")


def main() -> int:
    args = parse_args()
    groups_to_run = {g.strip().upper() for g in args.groups if g.strip()}

    sep = '=' * 64
    print(f"{sep}\n  链路抖动压力矩阵 —— 批量实验\n  学号: {STUDENT_ID}"
          f"\n  {len(MATRIX)} 组 × {REPEAT} 次 = {len(MATRIX) * REPEAT} 次实验"
          f"\n  时间戳: {TIMESTAMP}\n{sep}")

    # 校验组号
    valid_groups = {e.group for e in MATRIX}
    if bad := sorted(groups_to_run - valid_groups):
        print(f"[警告] 以下组号不存在，将忽略: {' '.join(bad)}")

    generate_configs()
    print(f"\n所有配置已生成到: {CONFIG_DIR}/\n")

    # 逐组运行
    entries = [e for e in MATRIX if not groups_to_run or e.group in groups_to_run]
    if not entries:
        print("[错误] 没有匹配到任何可运行的组号")
        return 1

    results = [run_group(e) for e in entries]
    succeeded, failed = results.count(True), results.count(False)

    generate_summary()

    print(f"\n{sep}\n  实验完成！  学号: {STUDENT_ID}"
          f"\n  总计: {len(entries)} 组  |  成功: {succeeded}  |  失败: {failed}"
          f"\n  结果目录: {SUMMARY_DIR}\n{sep}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())