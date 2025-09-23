import cv2

import numpy as np

import pandas as pd


def process_blue_area(image_path,output_path):
    # 阶段1：读取图片
    img = cv2.imread(image_path)   
    if img is None:
        raise ValueError("无法读取图片，请检查路径是否正确")

    # 阶段2：处理红色部分（更大范围）
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # 红色有两个区间
    lower_red1 = np.array([0, 70, 50])
    upper_red1 = np.array([10, 255, 255])
    lower_red2 = np.array([170, 70, 50])
    upper_red2 = np.array([180, 255, 255])

    # 创建掩膜
    mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
    mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
    mask = cv2.bitwise_or(mask1, mask2)

    # 阶段3：提取边界点
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        print("未检测到红色区域")
        return pd.DataFrame()

    # 获取最大轮廓
    max_contour = max(contours, key=cv2.contourArea)
    # 多边形近似（减少坐标点数量）
    epsilon = 0.002 * cv2.arcLength(max_contour, True)
    approx_points = cv2.approxPolyDP(max_contour, epsilon, True)
    # 获取图像中心
    h, w = img.shape[:2]
    cx, cy = w // 2, h // 2
    # 转换为以图像中心为原点的坐标列表
    coordinates = [(point[0][0] - cx, point[0][1] - cy) for point in approx_points]
    # 阶段4：创建表格输出
    df = pd.DataFrame(coordinates, columns=["X", "Y"])
    # 可视化结果（可选）
    cv2.drawContours(img, [approx_points], -1, (0, 255, 0), 2)
    cv2.imshow("Result", img)
    cv2.waitKey(0)
    cv2.destroyAllWindows()
    df.to_csv(output_path, index=False)
    return df


# 使用示例

if __name__ == "__main__":
    df_result = process_blue_area("captured_photos\WIN_20250819_20_42_25_Pro.jpg","test.csv")

    print("边界坐标表格：")

    print(df_result)

    # 保存为CSV文件

