import csv
import warnings
from collections import namedtuple
import pendulum # Used for parsing date time
import numpy as np

def read_sleepasandroid_file(saa_filename):
    """
    read in a SleepAsAndroid backup file and return it as a parsed list
    """
    with open(saa_filename) as file:
        file_as_list = list(csv.reader(file, delimiter=','))
    return file_as_list

SplitRecord = namedtuple('SasA_SplitRecord', ['start_datetime', 'end_datetime',
                                              'record_start_ms', 'record_end_ms',
                                              'light_sleep', 'deep_sleep',
                                              'rem_sleep', 'awake', 'heart_rate',
                                              'hr_zone', 'noise_events',
                                              'alarms'])


def split_sleepasandroid_record(file_as_list, header_idx):
    """
    this assumes the sleep as android backup file is already parsed into
    a list by using csvreader()

    Parameters:
        file_as_list (list): The sleep as android backup file parsed into
            a list from csvreader
        header_idx (int): The index for the header of the record to parse

    Returns:
        split_record (namedtuple 'SplitRecord')
    """
    # NOTES: ID will = first event timestamp
    # Id	Tz	From	To	Sched	Hours	Rating	Comment	Framerate	Snore	Noise	Cycles	DeepSleep	LenAdjust	Geo

    value_idx = header_idx + 1
    movment_data = []
    # check for manual entries
    for idx, col in enumerate(file_as_list[header_idx][:]):
        if 'id' in col.lower():
            record_id = int(float(file_as_list[value_idx][idx]))
        elif 'tz' in col.lower():
            timezone = file_as_list[value_idx][idx]
        elif 'to' in col.lower():
            start_date_str = file_as_list[value_idx][idx]
        elif 'from' in col.lower():
            end_date_str = file_as_list[value_idx][idx]
        elif 'hours' in col.lower():
            sleep_duration = float(file_as_list[value_idx][idx])
        elif 'snore' in col.lower():
            snore = int(file_as_list[value_idx][idx])
        elif 'noise' in col.lower():
            noise = float(file_as_list[value_idx][idx])
        elif 'cycles' in col.lower():
            sleep_cycles = int(file_as_list[value_idx][idx])
        elif 'deepsleep' in col.lower():
            pct_deep_sleep = float(file_as_list[value_idx][idx])
        elif 'len' in col.lower():
            length_adjust = int(file_as_list[value_idx][idx])
        elif 'geo' in col.lower():
            geo_code = file_as_list[value_idx][idx]
        elif 'comment' in col.lower():
            if 'manually added' in file_as_list[value_idx][idx].lower():
                warnings.warn('manual entry found, unable to parse '
                              'sleep data')
                return
            else:
                comment = file_as_list[value_idx][idx].split(' ')
        elif col.isnumeric():
            movment_data.append(col)

    start_date = pendulum.from_format(start_date_str, 'DD. MM. YYYY HH:mm',
                                      formatter='alternative', tz=timezone)
    end_date = pendulum.from_format(end_date_str, 'DD. MM. YYYY HH:mm',
                                    formatter='alternative', tz=timezone)
    # Parse Events
    light_sleep = []
    deep_sleep = []
    rem_sleep = []
    noise = []
    alarm = []
    hr_zone = []
    hr = []
    awake = []
    record_start_ms = 0
    record_end_ms = 0
    found_record_start = False
    for idx in range(len(file_as_list[header_idx][:])):
        event_idx = header_idx + 1
        if 'event' in file_as_list[header_idx][idx].lower():
            event = file_as_list[event_idx][idx].split('-')
            event_time = int(event[1])
            event_name = event[0]
            if not found_record_start:
                record_time_ms = event_time
                found_record_start = True

            if event_time > record_end_ms:
                record_end_ms = event_time

            if 'LIGHT' in event_name:
                light_sleep.append(event)
            elif 'AWAKE' in event_name:
                awake.append(event)
            elif 'DEEP' in event_name:
                deep_sleep.append(event)
            elif 'HR_' in event_name:
                hr_zone.append(event)
            elif 'HR' in event_name:
                hr.append(event)
            elif 'HR' in event_name:
                hr.append(event)
            elif 'REM' in event_name:
                rem_sleep.append(event)
            elif 'TALK' in event_name or 'SNORING' in event_name:
                noise.append(event)
            elif 'ALARM' in event_name:
                alarm.append(event)
            elif 'USER' in event_name or 'BROKEN' in event_name:
                pass
            else:
                warnings.warn("unrecognized event: {0}".format(event))

    if not light_sleep:
        light_sleep = None
    if not deep_sleep:
        deep_sleep = None
    if not rem_sleep:
        rem_sleep = None
    if not awake:
        awake = None
    if not hr_zone:
        hr_zone = None
    if not hr:
        hr = None
    if not noise:
        noise = None
    if not alarm:
        alarm = None

    split_record = SplitRecord(start_datetime=start_date,
                               end_datetime=end_date,
                               record_start_ms=record_start_ms,
                               record_end_ms=record_end_ms,
                               light_sleep=light_sleep,
                               deep_sleep=deep_sleep, rem_sleep=rem_sleep,
                               alarms=alarm, noise_events=noise,
                               awake=awake, heart_rate=hr, hr_zone=hr_zone)
    return split_record


lightSleepRecord = namedtuple('LightSleep_Record', ['cycle_start_ms',
                                                    'cycle_end_ms',
                                                    'cycle_duration_ms',
                                                    'ncycles'])
deepSleepRecord = namedtuple('DeepSleep_Record', ['cycle_start_ms',
                                                  'cycle_end_ms',
                                                  'cycle_duration_ms',
                                                  'ncycles'])
awakeRecord = namedtuple('Awake_Record', ['cycle_start_ms',
                                          'cycle_end_ms',
                                          'cycle_duration_ms',
                                          'ncycles'])
sleepRecord = namedtuple('Sleep_Record', ['ncycles', 'start_ms',
                                          'end_ms', 'duration_ms',
                                          'stage', 'stage_code'])


def parse_sleep_records(split_record, ls_int_code=2, ds_int_code=1,
                        awake_int_code=3):
    """
    take a list of the sleep events and parse them into namedtuples

    Parameters:
        split_record (namedtuple): `SplitRecord` namedtuple
        ls_int_code (int): integer code for light sleep cycle
        ds_int_code (int): integer code for deep sleep cycle
        awake_int_code (int): integer code for awake cycle

    Returns:
        lightSleep_Record, DeepSleep_Record, sleep_Record
    """

    ls_record = _parse_event(split_record, 'light_sleep')
    ds_record = _parse_event(split_record, 'deep_sleep')
    awake_record = _parse_event(split_record, 'awake')

    # Parse Sleep Cycle Record
    dtype = dtype = [('event', np.object_), ('cycle_start', int), ('cycle_end', int),
                     ('cycle_duration', int), ('event_id', int)]
    values = []
    for idx in range(ls_record.ncycles):
        values.append(('LightSleep', ls_record.cycle_start_time[idx],
                       ls_record.cycle_end_time[idx],
                       ls_record.cycle_duration[idx],
                       ls_int_code))
    for idx in range(ds_record.ncycles):
        values.append(('DeepSleep', ds_record.cycle_start_time[idx],
                       ds_record.cycle_end_time[idx],
                       ds_record.cycle_duration[idx],
                       ds_int_code))
    for idx in range(awake_record.ncycles):
        values.append(('Awake', awake_record.cycle_start_time[idx],
                       awake_record.cycle_end_time[idx],
                       awake_record.cycle_duration[idx],
                       awake_int_code))

    combined_fields = np.array(values, dtype=dtype)       # create a structured array
    sorted_records = np.sort(combined_fields, order='cycle_start')

    sleep_record = sleepRecord(ncycles=len(sorted_records),
                               start_ms=sorted_records['cycle_start'],
                               end_ms=sorted_records['cycle_end'],
                               duration_ms=sorted_records['cycle_duration'],
                               stage=sorted_records['event'],
                               stage_code=sorted_records['event_id'])

    return sleep_record, ls_record, ds_record, awake_record


sleepStageRecord = namedtuple('sleepStageRecord', ['sleep_stage',
                                                   'cycle_start_time',
                                                   'cycle_end_time',
                                                   'cycle_duration',
                                                   'ncycles'])

def _parse_event(split_record_namedtuple, event):
    """
    parse a list of the different sleep events for one record and return the
    lightSleep_Record namedtuple

    Parameters:
        split_record_namedtuple: A `SasA_SplitRecord` namedtuple instance
        event (str): acceptable events are `light_sleep`, `deep_sleep`, `awake`, `rem_sleep`
    """
    timezone = split_record_namedtuple.start_datetime.timezone
    start_time = []
    end_time = []
    cycle_duration = []
    event_as_list = getattr(split_record_namedtuple, event)
    nrecords = len(event_as_list)
    ncycles = int(nrecords/2)
    # Loop through and parse light sleep event record times
    for idx in range(0, nrecords, 2):
        start_java_timestamp = int(event_as_list[idx][1])
        seconds = start_java_timestamp / 1000
        sub_seconds = (start_java_timestamp % 1000.0) / 1000.0
        cycle_starttime = pendulum.from_timestamp(seconds + sub_seconds,
                                                  tz=timezone)

        end_java_timestamp = int(event_as_list[idx+1][1])
        seconds = end_java_timestamp / 1000
        sub_seconds  = (end_java_timestamp % 1000.0) / 1000.0
        cycle_endtime = pendulum.from_timestamp(seconds + sub_seconds,
                                                tz=timezone)
        start_time.append(cycle_starttime)
        end_time.append(cycle_endtime)
        cycle_duration.append(cycle_starttime.diff(cycle_endtime))
    record = sleepStageRecord(sleep_stage=event,
                              cycle_start_time=start_time,
                              cycle_end_time=end_time,
                              cycle_duration=cycle_duration,
                              ncycles=ncycles)
    return record
