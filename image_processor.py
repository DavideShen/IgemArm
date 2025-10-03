"""
改进的图像处理模块
提供更稳定、更准确的伤口检测和图像处理功能
"""
import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import logging
import time
from config import get_config
from error_handler import handle_error, ErrorType, image_processing_error_handler
from coordinate_transformer import Point2D

logger = logging.getLogger(__name__)

@dataclass
class ContourInfo:
    """轮廓信息"""
    points: List[Point2D]
    center: Point2D
    area: float
    perimeter: float
    bounding_rect: Tuple[int, int, int, int]  # (x, y, w, h)
    confidence: float  # 检测置信度

@dataclass
class DetectionResult:
    """检测结果"""
    success: bool
    contours: List[ContourInfo]
    processing_time: float
    image_center: Point2D
    error_message: str = ""

class ImagePreprocessor:
    """图像预处理器"""
    
    def __init__(self):
        self.config = get_config()
    
    @image_processing_error_handler({"operation": "preprocess"})
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """图像预处理"""
        try:
            # 1. 高斯模糊去噪
            blurred = cv2.GaussianBlur(image, self.config.image_processing.gaussian_blur_kernel, 0)
            
            # 2. 转换到LAB颜色空间进行对比度增强
            lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            
            # 3. CLAHE对比度限制自适应直方图均衡化
            clahe = cv2.createCLAHE(
                clipLimit=self.config.image_processing.clahe_clip_limit,
                tileGridSize=self.config.image_processing.clahe_tile_grid_size
            )
            l = clahe.apply(l)
            
            # 4. 合并通道并转换回BGR
            enhanced = cv2.merge([l, a, b])
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)
            
            return enhanced
            
        except Exception as e:
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, f"图像预处理失败: {e}")
            return image
    
    def enhance_red_detection(self, image: np.ndarray) -> np.ndarray:
        """增强红色检测"""
        try:
            # 转换到HSV颜色空间
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            
            # 创建红色掩膜
            mask = self._create_red_mask(hsv)
            
            # 形态学处理
            mask = self._morphological_processing(mask)
            
            # 应用掩膜
            result = cv2.bitwise_and(image, image, mask=mask)
            
            return result
            
        except Exception as e:
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, f"红色检测增强失败: {e}")
            return image
    
    def _create_red_mask(self, hsv: np.ndarray) -> np.ndarray:
        """创建红色掩膜"""
        # 获取配置中的HSV范围
        red1_lower = np.array(self.config.image_processing.hsv_red1_lower)
        red1_upper = np.array(self.config.image_processing.hsv_red1_upper)
        red2_lower = np.array(self.config.image_processing.hsv_red2_lower)
        red2_upper = np.array(self.config.image_processing.hsv_red2_upper)
        
        # 创建两个红色区间掩膜
        mask1 = cv2.inRange(hsv, red1_lower, red1_upper)
        mask2 = cv2.inRange(hsv, red2_lower, red2_upper)
        
        # 合并掩膜
        combined_mask = cv2.bitwise_or(mask1, mask2)
        
        return combined_mask
    
    def _morphological_processing(self, mask: np.ndarray) -> np.ndarray:
        """形态学处理"""
        # 开运算去除噪声
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
        
        # 闭运算填充空洞
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
        
        return mask

class ContourDetector:
    """轮廓检测器"""
    
    def __init__(self):
        self.config = get_config()
    
    @image_processing_error_handler({"operation": "detect_contours"})
    def detect_contours(self, image: np.ndarray) -> List[ContourInfo]:
        """检测轮廓"""
        try:
            # 预处理图像
            preprocessor = ImagePreprocessor()
            processed_image = preprocessor.preprocess(image)
            
            # 创建红色掩膜
            hsv = cv2.cvtColor(processed_image, cv2.COLOR_BGR2HSV)
            mask = preprocessor._create_red_mask(hsv)
            mask = preprocessor._morphological_processing(mask)
            
            # 查找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            if not contours:
                return []
            
            # 过滤轮廓
            valid_contours = self._filter_contours(contours)
            
            # 转换为ContourInfo对象
            contour_infos = []
            for contour in valid_contours:
                contour_info = self._contour_to_info(contour, image.shape)
                if contour_info:
                    contour_infos.append(contour_info)
            
            # 按面积排序
            contour_infos.sort(key=lambda x: x.area, reverse=True)
            
            return contour_infos
            
        except Exception as e:
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, f"轮廓检测失败: {e}")
            return []
    
    def _filter_contours(self, contours: List[np.ndarray]) -> List[np.ndarray]:
        """过滤轮廓"""
        valid_contours = []
        min_area = self.config.image_processing.min_contour_area
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > min_area:
                valid_contours.append(contour)
        
        return valid_contours
    
    def _contour_to_info(self, contour: np.ndarray, image_shape: Tuple[int, int, int]) -> Optional[ContourInfo]:
        """将轮廓转换为ContourInfo对象"""
        try:
            # 计算轮廓属性
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            # 多边形近似
            epsilon = self.config.image_processing.contour_epsilon_factor * perimeter
            approx_points = cv2.approxPolyDP(contour, epsilon, True)
            
            # 转换为Point2D列表
            h, w = image_shape[:2]
            image_center = Point2D(w // 2, h // 2)
            
            points = []
            for point in approx_points:
                pixel_point = Point2D(point[0][0], point[0][1])
                # 转换为相对于图像中心的坐标
                relative_point = pixel_point - image_center
                points.append(relative_point)
            
            # 计算质心
            if points:
                center_x = sum(p.x for p in points) / len(points)
                center_y = sum(p.y for p in points) / len(points)
                center = Point2D(center_x, center_y)
            else:
                center = Point2D(0, 0)
            
            # 计算边界矩形
            x, y, w, h = cv2.boundingRect(contour)
            bounding_rect = (x, y, w, h)
            
            # 计算置信度
            confidence = self._calculate_confidence(contour, area, perimeter)
            
            return ContourInfo(
                points=points,
                center=center,
                area=area,
                perimeter=perimeter,
                bounding_rect=bounding_rect,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"轮廓转换失败: {e}")
            return None
    
    def _calculate_confidence(self, contour: np.ndarray, area: float, perimeter: float) -> float:
        """计算检测置信度"""
        try:
            # 基于轮廓的紧凑性计算置信度
            if perimeter > 0:
                compactness = 4 * np.pi * area / (perimeter * perimeter)
            else:
                compactness = 0
            
            # 基于面积计算置信度
            area_confidence = min(area / 1000, 1.0)  # 面积越大置信度越高，最大1.0
            
            # 综合置信度
            confidence = (compactness * 0.3 + area_confidence * 0.7)
            
            return max(0, min(1, confidence))
            
        except Exception as e:
            logger.error(f"置信度计算失败: {e}")
            return 0.5

class WoundDetector:
    """伤口检测器"""
    
    def __init__(self):
        self.config = get_config()
        self.contour_detector = ContourDetector()
        self.preprocessor = ImagePreprocessor()
    
    @image_processing_error_handler({"operation": "detect_wound"})
    def detect_wound(self, image: np.ndarray) -> DetectionResult:
        """检测伤口"""
        start_time = time.time()
        
        try:
            # 获取图像中心
            h, w = image.shape[:2]
            image_center = Point2D(w // 2, h // 2)
            
            # 检测轮廓
            contours = self.contour_detector.detect_contours(image)
            
            if not contours:
                return DetectionResult(
                    success=False,
                    contours=[],
                    processing_time=time.time() - start_time,
                    image_center=image_center,
                    error_message="未检测到轮廓"
                )
            
            # 选择最佳轮廓（面积最大且置信度最高）
            best_contour = self._select_best_contour(contours)
            
            processing_time = time.time() - start_time
            
            return DetectionResult(
                success=True,
                contours=[best_contour] if best_contour else [],
                processing_time=processing_time,
                image_center=image_center
            )
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"伤口检测失败: {e}"
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, error_msg)
            
            return DetectionResult(
                success=False,
                contours=[],
                processing_time=processing_time,
                image_center=Point2D(0, 0),
                error_message=error_msg
            )
    
    def _select_best_contour(self, contours: List[ContourInfo]) -> Optional[ContourInfo]:
        """选择最佳轮廓"""
        if not contours:
            return None
        
        # 按面积和置信度综合评分
        best_contour = None
        best_score = 0
        
        for contour in contours:
            # 综合评分：面积权重0.6，置信度权重0.4
            score = contour.area * 0.6 + contour.confidence * 1000 * 0.4
            
            if score > best_score:
                best_score = score
                best_contour = contour
        
        return best_contour
    
    def detect_wound_stable(self, image: np.ndarray, num_checks: int = 3) -> DetectionResult:
        """稳定检测伤口（多次检测取平均）"""
        if num_checks < 1:
            num_checks = 1
        
        detection_results = []
        
        for i in range(num_checks):
            result = self.detect_wound(image)
            detection_results.append(result)
            
            if i < num_checks - 1:
                time.sleep(0.1)  # 短暂等待
        
        # 选择成功的结果
        successful_results = [r for r in detection_results if r.success]
        
        if not successful_results:
            # 所有检测都失败，返回最后一个结果
            return detection_results[-1]
        
        if len(successful_results) == 1:
            return successful_results[0]
        
        # 多个成功结果，计算平均中心点
        centers = [r.contours[0].center for r in successful_results if r.contours]
        if centers:
            avg_center = Point2D(
                sum(c.x for c in centers) / len(centers),
                sum(c.y for c in centers) / len(centers)
            )
            
            # 选择最接近平均中心的轮廓
            best_result = min(successful_results, 
                            key=lambda r: r.contours[0].center.distance_to(avg_center) if r.contours else float('inf'))
            
            return best_result
        
        return successful_results[0]

class ImageVisualizer:
    """图像可视化器"""
    
    def __init__(self):
        self.colors = {
            'contour': (0, 255, 0),      # 绿色
            'center': (0, 0, 255),       # 红色
            'points': (255, 255, 0),     # 青色
            'text': (255, 255, 255),     # 白色
            'error': (0, 0, 255)         # 红色
        }
    
    def draw_detection_result(self, image: np.ndarray, result: DetectionResult) -> np.ndarray:
        """绘制检测结果"""
        if not result.success:
            # 绘制错误信息
            cv2.putText(image, f"Error: {result.error_message}", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, self.colors['error'], 2)
            return image
        
        # 绘制轮廓
        for contour_info in result.contours:
            self._draw_contour(image, contour_info, result.image_center)
        
        # 绘制处理时间
        cv2.putText(image, f"Processing Time: {result.processing_time:.3f}s", 
                   (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['text'], 2)
        
        # 绘制轮廓数量
        cv2.putText(image, f"Contours: {len(result.contours)}", 
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, self.colors['text'], 2)
        
        return image
    
    def _draw_contour(self, image: np.ndarray, contour_info: ContourInfo, image_center: Point2D):
        """绘制单个轮廓"""
        h, w = image.shape[:2]
        
        # 转换回绝对像素坐标
        absolute_points = []
        for point in contour_info.points:
            abs_x = int(point.x + image_center.x)
            abs_y = int(point.y + image_center.y)
            absolute_points.append([abs_x, abs_y])
        
        if len(absolute_points) >= 3:
            # 绘制轮廓
            pts = np.array(absolute_points, np.int32)
            cv2.drawContours(image, [pts], -1, self.colors['contour'], 2)
            
            # 绘制轮廓点
            for point in absolute_points:
                cv2.circle(image, tuple(point), 3, self.colors['points'], -1)
        
        # 绘制中心点
        center_x = int(contour_info.center.x + image_center.x)
        center_y = int(contour_info.center.y + image_center.y)
        cv2.circle(image, (center_x, center_y), 5, self.colors['center'], -1)
        
        # 绘制中心坐标
        cv2.putText(image, f"Center: ({contour_info.center.x:.1f}, {contour_info.center.y:.1f})", 
                   (center_x + 10, center_y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text'], 1)
        
        # 绘制面积信息
        cv2.putText(image, f"Area: {contour_info.area:.0f}", 
                   (center_x + 10, center_y + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.colors['text'], 1)

# 全局检测器实例
wound_detector = WoundDetector()
image_visualizer = ImageVisualizer()

def detect_wound(image: np.ndarray, stable: bool = True) -> DetectionResult:
    """检测伤口（全局函数）"""
    if stable:
        return wound_detector.detect_wound_stable(image)
    else:
        return wound_detector.detect_wound(image)

def visualize_detection(image: np.ndarray, result: DetectionResult) -> np.ndarray:
    """可视化检测结果（全局函数）"""
    return image_visualizer.draw_detection_result(image, result)

if __name__ == "__main__":
    # 测试图像处理模块
    import cv2
    
    # 创建测试图像
    test_image = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # 绘制一个红色圆形
    cv2.circle(test_image, (320, 240), 50, (0, 0, 255), -1)
    
    # 检测伤口
    result = detect_wound(test_image)
    
    print(f"检测结果: {result.success}")
    if result.success and result.contours:
        contour = result.contours[0]
        print(f"中心点: ({contour.center.x:.1f}, {contour.center.y:.1f})")
        print(f"面积: {contour.area:.1f}")
        print(f"置信度: {contour.confidence:.2f}")
    
    # 可视化结果
    visualized = visualize_detection(test_image, result)
    
    # 显示结果
    cv2.imshow("Detection Result", visualized)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


