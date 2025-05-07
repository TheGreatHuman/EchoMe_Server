# Web 应用详细设计文档

## 1. 简介

Web 应用 (WebApp) 是 AI 推理服务的前端接口，负责通过 WebSocket 连接接收用户的推理请求、与后端任务队列和推理工作节点交互、并实时向用户展示任务状态和结果。 **所有用户交互均通过 WebSocket 连接进行。**

## 2. 技术栈 (建议)

*   **Web 框架:** Flask (Python)
*   **WebSocket 库:** Flask-SocketIO

## 3. WebSocket 接口

WebSocket 用于实现服务器与客户端之间的双向实时通信。用户通过建立的 WebSocket 连接提交任务、查询状态并接收实时更新和结果。

*   **连接端点:** `/ws` (具体路径可能由 Flask-SocketIO 配置决定)

### 3.1. 客户端 -> 服务器 事件 (Commands)

*   **`submit_task`**
    *   **用途:** 客户端通过 WebSocket 连接提交一个新的 AI 推理任务。
    *   **数据 (Data):**
        ```json
        {
          "user_id": "string", // 用户唯一标识符
          "input_data": { // 推理所需的输入数据，具体结构根据模型需求定义
            "param1": "value1",
            "param2": 123
            // ... 其他参数或数据引用 (例如 S3 URL)
          },
          "model_id": "string | null" // (可选) 指定要使用的模型 ID，如果为 null 或未提供，则使用默认模型
        }
        ```
    *   **服务器响应:** 通过 `task_submitted_ack` 或 `error` 事件响应。

*   **`query_task_status`**
    *   **用途:** 客户端查询一个或多个特定任务的当前状态。
    *   **数据 (Data):**
        ```json
        {
          "task_ids": ["string", ...] // 一个包含要查询的任务 ID 字符串的数组
        }
        ```
    *   **服务器响应:** 对每个 `task_id` 通过 `task_status_response` 或 `error` 事件响应。

*   **`subscribe_task`**
    *   **用途:** 客户端订阅一个或多个特定任务的实时更新 (状态变化, 进度, 结果, 错误)。
    *   **数据 (Data):**
        ```json
        {
          "task_ids": ["string", ...] // 一个包含任务 ID 字符串的数组
        }
        ```
    *   **服务器响应:** 通常不直接响应此事件，而是开始推送后续的 `task_update`, `task_result`, `task_error` 事件。如果订阅失败（例如 task_id 不存在或无权限），可以通过 `error` 事件通知客户端。

*   **`unsubscribe_task`**
    *   **用途:** 客户端取消对某个任务的实时更新订阅。
    *   **数据 (Data):**
        ```json
        {
          "task_ids": ["string", ...] // 一个包含要取消订阅的任务 ID 字符串的数组
        }
        ```

*   **(可选) `list_models`**
    *   **用途:** 客户端请求获取服务器上可用的 AI 模型列表。
    *   **数据 (Data):**
        ```json
        {
        }
        ```
    *   **服务器响应:** 通过 `models_list` 或 `error` 事件响应。


### 3.2. 服务器 -> 客户端 事件 (Events)

*   **`connect_ack`** (或者由 Socket.IO 库自动处理连接确认)
    *   **用途:** 服务器确认 WebSocket 连接已成功建立。
    *   **数据 (Data):**
        ```json
        {
          "message": "WebSocket connection established successfully.",
          "server_time": "string" // (可选) 当前服务器时间 (ISO 8601)
        }
        ```

*   **`task_submitted_ack`**
    *   **用途:** 服务器确认已成功接收并开始处理 `submit_task` 命令。
    *   **数据 (Data):**
        ```json
        {
          "task_id": "string", // 为此任务生成的唯一标识符
          "message": "任务已成功提交并排队等待处理。",
          "timestamp": "string" // 事件发生时间 (ISO 8601)
        }
        ```

*   **`task_status_response`**
    *   **用途:** 服务器响应 `query_task_status` 命令，提供任务的当前状态。
    *   **数据 (Data):**
        ```json
        {
          "task_id": "string", // 任务 ID
          "status": "string", // 任务状态 ("pending", "processing", "completed", "failed")
          "progress": "integer | null", // (可选) 处理进度百分比 (0-100)，仅在 "processing" 状态下可能提供
          "submitted_at": "string", // 任务提交时间 (ISO 8601 格式)
          "started_at": "string | null", // (可选) 任务开始处理时间 (ISO 8601 格式)
          "completed_at": "string | null", // (可选) 任务完成时间 (ISO 8601 格式)
          "result": "object | null", // (可选) 推理结果，仅在 status 为 "completed" 时存在，具体结构取决于模型输出
          "error_message": "string | null", // (可选) 错误信息，仅在 status 为 "failed" 时存在
          "timestamp": "string" // 事件发生时间 (ISO 8601)
        }
        ```

*   **`task_update`**
    *   **用途:** 当已订阅任务的状态或进度发生变化时，服务器向客户端推送此事件。
    *   **数据 (Data):**
        ```json
        {
          "task_id": "string",
          "status": "string", // 当前状态 ("pending", "processing")
          "progress": "integer | null", // 当前进度 (0-100)
          "timestamp": "string" // 事件发生时间 (ISO 8601)
        }
        ```

*   **`task_result`**
    *   **用途:** 当已订阅任务成功完成时，服务器向客户端推送此事件，包含最终结果。
    *   **数据 (Data):**
        ```json
        {
          "task_id": "string",
          "status": "completed",
          "result": "object", // 推理结果
          "completed_at": "string", // 完成时间 (ISO 8601)
          "timestamp": "string" // 事件发生时间 (ISO 8601)
        }
        ```

*   **`task_error`**
    *   **用途:** 当已订阅任务处理失败时，服务器向客户端推送此事件，包含错误信息。
    *   **数据 (Data):**
        ```json
        {
          "task_id": "string",
          "status": "failed",
          "error_message": "string", // 具体的错误描述
          "failed_at": "string", // 失败时间 (ISO 8601)
          "timestamp": "string" // 事件发生时间 (ISO 8601)
        }
        ```
*   **(可选) `models_list`**
    *   **用途:** 服务器响应 `list_models` 命令，提供可用的模型列表。
    *   **数据 (Data):**
        ```json
        {
          "models": [
            {
              "id": "string", // 模型唯一标识符
              "name": "string", // 模型名称 (用户友好)
              "description": "string", // 模型描述
              "input_schema": "object", // (可选) 描述模型期望的 input_data 结构
              "output_schema": "object" // (可选) 描述模型 result 的结构
            }
            // ... 更多模型
          ],
          "timestamp": "string" // 事件发生时间 (ISO 8601)
        }
        ```

*   **`error`**
    *   **用途:** 服务器向客户端发送通用的错误信息，例如无效命令、处理请求失败、订阅失败等。
    *   **数据 (Data):**
        ```json
        {
          "message": "string", // 错误描述
          "details": "string | object | null", // (可选) 错误的详细信息
          "timestamp": "string" // 事件发生时间 (ISO 8601)
        }
        ```

## 4. 会话数据管理 (内存)

*   **目的:** 在每个 WebSocket 连接的生命周期内，需要在服务器内存中临时存储与该连接相关的数据。这可能包括用户上传数据的引用、中间计算结果、用户特定的会话设置等。
*   **机制:**
    *   当一个客户端成功建立 WebSocket 连接时，服务器可以为其分配一个内存存储区域。在使用 Flask-SocketIO 时，可以利用其提供的 `session` 机制（与 Flask session 不同，这是 Socket.IO 连接特定的）或者维护一个以连接的唯一会话 ID (`sid`) 为键的 Python 字典。
    *   在处理来自特定客户端的事件 (如 `submit_task`) 时，服务器可以访问和修改与该连接 (`sid`) 关联的内存数据。
    *   **关键:** 必须实现当客户端断开连接时（对应 Flask-SocketIO 中的 `disconnect` 事件）自动清理与该 `sid` 相关的所有内存数据的逻辑。这可以防止内存泄漏。
*   **数据示例:**
    *   `{ sid1: { uploaded_file_path: "/tmp/user_upload_xyz", current_task_ids: ["task1", "task2"] }, sid2: { ... } }`
*   **注意:** 这种内存存储是临时的，适用于不需要持久化的会话数据。如果服务器重启，这些数据将丢失。
