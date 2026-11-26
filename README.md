# Soccer Analytics Platform

## Run locally on Windows (free)

1. [Download the project ZIP](https://github.com/Micaiahg888/soccer-analytics/archive/refs/heads/main.zip) and use **Extract All** in File Explorer.
2. Open the extracted `soccer-analytics-main` folder that contains `app.py`. Click the File Explorer address bar, type `powershell`, and press **Enter**.
3. With Python installed, run these commands one at a time:

   ```powershell
   py -m venv venv
   .\venv\Scripts\python.exe -m pip install Flask==3.1.3
   .\venv\Scripts\python.exe -m flask --app app run
   ```

4. When PowerShell shows **Running on http://127.0.0.1:5000**, open the [Soccer Analytics dashboard](http://127.0.0.1:5000/) in your browser. Leave PowerShell open while you use the app.

The first run creates an empty SQLite database. Use **Add Team** to get started. For later sessions, run just the last PowerShell command from this same folder.
