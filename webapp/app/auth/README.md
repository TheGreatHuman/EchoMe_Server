## Auth 模块接口文档

### 1. 发送验证码
- **URL**: `/auth/send_captcha`
- **方法**: POST
- **请求参数**:
  - `identifier` (string): 手机号或邮箱
  - `type` (string): 标识符类型，取值 `phone` 或 `email`
- **请求示例**:
```json
{
  "identifier": "13812345678",
  "type": "phone"
}
```
- **返回参数**:
  - `code` (int): 状态码
  - `message` (string): 返回信息
  - `is_first_use` (bool, 可选): 是否首次使用（首次注册时返回）
  - `captcha` (string): 验证码（开发环境返回）
  - `error_info` (string, 可选): 错误信息
- **返回示例**:
  - 首次使用:
    ```json
    {
      "code": 200,
      "message": "phone first use",
      "is_first_use": true,
      "captcha": "123456"
    }
    ```
  - 非首次:
    ```json
    {
      "code": 204,
      "captcha": "654321"
    }
    ```
  - 参数缺失/格式错误:
    ```json
    {
      "code": 400,
      "message": "send login code fail",
      "error_info": "Missing required parameters"
    }
    ```

### 2. 用户注册
- **URL**: `/auth/register`
- **方法**: POST
- **请求参数**:
  - `username` (string): 用户名
  - `identifier` (string): 手机号或邮箱
  - `type` (string): `phone` 或 `email`
  - `code` (string): 验证码
  - `password` (string): 密码
- **请求示例**:
```json
{
  "username": "testuser",
  "identifier": "test@example.com",
  "type": "email",
  "code": "123456",
  "password": "password123"
}
```
- **返回参数**:
  - `code` (int): 状态码
  - `message` (string): 返回信息
  - `user_id` (int, 可选): 用户ID（注册成功时返回）
  - `error_info` (string, 可选): 错误信息
- **返回示例**:
  - 注册成功:
    ```json
    {
      "code": 201,
      "message": "create user success",
      "user_id": 1
    }
    ```
  - 参数缺失:
    ```json
    {
      "code": 400,
      "message": "create user fail",
      "error_info": "Missing required parameters"
    }
    ```
  - 验证码错误:
    ```json
    {
      "code": 400,
      "message": "create user fail",
      "error_info": "Invalid or expired verification code"
    }
    ```
  - 用户已存在:
    ```json
    {
      "code": 400,
      "message": "create user fail",
      "error_info": "User with this email already exists"
    }
    ```

### 3. 用户登录
- **URL**: `/auth/login`
- **方法**: POST
- **请求参数**:
  - `identifier` (string): 手机号或邮箱
  - `type` (string): `phone` 或 `email`
  - `password` (string, 可选): 密码（密码登录时必填）
  - `code` (string, 可选): 验证码（验证码登录时必填）
- **请求示例**:
```json
{
  "identifier": "13812345678",
  "type": "phone",
  "password": "password123"
}
```
- **返回参数**:
  - `code` (int): 状态码
  - `message` (string): 返回信息
  - `access_token` (string, 可选): 访问令牌
  - `refresh_token` (string, 可选): 刷新令牌
  - `user_id` (int, 可选): 用户ID
  - `error_info` (string, 可选): 错误信息
- **返回示例**:
  - 登录成功:
    ```json
    {
      "code": 200,
      "message": "user login success",
      "access_token": "...",
      "refresh_token": "...",
      "user_id": 1
    }
    ```
  - 用户不存在:
    ```json
    {
      "code": 401,
      "message": "user login fail",
      "error_info": "User not found"
    }
    ```
  - 密码错误:
    ```json
    {
      "code": 401,
      "message": "user login fail",
      "error_info": "Invalid password"
    }
    ```
  - 验证码错误:
    ```json
    {
      "code": 401,
      "message": "user login fail",
      "error_info": "Invalid or expired verification code"
    }
    ```
  - 参数缺失:
    ```json
    {
      "code": 401,
      "message": "user login fail",
      "error_info": "Missing required parameters"
    }
    ```

### 4. 刷新令牌
- **URL**: `/auth/refresh`
- **方法**: POST
- **请求头**: 需携带有效的 `refresh_token`（JWT）
- **请求参数**: 无
- **返回参数**:
  - `code` (int): 状态码
  - `message` (string): 返回信息
  - `access_token` (string): 新的访问令牌
  - `refresh_token` (string): 新的刷新令牌
  - `error_info` (string, 可选): 错误信息
- **返回示例**:
  - 刷新成功:
    ```json
    {
      "code": 200,
      "message": "token refreshed",
      "access_token": "...",
      "refresh_token": "..."
    }
    ```
  - refresh_token 无效:
    ```json
    {
      "code": 401,
      "message": "Invalid refresh token",
      "error_info": "..."
    }
    ```