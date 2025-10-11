import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import threading
import numpy as np
import pandas as pd
import control
import time
import math
import os
import sys
import CoordinateConvert__XY as CXY
import WenxingCircle as WC
import csv
coordinate_of_edge= 0
Centerpoint=(0,0)
num=0
output_path = "coordinates.csv"
h,w=0,0
image=0
position={"x":150,"y":0,"z":180}
Counter=0
try:
    arm=control.RoArmControl()
except:
    print("串口未连接")


cameraoffset=40 ####摄像头与喷嘴的偏移矫正
def read_coordinates_csv(file_path):
    """
    使用csv模块读取第2列和第3列数据，跳过首行
    :param file_path: CSV文件路径
    :return: 包含(x, y)元组的列表
    """
    coordinates = []
    try:
        with open(file_path, 'r') as file:
            reader = csv.reader(file)
            next(reader)  # 跳过首行
            for row in reader:
                try:
                    x = float(row[1])  # 第2列（索引1）
                    y = float(row[2])  # 第3列（索引2）
                    coordinates.append((x, y))
                except (IndexError, ValueError):
                    print(f"跳过无效行：{row}")
    except FileNotFoundError:
        print(f"错误：文件 {file_path} 未找到")
    return coordinates
class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Camera live feed and wound recognition")

        # 设置窗口大小和最小尺寸
        self.root.geometry("800x900")
        self.root.minsize(600, 700)

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)

        # 灵敏度参数
        self.sensitivity_params = {
            'h_min': 0,
            'h_max': 10,
            's_min': 70,
            's_max': 255,
            'v_min': 50,
            'v_max': 255,
            'epsilon_factor': 0.002,
            'min_area': 100
        }
        
        # 标定控制相关
        self.calibration_cancelled = False

        # 创建主滚动区域
        self.main_canvas = tk.Canvas(root)
        self.main_scrollbar = ttk.Scrollbar(root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)

        # 创建GUI元素
        self.label = ttk.Label(self.scrollable_frame)
        self.label.pack()

        # 灵敏度控制面板
        self.sensitivity_frame = ttk.LabelFrame(self.scrollable_frame, text="伤口检测灵敏度设置", padding="10")
        self.sensitivity_frame.pack(fill="x", padx=10, pady=5)

        # HSV阈值控制
        self.hsv_frame = ttk.Frame(self.sensitivity_frame)
        self.hsv_frame.pack(fill="x", pady=5)

        # H通道控制
        ttk.Label(self.hsv_frame, text="H通道:").grid(row=0, column=0, sticky="w")
        self.h_min_var = tk.IntVar(value=self.sensitivity_params['h_min'])
        self.h_max_var = tk.IntVar(value=self.sensitivity_params['h_max'])
        ttk.Scale(self.hsv_frame, from_=0, to=180, variable=self.h_min_var, 
                 orient="horizontal", length=100, command=self.update_sensitivity).grid(row=0, column=1, padx=5)
        ttk.Scale(self.hsv_frame, from_=0, to=180, variable=self.h_max_var, 
                 orient="horizontal", length=100, command=self.update_sensitivity).grid(row=0, column=2, padx=5)
        ttk.Label(self.hsv_frame, text="Min").grid(row=1, column=1)
        ttk.Label(self.hsv_frame, text="Max").grid(row=1, column=2)

        # S通道控制
        ttk.Label(self.hsv_frame, text="S通道:").grid(row=2, column=0, sticky="w")
        self.s_min_var = tk.IntVar(value=self.sensitivity_params['s_min'])
        self.s_max_var = tk.IntVar(value=self.sensitivity_params['s_max'])
        ttk.Scale(self.hsv_frame, from_=0, to=255, variable=self.s_min_var, 
                 orient="horizontal", length=100, command=self.update_sensitivity).grid(row=2, column=1, padx=5)
        ttk.Scale(self.hsv_frame, from_=0, to=255, variable=self.s_max_var, 
                 orient="horizontal", length=100, command=self.update_sensitivity).grid(row=2, column=2, padx=5)

        # V通道控制
        ttk.Label(self.hsv_frame, text="V通道:").grid(row=3, column=0, sticky="w")
        self.v_min_var = tk.IntVar(value=self.sensitivity_params['v_min'])
        self.v_max_var = tk.IntVar(value=self.sensitivity_params['v_max'])
        ttk.Scale(self.hsv_frame, from_=0, to=255, variable=self.v_min_var, 
                 orient="horizontal", length=100, command=self.update_sensitivity).grid(row=3, column=1, padx=5)
        ttk.Scale(self.hsv_frame, from_=0, to=255, variable=self.v_max_var, 
                 orient="horizontal", length=100, command=self.update_sensitivity).grid(row=3, column=2, padx=5)

        # 轮廓检测参数控制
        self.contour_frame = ttk.Frame(self.sensitivity_frame)
        self.contour_frame.pack(fill="x", pady=5)

        # 轮廓精度控制
        ttk.Label(self.contour_frame, text="轮廓精度:").grid(row=0, column=0, sticky="w")
        self.epsilon_var = tk.DoubleVar(value=self.sensitivity_params['epsilon_factor'])
        ttk.Scale(self.contour_frame, from_=0.001, to=0.01, variable=self.epsilon_var, 
                 orient="horizontal", length=150, command=self.update_sensitivity).grid(row=0, column=1, padx=5)

        # 最小面积控制
        ttk.Label(self.contour_frame, text="最小面积:").grid(row=1, column=0, sticky="w")
        self.min_area_var = tk.IntVar(value=self.sensitivity_params['min_area'])
        ttk.Scale(self.contour_frame, from_=50, to=2000, variable=self.min_area_var, 
                 orient="horizontal", length=150, command=self.update_sensitivity).grid(row=1, column=1, padx=5)

        # 控制按钮行
        self.control_buttons_frame = ttk.Frame(self.sensitivity_frame)
        self.control_buttons_frame.pack(fill="x", pady=5)
        
        # 重置按钮
        ttk.Button(self.control_buttons_frame, text="重置为默认值", 
                  command=self.reset_sensitivity).pack(side="left", padx=5)
        
        # 实时预览开关
        self.preview_var = tk.BooleanVar(value=True)
        self.preview_check = ttk.Checkbutton(self.control_buttons_frame, 
                                           text="实时预览", 
                                           variable=self.preview_var)
        self.preview_check.pack(side="left", padx=5)
        
        # 保存参数按钮
        ttk.Button(self.control_buttons_frame, text="保存参数", 
                  command=self.save_sensitivity_params).pack(side="left", padx=5)
        
        # 加载参数按钮
        ttk.Button(self.control_buttons_frame, text="加载参数", 
                  command=self.load_sensitivity_params).pack(side="left", padx=5)
        
        # 标定状态显示
        self.calibration_status_frame = ttk.LabelFrame(self.scrollable_frame, text="标定状态", padding="5")
        self.calibration_status_frame.pack(fill="x", padx=10, pady=5)
        
        self.calibration_status_label = ttk.Label(self.calibration_status_frame, text="未开始标定")
        self.calibration_status_label.pack()
        
        self.calibration_progress = ttk.Progressbar(self.calibration_status_frame, mode='determinate')
        self.calibration_progress.pack(fill="x", pady=5)

        # 确认按钮 - 放在最显眼的位置
        self.confirm_frame = ttk.Frame(self.scrollable_frame)
        self.confirm_frame.pack(fill="x", padx=10, pady=10)
        
        self.confirm_button = ttk.Button(self.confirm_frame, text="🚀 开始治疗 (CONFIRM) 🚀", 
                                       command=self.confirm_action, 
                                       style="Accent.TButton")
        self.confirm_button.pack(fill="x", pady=5)
        
        # 取消标定按钮
        self.cancel_button = ttk.Button(self.confirm_frame, text="❌ 取消标定", 
                                      command=self.cancel_calibration, 
                                      state='disabled')
        self.cancel_button.pack(fill="x", pady=5)
        
        # 添加提示信息
        self.control_hint_label = ttk.Label(self.confirm_frame, 
                                          text="提示：按回车键(Enter)或空格键(Space)也可以开始治疗", 
                                          font=("Arial", 8))
        self.control_hint_label.pack(pady=2)

        # 控制按钮
        self.control_frame = ttk.LabelFrame(self.scrollable_frame, text="机械臂控制", padding="10")
        self.control_frame.pack(fill="x", padx=10, pady=5)

        # 方向控制按钮
        self.direction_frame = ttk.Frame(self.control_frame)
        self.direction_frame.pack(pady=5)

        self.w_button = ttk.Button(self.direction_frame, text="W", command=lambda: self.move_camera('w'))
        self.w_button.grid(row=0, column=1, padx=2, pady=2)
        self.a_button = ttk.Button(self.direction_frame, text="A", command=lambda: self.move_camera('a'))
        self.a_button.grid(row=0, column=0, padx=2, pady=2)
        self.s_button = ttk.Button(self.direction_frame, text="S", command=lambda: self.move_camera('s'))
        self.s_button.grid(row=0, column=2, padx=2, pady=2)
        self.d_button = ttk.Button(self.direction_frame, text="D", command=lambda: self.move_camera('d'))
        self.d_button.grid(row=0, column=3, padx=2, pady=2)

        self.q_button = ttk.Button(self.direction_frame, text="Q", command=lambda: self.move_camera('q'))
        self.q_button.grid(row=1, column=0, padx=2, pady=2)
        self.e_button = ttk.Button(self.direction_frame, text="E", command=lambda: self.move_camera('e'))
        self.e_button.grid(row=1, column=3, padx=2, pady=2)

        # 绑定键盘事件
        self.root.bind('<Key>', self.on_key_press)
        self.root.bind('<Return>', lambda e: self.confirm_action())  # 回车键触发确认
        self.root.bind('<space>', lambda e: self.confirm_action())   # 空格键触发确认
        self.root.focus_set()

        # 尝试加载保存的参数
        self.load_sensitivity_params()

        # 布局滚动区域
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.main_scrollbar.pack(side="right", fill="y")
        
        # 绑定鼠标滚轮事件
        def _on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        self.main_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # 开始更新摄像头画面
        self.update_camera()

    def update_sensitivity(self, event=None):
        """更新灵敏度参数"""
        self.sensitivity_params['h_min'] = self.h_min_var.get()
        self.sensitivity_params['h_max'] = self.h_max_var.get()
        self.sensitivity_params['s_min'] = self.s_min_var.get()
        self.sensitivity_params['s_max'] = self.s_max_var.get()
        self.sensitivity_params['v_min'] = self.v_min_var.get()
        self.sensitivity_params['v_max'] = self.v_max_var.get()
        self.sensitivity_params['epsilon_factor'] = self.epsilon_var.get()
        self.sensitivity_params['min_area'] = self.min_area_var.get()
        
        print(f"灵敏度参数已更新: {self.sensitivity_params}")

    def reset_sensitivity(self):
        """重置灵敏度参数为默认值"""
        default_params = {
            'h_min': 0,
            'h_max': 10,
            's_min': 70,
            's_max': 255,
            'v_min': 50,
            'v_max': 255,
            'epsilon_factor': 0.002,
            'min_area': 100
        }
        
        self.sensitivity_params = default_params.copy()
        
        # 更新GUI控件
        self.h_min_var.set(default_params['h_min'])
        self.h_max_var.set(default_params['h_max'])
        self.s_min_var.set(default_params['s_min'])
        self.s_max_var.set(default_params['s_max'])
        self.v_min_var.set(default_params['v_min'])
        self.v_max_var.set(default_params['v_max'])
        self.epsilon_var.set(default_params['epsilon_factor'])
        self.min_area_var.set(default_params['min_area'])
        
        print("灵敏度参数已重置为默认值")

    def save_sensitivity_params(self):
        """保存灵敏度参数到文件"""
        try:
            import json
            with open('sensitivity_params.json', 'w') as f:
                json.dump(self.sensitivity_params, f, indent=4)
            print("灵敏度参数已保存到 sensitivity_params.json")
        except Exception as e:
            print(f"保存参数失败: {e}")

    def load_sensitivity_params(self):
        """从文件加载灵敏度参数"""
        try:
            import json
            with open('sensitivity_params.json', 'r') as f:
                loaded_params = json.load(f)
            
            # 更新参数
            self.sensitivity_params.update(loaded_params)
            
            # 更新GUI控件
            self.h_min_var.set(self.sensitivity_params['h_min'])
            self.h_max_var.set(self.sensitivity_params['h_max'])
            self.s_min_var.set(self.sensitivity_params['s_min'])
            self.s_max_var.set(self.sensitivity_params['s_max'])
            self.v_min_var.set(self.sensitivity_params['v_min'])
            self.v_max_var.set(self.sensitivity_params['v_max'])
            self.epsilon_var.set(self.sensitivity_params['epsilon_factor'])
            self.min_area_var.set(self.sensitivity_params['min_area'])
            
            print("灵敏度参数已从文件加载")
        except FileNotFoundError:
            print("未找到参数文件，使用默认参数")
        except Exception as e:
            print(f"加载参数失败: {e}")

    def move_camera(self, direction):                 ######键盘机械臂控制
        # 这里你可以添加调用外部程序控制摄像头移动的代码
        # 例如使用subprocess调用一个控制摄像头的脚本或程序
        if direction == 'w':
            position["x"] += 10
        elif direction == 'a':
            position["y"] += 10
        elif direction == 's':  
            position["x"] -= 10
        elif direction == 'd':
            position["y"] -= 10
        elif direction == 'q':
            position["z"] -= 10
        elif direction == 'e':
            position["z"] += 10
        
        arm.move_to_position(position["x"],position["y"],position["z"])
        print(f"Moving camera {direction}")
        time.sleep(0.1)

    def improved_calibration(self):
        """改进的标定算法"""
        print("开始改进的标定过程...")
        
        # 更新UI状态
        self.calibration_status_label.config(text="开始标定...")
        self.calibration_progress.config(maximum=5, value=0)
        self.root.update()
        
        scales = []
        successful_calibrations = 0
        calibration_distance = 40  # mm
        max_attempts = 5
        min_successful = 3
        
        # 标定参数
        calibration_params = {
            'distance': 40,
            'max_attempts': 5,
            'min_successful': 3,
            'min_pixel_distance': 10,  # 最小像素距离阈值
            'max_pixel_distance': 200,  # 最大像素距离阈值
            'stability_checks': 3  # 稳定性检查次数
        }
        
        for attempt in range(1, calibration_params['max_attempts'] + 1):
            # 检查是否被取消
            if self.calibration_cancelled:
                print("标定已被用户取消")
                self.root.after(0, lambda: self.calibration_status_label.config(text="标定已取消"))
                self.root.after(0, lambda: self.confirm_button.config(state='normal', text='🚀 开始治疗 (CONFIRM) 🚀'))
                return None
                
            try:
                print(f"标定尝试 {attempt}/{calibration_params['max_attempts']}")
                
                # 更新UI状态（使用after方法确保在UI线程中执行）
                self.root.after(0, lambda: self.calibration_status_label.config(text=f"标定尝试 {attempt}/{calibration_params['max_attempts']}"))
                self.root.after(0, lambda: self.calibration_progress.config(value=attempt-1))
                
                # 1. 获取当前位置的伤口中心（多次检测确保稳定性）
                old_center = self.get_stable_center(calibration_params['stability_checks'])
                if old_center is None:
                    print(f"标定尝试 {attempt} 失败：无法检测到伤口中心")
                    self.root.after(0, lambda: self.calibration_status_label.config(text=f"标定尝试 {attempt} 失败：无法检测到伤口中心"))
                    continue
                
                print(f"当前位置伤口中心: ({old_center[0]:.2f}, {old_center[1]:.2f})")
                
                # 2. 移动机械臂
                target_y = position['y'] - calibration_params['distance']
                print(f"移动机械臂到: ({position['x']}, {target_y}, {position['z']})")
                
                arm.move_to_position(position['x'], target_y, position['z'])
                position["y"] = target_y
                
                # 等待机械臂稳定
                time.sleep(2)
                
                # 3. 获取新位置的伤口中心
                new_center = self.get_stable_center(calibration_params['stability_checks'])
                if new_center is None:
                    print(f"标定尝试 {attempt} 失败：移动后无法检测到伤口中心")
                    # 返回原位置
                    arm.move_to_position(position['x'], position['y'] + calibration_params['distance'], position['z'])
                    position["y"] += calibration_params['distance']
                    continue
                
                print(f"新位置伤口中心: ({new_center[0]:.2f}, {new_center[1]:.2f})")
                
                # 4. 计算像素距离
                pixel_distance = math.sqrt((new_center[0] - old_center[0])**2 + 
                                         (new_center[1] - old_center[1])**2)
                
                print(f"像素距离: {pixel_distance:.2f}px, 物理距离: {calibration_params['distance']}mm")
                
                # 5. 验证像素距离是否合理
                if pixel_distance < calibration_params['min_pixel_distance']:
                    print(f"标定尝试 {attempt} 失败：像素距离过小 ({pixel_distance:.2f}px)")
                    arm.move_to_position(position['x'], position['y'] + calibration_params['distance'], position['z'])
                    position["y"] += calibration_params['distance']
                    continue
                
                if pixel_distance > calibration_params['max_pixel_distance']:
                    print(f"标定尝试 {attempt} 失败：像素距离过大 ({pixel_distance:.2f}px)")
                    arm.move_to_position(position['x'], position['y'] + calibration_params['distance'], position['z'])
                    position["y"] += calibration_params['distance']
                    continue
                
                # 6. 计算比例
                scale = calibration_params['distance'] / pixel_distance
                scales.append(scale)
                successful_calibrations += 1
                
                print(f"标定尝试 {attempt} 成功：比例 = {scale:.4f} mm/px")
                
                # 更新UI状态
                self.root.after(0, lambda: self.calibration_status_label.config(text=f"标定尝试 {attempt} 成功：比例 = {scale:.4f}"))
                
                # 7. 返回原位置
                arm.move_to_position(position['x'], position['y'] + calibration_params['distance'], position['z'])
                position["y"] += calibration_params['distance']
                time.sleep(1)
                
                # 更新摄像头显示
                self.update_camera()
                
            except Exception as e:
                print(f"标定尝试 {attempt} 异常：{e}")
                # 尝试返回安全位置
                try:
                    arm.move_to_position(position['x'], position['y'] + calibration_params['distance'], position['z'])
                    position["y"] += calibration_params['distance']
                except:
                    pass
                continue
        
        # 8. 验证标定结果
        if successful_calibrations < calibration_params['min_successful']:
            raise Exception(f"标定失败：成功次数不足 ({successful_calibrations}/{calibration_params['min_successful']})")
        
        # 9. 计算最终比例（使用中位数，更稳定）
        scales.sort()
        if len(scales) % 2 == 0:
            median_scale = (scales[len(scales)//2 - 1] + scales[len(scales)//2]) / 2
        else:
            median_scale = scales[len(scales)//2]
        
        # 10. 计算标准差，检查一致性
        mean_scale = sum(scales) / len(scales)
        variance = sum((x - mean_scale) ** 2 for x in scales) / len(scales)
        std_dev = math.sqrt(variance)
        cv = std_dev / mean_scale  # 变异系数
        
        print(f"标定完成！")
        print(f"成功次数: {successful_calibrations}/{calibration_params['max_attempts']}")
        print(f"比例范围: {min(scales):.4f} - {max(scales):.4f} mm/px")
        print(f"中位数比例: {median_scale:.4f} mm/px")
        print(f"平均比例: {mean_scale:.4f} mm/px")
        print(f"标准差: {std_dev:.4f}")
        print(f"变异系数: {cv:.4f}")
        
        # 更新UI状态
        self.root.after(0, lambda: self.calibration_progress.config(value=calibration_params['max_attempts']))
        if cv > 0.1:  # 变异系数大于10%时警告
            print("警告：标定结果一致性较差，建议重新标定")
            self.root.after(0, lambda: self.calibration_status_label.config(text=f"标定完成（警告：一致性较差）比例: {median_scale:.4f}"))
        else:
            self.root.after(0, lambda: self.calibration_status_label.config(text=f"标定完成！比例: {median_scale:.4f}"))
        
        return median_scale

    def get_stable_center(self, checks=3):
        """获取稳定的伤口中心（多次检测取平均）"""
        centers = []
        
        for i in range(checks):
            try:
                center_point, df = self.caculate_center()
                if center_point is not None:
                    centers.append(center_point)
                time.sleep(0.5)  # 短暂等待
            except Exception as e:
                print(f"获取中心点失败 (尝试 {i+1}/{checks}): {e}")
                continue
        
        if not centers:
            return None
        
        # 计算平均中心点
        avg_x = sum(center[0] for center in centers) / len(centers)
        avg_y = sum(center[1] for center in centers) / len(centers)
        
        return (avg_x, avg_y)

    def confirm_action(self):  #确认以及后续操作
        try:
            # 禁用确认按钮，启用取消按钮
            self.confirm_button.config(state='disabled', text='标定中...')
            self.cancel_button.config(state='normal')
            self.calibration_cancelled = False
            self.root.update()
            
            # 在后台线程中执行标定
            import threading
            self.calibration_thread = threading.Thread(target=self._run_calibration_background)
            self.calibration_thread.daemon = True
            self.calibration_thread.start()
            
        except Exception as e:
            print(f"启动标定失败: {e}")
            self.confirm_button.config(state='normal', text='🚀 开始治疗 (CONFIRM) 🚀')
            self.cancel_button.config(state='disabled')
            self.calibration_status_label.config(text=f"标定启动失败: {e}")

    def cancel_calibration(self):
        """取消标定过程"""
        self.calibration_cancelled = True
        self.confirm_button.config(state='normal', text='🚀 开始治疗 (CONFIRM) 🚀')
        self.cancel_button.config(state='disabled')
        self.calibration_status_label.config(text="正在取消标定...")
        print("用户取消了标定过程")

    def _run_calibration_background(self):
        """在后台线程中运行标定过程"""
        try:
            # 使用改进的标定算法
            average_scale = self.improved_calibration()
            
            # 在UI线程中更新状态
            self.root.after(0, lambda: self.calibration_status_label.config(text=f"标定完成！比例: {average_scale:.4f}"))
            self.root.after(0, lambda: self.confirm_button.config(state='normal', text='🚀 开始治疗 (CONFIRM) 🚀'))
            self.root.after(0, lambda: self.cancel_button.config(state='disabled'))
            
            print("标定完成，开始后续处理...")
            
            # 坐标转换
            x_offset = position['x']
            y_offset = position['y']
            theta_deg = 90
        
            origondata = CXY.load_coordinates(output_path)
            transferedata = CXY.transform_coordinates(origondata, x_offset, y_offset, theta_deg, average_scale)
            CXY.save_results(transferedata, "transformedresult.csv")
            
            # 生成治疗路径
            WC.process_shape(
            input_file="transformedresult.csv",
            output_file="circle_intersections.csv",
            radius_step=5  # 半径检测步长（单位：坐标单位）
        )
            
            # 执行治疗路径
            self.execute_treatment_with_realtime_camera(average_scale)
            
        except Exception as e:
            print(f"标定或执行过程中发生错误：{e}")
            # 在UI线程中更新错误状态
            self.root.after(0, lambda: self.calibration_status_label.config(text=f"标定失败: {e}"))
            self.root.after(0, lambda: self.confirm_button.config(state='normal', text='🚀 开始治疗 (CONFIRM) 🚀'))
            self.root.after(0, lambda: self.cancel_button.config(state='disabled'))
            # 紧急停止
            self.emergency_stop()
        finally:
            print("治疗完成")



        

 


    
    def execute_treatment_with_realtime_camera(self, scale):
        """执行治疗并实时更新摄像头"""
        print("开始执行治疗路径...")
        
        # 读取治疗路径点
        pointlists = read_coordinates_csv("circle_intersections.csv")
        if not pointlists:
            print("没有找到治疗路径点")
            return
        
        # 设置机械臂参数
        arm.setPID(P=8, I=0)
        arm.move_to_position(position['x'], position['y'], position['z'])
        time.sleep(1)
        
        # 治疗参数
        camera_offset_x = 55
        camera_offset_y = -30
        nozzle_height = 95
        movement_speed = 50  # mm/s
        
        lastx = pointlists[0][0]
        lasty = pointlists[0][1]
        total_points = len(pointlists)
        
        print(f"开始执行 {total_points} 个治疗点...")
        
        for i, point in enumerate(pointlists):
            try:
                # 计算目标位置
                target_x = point[0] + camera_offset_x
                target_y = point[1] + camera_offset_y
                target_z = nozzle_height
                
                # 计算移动距离和时间
                distance = math.sqrt((point[0] - lastx)**2 + (point[1] - lasty)**2)
                move_time = max(distance / movement_speed, 0.5)  # 最小0.5秒
                
                print(f"执行点 {i+1}/{total_points}: ({target_x:.1f}, {target_y:.1f}, {target_z})")
                print(f"移动距离: {distance:.2f}mm, 预计时间: {move_time:.2f}s")
                
                # 移动机械臂
                arm.move_to_position(target_x, target_y, target_z)
                
                # 更新位置记录
                lastx = point[0]
                lasty = point[1]
                
                # 实时更新摄像头显示
                self.update_camera_during_treatment(i+1, total_points, point)
                
                # 等待移动完成
                time.sleep(move_time)
                
                # 执行治疗动作（可以在这里添加具体的治疗逻辑）
                self.execute_treatment_action(i+1, total_points)
                
            except Exception as e:
                print(f"执行第 {i+1} 个点失败：{e}")
                # 可以选择继续或停止
                continue
        
        print("治疗路径执行完成！")

    def update_camera_during_treatment(self, current_point, total_points, point):
        """治疗过程中的实时摄像头更新"""
        try:
            # 获取当前摄像头画面
            ret, frame = self.cap.read()
            if ret:
                # 在画面上显示治疗进度信息
                progress = (current_point / total_points) * 100
                
                # 显示进度信息
                progress_text = f"治疗进度: {progress:.1f}% ({current_point}/{total_points})"
                cv2.putText(frame, progress_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 255, 0), 2)
                
                # 显示当前目标点
                target_text = f"目标点: ({point[0]:.1f}, {point[1]:.1f})"
                cv2.putText(frame, target_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.6, (255, 255, 0), 2)
                
                # 显示当前时间
                import datetime
                time_text = f"时间: {datetime.datetime.now().strftime('%H:%M:%S')}"
                cv2.putText(frame, time_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.5, (255, 255, 255), 1)
                
                # 尝试检测当前伤口状态（可选）
                if self.preview_var.get():
                    coordinates, center_point = self.detect_red_contour(frame)
                    if center_point:
                        center_text = f"伤口中心: ({center_point[0]:.1f}, {center_point[1]:.1f})"
                        cv2.putText(frame, center_text, (10, 120), cv2.FONT_HERSHEY_SIMPLEX, 
                                   0.5, (0, 255, 255), 1)
                
                # 转换并显示
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image)
                self.label.configure(image=photo)
                self.label.image = photo
                
                # 强制更新GUI
                self.root.update_idletasks()
                
        except Exception as e:
            print(f"更新摄像头显示失败：{e}")

    def execute_treatment_action(self, current_point, total_points):
        """执行具体的治疗动作"""
        # 这里可以添加具体的治疗逻辑
        # 例如：喷涂、切割、加热等
        
        # 示例：简单的治疗动作
        print(f"执行治疗动作 {current_point}/{total_points}")
        
        # 可以添加以下功能：
        # 1. 控制治疗设备（如喷涂器、激光器等）
        # 2. 监测治疗参数（温度、压力等）
        # 3. 记录治疗数据
        # 4. 安全检查和异常处理
        
        # 示例治疗时间
        treatment_time = 0.5  # 秒
        time.sleep(treatment_time)

    def emergency_stop(self):
        """紧急停止"""
        print("执行紧急停止...")
        try:
            # 停止机械臂运动
            # arm.stop()  # 如果有停止方法
            print("机械臂已停止")
        except Exception as e:
            print(f"紧急停止失败：{e}")
        
        # 更新摄像头显示停止状态
        try:
            ret, frame = self.cap.read()
            if ret:
                cv2.putText(frame, "EMERGENCY STOP", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           1.0, (0, 0, 255), 3)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
                image = Image.fromarray(frame)
                photo = ImageTk.PhotoImage(image)
                self.label.configure(image=photo)
                self.label.image = photo
        except Exception as e:
            print(f"更新紧急停止显示失败：{e}")
    
    def Savetheshape(self, coordinates):
        """保存形状坐标到CSV文件"""
        df = pd.DataFrame(coordinates, columns=["X", "Y"])
        df.to_csv(output_path, index=False)
        print(f"形状坐标已保存到 {output_path}")

    def on_key_press(self, event):
        key = event.keysym.lower()
        self.move_camera(key)

    def enhanced_real_time_detection(self, frame):
        """增强的实时检测函数"""
        # 图像预处理
        enhanced_frame = self.enhance_image_preprocessing(frame)
        
        # HSV转换
        hsv = cv2.cvtColor(enhanced_frame, cv2.COLOR_BGR2HSV)
        
        # 自适应掩膜
        mask = self.create_adaptive_mask(hsv)
        
        # 形态学处理
        cleaned_mask = self.morphological_cleanup(mask)
        
        # 轮廓检测
        contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 过滤小轮廓
            valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 100]
            
            if valid_contours:
                max_contour = max(valid_contours, key=cv2.contourArea)
                
                # 自适应多边形近似
                perimeter = cv2.arcLength(max_contour, True)
                epsilon = 0.01 * perimeter  # 更精确的近似
                approx_points = cv2.approxPolyDP(max_contour, epsilon, True)
                
                # 计算中心点
                h, w = frame.shape[:2]
                cx, cy = w // 2, h // 2
                coordinates = [(point[0][0] - cx, point[0][1] - cy) for point in approx_points]
                
                # 计算质心
                x_sum, y_sum = 0, 0
                for points in coordinates:
                    x_sum += points[0]
                    y_sum += points[1]
                center_point = (x_sum/len(coordinates), y_sum/len(coordinates))
                
                # 绘制增强的可视化
                cv2.drawContours(frame, [max_contour], -1, (0, 255, 0), 2)  # 原始轮廓
                cv2.drawContours(frame, [approx_points], -1, (255, 0, 0), 2)  # 近似轮廓
                
                # 绘制中心点
                center_pixel = (int(center_point[0] + cx), int(center_point[1] + cy))
                cv2.circle(frame, center_pixel, 5, (0, 0, 255), -1)
                
                # 绘制边界点
                for point in approx_points:
                    cv2.circle(frame, tuple(point[0]), 3, (255, 255, 0), -1)
                
                return coordinates, center_point, max_contour
        
        return None, None, None

    def enhance_image_preprocessing(self, img):
        """图像预处理增强"""
        blurred = cv2.GaussianBlur(img, (3, 3), 0)
        lab = cv2.cvtColor(blurred, cv2.COLOR_BGR2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8,8))
        l = clahe.apply(l)
        enhanced = cv2.merge([l, a, b])
        return cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR)

    def create_adaptive_mask(self, hsv_img):
        """创建自适应颜色掩膜"""
        red_ranges = [
            ([0, 60, 60], [10, 255, 255]),
            ([170, 60, 60], [180, 255, 255]),
            ([0, 40, 40], [15, 255, 255]),
            ([165, 40, 40], [180, 255, 255])
        ]
        
        combined_mask = np.zeros(hsv_img.shape[:2], dtype=np.uint8)
        for lower, upper in red_ranges:
            mask = cv2.inRange(hsv_img, np.array(lower), np.array(upper))
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        return combined_mask

    def morphological_cleanup(self, mask):
        """形态学处理"""
        kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
        
        kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
        
        return mask

    def update_camera(self):
        """更新的摄像头函数"""
        ret, frame = self.cap.read()
        if ret:
            coordinates = None
            center_point = None
            
            # 根据预览开关决定是否进行检测
            if self.preview_var.get():
                # 使用灵敏度参数进行检测
                coordinates, center_point = self.detect_red_contour(frame)
            
            if coordinates is not None:
                self.coordinate_of_edge = coordinates
                self.center_point = center_point
                
                # 显示检测信息
                if center_point:
                    info_text = f"Center: ({center_point[0]:.1f}, {center_point[1]:.1f})"
                    cv2.putText(frame, info_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (255, 255, 255), 2)
                    
                    points_text = f"Points: {len(coordinates)}"
                    cv2.putText(frame, points_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 
                               0.7, (255, 255, 255), 2)
            else:
                # 不进行检测，只显示原始画面
                cv2.putText(frame, "Preview Disabled", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.7, (0, 0, 255), 2)
        
        # 转换并显示
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
        image = Image.fromarray(frame)
        photo = ImageTk.PhotoImage(image)
        self.label.configure(image=photo)
        self.label.image = photo
    
        self.root.after(20, self.update_camera)
    def detect_red_contour(self, frame):
        """改进的红色轮廓检测方法 - 使用可调节的灵敏度参数"""
        # HSV转换
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # 使用灵敏度参数设置红色区间
        lower_red1 = np.array([self.sensitivity_params['h_min'], 
                              self.sensitivity_params['s_min'], 
                              self.sensitivity_params['v_min']])
        upper_red1 = np.array([self.sensitivity_params['h_max'], 
                              self.sensitivity_params['s_max'], 
                              self.sensitivity_params['v_max']])
        lower_red2 = np.array([170, 
                              self.sensitivity_params['s_min'], 
                              self.sensitivity_params['v_min']])
        upper_red2 = np.array([180, 
                              self.sensitivity_params['s_max'], 
                              self.sensitivity_params['v_max']])
        
        # 创建掩膜
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        mask = cv2.bitwise_or(mask1, mask2)
        
        # 寻找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if contours:
            # 过滤小轮廓
            valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > self.sensitivity_params['min_area']]
            
            if valid_contours:
                # 获取最大轮廓
                max_contour = max(valid_contours, key=cv2.contourArea)
                epsilon = self.sensitivity_params['epsilon_factor'] * cv2.arcLength(max_contour, True)
                approx_points = cv2.approxPolyDP(max_contour, epsilon, True)
                
                # 计算相对于图像中心的坐标
                h, w = frame.shape[:2]
                cx, cy = w // 2, h // 2
                coordinates = [(point[0][0] - cx, point[0][1] - cy) for point in approx_points]
                
                # 计算质心
                x_sum, y_sum = 0, 0
                for points in coordinates:
                    x_sum += points[0]
                    y_sum += points[1]
                center_point = (x_sum/len(coordinates), y_sum/len(coordinates))
                
                # 绘制轮廓
                cv2.drawContours(frame, [max_contour], -1, (0, 255, 0), 2)
                cv2.drawContours(frame, [approx_points], -1, (255, 0, 0), 2)
                
                # 绘制边界点
                for point in approx_points:
                    cv2.circle(frame, tuple(point[0]), 3, (255, 255, 0), -1)
                
                # 显示轮廓信息和当前参数
                area = cv2.contourArea(max_contour)
                info_text = f"Area: {int(area)}, Points: {len(approx_points)}"
                param_text = f"H:{self.sensitivity_params['h_min']}-{self.sensitivity_params['h_max']} " \
                           f"S:{self.sensitivity_params['s_min']}-{self.sensitivity_params['s_max']} " \
                           f"V:{self.sensitivity_params['v_min']}-{self.sensitivity_params['v_max']}"
                
                cv2.putText(frame, info_text, (10, 90), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.6, (255, 255, 255), 2)
                cv2.putText(frame, param_text, (10, 110), cv2.FONT_HERSHEY_SIMPLEX, 
                           0.4, (200, 200, 200), 1)
                
                return coordinates, center_point
        
        return None, None
    def caculate_center(self):
        ret, frame = self.cap.read()
        if ret:
            # 伤口识别（红色区域）
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 使用灵敏度参数设置红色区间
            lower_red1 = np.array([self.sensitivity_params['h_min'], 
                                  self.sensitivity_params['s_min'], 
                                  self.sensitivity_params['v_min']])
            upper_red1 = np.array([self.sensitivity_params['h_max'], 
                                  self.sensitivity_params['s_max'], 
                                  self.sensitivity_params['v_max']])
            lower_red2 = np.array([170, 
                                  self.sensitivity_params['s_min'], 
                                  self.sensitivity_params['v_min']])
            upper_red2 = np.array([180, 
                                  self.sensitivity_params['s_max'], 
                                  self.sensitivity_params['v_max']])

            # 创建掩膜
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)
            h,w=frame.shape[:2]
            # 寻找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # 过滤小轮廓
                valid_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > self.sensitivity_params['min_area']]
                
                if valid_contours:
                # 获取最大轮廓
                    max_contour = max(valid_contours, key=cv2.contourArea)
                    epsilon = self.sensitivity_params['epsilon_factor'] * cv2.arcLength(max_contour, True)
                approx_points = cv2.approxPolyDP(max_contour, epsilon, True)
                cx, cy = w // 2, h // 2
                coordinates = [(point[0][0] - cx, point[0][1] - cy) for point in approx_points]
                coordinate_of_edge=coordinates
                x_sum,y_sum=0,0
                for points in coordinates:
                    x_sum+=points[0]
                    y_sum+=points[1]
                Centerpoint=(x_sum/len(coordinates),y_sum/len(coordinates))
                print("centerpoint:",Centerpoint,"WIDTH::",w,"HEIGHT::",h)
                print("使用灵敏度参数:", self.sensitivity_params)
                df = pd.DataFrame(coordinates, columns=["X", "Y"])
                df.to_csv(output_path, index=False)
                return Centerpoint,df

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

if __name__ == "__main__":
    try:
        arm.move_to_position(position['x'],position['y'],position['z'])
    except:
        print("机械臂连接失败，请检查连接")
    time.sleep(1)
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()
