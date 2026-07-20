import psycopg
import pandas as pd
from datetime import datetime
from openpyxl import load_workbook
import json
from openpyxl.styles import Font, PatternFill, Alignment
#this will be a fairly major change away from sql lite to psygopg so i hope it works?
DB_INFO = {
    "host": "localhost",
    #server ip is: 172.17.106.247, replace with host if not using the server computer
    "dbname": "dcdc_tests_lite",
    "user": "studadmin",
    "password": "password",
    "port": 5432
}
def get_connection():
    return psycopg.connect(**DB_INFO)

#can kill table with, but please dont
#DROP TABLE dc_dc_tests;
#DROP TABLE board_traces;

#this whole routine is very touchy, it may cause issues for both db i/o and data collection if
#you touch this file, sorry it is poorly documented
def init_db():
    '''this creates the database'''
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            
            CREATE TABLE IF NOT EXISTS dc_dc_tests (
                id SERIAL PRIMARY KEY,
                
                board_id TEXT UNIQUE,
                timestamp TIMESTAMP,
            
                calibrated_voltage_warm TEXT,     
                voltage_dev_warm REAL,
                mc_ave_vol REAL,
                mc_ave_cur REAL,
                within_range1 TEXT,
                
                calibrated_voltage_cold TEXT,
                voltage_dev_cold REAL,
                mc_ave_vol_c REAL,
                mc_ave_cur_c REAL,
                within_range2 TEXT
                
            )
            """)
            conn.commit()

def insert_test(data):
    '''this adds one set of board test data'''

    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            INSERT INTO dc_dc_tests (
                board_id,
                timestamp,
                
                calibrated_voltage_warm,
                voltage_dev_warm,
                mc_ave_vol,    
                mc_ave_cur,
                within_range1
                
            ) VALUES (%s, %s, %s, %s, %s,%s,%s)
            """, (
                data["board_id"],
                datetime.now(),
                data["calibrated_voltage_warm"],
                data["voltage_dev_warm"],
                data["mc_ave_vol"],
                data["mc_ave_cur"],
                data["within_range1"],
            ))
            conn.commit()

def update_cold_test(data):
    '''updates cold test data'''

    with get_connection() as conn:
        with conn.cursor() as cursor:

            cursor.execute("""
            UPDATE dc_dc_tests
            SET
                calibrated_voltage_cold =%s,
                voltage_dev_cold =%s,
                mc_ave_vol_c =%s,
                mc_ave_cur_c =%s,
                within_range2 =%s
        
            WHERE board_id = %s
        
            """,
                           (
                               data["calibrated_voltage_cold"],
                               data["voltage_dev_warm"],
                               data["mc_ave_vol_c"],
                               data["mc_ave_cur_c"],
                               data["within_range2"],
                               data["board_id"],
                           ))

            conn.commit()

def init_trace_db():
    """DB for cold and warm start ups"""
#multiple power cycle dump slots only
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS board_traces (
    id SERIAL PRIMARY KEY,

    board_id TEXT UNIQUE,
    timestamp TIMESTAMP,

    multiple_power_cycle_voltage TEXT,
    multiple_power_cycle_current TEXT,
    multiple_power_cycle_voltage_c TEXT,
    multiple_power_cycle_current_c TEXT
)
            """)
            conn.commit()

def insert_warm_traces(board_id,data):
    '''inserts new traces'''
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                           INSERT INTO board_traces
                           (board_id,
                            timestamp,
                            multiple_power_cycle_voltage,
                            multiple_power_cycle_current
                            )
                           VALUES (%s, %s, %s, %s)
                           """,
                           (
                               #create data slot
                               board_id,
                               datetime.now(),
                               json.dumps(data["multiple_power_cycle_voltage"]),
                               json.dumps(data["multiple_power_cycle_current"]),

                           ))
            conn.commit()

def update_cold_traces(board_id,data):
    '''Puts in cold test data'''
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                           UPDATE board_traces
                           SET
                                multiple_power_cycle_voltage_c=%s,
                                multiple_power_cycle_current_c=%s

                           WHERE board_id = %s
                           """,
                           (
                               json.dumps(data["multiple_power_cycle_voltage_c"]),
                               json.dumps(data["multiple_power_cycle_current_c"]),

                               board_id,
                           ))
            conn.commit()

def rename_board_id(old_id, new_id):
    '''updates an id to a new arg if it does not exist already'''
    with get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT board_id
                FROM dc_dc_tests
                WHERE board_id = %s
            """, (new_id,))

            if cursor.fetchone():
                raise ValueError(f"Board ID {new_id} already exists.")

            cursor.execute("""
                UPDATE dc_dc_tests
                SET board_id = %s
                WHERE board_id = %s
            """, (new_id, old_id))

            tests_updated = cursor.rowcount

            cursor.execute("""
                UPDATE board_traces
                SET board_id = %s
                WHERE board_id = %s
            """, (new_id, old_id))

            traces_updated = cursor.rowcount

            conn.commit()

    print(
        f"Renamed {old_id} -> {new_id}\n"
        f"Test rows updated: {tests_updated}\n"
        f"Trace rows updated: {traces_updated}"
    )