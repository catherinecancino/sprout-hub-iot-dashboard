@echo off
title Sprout Hub System Starter

echo [1/3] Starting Django Backend...
start "Django Backend" cmd /k "call venv\Scripts\activate && python manage.py runserver"

echo [2/3] Starting React Frontend...
start "React Frontend" cmd /k "cd frontend && npm run dev"

echo Waiting for backend to become available...
:wait_loop
timeout /t 2 /nobreak > nul

:: Ping the API endpoint to see if Django is awake yet
curl -s http://127.0.0.1:8000/api/v1/knowledge-library/ > nul
if errorlevel 1 (
    echo [ ] Backend is still booting up... retrying...
    goto wait_loop
)

echo [3/3] Backend is ONLINE! Opening the dashboard...
start http://localhost:5173

timeout /t 3
exit