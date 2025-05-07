# 音色相关接口文档

## 1. 获取音色列表

- **接口地址**：`/api/voice/get_voices`
- **请求方式**：POST
- **请求头**：
  - `Content-Type: application/json`
  - `Authorization: Bearer <JWT Token>`

### 请求参数
| 参数名                 | 类型    | 是否必填 | 描述                                                         |
|------------------------|---------|----------|--------------------------------------------------------------|
| key_word               | string  | 否       | 音色名称关键词，模糊搜索                                     |
| page                   | int     | 否       | 页码，默认1                                                  |
| page_size              | int     | 否       | 每页数量，默认10                                             |
| gender                 | string  | 否       | 音色性别筛选，可选值："all"/"male"/"female"/"other"，默认"all" |
| created_by_current_user| boolean | 否       | 是否只查询当前用户创建的音色，默认false                      |

### 请求示例
```json
{
  "key_word": "女声",
  "page": 1,
  "page_size": 10
}
```

### 返回参数
| 参数名                | 类型    | 描述                         |
|-----------------------|---------|------------------------------|
| code                  | int     | 状态码                       |
| message               | string  | 返回信息                     |
| has_next              | bool    | 是否有下一页                 |
| voices                | array   | 音色列表                     |
| └─ voice_id           | string  | 音色ID（UUID字符串）         |
| └─ voice_name         | string  | 音色名称                     |
| └─ voice_gender       | string  | 音色性别                     |
| └─ voice_audition_url | string  | 音色试听URL                  |
| └─ created_by_username| string  | 创建者用户名                 |
| └─ created_by_user_id | string  | 创建者用户ID（UUID字符串）   |
| └─ voice_description  | string  | 音色描述                     |
| └─ created_at         | string  | 创建时间（ISO8601格式）      |
| └─ is_public          | bool    | 是否公开                     |
| └─ is_created_by_current_user          | bool  | 是否当前用户创建   |
| error_info            | string  | 错误信息（仅失败时返回）     |

### 成功返回示例（code=200）
```json
{
  "code": 200,
  "message": "get voice success",
  "has_next": true,
  "voices": [
    {
      "voice_id": "e7b8e2e2-1234-4c56-9abc-1234567890ab",
      "voice_name": "女声A",
      "voice_gender": "female",
      "voice_audition_url": "https://example.com/voiceA.mp3",
      "created_by_username": "user1",
      "created_by_user_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
      "voice_description": "温柔女声",
      "created_at": "2024-05-01T12:00:00Z",
      "is_public": true,
      "is_created_by_current_user": true
    }
  ]
}
```

### 未找到音色返回示例（code=404）
```json
{
  "code": 404,
  "message": "no voice found"
}
```

### 服务器错误返回示例（code=500）
```json
{
  "code": 500,
  "message": "get voice fail",
  "error_info": "详细错误信息"
}
```

### 说明
- 需要携带有效的JWT Token。
- 仅返回当前用户创建的音色和公开音色。
- 支持分页和关键词模糊搜索。

## 2. 创建音色

- **接口地址**：`/api/voice/create_voice`
- **请求方式**：POST
- **请求头**：
  - `Content-Type: application/json`
  - `Authorization: Bearer <JWT Token>`

### 请求参数
| 参数名            | 类型    | 是否必填 | 描述                                       |
|-------------------|---------|----------|--------------------------------------------|
| voice_name        | string  | 是       | 音色名称                                   |
| voice_url         | string  | 是       | 音色试听URL（UUID字符串）                  |
| call_name         | string  | 是       | 音色呼叫名称                               |
| voice_gender      | string  | 是       | 音色性别，可选值："male"/"female"/"other" |
| voice_description | string  | 是       | 音色描述                                   |
| is_public         | boolean | 否       | 是否公开，默认false                        |

### 请求示例
```json
{
  "voice_name": "女声A",
  "voice_url": "e7b8e2e2-1234-4c56-9abc-1234567890ab",
  "call_name": "小美",
  "voice_gender": "female",
  "voice_description": "温柔女声",
  "is_public": true
}
```

### 返回参数
| 参数名     | 类型   | 描述                     |
|------------|--------|---------------------------|
| code       | int    | 状态码                   |
| message    | string | 返回信息                 |
| voice      | object | 创建的音色信息           |
| error_info | string | 错误信息（仅失败时返回） |

### 成功返回示例（code=200）
```json
{
  "code": 200,
  "message": "create voice success",
  "voice": {
    "voice_id": "e7b8e2e2-1234-4c56-9abc-1234567890ab",
    "voice_name": "女声A",
    "voice_gender": "female",
    "voice_url": "e7b8e2e2-1234-4c56-9abc-1234567890ab",
    "call_name": "小美",
    "voice_description": "温柔女声",
    "created_at": "2024-05-01T12:00:00Z",
    "is_public": true,
    "created_by": "a1b2c3d4-5678-90ab-cdef-1234567890ab"
  }
}
```

### 参数错误返回示例（code=400）
```json
{
  "code": 400,
  "message": "Missing fields: voice_name, voice_url"
}
```

### 服务器错误返回示例（code=500）
```json
{
  "code": 500,
  "message": "create voice fail",
  "error_info": "详细错误信息"
}
```

### 说明
- 需要携带有效的JWT Token。
- 所有必填字段都必须提供。
- voice_gender必须是指定的三个值之一。

## 3. 验证音色

- **接口地址**：`/api/voice/verify_voice`
- **请求方式**：POST
- **请求头**：
  - `Content-Type: application/json`
  - `Authorization: Bearer <JWT Token>`

### 请求参数
| 参数名    | 类型   | 是否必填 | 描述                 |
|-----------|--------|----------|----------------------|
| voice_id  | string | 是       | 音色ID（UUID字符串） |

### 请求示例
```json
{
  "voice_id": "e7b8e2e2-1234-4c56-9abc-1234567890ab"
}
```

### 返回参数
| 参数名     | 类型    | 描述                     |
|------------|---------|---------------------------|
| code       | int     | 状态码                   |
| message    | string  | 返回信息                 |
| voice      | object  | 音色详细信息             |
| can_access | boolean | 是否可以访问该音色       |
| error_info | string  | 错误信息（仅失败时返回） |

### 成功返回示例（code=200）
```json
{
  "code": 200,
  "message": "voice verification success",
  "voice": {
    "voice_id": "e7b8e2e2-1234-4c56-9abc-1234567890ab",
    "voice_name": "女声A",
    "voice_gender": "female",
    "voice_url": "e7b8e2e2-1234-4c56-9abc-1234567890ab",
    "created_by_username": "user1",
    "created_by": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
    "voice_description": "温柔女声",
    "created_at": "2024-05-01T12:00:00Z",
    "is_public": true,
    "is_created_by_current_user": true
  },
  "can_access": true
}
```

### 参数错误返回示例（code=400）
```json
{
  "code": 400,
  "message": "Missing required field: voice_id"
}
```

### 未找到音色返回示例（code=404）
```json
{
  "code": 404,
  "message": "Voice not found"
}
```

### 权限错误返回示例（code=403）
```json
{
  "code": 403,
  "message": "Permission denied: voice is not public and you are not the creator"
}
```

### 服务器错误返回示例（code=500）
```json
{
  "code": 500,
  "message": "voice verification fail",
  "error_info": "详细错误信息"
}
```

### 说明
- 需要携带有效的JWT Token。
- 非公开音色只有创建者可以访问。
- 返回的音色信息包含是否为当前用户创建的标志。

## 4. 获取我的音色

- **接口地址**：`/api/voice/my_voices`
- **请求方式**：GET
- **请求头**：
  - `Authorization: Bearer <JWT Token>`

### 请求参数
无需请求参数，通过JWT Token自动获取当前用户ID。

### 返回参数
| 参数名                | 类型    | 描述                         |
|-----------------------|---------|------------------------------|
| code                  | int     | 状态码                       |
| message               | string  | 返回信息                     |
| voices                | array   | 音色列表                     |
| └─ voice_id           | string  | 音色ID（UUID字符串）         |
| └─ voice_name         | string  | 音色名称                     |
| └─ voice_gender       | string  | 音色性别                     |
| └─ voice_audition_url | string  | 音色试听URL                  |
| └─ created_by_username| string  | 创建者用户名                 |
| └─ created_by_user_id | string  | 创建者用户ID（UUID字符串）   |
| └─ voice_description  | string  | 音色描述                     |
| └─ created_at         | string  | 创建时间（ISO8601格式）      |
| └─ is_public          | bool    | 是否公开                     |
| └─ is_created_by_current_user | bool  | 是否当前用户创建（始终为true）|
| error_info            | string  | 错误信息（仅失败时返回）     |

### 成功返回示例（code=200）
```json
{
  "code": 200,
  "message": "get my voices success",
  "voices": [
    {
      "voice_id": "e7b8e2e2-1234-4c56-9abc-1234567890ab",
      "voice_name": "女声A",
      "voice_gender": "female",
      "voice_audition_url": "https://example.com/voiceA.mp3",
      "created_by_username": "user1",
      "created_by_user_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
      "voice_description": "温柔女声",
      "created_at": "2024-05-01T12:00:00Z",
      "is_public": true,
      "is_created_by_current_user": true
    }
  ]
}
```

### 未找到音色返回示例（code=200）
```json
{
  "code": 200,
  "message": "no voice found",
  "voices": []
}
```

### 服务器错误返回示例（code=500）
```json
{
  "code": 500,
  "message": "get my voices fail",
  "error_info": "详细错误信息"
}
```

### 说明
- 需要携带有效的JWT Token。
- 仅返回当前用户创建的所有音色，无论是否公开。
- 按创建时间降序排列（最新创建的排在前面）。