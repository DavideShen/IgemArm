import time
import takephoto
import PngRead
import control
import countbyhand as CO
import numpy as np
import CoordinateConvert__XY as CXY
import WenxingCircle as WC
import csv

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


if __name__ == "__main__":
    # 设置摄像头拍照路径
    #picturepath=takephoto.capture_photo()
    PngRead.process_blue_area("captured_photos\WIN_20250819_20_42_25_Pro.jpg","Pictureredresult.csv")
    # 读取csv文件并转换坐标系  #################
    x_offset = -15
    y_offset = 250
    theta_deg = -90
    scale = 1
    origondata=CXY.load_coordinates("Pictureredresult.csv")
    transferedata=CXY.transform_coordinates(origondata,x_offset,y_offset,theta_deg,scale)
    CXY.save_results(transferedata,"transformedresult,csv")
    WC.process_shape(
        input_file="transformedresult,csv",
        output_file="circle_intersections.csv",
        radius_step=0.5  # 半径检测步长（单位：坐标单位）
    )
    pointlists=read_coordinates_csv("circle_intersections.csv")
    # 连接串口
    arm=control.RoArmControl()
    arm.setPID(P=8,I=0)
    arm.move_to_position(175,0,75)
    time.sleep(1)
    for point in pointlists:
        x=point[0]
        y=point[1]
        arm.move_to_position(x,y,75)
        time.sleep(1)
    arm.close()


    

    
