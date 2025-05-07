#!/bin/bash

# 定义默认值
REDIS_HOST="localhost"
REDIS_PORT=6379
BASE_URL="http://localhost:5000"
NUM_WORKERS=1
VISIBLE_DEVICES=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  case $1 in
    --redis-host)
      REDIS_HOST="$2"
      shift 2
      ;;
    --redis-port)
      REDIS_PORT="$2"
      shift 2
      ;;
    --base-url)
      BASE_URL="$2"
      shift 2
      ;;
    --num-workers)
      NUM_WORKERS="$2"
      shift 2
      ;;
    --visible-devices)
      VISIBLE_DEVICES="$2"
      shift 2
      ;;
    *)
      echo "未知参数: $1"
      exit 1
      ;;
  esac
done

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
# 获取项目根目录
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 导出通用环境变量
export REDIS_HOST="$REDIS_HOST"
export REDIS_PORT="$REDIS_PORT"
export BASE_URL="$BASE_URL"

# 如果指定了VISIBLE_DEVICES，则设置CUDA_VISIBLE_DEVICES
if [[ -n "$VISIBLE_DEVICES" ]]; then
  export CUDA_VISIBLE_DEVICES="$VISIBLE_DEVICES"
  echo "设置CUDA_VISIBLE_DEVICES=$VISIBLE_DEVICES"
fi

# 确定GPU数量
if [[ -n "$VISIBLE_DEVICES" ]]; then
  GPUS=($(echo $VISIBLE_DEVICES | tr ',' ' '))
  NUM_GPUS=${#GPUS[@]}
else
  # 尝试检测系统GPU数量
  if command -v nvidia-smi &>/dev/null; then
    NUM_GPUS=$(nvidia-smi --query-gpu=name --format=csv,noheader | wc -l)
  else
    NUM_GPUS=1
    echo "警告: 无法检测GPU数量，默认为1"
  fi
fi

# 根据参数和可用GPU确定实际启动的worker数量
if [[ $NUM_WORKERS -gt $NUM_GPUS ]]; then
  echo "警告: 请求的worker数量($NUM_WORKERS)超过可用GPU数量($NUM_GPUS)，将使用最大可用数量"
  NUM_WORKERS=$NUM_GPUS
fi

echo "============================================="
echo "启动 EchoMimic Workers"
echo "Redis主机: $REDIS_HOST"
echo "Redis端口: $REDIS_PORT"
echo "基础URL: $BASE_URL"
echo "启动Worker数量: $NUM_WORKERS"
echo "============================================="

# 创建日志目录
LOG_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOG_DIR"

# 启动Worker实例
for ((i=0; i<$NUM_WORKERS; i++)); do
  QUEUE_NAME="task_queue_gpu_$i"
  LOG_FILE="$LOG_DIR/worker_$i.log"
  
  echo "启动Worker $i，监听队列: $QUEUE_NAME"
  
  # 使用nohup后台运行worker进程
  nohup python -u "$PROJECT_ROOT/worker/run_worker.py" \
    --gpu-id $i \
    --redis-host "$REDIS_HOST" \
    --redis-port "$REDIS_PORT" \
    --queue-name "$QUEUE_NAME" \
    > "$LOG_FILE" 2>&1 &
  
  # 记录进程ID
  WORKER_PID=$!
  echo "Worker $i 启动成功，进程ID: $WORKER_PID, 日志文件: $LOG_FILE"
  
  # 等待一小段时间，避免同时启动多个worker导致资源争用
  sleep 2
done

echo "所有Worker已启动"
echo "使用 'tail -f $LOG_DIR/worker_*.log' 查看日志"
echo "=============================================" 