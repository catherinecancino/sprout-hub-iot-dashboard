:: 1. Activate venv, and start Python
start cmd /k "call venv\Scripts\activate && python manage.py runserver"

:: 2. Navigate to frontend and start React
start cmd /k "cd frontend && npm run dev"

:: 3. Initiate server
echo Waiting for system startup...
timeout /t 5 /nobreak > nul

:: 4. Automatic open browser
start http://localhost:5173