# AI角色API接口文档

## 概述

本文档描述了AI角色相关的API接口，包括创建、获取、更新和删除AI角色的功能。所有接口都需要JWT认证。

## 接口列表

### 1. 获取AI角色列表

**接口路径**：`/ai_role/get_roles`

**请求方法**：POST

**接口描述**：获取AI角色列表，支持分页、关键词搜索和筛选

**请求参数**：

```json
{
  "key_word": "可选，搜索关键词",
  "page": 1,                    // 可选，默认为1
  "page_size": 10,              // 可选，默认为10
  "gender": "all",              // 可选，性别筛选，可选值：all, male, female, other
  "created_by_current_user": false  // 可选，是否只看自己创建的角色
}
```

**响应结果**：

```json
{
  "code": 200,
  "message": "get roles success",
  "has_next": false,            // 是否有下一页
  "roles": [
    {
      "role_id": "uuid字符串",
      "name": "角色名称",
      "gender": "male/female/other",
      "age": 25,
      "personality": "角色性格描述",
      "avatar_url": "头像文件UUID字符串",
      "voice_name": "语音名称",
      "voice_id": "语音UUID字符串",
      "response_language": "chinese/english",
      "image_urls": ["图片UUID字符串列表"],
      "created_at": "2023-01-01T00:00:00Z",
      "role_color": 16711680,
      "created_by_username": "创建者用户名",
      "created_by_user_id": "创建者UUID字符串",
      "is_public": false,
      "used_num": 0,
      "is_created_by_current_user": true,
      "has_relation": true,                // 当前用户是否与该角色建立了关系
      "relation_id": "关系UUID字符串"       // 如果有关系，则返回关系ID
    }
  ]
}
```

### 2. 获取AI角色详情

**接口路径**：`/ai_role/get_role_detail`

**请求方法**：POST

**接口描述**：获取单个AI角色的详细信息

**请求参数**：

```json
{
  "role_id": "必填，角色UUID字符串"
}
```

**响应结果**：

```json
{
  "code": 200,
  "message": "get role detail success",
  "role": {
    "role_id": "uuid字符串",
    "name": "角色名称",
    "gender": "male/female/other",
    "age": 25,
    "personality": "角色性格描述",
    "avatar_url": "头像文件UUID字符串",
    "voice_name": "语音名称",
    "voice_id": "语音UUID字符串",
    "response_language": "chinese/english",
    "image_urls": ["图片UUID字符串列表"],
    "created_at": "2023-01-01T00:00:00Z",
    "role_color": 16711680,
    "created_by_username": "创建者用户名",
    "created_by_user_id": "创建者UUID字符串",
    "is_public": false,
    "used_num": 0,
    "is_created_by_current_user": true
  }
}
```

### 3. 创建AI角色

**接口路径**：`/ai_role/create_role`

**请求方法**：POST

**接口描述**：创建新的AI角色

**请求参数**：

```json
{
  "name": "必填，角色名称",
  "gender": "必填，性别，可选值：male, female, other",
  "age": 25,                    // 可选，年龄
  "personality": "必填，角色性格描述",
  "avatar_url": "必填，头像文件UUID字符串",
  "voice_name": "可选，语音名称",
  "voice_id": "可选，语音UUID字符串",
  "response_language": "必填，回复语言，可选值：chinese, english",
  "image_urls": ["可选，图片UUID字符串列表"],
  "role_color": 16711680,       // 可选，角色颜色
  "is_public": false            // 可选，是否公开，默认为false
}
```

**响应结果**：

```json
{
  "code": 200,
  "message": "create role success",
  "role": {
    "role_id": "uuid字符串",
    "name": "角色名称",
    "gender": "male/female/other",
    "age": 25,
    "personality": "角色性格描述",
    "avatar_url": "头像文件UUID字符串",
    "voice_name": "语音名称",
    "voice_id": "语音UUID字符串",
    "response_language": "chinese/english",
    "image_urls": ["图片UUID字符串列表"],
    "created_at": "2023-01-01T00:00:00Z",
    "role_color": 16711680,
    "created_by_user_id": "创建者UUID字符串",
    "is_public": false,
    "used_num": 0
  }
}
```

### 4. 更新AI角色

**接口路径**：`/ai_role/update_role`

**请求方法**：POST

**接口描述**：更新已有的AI角色信息

**请求参数**：

```json
{
  "role_id": "必填，角色UUID字符串",
  "name": "可选，角色名称",
  "gender": "可选，性别，可选值：male, female, other",
  "age": 25,                    // 可选，年龄
  "personality": "可选，角色性格描述",
  "avatar_url": "可选，头像文件UUID字符串",
  "voice_name": "可选，语音名称",
  "voice_id": "可选，语音UUID字符串",
  "response_language": "可选，回复语言，可选值：chinese, english",
  "image_urls": ["可选，图片UUID字符串列表"],
  "role_color": 16711680,       // 可选，角色颜色
  "is_public": false            // 可选，是否公开
}
```

**响应结果**：

```json
{
  "code": 200,
  "message": "update role success",
  "role": {
    "role_id": "uuid字符串",
    "name": "角色名称",
    "gender": "male/female/other",
    "age": 25,
    "personality": "角色性格描述",
    "avatar_url": "头像文件UUID字符串",
    "voice_name": "语音名称",
    "voice_id": "语音UUID字符串",
    "response_language": "chinese/english",
    "image_urls": ["图片UUID字符串列表"],
    "created_at": "2023-01-01T00:00:00Z",
    "role_color": 16711680,
    "created_by_user_id": "创建者UUID字符串",
    "is_public": false,
    "used_num": 0
  }
}
```

### 5. 删除AI角色

**接口路径**：`/ai_role/delete_role`

**请求方法**：POST

**接口描述**：删除指定的AI角色

**请求参数**：

```json
{
  "role_id": "必填，角色UUID字符串"
}
```

**响应结果**：

```json
{
  "code": 200,
  "message": "delete role success"
}
```

### 6. 获取用户的所有AI角色

**接口路径**：`/ai_role/get_user_roles`

**请求方法**：POST

**接口描述**：获取当前用户关联的所有AI角色信息

**请求参数**：无（使用JWT中的用户ID）

**响应结果**：

```json
{
  "code": 200,
  "message": "get user roles success",
  "roles": [
    {
      "role_id": "uuid字符串",
      "name": "角色名称",
      "gender": "male/female/other",
      "age": 25,
      "personality": "角色性格描述",
      "avatar_url": "头像文件UUID字符串",
      "voice_name": "语音名称",
      "voice_id": "语音UUID字符串",
      "response_language": "chinese/english",
      "image_urls": ["图片UUID字符串列表"],
      "created_at": "2023-01-01T00:00:00Z",
      "role_color": 16711680,
      "created_by_username": "创建者用户名",
      "created_by_user_id": "创建者UUID字符串",
      "is_public": false,
      "used_num": 0,
      "is_created_by_current_user": true,
      "relation_id": "关系UUID字符串"
    }
  ]
}
```

### 7. 添加用户角色关系

**接口路径**：`/ai_role/add_user_role_relation`

**请求方法**：POST

**接口描述**：为当前用户添加AI角色关系

**请求参数**：

```json
{
  "role_id": "必填，角色UUID字符串"
}
```

**响应结果**：

```json
{
  "code": 200,
  "message": "add user role relation success",
  "relation": {
    "id": "关系UUID字符串",
    "user_id": "用户UUID字符串",
    "role_id": "角色UUID字符串",
    "created_at": "2023-01-01T00:00:00Z"
  }
}
```

### 8. 删除用户角色关系

**接口路径**：`/ai_role/delete_user_role_relation`

**请求方法**：POST

**接口描述**：删除用户角色关系

**请求参数**：

```json
{
  "relation_id": "可选，关系UUID字符串",
  "role_id": "可选，角色UUID字符串"
}
```

**注意**：`relation_id` 和 `role_id` 至少需要提供一个

**响应结果**：

```json
{
  "code": 200,
  "message": "delete user role relation success",
  "relation": {
    "id": "关系UUID字符串",
    "user_id": "用户UUID字符串",
    "role_id": "角色UUID字符串",
    "created_at": "2023-01-01T00:00:00Z"
  }
}
```

### 9. 获取用户创建的所有AI角色

**接口路径**：`/ai_role/get_created_roles`

**请求方法**：POST

**接口描述**：获取当前用户创建的所有AI角色信息

**请求参数**：无（使用JWT中的用户ID）

**响应结果**：

```json
{
  "code": 200,
  "message": "get created roles success",
  "roles": [
    {
      "role_id": "uuid字符串",
      "name": "角色名称",
      "gender": "male/female/other",
      "age": 25,
      "personality": "角色性格描述",
      "avatar_url": "头像文件UUID字符串",
      "voice_name": "语音名称",
      "voice_id": "语音UUID字符串",
      "response_language": "chinese/english",
      "image_urls": ["图片UUID字符串列表"],
      "created_at": "2023-01-01T00:00:00Z",
      "role_color": 16711680,
      "created_by_username": "创建者用户名",
      "created_by_user_id": "创建者UUID字符串",
      "is_public": false,
      "used_num": 0,
      "is_created_by_current_user": true
    }
  ]
}
```

## 错误码说明

- 200: 成功
- 400: 请求参数错误
- 401: 未授权（JWT无效）
- 403: 权限不足（非角色创建者）
- 404: 资源不存在
- 500: 服务器内部错误