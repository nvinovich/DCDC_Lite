import os
import time
from os.path import samefile

import pyvisa
from colorama import init, Fore, Back, Style
from numpy.ma.extras import average
from pandas.core.config_init import pc_max_cols_doc
init(autoreset=True)
import numpy as np
from pyvisa import Resource
import matplotlib.pyplot as mp
show_plots = False

#               !!! I suppose we dont need most of the tests for this version !!!

def POWER_CYCLE_TEST(PS,DMM,which,
                     CALIBRATED_VOLTAGE_IN, test_output,trace_output):
    '''Turns on board, waits for stabilized time and then records, repeats 10 times.'''

    pc_vols = []
    pc_cur = []
    DMM.write("*RST")
    DMM.write("*CLS")
    PS.write("*RST")

    PS.write("VOLT " + str(CALIBRATED_VOLTAGE_IN))
    PS.write("CURR 0.033")
    for i in range(10):

    #i mostly just copied from aove to save times here
        time.sleep(0.1)
        DMM.write('FUNC "VOLT:DC"')
        DMM.write("ROUT:MULT:CLOS (@3)")
        DMM.write('TRAC:CLE "defbuffer1"')
        DMM.write('TRAC:POIN 10')
        DMM.write('TRIG:LOAD "SimpleLoop",10,0.05')
        PS.write("OUTP ON")
    #sorry this delay needed to be so long, voltage is somewhat slow to stabilize from off state
    #ask jane if we care ab that
        time.sleep(2)
        DMM.write('INIT')

        DMM.query("*OPC?")
        DMM.write("ROUT:MULT:OPEN (@3)")

        n = int(DMM.query('TRAC:ACT? "defbuffer1"'))
        data = DMM.query(f'TRAC:DATA? 1,{n},"defbuffer1",READ')
        datalist = list(data.split(','))
        datalist = [
            round(float(datalist[i][:datalist[i].index("E")]) * 10 ** int(datalist[i][datalist[i].index("E") + 1:]), 5)
            for i in range(len(datalist))]
        for i in datalist:
            pc_vols.append(i)

        DMM.write('FUNC "VOLT:DC"')
        DMM.write("ROUT:MULT:CLOS (@2)")
        DMM.write('TRAC:CLE "defbuffer1"')
        DMM.write('TRAC:POIN 10')
        DMM.write('TRIG:LOAD "SimpleLoop",10,0.05')
        time.sleep(2)
        DMM.write('INIT')

        DMM.query("*OPC?")
        DMM.write("ROUT:MULT:OPEN (@2)")
        n = int(DMM.query('TRAC:ACT? "defbuffer1"'))
        data = DMM.query(f'TRAC:DATA? 1,{n},"defbuffer1",READ')
        datalist = list(data.split(','))
        datalist = [
            round(float(datalist[i][:datalist[i].index("E")]) * 10 ** int(datalist[i][datalist[i].index("E") + 1:]), 5)
            for i in range(len(datalist))]
        for i in datalist:
            pc_cur.append(i)

        PS.write("OUTP OFF")
        time.sleep(0.1)

    # Calculate statistics
    avg_voltage = np.mean(pc_vols)
    std_voltage = np.std(pc_vols)
    ave_current = np.mean(pc_cur)

    #this selects which data sheet to update
    if which == "w":
        test_output["mc_ave_vol"]= avg_voltage
        test_output["mc_ave_cur"] = ave_current
        trace_output["multiple_power_cycle_voltage"] = pc_vols
        trace_output["multiple_power_cycle_current"] = pc_cur
        test_output["voltage_dev_warm"] = std_voltage
    elif which == "c":
        test_output["mc_ave_vol_c"]= avg_voltage
        test_output["mc_ave_cur_c"] = ave_current
        trace_output["multiple_power_cycle_voltage_c"] = pc_vols
        trace_output["multiple_power_cycle_current_c"] = pc_cur
        test_output["voltage_dev_cold"] = std_voltage
