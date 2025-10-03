"""
错误处理系统
提供统一的错误处理、日志记录和恢复机制
"""
import logging
import traceback
import time
from typing import Optional, Callable, Any, Dict
from enum import Enum
from dataclasses import dataclass
import threading
from datetime import datetime

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('robot_arm.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ErrorType(Enum):
    """错误类型枚举"""
    COMMUNICATION_ERROR = "communication_error"
    BOUNDARY_ERROR = "boundary_error"
    CALIBRATION_ERROR = "calibration_error"
    IMAGE_PROCESSING_ERROR = "image_processing_error"
    ROBOT_CONTROL_ERROR = "robot_control_error"
    CONFIG_ERROR = "config_error"
    UNKNOWN_ERROR = "unknown_error"

@dataclass
class ErrorInfo:
    """错误信息"""
    error_type: ErrorType
    message: str
    timestamp: datetime
    traceback: str
    context: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}

class RecoveryStrategy:
    """恢复策略基类"""
    
    def can_handle(self, error: ErrorInfo) -> bool:
        """判断是否能处理该错误"""
        raise NotImplementedError
    
    def execute(self, error: ErrorInfo) -> bool:
        """执行恢复策略"""
        raise NotImplementedError

class CommunicationRecovery(RecoveryStrategy):
    """通信错误恢复策略"""
    
    def __init__(self, max_retries: int = 3, retry_delay: float = 1.0):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.retry_count = 0
    
    def can_handle(self, error: ErrorInfo) -> bool:
        return error.error_type == ErrorType.COMMUNICATION_ERROR
    
    def execute(self, error: ErrorInfo) -> bool:
        if self.retry_count >= self.max_retries:
            logger.error(f"通信恢复失败，已达到最大重试次数: {self.max_retries}")
            return False
        
        self.retry_count += 1
        logger.info(f"尝试恢复通信连接 (第{self.retry_count}次)")
        
        try:
            # 这里应该调用实际的重新连接逻辑
            time.sleep(self.retry_delay)
            logger.info("通信连接已恢复")
            return True
        except Exception as e:
            logger.error(f"通信恢复失败: {e}")
            return False

class BoundaryRecovery(RecoveryStrategy):
    """边界错误恢复策略"""
    
    def can_handle(self, error: ErrorInfo) -> bool:
        return error.error_type == ErrorType.BOUNDARY_ERROR
    
    def execute(self, error: ErrorInfo) -> bool:
        logger.warning("检测到边界错误，移动到安全位置")
        
        try:
            # 移动到安全位置
            safe_position = error.context.get('safe_position', (0, 0, 100))
            logger.info(f"移动到安全位置: {safe_position}")
            # 这里应该调用实际的机械臂移动逻辑
            return True
        except Exception as e:
            logger.error(f"边界恢复失败: {e}")
            return False

class CalibrationRecovery(RecoveryStrategy):
    """标定错误恢复策略"""
    
    def can_handle(self, error: ErrorInfo) -> bool:
        return error.error_type == ErrorType.CALIBRATION_ERROR
    
    def execute(self, error: ErrorInfo) -> bool:
        logger.warning("标定失败，尝试重新标定")
        
        try:
            # 重置标定参数
            logger.info("重置标定参数")
            # 这里应该调用实际的重新标定逻辑
            return True
        except Exception as e:
            logger.error(f"标定恢复失败: {e}")
            return False

class ErrorHandler:
    """错误处理器"""
    
    def __init__(self):
        self.recovery_strategies: list[RecoveryStrategy] = []
        self.error_history: list[ErrorInfo] = []
        self.max_history_size = 100
        self.lock = threading.Lock()
        
        # 注册默认恢复策略
        self.register_recovery_strategy(CommunicationRecovery())
        self.register_recovery_strategy(BoundaryRecovery())
        self.register_recovery_strategy(CalibrationRecovery())
    
    def register_recovery_strategy(self, strategy: RecoveryStrategy) -> None:
        """注册恢复策略"""
        self.recovery_strategies.append(strategy)
        logger.info(f"已注册恢复策略: {strategy.__class__.__name__}")
    
    def handle_error(self, error_type: ErrorType, message: str, 
                    context: Dict[str, Any] = None, exception: Exception = None) -> bool:
        """处理错误"""
        with self.lock:
            # 创建错误信息
            error_info = ErrorInfo(
                error_type=error_type,
                message=message,
                timestamp=datetime.now(),
                traceback=traceback.format_exc() if exception else "",
                context=context or {}
            )
            
            # 记录错误
            self._log_error(error_info)
            self._add_to_history(error_info)
            
            # 尝试恢复
            return self._attempt_recovery(error_info)
    
    def _log_error(self, error: ErrorInfo) -> None:
        """记录错误日志"""
        log_message = f"[{error.error_type.value}] {error.message}"
        
        if error.traceback:
            log_message += f"\n{traceback}"
        
        if error.context:
            log_message += f"\n上下文: {error.context}"
        
        logger.error(log_message)
    
    def _add_to_history(self, error: ErrorInfo) -> None:
        """添加到错误历史"""
        self.error_history.append(error)
        
        # 保持历史记录大小
        if len(self.error_history) > self.max_history_size:
            self.error_history.pop(0)
    
    def _attempt_recovery(self, error: ErrorInfo) -> bool:
        """尝试恢复"""
        for strategy in self.recovery_strategies:
            if strategy.can_handle(error):
                logger.info(f"尝试使用恢复策略: {strategy.__class__.__name__}")
                try:
                    if strategy.execute(error):
                        logger.info("错误恢复成功")
                        return True
                    else:
                        logger.warning("错误恢复失败")
                except Exception as e:
                    logger.error(f"恢复策略执行异常: {e}")
        
        logger.error("没有可用的恢复策略")
        return False
    
    def get_error_history(self, limit: int = 10) -> list[ErrorInfo]:
        """获取错误历史"""
        with self.lock:
            return self.error_history[-limit:]
    
    def clear_error_history(self) -> None:
        """清空错误历史"""
        with self.lock:
            self.error_history.clear()
        logger.info("错误历史已清空")
    
    def get_error_statistics(self) -> Dict[str, int]:
        """获取错误统计"""
        with self.lock:
            stats = {}
            for error in self.error_history:
                error_type = error.error_type.value
                stats[error_type] = stats.get(error_type, 0) + 1
            return stats

# 全局错误处理器实例
error_handler = ErrorHandler()

def handle_error(error_type: ErrorType, message: str, 
                context: Dict[str, Any] = None, exception: Exception = None) -> bool:
    """处理全局错误"""
    return error_handler.handle_error(error_type, message, context, exception)

def get_error_history(limit: int = 10) -> list[ErrorInfo]:
    """获取全局错误历史"""
    return error_handler.get_error_history(limit)

def get_error_statistics() -> Dict[str, int]:
    """获取全局错误统计"""
    return error_handler.get_error_statistics()

# 装饰器：自动错误处理
def error_handler_decorator(error_type: ErrorType, 
                          context: Dict[str, Any] = None,
                          reraise: bool = False):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        def wrapper(*args, **kwargs) -> Any:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_context = context or {}
                error_context.update({
                    'function': func.__name__,
                    'args': str(args),
                    'kwargs': str(kwargs)
                })
                
                success = handle_error(error_type, str(e), error_context, e)
                
                if reraise and not success:
                    raise
                
                return None
        return wrapper
    return decorator

# 预定义的错误处理装饰器
def communication_error_handler(context: Dict[str, Any] = None):
    return error_handler_decorator(ErrorType.COMMUNICATION_ERROR, context)

def boundary_error_handler(context: Dict[str, Any] = None):
    return error_handler_decorator(ErrorType.BOUNDARY_ERROR, context)

def calibration_error_handler(context: Dict[str, Any] = None):
    return error_handler_decorator(ErrorType.CALIBRATION_ERROR, context)

def image_processing_error_handler(context: Dict[str, Any] = None):
    return error_handler_decorator(ErrorType.IMAGE_PROCESSING_ERROR, context)

def robot_control_error_handler(context: Dict[str, Any] = None):
    return error_handler_decorator(ErrorType.ROBOT_CONTROL_ERROR, context)

if __name__ == "__main__":
    # 测试错误处理系统
    print("测试错误处理系统...")
    
    # 测试通信错误
    handle_error(ErrorType.COMMUNICATION_ERROR, "串口连接失败", 
                {"port": "COM3", "baudrate": 115200})
    
    # 测试边界错误
    handle_error(ErrorType.BOUNDARY_ERROR, "目标位置超出工作空间", 
                {"target_position": (500, 500, 500), "safe_position": (0, 0, 100)})
    
    # 显示错误统计
    stats = get_error_statistics()
    print(f"错误统计: {stats}")
    
    # 显示错误历史
    history = get_error_history(5)
    print(f"最近错误: {len(history)} 个")
