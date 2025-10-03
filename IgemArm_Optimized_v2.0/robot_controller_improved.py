"""
改进的机械臂控制器
提供更安全、更可靠的机械臂控制功能
"""
import serial
import time
import json
import threading
import queue
import math
from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
import logging

from config import get_config
from error_handler import handle_error, ErrorType, communication_error_handler, boundary_error_handler
from coordinate_transformer import Point3D, Point2D

logger = logging.getLogger(__name__)

class RobotState(Enum):
    """机械臂状态"""
    DISCONNECTED = "disconnected"
    IDLE = "idle"
    MOVING = "moving"
    CALIBRATING = "calibrating"
    TREATING = "treating"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"

@dataclass
class JointAngles:
    """关节角度"""
    base: float = 0.0
    shoulder: float = 0.0
    elbow: float = 0.0
    wrist: float = 0.0
    roll: float = 0.0
    hand: float = 0.0

@dataclass
class JointLoads:
    """关节负载"""
    base_load: float = 0.0
    shoulder_load: float = 0.0
    elbow_load: float = 0.0
    wrist1_load: float = 0.0
    wrist2_load: float = 0.0

@dataclass
class RobotStatus:
    """机械臂状态信息"""
    current_state: RobotState = RobotState.DISCONNECTED
    current_position: Point3D = None
    current_joint_angles: JointAngles = None
    current_joint_loads: JointLoads = None
    is_connected: bool = False
    error_message: str = ""
    last_update: datetime = None
    
    def __post_init__(self):
        if self.current_position is None:
            self.current_position = Point3D(0, 0, 0)
        if self.current_joint_angles is None:
            self.current_joint_angles = JointAngles()
        if self.current_joint_loads is None:
            self.current_joint_loads = JointLoads()
        if self.last_update is None:
            self.last_update = datetime.now()

class SafetyChecker:
    """安全检查器"""
    
    def __init__(self, workspace_bounds: Dict[str, Tuple[float, float]]):
        self.workspace_bounds = workspace_bounds
        self.max_joint_angles = {
            'base': math.pi,
            'shoulder': math.pi/2,
            'elbow': math.pi,
            'wrist': math.pi,
            'roll': math.pi,
            'hand': math.pi
        }
        self.max_joint_loads = {
            'base_load': 1000,
            'shoulder_load': 1000,
            'elbow_load': 1000,
            'wrist1_load': 500,
            'wrist2_load': 500
        }
    
    def check_position(self, position: Point3D) -> Tuple[bool, str]:
        """检查位置是否安全"""
        x_min, x_max = self.workspace_bounds['x']
        y_min, y_max = self.workspace_bounds['y']
        z_min, z_max = self.workspace_bounds['z']
        
        if not (x_min <= position.x <= x_max):
            return False, f"X坐标 {position.x} 超出范围 [{x_min}, {x_max}]"
        
        if not (y_min <= position.y <= y_max):
            return False, f"Y坐标 {position.y} 超出范围 [{y_min}, {y_max}]"
        
        if not (z_min <= position.z <= z_max):
            return False, f"Z坐标 {position.z} 超出范围 [{z_min}, {z_max}]"
        
        return True, "位置安全"
    
    def check_joint_angles(self, angles: JointAngles) -> Tuple[bool, str]:
        """检查关节角度是否安全"""
        for joint_name, angle in angles.__dict__.items():
            max_angle = self.max_joint_angles.get(joint_name, math.pi)
            if abs(angle) > max_angle:
                return False, f"关节 {joint_name} 角度 {angle} 超出范围 [-{max_angle}, {max_angle}]"
        
        return True, "关节角度安全"
    
    def check_joint_loads(self, loads: JointLoads) -> Tuple[bool, str]:
        """检查关节负载是否安全"""
        for load_name, load_value in loads.__dict__.items():
            max_load = self.max_joint_loads.get(load_name, 1000)
            if abs(load_value) > max_load:
                return False, f"关节 {load_name} 负载 {load_value} 超出范围 [-{max_load}, {max_load}]"
        
        return True, "关节负载安全"
    
    def check_movement_safety(self, start_pos: Point3D, end_pos: Point3D) -> Tuple[bool, str]:
        """检查移动路径是否安全"""
        # 检查起点和终点
        start_safe, start_msg = self.check_position(start_pos)
        if not start_safe:
            return False, f"起点不安全: {start_msg}"
        
        end_safe, end_msg = self.check_position(end_pos)
        if not end_safe:
            return False, f"终点不安全: {end_msg}"
        
        # 检查路径中间点
        distance = start_pos.distance_to(end_pos)
        if distance > 100:  # 如果移动距离超过100mm，检查中间点
            steps = int(distance / 10)  # 每10mm检查一次
            for i in range(1, steps):
                t = i / steps
                intermediate_pos = Point3D(
                    start_pos.x + t * (end_pos.x - start_pos.x),
                    start_pos.y + t * (end_pos.y - start_pos.y),
                    start_pos.z + t * (end_pos.z - start_pos.z)
                )
                safe, msg = self.check_position(intermediate_pos)
                if not safe:
                    return False, f"路径中间点不安全: {msg}"
        
        return True, "移动路径安全"

class ImprovedRobotController:
    """改进的机械臂控制器"""
    
    def __init__(self, port: str = None, baudrate: int = None):
        self.config = get_config()
        self.port = port or self.config.robot.port
        self.baudrate = baudrate or self.config.robot.baudrate
        
        # 串口连接
        self.ser: Optional[serial.Serial] = None
        self.is_connected = False
        
        # 状态管理
        self.status = RobotStatus()
        self.status_lock = threading.Lock()
        
        # 安全检查器
        self.safety_checker = SafetyChecker(self.config.robot.workspace_bounds)
        
        # 数据记录
        self.position_data: List[Dict[str, Any]] = []
        self.data_queue: queue.Queue = queue.Queue()
        self.logging_thread: Optional[threading.Thread] = None
        self.stop_logging_flag = bool = False
        
        # 位置监控
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_monitoring_flag = bool = False
        
        # 运动控制
        self.movement_lock = threading.Lock()
        self.current_movement_id = 0
        
        # 连接机械臂
        self.connect()
        
        # 启动监控
        if self.is_connected:
            self.start_position_monitoring()
            if self.config.enable_logging:
                self.start_logging()
    
    @communication_error_handler({"operation": "connect"})
    def connect(self) -> bool:
        """连接机械臂"""
        try:
            if self.ser and self.ser.is_open:
                self.ser.close()
            
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=self.config.robot.timeout
            )
            
            time.sleep(2)  # 等待串口初始化
            
            # 测试连接
            if self._test_connection():
                self.is_connected = True
                self.status.is_connected = True
                self.status.current_state = RobotState.IDLE
                logger.info(f"机械臂连接成功: {self.ser.name}")
                return True
            else:
                self.is_connected = False
                logger.error("机械臂连接测试失败")
                return False
                
        except Exception as e:
            self.is_connected = False
            handle_error(ErrorType.COMMUNICATION_ERROR, 
                        f"机械臂连接失败: {e}",
                        {"port": self.port, "baudrate": self.baudrate})
            return False
    
    def _test_connection(self) -> bool:
        """测试连接"""
        try:
            # 发送测试命令
            test_command = {"T": 105}  # 获取位置命令
            response = self._send_command(test_command)
            return response is not None
        except:
            return False
    
    @communication_error_handler({"operation": "send_command"})
    def _send_command(self, command: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """发送命令到机械臂"""
        if not self.is_connected or not self.ser:
            raise Exception("机械臂未连接")
        
        command_str = json.dumps(command) + '\n'
        self.ser.write(command_str.encode('utf-8'))
        
        # 读取响应
        response = self.ser.readline().decode().strip()
        if response:
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                logger.warning(f"无法解析响应: {response}")
                return None
        return None
    
    def disconnect(self) -> None:
        """断开连接"""
        self.stop_logging_flag = True
        self.stop_monitoring_flag = True
        
        if self.logging_thread:
            self.logging_thread.join(timeout=2)
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        self.is_connected = False
        self.status.is_connected = False
        self.status.current_state = RobotState.DISCONNECTED
        logger.info("机械臂连接已断开")
    
    @boundary_error_handler({"operation": "move_to_position"})
    def move_to_position(self, x: float, y: float, z: float, 
                        speed: float = None, acceleration: float = None) -> bool:
        """移动到指定位置"""
        if not self.is_connected:
            handle_error(ErrorType.COMMUNICATION_ERROR, "机械臂未连接")
            return False
        
        target_position = Point3D(x, y, z)
        
        # 安全检查
        safe, msg = self.safety_checker.check_position(target_position)
        if not safe:
            handle_error(ErrorType.BOUNDARY_ERROR, msg, {"target_position": target_position})
            return False
        
        # 检查移动路径安全
        current_pos = self.get_current_position()
        if current_pos:
            path_safe, path_msg = self.safety_checker.check_movement_safety(current_pos, target_position)
            if not path_safe:
                handle_error(ErrorType.BOUNDARY_ERROR, path_msg, 
                           {"start_position": current_pos, "target_position": target_position})
                return False
        
        try:
            with self.movement_lock:
                self.status.current_state = RobotState.MOVING
                
                # 使用逆运动学计算关节角度
                from countbyhand import anglecommandgenerator
                command = anglecommandgenerator(x, y, z, 
                                              speed or self.config.robot.default_speed,
                                              acceleration or self.config.robot.default_acceleration)
                
                # 发送命令
                response = self._send_command(command)
                if response:
                    logger.info(f"移动到位置: ({x:.1f}, {y:.1f}, {z:.1f})")
                    return True
                else:
                    logger.error("移动命令执行失败")
                    return False
                    
        except Exception as e:
            handle_error(ErrorType.ROBOT_CONTROL_ERROR, f"移动失败: {e}")
            return False
        finally:
            self.status.current_state = RobotState.IDLE
    
    def move_to_position_smooth(self, x: float, y: float, z: float, 
                               steps: int = 10, speed: float = None) -> bool:
        """平滑移动到指定位置"""
        current_pos = self.get_current_position()
        if not current_pos:
            return False
        
        target_pos = Point3D(x, y, z)
        
        # 生成中间点
        for i in range(1, steps + 1):
            t = i / steps
            intermediate_pos = Point3D(
                current_pos.x + t * (target_pos.x - current_pos.x),
                current_pos.y + t * (target_pos.y - current_pos.y),
                current_pos.z + t * (target_pos.z - current_pos.z)
            )
            
            # 移动到中间点
            success = self.move_to_position(
                intermediate_pos.x, intermediate_pos.y, intermediate_pos.z, speed
            )
            if not success:
                return False
            
            # 等待移动完成
            time.sleep(0.1)
        
        return True
    
    def get_current_position(self) -> Optional[Point3D]:
        """获取当前位置"""
        try:
            command = {"T": 105}
            response = self._send_command(command)
            if response and 'x' in response and 'y' in response and 'z' in response:
                return Point3D(response['x'], response['y'], response['z'])
        except Exception as e:
            logger.error(f"获取位置失败: {e}")
        return None
    
    def get_current_status(self) -> RobotStatus:
        """获取当前状态"""
        with self.status_lock:
            return self.status
    
    def emergency_stop(self) -> None:
        """紧急停止"""
        logger.warning("执行紧急停止")
        self.status.current_state = RobotState.EMERGENCY_STOP
        
        try:
            # 发送紧急停止命令
            stop_command = {"T": 999}  # 假设999是紧急停止命令
            self._send_command(stop_command)
        except Exception as e:
            logger.error(f"紧急停止命令发送失败: {e}")
    
    def set_pid_parameters(self, p: float = None, i: float = None) -> bool:
        """设置PID参数"""
        try:
            p = p or self.config.robot.pid_p
            i = i or self.config.robot.pid_i
            
            for joint_id in range(1, 7):
                command = {"T": 108, "joint": joint_id, "p": p, "i": i}
                self._send_command(command)
            
            logger.info(f"PID参数已设置: P={p}, I={i}")
            return True
        except Exception as e:
            handle_error(ErrorType.ROBOT_CONTROL_ERROR, f"设置PID参数失败: {e}")
            return False
    
    def start_logging(self) -> None:
        """启动数据记录"""
        if self.logging_thread and self.logging_thread.is_alive():
            return
        
        self.stop_logging_flag = False
        self.logging_thread = threading.Thread(target=self._logging_worker)
        self.logging_thread.daemon = True
        self.logging_thread.start()
        logger.info("数据记录已启动")
    
    def stop_logging(self) -> None:
        """停止数据记录"""
        self.stop_logging_flag = True
        if self.logging_thread:
            self.logging_thread.join(timeout=2)
        logger.info("数据记录已停止")
    
    def _logging_worker(self) -> None:
        """数据记录工作线程"""
        while not self.stop_logging_flag:
            try:
                current_pos = self.get_current_position()
                if current_pos:
                    timestamp = datetime.now()
                    data_point = {
                        'timestamp': timestamp,
                        'x': current_pos.x,
                        'y': current_pos.y,
                        'z': current_pos.z,
                        'state': self.status.current_state.value
                    }
                    self.position_data.append(data_point)
                time.sleep(0.02)  # 50Hz采样率
            except Exception as e:
                logger.error(f"数据记录错误: {e}")
                time.sleep(0.1)
    
    def start_position_monitoring(self) -> None:
        """启动位置监控"""
        if self.monitor_thread and self.monitor_thread.is_alive():
            return
        
        self.stop_monitoring_flag = False
        self.monitor_thread = threading.Thread(target=self._position_monitor_worker)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        logger.info("位置监控已启动")
    
    def stop_position_monitoring(self) -> None:
        """停止位置监控"""
        self.stop_monitoring_flag = True
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        logger.info("位置监控已停止")
    
    def _position_monitor_worker(self) -> None:
        """位置监控工作线程"""
        while not self.stop_monitoring_flag:
            try:
                if self.ser and self.ser.in_waiting > 0:
                    response = self.ser.readline().decode().strip()
                    if response:
                        try:
                            data = json.loads(response)
                            self._update_status_from_data(data)
                        except json.JSONDecodeError:
                            pass
                time.sleep(0.01)  # 100Hz监控频率
            except Exception as e:
                logger.error(f"位置监控错误: {e}")
                time.sleep(0.1)
    
    def _update_status_from_data(self, data: Dict[str, Any]) -> None:
        """从数据更新状态"""
        with self.status_lock:
            if data.get('T') == 1051:  # 位置反馈数据
                self.status.current_position = Point3D(
                    data.get('x', 0),
                    data.get('y', 0),
                    data.get('z', 0)
                )
                self.status.current_joint_angles = JointAngles(
                    base=data.get('b', 0),
                    shoulder=data.get('s', 0),
                    elbow=data.get('e', 0),
                    wrist=data.get('t', 0),
                    roll=data.get('r', 0),
                    hand=data.get('g', 0)
                )
                self.status.current_joint_loads = JointLoads(
                    base_load=data.get('tB', 0),
                    shoulder_load=data.get('tS', 0),
                    elbow_load=data.get('tE', 0),
                    wrist1_load=data.get('tT', 0),
                    wrist2_load=data.get('tR', 0)
                )
                self.status.last_update = datetime.now()
    
    def save_position_data(self, filename: str = None) -> Optional[str]:
        """保存位置数据"""
        if not filename:
            filename = f"arm_position_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if not self.position_data:
            logger.warning("没有数据可保存")
            return None
        
        try:
            import pandas as pd
            df = pd.DataFrame(self.position_data)
            df.to_csv(filename, index=False)
            logger.info(f"位置数据已保存到: {filename}")
            return filename
        except Exception as e:
            logger.error(f"保存数据失败: {e}")
            return None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

# 全局机械臂控制器实例
robot_controller = None

def get_robot_controller(port: str = None, baudrate: int = None) -> ImprovedRobotController:
    """获取全局机械臂控制器"""
    global robot_controller
    if robot_controller is None:
        robot_controller = ImprovedRobotController(port, baudrate)
    return robot_controller

if __name__ == "__main__":
    # 测试机械臂控制器
    with ImprovedRobotController() as arm:
        if arm.is_connected:
            print("机械臂连接成功")
            
            # 获取当前位置
            pos = arm.get_current_position()
            print(f"当前位置: {pos}")
            
            # 移动到安全位置
            arm.move_to_position(175, 0, 75)
            time.sleep(2)
            
            # 平滑移动
            arm.move_to_position_smooth(200, 0, 100, steps=5)
            
            print("测试完成")
        else:
            print("机械臂连接失败")
