# EchoMimic Worker 服务使用指南

本文档旨在指导开发者如何调用和使用 EchoMimic Worker 服务。Worker 服务负责接收音视频生成任务，执行模型推理，并将结果返回。

## 1. 概述

Worker 服务通过 Redis 进行任务调度和状态同步。客户端将任务推送到指定的 Redis 队列，Worker 从队列中获取任务并处理。任务的处理进度和最终结果会通过 Redis Pub/Sub 机制发布。

## 2. 环境配置

在与 Worker 服务交互之前，请确保 Redis 服务已正确配置并正在运行。Worker 的 Redis 连接信息通过环境变量或配置文件设置，主要包括：

*   `REDIS_HOST`: Redis 服务器地址 (默认: `localhost`)
*   `REDIS_PORT`: Redis 服务器端口 (默认: `6379`)
*   `REDIS_DB`: Redis 数据库索引 (默认: `0`)
*   `REDIS_PASSWORD`: Redis 密码 (默认: `None`)
*   `BASE_URL`: 服务器基础URL (默认: `http://localhost:3000`)，Worker 使用此URL下载和上传文件

请确保客户端连接到与 Worker 服务相同的 Redis 实例和数据库。

## 3. 与 Redis 交互

### 3.1. 任务队列

Worker 服务监听一个特定的 Redis 列表 (List) 作为任务队列。

*   **队列名称**: 由环境变量 `TASK_QUEUE_NAME` 定义，默认为 `task_queue_gpu_{gpu_id}`。例如，如果 Worker 运行在 GPU 0 上，默认队列名称为 `task_queue_gpu_0`。
*   **任务推送**: 客户端需要将任务数据序列化为 JSON, 然后使用 `RPUSH` 命令将其推送到对应的任务队列。

    ```rediscli
    RPUSH task_queue_gpu_0 '{"task_id": "unique_task_123", "ref_image_id": "550e8400-e29b-41d4-a716-446655440000", "audio_id": "661f9511-f3ac-52e5-b827-557766551111", ...}'
    ```

### 3.2. 任务状态与结果 (Redis Pub/Sub)

Worker 服务通过 Redis Pub/Sub 机制发布任务的进度和最终结果。

*   **通道名称**: 由环境变量 `PROGRESS_CHANNEL` 定义，默认为 `task_progress`。
*   **消息格式**: 发布的消息是一个 JSON 字符串，包含以下字段：
    *   `task_id`: (字符串) 任务的唯一标识符。
    *   `session_id`: (字符串) 会话ID，可用于关联特定用户会话。
    *   `status`: (字符串) 任务的当前状态，可能的值包括：
        *   `processing`: 任务正在处理中。
        *   `downloading`: 正在下载所需文件。
        *   `face_detecting`: 正在进行人脸检测。
        *   `inference`: 正在进行模型推理。
        *   `merging_audio`: 正在合并音视频。
        *   `completed`: 任务成功完成。
        *   `failed`: 任务处理失败。
    *   `progress`: (浮点数, 可选) 任务的进度百分比 (0.0 到 100.0)。
    *   `message`: (字符串, 可选) 状态描述或进度消息。
    *   `video_file_id`: (字符串, 仅当 `status` 为 `completed` 时出现) 生成视频的临时文件ID，可用于从临时文件API下载视频。
    *   `error`: (字符串, 仅当 `status` 为 `failed` 时出现) 错误信息。

*   **订阅消息**: 客户端需要订阅 `task_progress` 通道来接收这些更新。

    ```python
    import redis
    import json

    r = redis.Redis(host='localhost', port=6379, db=0)
    pubsub = r.pubsub()
    pubsub.subscribe('task_progress')

    print("Listening for task progress...")
    for message in pubsub.listen():
        if message['type'] == 'message':
            data = json.loads(message['data'].decode('utf-8'))
            print(f"Received: {data}")
            # 在这里处理任务更新，例如根据 task_id 更新UI或数据库
            if data.get('status') == 'completed':
                # 获取生成视频的临时文件ID
                video_file_id = data.get('video_file_id')
                print(f"视频已生成，文件ID: {video_file_id}")
                # 可以通过临时文件API下载视频
    ```

### 3.3. Worker (GPU) 状态

Worker 会将其状态 (如 `idle`, `busy`) 更新到一个特定的 Redis 键。

*   **键名称**: `gpu_status:{gpu_id}` (例如: `gpu_status:0`)
*   **值**: 字符串，如 `idle` (空闲), `busy` (处理任务中)。

客户端可以读取此键来了解特定 GPU Worker 的当前状态，这有助于实现更智能的任务分发。

## 4. 临时文件 API

Worker 使用临时文件 API 来获取输入文件和存储输出视频。在发送任务之前，客户端需要先上传参考图片和音频文件，然后将获得的文件ID作为任务参数传递给Worker。

### 4.1. 上传文件

使用 POST 请求上传文件到临时文件 API：

```
POST /api/tempfile/upload
Content-Type: multipart/form-data
```

**请求体**: 包含 `file` 字段的表单数据

**示例响应** (成功):
```json
{
  "success": true,
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_type": "image",
  "original_name": "reference_face.jpg"
}
```

### 4.2. 下载文件

使用 GET 请求下载之前上传的文件：

```
GET /api/tempfile/download/{file_id}
```

Worker 完成任务后返回的 `video_file_id` 可以用此API下载生成的视频。

**更多详情**: 完整的临时文件 API 文档可在 `webapp/app/file/temp_file_api.md` 中找到。

## 5. 发送任务

### 5.1. 任务数据结构

任务数据是一个 JSON 对象，需要包含以下字段：

```json
{
    "task_id": "string (必须, 任务唯一ID)",
    "session_id": "string (必须, 会话ID)",
    "ref_image_id": "string (必须, 参考人脸图片的临时文件ID)",
    "audio_id": "string (必须, 驱动音频的临时文件ID)",
    "steps": "integer (可选, 推理步数，默认通常为25)",
    "cfg": "float (可选, guidance_scale，默认通常为2.5)",
    "seed": "integer (可选, 随机种子，用于可复现的结果)",
    "frames_num": "integer (可选, 生成视频的帧数。如果未提供，则根据音频长度和FPS自动计算)"
}
```

**重要提示**:

*   `ref_image_id` 和 `audio_id` 是通过临时文件 API 上传文件后获得的文件ID。
*   **不要** 直接使用 URL 或文件路径作为参数。所有文件都应该先上传到临时文件 API。

### 5.2. 发送任务示例 (Python)

```python
import redis
import json
import uuid
import requests

def upload_file_to_tempfile_api(file_path, base_url="http://localhost:3000"):
    """
    上传文件到临时文件API
    
    Args:
        file_path: 本地文件路径
        base_url: 服务器基础URL
        
    Returns:
        str: 成功时返回文件ID，失败时返回None
    """
    upload_url = f"{base_url}/api/tempfile/upload"
    
    with open(file_path, 'rb') as f:
        files = {'file': (os.path.basename(file_path), f)}
        response = requests.post(upload_url, files=files)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                return result.get('file_id')
    
    return None

def submit_task_to_worker(redis_client, task_queue, ref_image_path, audio_path, base_url="http://localhost:3000"):
    """
    上传文件并将任务提交到Worker
    
    Args:
        redis_client: Redis客户端实例
        task_queue: Worker任务队列名称
        ref_image_path: 参考图像的本地路径
        audio_path: 音频文件的本地路径
        base_url: 服务器基础URL
    """
    # 上传参考图像和音频文件
    ref_image_id = upload_file_to_tempfile_api(ref_image_path, base_url)
    audio_id = upload_file_to_tempfile_api(audio_path, base_url)
    
    if not ref_image_id or not audio_id:
        print("文件上传失败")
        return None
    
    # 准备任务数据
    task_id = str(uuid.uuid4())
    session_id = str(uuid.uuid4())  # 通常应该使用实际用户的会话ID
    
    task_data = {
        "task_id": task_id,
        "session_id": session_id,
        "ref_image_id": ref_image_id,
        "audio_id": audio_id,
        "steps": 30,
        "cfg": 3.0,
        "seed": 42
    }
    
    # 将任务提交到Redis队列
    redis_client.rpush(task_queue, json.dumps(task_data))
    print(f"任务已提交，ID: {task_id}")
    return task_id

# 使用示例
if __name__ == "__main__":
    # Redis连接
    r = redis.Redis(host='localhost', port=6379, db=0)
    
    # 提交任务
    task_id = submit_task_to_worker(
        r, 
        'task_queue_gpu_0',
        'path/to/reference_face.jpg',
        'path/to/audio.wav'
    )
    
    if task_id:
        print(f"等待任务 {task_id} 完成...")
        
        # 订阅进度通道
        pubsub = r.pubsub()
        pubsub.subscribe('task_progress')
        
        for message in pubsub.listen():
            if message['type'] == 'message':
                data = json.loads(message['data'].decode('utf-8'))
                
                # 仅处理当前任务的消息
                if data.get('task_id') == task_id:
                    status = data.get('status')
                    
                    if status == 'progress':
                        print(f"进度: {data.get('percentage')}% - {data.get('message', '')}")
                    
                    elif status == 'completed':
                        video_file_id = data.get('video_file_id')
                        print(f"任务完成！视频文件ID: {video_file_id}")
                        print(f"下载链接: http://localhost:3000/api/tempfile/download/{video_file_id}")
                        break
                    
                    elif status == 'error':
                        print(f"任务失败: {data.get('error')}")
                        break
```

## 6. 接收和下载结果

如 [3.2. 任务状态与结果](#32-任务状态与结果-redis-pubsub) 所述，客户端通过订阅 Redis 的 `task_progress` 通道来异步接收任务的进度更新和最终结果。

当收到 `status: "completed"` 的消息时，可以从消息的 `video_file_id` 字段获取生成视频的临时文件ID。使用这个ID，客户端可以通过临时文件 API 下载视频:

```
GET /api/tempfile/download/{video_file_id}
```

**示例** (假设 BASE_URL 是 `http://localhost:3000`):
```
http://localhost:3000/api/tempfile/download/550e8400-e29b-41d4-a716-446655440000
```

## 7. 错误处理

如果任务处理失败，`task_progress` 通道会发布一个 `status: "failed"` 的消息，并在 `error` 字段中包含错误描述。客户端应监控这些消息并进行相应的处理 (例如，重试、记录错误、通知用户)。

## 8. 注意事项

*   **文件有效期**: 临时文件 API 上传的文件有默认的有效期 (通常为 24 小时)，超过有效期后会被自动删除。确保在有效期内下载和使用生成的视频。
*   **资源管理**: 长时间运行的推理任务会消耗大量计算资源 (特别是 GPU)。确保 Worker 服务器有足够的资源。
*   **队列管理**: 监控任务队列的长度，以避免任务积压过多。可以考虑根据 Worker 的数量和处理能力来调整任务提交的速率。
*   **配置一致性**: 客户端和 Worker 端的 Redis 配置 (主机、端口、数据库、密码) 以及队列名称、通道名称必须一致。

---

通过遵循本指南，你应该能够成功地将任务发送到 EchoMimic Worker 服务并接收处理结果。 