import csv
import math
import matplotlib.pyplot as plt


def read_coordinates(input_file):
    """读取CSV文件中的坐标点"""
    points = []
    try:
        with open(input_file, 'r') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2:
                    try:
                        x = float(row[0])
                        y = float(row[1])
                        points.append((x, y))
                    except ValueError:
                        continue
        if not points:
            raise ValueError("未找到有效坐标数据")
        return points
    except FileNotFoundError:
        raise FileNotFoundError(f"文件 {input_file} 不存在")


def cartesian_to_polar(x, y):
    """将直角坐标转换为极坐标（角度单位：度）"""
    r = math.sqrt(x ** 2 + y ** 2)
    theta = math.degrees(math.atan2(y, x))
    return r, theta


def find_circle_intersections(line_start, line_end, radius):
    """计算线段与圆的交点"""
    # 线段参数方程：P = P0 + t*(P1-P0), t ∈ [0,1]
    x0, y0 = line_start
    x1, y1 = line_end
    dx = x1 - x0
    dy = y1 - y0

    # 圆的方程：x² + y² = r²
    # 代入线段方程：(x0 + t*dx)² + (y0 + t*dy)² = r²
    # 展开：t²*(dx²+dy²) + 2t*(x0dx+y0dy) + (x0²+y0² - r²) = 0
    a = dx ** 2 + dy ** 2
    b = 2 * (x0 * dx + y0 * dy)
    c = x0 ** 2 + y0 ** 2 - radius ** 2

    discriminant = b ** 2 - 4 * a * c
    intersections = []

    if discriminant >= 0:
        t1 = (-b + math.sqrt(discriminant)) / (2 * a)
        t2 = (-b - math.sqrt(discriminant)) / (2 * a)

        for t in [t1, t2]:
            if 0 <= t <= 1:
                x = x0 + t * dx
                y = y0 + t * dy
                intersections.append((x, y))

    return intersections


def process_shape(input_file, output_file, radius_step=1.0):
    try:
        # 读取原始坐标
        points = read_coordinates(input_file)
        closed_shape = points + [points[0]]  # 闭合图形

        # 计算所有边的半径范围
        min_radius = min(math.sqrt(x ** 2 + y ** 2) for x, y in points)
        max_radius = max(math.sqrt(x ** 2 + y ** 2) for x, y in points)

        # 生成测试半径（从最小半径-步长到最大半径+步长）
        radii = [r for r in
                 frange(min_radius - 2 * radius_step,
                        max_radius + 2 * radius_step,
                        radius_step)]

        # 查找所有交点
        results = []
        for radius in radii:
            intersections = []
            # 检查每条边
            for i in range(len(closed_shape) - 1):
                start = closed_shape[i]
                end = closed_shape[i + 1]
                pts = find_circle_intersections(start, end, radius)
                intersections.extend(pts)

            # 去重并转换为极坐标
            unique_pts = list(set(intersections))
            polar_pts = []
            for x, y in unique_pts:
                r, theta = cartesian_to_polar(x, y)
                polar_pts.append({
                    'radius': radius,
                    'x': x,
                    'y': y,
                    'polar_r': r,
                    'polar_theta': theta
                })
            # 按距离原点距离排序
            polar_pts.sort(key=lambda pt: pt['polar_r'])
            results.extend(polar_pts)

        # 保存结果到CSV
        with open(output_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=['radius', 'x', 'y', 'polar_r', 'polar_theta'])
            writer.writeheader()
            writer.writerows(results)

        # 绘制预览图
        plt.figure(figsize=(10, 8))

        # 绘制原始图形
        x_coords, y_coords = zip(*closed_shape)
        plt.plot(x_coords, y_coords, 'b-', lw=2, label='原始图形')

        # 绘制交点
        if results:
            x_pts = [row['x'] for row in results]
            y_pts = [row['y'] for row in results]
            plt.scatter(x_pts, y_pts, c='r', s=50, label='交点')

        # 绘制圆
        for radius in sorted(set(row['radius'] for row in results)):
            circle = plt.Circle((0, 0), radius, color='g', fill=False,
                                linestyle='--', alpha=0.3)
            plt.gca().add_patch(circle)

        plt.title("图形与圆的交点分析")
        plt.xlabel("X轴")
        plt.ylabel("Y轴")
        plt.axis('equal')
        plt.grid(True)
        plt.legend()
        plt.savefig('intersection_preview.png')
        plt.close()

        print(f"处理完成！结果已保存至 {output_file}")
        print(f"预览图已保存至 intersection_preview.png")

    except Exception as e:
        print(f"处理错误: {str(e)}")


def frange(start, stop, step):
    """生成浮点数范围"""
    while start < stop:
        yield start
        start += step


# 使用示例
if __name__ == "__main__":
    process_shape(
        input_file="transformedresult,csv",
        output_file="circle_intersections.csv",
        radius_step=0.5  # 半径检测步长（单位：坐标单位）
    )