import csv
import warnings
from collections import namedtuple
# import humanfriendly
import numpy as np


def read_sleepasandroid_file(saa_filename):
    """
    read in a SleepAsAndroid backup file and return it as a parsed list
    """
    with open(saa_filename) as file:
        file_as_list = list(csv.reader(file, delimiter=','))
    return file_as_list

SplitRecord = namedtuple('SasA_SplitRecord', ['start_time_ms', 'end_time_ms', 'light_sleep', 'deep_sleep',
                                              'awake', 'hr', 'hr_zone'])


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
    light_sleep = []
    deep_sleep = []
    hr_zone = []
    hr = []
    awake = []
    end_time_ms = 0

    found_record_start = False
    for idx in range(len(file_as_list[header_idx][:])):
        event_idx = header_idx + 1
        if 'event' in file_as_list[header_idx][idx].lower():
            event = file_as_list[event_idx][idx].split('-')
            event_time = int(event[1])
            event_name = event[0]
            if not found_record_start:
                start_time_ms = event_time
                found_record_start = True

            if event_time > end_time_ms:
                end_time_ms = event_time

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
            elif 'USER' in event_name:
                pass
            else:
                warnings.warn("unrecognized event: {0}".format(event))

    split_record = SplitRecord(start_time_ms=start_time_ms,
                               light_sleep=np.array(light_sleep),
                               deep_sleep=np.array(deep_sleep),
                               awake=np.array(awake), hr=np.array(hr),
                               hr_zone=np.array(hr_zone), end_time_ms=end_time_ms)
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
    ls_record = _parse_lightsleep_events(split_record.light_sleep, split_record.start_time_ms)
    ds_record = _parse_deepsleep_events(split_record.deep_sleep, split_record.start_time_ms)
    awake_record = _parse_awake_events(split_record.awake, split_record.start_time_ms)

    # Parse Sleep Cycle Record
    dtype = dtype = [('event', np.object_), ('cycle_start', int), ('cycle_end', int),
                     ('cycle_duration', int), ('event_id', int)]
    values = []
    for idx in range(ls_record.ncycles):
        values.append(('LightSleep', ls_record.cycle_start_ms[idx],
                       ls_record.cycle_end_ms[idx],
                       ls_record.cycle_duration_ms[idx],
                       ls_int_code))
    for idx in range(ds_record.ncycles):
        values.append(('DeepSleep', ds_record.cycle_start_ms[idx],
                       ds_record.cycle_end_ms[idx],
                       ds_record.cycle_duration_ms[idx],
                       ds_int_code))
    for idx in range(awake_record.ncycles):
        values.append(('Awake', awake_record.cycle_start_ms[idx],
                       awake_record.cycle_end_ms[idx],
                       awake_record.cycle_duration_ms[idx],
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


def _parse_lightsleep_events(ls_events_as_list, start_time_ms):
    """
    parse a list of the lightsleep events for one record and return the
    lightSleep_Record namedtuple
    """
    start_ms = []
    end_ms = []
    time_delta = []

    ncycles = int(len(ls_events_as_list)/2)
    # Loop through and parse light sleep event record times
    for idx in range(0, len(ls_events_as_list), 2):
        cycleEnd_ms = int(ls_events_as_list[idx+1][1])
        cycleStart_ms = int(ls_events_as_list[idx][1])
        delta = cycleEnd_ms - cycleStart_ms
        time_delta.append(delta)
        cycle_starttime = cycleStart_ms - start_time_ms
        cycle_endtime = cycleEnd_ms - start_time_ms
        start_ms.append(cycle_starttime)
        end_ms.append(cycle_endtime)
    ls_record = lightSleepRecord(cycle_start_ms=np.array(start_ms),
                                 cycle_end_ms=np.array(end_ms),
                                 cycle_duration_ms=np.array(time_delta),
                                 ncycles=ncycles)
    return ls_record


def _parse_deepsleep_events(ds_events_as_list, start_time_ms):
    """
    parse a list of the lightsleep events for one record and return the
    deepSleep_Record namedtuple
    """
    start_ms = []
    end_ms = []
    time_delta = []

    ncycles = int(len(ds_events_as_list)/2)
    # Loop through and parse light sleep event record times
    for idx in range(0, len(ds_events_as_list), 2):
        cycleEnd_ms = int(ds_events_as_list[idx+1][1])
        cycleStart_ms = int(ds_events_as_list[idx][1])
        delta = cycleEnd_ms - cycleStart_ms
        time_delta.append(delta)
        cycle_starttime = cycleStart_ms - start_time_ms
        cycle_endtime = cycleEnd_ms - start_time_ms
        start_ms.append(cycle_starttime)
        end_ms.append(cycle_endtime)
    ds_record = deepSleepRecord(cycle_start_ms=np.array(start_ms),
                                cycle_end_ms=np.array(end_ms),
                                cycle_duration_ms=np.array(time_delta),
                                ncycles=ncycles)
    return ds_record


def _parse_awake_events(awake_events_as_list, start_time_ms):
    """
    parse a list of the awake events for one record and return the
    awake_Record namedtuple
    """
    start_ms = []
    end_ms = []
    time_delta = []

    ncycles = int(len(awake_events_as_list)/2)
    # Loop through and parse light sleep event record times
    for idx in range(0, len(awake_events_as_list), 2):
        cycleEnd_ms = int(awake_events_as_list[idx+1][1])
        cycleStart_ms = int(awake_events_as_list[idx][1])
        delta = cycleEnd_ms - cycleStart_ms
        time_delta.append(delta)
        cycle_starttime = cycleStart_ms - start_time_ms
        cycle_endtime = cycleEnd_ms - start_time_ms
        start_ms.append(cycle_starttime)
        end_ms.append(cycle_endtime)
    awake_record = awakeRecord(cycle_start_ms=np.array(start_ms),
                               cycle_end_ms=np.array(end_ms),
                               cycle_duration_ms=np.array(time_delta),
                               ncycles=ncycles)
    return awake_record


def _parse_sleep_record(sleep_events_as_list, namedtuple_obj, start_time_ms):
    """
    parse a list of either the lightsleep or deepsleep events for one
    record and return the namedtuple_obj
    """
    msecs = []
    time_delta = []

    ncycles = int(len(sleep_events_as_list)/2)
    # Loop through and parse light sleep event record times
    for idx in range(0, len(sleep_events_as_list), 2):
        delta = int(sleep_events_as_list[idx+1][1]) - int(sleep_events_as_list[idx][1])
        time_delta.append(delta)
        cycle_starttime_ms = int(sleep_events_as_list[idx][1]) - int(start_time_ms)
        msecs.append(cycle_starttime_ms)
    s_record = namedtuple_obj(cycle_start_ms=np.array(msecs),
                              cycle_duration_ms=np.array(time_delta),
                              ncycles=ncycles)
    return s_record
