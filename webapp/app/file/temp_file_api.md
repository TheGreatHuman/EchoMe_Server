# 临时文件上传下载接口文档

## 概述

临时文件接口用于处理需要短期存储的文件，如聊天过程中的临时图片、音频或视频文件。这些文件不会永久保存，系统会在指定时间后（默认24小时）自动清理。

## 基本信息
- **BaseURL**: `localhost:3000`
- **基础URL**: `/api/tempfile`
- **权限要求**: 无需JWT鉴权
- **支持的文件类型**:
  - 图片: png, jpg, jpeg, gif, webp
  - 音频: mp3, wav, ogg, aac, m4a, flac
  - 视频: mp4, avi, mov, wmv, flv, mpeg, mpg, m4v, webm, mkv

## 接口列表

### 1. 上传临时文件

上传文件并获取临时ID，该ID可用于后续下载或删除操作。

- **URL**: `/api/tempfile/upload`
- **方法**: `POST`
- **Content-Type**: `multipart/form-data`
- **参数**:
  - `file`: 要上传的文件

**请求示例**:
```bash
curl -X POST 'http://your-domain.com/api/tempfile/upload' \
  -F 'file=@/path/to/your/file.jpg'
```

**成功响应** (200 OK):
```json
{
  "success": true,
  "file_id": "550e8400-e29b-41d4-a716-446655440000",
  "file_type": "image",
  "original_name": "example.jpg"
}
```

**错误响应** (400 Bad Request):
```json
{
  "success": false,
  "message": "不允许的文件类型"
}
```

### 2. 下载临时文件

通过文件ID下载之前上传的临时文件。

- **URL**: `/api/tempfile/download/<file_id>`
- **方法**: `GET`
- **参数**:
  - `file_id`: 上传时获取的文件ID

**请求示例**:
```bash
curl -X GET 'http://your-domain.com/api/tempfile/download/550e8400-e29b-41d4-a716-446655440000' --output downloaded_file.jpg
```

**成功响应**: 
文件内容将直接返回，并设置适当的Content-Type和Content-Disposition头。

**错误响应** (404 Not Found):
```json
{
  "success": false,
  "message": "文件不存在或已过期"
}
```

### 3. 删除临时文件

删除指定ID的临时文件。

- **URL**: `/api/tempfile/delete/<file_id>`
- **方法**: `DELETE`
- **参数**:
  - `file_id`: 上传时获取的文件ID

**请求示例**:
```bash
curl -X DELETE 'http://your-domain.com/api/tempfile/delete/550e8400-e29b-41d4-a716-446655440000'
```

**成功响应** (200 OK):
```json
{
  "success": true,
  "message": "文件删除成功"
}
```

**错误响应** (404 Not Found):
```json
{
  "success": false,
  "message": "文件不存在或已过期"
}
```

### 4. 批量删除临时文件

一次删除多个临时文件。

- **URL**: `/api/tempfile/batch-delete`
- **方法**: `POST`
- **Content-Type**: `application/json`
- **请求体**:
  ```json
  {
    "file_ids": ["id1", "id2", "id3"]
  }
  ```

**请求示例**:
```bash
curl -X POST 'http://your-domain.com/api/tempfile/batch-delete' \
  -H 'Content-Type: application/json' \
  -d '{"file_ids": ["550e8400-e29b-41d4-a716-446655440000", "661f9511-f3ac-52e5-b827-557766551111"]}'
```

**成功响应** (200 OK):
```json
{
  "success": true,
  "message": "成功删除2个文件",
  "deleted_count": 2
}
```

**错误响应** (400 Bad Request):
```json
{
  "success": false,
  "message": "请求格式错误"
}
```

## 使用注意事项

1. **文件有效期**：所有上传的临时文件默认有效期为24小时，超过有效期后将被自动清理，无法再次访问。

2. **文件大小限制**：根据服务器配置，可能存在上传文件大小的限制，建议控制上传文件的大小。

3. **文件类型**：只允许上传指定类型的文件，如果上传了不支持的文件类型，接口将返回错误。

4. **安全性**：虽然接口不需要鉴权，但建议在前端实现适当的权限控制，避免接口被滥用。

## 示例场景

### 在聊天应用中发送临时图片
1. 前端调用上传接口，获取图片的`file_id`
2. 将`file_id`嵌入到消息中发送给服务器
3. 接收方通过`file_id`调用下载接口获取并显示图片

### 语音消息处理
1. 录制语音后调用上传接口，获取音频文件的`file_id`
2. 将`file_id`与消息一起发送
3. 接收方根据`file_id`调用下载接口获取并播放音频 