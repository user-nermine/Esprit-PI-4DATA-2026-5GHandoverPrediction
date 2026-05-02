@echo off
echo === CD Pipeline - DoNext Backend ===

:: Get current git commit hash
for /f %%i in ('git rev-parse --short HEAD') do set VERSION=%%i
echo Version: %VERSION%

:: Build image
echo Building Docker image...
docker build -t adminnermine/donext-backend:%VERSION% .
docker tag adminnermine/donext-backend:%VERSION% adminnermine/donext-backend:latest

:: Push to DockerHub
echo Pushing to DockerHub...
docker push adminnermine/donext-backend:%VERSION%
docker push adminnermine/donext-backend:latest

:: Restart local container
echo Restarting local container...
docker stop donext-backend donext-test 2>nul
docker rm donext-backend donext-test 2>nul
docker run -d --name donext-backend -p 8000:8000 adminnermine/donext-backend:latest

echo.
echo === CD Complete ===
echo Image : adminnermine/donext-backend:%VERSION%
echo API   : http://localhost:8000/docs
echo MLflow: http://localhost:5000
echo Airflow: http://localhost:8082


