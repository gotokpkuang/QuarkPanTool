# QuarkPanTool API 使用文档

## 概述

QuarkPanTool API 提供了一套 REST API 接口，用于程序化操作夸克网盘。支持分享链接生成、文件转存、链接验证和文件列表查询等功能。

## 快速开始

### 1. 安装依赖

```bash
cd g:\pro\QuarkPanTool-main
pip install -r requirements.txt
```

### 2. 配置Cookie

API模式只能通过读取 `config/cookies.txt` 文件来登录。首先需要获取Cookie：

```bash
# 运行主程序
python quark.py

# 选择选项 6 (登录)
# 在弹出的浏览器中登录夸克账号
# 登录成功后Cookie会自动保存到 config/cookies.txt
```

### 3. 配置邮件通知（可选）

编辑 `config.py` 文件，配置Gmail邮件通知：

```python
EMAIL_CONFIG = {
    'sender_email': 'your_email@gmail.com',  # 你的Gmail地址
    'sender_password': 'your_app_password',   # Gmail应用专用密码
    'recipient_email': 'libertygm@gmail.com', # 接收通知的邮箱
    'enabled': True  # 启用邮件通知
}
```

**注意**: 需要使用Gmail应用专用密码，不是普通密码。获取方法：
1. 访问 https://myaccount.google.com/apppasswords
2. 创建新的应用专用密码
3. 将生成的密码填入 `sender_password`

### 4. 启动API服务

```bash
# 使用默认端口 13000
python quark_api.py --api

# 或指定自定义端口
python quark_api.py --api --port 8080
```

启动成功后会显示：

```
QuarkPanTool API Server
============================================================
监听地址: http://0.0.0.0:13000
健康检查: http://localhost:13000/api/health

可用接口:
  POST /api/generate_sharelink - 生成分享链接
  POST /api/save_share         - 转存分享文件
  POST /api/check_sharelink    - 检查分享链接
  POST /api/list_sharelink     - 列出分享文件
  GET  /api/health             - 健康检查
============================================================
```

## API 接口文档

### 响应格式

所有接口统一使用以下JSON格式：

```json
{
  "code": 1,        // 1=成功, 0=失败
  "data": {},       // 返回数据
  "message": ""     // 消息描述
}
```

---

### 1. 生成分享链接

**接口**: `POST /api/generate_sharelink`

**功能**: 为指定路径的文件或文件夹生成分享链接

**请求参数**:

```json
{
  "target_path": "/abc/20260123",  // 必需，要分享的文件/文件夹路径
  "password": "1234",              // 可选，分享密码，默认为空（公开）
  "days": 7                        // 可选，有效期天数：1/7/30/null(永久)，默认永久
}
```

**响应示例**:

```json
{
  "code": 1,
  "data": {
    "share_url": "https://pan.quark.cn/s/abc123?pwd=1234",
    "title": "20260123",
    "expired_type": 3  // 1=永久, 2=1天, 3=7天, 4=30天
  },
  "message": "分享链接生成成功"
}
```

**cURL示例**:

```bash
curl -X POST http://localhost:13000/api/generate_sharelink \
  -H "Content-Type: application/json" \
  -d '{
    "target_path": "/我的文件夹",
    "password": "test",
    "days": 7
  }'
```

---

### 2. 转存分享文件

**接口**: `POST /api/save_share`

**功能**: 将别人的分享链接转存到自己的网盘

**请求参数**:

```json
{
  "sharelink": "https://pan.quark.cn/s/abc123",  // 必需，分享链接
  "password": "1234",                            // 可选，分享密码
  "target_path": "/abc/20260123"                 // 必需，转存到的目标路径
}
```

**响应示例**:

```json
{
  "code": 1,
  "data": {
    "files": [
      {
        "name": "杀手记忆",
        "size": 0,
        "size_formatted": "0 B",
        "is_dir": true,
        "relative_path": "/杀手记忆",
        "file_type": "",
        "created_at": 1706234567,
        "updated_at": 1706234567
      },
      {
        "name": "01.mkv",
        "size": 2147483648,
        "size_formatted": "2.00 GB",
        "is_dir": false,
        "relative_path": "/杀手记忆/01.mkv",
        "file_type": "video",
        "created_at": 1706234567,
        "updated_at": 1706234567
      }
    ],
    "total_count": 2,
    "file_count": 1,
    "dir_count": 1
  },
  "message": "转存成功"
}
```

**注意**: 
- 返回的 `files` 数组包含转存目录下的所有文件（递归）
- `relative_path` 是相对于转存目标路径的相对路径
- `file_type` 可能的值包括: video, audio, image, doc 等
- `created_at` 和 `updated_at` 是时间戳（秒）

**cURL示例**:

```bash
curl -X POST http://localhost:13000/api/save_share \
  -H "Content-Type: application/json" \
  -d '{
    "sharelink": "https://pan.quark.cn/s/abc123?pwd=test",
    "password": "test",
    "target_path": "/我的收藏"
  }'
```

---

### 3. 检查分享链接

**接口**: `POST /api/check_sharelink`

**功能**: 检查分享链接是否有效（未过期、未删除）

**请求参数**:

```json
{
  "sharelink": "https://pan.quark.cn/s/abc123",  // 必需，分享链接
  "password": "1234"                             // 可选，分享密码
}
```

**响应示例（有效）**:

```json
{
  "code": 1,
  "data": {
    "is_valid": true,
    "file_count": 5
  },
  "message": "分享链接有效"
}
```

**响应示例（无效）**:

```json
{
  "code": 0,
  "data": {
    "is_valid": false
  },
  "message": "分享链接已失效或密码错误"
}
```

**cURL示例**:

```bash
curl -X POST http://localhost:13000/api/check_sharelink \
  -H "Content-Type: application/json" \
  -d '{
    "sharelink": "https://pan.quark.cn/s/abc123",
    "password": "test"
  }'
```

---

#### 4. 列出分享文件
```
POST /api/list_sharelink
Content-Type: application/json

Request:
{
  "sharelink": "https://pan.quark.cn/s/abc123",  // 必需，分享链接
  "password": "1234"                             // 可选，分享密码
}

Response:
{
  "code": 1,
  "data": {
    "files": [
      {
        "name": "杀手记忆",
        "size": 0,
        "size_formatted": "0 B",
        "is_dir": true,
        "relative_path": "/杀手记忆",
        "file_type": "",
        "item_count": 2
      },
      {
        "name": "01.mkv",
        "size": 1073741824,
        "size_formatted": "1.00 GB",
        "is_dir": false,
        "relative_path": "/杀手记忆/01.mkv",
        "file_type": "video"
      },
      {
        "name": "02.mkv",
        "size": 1073741824,
        "size_formatted": "1.00 GB",
        "is_dir": false,
        "relative_path": "/杀手记忆/02.mkv",
        "file_type": "video"
      }
    ],
    "total_count": 3,
    "file_count": 2,
    "dir_count": 1
  },
  "message": "获取成功"
}
```

**注意**:
- 返回所有文件和子目录（递归遍历）
- `relative_path` 是相对于分享根目录的路径
- `item_count` 仅对文件夹有效，表示直接子项数量
- `file_type` 表示文件类型


**cURL示例**:

```bash
curl -X POST http://localhost:13000/api/list_sharelink \
  -H "Content-Type: application/json" \
  -d '{
    "sharelink": "https://pan.quark.cn/s/abc123",
    "password": "test"
  }'
```

---

### 5. 健康检查

**接口**: `GET /api/health`

**功能**: 检查API服务状态和Cookie有效性

**响应示例**:

```json
{
  "code": 1,
  "data": {
    "status": "running",
    "cookie_valid": true
  },
  "message": "API服务运行正常"
}
```

**cURL示例**:

```bash
curl http://localhost:13000/api/health
```

---

## 错误处理

### Cookie过期

当Cookie过期时，所有接口会返回：

```json
{
  "code": 0,
  "data": {},
  "message": "Cookie已过期，请更新config/cookies.txt文件"
}
```

**HTTP状态码**: 401

同时，如果配置了邮件通知，系统会自动发送邮件提醒。

### 参数错误

缺少必需参数时：

```json
{
  "code": 0,
  "data": {},
  "message": "缺少必需参数: target_path"
}
```

**HTTP状态码**: 400

### 服务器错误

内部错误时：

```json
{
  "code": 0,
  "data": {},
  "message": "生成分享链接失败: [具体错误信息]"
}
```

**HTTP状态码**: 500

---

## Python调用示例

```python
import requests

# API基础URL
BASE_URL = "http://localhost:13000"

# 1. 生成分享链接
response = requests.post(
    f"{BASE_URL}/api/generate_sharelink",
    json={
        "target_path": "/我的视频",
        "password": "test123",
        "days": 7
    }
)
result = response.json()
if result['code'] == 1:
    print(f"分享链接: {result['data']['share_url']}")
else:
    print(f"失败: {result['message']}")

# 2. 转存文件
response = requests.post(
    f"{BASE_URL}/api/save_share",
    json={
        "sharelink": "https://pan.quark.cn/s/abc123",
        "password": "test",
        "target_path": "/我的收藏"
    }
)
result = response.json()
if result['code'] == 1:
    print(f"转存成功，共{result['data']['saved_count']}个文件")
else:
    print(f"失败: {result['message']}")

# 3. 检查链接
response = requests.post(
    f"{BASE_URL}/api/check_sharelink",
    json={
        "sharelink": "https://pan.quark.cn/s/abc123",
        "password": "test"
    }
)
result = response.json()
if result['code'] == 1 and result['data']['is_valid']:
    print(f"链接有效，包含{result['data']['file_count']}个文件")
else:
    print("链接已失效")

# 4. 列出文件
response = requests.post(
    f"{BASE_URL}/api/list_sharelink",
    json={
        "sharelink": "https://pan.quark.cn/s/abc123",
        "password": "test"
    }
)
result = response.json()
if result['code'] == 1:
    for file in result['data']['files']:
        file_type = "文件夹" if file['is_dir'] else "文件"
        print(f"{file_type}: {file['name']} ({file['size_formatted']})")
```

---

## 邮件通知

当Cookie过期时，系统会自动发送邮件通知到配置的邮箱。邮件内容包括：

- 过期检测时间
- 更新Cookie的详细步骤
- 自动通知标识

**测试邮件配置**:

```bash
python email_notifier.py
```

---

## 常见问题

### Q: 如何获取Gmail应用专用密码？

A: 
1. 访问 https://myaccount.google.com/apppasswords
2. 选择"应用"为"邮件"，"设备"为"Windows计算机"
3. 点击"生成"
4. 复制生成的16位密码到 `config.py` 的 `sender_password`

### Q: Cookie多久会过期？

A: 夸克网盘的Cookie通常有效期为30天，具体取决于账号设置。建议定期检查。

### Q: 如何在生产环境部署？

A: 建议使用 gunicorn 或 uwsgi 等WSGI服务器：

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:13000 quark_api:app
```

### Q: 支持HTTPS吗？

A: API服务本身不提供HTTPS，建议在前面加Nginx反向代理来提供SSL支持。

---

## 更新日志

### v1.0.0 (2026-01-26)

- ✅ 新增API模式，支持 `--api` 参数启动
- ✅ 实现4个核心接口：生成分享、转存、检查、列表
- ✅ 支持Cookie过期自动邮件通知
- ✅ 统一JSON响应格式
- ✅ 支持自定义端口配置

---

## 技术支持

如有问题，请在GitHub提交Issue或联系开发者。
