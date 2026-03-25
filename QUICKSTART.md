# QuarkPanTool API 快速开始指南

## 1. 安装依赖

```bash
cd g:\pro\QuarkPanTool-main
pip install -r requirements.txt
playwright install firefox
```

## 2. 验证安装

```bash
python verify_installation.py
```

该脚本会检查:
- 所有Python依赖是否已安装
- 必需的文件是否存在
- Cookie配置是否正确
- 邮件配置是否完整

## 3. 配置Cookie

API模式需要有效的Cookie才能运行。

### 方法1: 使用交互式登录（推荐）

```bash
python quark.py
# 选择选项 6 (登录)
# 在弹出的浏览器中登录夸克账号
# 登录成功后按Enter，Cookie会自动保存
```

### 方法2: 手动配置

1. 在浏览器中登录 https://pan.quark.cn
2. 打开开发者工具 (F12)
3. 切换到 Network 标签
4. 刷新页面
5. 找到任意请求，复制Cookie
6. 粘贴到 `config/cookies.txt` 文件

## 4. 配置邮件通知（可选）

编辑 `config.py` 文件:

```python
EMAIL_CONFIG = {
    'sender_email': 'your_email@gmail.com',
    'sender_password': 'your_app_password',  # Gmail应用专用密码
    'recipient_email': 'libertygm@gmail.com',
    'enabled': True  # 设置为True启用邮件通知
}
```

### 获取Gmail应用专用密码:

1. 访问 https://myaccount.google.com/apppasswords
2. 选择"应用"为"邮件"
3. 选择"设备"为"Windows计算机"
4. 点击"生成"
5. 复制16位密码到 `sender_password`

### 测试邮件配置:

```bash
python email_notifier.py
```

## 5. 启动API服务

```bash
# 使用默认端口 13000
python quark_api.py --api

# 或指定自定义端口
python quark_api.py --api --port 8080
```

启动成功后会显示:

```
============================================================
QuarkPanTool API Server
============================================================
监听地址: http://0.0.0.0:13000
健康检查: http://localhost:13000/api/health
...
```

## 6. 测试API

### 健康检查

```bash
curl http://localhost:13000/api/health
```

### 生成分享链接

```bash
curl -X POST http://localhost:13000/api/generate_sharelink \
  -H "Content-Type: application/json" \
  -d '{
    "target_path": "/",
    "password": "test",
    "days": 7
  }'
```

### 检查分享链接

```bash
curl -X POST http://localhost:13000/api/check_sharelink \
  -H "Content-Type: application/json" \
  -d '{
    "sharelink": "https://pan.quark.cn/s/xxxxx",
    "password": "test"
  }'
```

## 7. 查看完整文档

- API详细文档: [API_DOCUMENTATION.md](./API_DOCUMENTATION.md)
- 实现说明: 查看 walkthrough.md (在artifacts目录)

## 常见问题

### Q: 提示"Cookie已过期"怎么办？

A: 重新运行 `python quark.py` 选择选项6登录，或手动更新 `config/cookies.txt`

### Q: 邮件发送失败？

A: 
1. 确认使用的是Gmail应用专用密码，不是普通密码
2. 检查网络连接
3. 运行 `python email_notifier.py` 测试配置

### Q: API返回500错误？

A: 
1. 检查Cookie是否有效
2. 查看控制台错误信息
3. 确认目标路径是否存在

### Q: 如何停止API服务？

A: 在终端按 `Ctrl+C`

## 下一步

现在你可以:
- 使用Python/JavaScript调用API
- 集成到自己的应用中
- 部署到服务器（建议使用gunicorn）
- 添加Nginx反向代理实现HTTPS

祝使用愉快！
