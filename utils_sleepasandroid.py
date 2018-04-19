import numpy as np
import csv
import humanfriendly
import warnings
from collections import namedtuple

def read_sleepasandroid_file(saa_filename):
    """
    read in a SleepAsAndroid backup file and return it as a parsed list
    """
    with open(saa_filename) as fl:
        file_as_list = list(csv.reader(fl, delimiter=','))
    return file_as_list

def split_sleepasandroid_record(file_as_list, header_idx):
    """
    this assumes the sleep as android backup file is already parsed into
    a list by using csvreader()

    """
    light_sleep = []
    deep_sleep = []
    hr_zone = []
    hr = []

    found_record_start = False
    for idx in range(len(file[header_idx][:])):
        event_idx = header_idx + 1
        if 'event' in file[header_idx][idx].lower():
            event = file[event_idx][idx].split('-')
            if not found_record_start:
                start_time_ms = event[1]
                found_record_start = True
            if 'LIGHT' in event[0]:
                light_sleep.append(event)
            elif 'DEEP' in event[0]:
                deep_sleep.append(event)
            elif 'HR_' in event[0]:
                hr_zone.append(event)
            elif 'HR' in event[0]:
                hr.append(event)
            else:
                warnings.warn("unrecognized event: {0}".format(event))
    return start_time_ms, light_sleep, deep_sleep, hr, hr_zone


lightSleep_Record = namedtuple('LightSleep_Record', ['cycle_start_ms', 'cycle_duration_ms', 'ncycles'])
deepSleep_Record = namedtuple('DeepSleep_Record', ['cycle_start_ms', 'cycle_duration_ms', 'ncycles'])
sleep_Record = namedtuple('Sleep_Record', ['ncycles', 'start_ms', 'duration_ms', 'stage', 'stage_code'])


def parse_sleep_records(ls_events_as_list, ds_events_as_list, start_time_ms,
                        ls_int_code=2, ds_int_code=1):
    """
    take a list of the sleep events and parse them into namedtuples

    Parameters:
        ls_events_as_list (list): a list of the light sleep events for one record
        ls_events_as_list (list): a list of the light sleep events for one record

    Returns:
        lightSleep_Record, DeepSleep_Record, sleep_Record
    """
    ls_record = _parse_lightsleep_events(ls_events_as_list, start_time_ms)
    ds_record = _parse_deepsleep_events(ds_events_as_list, start_time_ms)

    ## Parse Sleep Cycle Record

    total_cycles = DS.ncycles + LS.ncycles
    start_times = []
    time_delta = []
    stage = []
    stagecode = []
    idx_ds = 0
    idx_ls = 0
    # The first event is always going to be a lightsleep event
    # and the events will always alternate
    grab_ls_cycle = True
    grab_ds_cycle = False
    ncycle = 0
    for idx in range(total_cycles):
        if grab_ls_cycle:
            start_times.append(LS.cycle_start_ms[idx_ls])
            time_delta.append(LS.cycle_duration_ms[idx_ls])
            stage.append('LightSleep')
            stagecode.append(ls_int_code)
            idx_ls += 1
            # Swap so that we grab deepsleep record next
            grab_ls_cycle = False
            grab_ds_cycle = True
        elif grab_ds_cycle:
            start_times.append(DS.cycle_start_ms[idx_ds])
            time_delta.append(DS.cycle_duration_ms[idx_ds])
            stage.append('DeepSleep')
            stagecode.append(ds_int_code)
            idx_ds += 1
            # Swap so that we grab lightsleep record next
            grab_ls_cycle = True
            grab_ds_cycle = False
        ncycle += 1
    s_record = sleep_Record(ncycles=ncycle, start_ms=np.array(start_times),
                            duration_ms=np.array(time_delta),
                            stage=np.array(stage),
                            stage_code=np.array(stagecode))

    return s_record, ls_record, ds_record

def _parse_lightsleep_events(ls_events_as_list, start_time_ms):
    """
    parse a list of the lightsleep events for one record and return the
    lightSleep_Record namedtuple
    """
    msecs = []
    time_delta = []

    ncycles = int(len(ls_events_as_list)/2)
    # Loop through and parse light sleep event record times
    for idx_ls, idx  in enumerate(range(0, len(ls_events_as_list), 2)):
        delta = int(ls_events_as_list[idx+1][1]) - int(ls_events_as_list[idx][1])
        time_delta.append(delta)
        cycle_starttime_ms = int(ls_events_as_list[idx][1]) - int(start_time_ms)
        msecs.append(cycle_starttime_ms)
    ls_record = lightSleep_Record(cycle_start_ms=np.array(msecs),
                                  cycle_duration_ms=np.array(time_delta),
                                  ncycles=ncycles)
    return ls_record

def _parse_deepsleep_events(ds_events_as_list, start_time_ms):
    """
    parse a list of the lightsleep events for one record and return the
    deepSleep_Record namedtuple
    """
    msecs = []
    time_delta = []

    ncycles = int(len(ds_events_as_list)/2)
    # Loop through and parse deep sleep event record times
    for idx_ls, idx  in enumerate(range(0, len(ds_events_as_list), 2)):
        delta = int(ds_events_as_list[idx+1][1]) - int(ds_events_as_list[idx][1])
        time_delta.append(delta)
        cycle_starttime_ms = int(ds_events_as_list[idx][1]) - int(start_time_ms)
        msecs.append(cycle_starttime_ms)
    ds_record = deepSleep_Record(cycle_start_ms=np.array(msecs),
                                 cycle_duration_ms=np.array(time_delta),
                                 ncycles=ncycles)
    return ds_record


def parse_sleep_record(sleep_events_as_list, namedtuple_obj, start_time_ms):
    """
    parse a list of either the lightsleep or deepsleep events for one
    record and return the namedtuple_obj
    """
    msecs = []
    time_delta = []

    ncycles = int(len(sleep_events_as_list)/2)
    # Loop through and parse light sleep event record times
    for idx_ls, idx  in enumerate(range(0, len(sleep_events_as_list), 2)):
        delta = int(sleep_events_as_list[idx+1][1]) - int(sleep_events_as_list[idx][1])
        time_delta.append(delta)
        cycle_starttime_ms = int(sleep_events_as_list[idx][1]) - int(start_time_ms)
        msecs.append(cycle_starttime_ms)
    s_record = namedtuple_obj(cycle_start_ms=np.array(msecs),
                              cycle_duration_ms=np.array(time_delta),
                              ncycles=ncycles)
    return s_record
