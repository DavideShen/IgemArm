"""
配置管理系统
统一管理所有系统参数，支持运行时调整和持久化存储
"""
import json
import os
from typing import Dict, Any, Tuple
from dataclasses import dataclass, asdict
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class CameraConfig:
    """摄像头配置"""
    offset_x: float = 55.0
    offset_y: float = -30.0
    nozzle_height: float = 95.0
    device_id: int = 0
    resolution: Tuple[int, int] = (640, 480)
    fps: int = 30

@dataclass
class ImageProcessingConfig:
    """图像处理配置"""
    # HSV红色检测范围
    hsv_red1_lower: Tuple[int, int, int] = (0, 70, 50)
    hsv_red1_upper: Tuple[int, int, int] = (10, 255, 255)
    hsv_red2_lower: Tuple[int, int, int] = (170, 70, 50)
    hsv_red2_upper: Tuple[int, int, int] = (180, 255, 255)
    
    # 轮廓检测参数
    contour_epsilon_factor: float = 0.002
    min_contour_area: int = 100
    
    # 图像预处理
    gaussian_blur_kernel: Tuple[int, int] = (3, 3)
    clahe_clip_limit: float = 1.5
    clahe_tile_grid_size: Tuple[int, int] = (8, 8)

@dataclass
class CalibrationConfig:
    """标定配置"""
    distance_mm: float = 40.0
    max_attempts: int = 5
    min_successful: int = 3
    min_pixel_distance: float = 10.0
    max_pixel_distance: float = 200.0
    stability_checks: int = 3
    max_cv_threshold: float = 0.1  # 变异系数阈值

@dataclass
class RobotConfig:
    """机械臂配置"""
    port: str = 'COM3'
    baudrate: int = 115200
    timeout: float = 1.0
    
    # PID参数
    pid_p: float = 8.0
    pid_i: float = 0.0
    
    # 运动参数
    default_speed: float = 0.08
    default_acceleration: float = 10.0
    
    # 工作空间边界 (mm)
    workspace_bounds: Dict[str, Tuple[float, float]] = None
    
    def __post_init__(self):
        if self.workspace_bounds is None:
            self.workspace_bounds = {
                'x': (-200, 400),
                'y': (-200, 200),
                'z': (50, 300)
            }

@dataclass
class TreatmentConfig:
    """治疗配置"""
    movement_speed: float = 50.0  # mm/s
    treatment_time: float = 0.5   # 秒
    radius_step: float = 5.0      # 半径检测步长
    min_treatment_distance: float = 1.0  # 最小治疗距离

@dataclass
class SystemConfig:
    """系统配置"""
    camera: CameraConfig = None
    image_processing: ImageProcessingConfig = None
    calibration: CalibrationConfig = None
    robot: RobotConfig = None
    treatment: TreatmentConfig = None
    
    # 系统参数
    log_level: str = 'INFO'
    enable_logging: bool = True
    data_save_path: str = './data'
    
    def __post_init__(self):
        if self.camera is None:
            self.camera = CameraConfig()
        if self.image_processing is None:
            self.image_processing = ImageProcessingConfig()
        if self.calibration is None:
            self.calibration = CalibrationConfig()
        if self.robot is None:
            self.robot = RobotConfig()
        if self.treatment is None:
            self.treatment = TreatmentConfig()

class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = SystemConfig()
        self.load_config()
    
    def load_config(self) -> None:
        """从文件加载配置"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._update_config_from_dict(config_data)
                logger.info(f"配置已从 {self.config_file} 加载")
            else:
                logger.info("使用默认配置")
                self.save_config()
        except Exception as e:
            logger.error(f"加载配置失败: {e}")
            logger.info("使用默认配置")
    
    def save_config(self) -> None:
        """保存配置到文件"""
        try:
            config_dict = self._config_to_dict()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=4, ensure_ascii=False)
            logger.info(f"配置已保存到 {self.config_file}")
        except Exception as e:
            logger.error(f"保存配置失败: {e}")
    
    def _config_to_dict(self) -> Dict[str, Any]:
        """将配置对象转换为字典"""
        return asdict(self.config)
    
    def _update_config_from_dict(self, config_data: Dict[str, Any]) -> None:
        """从字典更新配置对象"""
        try:
            # 更新摄像头配置
            if 'camera' in config_data:
                camera_data = config_data['camera']
                self.config.camera = CameraConfig(**camera_data)
            
            # 更新图像处理配置
            if 'image_processing' in config_data:
                img_data = config_data['image_processing']
                self.config.image_processing = ImageProcessingConfig(**img_data)
            
            # 更新标定配置
            if 'calibration' in config_data:
                calib_data = config_data['calibration']
                self.config.calibration = CalibrationConfig(**calib_data)
            
            # 更新机械臂配置
            if 'robot' in config_data:
                robot_data = config_data['robot']
                self.config.robot = RobotConfig(**robot_data)
            
            # 更新治疗配置
            if 'treatment' in config_data:
                treat_data = config_data['treatment']
                self.config.treatment = TreatmentConfig(**treat_data)
            
            # 更新系统参数
            if 'log_level' in config_data:
                self.config.log_level = config_data['log_level']
            if 'enable_logging' in config_data:
                self.config.enable_logging = config_data['enable_logging']
            if 'data_save_path' in config_data:
                self.config.data_save_path = config_data['data_save_path']
                
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
            raise
    
    def get_config(self) -> SystemConfig:
        """获取当前配置"""
        return self.config
    
    def update_config(self, **kwargs) -> None:
        """更新配置参数"""
        try:
            for key, value in kwargs.items():
                if hasattr(self.config, key):
                    setattr(self.config, key, value)
                else:
                    logger.warning(f"未知配置参数: {key}")
            self.save_config()
            logger.info("配置已更新")
        except Exception as e:
            logger.error(f"更新配置失败: {e}")
    
    def reset_to_default(self) -> None:
        """重置为默认配置"""
        self.config = SystemConfig()
        self.save_config()
        logger.info("配置已重置为默认值")
    
    def validate_config(self) -> bool:
        """验证配置有效性"""
        try:
            # 验证摄像头配置
            if self.config.camera.device_id < 0:
                logger.error("摄像头设备ID不能为负数")
                return False
            
            # 验证机械臂配置
            if self.config.robot.baudrate <= 0:
                logger.error("波特率必须大于0")
                return False
            
            # 验证标定配置
            if self.config.calibration.distance_mm <= 0:
                logger.error("标定距离必须大于0")
                return False
            
            # 验证工作空间边界
            bounds = self.config.robot.workspace_bounds
            for axis, (min_val, max_val) in bounds.items():
                if min_val >= max_val:
                    logger.error(f"{axis}轴边界值无效: {min_val} >= {max_val}")
                    return False
            
            logger.info("配置验证通过")
            return True
            
        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False

# 全局配置管理器实例
config_manager = ConfigManager()

def get_config() -> SystemConfig:
    """获取全局配置"""
    return config_manager.get_config()

def update_config(**kwargs) -> None:
    """更新全局配置"""
    config_manager.update_config(**kwargs)

def save_config() -> None:
    """保存全局配置"""
    config_manager.save_config()

def load_config() -> None:
    """重新加载全局配置"""
    config_manager.load_config()

if __name__ == "__main__":
    # 测试配置管理器
    config = get_config()
    print("当前配置:")
    print(f"摄像头偏移: ({config.camera.offset_x}, {config.camera.offset_y})")
    print(f"机械臂端口: {config.robot.port}")
    print(f"标定距离: {config.calibration.distance_mm}mm")
    
    # 测试配置更新
    update_config(log_level='DEBUG')
    print("配置更新完成")
