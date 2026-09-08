@echo off
REM ============================================================
REM  Chay pipeline hang ngay (dung voi Windows Task Scheduler).
REM  - Crawl ca hai nguon
REM  - Xuat lai ban chup cho dashboard cong khai
REM  Log da duoc pipeline ghi san vao thu muc logs\
REM ============================================================
setlocal

REM %~dp0 = thu muc chua file .bat nay -> lui mot cap ra goc project.
REM Phai lam vay vi Task Scheduler chay script tu mot thu muc khac han.
cd /d "%~dp0.."

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
) else (
    echo [canh bao] Khong tim thay .venv - dung Python he thong.
)

echo [%date% %time%] Bat dau crawl CareerLink
python run_pipeline.py --sources careerlink
if errorlevel 1 echo [loi] CareerLink that bai

echo [%date% %time%] Bat dau crawl ITviec
python run_pipeline.py --sources itviec --max-pages 15 --no-detail
if errorlevel 1 echo [loi] ITviec that bai

echo [%date% %time%] Xuat ban chup du lieu
python scripts\export_snapshot.py

echo [%date% %time%] Xong.
endlocal
