import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import subprocess
import threading
import numpy as np
import pandas as pd
import control
import time
import math
import os
import MAINCONTROL as MC
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
postion={"x":150,"y":0,"z":180}
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
        self.root.title("摄像头实时画面与伤口识别")

        # 打开摄像头
        self.cap = cv2.VideoCapture(0)

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

    def move_camera(self, direction):                 ######键盘机械臂控制
        # 这里你可以添加调用外部程序控制摄像头移动的代码
        # 例如使用subprocess调用一个控制摄像头的脚本或程序
        if direction == 'w':
            postion["x"] += 10
        elif direction == 'a':
            postion["y"] += 10
        elif direction == 's':  
            postion["x"] -= 10
        elif direction == 'd':
            postion["y"] -= 10
        elif direction == 'q':
            postion["z"] -= 10
        elif direction == 'e':
            postion["z"] += 10
        
        arm.move_to_position(postion["x"],postion["y"],postion["z"])
        print(f"Moving camera {direction}")
        time.sleep(0.1)

    def confirm_action(self):  #确认以及后续操作
        scales=[]
        for i in range(1,6):
            oldcenterpoint,df=self.caculate_center()
            arm.move_to_position(postion['x'],postion['y']-40,postion['z'])
            postion["y"]-=40
            time.sleep(1)
        
        
            print("sleep 2s")
        
            time.sleep(1)
            print("update camera")
            newcenterpoint,df=self.caculate_center() 
            distance_of_piexel=math.sqrt((newcenterpoint[0]-oldcenterpoint[0])**2+(newcenterpoint[1]-oldcenterpoint[1])**2)
            print("像素距离：",distance_of_piexel,"物理距离：60mm")
            distance_of_onepiexel=40/distance_of_piexel
            print("每像素距离：",distance_of_onepiexel)
            postion["y"]+=40
            arm.move_to_position(postion['x'],postion['y'],postion['z'])
            self.update_camera()
            scales.append(distance_of_onepiexel)
            time.sleep(1)
        postion["y"]-=40
        average_scale=sum(scales)/len(scales)
        print("Actionconfirmed!")
        x_offset = postion['x']
        y_offset = postion['y']
        theta_deg = 90
        
        origondata=CXY.load_coordinates(output_path)
        transferedata=CXY.transform_coordinates(origondata,x_offset,y_offset,theta_deg,average_scale)
        #CXY.plot_preview(origondata,transferedata)
        CXY.save_results(transferedata,"transformedresult,csv")
        WC.process_shape(
        input_file="transformedresult,csv",
        output_file="circle_intersections.csv",
        radius_step=5  # 半径检测步长（单位：坐标单位）
        )
        pointlists=read_coordinates_csv("circle_intersections.csv")
    # 连接串口
        
        arm.setPID(P=8,I=0)
        arm.move_to_position(postion['x'],postion['y'],postion['z'])
        time.sleep(1)
        lastx=pointlists[0][0]
        lasty=pointlists[0][1]  
        for point in pointlists:
            distance=math.sqrt((point[0]-lastx)**2+(point[1]-lasty)**2)
            lastx=point[0]
            lasty=point[1]
            x=point[0]+55  #####摄像头偏移矫正
            y=point[1]-30 #####摄像头偏移矫正
            arm.move_to_position(x,y,95)   ####喷嘴高度矫正
            time.sleep(distance/50)
    
        
        print("完成")
        #arm.move_to_position(postion['x'],postion['y'],postion['z'])



        

 


    
    def Savetheshape(self,coordinates):
        df = pd.DataFrame(coordinates, columns=["X", "Y"])
        


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
            h,w=frame.shape[:2]
            # 寻找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # 获取最大轮廓

                max_contour = max(contours, key=cv2.contourArea)
                epsilon = 0.02 * cv2.arcLength(max_contour, True)
                approx_points = cv2.approxPolyDP(max_contour, epsilon, True)
                cx, cy = w // 2, h // 2
                coordinates = [(point[0][0] - cx, point[0][1] - cy) for point in approx_points]
                coordinate_of_edge=coordinates
                x_sum,y_sum=0,0
                for points in coordinates:
                    x_sum+=points[0]
                    y_sum+=points[1]
                Centerpoint=(x_sum/len(coordinates),y_sum/len(coordinates))
               # print("centerpoint:",Centerpoint,"WIDTH::",w,"HEIGHT::",h)
                   
                # 在原图上绘制轮廓
                cv2.drawContours(frame, [approx_points], -1, (0, 255, 0), 2)


            # 转换颜色从BGR到RGBA
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGBA)
            image=frame
            
            # 转换为Image
            image = Image.fromarray(frame)
            # 转换为ImageTk
            photo = ImageTk.PhotoImage(image)
            # 显示图片
            # 更新标签
            self.label.configure(image=photo)
            self.label.image = photo

        # 每隔10毫秒更新一次
        self.root.after(20, self.update_camera)
    def caculate_center(self):
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
            h,w=frame.shape[:2]
            # 寻找轮廓
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if contours:
                # 获取最大轮廓

                max_contour = max(contours, key=cv2.contourArea)
                epsilon = 0.02 * cv2.arcLength(max_contour, True)
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
                df = pd.DataFrame(coordinates, columns=["X", "Y"])
                df.to_csv(output_path, index=False)
                return Centerpoint,df

    def __del__(self):
        if self.cap.isOpened():
            self.cap.release()

if __name__ == "__main__":
    try:
        arm.move_to_position(postion['x'],postion['y'],postion['z'])
    except:
        print("机械臂连接失败，请检查连接")
    time.sleep(1)
    root = tk.Tk()
    app = CameraApp(root)
    root.mainloop()