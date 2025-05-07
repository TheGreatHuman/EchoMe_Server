# Conversation API 文档

## 概述

会话(Conversation)接口提供了创建、查询、修改和删除会话的功能。会话是用户与特定AI角色之间的交流容器，包含多条消息。

## API 接口

### 1. 创建会话

创建一个新的会话。

- **URL**: `/api/conversation/create_conversation`
- **方法**: `POST`
- **认证**: 需要JWT令牌
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| role_id | string | 是 | AI角色ID |
| title | string | 否 | 会话标题，默认为"新的聊天" |
| voice_id | string | 否 | 语音ID |
| speech_rate | integer | 否 | 语速，范围5-20，默认10 |
| pitch_rate | integer | 否 | 音调，范围5-20，默认10 |

- **请求示例**:

```json
{
  "role_id": "550e8400-e29b-41d4-a716-446655440000",
  "title": "关于Python的讨论",
  "voice_id": "550e8400-e29b-41d4-a716-446655440001",
  "speech_rate": 12,
  "pitch_rate": 10
}
```

- **成功响应**:

```json
{
  "code": 200,
  "message": "会话创建成功",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
    "role_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440003",
    "title": "关于Python的讨论",
    "last_message": null,
    "last_message_time": null,
    "created_at": "2023-05-01T12:00:00Z",
    "voice_id": "550e8400-e29b-41d4-a716-446655440001",
    "speech_rate": 12,
    "pitch_rate": 10
  }
}
```

- **错误响应**:

```json
{
  "code": 400,
  "message": "缺少必要参数：角色ID"
}
```

```json
{
  "code": 500,
  "message": "服务器错误: ..."
}
```

### 2. 查询用户与特定角色的所有会话

查询当前用户与指定角色的所有会话。

- **URL**: `/api/conversation/get_user_role_conversations`
- **方法**: `POST`
- **认证**: 需要JWT令牌
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| role_id | string | 是 | AI角色ID |

- **请求示例**:

```json
{
  "role_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

- **成功响应**:

```json
{
  "code": 200,
  "message": "查询成功",
  "data": [
    {
      "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
      "role_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "550e8400-e29b-41d4-a716-446655440003",
      "title": "关于Python的讨论",
      "last_message": "这是最后一条消息",
      "last_message_time": "2023-05-01T13:00:00Z",
      "created_at": "2023-05-01T12:00:00Z",
      "voice_id": "550e8400-e29b-41d4-a716-446655440001",
      "speech_rate": 12,
      "pitch_rate": 10
    },
    // 更多会话...
  ]
}
```

- **错误响应**:

```json
{
  "code": 400,
  "message": "缺少必要参数：角色ID"
}
```

```json
{
  "code": 500,
  "message": "服务器错误: ..."
}
```

### 3. 更新会话

更新会话信息，如标题、语音设置等。

- **URL**: `/api/conversation/update_conversation`
- **方法**: `POST`
- **认证**: 需要JWT令牌
- **请求参数**:

| 参数名 | 类型 | 必填 | 说明 |
|-------|------|------|------|
| conversation_id | string | 是 | 会话ID |
| title | string | 否 | 会话标题 |
| voice_id | string | 否 | 语音ID |
| speech_rate | integer | 否 | 语速，范围5-20 |
| pitch_rate | integer | 否 | 音调，范围5-20 |

- **请求示例**:

```json
{
  "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
  "title": "更新后的标题",
  "voice_id": "550e8400-e29b-41d4-a716-446655440001",
  "speech_rate": 15,
  "pitch_rate": 8
}
```

- **成功响应**:

```json
{
  "code": 200,
  "message": "会话更新成功",
  "data": {
    "conversation_id": "550e8400-e29b-41d4-a716-446655440002",
    "role_id": "550e8400-e29b-41d4-a716-446655440000",
    "user_id": "550e8400-e29b-41d4-a716-446655440003",
    "title": "更新后的标题",
    "last_message": "这是最后一条消息",
    "last_message_time": "2023-05-01T13:00:00Z",
    "created_at": "2023-05-01T12:00:00Z",
    "voice_id": "550e8400-e29b-41d4-a716-446655440001",
    "speech_rate": 15,
    "pitch_rate": 8
  }
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
  "message": "无权修改此会话"
}
```

```json
{
  "code": 500,
  "message": "服务器错误: ..."
}
```

### 4. 删除会话

删除指定会话及其所有消息。

- **URL**: `/api/conversation/delete_conversation`
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
  "message": "会话及其消息已成功删除"
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
  "message": "无权删除此会话"
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