# WebSocket 通信协议详解

本文档基于 `interaction_flow.md`，详细定义了客户端 (Client) 与服务器 (WebApp) 之间通过 WebSocket 进行通信的事件名称和数据负载格式。

## 基本约定

*   所有通过 WebSocket 传输的数据都应采用 JSON 格式。
*   每个消息都包含一个 `event` 字段来标识消息类型。
*   服务器到客户端的消息可能包含一个 `task_id` (如果与特定后台任务相关) 和 `user_id` (或 `session_id`)，用于客户端关联。

## 客户端 -> 服务器 事件

1.  **`request_connection` (或隐式 `connect`)**
    *   **触发**: 客户端首次建立 WebSocket 连接时。
    *   **目的**: 通知服务器新连接建立，并指定**本次会话固定**的交互模式和 AI 角色。
    *   **数据负载 (Payload)**: 
        ```json
        {
          "event": "request_connection", 
          "data": {
            "token": "user_auth_token_if_needed", 
            "mode": "voice | video", 
            "role_id": "fixed_role_identifier_for_session", // 会话期间角色固定
            "conversation_id": "current_conversation_id",
            "speech_rate": 1.0, 
            "pitch_rate": 1.0, 
            "image_id": "uploaded image id"
          }
        }
        ```
    *   **服务器响应**: `connection_ack` 事件。

2.  **`audio_stream_chunk`** (流式上传音频)
    *   **触发**: 用户开始说话并持续发送音频数据流。
    *   **目的**: 将用户语音实时传输到服务器进行处理。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "audio_stream_chunk",
          "data": {
            "chunk": "base64_encoded_audio_data", // 二进制音频数据的Base64编码
            "is_last": false, // 标识是否为最后一个音频块
            "timestamp": "client_timestamp_isoformat", // 可选，用于排序
            "format": "wav" // 音频格式，可选
          }
        }
        ```
    *   **服务器响应**: 如果是最后一个块，服务器开始处理整个音频并通过后续事件返回结果。

3.  **`audio_uploaded`** (单独上传音频)
    *   **触发**: 用户完成录音后通过HTTP上传完整音频文件，然后通过WebSocket发送通知。
    *   **目的**: 通知服务器用户已上传一段新的音频，并提供了访问该音频的方式。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "audio_uploaded",
          "data": {
            "audio_url": "publicly_accessible_url_to_the_uploaded_audio.wav", // 由 HTTP 上传接口返回
            "session_id": "user_session_identifier", // 确保服务器知道是哪个用户的音频
            "timestamp": "client_timestamp_isoformat" // 可选，用于排序
          }
        }
        ```
    *   **服务器响应**: 服务器开始处理（调用 ASR -> TTS -> ...），并通过后续事件返回结果/进度。

4.  **`stop_session` (可选)**
    *   **触发**: 用户在客户端主动点击"停止"或"结束会话"按钮。
    *   **目的**: 通知服务器用户希望结束当前会话并清理相关资源，可能但不一定会立即断开连接。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "stop_session",
          "data": {
            "session_id": "user_session_identifier"
          }
        }
        ```
    *   **服务器响应**: 可选发送一个确认事件 `session_stopped_ack`。服务器会触发后台清理任务。

5.  **`disconnect` (隐式事件)**
    *   **触发**: 客户端断开 WebSocket 连接。
    *   **目的**: 通知服务器连接已断开，**触发会话相关的临时文件清理**。
    *   **数据负载 (Payload)**: 无。
    *   **服务器响应**: 无，服务器内部处理清理逻辑。

## 服务器 -> 客户端 事件

1.  **`connection_ack`**
    *   **触发**: 响应客户端的 `request_connection` (或隐式 `connect`) 事件。
    *   **目的**: 确认连接成功，并发送会话 ID、已确认的交互模式和**固定的 AI 角色信息**。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "connection_ack",
          "data": {
            "session_id": "unique_session_identifier_for_this_connection",
          }
        }
        ```

2.  **`llm_result`**
    *   **触发**: 服务器完成对用户上传音频的回答后。
    *   **目的**: 将回复文本发送给客户端显示。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "asr_result",
          "data": {
            "user_text": "用户所说的识别文本内容。",
            "original_audio_url": "publicly_accessible_url_to_the_uploaded_audio.wav" // 用于客户端关联
          }
        }
        ```

3.  **`tts_audio_stream`** (语音聊天模式下的流式TTS)
    *   **触发**: 服务器在语音聊天模式下实时生成TTS音频流时。
    *   **目的**: 将合成的AI语音以流的形式推送给客户端，实现更快的响应体验。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "tts_audio_stream",
          "data": {
            "chunk": "base64_encoded_audio_data", // 二进制音频数据的Base64编码
            "is_last": false, // 标识是否为最后一个音频块
            "timestamp": "server_timestamp_isoformat",
            "text_part": "当前音频块对应的文本片段", // 可选，用于客户端同步显示文本
            "format": "mp3" // 音频格式
          }
        }
        ```
    *   **说明**: 服务器会持续发送多个`tts_audio_stream`事件，直到完整的语音合成完成。最后一个块的`is_last`为`true`。

4.  **`tts_audio`** (完整音频文件)
    *   **触发**: 当完整的TTS音频合成完成，且**客户端需要完整音频文件**时。
    *   **目的**: 将合成的AI语音完整文件推送给客户端播放。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "tts_audio",
          "data": {
            "ai_text": "AI 回答的文本内容。", 
            "audio_url": "url_to_the_synthesized_ai_audio.wav"
          }
        }
        ```

5.  **`task_submitted`**
    *   **触发**: 服务器已成功将视频生成任务提交到后台队列 (仅在**连接模式为"视频聊天"**时)。
    *   **目的**: 告知客户端任务已开始排队处理，并提供任务 ID。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "task_submitted",
          "data": {
            "task_id": "unique_identifier_for_the_background_task",
            "message": "视频生成任务已提交，请稍候..."
          }
        }
        ```

6.  **`task_progress`**
    *   **触发**: 后台 Worker 在处理视频生成任务过程中，通过 Redis Pub/Sub 上报进度，WebApp 监听到并转发。
    *   **目的**: 向客户端实时更新视频生成进度。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "task_progress",
          "data": {
            "task_id": "unique_identifier_for_the_background_task",
            "status": "processing | generating | rendering | ...", // 当前状态描述
            "percentage": 25, // 进度百分比 (0-100)
            "message": "正在生成面部动画... (25%)" // 可选的详细信息
          }
        }
        ```

7.  **`task_result`**
    *   **触发**: 后台 Worker 完成视频生成任务，WebApp 监听到结果并转发。
    *   **目的**: 将最终生成的视频 URL 发送给客户端播放。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "task_result",
          "data": {
            "task_id": "unique_identifier_for_the_background_task",
            "status": "completed",
            "video_url": "url_to_the_final_generated_video.mp4"
          }
        }
        ```

8.  **`error`**
    *   **触发**: 服务器在处理过程中遇到任何错误时 (如 API 调用失败、任务处理失败等)。
    *   **目的**: 向客户端报告错误信息。
    *   **数据负载 (Payload)**:
        ```json
        {
          "event": "error",
          "data": {
            "task_id": "optional_task_id_if_related",
            "code": "ERROR_CODE_ENUM", // 可选的错误码
            "message": "详细的错误描述信息。例如：语音识别失败，请重试。"
          }
        }
        ``` 