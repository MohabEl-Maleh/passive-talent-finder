@echo off
echo ============================================================
echo   Train AI Model on Kaggle Resume Dataset
echo ============================================================
echo.
echo Please drag and drop your Resume.csv file into this window,
echo then press Enter. (Or type the full path manually)
echo.
echo Example: C:\Users\YourName\Downloads\resume-dataset\Resume.csv
echo.
set /p CSV_PATH="Path to Resume.csv: "

if not exist "%CSV_PATH%" (
    echo ERROR: File not found at %CSV_PATH%
    echo Make sure you downloaded and extracted the Kaggle dataset.
    pause
    exit /b 1
)

echo.
echo Training model on: %CSV_PATH%
echo This will take 1-2 minutes...
echo.

cd backend
call venv\Scripts\activate
set PYTHONPATH=%CD%
cd ..
python ml/scripts/train_on_kaggle_dataset.py --csv "%CSV_PATH%"

echo.
echo ============================================================
echo   Model trained and saved to backend/models/passivity_model.pkl
echo   You can now use the full AI matching feature.
echo ============================================================
pause
