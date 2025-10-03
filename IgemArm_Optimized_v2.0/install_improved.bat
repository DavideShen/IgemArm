@echo off
echo ========================================
echo 智能机械臂伤口治疗系统 v2.0 安装程序
echo ========================================
echo.

echo 正在检查Python环境...
python --version >nul 2>&1
if errorlevel 1 (
    echo 错误: 未找到Python环境
    echo 请先安装Python 3.8或更高版本
    pause
    exit /b 1
)

echo Python环境检查通过
echo.

echo 正在安装依赖包...
pip install -r requirements.txt
if errorlevel 1 (
    echo 错误: 依赖包安装失败
    pause
    exit /b 1
)

echo 依赖包安装完成
echo.

echo 正在创建必要目录...
if not exist "logs" mkdir logs
if not exist "data" mkdir data
if not exist "captured_photos" mkdir captured_photos
if not exist "config" mkdir config

echo 目录创建完成
echo.

echo 正在初始化配置...
python -c "from config import config_manager; config_manager.save_config(); print('配置初始化完成')"
if errorlevel 1 (
    echo 警告: 配置初始化失败，将使用默认配置
)

echo.
echo ========================================
echo 安装完成！
echo ========================================
echo.
echo 使用方法:
echo   运行GUI模式: python main_improved.py --mode gui
echo   运行CLI模式: python main_improved.py --mode cli
echo   运行测试模式: python main_improved.py --mode test
echo.
echo 或者直接运行: run_improved.bat
echo.
pause
