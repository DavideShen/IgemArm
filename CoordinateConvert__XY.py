import pandas as pd
import matplotlib.pyplot as plt
import math
import argparse
import sys

def load_coordinates(input_source):
    """加载坐标数据"""
    if input_source.endswith('.csv'):
        try:
            df = pd.read_csv(input_source)
            return list(zip(df['X'], df['Y']))
        except Exception as e:
            print(f"CSV读取错误: {str(e)}")
            sys.exit(1)
    else:
        try:
            return [tuple(map(float, pair.split(',')))
                   for pair in input_source.split()]
        except:
            print("输入格式错误，请使用：x1,y1 x2,y2 ...")
            sys.exit(1)


def transform_coordinates(coords, x_offset, y_offset, theta_deg, scale):
    """坐标转换核心函数（先旋转再缩放平移）"""
    theta = math.radians(theta_deg)
    cos_theta = math.cos(theta)
    sin_theta = math.sin(theta)
    transformed = []

    for x, y in coords:
        y=0-y
        # 先旋转（逆时针）
        rx = x * cos_theta + y * sin_theta
        ry = -x * sin_theta + y * cos_theta

        # 再缩放
        sx = rx * scale
        sy = ry * scale

        # 最后平移
        new_x = sx + x_offset
        new_y = sy + y_offset

        transformed.append((new_x, new_y))

    return transformed

def save_results( transformed, output_path):
    """保存结果到CSV"""
    df = pd.DataFrame({

        'Transformed_X': [x for x, y in transformed],
        'Transformed_Y': [y for x, y in transformed]
    })
    df.to_csv(output_path, index=False)
    print(f"结果已保存至：{output_path}")
# 使用示例
def plot_preview(original, transformed):
    """可视化对比图"""
    plt.figure(figsize=(10, 5))

    # 原始坐标（蓝色）
    ox, oy = zip(*original)
    plt.scatter(ox, oy, c='blue', label='原始坐标', zorder=2)

    # 转换后坐标（红色）
    tx, ty = zip(*transformed)
    plt.scatter(tx, ty, c='red', label='转换后坐标', zorder=2)

    # 添加连接线
    for i in range(len(original)):
        plt.plot([ox[i], tx[i]], [oy[i], ty[i]],
                 'gray', linestyle='--', alpha=0.5, zorder=1)

    plt.title('坐标转换预览')
    plt.xlabel('X轴')
    plt.ylabel('Y轴')
    plt.grid(True, linestyle='--', alpha=0.6)
    plt.legend()
    plt.show()
if __name__ == "__main__":
    # 示例参数：新坐标系原点在(2,3)，逆时针旋转30度，缩放0.5倍
    x_offset = -250
    y_offset = 15
    theta_deg = 0
    scale = 0.5


    origondata=load_coordinates("test.csv")
    transferedata=transform_coordinates(origondata,x_offset,y_offset,theta_deg,scale)
    save_results(transferedata,"transformedresult,csv")
    plot_preview(origondata,transferedata)