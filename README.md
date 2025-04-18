# Google Drive Integration

## Setup
- Since OAuth require authorized testers, please send me an email with a list of gmail ids that you would like to test app with.
- I wil add them to the list of authorized testers.
- The app requires 'credentials.json' and '.env' files to run. I shall provide those in the email as well. They need to be put in the root directory.
- The app uses Python and Flask. Python version 3.12.5 and Flask versionn 3.1.0
- To install requirements: `pip install -r requirements.txt` in the root directory and then `playwright install` to install browser plugins for testing.
- To run the app: `python strac_app.py` in the root directory
- The app runs on `http://localhost:5000/` by default. Navigate to the url to open the app.
- To run tests: `pytest -v` in the root directory.
