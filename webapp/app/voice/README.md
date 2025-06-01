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

# 音色管理模块 API 文档

本模块提供音色的创建、获取、管理等功能。所有接口都需要JWT验证。

## 环境配置

在使用音色创建功能前，需要设置以下环境变量：

```bash
export DASHSCOPE_API_KEY="your_dashscope_api_key"
```

## 接口列表

### 1. 创建新音色

通过上传的音频文件创建新的音色，使用阿里云DashScope进行音色复刻。

- **URL**: `/api/voice/create_voice`
- **方法**: POST
- **认证**: 需要JWT令牌
- **请求参数**:
  - `audio_file_id` (字符串): 音频文件ID（通过文件上传API获得）
  - `voice_name` (字符串): 音色名称
  - `voice_gender` (字符串): 音色性别，可选值：'male', 'female', 'other'
  - `voice_description` (字符串): 音色描述
  - `is_public` (布尔值, 可选): 是否公开，默认为false

**请求示例**:
```json
{
  "audio_file_id": "550e8400-e29b-41d4-a716-446655440000",
  "voice_name": "我的音色",
  "voice_gender": "female",
  "voice_description": "这是一个温柔的女声音色",
  "is_public": false
}
```

**返回参数**:
- `code` (整数): 状态码
- `message` (字符串): 返回信息
- `voice` (对象): 创建的音色信息
  - `voice_id` (字符串): 音色ID
  - `voice_name` (字符串): 音色名称
  - `voice_audition_url` (字符串): 试听音频文件ID
  - `created_at` (字符串): 创建时间
  - `created_by_user_id` (字符串): 创建者用户ID
  - `is_public` (布尔值): 是否公开
  - `call_name` (字符串): DashScope音色ID
  - `voice_gender` (字符串): 音色性别
  - `voice_description` (字符串): 音色描述
- `dashscope_voice_id` (字符串): DashScope返回的音色ID
- `error_info` (字符串, 可选): 错误信息

**返回示例**:
- 成功:
  ```json
  {
    "code": 200,
    "message": "create voice success",
    "voice": {
      "voice_id": "550e8400-e29b-41d4-a716-446655440000",
      "voice_name": "我的音色",
      "voice_audition_url": "661f9511-f3ac-52e5-b827-557766551111",
      "created_at": "2023-04-01T12:00:00Z",
      "created_by_user_id": "123e4567-e89b-12d3-a456-426614174000",
      "is_public": false,
      "call_name": "voice_my_voice_12345678",
      "voice_gender": "female",
      "voice_description": "这是一个温柔的女声音色"
    },
    "dashscope_voice_id": "voice_my_voice_12345678"
  }
  ```
- 失败:
  ```json
  {
    "code": 400,
    "message": "Missing fields: audio_file_id"
  }
  ```

**创建流程说明**:
1. 验证用户提供的音频文件ID是否存在且有权限访问
2. 构建音频文件下载URL（格式：`baseurl/api/temfile/download/<audio_file_id>`）
3. 调用DashScope API创建音色复刻
4. 使用复刻的音色生成试听音频（"今天天气怎么样？"）
5. 将试听音频上传到文件系统
6. 保存音色记录到数据库

**注意事项**:
- 音频文件必须是有效的音频格式（mp3, wav, ogg, aac, m4a, flac）
- 每个阿里云主账号最多可复刻1000个音色
- 避免频繁调用创建接口，每次调用都会创建新音色
- 试听音频会自动设置为私有文件

### 2. 获取音色列表

获取音色列表，支持分页、筛选等功能。

- **URL**: `/api/voice/get_voices`
- **方法**: POST
- **认证**: 需要JWT令牌
- **请求参数**:
  - `key_word` (字符串, 可选): 搜索关键词
  - `page` (整数, 可选): 页码，默认为1
  - `page_size` (整数, 可选): 每页数量，默认为10
  - `gender` (字符串, 可选): 性别筛选，可选值：'all', 'male', 'female', 'other'，默认为'all'
  - `created_by_current_user` (布尔值, 可选): 是否只显示当前用户创建的音色，默认为false

**请求示例**:
```json
{
  "key_word": "温柔",
  "page": 1,
  "page_size": 20,
  "gender": "female",
  "created_by_current_user": false
}
```

**返回参数**:
- `code` (整数): 状态码
- `message` (字符串): 返回信息
- `has_next` (布尔值): 是否有下一页
- `voices` (数组): 音色列表
  - `voice_id` (字符串): 音色ID
  - `voice_name` (字符串): 音色名称
  - `voice_gender` (字符串): 音色性别
  - `voice_audition_url` (字符串): 试听音频文件ID
  - `created_by_username` (字符串): 创建者用户名
  - `created_by_user_id` (字符串): 创建者用户ID
  - `voice_description` (字符串): 音色描述
  - `created_at` (字符串): 创建时间
  - `is_public` (布尔值): 是否公开
  - `is_created_by_current_user` (布尔值): 是否为当前用户创建

### 3. 获取我的音色列表

获取当前用户创建的所有音色。

- **URL**: `/api/voice/my_voices`
- **方法**: GET
- **认证**: 需要JWT令牌

**返回参数**:
- `code` (整数): 状态码
- `message` (字符串): 返回信息
- `voices` (数组): 音色列表（格式同上）

### 4. 验证音色

验证指定音色是否存在且当前用户是否有权限访问。

- **URL**: `/api/voice/verify_voice`
- **方法**: POST
- **认证**: 需要JWT令牌
- **请求参数**:
  - `voice_id` (字符串): 音色ID

**请求示例**:
```json
{
  "voice_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

**返回参数**:
- `code` (整数): 状态码
- `message` (字符串): 返回信息
- `voice` (对象): 音色详细信息
- `can_access` (布尔值): 是否可以访问

## 使用流程示例

### 创建新音色的完整流程

1. **上传音频文件**
   ```bash
   curl -X POST 'http://your-domain.com/api/file/upload' \
     -H 'Authorization: Bearer your_jwt_token' \
     -F 'file=@voice_sample.mp3' \
     -F 'is_public=false' \
     -F 'description=音色训练样本'
   ```

2. **创建音色**
   ```bash
   curl -X POST 'http://your-domain.com/api/voice/create_voice' \
     -H 'Authorization: Bearer your_jwt_token' \
     -H 'Content-Type: application/json' \
     -d '{
       "audio_file_id": "550e8400-e29b-41d4-a716-446655440000",
       "voice_name": "我的音色",
       "voice_gender": "female",
       "voice_description": "温柔的女声",
       "is_public": false
     }'
   ```

3. **获取试听音频**
   ```bash
   curl -X GET 'http://your-domain.com/api/file/download/661f9511-f3ac-52e5-b827-557766551111' \
     -H 'Authorization: Bearer your_jwt_token' \
     --output audition.mp3
   ```

## 错误码说明

- `200`: 成功
- `400`: 请求参数错误
- `401`: 未授权（JWT令牌无效）
- `403`: 权限不足
- `404`: 资源不存在
- `500`: 服务器内部错误

## 依赖说明

本模块依赖以下外部服务和库：
- 阿里云DashScope API（音色复刻服务）
- 文件上传模块（存储音频文件）
- JWT认证模块（用户身份验证）

确保在部署前正确配置相关环境变量和依赖。