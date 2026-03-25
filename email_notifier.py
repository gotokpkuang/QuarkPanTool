"""
Email notification module for QuarkPanTool
Sends alerts when cookies expire
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from config import EMAIL_CONFIG


def send_cookie_expiration_alert(recipient_email=None):
    """
    发送Cookie过期提醒邮件
    
    Args:
        recipient_email: 接收邮件的地址，如果为None则使用配置中的默认地址
        
    Returns:
        tuple: (success: bool, message: str)
    """
    if not EMAIL_CONFIG.get('enabled', False):
        return False, "邮件通知功能未启用"
    
    # 检查必要的配置
    if not EMAIL_CONFIG.get('sender_email') or not EMAIL_CONFIG.get('sender_password'):
        return False, "邮件发送者信息未配置，请在config.py中设置sender_email和sender_password"
    
    # 使用默认接收者或指定接收者
    recipient = recipient_email or EMAIL_CONFIG.get('recipient_email')
    if not recipient:
        return False, "未指定接收邮件的地址"
    
    try:
        # 创建邮件内容
        msg = MIMEMultipart('alternative')
        msg['Subject'] = EMAIL_CONFIG.get('subject', '夸克网盘Cookie已过期提醒')
        msg['From'] = EMAIL_CONFIG['sender_email']
        msg['To'] = recipient
        
        # 邮件正文
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        text_content = f"""
夸克网盘Cookie过期通知

检测时间: {current_time}

您的夸克网盘Cookie已过期，API服务无法正常工作。

请执行以下操作更新Cookie：
1. 运行命令: python quark.py
2. 选择选项 6 (登录)
3. 在弹出的浏览器中登录夸克账号
4. 登录成功后，Cookie将自动保存到 config/cookies.txt

更新Cookie后，API服务将恢复正常。

---
QuarkPanTool API 自动通知
"""
        
        html_content = f"""
<html>
<head></head>
<body>
    <h2 style="color: #d9534f;">夸克网盘Cookie过期通知</h2>
    <p><strong>检测时间:</strong> {current_time}</p>
    <p>您的夸克网盘Cookie已过期，API服务无法正常工作。</p>
    
    <h3>请执行以下操作更新Cookie：</h3>
    <ol>
        <li>运行命令: <code>python quark.py</code></li>
        <li>选择选项 <strong>6 (登录)</strong></li>
        <li>在弹出的浏览器中登录夸克账号</li>
        <li>登录成功后，Cookie将自动保存到 <code>config/cookies.txt</code></li>
    </ol>
    
    <p>更新Cookie后，API服务将恢复正常。</p>
    
    <hr>
    <p style="color: #666; font-size: 12px;">QuarkPanTool API 自动通知</p>
</body>
</html>
"""
        
        # 添加文本和HTML版本
        part1 = MIMEText(text_content, 'plain', 'utf-8')
        part2 = MIMEText(html_content, 'html', 'utf-8')
        msg.attach(part1)
        msg.attach(part2)
        
        # 连接到Gmail SMTP服务器并发送邮件
        server = smtplib.SMTP(EMAIL_CONFIG['smtp_server'], EMAIL_CONFIG['smtp_port'])
        server.starttls()  # 启用TLS加密
        server.login(EMAIL_CONFIG['sender_email'], EMAIL_CONFIG['sender_password'])
        server.send_message(msg)
        server.quit()
        
        return True, f"邮件发送成功至 {recipient}"
        
    except smtplib.SMTPAuthenticationError:
        return False, "SMTP认证失败，请检查sender_email和sender_password是否正确（需要使用Gmail应用专用密码）"
    except smtplib.SMTPException as e:
        return False, f"SMTP错误: {str(e)}"
    except Exception as e:
        return False, f"发送邮件失败: {str(e)}"


def test_email_config():
    """
    测试邮件配置是否正确
    
    Returns:
        tuple: (success: bool, message: str)
    """
    print("正在测试邮件配置...")
    print(f"SMTP服务器: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
    print(f"发送者: {EMAIL_CONFIG.get('sender_email', '未配置')}")
    print(f"接收者: {EMAIL_CONFIG.get('recipient_email', '未配置')}")
    print(f"邮件通知: {'启用' if EMAIL_CONFIG.get('enabled') else '禁用'}")
    
    if not EMAIL_CONFIG.get('enabled'):
        return False, "邮件通知功能未启用"
    
    success, message = send_cookie_expiration_alert()
    return success, message


if __name__ == '__main__':
    # 测试邮件发送功能
    success, message = test_email_config()
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
