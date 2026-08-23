# CanSat Ground Station Prototype

Hi I'm Kisa! This is my groundstation prototype.

## What my prototype includes

A Flask backend that serves flight telemetry as JSON, a summary panel of flight highlights, and
six interactive, zoom-synced charts covering acceleration, gyroscope, pressure/altitude, power,
and GPS — plus a test suite covering the backend logic.

## How to run the program

You'll need **Python** version 3.9+ installed

### Get the code from GitHub

1. Go to this project's page on GitHub.
2. Click the green **Code** button, then pick
    **Download ZIP**   Once it downloads, right click
     the ZIP file and choose **Extract All** or just double-click it to unzip it
    



### Work the code

1. **Open the project in VS Code.** Open VS Code, go to **File → Open Folder...**, and select
   the project folder you just downloaded.
2. **Open a terminal inside VS Code.** Once the folder's open, go to **Terminal → New Terminal**
  
3. **Create and activate a virtual environment:**
   Copy/paste in terminal:

   python -m venv venv
   venv\Scripts\activate
   
   
   
4. **Install the dependencies:**
   
   pip install -r requirements.txt
   
5. **Start the server:**
   
   python telemetryapp.py
   
   Wait for a line like Running on http://127.0.0.1:5000.
6. **Open the dashboard** — go to [http://localhost:5000](http://localhost:5000) in your browser.
7. **When you're done**, go back to the terminal and press `Ctrl+C` to stop the server.




### Running the tests

There's a separate file, `test_telemetryapp.py`, full of small checks that verify the backend
math and logic actually work correctly (things like "does the acceleration magnitude formula
give the right number" or "does the API return an error if the CSV is missing"). "Running" the
tests just means telling Python to go through that file and actually execute each of those checks
one by one, instead of just having them sit there unused.

STEPS: go back to the same terminal you used to start the server then type:

pytest


- Pytest will find every check in `test_telemetryapp.py`, run each one, and print a
`.` for every check that passed (or an `F` for one that failed). At the end you'll get a one-line
summary like `14 passed in 0.6s`. that means all 14 checks ran and every single one confirmed the
code is behaving the way it's supposed to.

## How the project is put together

```
groundstation/
├── telemetryapp.py       Flask app — reads the CSV and computes the derived columns
├── requirements.txt      The packages you need installed to run this
├── README.md             This file
├── telemetry.csv         Sample flight data
├── test_telemetryapp.py  Pytest checks for the backend
├── templates/
│   └── index.html        The one page the app serves
└── static/
    ├── css/
    │   └── style.css     All the page styling
    └── js/
        └── app.js        Frontend logic — fetches the data and builds the graphs
```



## Design decisions & assumptions

- **This groundstation is for a finished flight, not a live one.** Every time the page loads, it
  reads the whole CSV file from the start — it doesn't watch for new rows being added.

- **A GPS reading of exactly (0, 0) means "no signal."** The app treats that as missing data
  instead of a real location, since no real flight is actually going to land on that exact spot.
  This is why you might sometimes see a gap in the GPS chart.

- **Liftoff is just a guess based on acceleration.** The app looks for the first moment
  acceleration passes 20 m/s² (about 2 times gravity) and calls that liftoff.

- **Altitude is shown two different ways.** One line is the GPS altitude reading. The other
  is an estimate calculated from air pressure. Showing both lets you compare them and spot any
  sources of error.

- **Gyro magnitude is calculated but not graphed.** It still shows up in the Max Angular Velocity
  stat card, but unlike acceleration magnitude, it doesn't trigger any flight event, so plotting
  it as a fourth line on the Gyroscope chart was just clutter.

- **Every chart's x-axis stays in sync.** Zoom or pan on one chart and every other chart jumps to
  that same time window, so you're always comparing the same slice of the flight across all the
  sensors.

- **Missing or broken readings show up as blank, not zero.** If a value is missing or isn't a
  real number, the app leaves it blank instead of guessing or dropping it.

- **One flight, one CSV file.** There's no flight picker or database — it always reads whatever's
  sitting in `telemetry.csv`.


