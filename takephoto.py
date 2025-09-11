import cv2
import os
from datetime import datetime

def capture_photo(save_dir="captured_photos"):
    """
    调用USB摄像头拍摄照片并保存
    
    参数:
        save_dir: 照片保存的目录
        
    返回:
        保存的照片路径，如果出错则返回None
    """
    # 创建保存目录（如果不存在）
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    # 生成唯一的文件名（基于当前时间）
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"photo_{timestamp}.jpg"
    save_path = os.path.join(save_dir, filename)
    
    # 尝试打开摄像头（0通常是默认的USB摄像头）
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("无法打开摄像头，请检查设备是否连接正确")
        return None
    
    try:
        # 读取一帧图像
        ret, frame = cap.read()
        
        if not ret:
            print("无法获取图像")
            return None
        
        # 保存图像
        cv2.imwrite(save_path, frame)
        print(f"照片已保存至: {save_path}")
        return save_path
        
    finally:
        # 释放摄像头资源
        cap.release()

if __name__ == "__main__":
    # 调用函数拍摄照片并获取保存路径
    photo_path = capture_photo()
    
    # 如果需要在其他程序中使用，可以直接使用这个路径
    if photo_path:
        print(f"返回的照片地址: {photo_path}")