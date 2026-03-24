@echo off
echo =======================================================
echo   AutoBIMNote - Local Area Network (LAN) Server Start
echo =======================================================
echo.
echo 🌐 내부망 접속 주소: http://192.168.0.60:8000
echo 💡 팀원들에게 위 주소를 공유하세요!
echo.
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
