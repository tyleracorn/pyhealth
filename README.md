# pyhealth
This is a python package for parsing and viewing health/wellness/fitness data from different sources.

---
## Current data sources
* sleep_as_Android backup excel file (re-saved as a csv)
    * Currently you can parse the backup file that sleep as android saves to cloud for you. Right now there are a couple of steps you need to do for each record, which I show in the example jupyter notebook. This allows you to plot individual sleep records... or (what is more interesting to me) calculate and plot your resting heart rate. Right now I am looking at both the minimum heart rate and the 5th percentile heart rate value for each sleep record. The 5th percentile is less noisy then the minimum value so I'm leaning towards that.

Example sleep record plot
![sleep record image](/examples/example_sleep_record.png?raw=true "Example Sleep Record")

Example resting heart rate plot
![sleep record image](/examples/example_resting_heartrate.png?raw=true "Example Resting Heart Rates")

---
### Planned sources
* parse and view .gpx, .tix, and .fit data, some sample data is included (downloaded from the garmin website) for development and example purposes. The viewing the data will incorporate either openMaps or google maps
* access to google fit date. 
    * will likely start by parsing already downloaded google fit archive. Hopefully can move towards directly accessing google fit
    * access to events by specific labels i.e. (running, biking, etc)
    * access to weight data

---
## Installation
Currently there is not setup.py file. I don't have it developed far enough to warrent an installation since it is currently just a collection of functions. Once I figure out a class structure then I'll start working on the installation files.

