"""
改进的主程序入口
提供统一的程序启动和模式选择
"""
import sys
import os
import argparse
import logging
from typing import Optional

# 添加当前目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import get_config, config_manager
from error_handler import handle_error, ErrorType, get_error_statistics
from robot_controller_improved import get_robot_controller
from image_processor import detect_wound
from coordinate_transformer import get_coordinate_transformer

def setup_logging():
    """设置日志系统"""
    config = get_config()
    
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, config.log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'{log_dir}/robot_arm.log', encoding='utf-8'),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger(__name__)
    logger.info("日志系统初始化完成")
    return logger

def run_gui_mode():
    """运行GUI模式"""
    try:
        import tkinter as tk
        from gui_improved import ModernGUI
        
        logger = logging.getLogger(__name__)
        logger.info("启动GUI模式")
        
        root = tk.Tk()
        
        # 设置样式
        style = tk.ttk.Style()
        style.theme_use('clam')
        
        # 创建应用
        app = ModernGUI(root)
        
        # 运行主循环
        root.mainloop()
        
    except ImportError as e:
        print(f"GUI模式启动失败: {e}")
        print("请确保已安装tkinter")
        return False
    except Exception as e:
        handle_error(ErrorType.UNKNOWN_ERROR, f"GUI模式运行失败: {e}")
        return False
    
    return True

def run_cli_mode():
    """运行命令行模式"""
    logger = logging.getLogger(__name__)
    logger.info("启动CLI模式")
    
    try:
        # 初始化系统
        config = get_config()
        robot_controller = get_robot_controller()
        coordinate_transformer = get_coordinate_transformer()
        
        print("=== 智能机械臂伤口治疗系统 CLI模式 ===")
        print("输入 'help' 查看可用命令")
        
        while True:
            try:
                command = input("\n> ").strip().lower()
                
                if command in ['quit', 'exit', 'q']:
                    print("退出程序")
                    break
                elif command == 'help':
                    print_help()
                elif command == 'status':
                    show_status(robot_controller)
                elif command == 'connect':
                    connect_robot(robot_controller)
                elif command == 'disconnect':
                    disconnect_robot(robot_controller)
                elif command == 'calibrate':
                    calibrate_system(robot_controller, coordinate_transformer)
                elif command == 'test':
                    test_system(robot_controller, coordinate_transformer)
                elif command == 'config':
                    show_config(config)
                elif command == 'errors':
                    show_errors()
                else:
                    print(f"未知命令: {command}")
                    print("输入 'help' 查看可用命令")
            
            except KeyboardInterrupt:
                print("\n程序被用户中断")
                break
            except Exception as e:
                print(f"命令执行失败: {e}")
                handle_error(ErrorType.UNKNOWN_ERROR, f"CLI命令执行失败: {e}")
    
    except Exception as e:
        handle_error(ErrorType.UNKNOWN_ERROR, f"CLI模式运行失败: {e}")
        return False
    
    return True

def print_help():
    """打印帮助信息"""
    help_text = """
可用命令:
  help        - 显示此帮助信息
  status      - 显示系统状态
  connect     - 连接机械臂
  disconnect  - 断开机械臂连接
  calibrate   - 执行系统标定
  test        - 测试系统功能
  config      - 显示当前配置
  errors      - 显示错误统计
  quit/exit/q - 退出程序
    """
    print(help_text)

def show_status(robot_controller):
    """显示系统状态"""
    print("\n=== 系统状态 ===")
    
    # 机械臂状态
    if robot_controller and robot_controller.is_connected:
        status = robot_controller.get_current_status()
        pos = status.current_position
        print(f"机械臂: 已连接")
        print(f"位置: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")
        print(f"状态: {status.current_state.value}")
    else:
        print("机械臂: 未连接")
    
    # 配置状态
    config = get_config()
    print(f"摄像头设备: {config.camera.device_id}")
    print(f"机械臂端口: {config.robot.port}")
    print(f"日志级别: {config.log_level}")

def connect_robot(robot_controller):
    """连接机械臂"""
    if robot_controller and robot_controller.is_connected:
        print("机械臂已连接")
        return
    
    print("正在连接机械臂...")
    try:
        robot_controller = get_robot_controller()
        if robot_controller.is_connected:
            print("机械臂连接成功")
        else:
            print("机械臂连接失败")
    except Exception as e:
        print(f"连接失败: {e}")
        handle_error(ErrorType.COMMUNICATION_ERROR, f"机械臂连接失败: {e}")

def disconnect_robot(robot_controller):
    """断开机械臂连接"""
    if not robot_controller or not robot_controller.is_connected:
        print("机械臂未连接")
        return
    
    try:
        robot_controller.disconnect()
        print("机械臂已断开连接")
    except Exception as e:
        print(f"断开连接失败: {e}")

def calibrate_system(robot_controller, coordinate_transformer):
    """执行系统标定"""
    if not robot_controller or not robot_controller.is_connected:
        print("请先连接机械臂")
        return
    
    print("系统标定功能需要GUI模式或手动操作")
    print("请使用GUI模式进行标定")

def test_system(robot_controller, coordinate_transformer):
    """测试系统功能"""
    print("\n=== 系统测试 ===")
    
    # 测试机械臂连接
    if robot_controller and robot_controller.is_connected:
        print("✓ 机械臂连接正常")
        
        # 测试位置获取
        pos = robot_controller.get_current_position()
        if pos:
            print(f"✓ 位置获取正常: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})")
        else:
            print("✗ 位置获取失败")
    else:
        print("✗ 机械臂未连接")
    
    # 测试配置
    config = get_config()
    if config_manager.validate_config():
        print("✓ 配置验证通过")
    else:
        print("✗ 配置验证失败")
    
    # 测试错误处理
    try:
        handle_error(ErrorType.UNKNOWN_ERROR, "测试错误处理")
        print("✓ 错误处理系统正常")
    except Exception as e:
        print(f"✗ 错误处理系统异常: {e}")

def show_config(config):
    """显示当前配置"""
    print("\n=== 当前配置 ===")
    print(f"摄像头偏移: ({config.camera.offset_x}, {config.camera.offset_y})")
    print(f"喷嘴高度: {config.camera.nozzle_height}")
    print(f"机械臂端口: {config.robot.port}")
    print(f"波特率: {config.robot.baudrate}")
    print(f"标定距离: {config.calibration.distance_mm}mm")
    print(f"HSV范围: {config.image_processing.hsv_red1_lower} - {config.image_processing.hsv_red1_upper}")
    print(f"轮廓精度: {config.image_processing.contour_epsilon_factor}")
    print(f"最小面积: {config.image_processing.min_contour_area}")

def show_errors():
    """显示错误统计"""
    stats = get_error_statistics()
    if stats:
        print("\n=== 错误统计 ===")
        for error_type, count in stats.items():
            print(f"{error_type}: {count}次")
    else:
        print("暂无错误记录")

def run_test_mode():
    """运行测试模式"""
    logger = logging.getLogger(__name__)
    logger.info("启动测试模式")
    
    try:
        # 运行单元测试
        import subprocess
        result = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-v"], 
                              capture_output=True, text=True)
        
        print("=== 测试结果 ===")
        print(result.stdout)
        if result.stderr:
            print("错误输出:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except FileNotFoundError:
        print("pytest未安装，无法运行测试")
        return False
    except Exception as e:
        handle_error(ErrorType.UNKNOWN_ERROR, f"测试模式运行失败: {e}")
        return False

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="智能机械臂伤口治疗系统")
    parser.add_argument("--mode", choices=["gui", "cli", "test"], default="gui",
                       help="运行模式: gui(图形界面), cli(命令行), test(测试)")
    parser.add_argument("--config", type=str, help="配置文件路径")
    parser.add_argument("--log-level", choices=["DEBUG", "INFO", "WARNING", "ERROR"], 
                       help="日志级别")
    parser.add_argument("--port", type=str, help="机械臂串口端口")
    parser.add_argument("--baudrate", type=int, help="机械臂波特率")
    
    args = parser.parse_args()
    
    # 设置日志
    logger = setup_logging()
    
    try:
        # 加载配置
        if args.config:
            config_manager.config_file = args.config
            config_manager.load_config()
        
        # 应用命令行参数
        if args.log_level:
            update_config(log_level=args.log_level)
        
        if args.port:
            update_config(robot={'port': args.port})
        
        if args.baudrate:
            update_config(robot={'baudrate': args.baudrate})
        
        # 验证配置
        if not config_manager.validate_config():
            logger.error("配置验证失败")
            return 1
        
        logger.info(f"启动模式: {args.mode}")
        
        # 根据模式运行
        if args.mode == "gui":
            success = run_gui_mode()
        elif args.mode == "cli":
            success = run_cli_mode()
        elif args.mode == "test":
            success = run_test_mode()
        else:
            logger.error(f"未知模式: {args.mode}")
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
        return 0
    except Exception as e:
        logger.error(f"程序运行失败: {e}")
        handle_error(ErrorType.UNKNOWN_ERROR, f"程序运行失败: {e}")
        return 1
    finally:
        # 清理资源
        try:
            from robot_controller_improved import robot_controller
            if robot_controller:
                robot_controller.disconnect()
        except:
            pass

if __name__ == "__main__":
    sys.exit(main())
