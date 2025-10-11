@echo off
echo ========================================
echo 智能机械臂伤口治疗系统 v2.0
echo ========================================
echo.

echo 选择运行模式:
echo 1. GUI模式 (图形界面)
echo 2. CLI模式 (命令行)
echo 3. 测试模式
echo 4. 退出
echo.

set /p choice="请选择 (1-4): "

if "%choice%"=="1" (
    echo 启动GUI模式...
    python main_improved.py --mode gui
) else if "%choice%"=="2" (
    echo 启动CLI模式...
    python main_improved.py --mode cli
) else if "%choice%"=="3" (
    echo 启动测试模式...
    python main_improved.py --mode test
) else if "%choice%"=="4" (
    echo 退出程序
    exit /b 0
) else (
    echo 无效选择，启动默认GUI模式...
    python main_improved.py --mode gui
)

echo.
echo 程序已结束
pause








