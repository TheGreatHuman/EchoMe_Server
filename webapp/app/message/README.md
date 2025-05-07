# Message API 文档

## 概述

消息(Message)接口提供了发送、查询和删除消息的功能。消息是用户与AI之间交流的具体内容，属于特定会话。

## API 接口

### 1. 发送消息

发送用户消息并获取AI回复。

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

- **成功响应**:

```json
{
  "code": 200,
  "message": "消息发送成功",
  "data": {
    "user_message": {
      "message_id": "550e8400-e29b-41d4-a716-446655440004",
      "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
      "type": "text",
      "content": "Python中如何处理异常？",
      "is_user": true,
      "created_at": "2023-05-01T14:00:00Z",
      "end_of_conversation": null
    },
    "ai_message": {
      "message_id": "550e8400-e29b-41d4-a716-446655440005",
      "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
      "type": "text",
      "content": "在Python中，异常处理使用try-except语句块...",
      "is_user": false,
      "created_at": "2023-05-01T14:00:05Z",
      "end_of_conversation": null
    }
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
| 400 | 请求参数错误 |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |

## 注意事项

1. 消息类型(type)必须是以下值之一：text、image、audio、video
2. 发送消息后会自动调用外部AI服务获取回复，并返回AI回复消息
3. 删除消息前会检查用户对所有消息所属会话的权限 