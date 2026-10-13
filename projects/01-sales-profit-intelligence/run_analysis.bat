
@echo off
cd /d "%~dp0"
if not exist "reports" mkdir "reports"

python -m jupyter nbconvert --to notebook --execute "notebooks\sales_profit_analysis.ipynb" --output "sales_profit_analysis_executed.ipynb" --output-dir "%~dp0reports"

if errorlevel 1 (
    echo ERROR: Analysis failed.
    pause
    exit /b 1
)

echo SUCCESS: Analysis completed.
pause
