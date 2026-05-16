@echo off
chcp 65001 >nul
cd /d "%~dp0"
cls
echo ==================================================
echo      DELIVROUTE - KHOI DONG HE THONG TOI UU
echo ==================================================
echo.
echo  Dang khoi dong giao dien Web Demo giong delivery_optimizer_demo.html...
echo  Vui long doi trong giay lat...
echo.
python delivery_optimizer/gui.py
if %errorlevel% neq 0 (
    echo.
    echo [LOI] Khong the khoi chay ung dung. 
    echo Vui long kiem tra lai moi truong Python va cac thu vien.
    pause
)
exit
