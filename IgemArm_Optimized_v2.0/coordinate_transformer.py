"""
坐标转换模块
提供高精度的像素坐标到物理坐标转换功能
"""
import math
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging
from config import get_config
from error_handler import handle_error, ErrorType, image_processing_error_handler

logger = logging.getLogger(__name__)

@dataclass
class Point2D:
    """2D点"""
    x: float
    y: float
    
    def distance_to(self, other: 'Point2D') -> float:
        """计算到另一点的距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def __add__(self, other: 'Point2D') -> 'Point2D':
        """点加法"""
        return Point2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other: 'Point2D') -> 'Point2D':
        """点减法"""
        return Point2D(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar: float) -> 'Point2D':
        """标量乘法"""
        return Point2D(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar: float) -> 'Point2D':
        """标量除法"""
        return Point2D(self.x / scalar, self.y / scalar)

@dataclass
class Point3D:
    """3D点"""
    x: float
    y: float
    z: float
    
    def distance_to(self, other: 'Point3D') -> float:
        """计算到另一点的距离"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2 + (self.z - other.z)**2)

@dataclass
class CalibrationData:
    """标定数据"""
    scale_factor: float  # 像素到毫米的比例因子
    rotation_angle: float  # 旋转角度（弧度）
    translation_offset: Point2D  # 平移偏移
    confidence: float  # 标定置信度 (0-1)
    timestamp: float  # 标定时间戳
    
    def is_valid(self) -> bool:
        """检查标定数据是否有效"""
        return (self.scale_factor > 0 and 
                self.confidence > 0.5 and 
                abs(self.rotation_angle) < math.pi)

class CoordinateTransformer:
    """坐标转换器"""
    
    def __init__(self):
        self.config = get_config()
        self.calibration_data: Optional[CalibrationData] = None
        self.image_center: Optional[Point2D] = None
        self.workspace_bounds = self.config.robot.workspace_bounds
        
    def set_image_center(self, width: int, height: int) -> None:
        """设置图像中心"""
        self.image_center = Point2D(width / 2, height / 2)
        logger.info(f"图像中心设置为: ({self.image_center.x}, {self.image_center.y})")
    
    def set_calibration_data(self, calibration_data: CalibrationData) -> None:
        """设置标定数据"""
        if not calibration_data.is_valid():
            handle_error(ErrorType.CALIBRATION_ERROR, 
                        "标定数据无效", 
                        {"calibration_data": calibration_data})
            return
        
        self.calibration_data = calibration_data
        logger.info(f"标定数据已设置: 比例={calibration_data.scale_factor:.4f}, "
                   f"置信度={calibration_data.confidence:.2f}")
    
    def pixel_to_physical(self, pixel_point: Point2D) -> Point3D:
        """将像素坐标转换为物理坐标"""
        if not self.calibration_data:
            handle_error(ErrorType.CALIBRATION_ERROR, 
                        "未进行标定，无法转换坐标")
            return Point3D(0, 0, 0)
        
        if not self.image_center:
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, 
                        "图像中心未设置")
            return Point3D(0, 0, 0)
        
        try:
            # 1. 转换为相对于图像中心的坐标
            relative_point = pixel_point - self.image_center
            
            # 2. Y轴翻转（图像Y轴向下，机械臂Y轴向上）
            relative_point = Point2D(relative_point.x, -relative_point.y)
            
            # 3. 旋转变换
            rotated_point = self._rotate_point(relative_point, self.calibration_data.rotation_angle)
            
            # 4. 缩放变换
            scaled_point = rotated_point * self.calibration_data.scale_factor
            
            # 5. 平移变换
            physical_point = scaled_point + self.calibration_data.translation_offset
            
            # 6. 添加Z坐标（喷嘴高度）
            z_coord = self.config.camera.nozzle_height
            
            result = Point3D(physical_point.x, physical_point.y, z_coord)
            
            # 7. 边界检查
            if not self._is_within_bounds(result):
                handle_error(ErrorType.BOUNDARY_ERROR, 
                            "转换后的坐标超出工作空间边界",
                            {"point": result, "bounds": self.workspace_bounds})
            
            return result
            
        except Exception as e:
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, 
                        f"坐标转换失败: {e}",
                        {"pixel_point": pixel_point})
            return Point3D(0, 0, 0)
    
    def physical_to_pixel(self, physical_point: Point3D) -> Point2D:
        """将物理坐标转换为像素坐标（逆变换）"""
        if not self.calibration_data or not self.image_center:
            handle_error(ErrorType.CALIBRATION_ERROR, 
                        "标定数据或图像中心未设置")
            return Point2D(0, 0)
        
        try:
            # 1. 移除Z坐标，只考虑X、Y
            physical_2d = Point2D(physical_point.x, physical_point.y)
            
            # 2. 反向平移
            translated_point = physical_2d - self.calibration_data.translation_offset
            
            # 3. 反向缩放
            scaled_point = translated_point / self.calibration_data.scale_factor
            
            # 4. 反向旋转
            rotated_point = self._rotate_point(scaled_point, -self.calibration_data.rotation_angle)
            
            # 5. Y轴翻转
            flipped_point = Point2D(rotated_point.x, -rotated_point.y)
            
            # 6. 转换回绝对像素坐标
            pixel_point = flipped_point + self.image_center
            
            return pixel_point
            
        except Exception as e:
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, 
                        f"逆坐标转换失败: {e}",
                        {"physical_point": physical_point})
            return Point2D(0, 0)
    
    def _rotate_point(self, point: Point2D, angle: float) -> Point2D:
        """旋转点"""
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        
        new_x = point.x * cos_angle + point.y * sin_angle
        new_y = -point.x * sin_angle + point.y * cos_angle
        
        return Point2D(new_x, new_y)
    
    def _is_within_bounds(self, point: Point3D) -> bool:
        """检查点是否在工作空间边界内"""
        x_min, x_max = self.workspace_bounds['x']
        y_min, y_max = self.workspace_bounds['y']
        z_min, z_max = self.workspace_bounds['z']
        
        return (x_min <= point.x <= x_max and
                y_min <= point.y <= y_max and
                z_min <= point.z <= z_max)
    
    def batch_transform(self, pixel_points: List[Point2D]) -> List[Point3D]:
        """批量转换坐标"""
        if not pixel_points:
            return []
        
        physical_points = []
        for pixel_point in pixel_points:
            physical_point = self.pixel_to_physical(pixel_point)
            physical_points.append(physical_point)
        
        logger.info(f"批量转换完成: {len(pixel_points)} 个点")
        return physical_points
    
    def validate_transformation(self, pixel_points: List[Point2D], 
                              physical_points: List[Point3D]) -> Dict[str, float]:
        """验证转换精度"""
        if len(pixel_points) != len(physical_points):
            return {"error": "点数量不匹配"}
        
        errors = []
        for i, (pixel, physical) in enumerate(zip(pixel_points, physical_points)):
            # 转换回像素坐标
            back_pixel = self.physical_to_pixel(physical)
            error = pixel.distance_to(back_pixel)
            errors.append(error)
        
        mean_error = np.mean(errors)
        max_error = np.max(errors)
        std_error = np.std(errors)
        
        result = {
            "mean_error_pixels": mean_error,
            "max_error_pixels": max_error,
            "std_error_pixels": std_error,
            "mean_error_mm": mean_error * (self.calibration_data.scale_factor if self.calibration_data else 0),
            "is_accurate": mean_error < 2.0  # 平均误差小于2像素认为准确
        }
        
        logger.info(f"转换精度验证: 平均误差={mean_error:.2f}像素, "
                   f"最大误差={max_error:.2f}像素")
        
        return result
    
    def get_transformation_matrix(self) -> np.ndarray:
        """获取变换矩阵"""
        if not self.calibration_data:
            return np.eye(3)
        
        cos_angle = math.cos(self.calibration_data.rotation_angle)
        sin_angle = math.sin(self.calibration_data.rotation_angle)
        scale = self.calibration_data.scale_factor
        
        # 组合变换矩阵: T = S * R * T
        matrix = np.array([
            [scale * cos_angle, -scale * sin_angle, self.calibration_data.translation_offset.x],
            [scale * sin_angle,  scale * cos_angle, self.calibration_data.translation_offset.y],
            [0,                  0,                 1]
        ])
        
        return matrix

class CalibrationManager:
    """标定管理器"""
    
    def __init__(self, transformer: CoordinateTransformer):
        self.transformer = transformer
        self.config = get_config()
        self.calibration_points: List[Tuple[Point2D, Point3D]] = []
    
    def add_calibration_point(self, pixel_point: Point2D, physical_point: Point3D) -> None:
        """添加标定点"""
        self.calibration_points.append((pixel_point, physical_point))
        logger.info(f"添加标定点: 像素({pixel_point.x:.1f}, {pixel_point.y:.1f}) -> "
                   f"物理({physical_point.x:.1f}, {physical_point.y:.1f})")
    
    def perform_calibration(self) -> CalibrationData:
        """执行标定"""
        if len(self.calibration_points) < 2:
            handle_error(ErrorType.CALIBRATION_ERROR, 
                        "标定点数量不足，至少需要2个点")
            return None
        
        try:
            # 使用最小二乘法计算变换参数
            calibration_data = self._calculate_transformation()
            
            if calibration_data and calibration_data.is_valid():
                self.transformer.set_calibration_data(calibration_data)
                logger.info("标定完成")
                return calibration_data
            else:
                handle_error(ErrorType.CALIBRATION_ERROR, 
                            "标定失败，数据质量不足")
                return None
                
        except Exception as e:
            handle_error(ErrorType.CALIBRATION_ERROR, 
                        f"标定过程异常: {e}")
            return None
    
    def _calculate_transformation(self) -> CalibrationData:
        """计算变换参数"""
        # 提取像素和物理坐标
        pixel_coords = np.array([(p.x, p.y) for p, _ in self.calibration_points])
        physical_coords = np.array([(p.x, p.y) for _, p in self.calibration_points])
        
        # 计算中心点
        pixel_center = np.mean(pixel_coords, axis=0)
        physical_center = np.mean(physical_coords, axis=0)
        
        # 去中心化
        pixel_centered = pixel_coords - pixel_center
        physical_centered = physical_coords - physical_center
        
        # 计算旋转角度
        angle = self._calculate_rotation_angle(pixel_centered, physical_centered)
        
        # 计算缩放因子
        scale = self._calculate_scale_factor(pixel_centered, physical_centered, angle)
        
        # 计算平移偏移
        translation = physical_center - scale * self._rotate_points(pixel_center, angle)
        
        # 计算置信度
        confidence = self._calculate_confidence(pixel_coords, physical_coords, 
                                              scale, angle, translation)
        
        return CalibrationData(
            scale_factor=scale,
            rotation_angle=angle,
            translation_offset=Point2D(translation[0], translation[1]),
            confidence=confidence,
            timestamp=time.time()
        )
    
    def _calculate_rotation_angle(self, pixel_coords: np.ndarray, 
                                 physical_coords: np.ndarray) -> float:
        """计算旋转角度"""
        # 使用SVD分解计算最优旋转
        H = pixel_coords.T @ physical_coords
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T
        
        # 确保是旋转矩阵（行列式为1）
        if np.linalg.det(R) < 0:
            Vt[-1, :] *= -1
            R = Vt.T @ U.T
        
        # 提取旋转角度
        angle = math.atan2(R[1, 0], R[0, 0])
        return angle
    
    def _calculate_scale_factor(self, pixel_coords: np.ndarray, 
                               physical_coords: np.ndarray, angle: float) -> float:
        """计算缩放因子"""
        # 旋转像素坐标
        rotated_pixel = self._rotate_points(pixel_coords, angle)
        
        # 计算缩放因子
        pixel_norm = np.linalg.norm(rotated_pixel, axis=1)
        physical_norm = np.linalg.norm(physical_coords, axis=1)
        
        # 避免除零
        valid_indices = pixel_norm > 1e-6
        if not np.any(valid_indices):
            return 1.0
        
        scale_factors = physical_norm[valid_indices] / pixel_norm[valid_indices]
        return np.median(scale_factors)  # 使用中位数更鲁棒
    
    def _rotate_points(self, points: np.ndarray, angle: float) -> np.ndarray:
        """旋转点集"""
        cos_angle = math.cos(angle)
        sin_angle = math.sin(angle)
        rotation_matrix = np.array([[cos_angle, -sin_angle], 
                                   [sin_angle, cos_angle]])
        return points @ rotation_matrix.T
    
    def _calculate_confidence(self, pixel_coords: np.ndarray, 
                            physical_coords: np.ndarray, scale: float, 
                            angle: float, translation: np.ndarray) -> float:
        """计算标定置信度"""
        # 应用变换
        rotated_pixel = self._rotate_points(pixel_coords, angle)
        transformed_pixel = scale * rotated_pixel + translation
        
        # 计算误差
        errors = np.linalg.norm(transformed_pixel - physical_coords, axis=1)
        mean_error = np.mean(errors)
        max_error = np.max(errors)
        
        # 基于误差计算置信度
        confidence = max(0, 1 - mean_error / 10)  # 10mm误差对应0置信度
        confidence = min(confidence, 1 - max_error / 50)  # 50mm最大误差
        
        return confidence

# 全局坐标转换器实例
coordinate_transformer = CoordinateTransformer()

def get_coordinate_transformer() -> CoordinateTransformer:
    """获取全局坐标转换器"""
    return coordinate_transformer

if __name__ == "__main__":
    # 测试坐标转换
    transformer = CoordinateTransformer()
    
    # 设置图像中心
    transformer.set_image_center(640, 480)
    
    # 创建测试标定数据
    calibration_data = CalibrationData(
        scale_factor=0.1,  # 0.1 mm/pixel
        rotation_angle=0,
        translation_offset=Point2D(100, 50),
        confidence=0.9,
        timestamp=time.time()
    )
    
    transformer.set_calibration_data(calibration_data)
    
    # 测试转换
    pixel_point = Point2D(320, 240)  # 图像中心
    physical_point = transformer.pixel_to_physical(pixel_point)
    print(f"像素坐标 {pixel_point} -> 物理坐标 {physical_point}")
    
    # 测试逆转换
    back_pixel = transformer.physical_to_pixel(physical_point)
    print(f"物理坐标 {physical_point} -> 像素坐标 {back_pixel}")
