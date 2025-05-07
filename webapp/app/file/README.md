# 文件管理模块 API 文档

本模块提供图片文件的上传、下载、管理等功能。所有接口都需要JWT验证。

## 1. 上传文件

- **URL**: `/api/file/upload`
- **方法**: POST
- **认证**: 需要JWT令牌
- **请求参数**:
  - `file` (文件): 要上传的文件（支持图片和音频）
  - `is_public` (布尔值, 可选): 是否为私有文件，默认为true
  - `description` (字符串, 可选): 文件描述
- **支持的文件类型**: 
  - 图片: png, jpg, jpeg, gif, webp
  - 音频: mp3, wav, ogg, aac, m4a, flac
- **请求示例**:
  ```
  // 使用FormData上传
  const formData = new FormData();
  formData.append('file', fileObject);
  formData.append('is_public', 'false');
  formData.append('description', '这是一张测试图片');
  ```
- **返回参数**:
  - `code` (整数): 状态码
  - `message` (字符串): 返回信息
  - `file_id` (字符串): 文件ID
  - `file_name` (字符串): 文件名
  - `file_path` (字符串): 文件下载路径
  - `file_size` (整数): 文件大小(字节)
  - `file_type` (字符串): 文件MIME类型
  - `is_public` (布尔值): 是否为私有文件
  - `created_at` (字符串): 创建时间
  - `error_info` (字符串, 可选): 错误信息
- **返回示例**:
  - 成功:
    ```json
    {
      "code": 201,
      "message": "upload file success",
      "file_id": "550e8400-e29b-41d4-a716-446655440000",
      "file_name": "example.jpg",
      "file_path": "/api/file/download/550e8400-e29b-41d4-a716-446655440000",
      "file_size": 24680,
      "file_type": "image/jpeg",
      "is_public": false,
      "created_at": "2023-04-01T12:00:00Z"
    }
    ```
  - 失败:
    ```json
    {
      "code": 400,
      "message": "upload file fail",
      "error_info": "File type not allowed. Allowed types: png, jpg, jpeg, gif, webp"
    }
    ```

## 2. 下载文件

- **URL**: `/api/file/download/{file_id}`
- **方法**: GET
- **认证**: 需要JWT令牌
- **URL参数**:
  - `file_id` (字符串): 文件ID
- **权限**:
  - 公开文件: 任何有效JWT用户可下载
  - 私有文件: 仅文件所有者可下载
- **返回**: 文件内容或错误信息
- **错误返回示例**:
  ```json
  {
    "code": 403,
    "message": "download file fail",
    "error_info": "You do not have permission to access this file"
  }
  ```

## 3. 获取文件列表

- **URL**: `/api/file/list`
- **方法**: POST
- **认证**: 需要JWT令牌
- **请求参数**:
  - `page` (整数, 可选): 页码，默认为1
  - `page_size` (整数, 可选): 每页数量，默认为10
  - `only_mine` (布尔值, 可选): 是否只显示当前用户的文件，默认为false
- **请求示例**:
  ```json
  {
    "page": 1,
    "page_size": 20,
    "only_mine": true
  }
  ```
- **返回参数**:
  - `code` (整数): 状态码
  - `message` (字符串): 返回信息
  - `has_next` (布尔值): 是否有下一页
  - `total_items` (整数): 总文件数
  - `total_pages` (整数): 总页数
  - `current_page` (整数): 当前页码
  - `files` (数组): 文件列表
    - `file_id` (字符串): 文件ID
    - `file_name` (字符串): 文件名
    - `file_path` (字符串): 文件下载路径
    - `file_size` (整数): 文件大小(字节)
    - `file_type` (字符串): 文件MIME类型
    - `created_at` (字符串): 创建时间
    - `created_by_username` (字符串): 创建者用户名
    - `created_by_user_id` (字符串): 创建者用户ID
    - `is_public` (布尔值): 是否为私有文件
    - `description` (字符串): 文件描述
    - `is_owner` (布尔值): 当前用户是否为文件所有者
  - `error_info` (字符串, 可选): 错误信息
- **返回示例**:
  ```json
  {
    "code": 200,
    "message": "get files success",
    "has_next": false,
    "total_items": 1,
    "total_pages": 1,
    "current_page": 1,
    "files": [
      {
        "file_id": "550e8400-e29b-41d4-a716-446655440000",
        "file_name": "example.jpg",
        "file_path": "/api/file/download/550e8400-e29b-41d4-a716-446655440000",
        "file_size": 24680,
        "file_type": "image/jpeg",
        "created_at": "2023-04-01T12:00:00Z",
        "created_by_username": "user1",
        "created_by_user_id": "123e4567-e89b-12d3-a456-426614174000",
        "is_public": false,
        "description": "这是一张测试图片",
        "is_owner": true
      }
    ]
  }
  ```

## 4. 删除文件

- **URL**: `/api/file/delete/{file_id}`
- **方法**: DELETE
- **认证**: 需要JWT令牌
- **URL参数**:
  - `file_id` (字符串): 文件ID
- **权限**: 仅文件所有者可删除
- **返回参数**:
  - `code` (整数): 状态码
  - `message` (字符串): 返回信息
  - `error_info` (字符串, 可选): 错误信息
- **返回示例**:
  - 成功:
    ```json
    {
      "code": 200,
      "message": "delete file success"
    }
    ```
  - 失败:
    ```json
    {
      "code": 403,
      "message": "delete file fail",
      "error_info": "You do not have permission to delete this file"
    }
    ```

## 5. 更新文件信息

- **URL**: `/api/file/update/{file_id}`
- **方法**: PUT
- **认证**: 需要JWT令牌
- **URL参数**:
  - `file_id` (字符串): 文件ID
- **请求参数**:
  - `file_name` (字符串, 可选): 新文件名
  - `is_public` (布尔值, 可选): 是否为私有文件
  - `description` (字符串, 可选): 文件描述
- **权限**: 仅文件所有者可更新
- **请求示例**:
  ```json
  {
    "file_name": "新文件名.jpg",
    "is_private": false,
    "description": "更新后的描述"
  }
  ```
- **返回参数**:
  - `code` (整数): 状态码
  - `message` (字符串): 返回信息
  - `file` (对象): 更新后的文件信息
  - `error_info` (字符串, 可选): 错误信息
- **返回示例**:
  ```json
  {
    "code": 200,
    "message": "update file success",
    "file": {
      "file_id": "550e8400-e29b-41d4-a716-446655440000",
      "file_name": "新文件名.jpg",
      "file_path": "550e8400-e29b-41d4-a716-446655440000.jpg",
      "file_size": 24680,
      "file_type": "image/jpeg",
      "created_at": "2023-04-01T12:00:00Z",
      "created_by_user_id": "123e4567-e89b-12d3-a456-426614174000",
      "is_public": false,
      "description": "更新后的描述"
    }
  }
  ```

## 6. 更新文件内容

- **URL**: `/api/file/update_content/{file_id}`
- **方法**: POST
- **认证**: 需要JWT令牌
- **URL参数**:
  - `file_id` (字符串): 文件ID
- **请求参数**:
  - `file` (文件): 要上传的新文件内容
- **权限**: 仅文件所有者可更新
- **请求示例**:
  ```
  // 使用FormData上传
  const formData = new FormData();
  formData.append('file', newFileObject);
  ```
- **返回参数**:
  - `code` (整数): 状态码
  - `message` (字符串): 返回信息
  - `file` (对象): 更新后的文件信息
  - `error_info` (字符串, 可选): 错误信息
- **返回示例**:
  - 成功:
    ```json
    {
      "code": 200,
      "message": "update file content success",
      "file": {
        "file_id": "550e8400-e29b-41d4-a716-446655440000",
        "file_name": "example.jpg",
        "file_path": "/api/file/download/550e8400-e29b-41d4-a716-446655440000",
        "file_size": 35790,
        "file_type": "image/jpeg",
        "created_at": "2023-04-01T12:00:00Z",
        "created_by_user_id": "123e4567-e89b-12d3-a456-426614174000",
        "is_public": false,
        "description": "文件描述"
      }
    }
    ```
  - 失败:
    ```json
    {
      "code": 400,
      "message": "update file content fail",
      "error_info": "File type not allowed or does not match original file type"
    }
    ```