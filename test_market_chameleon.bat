@echo off
echo.
echo =====================================
echo  MARKET CHAMELEON INTEGRATION TEST
echo =====================================
echo.

cd /d "D:\XAVIER\DEV\Python Projects\squeeze-finder"

echo Launching Market Chameleon test...
python test_market_chameleon_integration.py

echo.
echo Test complete! Check the output above for results.
echo.
pause