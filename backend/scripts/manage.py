#!/usr/bin/env python3
"""
项目管理脚本
提供常用的开发和维护命令
"""
import sys
import os
import subprocess
import argparse

# Add the backend directory to Python path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

def run_tests(test_type=None):
    """运行测试"""
    test_cmd = [sys.executable, "tests/run_tests.py"]
    if test_type:
        test_cmd.extend(["--type", test_type])
    
    print(f"🧪 运行测试...")
    result = subprocess.run(test_cmd, cwd=backend_dir)
    return result.returncode == 0

def check_services():
    """检查服务状态"""
    print("🔍 检查服务状态...")
    test_cmd = [sys.executable, "tests/integration/test_services.py"]
    result = subprocess.run(test_cmd, cwd=backend_dir)
    return result.returncode == 0

def start_dev_server(mode='main', port=None):
    """启动开发服务器"""
    cmd = [sys.executable, "scripts/dev_server.py", "--mode", mode]
    if port:
        cmd.extend(["--port", str(port)])
    
    print(f"🚀 启动{mode}模式开发服务器...")
    subprocess.run(cmd, cwd=backend_dir)

def show_project_info():
    """显示项目信息"""
    print("📊 股票分析系统 - 后端项目信息")
    print("=" * 50)
    print(f"项目目录: {backend_dir}")
    
    # 检查主要目录
    directories = ["app", "tests", "scripts"]
    for dir_name in directories:
        dir_path = os.path.join(backend_dir, dir_name)
        status = "✅" if os.path.exists(dir_path) else "❌"
        print(f"{status} {dir_name}/ 目录")
    
    # 检查主要文件
    files = ["requirements.txt", "Dockerfile"]
    for file_name in files:
        file_path = os.path.join(backend_dir, file_name)
        status = "✅" if os.path.exists(file_path) else "❌"
        print(f"{status} {file_name}")
    
    print("\n🛠️ 可用命令:")
    print("  python scripts/manage.py --help")
    print("  python scripts/dev_server.py --help")
    print("  python tests/run_tests.py --help")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='项目管理脚本')
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 测试命令
    test_parser = subparsers.add_parser('test', help='运行测试')
    test_parser.add_argument('--type', choices=['unit', 'integration', 'data'],
                           help='测试类型')
    
    # 服务检查命令
    subparsers.add_parser('check', help='检查服务状态')
    
    # 服务器启动命令
    server_parser = subparsers.add_parser('server', help='启动开发服务器')
    server_parser.add_argument('--mode', choices=['main', 'simple', 'news'], 
                              default='main', help='服务器模式')
    server_parser.add_argument('--port', type=int, help='端口号')
    
    # 项目信息命令
    subparsers.add_parser('info', help='显示项目信息')
    
    args = parser.parse_args()
    
    if not args.command:
        show_project_info()
        return
    
    try:
        if args.command == 'test':
            success = run_tests(args.type)
            sys.exit(0 if success else 1)
        elif args.command == 'check':
            success = check_services()
            sys.exit(0 if success else 1)
        elif args.command == 'server':
            start_dev_server(args.mode, args.port)
        elif args.command == 'info':
            show_project_info()
            
    except KeyboardInterrupt:
        print("\n⏸ 操作被用户中断")
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()