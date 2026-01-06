# Element-Tester
This will be a program for the Frymaster Element Tester to test the high potential and resistance.

## If you are trying to rebuild a new executable file (.exe file) after changing something use this process
- Step 1: Open command prompt or powershell
- Step 2: Run this command --> cd "C:\Files\element tester\Element_Tester\src\element_tester\system\core"
- Step 3: Activate the virtual environment with these commands in that order and you should see a (.venv) appear in front of the location you cd into -->
  - SetExecutionPolicy -Scope Process -ExecutionPolicy Bypass
  - & "C:\Files\element tester\Element_Tester\.venv\Scripts\Activate.ps1"
- Step 4: Run this command --> python build_application.py
  - This should build and overrite the previous version of the application


  
