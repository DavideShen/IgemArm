import math


def cartesian_to_polar(x, y, degrees=False):
    """
    将直角坐标 (x, y) 转换为极坐标 (r, θ)
    
    参数:
        x (float): 直角坐标系的x值
        y (float): 直角坐标系的y值
        degrees (bool): 若为True，角度θ返回度数；否则返回弧度（默认）
    
    返回:
        tuple: (r, θ) 
        若输入无效（非数值），返回 (None, None)
    """
    try:
        # 计算极径 r = √(x² + y²)
        r = math.sqrt(x**2 + y**2)
        
        # 计算极角 θ = atan2(y, x)（弧度制，范围[-π, π]）
        theta = math.atan2(y, x)
        
        # 转换为度数（若需要）
        if degrees:
            theta = math.degrees(theta)
            # 调整角度到 [0, 360) 范围
            if theta < 0:
                theta += 360
        
        return theta
    except:
        return {"r": None, "BASE": None}

def calculate_elbow_angle(x,y,z):
    l3=math.sqrt(x**2+y**2+z**2)
    l1=238.7127
    l2=145
    # 使用余弦定理计算角度: c² = a² + b² - 2ab·cos(C)
    cos_C = (l1**2 + l2**2 - l3**2) / (2 * l1 * l2)
    
    # 确保cos值在[-1, 1]范围内 (浮点数精度问题可能导致超出范围)
    cos_C = max(min(cos_C, 1.0), -1.0)
    
    # 计算角度弧度
    angle_C = math.pi - math.acos(cos_C)
    
    return angle_C-0.12600731876944798
def calculate_shoulder_angle(x,y,z):
    distance=math.sqrt(x**2+y**2+z**2)
    
    angle=math.acos(math.sqrt(x**2+y**2)/distance)
    
    angle2=math.acos((238.7127**2+distance**2-145**2)/(2*238.7127*distance))
    return 3.1415926/2-(angle2+0.12600731876944798+angle)
def calculate_all_angles(x,y,z):
    base=cartesian_to_polar(x,y)
    shoulder=calculate_shoulder_angle(x,y,z)
    elbow=calculate_elbow_angle(x,y,z)
    return{"base":base,"shoulder":shoulder,"elbow":elbow}

def anglecommandgenerator(x,y,z,speed=0,acc=10):
    angles=calculate_all_angles(x,y,z)
    command={"T":102,"base":angles["base"],"shoulder":angles["shoulder"],"elbow":angles["elbow"],"wrist":math.pi-angles["elbow"]-angles["shoulder"]-0.1,"roll":angles["base"],"hand":3.14,"spd":speed,"acc":acc}
    return command
    


if __name__ == '__main__':
    
    print(anglecommandgenerator(275,0,55))
    
          


    
    