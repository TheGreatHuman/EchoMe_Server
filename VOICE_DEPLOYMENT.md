# 音色创建功能部署说明

## 概述

本文档说明如何部署和使用新的音色创建功能，该功能集成了阿里云DashScope的音色复刻服务。

## 前置条件

### 1. 环境要求
- Python 3.8+
- MySQL 8.0+
- Redis 4.0+
- 阿里云DashScope API账号

### 2. 依赖安装

确保安装了所有必要的Python依赖：

```bash
pip install -r requirements.txt
```

新增的依赖包括：
- `dashscope` - 阿里云DashScope SDK

### 3. 环境变量配置

在系统环境变量或`.env`文件中设置：

```bash
# DashScope API密钥
export DASHSCOPE_API_KEY="your_dashscope_api_key_here"

# 其他现有环境变量...
export DATABASE_URL="mysql://user:password@localhost/database"
export JWT_SECRET_KEY="your_jwt_secret"
```

## 数据库配置

音色功能使用现有的数据库表结构，无需额外的数据库迁移。相关表包括：

- `voices` - 音色信息表
- `files` - 文件存储表
- `users` - 用户表

## 功能特性

### 1. 音色创建流程

1. **音频文件上传**：用户上传音频文件到文件系统
2. **URL构建**：构建音频文件下载URL（格式：`baseurl/api/temfile/download/<audio_file_id>`）
3. **DashScope音色复刻**：调用阿里云API创建音色
4. **试听音频生成**：使用复刻的音色生成试听音频
5. **文件存储**：将试听音频保存到文件系统
6. **数据库记录**：保存音色信息到数据库

### 2. 支持的音频格式

- MP3
- WAV
- OGG
- AAC
- M4A
- FLAC

### 3. 权限控制

- 只有文件所有者或公开文件可用于音色创建
- 音色可设置为公开或私有
- 试听音频自动设置为私有

## API接口

### 创建音色

```http
POST /api/voice/create_voice
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "audio_file_id": "550e8400-e29b-41d4-a716-446655440000",
  "voice_name": "我的音色",
  "voice_gender": "female",
  "voice_description": "温柔的女声",
  "is_public": false
}
```

### 获取音色列表

```http
POST /api/voice/get_voices
Authorization: Bearer <jwt_token>
Content-Type: application/json

{
  "page": 1,
  "page_size": 10,
  "gender": "all",
  "created_by_current_user": false
}
```

## 部署步骤

### 1. 代码部署

```bash
# 拉取最新代码
git pull origin main

# 安装依赖
pip install -r requirements.txt

# 设置环境变量
export DASHSCOPE_API_KEY="your_api_key"
```

### 2. 服务重启

```bash
# 重启Flask应用
sudo systemctl restart your_flask_app

# 或使用其他进程管理器
pm2 restart your_app
```

### 3. 验证部署

使用提供的测试脚本验证功能：

```bash
python test_voice_creation.py
```

## 监控和日志

### 1. 关键监控指标

- DashScope API调用成功率
- 音色创建耗时
- 文件上传成功率
- 数据库操作性能

### 2. 日志配置

建议在生产环境中配置详细的日志记录：

```python
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('voice_creation.log'),
        logging.StreamHandler()
    ]
)
```

## 故障排除

### 1. 常见问题

**问题：DashScope API调用失败**
- 检查API密钥是否正确
- 确认账户余额充足
- 检查网络连接

**问题：音频文件上传失败**
- 检查文件格式是否支持
- 确认文件大小在限制范围内
- 检查磁盘空间

**问题：试听音频生成失败**
- 检查DashScope音色是否创建成功
- 确认音色ID有效
- 检查文件上传权限

### 2. 错误码说明

- `400` - 请求参数错误
- `403` - 权限不足
- `404` - 资源不存在
- `500` - 服务器内部错误

## 性能优化

### 1. 缓存策略

- 音色列表缓存
- 文件元数据缓存
- DashScope响应缓存

### 2. 异步处理

考虑将音色创建过程改为异步处理：

```python
# 使用Celery或其他任务队列
@celery.task
def create_voice_async(user_id, audio_file_id, voice_data):
    # 异步处理音色创建
    pass
```

## 安全考虑

### 1. API密钥安全

- 使用环境变量存储API密钥
- 定期轮换密钥
- 限制API密钥权限

### 2. 文件安全

- 验证上传文件类型
- 限制文件大小
- 扫描恶意文件

### 3. 访问控制

- JWT令牌验证
- 用户权限检查
- 频率限制

## 扩展功能

### 1. 批量音色创建

支持批量上传音频文件并创建多个音色。

### 2. 音色质量评估

集成音色质量评估功能，为用户提供音色质量反馈。

### 3. 音色分享

允许用户分享自己创建的音色给其他用户。

## 维护建议

### 1. 定期备份

- 数据库定期备份
- 音频文件备份
- 配置文件备份

### 2. 监控告警

- API调用失败告警
- 磁盘空间告警
- 服务异常告警

### 3. 性能调优

- 定期分析慢查询
- 优化文件存储策略
- 调整缓存配置

## 联系支持

如遇到问题，请联系技术支持团队或查看相关文档：

- API文档：`webapp/app/voice/README.md`
- 错误日志：检查应用日志文件
- 监控面板：查看系统监控指标 