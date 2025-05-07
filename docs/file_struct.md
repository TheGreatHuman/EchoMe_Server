# 文件结构设计 (多 GPU + 调度器 + 模型复用)

这是一个推荐的文件结构，用于分离 Web 应用 (Flask) 和后台 AI 推理 Worker。针对**单机多 GPU** 场景，并引入了 **WebApp 内的调度器** 来分配任务到特定 GPU Worker，同时明确了**模型在 Worker 初始化时加载并复用**。

**注意:** 以下结构是基于当前探测到的文件布局进行的更新。某些功能（如调度器、Worker 逻辑）的具体实现文件可能尚未创建或位于预期之外的位置。

## 根目录结构概览

```
echomimic/
├── webapp/                  # Web 应用目录
│   ├── run.py               # Web 服务器启动脚本 (替代 run_app.py)
│   ├── app/                 # Flask 应用核心代码包 (模块化结构)
│   │   ├── __init__.py      # 初始化 Flask, 可能包含 SocketIO, Redis 连接等
│   │   ├── auth/            # 用户认证模块
│   │   ├── ai_role/         # AI 角色相关模块 (存储/加载角色配置)
│   │   ├── file/            # 文件处理模块 (临时文件存储, 公开 URL 生成)
│   │   ├── models/          # 数据库模型或特定业务模型
│   │   ├── voice/           # 语音处理相关模块 (可能包含部分 ASR/TTS 逻辑触发点)
│   │   ├── services/        # <-- 新增: 外部服务和核心业务逻辑封装
│   │   │   ├── __init__.py
│   │   │   └── aliyun_api.py  # <-- 新增: 封装 Qwen-Audio, CosyVoice API 调用
│   │   ├── scheduler.py     # 任务调度逻辑 (仅选择 Worker 队列)
│   │   ├── sockets.py       # WebSocket 事件处理 (连接, 消息收发, 进度监听转发)
│   │   ├── tasks.py         # WebApp 任务辅助 (仅负责发送任务到队列)
│   │   └── ... (其他模块, templates, static - 如果存在)
│   ├── requirements.txt     # Web 应用依赖
│   ├── config.py            # (推测存在) Web 应用配置
│   └── ... (其他如 .gitignore)
├── worker/                  # 推理 Worker 目录 (当前为空)
│   # ├── run_worker.py      # (预期) Worker 进程启动脚本
│   # ├── worker/            # (预期) Worker 核心逻辑包
│   # │   ├── tasks.py       # (预期) 监听特定任务队列, 调用推理流程
│   # │   └── redis_reporter.py # (预期/可选) 封装向 Redis Pub/Sub 发送进度/结果的逻辑
│   # │   └── ...
│   # ├── config.py          # (预期) Worker 通用配置 (Redis 连接信息等)
│   # └── requirements.txt   # (预期) Worker 依赖
├── inference/               # 共享的核心 AI 推理逻辑目录
│   ├── __init__.py
│   ├── models/              # AI 模型定义
│   │   ├── __init__.py
│   │   ├── unet_2d_condition.py  # 2D UNet 条件模型
│   │   ├── unet_3d_echo.py     # 3D Echo UNet 条件模型
│   │   ├── face_locator.py     # 面部定位器模型
│   │   └── whisper/            # Whisper 相关模型
│   │       └── audio2feature.py # 音频特征提取
│   ├── pipelines/           # 推理流水线
│   │   ├── __init__.py
│   │   └── pipeline_echo_mimic_acc.py # 音频到视频流水线
│   ├── utils/               # 工具函数
│   │   ├── __init__.py
│   │   └── util.py            # 常用工具 (如视频保存、裁剪)
│   └── # (可选) tasks.py / entry.py # 封装 generate_video 逻辑的入口
├── scripts/                 # 启动和管理脚本目录
│   # └── start_workers.sh   # (预期) 启动多个 Worker 的脚本
│   # └── manage.py          # (可选) Python 管理脚本
├── configs/                 # 配置文件目录 (用途待定)
├── pretrained_weights/      # 预训练权重目录
├── docs/                    # 文档目录
│   └── file_struct.md       # 本文件
├── .gitignore
├── requirements.txt         # 项目全局依赖 (可能与 webapp/worker 内重复)
├── infer_example.py         # 推理示例脚本
└── LICENSE
```

## 文件/目录说明 (重点关注预期功能与当前结构)

### `webapp/` - Web 应用

*   **`run.py`**: Web 应用的启动入口。
*   **`app/`**: Flask 应用的核心。
    *   **`__init__.py`**: 应用工厂或初始化脚本，设置 Flask 实例、扩展 (如数据库、登录管理器、SocketIO)、蓝图注册等。Redis 连接和 SocketIO 实例通常在这里初始化。
    *   **`auth/`, `ai_role/`, `file/`, `models/`, `voice/`, `services/`**: 这些目录代表了按功能划分的模块。每个模块内部可能包含自己的路由 (`routes.py` 或 `views.py`)、表单 (`forms.py`)、逻辑 (`services.py`) 等。
    *   **`ai_role/`: 需要实现加载和提供 AI 角色信息（性格、图片路径）的功能。**
    *   **`file/`: 需要实现接收上传文件、保存到临时位置、并生成可公开访问 URL 的功能。**
    *   **路由**: API 路由可能分散在各模块。例如，文件上传路由在 `file/routes.py`。核心交互逻辑可能由 `sockets.py` 处理，或由一个专门的路由触发。
    *   **`services/`**: (新增)
        *   `aliyun_api.py`: 封装对阿里云 Qwen-Audio (ASR) 和 CosyVoice (TTS) 的 API 调用逻辑，处理认证和请求/响应。
    *   **`scheduler.py`**:
        *   **功能**: 实现任务调度，**只负责选择 Worker**。
        *   **预期内容**: 连接 Redis，读取各 Worker 的状态键 (`gpu_status:{id}`), 根据策略 (如轮询空闲 Worker) 返回一个目标任务队列的名称 (如 `task_queue_gpu_0`)。**不直接发送任务**。
    *   **`sockets.py`**:
        *   **功能**: 处理 WebSocket 连接 (`connect`, `disconnect`)，接收客户端消息/音频。**编排核心交互流程**：调用 `services/aliyun_api.py` 进行 ASR/TTS，根据聊天模式决定直接推送音频或调用 `scheduler.py` + `tasks.py` 将任务入队。**关键**: 启动并管理一个后台监听器 (如 Redis Pub/Sub 订阅)，接收 Worker 发送的进度和最终结果，并通过 SocketIO 将信息 `emit` 给正确的客户端房间。
    *   **`tasks.py`** (`webapp/app/tasks.py`):
        *   **功能**: 提供**将任务发送到指定队列**的单一功能。
        *   **预期内容**: 接收由 `sockets.py` (或其他调用者) 准备好的任务数据和由 `scheduler.py` 返回的目标队列名称，连接 Redis，执行 `lpush` 将任务消息推入队列。
    *   **`webapp/config.py` (推测)**: 存储 Web 应用的配置，包括 Redis URL, **各 Worker 状态键前缀**, **任务队列名前缀**, **Redis Pub/Sub 通道名称**, **阿里云 API Keys (AK/SK)**, 临时文件存储路径, SocketIO 相关配置等。

### `worker/` - 推理 Worker (当前为空)

*   **`run_worker.py` (预期)**:
    *   功能: 启动 Worker 进程，初始化时加载模型。
    *   关键: 接收目标 **GPU ID** 和监听的 **特定任务队列名称**。
    *   内容: 设置设备 (`cuda:X`)，调用 `inference` 下的逻辑加载模型到指定 GPU。初始化 Redis 连接。启动时在 Redis 中将自己的状态 (`gpu_status:{id}`) 设置为 'idle'。启动任务监听循环 (`worker.tasks.run_consumer`)。
*   **`worker/tasks.py` (预期)**:
    *   功能: 包含从**特定队列**消费任务、调用推理、**上报进度和结果**的逻辑。
    *   内容: 接收加载好的模型和设备信息。**循环阻塞监听 (`blpop`) 指定的任务队列**。获取任务后，**立即通过 Redis Pub/Sub (`redis_reporter`) 上报"开始处理"状态**，并将 Redis 状态键更新为 'busy'。调用 `inference/pipelines/pipeline_echo_mimic_acc.py` 中的核心推理逻辑，**传入进度回调函数**。进度回调函数内部调用 `redis_reporter` 上报进度百分比。推理完成后，获取结果（如视频 URL），**通过 `redis_reporter` 上报"完成"状态和结果 URL**。最后将 Redis 状态键更新回 'idle'。
*   **`worker/redis_reporter.py` (预期/可选)**:
    *   功能: 封装向 Redis Pub/Sub 发布消息的标准方法。
    *   内容: 提供如 `report_progress(task_id, user_id, percentage)` 和 `report_completion(task_id, user_id, result_url)` 等函数，内部处理连接 Redis 和执行 `publish` 到预定义的通道。
*   **`worker/config.py` (预期)**: 存储 Worker 相关的配置，主要是 Redis 连接信息（如果与 WebApp 不同或为了独立部署）。

### `inference/` - 核心 AI 推理逻辑

*   根据 `infer_example.py` 的使用情况，此目录预期包含以下子模块：
    *   **`models/`**: 存放构成 EchoMimic 核心功能的神经网络模型定义。
        *   `unet_2d_condition.py`: 参考网络的 UNet 模型。
        *   `unet_3d_echo.py`: 去噪网络的 UNet 模型 (包含运动模块)。
        *   `face_locator.py`: 面部定位器模型。
        *   `whisper/audio2feature.py`: 用于从音频提取特征的模型（如 Whisper）。
    *   **`pipelines/`**: 定义将模型组合起来完成特定任务（如音频到视频生成）的推理流水线。
        *   `pipeline_echo_mimic_acc.py`: 实现了核心的 `Audio2VideoPipeline`。
    *   **`utils/`**: 包含推理过程中可能用到的辅助函数。
        *   `util.py`: 包含如视频网格保存 (`save_videos_grid`)、图像裁剪填充 (`crop_and_pad`) 等功能。
*   **模型加载与推理函数**: (与 `infer_example.py` 对照)
    *   **模型加载**: Worker 启动时，应调用类似 `inference/models/` 下模块的 `from_pretrained` 或自定义加载函数，并传入正确的设备参数 (`device`)。`infer_example.py` 中的全局加载部分展示了需要加载哪些模型 (`vae`, `reference_unet`, `denoising_unet`, `face_locator`, `audio_processor`, `face_detector`)。
    *   **推理执行**: Worker 接收到任务后，应调用 `inference/pipelines/pipeline_echo_mimic_acc.py` 中的 `Audio2VideoPipeline` (或一个封装了它的更高层函数) 来执行推理。该流水线需要接收已加载的模型、输入数据（参考图像、音频路径）、配置参数和设备信息。
    *   **核心逻辑封装**: `infer_example.py` 中的 `generate_video` 函数包含了完整的端到端逻辑（包括前处理如人脸检测和裁剪）。这部分逻辑最终应被良好地封装在 `inference/` 目录下，可以是在 `pipelines` 中扩展，或创建一个新的 `tasks.py` 或 `entry.py` 作为 Worker 调用的入口点。

### `scripts/` - 管理脚本

*   **`start_workers.sh` (预期)**:
    *   功能: 启动多个 Worker 实例，为每个实例分配 GPU ID 和特定的任务队列名称。
    *   需要根据 `worker/run_worker.py` 的实际参数传递方式来编写。

### `configs/`

*   包含一些配置文件，具体用途需要根据内部文件判断。

### `pretrained_weights/`

*   存放 AI 模型的预训练权重文件。

### `infer_example.py`

*   一个独立的 Python 脚本，用于演示或测试 `inference/` 目录下的推理功能。

**总结:** 当前文件结构显示 Web 应用部分 (`webapp/app`) 采用了模块化的组织方式。核心的**调度逻辑**和**推理 Worker** 部分的文件尚未在预期位置找到，可能还未实现或放置在其他地方。文档已更新以反映当前的文件布局，并保留了关于调度器、Worker 和模型复用设计思想的描述，指明了这些功能预期实现的位置和方式。您需要根据实际开发进度，创建或调整 `scheduler.py`、`worker/` 目录下的相关文件，并确保它们与 `inference/` 模块正确交互。

核心的**调度逻辑 (`scheduler.py`)**、**WebSocket 处理 (`sockets.py`)** 和 **任务提交辅助 (`tasks.py`)** 文件已在 `webapp/app` 目录下创建。接下来的步骤是实现这些文件中的逻辑，并在 `app/__init__.py` 中正确初始化和连接它们（特别是 SocketIO 和 Redis），同时确保 API 路由能调用调度器。推理 **Worker** 部分的文件仍然需要创建和实现。
