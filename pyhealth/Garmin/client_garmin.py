#! /usr/bin/env python
"""A Python 3 module for authenticating against and communicating with selected
parts of the Garmin Connect REST API. Based on Python 2 Code from
https://github.com/petergardfjall/garminexport
https://github.com/cpfair/tapiriik/blob/master/tapiriik/services/GarminConnect/garminconnect.py
https://github.com/magsol/garmin
"""
from io import StringIO
from contextlib import contextmanager
# from datetime import datetime
import functools
import re
import sys
import os
import json
import logging
import zipfile
import requests
import dateutil
import warnings
from gui_interfaces import get_login_credentials

LOG = logging.getLogger(__name__)

# reduce logging noise from requests library
logging.getLogger("requests").setLevel(logging.ERROR)


def require_session(client_function):
    """Decorator that is used to make sure the session has been authenticated before
    trying to call the function.
    """
    @functools.wraps(client_function)
    def check_session(*args, **kwargs):
        client_object = args[0]
        if not client_object.session:
            raise Exception("Attempting to use GarminClient without being connected. "
                            "Call self.connect() before first use.")
        return client_function(*args, **kwargs)
    return check_session


class ClientGarmin():
    """A client class used to authenticate with Garmin Connect and
    extract data from the user account.

    Since this class implements the context manager protocol, this object
    can preferably be used together with the with-statement. This will
    automatically take care of logging in to Garmin Connect before any
    further interactions and logging out after the block completes or
    a failure occurs.

    Parameters:
        username (str): username for your Garmin connect account
        password (str): password for your Garmin connect account

    Examples:

    Using a `with` block to grab activity data

    >>> with GarminClient() as client:
    >>>    ids = client.list_activity_ids()
    >>>    for activity_id in ids:
    >>>        gpx = client.get_activity_gpx(activity_id)

    a pop up window will open asking you to enter your loginname, password, and username
    the username can be different from your loginname if you've ever changed your loginname
    (Like I did a number of years ago). If you are unsure, login into garmin connect online
    and go to your wellness daily report url to see if it has a username different from
    your login name.  address should be:
    'https://connect.garmin.com/modern/proxy/userstats-service/wellness/daily/{username}'

    """
    URL_SSO_LOGIN = "https://sso.garmin.com/sso/login"
    URL_AUTH = "https://connect.garmin.com/modern/auth/hostname"
    URL_LEGACY_SESSION = 'https://connect.garmin.com/legacy/session'
    URL_REDIRECT = "https://connect.garmin.com/modern"
    URL_BASE = "https://connect.garmin.com/modern/proxy/"
    URL_CSS = "https://static.garmincdn.com/com.garmin.connect/ui/css/gauth-custom-v1.2-min.css"
    URL_ACTIVITY = URL_BASE + "activity-service/activity/{activity_id}"
    URL_ACTIVITY_LIST = URL_BASE + "activitylist-service/activities/search/activities"  # requires `start` and `limit`
    URL_ACTIVITY_DETAILS = URL_BASE + "activity-service-1.3/json/activityDetails/{activity_id}"
    URL_ACTIVITY_GPX = URL_BASE + "download-service/export/gpx/activity/{activity_id}"
    URL_ACTIVITY_TCX = URL_BASE + "download-service/export/tcx/activity/{activity_id}"
    URL_ACTIVITY_ORIG = URL_BASE + "download-service/files/activity/{activity_id}"
    URL_WELLNESS = URL_BASE + "userstats-service/wellness/daily/{username}"  # requires `fromDate` and `untilDate`
    URL_DAILYSUMMARY = URL_BASE + "wellness-service/wellness/dailySummaryChart"  # requires `date`
    URL_UPLOAD = URL_BASE + "upload-service/upload/.{flformat}"  # expectes `files`and `headers`
    URL_ACTVITY_PUT = "https://connect.garmin.com/proxy/activity-service/activity/{activity_id}"

    activity_urls = {'summary': URL_ACTIVITY,
                     'details': URL_ACTIVITY_DETAILS,
                     'original_file': URL_ACTIVITY_ORIG,
                     'fit': URL_ACTIVITY_ORIG,
                     'tcx': URL_ACTIVITY_TCX,
                     'gpx': URL_ACTIVITY_GPX}

    def __init__(self):
        """Initialize GarminClient class"""

        self.loginname, self.password, self.username = get_login_credentials(site='GarminConnect',
                                                                             extended_info=True)
        self.session = None
        self.activity_list = None
        self.wellness_summary_from = None
        self.wellness_summary_until = None
        self.wellness_summary = None

    @contextmanager
    def manage_connection(self):
        """Enable GarminClient to be used in a with statement"""

        connection = self.connect()
        try:
            yield connection
        finally:
            self.disconnect()

    def connect(self):
        """
        connect using the requests.Session() authentication
        """

        self.session = requests.Session()
        self._authenticate()

    def disconnect(self):
        """
        disconnect from the session
        """

        if self.session:
            self.session.close()
            self.session = None

    def _authenticate(self):
        """
        try to authenticate the session using session.post()
        if response.status_code does not equal 200 through a
        RuntimeError with the failed claim auth ticket
        """

        LOG.info(f'authentication user: {self.username}')
        data = {'username': self.loginname,
                'password': self.password,
                'embed': 'false'}
        request_params = {'service': self.URL_REDIRECT}
        auth_response = self.session.post(self.URL_SSO_LOGIN, params=request_params, data=data)
        LOG.debug('authorization respones: {0}'.format(auth_response.text))
        if auth_response.status_code != 200:
            raise ValueError('authentication failed. Check for valid credentials')
        auth_ticket_url = self._extract_auth_ticket_url(auth_response.text)
        LOG.debug("authorization ticket url: {0}".format(auth_ticket_url))

        LOG.info('Claiming authorization ticket')
        response = self.session.get(auth_ticket_url)
        if response.status_code != 200:
            raise RuntimeError("authorization failed to claim auth ticket:"
                               " {url} \n {code} \n {text}".format(url=auth_ticket_url,
                                                                   code=response.status_code,
                                                                   text=response.text))

        # appears like we need to touch base with the old API to initiate
        # some form of legacy session. otherwise certain downloads will fail.
        self.session.get(self.URL_LEGACY_SESSION)

    def _extract_auth_ticket_url(self, auth_response):
        """
        Extract the authentication ticket URL from the response of an
        authentication form submission. The auth ticket URL is typically
        of form:

          https://connect.garmin.com/modern?ticket=ST-0123456-aBCDefgh1iJkLmN5opQ9R-cas

        Parameters:
            auth_response: HTML response from an auth form submission

        .. codeauther:: petergardfjall
        """

        match = re.search(r'response_url\s*=\s*"(https:[^"]+)"', auth_response)
        if not match:
            raise RuntimeError("auth failure: unable to extract auth ticket URL. "
                               "did you provide a correct username/password?")
        auth_ticket_url = match.group(1).replace("\\", "")
        return auth_ticket_url

    def _check_response_code(self, response, act_type=None, activity_id=None):
        """
        check the response for common response codes

        404: Not Found
        204: No Content
        200: Found and no issues
        """

        # A 404 (Not Found) or 204 (No Content) response are both indicators
        # of a gpx file not being available for the activity. It may, for
        # example be a manually entered activity without any device data.
        if response.status_code in (404, 204):
            LOG.error(f"no {act_type} file found for activity " +
                      f"{activity_id}: {response.status_code}\n{response.text}")
            warnings.warn(f"no {act_type} file found for activity " +
                          f"{activity_id}, possible manuel entry: {response.status_code}")
        elif response.status_code != 200:
            LOG.error(f"failed to fetch {act_type} for activity " +
                      f"{activity_id}: {response.status_code}\n{response.text}")
            raise Exception(f"failed to fetch {act_type} for activity " +
                            f"{activity_id}: {response.status_code}\n{response.text}")
        else:
            return True
        return False

    @require_session
    def _fetch_activity_ids_and_ts(self, start_index=0, max_limit=100):
        """Return a sequence of activity ids (along with their starting
        timestamps) starting at a given index, with index 0 being the user's
        most recently registered activity.

        Should the index be out of bounds or the account empty, an empty
        list is returned.

        Parameters:
            start_index (str): The index of the first activity to retrieve.
            max_limit (int): The (maximum) number of activities to retrieve.

        Returns:
            entries (tuple of (int, datetime)): A list of activity identifiers (along with their
                starting timestamps).

        taken from petergardfjall_

        .. _`petergardfjall`: https://github.com/90oak
        """

        end_index = start_index + max_limit - 1
        LOG.debug(f"fetching activities {start_index} through {end_index} ...")
        response = self.session.get(self.URL_ACTIVITY_LIST, params={"start": start_index, "limit": max_limit})
        if response.status_code != 200:
            scode = response.status_code
            text = response.text
            raise Exception(f"failed to fetch activities {start_index} to" +
                            f" {end_index} types: {scode}\n{text}")

        activities = json.loads(response.text)
        if not activities:
            # index out of bounds or empty account
            return []

        entries = []
        for activity in activities:
            activity_id = int(activity["activityId"])
            timestamp_utc = dateutil.parser.parse(activity["startTimeGMT"])
            # make sure UTC timezone gets set
            timestamp_utc = timestamp_utc.replace(tzinfo=dateutil.tz.tzutc())
            entries.append((activity_id, timestamp_utc))
        n_activities = len(entries)
        LOG.debug(f"retrieved {n_activities} activities.")

        return entries

    @require_session
    def _get_activity(self, activity_id, act_type='summary'):
        """
        given an activity id, return the file type

        Parameters:
            activity_id (int): garmin activity id
            act_type (str): `summary`, `details`, `original_file`, `tcx`, `gpx`, `fit`,

        Returns:
            'summary' or 'Details': json.loads(response.text)
            'orginal_file': response
            'tcx', 'gpx', or 'fit': response.text
        """

        session_url = self.activity_urls[act_type]
        response = self.session.get(session_url.format(activity_id=activity_id))
        if self._check_response_code(response, act_type=act_type, activity_id=activity_id):
            if act_type.lower() in ('summary', 'details'):
                return json.loads(response.text)
            if act_type.lower() == 'original_file':
                return response
            return response.text
        return []

    @require_session
    def list_activities(self, batch_size=100, force_reload=False):
        """Return all activity ids stored by the logged in user, along
        with their starting timestamps.

        Returns:
        ids (tuple of (int, datetime)): The full list of activity identifiers
            (along with their starting timestamps).

        taken from petergardfjall_

        .. _`petergardfjall`: https://github.com/90oak
        """

        if not self.activity_list or force_reload:
            ids = []
            # fetch in batches since the API doesn't allow more than a certain
            # number of activities to be retrieved on every invocation
            for start_index in range(0, sys.maxsize, batch_size):
                next_batch = self._fetch_activity_ids_and_ts(start_index, batch_size)
                if not next_batch:
                    break
                ids.extend(next_batch)
            self.activity_list = ids

        return self.activity_list

    @require_session
    def get_wellness_summary_datespan(self, from_date='2018-07-01', until_date='2018-09-01', force_reload=False):
        """Return summary of wellness data stored by the logged in user

        Parameters:
            from_date (str): yyyy-mm-dd
            until_date (str): yyyy-mm-dd

        Returns:
        json dictionary load of response
        """

        fetch_data = False
        if force_reload:
            fetch_data = True
        if from_date != self.wellness_summary_from or until_date != self.wellness_summary_until:
            fetch_data = True

        if fetch_data:
            response = self.session.get(self.URL_WELLNESS.format(username=self.username),
                                      params={"fromDate": from_date, "untilDate": until_date})

            if self._check_response_code(response, act_type="wellness summary",
                                         activity_id=f"{from_date} to {until_date}"):
                self.wellness_summary_from = from_date
                self.wellness_summary_until = until_date
                wellness_response = json.loads(response.text)
                if wellness_response['groupedMetrics']:
                    self.wellness_grouped_summary = wellness_response['groupedMetrics']
                else:
                    wellness_grouped_summary = []

                self.wellness_summary = wellness_response['allMetrics']['metricsMap']
        return self.wellness_summary

    @require_session
    def get_activity_summary(self, activity_id):
        """Return a summary about a given activity. The
        summary contains several statistics, such as duration, GPS starting
        point, GPS end point, elevation gain, max heart rate, max pace, max
        speed, etc.

        Parameters:
            activity_id (int): activity identifier

        Returns:
            dict: the activity summary as a JSON dict.

        """
        response_json = self._get_activity(activity_id, act_type='summary')
        return response_json

    @require_session
    def get_activity_details(self, activity_id):
        """Return a JSON representation of a given activity including
        available measurements such as location (longitude, latitude),
        heart rate, distance, pace, speed, elevation.

        Parameters:
            activity_id (int): activity identifier

        Returns:
            dict: The activity details as a JSON dict.

        """
        response_json = self._get_activity(activity_id, act_type='details')
        return response_json

    @require_session
    def get_activity_gpx(self, activity_id):
        """Return a GPX (GPS Exchange Format) representation of a
        given activity. If the activity cannot be exported to GPX
        (not yet observed in practice, but that doesn't exclude the
        possibility), a :obj:`None` value is returned.

        Parameters:
            activity_id (int): activity identifier

        Returns:
            str: The GPX representation of the activity as an XML string
                or ``None`` if the activity couldn't be exported to GPX.

        """
        # An alternate URL that seems to produce the same results
        # and is the one used when exporting through the Garmin
        # Connect web page.
        # response = self.session.get("https://connect.garmin.com/proxy/activity-service-1.1/gpx/activity/{}?full=true".format(activity_id))

        response_text = self._get_activity(activity_id, act_type='gpx')
        return response_text

    @require_session
    def get_activity_tcx(self, activity_id):
        """Return a TCX (Training Center XML) representation of a
        given activity. If the activity doesn't have a TCX source (for
        example, if it was originally uploaded in GPX format, Garmin
        won't try to synthesize a TCX file) a :obj:`None` value is
        returned.

        Parameters:
            activity_id (int): activity identifier

        Returns:
            str: The TCX representation of the activity as an XML string
            or ``None`` if the activity cannot be exported to TCX.

        """

        response_text = self._get_activity(activity_id, act_type='tcx')
        return response_text

    def get_original_activity(self, activity_id):
        """Return the original file that was uploaded for an activity.
        If the activity doesn't have any file source (for example,
        if it was entered manually rather than imported from a Garmin
        device) then :obj:`(None,None)` is returned.

        Parameters:
            activity_id (int): activity identifier

        Returns:
            (fltype, content): A tuple of the file type (e.g. 'fit', 'tcx', 'gpx') and
                its contents, or `(None,None)` if no file is found.

        """

        response = self._get_activity(activity_id, act_type='original_file')

        # return the first entry from the zip archive where the filename is
        # activity_id (should be the only entry!)
        zip_file = zipfile.ZipFile(StringIO(response.content), mode="r")
        for path in zip_file.namelist():
            filename, ext = os.path.splitext(path)
            if filename == str(activity_id):
                return ext[1:], zip_file.open(path).read()
        return (None, None)


    def get_activity_fit(self, activity_id):
        """Return a FIT representation for a given activity. If the activity
        doesn't have a FIT source (for example, if it was entered manually
        rather than imported from a Garmin device) a :obj:`None` value is
        returned.

        Parameters:
            activity_id (int): activity identifier

        Returns:
            (str): A string with a FIT file for the activity or :obj:`None`
                if no FIT source exists for this activity (e.g., entered manually).

        taken from petergardfjall_

        .. _`petergardfjall`: https://github.com/90oak
        """
        fmt, orig_file = self.get_original_activity(activity_id)
        # if the file extension of the original activity file isn't 'fit',
        # this activity was uploaded in a different format (e.g. gpx/tcx)
        # and cannot be exported to fit
        if fmt == 'fit':
            return orig_file
        return None

    @require_session
    def upload_activity(self, file, format=None, name=None, description=None, activity_type=None, private=None):
        """Upload a GPX, TCX, or FIT file for an activity.

        Parameters:
            file (str, path, or open file): Path or open file for activity to upload
            format (str): file format uploading ('gpx', 'tcx', 'fit'). Will attempt to guess
                if None is provided
            name (str): Optional name for the activity
            description (str): Optional description of the activity
            activity_type (str): Optional activity type ket (lowercase: e.g. running, cycling)
            private (bool): if True, then activity will be set as private

        Returns:
            (int): activity_id of the newly-uploaded activity

        taken from petergardfjall_

        .. _`petergardfjall`: https://github.com/90oak
        """

        if isinstance(file, basestring):
            file = open(file, "rb")

        # guess file type if unspecified
        filename = os.path.basename(file.name)
        _, ext = os.path.splitext(fn)
        if format is None:
            if ext.lower() in ('.gpx', '.tcx', '.fit'):
                format = ext.lower()[1:]
            else:
                raise Exception(u"could not guess file type for {}".format(filename))

        # upload it
        files = dict(data=(filename, file))
        response = self.session.post(self.URL_UPLOAD.format(flformat=format),
                                     files=files, headers={"nk": "NT"})

        # check response and get activity ID
        try:
            j = response.json()["detailedImportResult"]
        except (json.JSONDecodeError, KeyError):
            raise Exception(u"failed to upload {} for activity: {}\n{}".format(
                format, response.status_code, response.text))

        if len(j["failures"]) or len(j["successes"]) < 1:
            raise Exception(u"failed to upload {} for activity: {}\n{}".format(
                format, response.status_code, j["failures"]))

        if len(j["successes"]) > 1:
            raise Exception(u"uploading {} resulted in multiple activities ({})".format(
                format, len(j["successes"])))

        activity_id = j["successes"][0]["internalId"]

        # add optional fields
        data = {}
        if name is not None:
            data['activityName'] = name
        if description is not None:
            data['description'] = name
        if activity_type is not None:
            data['activityTypeDTO'] = {"typeKey": activity_type}
        if private:
            data['privacy'] = {"typeKey": "private"}
        if data:
            data['activityId'] = activity_id
            encoding_headers = {"Content-Type": "application/json; charset=UTF-8"} # see Tapiriik
            response = self.session.put(self.URL_ACTVITY_PUT.format(activity_id), data=json.dumps(data), headers=encoding_headers)
            if response.status_code != 204:
                raise Exception(u"failed to set metadata for activity {}: {}\n{}".format(
                    activity_id, response.status_code, response.text))

        return activity_id

    def Get_RestingHR_Trend(self, from_date, until_date):
        """
        Return list of the resting heart rate for a range of dates

        Parameters:
            from_date (str): yyyy-mm-dd
            until_date (str): yyyy-mm-dd

        Returns:
            rHR (list), Dates (list), n_records (int)
        """
        wellness = self.get_wellness_summary_datespan(from_date=from_date, until_date=until_date)
        rHR = []
        Dates = []
        nrecs = 0
        for hr_data in wellness['WELLNESS_RESTING_HEART_RATE']:
            if hr_data['value']:
                rHR.append(hr_data['value'])
                Dates.append(hr_data['calendarDate'])

        n_records = len(rHR)

        return rHR, Dates, n_records
