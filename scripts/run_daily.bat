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

REM Ma tra ve: 0 = binh thuong | 1 = pipeline loi | 2 = vi pham nguong chat luong
set FAILED=0

echo [%date% %time%] Bat dau crawl CareerLink
python run_pipeline.py --sources careerlink
if errorlevel 2 (
    echo [CANH BAO] CareerLink vi pham nguong chat luong - kiem tra tab "Suc khoe pipeline"
    set FAILED=1
) else if errorlevel 1 (
    echo [LOI] CareerLink that bai
    set FAILED=1
)

echo [%date% %time%] Bat dau crawl ITviec
python run_pipeline.py --sources itviec --max-pages 15 --no-detail
if errorlevel 2 (
    echo [CANH BAO] ITviec vi pham nguong chat luong - kiem tra tab "Suc khoe pipeline"
    set FAILED=1
) else if errorlevel 1 (
    echo [LOI] ITviec that bai
    set FAILED=1
)

echo [%date% %time%] Xuat ban chup du lieu
python scripts\export_snapshot.py

echo [%date% %time%] Xong.
REM Tra ma loi ra ngoai de Task Scheduler ghi nhan dung trang thai lan chay
endlocal & exit /b %FAILED%
