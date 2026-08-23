# CanSat Ground Station Prototype

Hi I'm Kisa! This is my groundstation prototype.

## What my prototype includes

A Flask backend that serves flight telemetry as JSON, a summary panel of flight highlights,
six charts covering acceleration, gyroscope, pressure/altitude, power,
and GPS, and a test suite covering the backend logic.

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
   
   Wait for a line like Running on http://127.0.0.1:5000 and click follow link

7. **When you're done** - go back to the terminal and press `Ctrl+C` to stop the server.




### Running the tests


STEPS: go back to the same terminal you used to start the server then type:

pytest


- Pytest will run each test and print a
`.` for every check that passed or an `F` for one that failed.

## How the project is put together

├── telemetryapp.py        reads the CSV and computes the derived columns
├── requirements.txt      The packages you need installed to run this
├── README.md             This file
├── telemetry.csv         Sample flight data
├── test_telemetryapp.py  Pytest checks for the backend
├── templates/
│   └── index.html        The frontend of the groundstation
└── static/
    ├── css/
    │   └── style.css     The frontend styling
    └── js/
        └── app.js        the frontend logic — fetches the data and builds the graphs
```



## Design decisions & assumptions



 **This groundstation is for a finished flight.** Every time the page loads, it
  reads the whole CSV file from the start. it doesn't watch for new rows being added.

- **A GPS reading of exactly (0, 0) means "no signal."** The app treats that as missing data
  instead of a real location, since no real flight is actually going to land on that exact spot.
  This is why you might sometimes see a gap in the GPS chart.

- **Liftoff is just a guess based on acceleration.** The app looks for the first moment
  acceleration passes 20 m/s² (about 2x gravity) and calls that liftoff.

- **Altitude is shown two different ways.** One line is the GPS altitude reading and the other one
  is an estimate calculated from air pressure. 

- **Gyro magnitude is calculated but not graphed.** It still shows up in the Max Angular Velocity
  stat card, but unlike acceleration magnitude, it doesn't trigger any flight event, so I didn't plot it.

- **Every chart's x-axis stays in sync.** Zoom or pan on one chart and every other chart jumps to
  that same time window, so you're always comparing the same slice of the flight across all the
  sensors.


- **One flight, one CSV file.** There's no flight picker or database. it always reads whatever's
  sitting in `telemetry.csv`.





