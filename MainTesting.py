import pyvisa
from colorama import init, Fore, Back, Style

from Utilities import AUTOCALIBRATE_TO_IDEAL_INCOMING_VOLTAGE, WARM_TEST_EXISTS

init(autoreset=True)
import Utilities

from WorkbookCreator import *
from Tests import *

#init dbs if not already
init_db()

init_trace_db()
Utilities.DUNE_ASCII()

#====================================================TESTING PARAMS====================================================#
#These are to be chosen in accordance with the DC_DC Converter Report 2.1
#voltage autocalibration
IDEAL_INCOMING_VOLTAGE = 5.0
CALIBRATED_VOLTAGE_IN = 5.0
INITIAL_START_UP_VOLTAGE = [58.0,61.0]
INITIAL_START_UP_CURRENT = [-0.035,-0.033]
OUTPUT_VOLTAGE_COLD = [48.0,50.0]
INPUT_CURRENT_COLD = [-0.027,-0.025]
#DEBUG CONFIG SETTINGS
debug = False #general debug to see more numbers during testing
#======================================================================================================================#

#Check for good multimeter and power supply connections
print(Fore.BLUE + "ABRIDGED DCDC CONVERTER TESTING CYCLE")

print("Checking for resources...")
#                                               !!!THIS VERSION NEEDS NO SERIAL RELAY!!!
#RELAY = Utilities.SERIAL_CONNECTOR()
RM = pyvisa.ResourceManager()
DMM,PS = Utilities.RESOURCE_CONNECTOR(RM)

#if it makes it this far, we are good to go
print(Fore.GREEN + "All resources connected successfully.\n")

#Configure and reset meters
DMM.write("*RST")
DMM.write("*CLS")
DMM.write("SENS:FUNC 'VOLT:DC'")
PS.write("*RST")
DMM.write("ROUT:MULT:OPEN (@3)")
DMM.write("ROUT:MULT:OPEN (@2)")
DMM.write("ROUT:MULT:OPEN (@1)")

#testing loop:
first = True
test_more_boards_o7 = True
while test_more_boards_o7:
#smaller footprint data storage
    test_output = {
        "board_id": "NA", #warm

        "calibrated_voltage_warm": -1,
        "mc_ave_vol": -1, #powercyles
        "voltage_dev_warm":-1,
        "mc_ave_cur": -1,
        "within_range1": "NULL",

        "calibrated_voltage_cold": -1,
        "mc_ave_vol_c": -1, #powercylescold
        "voltage_dev_cold":-1,
        "mc_ave_cur_c": -1,
        "within_range2": "NULL",
    }
    trace_output = {
        "multiple_power_cycle_voltage": [],
        "multiple_power_cycle_current": [],

        "multiple_power_cycle_voltage_c": [],
        "multiple_power_cycle_current_c": []
    }

#reset power supply, ask user to replace board
    if not first:
        if input(Fore.MAGENTA + "Test Next Board? (y/n) ").lower() != "y":
            test_more_boards_o7 = False
            break
    PS.write("*RST")
    input(Fore.MAGENTA + "Confirm that all power supply channels are OFF by pressing ENTER")

    if first == True:
        first = False
    else:
        input(Fore.MAGENTA + "Replace current board, press ENTER to continue")

    #this chunk takes a board id and checks to see if db already has warm data, which we will skip if there is
    test_output["board_id"] = input(Fore.MAGENTA + "Board ID: ")
#cold or warm
    CorW = input(Fore.MAGENTA + "Warm or Cold Testing? (W/c)").lower()
    print()

    if CorW =='w':
        input("Press ENTER to continue")
    #this is the abridged test cycle for the current phase of early testing
        #warm
        CALIBRATED_VOLTAGE_IN, inboard = Utilities.AUTOCALIBRATE_TO_IDEAL_INCOMING_VOLTAGE(DMM, PS,
                                                                         IDEAL_INCOMING_VOLTAGE,
                                                                       CALIBRATED_VOLTAGE_IN, debug)
        POWER_CYCLE_TEST(PS,DMM, CorW, CALIBRATED_VOLTAGE_IN,test_output,trace_output)
        test_output["calibrated_voltage_warm"] = (str(round(CALIBRATED_VOLTAGE_IN, 5)) +
                                     " IN " + "/ " + str(round(inboard, 5)) + " OUT")
        if all([test_output["mc_ave_vol"] <= INITIAL_START_UP_VOLTAGE[1],test_output["mc_ave_vol"]>=
                INITIAL_START_UP_VOLTAGE[0], test_output["mc_ave_cur"] <= INITIAL_START_UP_CURRENT[1],
                test_output["mc_ave_cur"] >= INITIAL_START_UP_CURRENT[0]]):
            #pass condition ^
            test_output["within_range1"] = "PASS"
            print("WARM OPERATIONAL RANGE: ",Fore.GREEN + "PASS")
        else:
            test_output["within_range1"] = "FAIL"
            print("WARM OPERATIONAL RANGE: ", Fore.RED + "FAIL")

        insert_warm_traces(test_output["board_id"],
                       trace_output)
        insert_test(test_output)
        print(Fore.LIGHTCYAN_EX + "WARM TEST RESULTS EXPORTED")

    elif CorW == 'c':
        #cold
        input("Press ENTER to continue")
        if not WARM_TEST_EXISTS(str(test_output["board_id"])):
            #doesnt let you write ahead without the warm tests for benchmark
            print(Fore.RED + f"No warm tests exist for{test_output['board_id']}")

        CALIBRATED_VOLTAGE_IN, inboard = Utilities.AUTOCALIBRATE_TO_IDEAL_INCOMING_VOLTAGE(DMM, PS,
                                                                                       IDEAL_INCOMING_VOLTAGE,
                                                                                       CALIBRATED_VOLTAGE_IN, debug)
        POWER_CYCLE_TEST(PS, DMM, CorW, CALIBRATED_VOLTAGE_IN, test_output, trace_output)
        test_output["calibrated_voltage_cold"] = (str(round(CALIBRATED_VOLTAGE_IN, 5)) +
                                          " IN " + "/ " + str(round(inboard, 5)) + " OUT")
        if all([test_output["mc_ave_vol_c"] <= OUTPUT_VOLTAGE_COLD[1],test_output["mc_ave_vol_c"]>=
                OUTPUT_VOLTAGE_COLD[0], test_output["mc_ave_cur_c"] <= INPUT_CURRENT_COLD[1],
                test_output["mc_ave_cur_c"] >= INPUT_CURRENT_COLD[0]]):
            #pass condition ^
            test_output["within_range1"] = "PASS"
            print("COLD OPERATIONAL RANGE: ",Fore.GREEN + "PASS")
        else:
            test_output["within_range1"] = "FAIL"
            print("COLD OPERATIONAL RANGE: ", Fore.RED + "FAIL")

        update_cold_test(test_output)
        update_cold_traces(test_output["board_id"],trace_output)
        print(Fore.LIGHTCYAN_EX + "COLD TEST RESULTS EXPORTED")

    else:
        print(Fore.RED + "Invalid Input")
        continue

    if debug:
        print(test_output)
        print(trace_output)

    print()

#safely close resources i hope
PS.write("*RST")
DMM.write("*RST")
RM.close()
