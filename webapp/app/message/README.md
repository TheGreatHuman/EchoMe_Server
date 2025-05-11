# Message API 文档

## 概述

消息(Message)接口提供了发送、查询和删除消息的功能。消息是用户与AI之间交流的具体内容，属于特定会话。

## API 接口

### 1. 发送消息（流式响应）

发送用户消息并获取AI的流式回复，实时返回生成内容。

- **URL**: `/api/message/send_message`
- **方法**: `POST`
- **认证**: 需要JWT令牌
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| conversation_id | string | 是 | 会话ID |
| content | string | 是 | 消息内容 |
| type | string | 是 | 消息类型，可选值：text、image、audio、video |

- **请求示例**:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
  "content": "Python中如何处理异常？",
  "type": "text"
}
```

- **响应类型**: `application/x-ndjson` (换行分隔的JSON)

- **流式响应说明**:
  - 响应以流式方式返回，每一行是一个独立的JSON对象
  - 每个JSON对象包含一个文本块或状态更新
  - 客户端应逐行处理响应，并更新UI显示

- **响应流示例**:

```jsonl
{"code": 200, "message": "开始生成", "data": {"ai_message_id": "550e8400-e29b-41d4-a716-446655440005", "chunk": "", "is_last": false}}
{"code": 200, "message": "生成中", "data": {"ai_message_id": "550e8400-e29b-41d4-a716-446655440005", "chunk": "在Python中，异常处理使用", "is_last": false}}
{"code": 200, "message": "生成中", "data": {"ai_message_id": "550e8400-e29b-41d4-a716-446655440005", "chunk": "try-except语句块。", "is_last": false}}
{"code": 200, "message": "生成中", "data": {"ai_message_id": "550e8400-e29b-41d4-a716-446655440005", "chunk": "基本语法如下：", "is_last": false}}
{"code": 200, "message": "生成中", "data": {"ai_message_id": "550e8400-e29b-41d4-a716-446655440005", "chunk": "\n\n```python\ntry:\n    # 可能引发异常的代码\n    result = 10 / 0\nexcept ZeroDivisionError:\n    # 处理特定异常\n    print(\"除数不能为零\")\nexcept Exception as e:\n    # 处理其他异常\n    print(f\"发生异常：{e}\")\nelse:\n    # 没有异常发生时执行\n    print(\"操作成功\")\nfinally:\n    # 无论是否发生异常都会执行\n    print(\"清理资源\")\n```", "is_last": false}}
{"code": 200, "message": "生成完成", "data": {"ai_message_id": "550e8400-e29b-41d4-a716-446655440005", "chunk": "\n\n这种结构可以帮助你有效地管理程序中可能出现的错误情况。", "is_last": true}}
```

- **前端处理示例 (JavaScript)**:

```javascript
// 发送消息并处理流式响应
async function sendMessage(conversationId, content, type) {
  try {
    const response = await fetch('/api/message/send_message', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${yourJwtToken}`
      },
      body: JSON.stringify({
        conversation_id: conversationId,
        content: content,
        type: type
      })
    });

    // 创建响应的reader
    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let aiMessageId = null;
    let accumulatedText = '';
    
    // 创建消息元素（可根据UI框架调整）
    const messageContainer = document.getElementById('message-container');
    const aiMessageElement = document.createElement('div');
    aiMessageElement.className = 'ai-message';
    messageContainer.appendChild(aiMessageElement);

    // 处理流式响应
    while (true) {
      const { value, done } = await reader.read();
      
      if (done) break;
      
      // 解码二进制数据为文本
      const text = decoder.decode(value);
      // 按行分割（每行是一个JSON对象）
      const lines = text.split('\n').filter(line => line.trim());
      
      for (const line of lines) {
        try {
          const data = JSON.parse(line);
          
          // 存储AI消息ID
          if (data.data.ai_message_id && !aiMessageId) {
            aiMessageId = data.data.ai_message_id;
          }
          
          // 处理文本块
          if (data.data.chunk) {
            accumulatedText += data.data.chunk;
            aiMessageElement.textContent = accumulatedText;
            
            // 自动滚动到底部
            messageContainer.scrollTop = messageContainer.scrollHeight;
          }
          
          // 处理错误
          if (data.code !== 200) {
            console.error('API错误:', data.message);
          }
          
          // 处理完成状态
          if (data.data.is_last) {
            console.log('AI回复完成:', accumulatedText);
          }
        } catch (e) {
          console.error('解析JSON失败:', e, line);
        }
      }
    }
    
    return {
      aiMessageId: aiMessageId,
      completeResponse: accumulatedText
    };
    
  } catch (error) {
    console.error('发送消息失败:', error);
    throw error;
  }
}
```

- **错误响应**:

```json
{
  "code": 400,
  "message": "缺少必要参数：content"
}
```

```json
{
  "code": 404,
  "message": "会话不存在"
}
```

```json
{
  "code": 403,
  "message": "无权操作此会话"
}
```

```json
{
  "code": 500,
  "message": "服务器错误: ..."
}
```

### 2. 获取会话的所有消息

获取指定会话的所有消息记录。

- **URL**: `/api/message/get_conversation_messages`
- **方法**: `POST`
- **认证**: 需要JWT令牌
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| conversation_id | string | 是 | 会话ID |

- **请求示例**:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440002"
}
```

- **成功响应**:

```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "message_id": "550e8400-e29b-41d4-a716-446655440004",
      "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
      "type": "text",
      "content": "Python中如何处理异常？",
      "is_user": true,
      "created_at": "2023-05-01T14:00:00Z",
      "end_of_conversation": null
    },
    {
      "message_id": "550e8400-e29b-41d4-a716-446655440005",
      "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
      "type": "text",
      "content": "在Python中，异常处理使用try-except语句块...",
      "is_user": false,
      "created_at": "2023-05-01T14:00:05Z",
      "end_of_conversation": null
    },
    // 更多消息...
  ]
}
```

- **错误响应**:

```json
{
  "code": 400,
  "message": "缺少必要参数：会话ID"
}
```

```json
{
  "code": 404,
  "message": "会话不存在"
}
```

```json
{
  "code": 403,
  "message": "无权查看此会话"
}
```

```json
{
  "code": 500,
  "message": "服务器错误: ..."
}
```

### 3. 删除消息

删除指定的一条或多条消息。

- **URL**: `/api/message/delete_messages`
- **方法**: `POST`
- **认证**: 需要JWT令牌
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| message_ids | array | 是 | 消息ID数组 |

- **请求示例**:

```json
{
  "message_ids": [
    "550e8400-e29b-41d4-a716-446655440004",
    "550e8400-e29b-41d4-a716-446655440005"
  ]
}
```

- **成功响应**:

```json
{
  "code": 200,
  "message": "消息删除成功",
  "data": {
    "deleted_count": 2
  }
}
```

- **错误响应**:

```json
{
  "code": 400,
  "message": "缺少必要参数：消息ID列表"
}
```

```json
{
  "code": 400,
  "message": "消息ID列表不能为空"
}
```

```json
{
  "code": 404,
  "message": "未找到指定的消息"
}
```

```json
{
  "code": 403,
  "message": "无权删除部分消息"
}
```

```json
{
  "code": 500,
  "message": "服务器错误: ..."
}
```

## 错误代码说明

| 错误代码 | 说明 |
|---------|------|
| 200 | 成功 |
| 400 | 客户端请求错误，如参数缺失或格式错误 |
| 401 | 未认证，JWT令牌无效或已过期 |
| 403 | 权限不足，无权操作指定资源 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 流式接口说明

### 关于NDJSON格式

消息发送接口使用NDJSON（Newline Delimited JSON）格式进行流式传输。这种格式的特点是：

1. 每行是一个有效的JSON对象
2. 行与行之间用换行符`\n`分隔
3. 适合流式传输，客户端可以逐行解析

### 流式响应字段说明

| 字段 | 说明 |
|------|------|
| code | 状态码，200表示正常 |
| message | 状态消息，如"开始生成"、"生成中"、"生成完成" |
| data.ai_message_id | AI消息的唯一ID |
| data.chunk | 当前生成的文本块 |
| data.is_last | 是否是最后一个块，true表示生成完成 |

### 前端处理建议

1. 使用`fetch` API的流式处理能力
2. 建立一个文本缓冲区，逐步累加接收到的文本块
3. 每接收到新文本块就更新UI显示
4. 根据`is_last`标志判断生成是否完成
5. 完成后可以将完整内容存储到应用状态中

## 注意事项

1. 消息类型(type)必须是以下值之一：text、image、audio、video
2. 发送消息后会自动调用外部AI服务获取回复，并返回AI回复消息
3. 删除消息前会检查用户对所有消息所属会话的权限 