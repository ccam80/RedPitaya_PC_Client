# Getting started
- starting the server (<https://github.com/ccam80/RedPitaya_Onboard>)
- change IP address inside socket_process.py
- run main.py
- if spyder is used, it can be good to switch the graphics backend:
  - tools --> preferences --> IPython console --> Graphics --> Backend --> switch to Qt5

# Structure
File               | Classes                  | Used for
------------------ | ------------------------ | --------
Main.py            | Window                   | build the connection between UI and all other processes
socket_process.py  | StreamToLogger           | generate log file
&nbsp;             | dataThread               | background thread for server communication
float_converter.py | NumpyFloatToFixConverter | converts Numpy arrays of floats to fixed point arrays
Canvas.py          | MyFigureCanvas           | can be used to create a matplotlib canvas inside the UI
UI.py              | Ui_MainWindow            | autogenerated UI layout see UI_Designer.md
&nbsp;             | retranslateUi            | autogenerated UI text translation see UI_Designer.md
