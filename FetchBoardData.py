import os
import time
from colorama import Fore,init
import psycopg
import sys
import subprocess
from WorkbookCreator import *
import matplotlib.pyplot as mp
import numpy as np
init(autoreset=True)

#updates here too
DB_INFO = {
    "host": "localhost",
    "dbname": "dcdc_tests_lite",
    "user": "studadmin",
    "password": "password",
    "port": 5432
}
def get_connection():
    return psycopg.connect(**DB_INFO)

#Run this file to update data in your local spreadsheet, but replace the following parameter with system desktop path or
#other desired download destination:
DD = rf"C:\Users\StudentAdmin\Desktop"
XLSX_NAME= "TESTS"

def Trace_Getter(board_id,output_path):
    '''Writes the data for the trace of a board to a file'''
    #again im very iffy about sql atm but this should work mostly fine
    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                           SELECT *
                           FROM board_traces
                           WHERE board_id = %s
                       """, (board_id,))

            row = cursor.fetchone()

            if row is None:
                sys.exit(f"No trace data found for board {board_id}")

            columns = [desc[0] for desc in cursor.description]
        data = dict(zip(columns, row))

        trace_pairs = {

            "Multiple Power Cycle Warm": (
                "multiple_power_cycle_voltage",
                "multiple_power_cycle_current"
            ),
            "Multiple Power Cycle Cold": (
                "multiple_power_cycle_voltage_c",
                "multiple_power_cycle_current_c")
        }

        with pd.ExcelWriter(output_path, engine="openpyxl") as writer:

            for name, (vol_col, cur_col) in trace_pairs.items():

                voltage = data.get(vol_col)
                current = data.get(cur_col)

                if voltage is not None:

                    voltage = json.loads(voltage)

                    output = {
                        "Sample": range(len(voltage)),
                        "Voltage": voltage
                    }

                    if current is not None:
                        current = json.loads(current)
                        output["Current"] = current

                    df = pd.DataFrame(output)

                    df.to_excel(
                        writer,
                        sheet_name=name[:31],
                        index=False
                    )
        wb = load_workbook(output_path)

        for ws in wb:
            for col in ws.columns:
                max_length = max(
                    len(str(cell.value)) if cell.value else 0
                    for cell in col
                )
                ws.column_dimensions[col[0].column_letter].width = max_length + 3
        wb.save(output_path)
        print(Fore.LIGHTCYAN_EX + f"{board_id} TRACE DOWNLOAD COMPLETE")

def Export_All_Traces(output_folder):
    """Exports every board trace to its own xlsx file"""
    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(
                "SELECT board_id FROM board_traces"
            )

            board_ids = [
                row[0]
                for row in cursor.fetchall()
            ]

    if not board_ids:
        sys.exit("No trace data found.")
    for board_id in board_ids:
        output_path = os.path.join(
            output_folder,
            f"{board_id}_Trace_Data.xlsx"
        )
        Trace_Getter(board_id, output_path)

    print(Fore.GREEN + "ALL TRACE DOWNLOADS COMPLETE")

def Test_Results_Getter(DD, XLSX_NAME) -> None:
    '''Writes out the test data for full database onto one xlsx file'''

    output_file = DD + rf"\{XLSX_NAME}.xlsx"
    #this part got really ugly tbf
    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
                SELECT *
                FROM dc_dc_tests
            """)
            rows = cursor.fetchall()

            columns = [
                desc[0]
                for desc in cursor.description
            ]

    df = pd.DataFrame(
        rows,
        columns=columns
    )

    df = df.rename(columns={
        "board_id": "BOARD ID",
        "timestamp": "TIMESTAMP",

        "calibrated_voltage_warm": "CALIBRATED INPUT VOLTAGE (WARM)",
        "voltage_dev_warm": "WARM VOLTAGE DEVIATION",
        "mc_ave_vol": "WARM POWERCYCLE AVE VOLTAGE",
        "mc_ave_cur": "WARM POWERCYCLE AVE CURRENT",
        "within_range1": "WARM OPERATIONAL RANGE",

        "calibrated_voltage_cold": "CALIBRATED INPUT VOLTAGE (COLD)",
        "voltage_dev_cold": "COLD VOLTAGE DEVIATION",
        "mc_ave_vol_c": "COLD_POWERCYCLE_AVE_VOLTAGE",
        "mc_ave_cur_c": "COLD_POWERCYCLE_AVE_CURRENT",
        "within_range2": "COLD OPERATIONAL RANGE",

    })
    df.to_excel(output_file, index=False)
    wb = load_workbook(output_file)
    ws = wb.active

    for col in ws.columns:
        max_len = 0
        col_letter = col[0].column_letter

        for cell in col:
            if cell.value:
                max_len = max(
                    max_len,
                    len(str(cell.value))
                )

        ws.column_dimensions[col_letter].width = max_len + 3

    wb.save(output_file)

def Voltage_Histogram(board_id,xrs,temp="(Warm)",
                      trace_column="multiple_power_cycle_voltage",
                      output_folder=r"C:\Users\StudentAdmin\Desktop"):
    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute(f"""
                SELECT {trace_column}
                FROM board_traces
                WHERE board_id = %s
            """, (board_id,))

            row = cursor.fetchone()

    if row is None:
        print(f"No data found for board {board_id}")
        return

    if row[0] is None:
        print(f"{trace_column} is empty for board {board_id}")
        return

    pc_vols = json.loads(row[0])

    avg_voltage = np.mean(pc_vols)
    std_voltage = np.std(pc_vols)

    mp.figure(figsize=(8,5))

    mp.hist(
        pc_vols,
        bins=50
    )
    #added in clearance zone plotting
    mp.axvspan(xrs[0],xrs[1], alpha=0.35, color="grey", label="Ideal Operating Range")

    mp.legend(
        title=f"Ave = {avg_voltage:.5f} V\nStDev = {std_voltage:.5f} V"
    )

    mp.title(f"Voltage Behavior for {board_id}" + temp)
    mp.xlabel("Voltage (V)")
    mp.ylabel("Samples at Voltage")
    mp.grid(True)

    filename = f"{board_id}_{trace_column}.png"
    save_path = os.path.join(output_folder, filename)

    mp.savefig(save_path, dpi=300, bbox_inches="tight")
    mp.close()

    print(Fore.GREEN + f"Histogram saved to:\n{save_path}")


def Plot_All_Board_Voltages(yrs,
        trace_column="multiple_power_cycle_voltage",
        output_folder=r"C:\Users\StudentAdmin\Desktop",
        graph_sub_title = "Voltage Stabily over 10 Power Cycles (Warm)"
):
    board_data = []

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(f"""
                SELECT board_id, {trace_column}
                FROM board_traces
                WHERE {trace_column} IS NOT NULL
            """)

            rows = cursor.fetchall()

    if not rows:
        print(Fore.RED + "No voltage trace data found.")
        return

    for board_id, trace in rows:
        voltage_samples = json.loads(trace)

        average = np.mean(voltage_samples)
        deviation = np.std(voltage_samples)

        board_data.append(
            (
                board_id,
                average,
                deviation
            )
        )
    boards = [x[0] for x in board_data]
    averages = [x[1] for x in board_data]
    deviations = [x[2] for x in board_data]
    x = np.arange(len(boards))

    mp.figure(figsize=(12, 6))

    mp.errorbar(
        x,
        averages,
        yerr=deviations,
        color="blue",
        ecolor="blue",
        fmt='o',
        capsize=5,
        label="Average Voltage ± Std Dev")
    mp.xticks(
        x,boards,rotation=45,
        ha="right"
    )
    #lines to indicate good boundaries
    mp.axhspan(
        yrs[0],
        yrs[1],
        alpha=0.2,
        color="grey",
        label="Ideal Operating Range"
    )
    mp.xlabel("Board ID")
    mp.ylabel("Voltage (V)")
    mp.title(graph_sub_title)

    mp.grid(True)
    mp.legend()

    mp.tight_layout()

    filename = f"All_Board_Average_Voltage_{trace_column}.png"
    save_path = os.path.join(output_folder, filename)

    mp.savefig(
        save_path,
        dpi=300,
        bbox_inches="tight"
    )

    mp.close()

    print(Fore.GREEN + f"Plot saved to:\n{save_path}")



if __name__ == "__main__":
    TRCHOICE = input(Fore.MAGENTA + ">Download full SQL data to PC (1)\n"
                                    ">Download full SQL data to external drive (2)\n"
                                    ">Download voltage stability plot (3)\n"
                            "Choose a readback option: ")

    if TRCHOICE == "1":
        folder_path = os.path.join(DD, "DB_IMAGE")

        try:
            os.makedirs(folder_path, exist_ok=True)
            Test_Results_Getter(folder_path,XLSX_NAME)
            print(Fore.GREEN + "TEST DOWNLOAD COMPLETE")
            #now that this saves, lets give it a moment and then write all trace data, this may take some time
            time.sleep(0.2)
            Export_All_Traces(folder_path)

        #just some generic error throws I stole that should be helpful
        except PermissionError:
            print("Error: No permission to write to this drive.")
        except OSError as e:
            print(f"Error creating folder or file: {e}")

    elif TRCHOICE == "2":
        drive_letter = "D"
        # needs usb or other external mount at D
        if os.path.exists(f"{drive_letter.upper()}:\\"):
            print(f"{drive_letter.upper()}: DRIVE FOUND")

            folder_path = os.path.join(f"{drive_letter.upper()}:\\", "DB_IMAGE")

            try:
                # this is the actual writing setp, maybe I should prompt this for every n tests
                os.makedirs(folder_path, exist_ok=True)
                Test_Results_Getter(folder_path, XLSX_NAME)
                print(Fore.GREEN + "TEST DOWNLOAD COMPLETE")
                # now that this saves, lets give it a moment and then write all trace data, this may take some time
                time.sleep(0.2)
                Export_All_Traces(folder_path)

            # just some generic error throws I stole that should be helpful
            except PermissionError:
                print("Error: No permission to write to this drive.")
            except OSError as e:
                print(f"Error creating folder or file: {e}")
        else:
            print(f"{drive_letter.upper()}: DRIVE NOT FOUND.")

    elif TRCHOICE == "3":
        if input("Warm or Cold Stability? (W/c)").lower() =="w":

            Plot_All_Board_Voltages([58.0,61.0])
            sys.exit()
        Plot_All_Board_Voltages([48.0,50.0],trace_column="multiple_power_cycle_voltage_c",
             graph_sub_title= "Voltage Stabily over 10 Power Cycles (Cold)")

    elif TRCHOICE == "4":
        #specific board behavior plotting
        board_id = int(input("Board ID: "))
        if input("Warm or Cold Stability? (W/c)").lower() == "w":

            Voltage_Histogram(board_id,[58.0,61.0])
            sys.exit()
        Voltage_Histogram(board_id,trace_column="multiple_power_cycle_voltage_c",
                         xrs=[48.0,50.0], temp= "(Cold)")

    elif TRCHOICE == "0":
        #renames id as debug option
        print("debug change bd id")
        board_id = input("Board ID: ")
        new_id = input("New board ID: ")
        rename_board_id(board_id,new_id)

    else:
        sys.exit("INVALID SELECTION")