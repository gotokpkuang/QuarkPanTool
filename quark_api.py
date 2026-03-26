"""
QuarkPanTool API Server
提供REST API接口用于夸克网盘操作
"""

import sys
import os
import argparse
import asyncio
import logging
import logging.handlers
from flask import Flask, request, jsonify
from flask_cors import CORS
from quark import QuarkPanFileManager
from email_notifier import send_cookie_expiration_alert
from config import API_CONFIG, EXPIRATION_TYPE_MAP
from utils import custom_print


app = Flask(__name__)
CORS(app)  # 允许跨域请求

# ── 日志配置 ──────────────────────────────────────────────────────────────────
os.makedirs('logs', exist_ok=True)
logger = logging.getLogger('quark_api')
logger.setLevel(logging.DEBUG)
_fmt = logging.Formatter('[%(asctime)s] %(levelname)s %(message)s',
                         datefmt='%Y-%m-%d %H:%M:%S')
# 滚动文件：单文件 10 MB，最多保留 5 个
_fh = logging.handlers.RotatingFileHandler(
    'logs/api.log', maxBytes=10 * 1024 * 1024, backupCount=5, encoding='utf-8')
_fh.setFormatter(_fmt)
_sh = logging.StreamHandler(sys.stdout)
_sh.setFormatter(_fmt)
logger.addHandler(_fh)
logger.addHandler(_sh)
# 屏蔽 werkzeug 的默认请求行（避免重复）
logging.getLogger('werkzeug').setLevel(logging.WARNING)

# 全局QuarkPanFileManager实例
quark_manager = None
cookie_expired_notified = False  # 防止重复发送邮件


# ── 请求日志钩子 ─────────────────────────────────────────────────────────────
@app.before_request
def _log_request():
    client_ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    body = ''
    if request.is_json:
        try:
            body = request.get_json(silent=True) or {}
            # 隐藏密码明文
            if isinstance(body, dict) and 'password' in body and body['password']:
                body = {**body, 'password': '***'}
        except Exception:
            body = '<parse error>'
    logger.info('REQUEST  %s %s  client=%s  body=%s',
                request.method, request.path, client_ip, body)


# ── 统一响应日志助手 ──────────────────────────────────────────────────────────
def log_resp(code: int, data: dict, message: str, http_status: int = 200):
    """记录响应摘要并返回 Flask Response 对象"""
    level = logging.INFO if code == 1 else logging.WARNING
    logger.log(level, 'RESPONSE code=%d  message=%s  http=%d', code, message, http_status)
    return jsonify({'code': code, 'data': data, 'message': message}), http_status


def init_quark_manager():
    """初始化QuarkPanFileManager实例"""
    global quark_manager
    try:
        logger.info('正在初始化 QuarkPanFileManager ...')
        quark_manager = QuarkPanFileManager(headless=True, slow_mo=0)
        logger.info('QuarkPanFileManager 初始化成功')
        return True
    except Exception as e:
        logger.exception('QuarkPanFileManager 初始化失败: %s', e)
        return False


def check_cookie_and_notify():
    """
    检查cookie是否有效，如果无效则发送邮件通知

    Returns:
        bool: cookie是否有效
    """
    global cookie_expired_notified

    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        user_info = loop.run_until_complete(quark_manager.get_user_info())
        loop.close()

        if user_info:
            cookie_expired_notified = False
            logger.debug('Cookie 验证通过，当前用户: %s', user_info)
            return True
        else:
            logger.warning('Cookie 已失效')
            if not cookie_expired_notified:
                logger.info('正在发送 Cookie 过期邮件通知 ...')
                try:
                    success, msg = send_cookie_expiration_alert()
                    if success:
                        logger.info('Cookie 过期邮件已发送: %s', msg)
                    else:
                        logger.error('Cookie 过期邮件发送失败: %s', msg)
                except Exception as mail_err:
                    logger.exception('发送过期邮件时抛出异常: %s', mail_err)
                cookie_expired_notified = True
            return False
    except Exception as e:
        logger.exception('检查 Cookie 时出错: %s', e)
        return False


def format_file_size(size_bytes):
    """
    格式化文件大小
    
    Args:
        size_bytes: 文件大小（字节）
        
    Returns:
        str: 格式化后的文件大小
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


@app.route('/api/generate_sharelink', methods=['POST'])
def generate_sharelink():
    """
    生成分享链接
    
    Request JSON:
        {
            "target_path": "/abc/20260123",  # 必需
            "password": "1234",              # 可选
            "days": 7                        # 可选，1/7/30/null(永久)
        }
    
    Response JSON:
        {
            "code": 1,
            "data": {
                "share_url": "https://pan.quark.cn/s/xxxxx",
                "title": "文件夹名称"
            },
            "message": "成功"
        }
    """
    try:
        # 检查cookie
        if not check_cookie_and_notify():
            return jsonify({
                'code': 0,
                'data': {},
                'message': 'Cookie已过期，请更新config/cookies.txt文件'
            }), 401
        
        # 获取请求参数
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '请求体不能为空'
            }), 400
        
        target_path = data.get('target_path')
        password = data.get('password', '')
        days = data.get('days')
        
        # 验证必需参数
        if not target_path:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '缺少必需参数: target_path'
            }), 400
        
        # 转换有效期
        expired_type = EXPIRATION_TYPE_MAP.get(days, 1)  # 默认永久
        
        # 获取目标路径的fid
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # 获取文件/文件夹信息
        fid_list = loop.run_until_complete(
            asyncio.to_thread(quark_manager.get_fids, [target_path])
        )
        
        if not fid_list or len(fid_list) == 0:
            loop.close()
            return jsonify({
                'code': 0,
                'data': {},
                'message': f'目标路径不存在: {target_path}'
            }), 404
        
        fid = fid_list[0]['fid']
        file_name = fid_list[0].get('file_name', target_path.split('/')[-1])
        
        # 生成分享链接
        url_type = 2 if password else 1  # 2=加密, 1=公开
        
        task_id = loop.run_until_complete(
            quark_manager.get_share_task_id(fid, file_name, url_type, expired_type, password)
        )
        
        share_id = loop.run_until_complete(quark_manager.get_share_id(task_id))
        share_url, title = loop.run_until_complete(quark_manager.submit_share(share_id))
        
        loop.close()
        
        return jsonify({
            'code': 1,
            'data': {
                'share_url': share_url,
                'title': title,
                'expired_type': expired_type
            },
            'message': '分享链接生成成功'
        }), 200
        
    except Exception as e:
        return jsonify({
            'code': 0,
            'data': {},
            'message': f'生成分享链接失败: {str(e)}'
        }), 500


@app.route('/api/save_share', methods=['POST'])
def save_share():
    """
    转存分享文件
    
    Request JSON:
        {
            "sharelink": "https://pan.quark.cn/s/xxxxx",  # 必需
            "password": "1234",                           # 可选
            "target_path": "/abc/20260123"                # 必需
        }
    
    Response JSON:
        {
            "code": 1,
            "data": {
                "saved_files": ["file1.mp4"],
                "saved_count": 1
            },
            "message": "转存成功"
        }
    """
    try:
        # 检查cookie
        if not check_cookie_and_notify():
            return jsonify({
                'code': 0,
                'data': {},
                'message': 'Cookie已过期，请更新config/cookies.txt文件'
            }), 401
        
        # 获取请求参数
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '请求体不能为空'
            }), 400
        
        sharelink = data.get('sharelink')
        password = data.get('password', '')
        target_path = data.get('target_path')
        
        # 验证必需参数
        if not sharelink:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '缺少必需参数: sharelink'
            }), 400
        
        if not target_path:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '缺少必需参数: target_path'
            }), 400
        
        # 获取目标文件夹ID
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        fid_list = loop.run_until_complete(
            asyncio.to_thread(quark_manager.get_fids, [target_path])
        )
        
        if not fid_list or len(fid_list) == 0:
            # 目标文件夹不存在，尝试递归创建
            try:
                # 使用mkdir_recursive支持多级目录创建
                result = quark_manager.mkdir_recursive(target_path)
                
                if result.get('code') != 0 and result.get('code') != 23008:
                    loop.close()
                    return jsonify({
                        'code': 0,
                        'data': {},
                        'message': f'目标路径创建失败: {result.get("message", "未知错误")}'
                    }), 500
                
                # 重新获取fid
                import time
                time.sleep(0.5)  # 等待一下确保目录创建完成
                
                fid_list = loop.run_until_complete(
                    asyncio.to_thread(quark_manager.get_fids, [target_path])
                )
                
                if not fid_list:
                    loop.close()
                    return jsonify({
                        'code': 0,
                        'data': {},
                        'message': f'目标路径创建后仍无法获取: {target_path}'
                    }), 500
            except Exception as e:
                loop.close()
                return jsonify({
                    'code': 0,
                    'data': {},
                    'message': f'目标路径创建失败: {str(e)}'
                }), 500
        
        folder_id = fid_list[0]['fid']
        
        # 执行转存
        # 使用自定义的转存逻辑来捕获文件列表
        pwd_id = quark_manager.get_pwd_id(sharelink)
        stoken = loop.run_until_complete(quark_manager.get_stoken(pwd_id, password))
        
        if not stoken:
            loop.close()
            return jsonify({
                'code': 0,
                'data': {},
                'message': '分享链接无效或密码错误'
            }), 400
        
        is_owner, data_list = loop.run_until_complete(quark_manager.get_detail(pwd_id, stoken))
        
        if is_owner == 1:
            loop.close()
            return jsonify({
                'code': 0,
                'data': {},
                'message': '该文件已在您的网盘中，无需转存'
            }), 400
        
        if not data_list:
            loop.close()
            return jsonify({
                'code': 0,
                'data': {},
                'message': '分享链接中没有文件'
            }), 404
        
        # 提取文件信息
        saved_files = [item['file_name'] for item in data_list]
        fid_list_to_save = [item['fid'] for item in data_list]
        share_fid_token_list = [item['share_fid_token'] for item in data_list]
        
        # 执行转存
        task_id = loop.run_until_complete(
            quark_manager.get_share_save_task_id(pwd_id, stoken, fid_list_to_save, 
                                                  share_fid_token_list, folder_id)
        )
        
        result = loop.run_until_complete(quark_manager.submit_task(task_id))
        
        if result and isinstance(result, dict):
            # 转存成功后，递归查询转存目录的所有文件
            try:
                # 获取转存目录的所有文件（递归）
                all_files = loop.run_until_complete(
                    quark_manager.list_files_recursive(folder_id, '')
                )
                
                loop.close()
                
                # 格式化文件列表
                formatted_files = []
                for file_info in all_files:
                    formatted_file = {
                        'name': file_info['name'],
                        'size': file_info['size'],
                        'size_formatted': format_file_size(file_info['size']),
                        'is_dir': file_info['is_dir'],
                        'relative_path': file_info['relative_path'],
                        'file_type': file_info.get('file_type', ''),
                        'created_at': file_info.get('created_at', ''),
                        'updated_at': file_info.get('updated_at', '')
                    }
                    formatted_files.append(formatted_file)
                
                # 统计文件和文件夹数量
                file_count = sum(1 for f in formatted_files if not f['is_dir'])
                dir_count = sum(1 for f in formatted_files if f['is_dir'])
                
                return jsonify({
                    'code': 1,
                    'data': {
                        'files': formatted_files,
                        'total_count': len(formatted_files),
                        'file_count': file_count,
                        'dir_count': dir_count
                    },
                    'message': '转存成功'
                }), 200
            except Exception as e:
                loop.close()
                # 即使查询文件列表失败，转存本身是成功的
                return jsonify({
                    'code': 1,
                    'data': {
                        'saved_files': saved_files,
                        'saved_count': len(saved_files),
                        'note': f'转存成功但查询文件列表失败: {str(e)}'
                    },
                    'message': '转存成功'
                }), 200
        else:
            loop.close()
            return jsonify({
                'code': 0,
                'data': {},
                'message': '转存失败'
            }), 500

        
    except Exception as e:
        return jsonify({
            'code': 0,
            'data': {},
            'message': f'转存失败: {str(e)}'
        }), 500


@app.route('/api/check_sharelink', methods=['POST'])
def check_sharelink():
    """
    检查分享链接是否有效
    
    Request JSON:
        {
            "sharelink": "https://pan.quark.cn/s/xxxxx",  # 必需
            "password": "1234"                            # 可选
        }
    
    Response JSON:
        {
            "code": 1,
            "data": {
                "is_valid": true,
                "file_count": 5
            },
            "message": "分享链接有效"
        }
    """
    try:
        # 此接口均为匿名请求，无需检查 cookie
        # 获取请求参数
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '请求体不能为空'
            }), 400
        
        sharelink = data.get('sharelink')
        password = data.get('password', '')
        
        # 验证必需参数
        if not sharelink:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '缺少必需参数: sharelink'
            }), 400
        
        # 匿名检查分享链接
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        pwd_id = quark_manager.get_pwd_id(sharelink)
        stoken = loop.run_until_complete(
            quark_manager.get_stoken(pwd_id, password,
                                     custom_headers=quark_manager.anon_headers))
        
        if not stoken:
            loop.close()
            return jsonify({
                'code': 0,
                'data': {
                    'is_valid': False
                },
                'message': '分享链接已失效或密码错误'
            }), 200
        
        # 匿名获取详情
        is_owner, data_list = loop.run_until_complete(
            quark_manager.get_detail(pwd_id, stoken,
                                     custom_headers=quark_manager.anon_headers))
        
        loop.close()
        
        if data_list is not None:
            return jsonify({
                'code': 1,
                'data': {
                    'is_valid': True,
                    'file_count': len(data_list) if data_list else 0
                },
                'message': '分享链接有效'
            }), 200
        else:
            return jsonify({
                'code': 0,
                'data': {
                    'is_valid': False
                },
                'message': '分享链接已失效'
            }), 200
        
    except Exception as e:
        return jsonify({
            'code': 0,
            'data': {
                'is_valid': False
            },
            'message': f'检查失败: {str(e)}'
        }), 500


@app.route('/api/list_sharelink', methods=['POST'])
def list_sharelink():
    """
    列出分享链接中的文件
    
    Request JSON:
        {
            "sharelink": "https://pan.quark.cn/s/xxxxx",  # 必需
            "password": "1234"                            # 可选
        }
    
    Response JSON:
        {
            "code": 1,
            "data": {
                "files": [
                    {
                        "name": "video.mp4",
                        "size": 1073741824,
                        "size_formatted": "1.00 GB",
                        "is_dir": false
                    }
                ],
                "total_count": 1
            },
            "message": "获取成功"
        }
    """
    try:
        # 此接口均为匿名请求，无需检查 cookie
        # 获取请求参数
        data = request.get_json()
        if not data:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '请求体不能为空'
            }), 400
        
        sharelink = data.get('sharelink')
        password = data.get('password', '')
        
        # 验证必需参数
        if not sharelink:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '缺少必需参数: sharelink'
            }), 400
        
        # 匿名获取分享链接内容
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        pwd_id = quark_manager.get_pwd_id(sharelink)
        stoken = loop.run_until_complete(
            quark_manager.get_stoken(pwd_id, password,
                                     custom_headers=quark_manager.anon_headers))
        
        if not stoken:
            loop.close()
            return jsonify({
                'code': 0,
                'data': {},
                'message': '分享链接已失效或密码错误'
            }), 400
        
        # 匿名递归获取所有文件（包括子目录）
        all_files = loop.run_until_complete(
            quark_manager.list_share_files_recursive(pwd_id, stoken, '0', '', anonymous=True)
        )
        
        loop.close()
        
        if all_files is None:
            return jsonify({
                'code': 0,
                'data': {},
                'message': '获取文件列表失败'
            }), 500
        
        # 格式化文件列表
        formatted_files = []
        for file_info in all_files:
            formatted_file = {
                'name': file_info['name'],
                'size': file_info['size'],
                'size_formatted': format_file_size(file_info['size']),
                'is_dir': file_info['is_dir'],
                'relative_path': file_info['relative_path'],
                'file_type': file_info.get('file_type', ''),
                'fid': file_info.get('fid', ''),
                'pdir_fid': file_info.get('pdir_fid', ''),
                'updated_at': file_info.get('updated_at', 0),
                'created_at': file_info.get('created_at', 0),
            }

            if file_info['is_dir']:
                # 目录：加入 item_count
                include_items = file_info.get('include_items', '')
                formatted_file['item_count'] = int(include_items) if str(include_items).isdigit() else 0
            else:
                # 文件：加入完整路径
                formatted_file['fullpath'] = file_info['relative_path']
                # 视频文件：加入视频专属信息
                if file_info.get('obj_category') == 'video':
                    formatted_file['video_max_resolution'] = file_info.get('video_max_resolution', '')
                    formatted_file['video_width'] = file_info.get('video_width', 0)
                    formatted_file['video_height'] = file_info.get('video_height', 0)
                    formatted_file['fps'] = file_info.get('fps', 0)
                    formatted_file['duration'] = file_info.get('duration', 0)
                    formatted_file['format_type'] = file_info.get('format_type', '')

            formatted_files.append(formatted_file)
        
        # 统计文件和文件夹数量
        file_count = sum(1 for f in formatted_files if not f['is_dir'])
        dir_count = sum(1 for f in formatted_files if f['is_dir'])
        
        return jsonify({
            'code': 1,
            'data': {
                'files': formatted_files,
                'total_count': len(formatted_files),
                'file_count': file_count,
                'dir_count': dir_count
            },
            'message': '获取成功'
        }), 200

        
    except Exception as e:
        return jsonify({
            'code': 0,
            'data': {},
            'message': f'获取文件列表失败: {str(e)}'
        }), 500


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    cookie_valid = check_cookie_and_notify()
    return jsonify({
        'code': 1,
        'data': {
            'status': 'running',
            'cookie_valid': cookie_valid
        },
        'message': 'API服务运行正常'
    }), 200


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='QuarkPanTool API Server')
    parser.add_argument('--api', action='store_true', help='以API模式启动')
    parser.add_argument('--port', type=int, default=API_CONFIG['default_port'], 
                       help=f'API服务端口 (默认: {API_CONFIG["default_port"]})')
    
    args = parser.parse_args()
    
    if not args.api:
        print("请使用 --api 参数启动API服务")
        print("示例: python quark_api.py --api")
        print("或指定端口: python quark_api.py --api --port 8080")
        sys.exit(1)
    
    # 初始化QuarkPanFileManager
    print("正在初始化QuarkPanFileManager...")
    if not init_quark_manager():
        print("初始化失败，请检查config/cookies.txt文件是否存在且有效")
        sys.exit(1)
    
    print("初始化成功！")
    print(f"\n{'='*60}")
    print(f"QuarkPanTool API Server")
    print(f"{'='*60}")
    print(f"监听地址: http://{API_CONFIG['host']}:{args.port}")
    print(f"健康检查: http://localhost:{args.port}/api/health")
    print(f"\n可用接口:")
    print(f"  POST /api/generate_sharelink - 生成分享链接")
    print(f"  POST /api/save_share         - 转存分享文件")
    print(f"  POST /api/check_sharelink    - 检查分享链接")
    print(f"  POST /api/list_sharelink     - 列出分享文件")
    print(f"  GET  /api/health             - 健康检查")
    print(f"{'='*60}\n")
    
    # 启动Flask应用
    app.run(
        host=API_CONFIG['host'],
        port=args.port,
        debug=API_CONFIG['debug']
    )


if __name__ == '__main__':
    main()
