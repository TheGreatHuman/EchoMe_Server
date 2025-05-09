# WebSocket API 交互指南

本文档为前端开发者提供与后端 WebSocket 服务进行交互的详细指南。

## 目录

1.  [基本约定](#基本约定)
2.  [连接流程](#连接流程)
3.  [核心交互流程（音频上传与处理）](#核心交互流程音频上传与处理)
4.  [客户端 -> 服务器 事件](#客户端---服务器-事件)
    *   [request_connection](#request_connection)
    *   [audio_uploaded](#audio_uploaded)
    *   [stop_session](#stop_session)
5.  [服务器 -> 客户端 事件](#服务器---客户端-事件)
    *   [connection_ack](#connection_ack)
    *   [asr_result](#asr_result)
    *   [tts_audio](#tts_audio)
    *   [task_submitted](#task_submitted)
    *   [task_progress](#task_progress)
    *   [task_result](#task_result)
    *   [error](#error)
    *   [session_stopped_ack](#session_stopped_ack)
6.  [错误处理](#错误处理)
7.  [会话管理](#会话管理)

## 基本约定

*   所有通过 WebSocket 传输的数据都应采用 **JSON** 格式。
*   客户端发往服务器的每个消息都应包含一个 `event` 字段来标识消息类型，以及一个 `data` 字段包含具体数据。
*   服务器到客户端的消息结构类似，也包含 `event` 和 `data` 字段。

## 连接流程

1.  **建立连接**: 客户端向服务器发起 WebSocket 连接。
    *   连接成功后，客户端应立即发送 `request_connection` 事件。

2.  **请求连接 (`request_connection`)**:
    *   客户端发送此事件，告知服务器期望的交互模式（语音或视频）和所选的 AI 角色。
    *   **重要**: 此处选择的模式和角色将固定用于整个会话。

3.  **连接确认 (`connection_ack`)**:
    *   服务器响应 `request_connection` 事件。
    *   如果成功，服务器会返回一个唯一的 `session_id`，确认的交互 `mode`，以及AI角色的详细信息（包括名称、性格、图片URL等）。
    *   客户端应保存 `session_id`，并在后续的事件中（如适用）带上它。

## 核心交互流程（音频上传与处理）

1.  **用户录制音频**: 客户端负责用户音频的录制。

2.  **上传音频文件**:
    *   客户端将录制好的音频文件（推荐 `.wav` 或 `.mp3` 格式）上传到服务器提供的 HTTP 端点（例如 `/api/upload_audio` - 具体端点需与后端确认）。
    *   上传成功后，服务器会返回该音频文件的可公开访问 URL。

3.  **发送 `audio_uploaded` 事件**:
    *   客户端在获取到音频文件的 URL 后，通过 WebSocket 向服务器发送 `audio_uploaded` 事件，并将音频 URL 和当前 `session_id` 包含在数据中。

4.  **服务器处理**:
    *   **ASR (语音识别)**: 服务器接收到音频 URL 后，会调用语音识别服务将音频转换为文本。完成后，服务器会发送 `asr_result` 事件给客户端，包含识别出的用户文本。
    *   **TTS (语音合成)**: 服务器接着会将识别出的文本（或经过LLM处理后的文本）合成为 AI 的回复语音。
    *   **根据模式响应**:
        *   **语音模式 (`voice`)**: 服务器会发送 `tts_audio` 事件，包含 AI 回复的文本和合成语音的 URL。客户端收到后应播放该音频。
        *   **视频模式 (`video`)**: 服务器会提交一个视频生成任务到后台 Worker。
            *   服务器首先会发送 `task_submitted` 事件，告知客户端任务已提交，并提供一个 `task_id`。
            *   Worker 处理过程中，服务器会通过 `task_progress` 事件向客户端实时推送进度（百分比、状态消息）。
            *   任务完成后，服务器会发送 `task_result` 事件，包含最终生成的视频 URL。客户端收到后应加载并播放视频。

5.  **循环**: 用户可以继续上传新的音频，重复步骤 3-4。

## 客户端 -> 服务器 事件

### `request_connection`

*   **触发**: 客户端首次建立 WebSocket 连接成功后。
*   **目的**: 初始化会话，指定交互模式和 AI 角色。
*   **数据负载 (`data`)**:
    ```json
    {
      "token": "user_auth_token_if_needed", // 可选，根据实际认证需求
      "mode": "voice" | "video",            // 必选：交互模式
      "role_id": "fixed_role_identifier"    // 必选：AI 角色 ID
    }
    ```

### `audio_uploaded`

*   **触发**: 客户端已成功将用户音频上传到 HTTP 端点，并获取到音频 URL 后。
*   **目的**: 通知服务器新的用户音频已准备好处理。
*   **数据负载 (`data`)**:
    ```json
    {
      "audio_url": "publicly_accessible_url_to_the_uploaded_audio.wav", // 必选
      "session_id": "user_session_identifier"                             // 必选，由 connection_ack 返回
    }
    ```

### `stop_session`

*   **触发**: 用户在客户端主动点击"停止"或"结束会话"按钮。
*   **目的**: 通知服务器用户希望结束当前会话。服务器将进行资源清理。
*   **数据负载 (`data`)**:
    ```json
    {
      "session_id": "user_session_identifier" // 必选
    }
    ```

## 服务器 -> 客户端 事件

### `connection_ack`

*   **触发**: 响应客户端的 `request_connection` 事件。
*   **目的**: 确认连接成功，返回会话信息和 AI 角色详情。
*   **数据负载 (`data`)**:
    ```json
    {
      "session_id": "unique_session_identifier_for_this_connection",
      "mode": "voice" | "video",
      "ai_role": {
        "role_id": "fixed_role_identifier_for_session",
        "name": "角色名称",
        "personality": "角色的性格描述...",
        "image_url": "url_to_role_reference_image.jpg" // 在视频模式中重要
      },
      "chat_history": [ // 可选，用于加载历史聊天记录
        // {"type": "user", "text": "用户之前的文本", "audio_url": "..."},
        // {"type": "ai", "text": "AI 之前的文本", "audio_url": "..."}
      ]
    }
    ```

### `asr_result`

*   **触发**: 服务器完成对用户上传音频的语音识别后。
*   **目的**: 将识别出的用户文本发送给客户端显示。
*   **数据负载 (`data`)**:
    ```json
    {
      "user_text": "用户所说的识别文本内容。",
      "original_audio_url": "publicly_accessible_url_to_the_uploaded_audio.wav" // 用于客户端关联
    }
    ```

### `tts_audio`

*   **触发**: 服务器完成 TTS 且**连接模式为 "voice"**。
*   **目的**: 将合成的 AI 语音推送给客户端播放。
*   **数据负载 (`data`)**:
    ```json
    {
      "ai_text": "AI 回答的文本内容。",
      "audio_url": "url_to_the_synthesized_ai_audio.wav"
    }
    ```

### `task_submitted`

*   **触发**: 服务器已成功将视频生成任务提交到后台队列 (仅在**连接模式为 "video"** 时)。
*   **目的**: 告知客户端任务已开始排队处理，并提供任务 ID。
*   **数据负载 (`data`)**:
    ```json
    {
      "task_id": "unique_identifier_for_the_background_task",
      "message": "视频生成任务已提交，请稍候..."
    }
    ```

### `task_progress`

*   **触发**: 后台 Worker 在处理视频生成任务过程中上报进度，服务器转发。
*   **目的**: 向客户端实时更新视频生成进度。
*   **数据负载 (`data`)**:
    ```json
    {
      "task_id": "unique_identifier_for_the_background_task",
      "status": "processing" | "progress", // processing 表示开始处理，progress 表示具体进度
      "percentage": 25, // 进度百分比 (0-100)，仅当 status 为 'progress' 时有效
      "message": "正在生成面部动画... (25%)" // 可选的详细信息
    }
    ```

### `task_result`

*   **触发**: 后台 Worker 完成视频生成任务，服务器转发结果。
*   **目的**: 将最终生成的视频 URL 发送给客户端播放。
*   **数据负载 (`data`)**:
    ```json
    {
      "task_id": "unique_identifier_for_the_background_task",
      "status": "completed",
      "video_url": "url_to_the_final_generated_video.mp4"
    }
    ```

### `error`

*   **触发**: 服务器在处理过程中遇到任何错误时。
*   **目的**: 向客户端报告错误信息。
*   **数据负载 (`data`)**:
    ```json
    {
      "task_id": "optional_task_id_if_related_to_a_video_task",
      "message": "详细的错误描述信息。例如：语音识别失败，请重试。"
    }
    ```

### `session_stopped_ack`

*   **触发**: 响应客户端的 `stop_session` 事件。
*   **目的**: 确认会话已成功标记为停止，后端将进行清理。
*   **数据负载 (`data`)**:
    ```json
    {
      "message": "会话已结束"
    }
    ```

## 错误处理

*   服务器通过 `error` 事件向客户端发送错误信息。
*   客户端应监听此事件，并以合适的方式向用户展示错误信息。
*   常见的错误可能包括：音频识别失败、语音合成失败、视频生成失败、参数缺失、无可用 Worker 等。

## 会话管理

*   **会话 ID (`session_id`)**: 由服务器在 `connection_ack` 中生成并返回，用于唯一标识一个客户端连接会话。客户端在后续的某些事件（如 `audio_uploaded`, `stop_session`）中需要携带此 ID。
*   **断开连接**: 当 WebSocket 连接意外断开时，服务器会自动清理与该 `session_id` 相关的资源。
*   **主动停止 (`stop_session`)**: 客户端可以通过发送 `stop_session` 事件来主动请求结束会话。服务器会进行清理，并可能回复 `session_stopped_ack`。

---

请前端开发者仔细阅读此文档，并与后端开发者确认音频上传的具体 HTTP 端点和认证机制（如果需要）。
如有任何疑问，请及时沟通。 