import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import subprocess
import threading
import numpy as np
import pandas as pd
MAXcounter= 0
output_path = "coordinates.csv"
h,w=0,0
class CameraApp:
    def __init__(self, root):
        self.root = root
        self.root.title("摄像头实时画面与伤口识别")

        # 打开摄像头
        self.cap = cv2.VideoCapture(0).

        # 创建GUI元素
        self.label = ttk.Label(root)
        self.label.pack()

        # 控制按钮
        self.control_frame = ttk.Frame(root)
        self.control_frame.pack()

        self.w_button = ttk.Button(self.control_frame, text="W", command=lambda: self.move_camera('w'))
        self.w_button.grid(row=0, column=1)
        self.a_button = ttk.Button(self.control_frame, text="A", command=lambda: self.move_camera('a'))
        self.a_button.grid(row=0, column=0)
        self.s_button = ttk.Button(self.control_frame, text="S", command=lambda: self.move_camera('s'))
        self.s_button.grid(row=0, column=2)
        self.d_button = ttk.Button(self.control_frame, text="D", command=lambda: self.move_camera('d'))
        self.d_button.grid(row=0, column=3)

        self.q_button = ttk.Button(self.control_frame, text="Q", command=lambda: self.move_camera('q'))
        self.q_button.grid(row=1, column=0)
        self.e_button = ttk.Button(self.control_frame, text="E", command=lambda: self.move_camera('e'))
        self.e_button.grid(row=1, column=3)

        self.confirm_button = ttk.Button(self.control_frame, text="确定", command=self.confirm_action)
        self.confirm_button.grid(row=1, column=1, columnspan=2)

        # 绑定键盘事件
        self.root.bind('<Key>', self.on_key_press)
        self.root.focus_set()

        # 开始更新摄像头画面
        self.update_camera()

    def move_camera(self, direction):
        # 这里你可以添加调用外部程序控制摄像头移动的代码
        # 例如使用subprocess调用一个控制摄像头的脚本或程序
        print(f"Moving camera {direction}")

    def confirm_action(self):
        # 这里你可以添加调用外部程序执行确定操作的代码
        epsilon = 0.002 * cv2.arcLength(max_contour, True)
        approx_points = cv2.approxPolyDP(max_contour, epsilon, True)
        # 获取图像中心
        h, w = img.shape[:2]
        cx, cy = w // 2, h // 2
        # 转换为以图像中心为原点的坐标列表
        coordinates = [(point[0][0] - cx, point[0][1] - cy) for point in approx_points] # 阶段4：创建表格输出
        df = pd.DataFrame(coordinates, columns=["X", "Y"])
        df.to_csv(output_path, index=False)
        print("Confirm action")

    def on_key_press(self, event):
        key = event.keysym.lower()
        self.move_camera(key)

    def update_camera(self):
        # 读取摄像头帧
        ret, frame = self.cap.read()
        if ret:
            # 伤口识别（红色区域）
            hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

            # 红色有两个区间
            lower_red1 = np.array([0, 70, 50])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 70, 50])
            upper_red2 = np.array([180, 255, 255])

            # 创建掩膜
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)

            # 寻找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # 获取最大轮廓
                max_contour = max(contours, key=cv2.contourArea)
                # 在原图上绘制轮廓
                cv2.drawContours(frame, [max_contour], -1, (0, 255, 0), 2)
                MAXcounter=max_contour

            # 转换颜色从BGR到RGBA
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            # 转换为Image
            image = Image.fromarray(frame)
            # 转换为ImageTk
            photo = ImageTk.PhotoImage(image)
            # 显示图片
            # 更新标签
            self.label.configure(image=photo)
            self.label.image = photo

        # 每隔10毫秒更新一次
        self.root.after(10, self.update_camera)

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

if __name__ == "__main__":
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()