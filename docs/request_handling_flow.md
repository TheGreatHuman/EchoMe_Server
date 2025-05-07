# 请求处理与调用流程详解 (音频接收后)

本文档详细描述了当 WebApp 收到用户上传音频的通知 (`audio_uploaded` 事件) 后，内部及与外部服务、Worker 交互的详细调用流程。这里假设音频文件本身已通过 HTTP 等方式上传，并通过 WebSocket 事件传递了其可访问 URL。

**责任划分:**

*   **`webapp/app/sockets.py`**: 核心编排者。接收 WebSocket 事件 (`request_connection`, `audio_uploaded`, `stop_session`), 调用其他服务/模块，根据模式决定流程分支，监听并转发 Worker 进度/结果。**处理 `disconnect` 和 `stop_session` 事件，触发会话清理逻辑。**
*   **`webapp/app/services/aliyun_api.py`**: 封装对阿里云 API (ASR, TTS) 的调用。
*   **`webapp/app/scheduler.py`**: 决定哪个 Worker 处理任务 (返回队列名)。
*   **`webapp/app/tasks.py`**: 将任务消息实际推送到 Redis 队列。
*   **`FileCleanupService` (假设)**: 一个新的服务，负责根据 `session_id` 查找并删除相关临时文件。
*   **`SessionManager` (假设)**: 管理活动会话的状态 (模式, 角色, 关联的文件列表等)。
*   **`worker/tasks.py`**: Worker 端任务处理主逻辑，调用推理，通过 Reporter 上报状态。
*   **`worker/redis_reporter.py`**: 封装 Worker 向 Redis Pub/Sub 发送状态/结果的逻辑。
*   **`ChatHistoryManager` (假设)**: 一个用于管理用户会话聊天记录的类或模块。
*   **`RoleManager` (假设)**: 管理 AI 角色配置信息的类或模块。

## 调用流程

1.  **触发点: WebSocket 事件接收**
    *   **位置**: `webapp/app/sockets.py`
    *   **事件**: `audio_uploaded`
    *   **处理函数 (示例)**: `on_audio_uploaded(data)`
    *   **输入**: `data = {'audio_url': '...', 'session_id': '...'}`
    *   **前置条件**: 在处理此事件前，服务器应已通过 `session_id` 知道此连接的**交互模式 (`mode`)** 和**当前 AI 角色信息** (在 `connect` / `connection_ack` 时已确定和存储)。
    *   **动作**: 解析 `audio_url` 和 `session_id`。获取当前会话的 `mode` 和 `role_info`。

2.  **记录用户音频**
    *   **调用**: `ChatHistoryManager`
    *   **函数 (示例)**: `chat_manager.add_user_audio(session_id=data['session_id'], audio_url=data['audio_url'])`
    *   **目的**: 将用户输入的音频信息存入聊天记录。

3.  **调用语音识别 (ASR)**
    *   **调用**: `webapp/app/services/aliyun_api.py` -> `AliyunAPIService`
    *   **函数 (示例)**: `recognized_text = aliyun_service.recognize_audio(audio_url=data['audio_url'])`
    *   **目的**: 将音频转换为文字。
    *   **错误处理**: 如果调用失败，应捕获异常并通过 WebSocket 发送 `error` 事件给客户端。

4.  **记录并发送 ASR 结果**
    *   **调用**: `ChatHistoryManager`
    *   **函数 (示例)**: `chat_manager.add_user_text(session_id=data['session_id'], text=recognized_text)`
    *   **调用**: `webapp/app/sockets.py` -> `socketio`
    *   **函数 (示例)**: `socketio.emit('asr_result', {'user_text': recognized_text, 'original_audio_url': data['audio_url']}, room=data['session_id'])`
    *   **目的**: 存储识别文本，并将其发送给客户端显示。

5.  **调用文字转语音 (TTS)**
    *   **获取音色 (可选)**: 从已获取的 `role_info` 中提取 `voice_id`。
    *   **调用**: `webapp/app/services/aliyun_api.py` -> `AliyunAPIService`
    *   **函数 (示例)**: `synthesized_audio_url = aliyun_service.synthesize_speech(text=recognized_text, voice_id=role_voice_id)`
    *   **目的**: 将 AI 回答文本转换为语音。
    *   **错误处理**: 如果调用失败，应捕获异常并通过 WebSocket 发送 `error` 事件。

6.  **记录 AI 回答**
    *   **调用**: `ChatHistoryManager`
    *   **函数 (示例)**: `chat_manager.add_ai_response(session_id=data['session_id'], text=recognized_text, audio_url=synthesized_audio_url)`
    *   **目的**: 将 AI 的文本和对应语音存入聊天记录。

7.  **判断聊天模式 (基于会话初始模式)**
    *   **检查**: `session_mode = get_session_mode(session_id=data['session_id'])` (此信息应在连接建立时存储)

8.  **处理语音聊天模式 (`session_mode == 'voice'`)**
    *   (此步骤仅在模式为"语音聊天"时执行)
    *   **调用**: `webapp/app/sockets.py` -> `socketio`
    *   **函数 (示例)**: `socketio.emit('tts_audio', {'audio_url': synthesized_audio_url, 'ai_text': recognized_text}, room=data['session_id'])`
    *   **目的**: 直接将合成的语音发送给客户端播放。
    *   **流程结束** (等待下一次 `audio_uploaded`)。

9.  **处理视频聊天模式 (`session_mode == 'video'`)**
    *   (此步骤仅在模式为"视频聊天"时执行)
    *   9.1 **获取角色图片**: 
        *   **动作**: 从已获取的 `role_info` 中提取 `role_image_url`。
    *   9.2 **准备任务数据**: 
        *   **动作**: 生成唯一的 `task_id`。
        *   **动作**: 构建 `task_payload = {'task_id': task_id, 'session_id': data['session_id'], 'role_image_url': role_image_url, 'audio_url': synthesized_audio_url, ...}`
    *   9.3 **选择 Worker 队列**: 
        *   **调用**: `webapp/app/scheduler.py` -> `Scheduler`
        *   **函数 (示例)**: `target_queue = scheduler.select_worker_queue()`
        *   **错误处理**: 如果没有可用 Worker，应发送 `error` 事件或进行排队处理。
    *   9.4 **提交任务到队列**: 
        *   **调用**: `webapp/app/tasks.py` -> `TaskSubmitter` (或函数)
        *   **函数 (示例)**: `tasks.submit_task_to_worker(queue_name=target_queue, task_data=task_payload)`
    *   9.5 **通知客户端任务已提交**: 
        *   **调用**: `webapp/app/sockets.py` -> `socketio`
        *   **函数 (示例)**: `socketio.emit('task_submitted', {'task_id': task_id, 'message': '视频生成任务已提交...'}, room=data['session_id'])`
    *   **WebApp 端当前请求处理结束** (后续由 Worker 处理及 Pub/Sub 触发)。

## Worker 端处理流程 (任务入队后触发)

1.  **任务监听与获取**
    *   **位置**: `worker/tasks.py`
    *   **函数 (示例)**: `run_consumer()` 循环
    *   **动作**: `task_data = redis.blpop(worker_queue_name)`
    *   **解析**: 获取 `task_id`, `session_id`, `role_image_url`, `audio_url` 等。

2.  **上报"开始处理"状态**
    *   **调用**: `worker/redis_reporter.py` -> `RedisReporter`
    *   **函数 (示例)**: `reporter.report_status(task_id=task_data['task_id'], session_id=task_data['session_id'], status='processing', message='开始处理视频生成...')`
    *   **同时**: 更新 Worker 自身状态键: `redis.set(f"gpu_status:{gpu_id}", 'busy')`

3.  **定义进度回调函数**
    *   **位置**: `worker/tasks.py`
    *   **函数 (示例)**: 
        ```python
        def progress_callback(percentage, message):
            reporter.report_progress(task_id=task_data['task_id'], session_id=task_data['session_id'], percentage=percentage, message=message)
        ```

4.  **调用核心推理流程**
    *   **调用**: `inference/pipelines/pipeline_echo_mimic_acc.py` -> `Audio2VideoPipeline` 实例
    *   **函数 (示例)**: `video_result = inference_pipeline(ref_image_path=task_data['role_image_url'], audio_path=task_data['audio_url'], ..., progress_callback=progress_callback)`
    *   **目的**: 执行实际的视频生成。
    *   **错误处理**: 如果推理失败，应调用 `reporter.report_error(...)`。

5.  **上报"完成"状态和结果**
    *   **假设**: `video_result` 包含生成的视频 URL: `video_url = video_result['output_url']`
    *   **调用**: `worker/redis_reporter.py` -> `RedisReporter`
    *   **函数 (示例)**: `reporter.report_completion(task_id=task_data['task_id'], session_id=task_data['session_id'], video_url=video_url)`

6.  **更新 Worker 状态**
    *   **动作**: `redis.set(f"gpu_status:{gpu_id}", 'idle')`
    *   **Worker 端当前任务处理结束**。

## WebApp 端 Pub/Sub 监听流程

1.  **监听 Redis Pub/Sub 通道**
    *   **位置**: `webapp/app/sockets.py` (或由 `app/__init__.py` 启动的后台线程/协程)
    *   **函数 (示例)**: `redis_listener_thread()` 循环监听 `pubsub.listen()`

2.  **处理接收到的消息**
    *   **函数 (示例)**: `handle_redis_message(message)`
    *   **动作**: 解析消息数据 (`task_id`, `session_id`, `status`, `percentage`, `message`, `video_url` 等)。

3.  **根据消息类型转发给客户端**
    *   **如果** 消息是进度更新 (`status == 'processing'` 或 `'progress'`):
        *   **调用**: `socketio.emit('task_progress', progress_data, room=message['session_id'])`
    *   **如果** 消息是完成通知 (`status == 'completed'`):
        *   **调用**: `socketio.emit('task_result', result_data, room=message['session_id'])`
    *   **如果** 消息是错误通知 (`status == 'error'`):
        *   **调用**: `socketio.emit('error', error_data, room=message['session_id'])` 

## 会话结束与清理流程

1.  **触发点: WebSocket 事件接收 (`disconnect` 或 `stop_session`)**
    *   **位置**: `webapp/app/sockets.py`
    *   **事件**: `disconnect` (由 SocketIO 库触发) 或 `stop_session`
    *   **处理函数 (示例)**: `on_disconnect()` 或 `on_stop_session(data)`
    *   **输入**: 无 (对于 `disconnect`) 或 `data = {'session_id': '...'}` (对于 `stop_session`)。
    *   **动作**: 从连接信息或 `data` 中获取 `session_id`。

2.  **获取会话关联的文件列表**
    *   **调用**: `SessionManager` (或其他存储会话信息的地方，如 Redis)
    *   **函数 (示例)**: `file_list = session_manager.get_session_files(session_id)`
    *   **目的**: 获取此会话期间生成的所有需要清理的临时文件路径或标识符列表 (包括用户上传的音频、TTS 音频、生成的视频)。这些文件路径需要在生成时就与 `session_id` 关联并存储。

3.  **调用文件清理服务**
    *   **调用**: `FileCleanupService` (假设存在)
    *   **函数 (示例)**: `cleanup_service.delete_files(file_list)`
    *   **目的**: 实际执行文件删除操作（本地文件系统或云存储 API）。
    *   **错误处理**: 记录删除失败的文件，但不应阻塞流程。

4.  **清理会话状态**
    *   **调用**: `SessionManager`, `ChatHistoryManager` 等
    *   **函数 (示例)**: `session_manager.remove_session(session_id)`, `chat_manager.clear_history(session_id)`
    *   **目的**: 从内存或 Redis 中移除该会话的状态信息、聊天记录等。

5.  **(对于 `stop_session`) 发送确认 (可选)**
    *   **调用**: `webapp/app/sockets.py` -> `socketio`
    *   **函数 (示例)**: `socketio.emit('session_stopped_ack', {}, room=session_id)` 