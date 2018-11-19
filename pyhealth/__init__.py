"""
Python interface for pulling and pushing your health data
=========================================================

pyhealth is a python module for collecting and analyzing
your health, activity tracking, sport data. The intent is
to be able to set up your scripts to collect your data
from SleepAsAndroid, Garmin, Suunto, Google Health, Fitbit,
etc. I would also like to eventually set it up to push to
those same services. This would be similar to the Tapirik
service, but will pull and push activity data if available
(steps, resting heart rate, sleep data, etc). This is very
much a work in progress that I am playing around to teach
myself how to connect to these different services.
"""
__version__ = '0.1dev'

from .gui_interfaces import get_login_credentials
from .Garmin import *
from .SleepAsAndroid import *
