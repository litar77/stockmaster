#!/usr/bin/env python3
"""
StockMaster 自动安装脚本
自动完成环境检测、依赖安装和配置初始化
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

# 颜色输出
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    END = '\033[0m'
    BOLD = '\033[1m'

def print_header(text):
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*60}{Colors.END}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")

def print_warning(text):
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.END}")

def print_info(text):
    print(f"{Colors.BLUE}ℹ️  {text}{Colors.END}")

def check_python_version():
    """检查 Python 版本"""
    print_header("步骤 1: 检查 Python 环境")
    
    version = sys.version_info
    if version.major == 3 and version.minor >= 9:
        print_success(f"Python 版本：{version.major}.{version.minor}.{version.micro} ✅")
        return True
    else:
        print_error(f"Python 版本过低：{version.major}.{version.minor}.{version.micro}")
        print_info("需要 Python 3.9 或更高版本")
        print_info("请访问 https://www.python.org/downloads/ 下载最新版本")
        return False

def check_pip():
    """检查 pip 是否可用"""
    try:
        result = subprocess.run([sys.executable, '-m', 'pip', '--version'], 
                              capture_output=True, text=True, check=True)
        print_success(f"pip 已安装：{result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError:
        print_error("pip 未安装")
        return False

def create_venv():
    """创建虚拟环境"""
    print_header("步骤 2: 创建虚拟环境")
    
    venv_path = Path(__file__).parent / '.venv'
    
    if venv_path.exists():
        print_warning("虚拟环境已存在")
        response = input("是否重新创建？(y/N): ")
        if response.lower() != 'y':
            print_info("使用现有虚拟环境")
            return str(venv_path)
        else:
            print_info("删除旧虚拟环境...")
            import shutil
            shutil.rmtree(venv_path)
    
    print_info("正在创建虚拟环境...")
    try:
        subprocess.run([sys.executable, '-m', 'venv', str(venv_path)], check=True)
        print_success(f"虚拟环境已创建：{venv_path}")
        return str(venv_path)
    except subprocess.CalledProcessError as e:
        print_error(f"创建虚拟环境失败：{e}")
        print_warning("将继续使用当前 Python 环境")
        return None

def get_pip_command(venv_path=None):
    """获取 pip 命令"""
    if venv_path:
        if platform.system() == 'Windows':
            return str(Path(venv_path) / 'Scripts' / 'pip.exe')
        else:
            return str(Path(venv_path) / 'bin' / 'pip')
    return sys.executable + ' -m pip'

def install_dependencies(pip_cmd):
    """安装依赖包"""
    print_header("步骤 3: 安装依赖包")
    
    # 核心依赖
    core_deps = ['akshare', 'pandas', 'numpy', 'ta']
    
    # 可选依赖
    optional_deps = ['matplotlib', 'mplfinance']
    
    # 使用国内镜像加速
    mirror = 'https://pypi.tuna.tsinghua.edu.cn/simple/'
    
    print_info("安装核心依赖...")
    for dep in core_deps:
        print(f"  正在安装 {dep}...")
        try:
            cmd = f'{pip_cmd} install {dep} -i {mirror}'
            subprocess.run(cmd, shell=True, check=True, capture_output=True)
            print_success(f"{dep} 安装成功")
        except subprocess.CalledProcessError as e:
            print_error(f"{dep} 安装失败，尝试使用官方源...")
            try:
                subprocess.run(f'{pip_cmd} install {dep}', shell=True, check=True, capture_output=True)
                print_success(f"{dep} 安装成功（官方源）")
            except subprocess.CalledProcessError:
                print_error(f"{dep} 安装失败")
                return False
    
    print_info("\n可选依赖（用于可视化功能）:")
    for dep in optional_deps:
        print(f"  正在安装 {dep}...")
        try:
            subprocess.run(f'{pip_cmd} install {dep} -i {mirror}', shell=True, check=True, capture_output=True)
            print_success(f"{dep} 安装成功")
        except subprocess.CalledProcessError:
            print_warning(f"{dep} 安装失败（可选，不影响核心功能）")
    
    return True

def verify_installation(pip_cmd):
    """验证安装"""
    print_header("步骤 4: 验证安装")
    
    print_info("检查依赖包...")
    
    packages = ['akshare', 'pandas', 'numpy', 'ta']
    all_ok = True
    
    for pkg in packages:
        try:
            subprocess.run(f'{pip_cmd} show {pkg}', shell=True, check=True, 
                         capture_output=True)
            print_success(f"{pkg} ✅")
        except subprocess.CalledProcessError:
            print_error(f"{pkg} ❌")
            all_ok = False
    
    return all_ok

def test_data_fetch():
    """测试数据获取"""
    print_header("步骤 5: 测试数据获取")
    
    print_info("测试 AKShare 数据接口...")
    
    try:
        test_code = """
import akshare as ak
df = ak.stock_zh_index_daily(symbol='sh000001')
print(f"成功获取上证指数数据，共{len(df)}条记录")
"""
        result = subprocess.run([sys.executable, '-c', test_code], 
                              capture_output=True, text=True, check=True)
        print_success(result.stdout.strip())
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"数据获取测试失败：{e}")
        print_warning("请检查网络连接")
        return False

def init_directories():
    """初始化目录结构"""
    print_header("步骤 6: 初始化目录")
    
    base_dir = Path(__file__).parent
    
    directories = ['data', 'config', 'tests', '__pycache__']
    
    for dir_name in directories:
        dir_path = base_dir / dir_name
        if not dir_path.exists():
            dir_path.mkdir(parents=True)
            print_success(f"创建目录：{dir_name}")
        else:
            print_info(f"目录已存在：{dir_name}")
    
    # 初始化 portfolio.json
    portfolio_file = base_dir / 'data' / 'portfolio.json'
    if not portfolio_file.exists():
        import json
        initial_data = {
            "account": {
                "total_capital": 500000,
                "cash": 500000,
                "last_updated": "2026-03-27"
            },
            "holdings": [],
            "watchlist": [],
            "history": []
        }
        with open(portfolio_file, 'w', encoding='utf-8') as f:
            json.dump(initial_data, f, ensure_ascii=False, indent=2)
        print_success("初始化持仓数据文件：data/portfolio.json")
    
    return True

def run_test():
    """运行测试"""
    print_header("步骤 7: 运行测试")
    
    test_script = Path(__file__).parent / 'scripts' / 'market_analysis.py'
    
    if not test_script.exists():
        print_warning("测试脚本不存在，跳过测试")
        return True
    
    print_info("运行行情分析测试...")
    
    try:
        result = subprocess.run([sys.executable, str(test_script)], 
                              capture_output=True, text=True, check=True)
        
        # 显示输出（只显示最后几行）
        lines = result.stdout.strip().split('\n')
        if len(lines) > 5:
            for line in lines[-5:]:
                print(f"  {line}")
        else:
            for line in lines:
                print(f"  {line}")
        
        print_success("测试通过！")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"测试失败：{e}")
        return False

def print_summary():
    """打印安装总结"""
    print_header("安装完成！")
    
    print_success("StockMaster 已成功安装！")
    print()
    print_info("下一步操作：")
    print()
    print("  1. 激活虚拟环境（如果创建了虚拟环境）:")
    if platform.system() == 'Windows':
        print("     .venv\\Scripts\\activate")
    else:
        print("     source .venv/bin/activate")
    print()
    print("  2. 运行行情分析:")
    print("     python scripts/market_analysis.py")
    print()
    print("  3. 查看使用文档:")
    print("     打开 SKILL.md 文件")
    print()
    print("  4. 配置 OpenClaw 集成（可选）:")
    print("     参考 INSTALL.md 文档")
    print()
    print("="*60)
    print()

def main():
    """主函数"""
    print_header("StockMaster 自动安装程序")
    print_info("本脚本将自动完成 StockMaster 的安装和配置")
    print()
    
    # 步骤 1: 检查环境
    if not check_python_version():
        sys.exit(1)
    
    if not check_pip():
        sys.exit(1)
    
    # 步骤 2: 创建虚拟环境
    venv_path = create_venv()
    
    # 步骤 3: 安装依赖
    pip_cmd = get_pip_command(venv_path)
    if isinstance(pip_cmd, str) and ' ' in pip_cmd:
        pip_cmd = pip_cmd  # 已经是完整命令
    else:
        pip_cmd = f'{pip_cmd}'
    
    if not install_dependencies(pip_cmd):
        print_error("依赖安装失败")
        sys.exit(1)
    
    # 步骤 4: 验证安装
    if not verify_installation(pip_cmd):
        print_error("依赖验证失败")
        sys.exit(1)
    
    # 步骤 5: 测试数据获取
    if not test_data_fetch():
        print_warning("数据获取测试失败，但安装可能仍然可用")
    
    # 步骤 6: 初始化目录
    if not init_directories():
        print_error("目录初始化失败")
        sys.exit(1)
    
    # 步骤 7: 运行测试
    if not run_test():
        print_warning("测试失败，但安装可能仍然可用")
    
    # 打印总结
    print_summary()
    
    print_success("🎉 安装完成！")
    print()
    print_info("如有问题，请查看 INSTALL.md 文档或常见问题部分")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n")
        print_warning("安装被用户中断")
        sys.exit(1)
    except Exception as e:
        print("\n")
        print_error(f"安装过程中出现错误：{e}")
        print_info("请查看 INSTALL.md 文档获取帮助")
        sys.exit(1)
