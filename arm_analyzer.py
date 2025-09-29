import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
import seaborn as sns
from datetime import datetime

class ArmMotionAnalyzer:
    def __init__(self, data_file):
        """初始化分析器"""
        self.data = pd.read_csv(data_file)
        self.data['timestamp'] = pd.to_datetime(self.data['timestamp'])
        
    def calculate_precision_metrics(self, target_x=None, target_y=None, target_z=None):
        """计算精度指标"""
        metrics = {}
        
        if target_x is not None:
            x_error = self.data['x'] - target_x
            metrics['x_rmse'] = np.sqrt(np.mean(x_error**2))
            metrics['x_std'] = np.std(x_error)
            metrics['x_max_error'] = np.max(np.abs(x_error))
            
        if target_y is not None:
            y_error = self.data['y'] - target_y
            metrics['y_rmse'] = np.sqrt(np.mean(y_error**2))
            metrics['y_std'] = np.std(y_error)
            metrics['y_max_error'] = np.max(np.abs(y_error))
            
        if target_z is not None:
            z_error = self.data['z'] - target_z
            metrics['z_rmse'] = np.sqrt(np.mean(z_error**2))
            metrics['z_std'] = np.std(z_error)
            metrics['z_max_error'] = np.max(np.abs(z_error))
            
        return metrics
    
    def analyze_vibration(self):
        """分析抖动情况"""
        vibration_metrics = {}
        
        for axis in ['x', 'y', 'z']:
            # 计算速度（位置的一阶导数）
            velocity = np.diff(self.data[axis])
            # 计算加速度（速度的一阶导数）
            acceleration = np.diff(velocity)
            
            vibration_metrics[f'{axis}_velocity_std'] = np.std(velocity)
            vibration_metrics[f'{axis}_acceleration_std'] = np.std(acceleration)
            vibration_metrics[f'{axis}_position_std'] = np.std(self.data[axis])
            
        return vibration_metrics
    
    def plot_motion_analysis(self, save_path=None):
        """绘制运动分析图表"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        
        # 位置时间序列
        axes[0, 0].plot(self.data['timestamp'], self.data['x'], label='X', alpha=0.7)
        axes[0, 0].plot(self.data['timestamp'], self.data['y'], label='Y', alpha=0.7)
        axes[0, 0].plot(self.data['timestamp'], self.data['z'], label='Z', alpha=0.7)
        axes[0, 0].set_title('位置时间序列')
        axes[0, 0].set_ylabel('位置 (mm)')
        axes[0, 0].legend()
        axes[0, 0].grid(True)
        
        # 位置分布直方图
        axes[0, 1].hist(self.data['x'], alpha=0.5, label='X', bins=30)
        axes[0, 1].hist(self.data['y'], alpha=0.5, label='Y', bins=30)
        axes[0, 1].hist(self.data['z'], alpha=0.5, label='Z', bins=30)
        axes[0, 1].set_title('位置分布')
        axes[0, 1].set_xlabel('位置 (mm)')
        axes[0, 1].set_ylabel('频次')
        axes[0, 1].legend()
        
        # 3D轨迹图
        ax_3d = fig.add_subplot(2, 2, 3, projection='3d')
        ax_3d.plot(self.data['x'], self.data['y'], self.data['z'], alpha=0.6)
        ax_3d.set_xlabel('X (mm)')
        ax_3d.set_ylabel('Y (mm)')
        ax_3d.set_zlabel('Z (mm)')
        ax_3d.set_title('3D轨迹')
        
        # 抖动分析
        for i, axis in enumerate(['x', 'y', 'z']):
            velocity = np.diff(self.data[axis])
            axes[1, 1].plot(velocity, label=f'{axis.upper()} 速度', alpha=0.7)
        axes[1, 1].set_title('速度变化（抖动指标）')
        axes[1, 1].set_xlabel('时间步')
        axes[1, 1].set_ylabel('速度 (mm/step)')
        axes[1, 1].legend()
        axes[1, 1].grid(True)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.show()
    
    def generate_report(self, target_position=None):
        """生成分析报告"""
        report = {
            'analysis_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'data_points': len(self.data),
            'duration_seconds': (self.data['timestamp'].iloc[-1] - self.data['timestamp'].iloc[0]).total_seconds()
        }
        
        # 基本统计
        for axis in ['x', 'y', 'z']:
            report[f'{axis}_mean'] = self.data[axis].mean()
            report[f'{axis}_std'] = self.data[axis].std()
            report[f'{axis}_range'] = self.data[axis].max() - self.data[axis].min()
        
        # 精度分析
        if target_position:
            precision_metrics = self.calculate_precision_metrics(*target_position)
            report.update(precision_metrics)
        
        # 抖动分析
        vibration_metrics = self.analyze_vibration()
        report.update(vibration_metrics)
        
        return report
    
    def save_report(self, report, filename=None):
        """保存报告到文件"""
        if not filename:
            filename = f"arm_analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("机械臂运动精度分析报告\n")
            f.write("=" * 50 + "\n\n")
            
            for key, value in report.items():
                if isinstance(value, float):
                    f.write(f"{key}: {value:.4f}\n")
                else:
                    f.write(f"{key}: {value}\n")
        
        print(f"分析报告已保存到: {filename}")

# 使用示例
if __name__ == "__main__":
    # 分析数据文件
    analyzer = ArmMotionAnalyzer("arm_position_data_20250101_120000.csv")
    
    # 生成报告（假设目标位置是 175, 0, 75）
    report = analyzer.generate_report(target_position=(175, 0, 75))
    
    # 保存报告
    analyzer.save_report(report)
    
    # 绘制分析图表
    analyzer.plot_motion_analysis("motion_analysis.png")