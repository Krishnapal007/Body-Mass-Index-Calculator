# BMI Health Tracker – Advanced Edition

A desktop dashboard for calculating, saving and analysing BMI for multiple users.
Built for the **Oasis Infobyte Python Programming Internship** (Advanced level).

> **Disclaimer:** BMI is a screening tool and not a medical diagnosis. Consult a qualified healthcare professional for medical advice.

## Features

- Sidebar dashboard: Dashboard, BMI Calculator, BMI History, BMI Analytics, User Management
- BMI = weight / (height ** 2), shown to 2 decimal places
- Colour-coded categories: Underweight (blue), Normal (green), Overweight (orange), Obese (red)
- Multi-user records stored in SQLite (`bmi_tracker.db`), persistent between runs
- Search by username, filter by category, refresh, total records counter
- Edit and delete records (multi-select delete), delete a whole user
- Matplotlib BMI trend graphs (date vs BMI) per user or all users, with legend; save as PNG/PDF/SVG
- Export history to CSV
- Input validation: empty, letters, negative, zero height, unrealistic values, cm entered as metres
- Error handling for SQLite connection, read/write, CSV export and graph generation

## Technology Stack

Python 3, Tkinter, SQLite3, Matplotlib, CSV, Datetime

## Project Structure

```
bmi_calculator/
├── main.py                 # Tkinter GUI (dashboard and pages)
├── database.py             # SQLite CRUD, search, summaries, CSV export
├── bmi_calculator.py       # BMI formula, categories, validation
├── visualization.py        # Matplotlib charts
├── test_bmi_tracker.py     # Automated tests
├── requirements.txt
├── README.md
├── bmi_tracker.db          # Created automatically on first run
└── screenshots/
```

## Installation (Windows 10 / 11)

1. **Install Python 3.10+** from https://www.python.org/downloads/ . On the first installer screen tick **"Add python.exe to PATH"**. Keep **"tcl/tk and IDLE"** ticked (it provides Tkinter).
2. Check it: open Command Prompt and run `python --version`.
3. **Install VS Code** from https://code.visualstudio.com/ , then install the **Python** extension (Microsoft).
4. Open the `bmi_calculator` folder in VS Code (File > Open Folder).
5. Open a terminal in VS Code (Ctrl + `) and create a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate
   ```
   If PowerShell blocks activation, run once: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`
6. Install libraries:
   ```
   pip install -r requirements.txt
   ```
7. In VS Code press Ctrl+Shift+P, choose **Python: Select Interpreter**, and pick the `venv` one.

## Run

```
python main.py
```

## Using the app

1. **BMI Calculator**: enter username, weight (kg) and height (m), press **Calculate BMI**. The result is saved automatically. *Clear* empties weight and height; *Reset* empties everything.
2. **BMI History**: search, filter, edit, delete, refresh, export CSV.
3. **BMI Analytics**: choose a user (or All Users) to see the trend graph; save it as an image.
4. **User Management**: see every user, open their history or graph, or delete a user.

## Testing

```
python -m unittest -v
```

Automated tests cover BMI accuracy, category boundaries, invalid input, multiple users, persistence, deletion, CSV export and chart creation (12 tests, all passing). Uses a temporary database.

Manual checklist: calculate for 2+ users, close and reopen the app (data remains), delete a record, export CSV and open it in Excel, view each user's graph, try bad input (empty, `abc`, `-5`, height `0`).

## Troubleshooting

| Problem | Fix |
|---|---|
| `'python' is not recognized` | Reinstall Python with "Add to PATH" ticked, or use `py` instead of `python` |
| `No module named 'tkinter'` | Re-run the Python installer > Modify > tick "tcl/tk and IDLE" |
| `No module named 'matplotlib'` | Activate the venv, then `pip install -r requirements.txt` |
| Activation script blocked | `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` |
| CSV export fails | Close the file in Excel, choose a folder you can write to |
| "database is locked" | Close other copies of the app |
| Start fresh | Close the app and delete `bmi_tracker.db` |

## GitHub setup

```
git init
git add .
git commit -m "BMI Health Tracker - Advanced Edition"
git branch -M main
git remote add origin https://github.com/<your-username>/bmi-health-tracker.git
git push -u origin main
```

Create the empty repository on github.com first. Consider adding `venv/` and `__pycache__/` to a `.gitignore`.

## Screenshots

Add your screenshots to the `screenshots/` folder and link them here:

```
![Dashboard](screenshots/dashboard.png)
![Calculator](screenshots/calculator.png)
![History](screenshots/history.png)
![Analytics](screenshots/analytics.png)
![Users](screenshots/users.png)
```

## Internship Submission Checklist

- [ ] App runs with `python main.py` on a clean virtual environment
- [ ] `python -m unittest -v` passes
- [ ] 5 screenshots added to `screenshots/` and linked above
- [ ] Repository is public on GitHub with a clear README
- [ ] Short demo video or screenshots ready (optional)
- [ ] Repository link submitted via the Oasis Infobyte form
- [ ] Project posted on LinkedIn tagging Oasis Infobyte (if required by your offer letter)

## License

For educational use as part of the Oasis Infobyte internship.
