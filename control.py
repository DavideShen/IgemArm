import serial
import time
import json
import numpy as np
import countbyhand as CO


class RoArmControl:
    def __init__(self, port='COM3', baudrate=115200):
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
        """发送JSON指令到机械臂"""
        command_str = json.dumps(command_dict) + '\n'
        self.ser.write(command_str.encode('utf-8'))
        #print(f"Sent: {command_str.strip()}")

        
        response = self.ser.readline().decode().strip()
        #if response:
            #print(f"Received: {response}")

    def set_end_position(self, x, y, z,t=3.1415/2,g=3.14,speed=0):
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
        command = {
            "T": 105
        }
        self.send_command(command)
        response=  self.ser.readline().decode().strip()
        print(response)
        try:
            data = json.loads(response)
            return [data['x'], data['y'], data['z']]
        except json.JSONDecodeError:
            print("Failed to decode JSON response")
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

        
 #zeropoint       (175,0,75)
 # centerpoint  (250,-15,75)
# stoppoint    (-50,0,200)
# 示例使用

if __name__ == "__main__":
    arm = RoArmControl(port='COM3')
    arm.setPID(P=8,I=0)
    command=CO.anglecommandgenerator(175,100,75)
    arm.send_command(command)
    
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