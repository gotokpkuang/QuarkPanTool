"""
QuarkPanTool API 安装验证脚本
检查所有依赖是否正确安装
"""

import sys

def check_dependencies():
    """检查所有必需的依赖"""
    print("正在检查依赖...")
    print("=" * 60)
    
    dependencies = {
        'httpx': 'httpx',
        'retrying': 'retrying',
        'prettytable': 'prettytable',
        'playwright': 'playwright',
        'tqdm': 'tqdm',
        'colorama': 'colorama',
        'requests': 'requests',
        'Flask': 'flask',
        'flask_cors': 'flask-cors'
    }
    
    missing = []
    installed = []
    
    for module_name, package_name in dependencies.items():
        try:
            __import__(module_name)
            installed.append(f"✓ {package_name}")
        except ImportError:
            missing.append(f"✗ {package_name}")
    
    # 打印结果
    if installed:
        print("\n已安装的依赖:")
        for item in installed:
            print(f"  {item}")
    
    if missing:
        print("\n缺少的依赖:")
        for item in missing:
            print(f"  {item}")
        print("\n请运行以下命令安装缺少的依赖:")
        print("  pip install -r requirements.txt")
        return False
    else:
        print("\n✓ 所有依赖已正确安装!")
        return True


def check_files():
    """检查必需的文件"""
    print("\n" + "=" * 60)
    print("正在检查文件...")
    print("=" * 60)
    
    import os
    
    required_files = {
        'quark_api.py': 'API服务器主文件',
        'email_notifier.py': '邮件通知模块',
        'config.py': '配置文件',
        'quark.py': '核心功能模块',
        'quark_login.py': '登录模块',
        'utils.py': '工具函数',
        'requirements.txt': '依赖列表',
        'API_DOCUMENTATION.md': 'API文档'
    }
    
    missing = []
    found = []
    
    for filename, description in required_files.items():
        if os.path.exists(filename):
            found.append(f"✓ {filename} - {description}")
        else:
            missing.append(f"✗ {filename} - {description}")
    
    # 打印结果
    if found:
        print("\n找到的文件:")
        for item in found:
            print(f"  {item}")
    
    if missing:
        print("\n缺少的文件:")
        for item in missing:
            print(f"  {item}")
        return False
    else:
        print("\n✓ 所有必需文件都存在!")
        return True


def check_config():
    """检查配置"""
    print("\n" + "=" * 60)
    print("正在检查配置...")
    print("=" * 60)
    
    import os
    
    # 检查config目录
    if not os.path.exists('config'):
        print("✗ config 目录不存在，正在创建...")
        os.makedirs('config', exist_ok=True)
        print("✓ config 目录已创建")
    else:
        print("✓ config 目录存在")
    
    # 检查cookies.txt
    cookies_path = 'config/cookies.txt'
    if not os.path.exists(cookies_path):
        print(f"⚠ {cookies_path} 不存在")
        print("  提示: API模式需要有效的cookies才能运行")
        print("  请运行 'python quark.py' 并选择选项6进行登录")
        return False
    else:
        # 检查cookies是否为空
        with open(cookies_path, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            print(f"⚠ {cookies_path} 为空")
            print("  提示: 请运行 'python quark.py' 并选择选项6进行登录")
            return False
        else:
            print(f"✓ {cookies_path} 存在且不为空")
            return True


def check_email_config():
    """检查邮件配置"""
    print("\n" + "=" * 60)
    print("正在检查邮件配置...")
    print("=" * 60)
    
    try:
        from config import EMAIL_CONFIG
        
        if not EMAIL_CONFIG.get('enabled'):
            print("⚠ 邮件通知功能未启用")
            print("  如需启用，请编辑 config.py 设置 enabled=True")
            return True
        
        if not EMAIL_CONFIG.get('sender_email'):
            print("✗ 未配置发送者邮箱 (sender_email)")
            print("  请编辑 config.py 配置邮件设置")
            return False
        
        if not EMAIL_CONFIG.get('sender_password'):
            print("✗ 未配置发送者密码 (sender_password)")
            print("  请编辑 config.py 配置Gmail应用专用密码")
            print("  获取方法: https://myaccount.google.com/apppasswords")
            return False
        
        print(f"✓ 发送者邮箱: {EMAIL_CONFIG['sender_email']}")
        print(f"✓ 接收者邮箱: {EMAIL_CONFIG.get('recipient_email', '未设置')}")
        print(f"✓ SMTP服务器: {EMAIL_CONFIG['smtp_server']}:{EMAIL_CONFIG['smtp_port']}")
        
        return True
        
    except Exception as e:
        print(f"✗ 检查邮件配置时出错: {e}")
        return False


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("QuarkPanTool API 安装验证")
    print("=" * 60)
    
    results = []
    
    # 检查依赖
    results.append(("依赖检查", check_dependencies()))
    
    # 检查文件
    results.append(("文件检查", check_files()))
    
    # 检查配置
    results.append(("Cookie配置", check_config()))
    
    # 检查邮件配置
    results.append(("邮件配置", check_email_config()))
    
    # 总结
    print("\n" + "=" * 60)
    print("检查总结")
    print("=" * 60)
    
    all_passed = True
    for name, passed in results:
        status = "✓ 通过" if passed else "✗ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("✓ 所有检查通过！可以启动API服务:")
        print("  python quark_api.py --api")
    else:
        print("✗ 部分检查未通过，请根据上述提示进行修复")
        print("\n常见问题:")
        print("1. 缺少依赖: pip install -r requirements.txt")
        print("2. 缺少Cookie: python quark.py (选择选项6登录)")
        print("3. 邮件配置: 编辑 config.py 文件")
    
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())
