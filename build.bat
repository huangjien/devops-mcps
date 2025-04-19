@echo off
REM Extract version from pyproject.toml
for /f "tokens=2 delims==" %%i in ('findstr "version =" pyproject.toml') do (
    set VERSION=%%i
)
set VERSION=%VERSION:"=%

REM Build Docker image with version and latest tags
docker build -t huangjien/devops-mcps:%VERSION% -t huangjien/devops-mcps:latest .

echo Successfully built huangjien/devops-mcps:%VERSION% and huangjien/devops-mcps:latest