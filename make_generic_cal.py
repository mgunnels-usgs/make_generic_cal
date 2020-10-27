#!/usr/bin/env python
import argparse
from obspy import read
from obspy.core import UTCDateTime
import subprocess
import shutil
import os
import struct
import stat

workingdir=os.getcwd()



st=read("/msd/IC_BJT/2020/267/_BC0.512.seed")            # Defines generic calibration input sequence

def main():


    outcal_file_dir= getargs()
    outcal_file_name=outcal_file_dir.datadir
    dir_list=outcal_file_dir.datadir.split('/')
    sta_name=dir_list[2]

    shutil.copy2(outcal_file_dir.datadir, workingdir)
    incal_file_name='/msd/IC_BJT/2020/267/00_BHZ.512.seed'
    out_cal_file=get_calibrations(outcal_file_name)
    out_cal_begin=UTCDateTime(out_cal_file[0]['start_time'])

    in_cal_file=get_calibrations(incal_file_name)
    in_cal_begin=UTCDateTime(in_cal_file[0]['start_time'])

    dt=out_cal_begin-in_cal_begin                              # find time shift needed to align cal input / output blockettes


    for tr in st:
        tr.stats.starttime=tr.stats.starttime+dt                   # add time shift to input blockette


    st.write(sta_name + '_BC0_generic.512.seed', format='MSEED')            # write generic input blockette for output blockette time

def getargs():
    " Gets user arguments"
    parser = argparse.ArgumentParser(description = "For corresponding calibration output 00_BHZ.512.seed."
                                                   "Program outputs a generic input sequence _BC.512.seed ")

    parser.add_argument('-datadir', type=str, action="store",
                         dest = "datadir", required=True,
                         help="Directory Path for output cal seed file e.g. /msd/IC_XAN/2020/273/00_BHZ.512.seed")


    parser_val = parser.parse_args()

    return parser_val


def get_calibrations(file_name, debug = False):

    calibrations = []

    #Read the first file and get the record length from blockette 1000
    fh = open(file_name, 'rb')
    record = fh.read(256)
    index = struct.unpack('>H', record[46:48])[0]
    file_stats = os.stat(file_name)
    record_length = 2 ** struct.unpack('>B', record[index+6:index+7])[0]

    #Get the total number of records

    total_records = file_stats[stat.ST_SIZE] / record_length

    #Now loop through the records and look for calibration blockettes

    for rec_idx in range(0,int(total_records)):
        fh.seek(rec_idx * record_length,0)
        record = fh.read(record_length)
        next_blockette = struct.unpack('>H', record[46:48])[0]
        while next_blockette != 0:
            index = next_blockette
            blockette_type, next_blockette = struct.unpack('>HH', record[index:index+4])
            if blockette_type in (300, 310, 320, 390):
                if debug:
                    print('We have a calibration blockette')
                year,jday,hour,minute,sec,_,tmsec,_,cal_flags,duration = tuple(struct.unpack('>HHBBBBHBBL', record[index+4:index+20]))
                stime = UTCDateTime(year=year,julday=jday,hour=hour,minute=minute,second=sec)
                if debug:
                    print(stime.ctime())
                if blockette_type == 300:
                    step_count,_,_,ntrvl_duration,amplitude,cal_input = struct.unpack('>BBLLf3s', record[index+14:index+31])
                    calibrations.append({'type':'step','amplitude': amplitude,'number':step_count,'start_time':stime,'duration':duration/10000,'inteveral_duration':ntrvl_duration})
                if blockette_type == 310:
                    signal_period,amplitude,cal_input = struct.unpack('>ff3s', record[index+20:index+31])
                    calibrations.append({'type':'sine','amplitude': amplitude, 'period': signal_period,'start_time':stime,'duration':duration/10000})
                if blockette_type in (320, 390):
                    amplitude,cal_input = struct.unpack('>f3s', record[index+20:index+27])
                    calibrations.append({'type':'random','amplitude': amplitude,'start_time':stime,'duration':duration/10000})

    fh.close()

    return calibrations


if __name__ == "__main__":
    main()
