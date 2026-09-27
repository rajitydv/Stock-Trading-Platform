@echo off
title Quantum Trade - Stock Trading Platform
echo ======================================================================
echo           QUANTUM TRADE - STOCK TRADING PLATFORM & SIMULATOR
echo ======================================================================
echo.
echo Select an option to launch:
echo   [1] Launch Modern Web Trading Dashboard (Recommended)
echo   [2] Launch Interactive Terminal Console (CLI)
echo   [3] Run Unit and Integration Test Suite
echo   [4] Exit
echo.
set /p choice="Enter choice (1-4): "

if "%choice%"=="1" (
    echo Starting Web Server on http://127.0.0.1:5000...
    python main.py
) else if "%choice%"=="2" (
    echo Launching CLI Interface...
    python main.py --cli
) else if "%choice%"=="3" (
    echo Running Test Suite...
    python main.py --test
    pause
) else (
    echo Exiting.
)
