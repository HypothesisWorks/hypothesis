:: To build extensions for 64 bit Python 3, we need to configure environment
:: variables to use the MSVC 2010 C++ compilers from GRMSDKX_EN_DVD.iso of:
:: MS Windows SDK for Windows 7 and .NET Framework 4 (SDK v7.1)
::
:: 32 bit builds do not require specific environment configurations.
::
:: Note: this script needs to be run with the /E:ON and /V:ON flags for the
:: cmd interpreter, at least for (SDK v7.0)
::
:: More details at:
:: https://github.com/cython/cython/wiki/64BitCythonExtensionsOnWindows
:: https://stackoverflow.com/a/13751649/163740
::
:: Author: Olivier Grisel
:: License: CC0 1.0 Universal: https://creativecommons.org/publicdomain/zero/1.0/
@ECHO OFF

SET COMMAND_TO_RUN=%*
SET WIN_SDK_ROOT=C:\Program Files\Microsoft SDKs\Windows

IF "%PYTHON_ARCH%"=="64" (
    ECHO Configuring Windows SDK v7.1 for Python 3 on a 64 bit architecture
    SET DISTUTILS_USE_SDK=1
    SET MSSdk=1
    "%WIN_SDK_ROOT%\v7.1\Setup\WindowsSdkVer.exe" -q -version:v7.1
    "%WIN_SDK_ROOT%\v7.1\Bin\SetEnv.cmd" /x64 /release
    ECHO Executing: %COMMAND_TO_RUN%
    call %COMMAND_TO_RUN% || EXIT 1
) ELSE (
    ECHO Using default MSVC build environment for 32 bit architecture
    ECHO Executing: %COMMAND_TO_RUN%
    call %COMMAND_TO_RUN% || EXIT 1
)
