"""
改进的GUI主程序
提供更现代、更用户友好的界面和更稳定的功能
"""
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import cv2
from PIL import Image, ImageTk
import threading
import time
import json
import os
from typing import Optional, Dict, Any, List
import logging

from config import get_config, update_config, save_config
from error_handler import handle_error, ErrorType, get_error_history, get_error_statistics
from robot_controller_improved import get_robot_controller, RobotState
from image_processor import detect_wound, visualize_detection, DetectionResult
from coordinate_transformer import get_coordinate_transformer, CalibrationManager, CalibrationData, Point2D, Point3D
import WenxingCircle as WC

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModernGUI:
    """现代化GUI主窗口"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("智能机械臂伤口治疗系统 v2.0")
        self.root.geometry("1200x800")
        self.root.minsize(1000, 600)
        
        # 配置
        self.config = get_config()
        
        # 状态变量
        self.is_camera_running = False
        self.is_calibrating = False
        self.is_treating = False
        self.calibration_cancelled = False
        
        # 组件
        self.cap: Optional[cv2.VideoCapture] = None
        self.robot_controller = None
        self.coordinate_transformer = get_coordinate_transformer()
        self.calibration_manager = CalibrationManager(self.coordinate_transformer)
        
        # 检测结果
        self.last_detection_result: Optional[DetectionResult] = None
        
        # 创建界面
        self.create_widgets()
        self.setup_bindings()
        
        # 初始化系统
        self.initialize_system()
        
        # 启动摄像头
        self.start_camera()
    
    def create_widgets(self):
        """创建界面组件"""
        # 创建主框架
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 创建左侧面板
        self.left_panel = ttk.Frame(self.main_frame)
        self.left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # 创建右侧面板
        self.right_panel = ttk.Frame(self.main_frame)
        self.right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, padx=(5, 0))
        
        # 创建摄像头显示区域
        self.create_camera_panel()
        
        # 创建控制面板
        self.create_control_panel()
        
        # 创建状态面板
        self.create_status_panel()
        
        # 创建日志面板
        self.create_log_panel()
    
    def create_camera_panel(self):
        """创建摄像头显示面板"""
        # 摄像头框架
        self.camera_frame = ttk.LabelFrame(self.left_panel, text="实时摄像头", padding="10")
        self.camera_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 摄像头显示标签
        self.camera_label = ttk.Label(self.camera_frame)
        self.camera_label.pack(expand=True)
        
        # 摄像头控制按钮
        self.camera_control_frame = ttk.Frame(self.camera_frame)
        self.camera_control_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.start_camera_btn = ttk.Button(self.camera_control_frame, text="启动摄像头", 
                                         command=self.start_camera)
        self.start_camera_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_camera_btn = ttk.Button(self.camera_control_frame, text="停止摄像头", 
                                        command=self.stop_camera, state=tk.DISABLED)
        self.stop_camera_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.capture_btn = ttk.Button(self.camera_control_frame, text="拍照", 
                                    command=self.capture_photo)
        self.capture_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 检测开关
        self.detection_var = tk.BooleanVar(value=True)
        self.detection_check = ttk.Checkbutton(self.camera_control_frame, 
                                             text="实时检测", 
                                             variable=self.detection_var)
        self.detection_check.pack(side=tk.LEFT, padx=(20, 0))
    
    def create_control_panel(self):
        """创建控制面板"""
        # 主控制框架
        self.control_frame = ttk.LabelFrame(self.right_panel, text="系统控制", padding="10")
        self.control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 机械臂控制
        self.create_robot_control()
        
        # 图像处理控制
        self.create_image_processing_control()
        
        # 标定控制
        self.create_calibration_control()
        
        # 治疗控制
        self.create_treatment_control()
    
    def create_robot_control(self):
        """创建机械臂控制"""
        robot_frame = ttk.LabelFrame(self.control_frame, text="机械臂控制", padding="5")
        robot_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 连接状态
        self.connection_status = ttk.Label(robot_frame, text="未连接", foreground="red")
        self.connection_status.pack(anchor=tk.W)
        
        # 连接按钮
        self.connect_btn = ttk.Button(robot_frame, text="连接机械臂", 
                                    command=self.connect_robot)
        self.connect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.disconnect_btn = ttk.Button(robot_frame, text="断开连接", 
                                       command=self.disconnect_robot, state=tk.DISABLED)
        self.disconnect_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # 紧急停止按钮
        self.emergency_btn = ttk.Button(robot_frame, text="紧急停止", 
                                      command=self.emergency_stop, 
                                      style="Accent.TButton")
        self.emergency_btn.pack(side=tk.RIGHT)
    
    def create_image_processing_control(self):
        """创建图像处理控制"""
        img_frame = ttk.LabelFrame(self.control_frame, text="图像处理参数", padding="5")
        img_frame.pack(fill=tk.X, pady=(0, 10))
        
        # HSV参数控制
        self.create_hsv_controls(img_frame)
        
        # 轮廓参数控制
        self.create_contour_controls(img_frame)
        
        # 参数保存/加载
        param_frame = ttk.Frame(img_frame)
        param_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(param_frame, text="保存参数", 
                  command=self.save_parameters).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(param_frame, text="加载参数", 
                  command=self.load_parameters).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(param_frame, text="重置参数", 
                  command=self.reset_parameters).pack(side=tk.LEFT)
    
    def create_hsv_controls(self, parent):
        """创建HSV控制"""
        hsv_frame = ttk.Frame(parent)
        hsv_frame.pack(fill=tk.X, pady=(0, 5))
        
        # H通道
        ttk.Label(hsv_frame, text="H通道:").grid(row=0, column=0, sticky=tk.W)
        self.h_min_var = tk.IntVar(value=self.config.image_processing.hsv_red1_lower[0])
        self.h_max_var = tk.IntVar(value=self.config.image_processing.hsv_red1_upper[0])
        ttk.Scale(hsv_frame, from_=0, to=180, variable=self.h_min_var, 
                 orient=tk.HORIZONTAL, length=100, command=self.update_hsv).grid(row=0, column=1, padx=5)
        ttk.Scale(hsv_frame, from_=0, to=180, variable=self.h_max_var, 
                 orient=tk.HORIZONTAL, length=100, command=self.update_hsv).grid(row=0, column=2, padx=5)
        ttk.Label(hsv_frame, text="Min").grid(row=1, column=1)
        ttk.Label(hsv_frame, text="Max").grid(row=1, column=2)
        
        # S通道
        ttk.Label(hsv_frame, text="S通道:").grid(row=2, column=0, sticky=tk.W)
        self.s_min_var = tk.IntVar(value=self.config.image_processing.hsv_red1_lower[1])
        self.s_max_var = tk.IntVar(value=self.config.image_processing.hsv_red1_upper[1])
        ttk.Scale(hsv_frame, from_=0, to=255, variable=self.s_min_var, 
                 orient=tk.HORIZONTAL, length=100, command=self.update_hsv).grid(row=2, column=1, padx=5)
        ttk.Scale(hsv_frame, from_=0, to=255, variable=self.s_max_var, 
                 orient=tk.HORIZONTAL, length=100, command=self.update_hsv).grid(row=2, column=2, padx=5)
        
        # V通道
        ttk.Label(hsv_frame, text="V通道:").grid(row=3, column=0, sticky=tk.W)
        self.v_min_var = tk.IntVar(value=self.config.image_processing.hsv_red1_lower[2])
        self.v_max_var = tk.IntVar(value=self.config.image_processing.hsv_red1_upper[2])
        ttk.Scale(hsv_frame, from_=0, to=255, variable=self.v_min_var, 
                 orient=tk.HORIZONTAL, length=100, command=self.update_hsv).grid(row=3, column=1, padx=5)
        ttk.Scale(hsv_frame, from_=0, to=255, variable=self.v_max_var, 
                 orient=tk.HORIZONTAL, length=100, command=self.update_hsv).grid(row=3, column=2, padx=5)
    
    def create_contour_controls(self, parent):
        """创建轮廓控制"""
        contour_frame = ttk.Frame(parent)
        contour_frame.pack(fill=tk.X, pady=(0, 5))
        
        # 轮廓精度
        ttk.Label(contour_frame, text="轮廓精度:").grid(row=0, column=0, sticky=tk.W)
        self.epsilon_var = tk.DoubleVar(value=self.config.image_processing.contour_epsilon_factor)
        ttk.Scale(contour_frame, from_=0.001, to=0.01, variable=self.epsilon_var, 
                 orient=tk.HORIZONTAL, length=150, command=self.update_contour).grid(row=0, column=1, padx=5)
        
        # 最小面积
        ttk.Label(contour_frame, text="最小面积:").grid(row=1, column=0, sticky=tk.W)
        self.min_area_var = tk.IntVar(value=self.config.image_processing.min_contour_area)
        ttk.Scale(contour_frame, from_=50, to=2000, variable=self.min_area_var, 
                 orient=tk.HORIZONTAL, length=150, command=self.update_contour).grid(row=1, column=1, padx=5)
    
    def create_calibration_control(self):
        """创建标定控制"""
        calib_frame = ttk.LabelFrame(self.control_frame, text="系统标定", padding="5")
        calib_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 标定状态
        self.calibration_status = ttk.Label(calib_frame, text="未标定")
        self.calibration_status.pack(anchor=tk.W)
        
        # 标定进度条
        self.calibration_progress = ttk.Progressbar(calib_frame, mode='determinate')
        self.calibration_progress.pack(fill=tk.X, pady=(5, 0))
        
        # 标定按钮
        calib_btn_frame = ttk.Frame(calib_frame)
        calib_btn_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.calibrate_btn = ttk.Button(calib_btn_frame, text="开始标定", 
                                      command=self.start_calibration)
        self.calibrate_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.cancel_calib_btn = ttk.Button(calib_btn_frame, text="取消标定", 
                                         command=self.cancel_calibration, state=tk.DISABLED)
        self.cancel_calib_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.manual_calib_btn = ttk.Button(calib_btn_frame, text="手动标定", 
                                         command=self.manual_calibration)
        self.manual_calib_btn.pack(side=tk.RIGHT)
    
    def create_treatment_control(self):
        """创建治疗控制"""
        treat_frame = ttk.LabelFrame(self.control_frame, text="治疗控制", padding="5")
        treat_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 治疗状态
        self.treatment_status = ttk.Label(treat_frame, text="就绪")
        self.treatment_status.pack(anchor=tk.W)
        
        # 治疗按钮
        self.start_treatment_btn = ttk.Button(treat_frame, text="开始治疗", 
                                            command=self.start_treatment, 
                                            style="Accent.TButton", state=tk.DISABLED)
        self.start_treatment_btn.pack(fill=tk.X, pady=(5, 0))
        
        # 治疗进度
        self.treatment_progress = ttk.Progressbar(treat_frame, mode='determinate')
        self.treatment_progress.pack(fill=tk.X, pady=(5, 0))
    
    def create_status_panel(self):
        """创建状态面板"""
        status_frame = ttk.LabelFrame(self.right_panel, text="系统状态", padding="10")
        status_frame.pack(fill=tk.X, pady=(0, 10))
        
        # 机械臂状态
        self.robot_status_label = ttk.Label(status_frame, text="机械臂: 未连接")
        self.robot_status_label.pack(anchor=tk.W)
        
        # 摄像头状态
        self.camera_status_label = ttk.Label(status_frame, text="摄像头: 未启动")
        self.camera_status_label.pack(anchor=tk.W)
        
        # 检测状态
        self.detection_status_label = ttk.Label(status_frame, text="检测: 未检测")
        self.detection_status_label.pack(anchor=tk.W)
        
        # 位置信息
        self.position_label = ttk.Label(status_frame, text="位置: 未知")
        self.position_label.pack(anchor=tk.W)
    
    def create_log_panel(self):
        """创建日志面板"""
        log_frame = ttk.LabelFrame(self.right_panel, text="系统日志", padding="5")
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        # 日志文本框
        self.log_text = tk.Text(log_frame, height=10, width=50)
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # 日志控制按钮
        log_btn_frame = ttk.Frame(log_frame)
        log_btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        ttk.Button(log_btn_frame, text="清空日志", 
                  command=self.clear_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_btn_frame, text="保存日志", 
                  command=self.save_log).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(log_btn_frame, text="错误统计", 
                  command=self.show_error_statistics).pack(side=tk.LEFT)
    
    def setup_bindings(self):
        """设置事件绑定"""
        # 键盘事件
        self.root.bind('<Key>', self.on_key_press)
        self.root.bind('<Return>', lambda e: self.start_treatment())
        self.root.bind('<space>', lambda e: self.capture_photo())
        self.root.bind('<Escape>', lambda e: self.emergency_stop())
        self.root.focus_set()
        
        # 窗口关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def initialize_system(self):
        """初始化系统"""
        try:
            # 初始化机械臂控制器
            self.robot_controller = get_robot_controller()
            
            # 更新状态显示
            self.update_status_display()
            
            self.log_message("系统初始化完成")
            
        except Exception as e:
            self.log_message(f"系统初始化失败: {e}", "ERROR")
            handle_error(ErrorType.UNKNOWN_ERROR, f"系统初始化失败: {e}")
    
    def start_camera(self):
        """启动摄像头"""
        try:
            if self.cap is None:
                self.cap = cv2.VideoCapture(self.config.camera.device_id)
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.camera.resolution[0])
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.camera.resolution[1])
                self.cap.set(cv2.CAP_PROP_FPS, self.config.camera.fps)
            
            if not self.cap.isOpened():
                raise Exception("无法打开摄像头")
            
            self.is_camera_running = True
            self.start_camera_btn.config(state=tk.DISABLED)
            self.stop_camera_btn.config(state=tk.NORMAL)
            
            # 设置图像中心
            ret, frame = self.cap.read()
            if ret:
                h, w = frame.shape[:2]
                self.coordinate_transformer.set_image_center(w, h)
            
            # 启动摄像头更新线程
            self.update_camera()
            
            self.log_message("摄像头启动成功")
            self.camera_status_label.config(text="摄像头: 运行中", foreground="green")
            
        except Exception as e:
            self.log_message(f"摄像头启动失败: {e}", "ERROR")
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, f"摄像头启动失败: {e}")
    
    def stop_camera(self):
        """停止摄像头"""
        self.is_camera_running = False
        
        if self.cap:
            self.cap.release()
            self.cap = None
        
        self.start_camera_btn.config(state=tk.NORMAL)
        self.stop_camera_btn.config(state=tk.DISABLED)
        
        self.log_message("摄像头已停止")
        self.camera_status_label.config(text="摄像头: 已停止", foreground="red")
    
    def update_camera(self):
        """更新摄像头显示"""
        if not self.is_camera_running or not self.cap:
            return
        
        try:
            ret, frame = self.cap.read()
            if ret:
                # 如果启用检测，进行伤口检测
                if self.detection_var.get():
                    result = detect_wound(frame, stable=True)
                    self.last_detection_result = result
                    
                    # 可视化检测结果
                    frame = visualize_detection(frame, result)
                    
                    # 更新检测状态
                    if result.success and result.contours:
                        contour = result.contours[0]
                        self.detection_status_label.config(
                            text=f"检测: 已检测 (中心: {contour.center.x:.1f}, {contour.center.y:.1f})",
                            foreground="green"
                        )
                    else:
                        self.detection_status_label.config(
                            text="检测: 未检测到伤口",
                            foreground="orange"
                        )
                else:
                    self.detection_status_label.config(text="检测: 已禁用", foreground="gray")
                
                # 转换并显示图像
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image)
                self.camera_label.configure(image=photo)
                self.camera_label.image = photo
        
        except Exception as e:
            self.log_message(f"摄像头更新失败: {e}", "ERROR")
        
        # 继续更新
        if self.is_camera_running:
            self.root.after(33, self.update_camera)  # 约30fps
    
    def capture_photo(self):
        """拍照"""
        if not self.cap or not self.is_camera_running:
            messagebox.showwarning("警告", "摄像头未启动")
            return
        
        try:
            ret, frame = self.cap.read()
            if ret:
                # 保存照片
                timestamp = time.strftime("%Y%m%d_%H%M%S")
                filename = f"captured_photos/photo_{timestamp}.jpg"
                
                # 确保目录存在
                os.makedirs("captured_photos", exist_ok=True)
                
                cv2.imwrite(filename, frame)
                self.log_message(f"照片已保存: {filename}")
                
                # 进行检测
                result = detect_wound(frame, stable=True)
                if result.success and result.contours:
                    self.log_message(f"检测到伤口，中心: ({result.contours[0].center.x:.1f}, {result.contours[0].center.y:.1f})")
                else:
                    self.log_message("未检测到伤口")
        
        except Exception as e:
            self.log_message(f"拍照失败: {e}", "ERROR")
            handle_error(ErrorType.IMAGE_PROCESSING_ERROR, f"拍照失败: {e}")
    
    def connect_robot(self):
        """连接机械臂"""
        try:
            if self.robot_controller and self.robot_controller.is_connected:
                self.log_message("机械臂已连接")
                return
            
            self.robot_controller = get_robot_controller()
            
            if self.robot_controller.is_connected:
                self.connect_btn.config(state=tk.DISABLED)
                self.disconnect_btn.config(state=tk.NORMAL)
                self.connection_status.config(text="已连接", foreground="green")
                self.robot_status_label.config(text="机械臂: 已连接", foreground="green")
                self.log_message("机械臂连接成功")
            else:
                raise Exception("机械臂连接失败")
        
        except Exception as e:
            self.log_message(f"机械臂连接失败: {e}", "ERROR")
            handle_error(ErrorType.COMMUNICATION_ERROR, f"机械臂连接失败: {e}")
            messagebox.showerror("错误", f"机械臂连接失败: {e}")
    
    def disconnect_robot(self):
        """断开机械臂连接"""
        try:
            if self.robot_controller:
                self.robot_controller.disconnect()
            
            self.connect_btn.config(state=tk.NORMAL)
            self.disconnect_btn.config(state=tk.DISABLED)
            self.connection_status.config(text="未连接", foreground="red")
            self.robot_status_label.config(text="机械臂: 未连接", foreground="red")
            
            self.log_message("机械臂已断开连接")
        
        except Exception as e:
            self.log_message(f"断开连接失败: {e}", "ERROR")
    
    def start_calibration(self):
        """开始标定"""
        if not self.robot_controller or not self.robot_controller.is_connected:
            messagebox.showwarning("警告", "请先连接机械臂")
            return
        
        if not self.last_detection_result or not self.last_detection_result.success:
            messagebox.showwarning("警告", "请先检测到伤口")
            return
        
        # 在后台线程中执行标定
        self.is_calibrating = True
        self.calibration_cancelled = False
        
        self.calibrate_btn.config(state=tk.DISABLED)
        self.cancel_calib_btn.config(state=tk.NORMAL)
        self.calibration_status.config(text="标定中...", foreground="orange")
        
        threading.Thread(target=self._calibration_worker, daemon=True).start()
    
    def _calibration_worker(self):
        """标定工作线程"""
        try:
            self.log_message("开始自动标定...")
            
            # 获取当前检测结果
            if not self.last_detection_result or not self.last_detection_result.contours:
                raise Exception("未检测到伤口轮廓")
            
            contour = self.last_detection_result.contours[0]
            pixel_center = contour.center
            
            # 获取当前位置
            current_pos = self.robot_controller.get_current_position()
            if not current_pos:
                raise Exception("无法获取机械臂当前位置")
            
            # 添加标定点
            self.calibration_manager.add_calibration_point(
                pixel_center, current_pos
            )
            
            # 移动机械臂进行标定
            calibration_distance = self.config.calibration.distance_mm
            target_y = current_pos.y - calibration_distance
            
            self.robot_controller.move_to_position(
                current_pos.x, target_y, current_pos.z
            )
            time.sleep(2)
            
            # 检测新位置
            ret, frame = self.cap.read()
            if not ret:
                raise Exception("无法获取新位置图像")
            
            result = detect_wound(frame, stable=True)
            if not result.success or not result.contours:
                raise Exception("新位置未检测到伤口")
            
            new_contour = result.contours[0]
            new_pixel_center = new_contour.center
            
            # 添加第二个标定点
            new_physical_pos = Point3D(current_pos.x, target_y, current_pos.z)
            self.calibration_manager.add_calibration_point(
                new_pixel_center, new_physical_pos
            )
            
            # 执行标定
            calibration_data = self.calibration_manager.perform_calibration()
            
            if calibration_data and calibration_data.is_valid():
                self.coordinate_transformer.set_calibration_data(calibration_data)
                
                # 更新UI
                self.root.after(0, lambda: self.calibration_status.config(
                    text=f"标定完成 (比例: {calibration_data.scale_factor:.4f})",
                    foreground="green"
                ))
                
                self.log_message(f"标定完成: 比例={calibration_data.scale_factor:.4f}, "
                               f"置信度={calibration_data.confidence:.2f}")
                
                # 启用治疗按钮
                self.root.after(0, lambda: self.start_treatment_btn.config(state=tk.NORMAL))
                
            else:
                raise Exception("标定失败")
            
        except Exception as e:
            error_msg = f"标定失败: {e}"
            self.log_message(error_msg, "ERROR")
            handle_error(ErrorType.CALIBRATION_ERROR, error_msg)
            
            # 更新UI
            self.root.after(0, lambda: self.calibration_status.config(
                text="标定失败", foreground="red"
            ))
        
        finally:
            # 恢复UI状态
            self.root.after(0, self._calibration_finished)
    
    def _calibration_finished(self):
        """标定完成后的UI更新"""
        self.is_calibrating = False
        self.calibrate_btn.config(state=tk.NORMAL)
        self.cancel_calib_btn.config(state=tk.DISABLED)
        self.calibration_progress.config(value=0)
    
    def cancel_calibration(self):
        """取消标定"""
        self.calibration_cancelled = True
        self.log_message("用户取消了标定")
    
    def manual_calibration(self):
        """手动标定"""
        messagebox.showinfo("手动标定", "手动标定功能开发中...")
    
    def start_treatment(self):
        """开始治疗"""
        if not self.robot_controller or not self.robot_controller.is_connected:
            messagebox.showwarning("警告", "请先连接机械臂")
            return
        
        if not self.coordinate_transformer.calibration_data:
            messagebox.showwarning("警告", "请先完成标定")
            return
        
        if not self.last_detection_result or not self.last_detection_result.success:
            messagebox.showwarning("警告", "请先检测到伤口")
            return
        
        # 在后台线程中执行治疗
        self.is_treating = True
        self.start_treatment_btn.config(state=tk.DISABLED)
        self.treatment_status.config(text="治疗中...", foreground="orange")
        
        threading.Thread(target=self._treatment_worker, daemon=True).start()
    
    def _treatment_worker(self):
        """治疗工作线程"""
        try:
            self.log_message("开始治疗...")
            
            # 获取伤口轮廓
            contour = self.last_detection_result.contours[0]
            
            # 转换坐标
            physical_points = self.coordinate_transformer.batch_transform(contour.points)
            
            # 生成治疗路径
            self._generate_treatment_path(physical_points)
            
            # 执行治疗路径
            self._execute_treatment_path()
            
            self.log_message("治疗完成")
            
        except Exception as e:
            error_msg = f"治疗失败: {e}"
            self.log_message(error_msg, "ERROR")
            handle_error(ErrorType.ROBOT_CONTROL_ERROR, error_msg)
        
        finally:
            # 恢复UI状态
            self.root.after(0, self._treatment_finished)
    
    def _generate_treatment_path(self, physical_points):
        """生成治疗路径"""
        # 这里应该调用路径规划算法
        # 暂时使用简单的圆形路径
        self.log_message("生成治疗路径...")
        # TODO: 实现路径规划
    
    def _execute_treatment_path(self):
        """执行治疗路径"""
        self.log_message("执行治疗路径...")
        # TODO: 实现治疗路径执行
    
    def _treatment_finished(self):
        """治疗完成后的UI更新"""
        self.is_treating = False
        self.start_treatment_btn.config(state=tk.NORMAL)
        self.treatment_status.config(text="就绪", foreground="green")
        self.treatment_progress.config(value=0)
    
    def emergency_stop(self):
        """紧急停止"""
        try:
            if self.robot_controller:
                self.robot_controller.emergency_stop()
            
            self.is_calibrating = False
            self.is_treating = False
            
            self.log_message("紧急停止已执行", "WARNING")
            
        except Exception as e:
            self.log_message(f"紧急停止失败: {e}", "ERROR")
    
    def update_hsv(self, event=None):
        """更新HSV参数"""
        try:
            # 更新配置
            self.config.image_processing.hsv_red1_lower = (
                self.h_min_var.get(),
                self.s_min_var.get(),
                self.v_min_var.get()
            )
            self.config.image_processing.hsv_red1_upper = (
                self.h_max_var.get(),
                self.s_max_var.get(),
                self.v_max_var.get()
            )
            
            # 保存配置
            save_config()
            
        except Exception as e:
            self.log_message(f"更新HSV参数失败: {e}", "ERROR")
    
    def update_contour(self, event=None):
        """更新轮廓参数"""
        try:
            # 更新配置
            self.config.image_processing.contour_epsilon_factor = self.epsilon_var.get()
            self.config.image_processing.min_contour_area = self.min_area_var.get()
            
            # 保存配置
            save_config()
            
        except Exception as e:
            self.log_message(f"更新轮廓参数失败: {e}", "ERROR")
    
    def save_parameters(self):
        """保存参数"""
        try:
            save_config()
            self.log_message("参数已保存")
            messagebox.showinfo("成功", "参数已保存")
        except Exception as e:
            self.log_message(f"保存参数失败: {e}", "ERROR")
            messagebox.showerror("错误", f"保存参数失败: {e}")
    
    def load_parameters(self):
        """加载参数"""
        try:
            from config import load_config
            load_config()
            self.config = get_config()
            
            # 更新UI控件
            self.h_min_var.set(self.config.image_processing.hsv_red1_lower[0])
            self.h_max_var.set(self.config.image_processing.hsv_red1_upper[0])
            self.s_min_var.set(self.config.image_processing.hsv_red1_lower[1])
            self.s_max_var.set(self.config.image_processing.hsv_red1_upper[1])
            self.v_min_var.set(self.config.image_processing.hsv_red1_lower[2])
            self.v_max_var.set(self.config.image_processing.hsv_red1_upper[2])
            self.epsilon_var.set(self.config.image_processing.contour_epsilon_factor)
            self.min_area_var.set(self.config.image_processing.min_contour_area)
            
            self.log_message("参数已加载")
            messagebox.showinfo("成功", "参数已加载")
        except Exception as e:
            self.log_message(f"加载参数失败: {e}", "ERROR")
            messagebox.showerror("错误", f"加载参数失败: {e}")
    
    def reset_parameters(self):
        """重置参数"""
        try:
            from config import config_manager
            config_manager.reset_to_default()
            self.config = get_config()
            
            # 更新UI控件
            self.h_min_var.set(self.config.image_processing.hsv_red1_lower[0])
            self.h_max_var.set(self.config.image_processing.hsv_red1_upper[0])
            self.s_min_var.set(self.config.image_processing.hsv_red1_lower[1])
            self.s_max_var.set(self.config.image_processing.hsv_red1_upper[1])
            self.v_min_var.set(self.config.image_processing.hsv_red1_lower[2])
            self.v_max_var.set(self.config.image_processing.hsv_red1_upper[2])
            self.epsilon_var.set(self.config.image_processing.contour_epsilon_factor)
            self.min_area_var.set(self.config.image_processing.min_contour_area)
            
            self.log_message("参数已重置")
            messagebox.showinfo("成功", "参数已重置为默认值")
        except Exception as e:
            self.log_message(f"重置参数失败: {e}", "ERROR")
            messagebox.showerror("错误", f"重置参数失败: {e}")
    
    def update_status_display(self):
        """更新状态显示"""
        if self.robot_controller:
            status = self.robot_controller.get_current_status()
            pos = status.current_position
            
            self.position_label.config(
                text=f"位置: ({pos.x:.1f}, {pos.y:.1f}, {pos.z:.1f})"
            )
        
        # 定期更新
        self.root.after(1000, self.update_status_display)
    
    def log_message(self, message: str, level: str = "INFO"):
        """记录日志消息"""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {level}: {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)
        
        # 限制日志长度
        lines = self.log_text.get("1.0", tk.END).split('\n')
        if len(lines) > 1000:
            self.log_text.delete("1.0", "100.0")
    
    def clear_log(self):
        """清空日志"""
        self.log_text.delete("1.0", tk.END)
    
    def save_log(self):
        """保存日志"""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
            )
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                self.log_message(f"日志已保存到: {filename}")
        except Exception as e:
            self.log_message(f"保存日志失败: {e}", "ERROR")
    
    def show_error_statistics(self):
        """显示错误统计"""
        try:
            stats = get_error_statistics()
            if stats:
                stats_text = "错误统计:\n"
                for error_type, count in stats.items():
                    stats_text += f"{error_type}: {count}次\n"
                messagebox.showinfo("错误统计", stats_text)
            else:
                messagebox.showinfo("错误统计", "暂无错误记录")
        except Exception as e:
            self.log_message(f"获取错误统计失败: {e}", "ERROR")
    
    def on_key_press(self, event):
        """键盘事件处理"""
        key = event.keysym.lower()
        
        if key == 'q':
            self.emergency_stop()
        elif key == 'c':
            self.capture_photo()
        elif key == 'r':
            self.start_calibration()
        elif key == 't':
            self.start_treatment()
    
    def on_closing(self):
        """窗口关闭事件"""
        try:
            # 停止摄像头
            self.stop_camera()
            
            # 断开机械臂连接
            if self.robot_controller:
                self.robot_controller.disconnect()
            
            # 保存配置
            save_config()
            
            self.root.destroy()
            
        except Exception as e:
            self.log_message(f"关闭程序时出错: {e}", "ERROR")
            self.root.destroy()

def main():
    """主函数"""
    root = tk.Tk()
    
    # 设置样式
    style = ttk.Style()
    style.theme_use('clam')
    
    # 创建应用
    app = ModernGUI(root)
    
    # 运行主循环
    root.mainloop()

if __name__ == "__main__":
    main()
