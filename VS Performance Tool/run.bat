@echo off
rem
rem setup vs profile environment
rem 
rem -P for run py
rem 
rem

if "%SomeNeedENV%" == '' goto BadEnv
if "%1" == "" echo Need output path & goto End

set PCFS=%1\PCFs
set OUTPUTS=%1\Outputs
set RUN=%1\Run

if not exist "%PCFS%" mkdir %PCFS%
if not exist "%OUTPUTS%" mkdir %OUTPUTS%

if "%2" == "-p" goto PyEnv

rem remove all outputs except ProfData.xml
rem ProfData.xml is performance data file, it stores each time the performace tool run
rem so we can check the performance is better or worse each time
rem this file is created by perf.py next
attrib +r +h %OUTPUTS%\PerfData.xml	
del /F /Q %OUTPUTS% > NUL
attrib -r -h %OUTPUTS%\PerfData.xml

rem check XXX exists or not
set PERFEXE=
if exist "%bin%\XXX.exe" set PERFEXE=%bin%\XXX.exe

if "%PERFEXE%" == "" goto BadEnv

rem
rem begin performance
rem
rem VSPerfCLREnv /sampleon

:RunXXX
echo .........................................
echo .... generating performance profile .....
echo .........................................

set STARTTIME=%time%
VsPerfCmd /start:sample /output:"%OUTPUTS%\perf.vsp" /launch:"%PERFEXE%" /args:"/perf %PCFS%"
VsPerfCmd /shutdown
set ENDTIME=%time%

:Report
echo ....................
echo .... reporting .....
echo ....................

if not exist "%OUTPUTS%\perf.vsp" goto End
VsPerfReport /summary:function /output:"%OUTPUTS%" /justmycode "%OUTPUTS%\perf.vsp"

move /Y "%PCFS%\*.csv" "%OUTPUTS%\"
move /Y "%PCFS%\*.dwg" "%OUTPUTS%\"

:PyEnv
rem this is only for me
if ("%PIPING_3RDPARTY_PYTHON%") == ("") goto MyOwnPyEnv
set PYTHONPATH=%PYTHON_PATH%
set PYTHONNET_EXE=%PYTHON_PATH%\pythonnet.exe
goto RunPy

:MyOwnPyEnv
set PYTHONPATH=%PYTHON_PATH_MIME%
set PYTHONNET_EXE=%PYTHON_PATH_MINE%\python.exe

:RunPy
if "%STARTTIME%" == "" goto End
if "%ENDTIME%" == "" goto End
"%PYTHONNET_EXE%" "%RUN%\perf.py" --csvpath="%OUTPUTS%" --starttime="%STARTTIME%" --endtime="%ENDTIME%"
goto End

:BadEnv
echo please setup environment first

:End
rem VSPerfCLREnv /off
set PCFS=
set OUTPUTS=
set PERFEXE=
