import serial
import time
import json
import numpy as np
import countbyhand as CO
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import threading
import queue

class externalcontrol:
    def __init__(self,port='COM4',baudrate=115200):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        time.sleep(2)  # 等待串口初始化
        print(f"Connected to {self.ser.name}")
    def send_command(self, command_dict):
        """发送JSON指令到主板"""
        command_str = json.dumps(command_dict) + '\n'
        self.ser.write(command_str.encode('utf-8'))
    def close(self):
        self.ser.close()
    def pumpcontrol(self,contition=True,way=True,speed=255):
        """控制吸泵"""
        command = {
            "T": 201,  
            "state":speed
        }
        
        response = self.ser.readline().decode().strip()
        #if response:
            #print(f"Received: {response}")
class RoArmControl:
    def __init__(self, port='COM3', baudrate=115200, enable_logging=True):
        self.ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=1
        )
        time.sleep(2)
        print(f"Connected to {self.ser.name}")
        
        # 数据记录相关
        self.enable_logging = enable_logging
        self.position_data = []
        self.data_queue = queue.Queue()
        self.logging_thread = None
        self.stop_logging = False
        
        # 位置和状态监听相关
        self.current_position = [0, 0, 0]
        self.current_joint_angles = {}
        self.current_joint_loads = {}
        self.position_monitoring = False
        self.monitor_thread = None
        
        if self.enable_logging:
            self.start_logging()
        
        # 启动位置监听
        self.start_position_monitoring()

    def start_logging(self):
        """启动数据记录线程"""
        self.stop_logging = False
        self.logging_thread = threading.Thread(target=self._logging_worker)
        self.logging_thread.daemon = True
        self.logging_thread.start()

    def _logging_worker(self):
        """数据记录工作线程"""
        while not self.stop_logging:
            try:
                # 定期获取当前位置
                current_pos = self.getcurrentposition()
                if current_pos:
                    timestamp = datetime.now()
                    data_point = {
                        'timestamp': timestamp,
                        'x': current_pos[0],
                        'y': current_pos[1],
                        'z': current_pos[2]
                    }
                    self.position_data.append(data_point)
                time.sleep(0.02)  # 50Hz采样率 (提高频率)
            except Exception as e:
                print(f"Logging error: {e}")
                time.sleep(0.1)

    def send_command(self, command_dict):
        """发送JSON指令到机械臂"""
        command_str = json.dumps(command_dict) + '\n'
        self.ser.write(command_str.encode('utf-8'))
        response = self.ser.readline().decode().strip()
        return response

    def set_end_position(self, x, y, z,t=3.1415/2,g=3.14,speed=0.08):
        """设置末端执行器位置（单位：毫米）"""
        # 301: 末端位置控制指令
        # speed: 0-255 (0最快，255最慢)
        command = {
            "T": 104,
            "x": x,
            "y": y,
            "z": z,
            "t": t,
            "g":g,
            "spd": speed
        }
        self.send_command(command)

    def close(self):
        self.stop_logging = True
        if self.logging_thread:
            self.logging_thread.join(timeout=2)
        self.ser.close()
        print("Serial connection closed")

    def zero(self):
        command = {
            "T": 100
        }
        self.send_command(command)
    
    def setPID(self,P=8,I=0):
        for i in range(1,7):
            command={"T":108,"joint":i,"p":P,"i":I}
            self.send_command(command)

    def getcurrentposition(self):
        """获取当前末端执行器位置"""
        command = {"T": 105}
        response = self.send_command(command)
        try:
            data = json.loads(response)
            return [data['x'], data['y'], data['z']]
        except (json.JSONDecodeError, KeyError):
            return None

    def move_to_position_straight(self,startpoint,endpoint,gap=10):
        """移动到指定位置"""
        # 301: 末端位置控制指令
        
        
    
        distance=((startpoint[0]-endpoint[0])**2+(startpoint[1]-endpoint[1])**2+(startpoint[2]-endpoint[2])**2)**0.5
        point_number=max(1,int(distance/gap)+1)
        print(point_number,distance)
        points = np.linspace(startpoint, endpoint, point_number)
        
        for point in points:    
            command = CO.anglecommandgenerator(point[0],point[1],point[2])
            print(command)
            self.send_command(command)
            time.sleep(0.020)
    def move_to_position(self,x,y,z):
        command=CO.anglecommandgenerator(x,y,z)
        self.send_command(command)

    def save_position_data(self, filename=None):
        """保存位置数据到CSV文件"""
        if not filename:
            filename = f"arm_position_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        if self.position_data:
            df = pd.DataFrame(self.position_data)
            df.to_csv(filename, index=False)
            print(f"位置数据已保存到: {filename}")
            return filename
        else:
            print("没有数据可保存")
            return None

    def start_position_monitoring(self):
        """启动位置监听"""
        self.position_monitoring = True
        self.monitor_thread = threading.Thread(target=self._position_monitor_worker)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def stop_position_monitoring(self):
        """停止位置监听"""
        self.position_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)

    def _position_monitor_worker(self):
        """位置监听工作线程 - 增强版"""
        while getattr(self, 'position_monitoring', False):
            try:
                # 持续监听串口
                if self.ser.in_waiting > 0:
                    response = self.ser.readline().decode().strip()
                    if response:
                        try:
                            data = json.loads(response)
                            # 检查是否为位置反馈数据 (T:1051)
                            if data.get('T') == 1051:
                                # 更新当前位置和状态
                                self.current_position = [data['x'], data['y'], data['z']]
                                self.current_joint_angles = {
                                    'tit': data.get('tit', 0),  # 末端关节姿态
                                    'b': data.get('b', 0),     # 基础关节
                                    's': data.get('s', 0),     # 肩关节
                                    'e': data.get('e', 0),     # 肘关节
                                    't': data.get('t', 0),     # 手腕关节1
                                    'r': data.get('r', 0),     # 手腕关节2
                                    'g': data.get('g', 0)      # 末端关节
                                }
                                self.current_joint_loads = {
                                    'tB': data.get('tB', 0),   # 基础关节负载
                                    'tS': data.get('tS', 0),   # 肩关节负载
                                    'tE': data.get('tE', 0),   # 肘关节负载
                                    'tT': data.get('tT', 0),   # 手腕关节1负载
                                    'tR': data.get('tR', 0)    # 手腕关节2负载
                                }
                                
                                # 如果启用了数据记录
                                if self.enable_logging:
                                    timestamp = datetime.now()
                                    data_point = {
                                        'timestamp': timestamp,
                                        'x': data['x'],
                                        'y': data['y'],
                                        'z': data['z'],
                                        'tit': data.get('tit', 0),
                                        'base_angle': data.get('b', 0),
                                        'shoulder_angle': data.get('s', 0),
                                        'elbow_angle': data.get('e', 0),
                                        'wrist1_angle': data.get('t', 0),
                                        'wrist2_angle': data.get('r', 0),
                                        'end_angle': data.get('g', 0),
                                        'base_load': data.get('tB', 0),
                                        'shoulder_load': data.get('tS', 0),
                                        'elbow_load': data.get('tE', 0),
                                        'wrist1_load': data.get('tT', 0),
                                        'wrist2_load': data.get('tR', 0)
                                    }
                                    self.position_data.append(data_point)
                        except (json.JSONDecodeError, KeyError) as e:
                            1==1
            
                time.sleep(0.01)  # 10ms间隔
            except Exception as e:
                print(f"Position monitoring error: {e}")
                time.sleep(0.1)

    def get_current_joint_status(self):
        """获取当前关节状态"""
        return {
            'position': self.current_position.copy(),
            'joint_angles': self.current_joint_angles.copy(),
            'joint_loads': self.current_joint_loads.copy()
        }
        
 #zeropoint       (175,0,75)
 # centerpoint  (250,-15,75)
# stoppoint    (-50,0,200)
# 示例使用

if __name__ == "__main__":
    arm = RoArmControl(port='COM3')
    arm.setPID(P=8,I=0)
    command=CO.anglecommandgenerator(175,100,75)
    arm.send_command(command)
    point=(175,100,75)
    
    while True:
        print("请输入移动方式:")
        print("1.直接移动104")
        print("2.曲线移动102")
  
        print("5.退出")
        choice=input("请输入移动方式:")
        
        if choice=="1":
            while True:
                try:
                    
                    arm.set_end_position(point[0],point[1],point[2])
                    movelength=float(input("请输入移动长度:"))
                    arm.set_end_position(point[0]+movelength,point[1]+movelength,point[2])
                    time.sleep(3)
                except ValueError:
                    break
           


        if choice=="2":
            while True:
                try:
                    
                    arm.move_to_position(point[0],point[1],point[2])
                    movelength=float(input("请输入移动长度:"))
                    arm.move_to_position(point[0]+movelength,point[1]+movelength,point[2])
                    time.sleep(3)
                except ValueError:
                    break
        if choice=="5":
            break
        
        
        
    '''time.sleep(2)
    startpoint=np.array([175,-100,75])
    endpoint=np.array([175,100,100])
    arm.move_to_position(startpoint,endpoint,gap=5)'''

    
   

# 计算20个中间点
    '''num_points = 20
    points = np.linspace(startpoint, endpoint, num_points)
    command = CO.anglecommandgenerator(points[0][0],points[0][1],points[0][2])
    arm.send_command(command)
    time.sleep(1)
# 打印出这20个中间点
    for point in points:
        print(point)
        command = CO.anglecommandgenerator(point[0],point[1],point[2])
        arm.send_command(command)
        time.sleep(0.1)


    startpoint = np.array([200, -15, 100])
    endpoint = np.array([200, 15, 100])

# 计算20个中间点
    num_points = 20
    points = np.linspace(startpoint, endpoint, num_points)
    command = CO.anglecommandgenerator(points[0][0],points[0][1],points[0][2])
    arm.send_command(command)
    time.sleep(1)
# 打印出这20个中间点
    for point in points:
        print(point)
        command = CO.anglecommandgenerator(point[0],point[1],point[2])
        arm.send_command(command)
        time.sleep(0.1)
    
    startpoint = np.array([200, -15, 200])
    endpoint = np.array([200, 15, 200])

# 计算20个中间点
    num_points = 20
    points = np.linspace(startpoint, endpoint, num_points)
    command = CO.anglecommandgenerator(points[0][0],points[0][1],points[0][2])
    arm.send_command(command)
    time.sleep(1)
# 打印出这20个中间点
    for point in points:
        print(point)
        command = CO.anglecommandgenerator(point[0],point[1],point[2])
        arm.send_command(command)
        time.sleep(0.1)

    startpoint = np.array([100, -15, 200])
    endpoint = np.array([100, 15, 200])

# 计算20个中间点
    num_points = 20
    points = np.linspace(startpoint, endpoint, num_points)
    command = CO.anglecommandgenerator(points[0][0],points[0][1],points[0][2])
    arm.send_command(command)
    time.sleep(1)
# 打印出这20个中间点
    for point in points:
        print(point)
        command = CO.anglecommandgenerator(point[0],point[1],point[2])
        arm.send_command(command)
        time.sleep(0.1)
    startpoint = np.array([100, -15, 100])
    endpoint = np.array([100, 15, 100])

# 计算20个中间点
    num_points = 20
    points = np.linspace(startpoint, endpoint, num_points)
    command = CO.anglecommandgenerator(points[0][0],points[0][1],points[0][2])
    arm.send_command(command)
    time.sleep(1)
# 打印出这20个中间点
    for point in points:
        print(point)
        command = CO.anglecommandgenerator(point[0],point[1],point[2])
        arm.send_command(command)
        time.sleep(0.1)'''
    
    
    
    
    
    
    time.sleep(4)

    


    arm.close()
    
    

    




        # 控制夹爪



    arm.close()
