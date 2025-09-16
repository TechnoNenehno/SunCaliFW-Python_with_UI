
import serial
import numpy as np
import time
import matplotlib.pyplot as plt
import os
from datetime import datetime

#Global variables
ser_merilno = None
ser_3D = None
#Global variable below is defined and initialized in calibrate_3D_printer(ser_3D), since we want to reset it on each call 
#uncalibrated_array = np.zeros((12,12))

def read_from_port(ser):

    temp_data_grid =np.zeros((12,12))
    print(f"Receiving data on {ser.port}...")
    try:
        while True:
            if ser.in_waiting > 0:  
                data = ser.readline().decode('utf-8').strip()

                col_values_dict = {}

                for i in range(12): 
                    col_name = f"COL{i}:"  
                    if data.startswith(col_name):
                        col_values_dict[f"COL{i}"] = list(map(int, data.split(":")[1].split(',')))

                        for rowin in range(12):
                            temp_data_grid[rowin, i] = col_values_dict[f"COL{i}"][rowin]

                    
                        if col_name == "COL11:":
                            return temp_data_grid

    except KeyboardInterrupt:
        print("Stopped reading by user.")


def send_gcode_line(file_path, ser, line):

    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            line_to_send = lines[line]

            line_to_send = line_to_send.strip()
            
            # Send the G-code line
            ser.write((line_to_send + '\n').encode('utf-8'))
            print(f"Sent: {line_to_send}")
                

            while ser.in_waiting > 0:
                response = ser.readline().decode()
                if response:
                    print(f"Response: {response}")

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except FileNotFoundError:
        print(f"File not found: {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


def array_to_gcode(array,output_gcode):
    
    try:
        
        with open(output_gcode, mode='w') as gcode_file:
            # Write G-code header
            gcode_file.write("G21 ; Set units to mm\n")
            gcode_file.write("G90 ; Use absolute positioning\n")
            gcode_file.write("M107 ; Turn off fan\n")
            gcode_file.write("G28 X0 Y0 Z0 ;move X/Y/Z to min endstops\n")
            #hardcoded Z height for 3D printer, where u get 1000 W/m2 on photodiode array which is one Sun
            gcode_file.write("G1 Z48.7 F9000 ;move the platform down 48.7 mm\n")
            
            
            for row in array:
                x, y = row
                x = float(x)
                y = float(y)
                
                # Write G-code command 
                gcode_line = f"G1 X{x:.1f} Y{y:.1f} \n"
                gcode_file.write(gcode_line)
            

        print(f"G-code file '{output_gcode}' generated successfully.")
    except Exception as e:
        print(f"An error occurred: {e}")


def process_column_validation(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, output_file_raw):
   
    rows = range(11, -1, -1) if reverse else range(12)
    for row in rows:
        send_gcode_line(Gcode_input_path,ser_3D,line_to_send)
        time.sleep(1.2) 
        
        if first_half:
            line_to_send += 1
        else:
            line_to_send -= 1

        
        ser_merilno.write(b'pulse\n\r')  
        time.sleep(0.1)
        data_grid = read_from_port(ser_merilno)
        # Update the global uncalibrated_array with the new data
        global uncalibrated_array
        uncalibrated_array[row,col] = data_grid[row,col]
        data_grid_int = data_grid.round().astype(int)

        with open(output_file_raw, "a") as file:
            file.write(f"ROW: {row} COL: {col}\n")
            file.write(np.array2string(data_grid_int, max_line_width=5000) + '\n')
            file.write("\n")

    return line_to_send


def correct_coordinate_sys(x_off,y_off,array):
    array[:, 0] = array[:, 0] + x_off
    array[:, 1] = array[:, 1]+  y_off

    return array


def calculate_statistics(array):
    all_stats = np.zeros(4)
    all_stats[0] = np.min(array) #MIN
    all_stats[1] = np.max(array) #MAX
    all_stats[2] = np.mean(array) #MEAN
    all_stats[3] = all_stats[1] - all_stats[0] #delta
    return all_stats


####################################################################
def open_serial_port(port, baud_rate, timeout):
    ser = serial.Serial(port, baud_rate, timeout=timeout)
    if ser.is_open:
        return ser
    else:
        pass

#Helper function to open serial ports
def Photodiode_serial(port, baud_rate, timeout1):
    ser_merilno = open_serial_port(port, baud_rate, timeout=timeout1)
    return ser_merilno

def Printer3D_serial(port, baud_rate, timeout1):
    ser_3D = open_serial_port(port, baud_rate, timeout=timeout1)
    return ser_3D

def validate_3D_printer(ser_3D):
    # Initialize global variable since it will be modified in other functions
    global uncalibrated_array
    uncalibrated_array = np.zeros((12,12))
    ###############################################################################
    #Set the path of the Gcode file
    Gcode_input_path = os.path.join(os.path.dirname(__file__), "Data", "GCODE_output.gcode") #Gcode file 
    if(Gcode_input_path == None):
        return("Gcode file path is not set. Please set the Gcode file path.")
    # Check if file exists
    if os.path.exists(Gcode_input_path):
        # Append date(YYYYMMDD)
        base, ext = os.path.splitext(Gcode_input_path)
        date_str = datetime.now().strftime("%Y%m%d")
        Gcode_input_path = f"{base}_{date_str}{ext}"
    ###############################################################################
    #Set the path of the array pick and place file
    array_path = os.path.join(os.path.dirname(__file__), "Data", "RAW_coordinates.csv") #Pick and Place photodiode coordinates
    loaded_array = np.loadtxt(array_path) #Pick and Place photodiode coordinates
    if(loaded_array.size == 0):
        return("Coordinates file is empty. Please check the coordinates file.")
    ###############################################################################
    #Offset between 3D printer C.S. and Photodiode array C.S
    x_offset = 0 #mm
    y_offset = -25 #mm
    #Correct the coordinate system
    corrected_offset = correct_coordinate_sys(x_offset,y_offset,loaded_array)
    #Koda za 3D printer kako se naj premika, vedno ista kr je odvisna od pick and place koordinat
    array_to_gcode(corrected_offset, Gcode_input_path)
    #Send first few Gcode lines that include settings and to move to (0,0)
    for i in range(3):
        send_gcode_line(Gcode_input_path,ser_3D,i)
        time.sleep(1)
    #Send Gcode line to move to (0,0)
    send_gcode_line(Gcode_input_path,ser_3D,3)
    time.sleep(15)
    send_gcode_line(Gcode_input_path,ser_3D,4)
    return("3D printer validated. Insert board and press *Start validating* \n\r")

def start_photodiode_validation(ser_merilno, ser_3D):
    ###############################################################################
    #Set the path of the Gcode file where it checks if it already exists
    # Find all files matching "GCODE_output*.gcode" in the Data directory
    data_dir = os.path.join(os.path.dirname(__file__), "Data")
    gcode_files = [f for f in os.listdir(data_dir) if f.startswith("GCODE_output") and f.endswith(".gcode")]

    if not gcode_files:
        raise FileNotFoundError("No GCODE_output files found in Data directory.")

    # Get the latest file by creation time
    gcode_files_full = [os.path.join(data_dir, f) for f in gcode_files]
    Gcode_input_path = max(gcode_files_full, key=os.path.getctime)
    if(Gcode_input_path == None):
        return("Gcode file path is not set. Please set the Gcode file path.")
    ###############################################################################
    #Set the path of the raw file where it check if it already exists
    output_file_raw = os.path.join(os.path.dirname(__file__), "Logs", "Validation_za_3Dprinter_RAW.txt") #Validation file
    if(output_file_raw == None):
        return("Validation file path is not set. Please set the Validation file path.")
    # Check if file exists
    if os.path.exists(output_file_raw):
        # Append date(YYYYMMDD)
        base, ext = os.path.splitext(output_file_raw)
        date_str = datetime.now().strftime("%Y%m%d")
        output_file_raw = f"{base}_{date_str}{ext}"
    ###############################################################################
    send_gcode_line(Gcode_input_path,ser_3D,5)
    time.sleep(3)

    line_to_send = 5 #start of Photodiode coordinates
    with open(output_file_raw, "a") as file:
        file.write("RAW sample used for calculating the weights:\n\r")
    # Write the uncalibrated array (done in process column)
    for col in range(6):
        first_half = True
        reverse = (col % 2 != 0)
        line_to_send = process_column_validation(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, output_file_raw)
    return("Half of the validation complete! Pleaser turn the circuit around and press *Continue validation* \n\r")

def continue_photodiode_validation(ser_merilno, ser_3D):
    #############################################################################
    #Set the path of the raw file
    # Find all files matching "Validation_za_3Dprinter_RAW*.txt" in the Logs directory
    data_dir = os.path.join(os.path.dirname(__file__), "Logs")
    raw_files = [f for f in os.listdir(data_dir) if f.startswith("Validation_za_3Dprinter_RAW") and f.endswith(".txt")]

    if not raw_files:
        raise FileNotFoundError("No raw files found in Logs directory.")

    # Get the latest file by creation time
    raw_files_full = [os.path.join(data_dir, f) for f in raw_files]
    output_file_raw = max(raw_files_full, key=os.path.getctime)
    if(output_file_raw == None):
        return("Raw file path is not set. Please set the Raw file path.")
    ###############################################################################
    #Set the path of the Gcode file
    # Find all files matching "GCODE_output*.gcode" in the Data directory
    data_dir = os.path.join(os.path.dirname(__file__), "Data")
    gcode_files = [f for f in os.listdir(data_dir) if f.startswith("GCODE_output") and f.endswith(".gcode")]

    if not gcode_files:
        raise FileNotFoundError("No GCODE_output files found in Data directory.")

    # Get the latest file by creation time
    gcode_files_full = [os.path.join(data_dir, f) for f in gcode_files]
    Gcode_input_path = max(gcode_files_full, key=os.path.getctime)
    if(Gcode_input_path == None):
        return("Gcode file path is not set. Please set the Gcode file path.")
    ###############################################################################
    #Set the path of the utezi file
    utezi_path = os.path.join(os.path.dirname(__file__), "Weights", "utezi_3D.txt") #utezi generirane pri kalibraciji
    utezi = np.loadtxt(utezi_path) #Pick and Place photodiode coordinates
    if(utezi.size == 0):
        return("Weights file is empty. Please check the utezi_3D.txt file.")
    ###############################################################################
    #line_to_send -=1
    line_to_send = 76

    for col in range(6,12):
        first_half = False
        reverse = (col % 2 == 0)
        line_to_send = process_column_validation(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, output_file_raw)
###ok tuki naprej
    #not modified only used below
    kalibrirano = uncalibrated_array*utezi
    kalibrirano = kalibrirano.round().astype(int)

    statistics = calculate_statistics(kalibrirano)
    
    with open(output_file_raw, "a") as file:
            file.write("\n\rMeasured Array:\n\r")
            file.write(np.array2string(uncalibrated_array,max_line_width=5000) + '\n')
            file.write("\n\rCalculated calibrated array:\n\r")
            file.write(np.array2string(kalibrirano,max_line_width=5000) + '\n')
            file.write("\nMIN: " + np.array2string(statistics[0],max_line_width=5000) + '\n')
            file.write("MAX: " + np.array2string(statistics[1],max_line_width=5000) + '\n')
            file.write("DELTA: " + np.array2string(statistics[3],max_line_width=5000) + '\n')
            file.write("MEAN: " + np.array2string(statistics[2],max_line_width=5000) + '\n')
    ser_merilno.close()
    ser_3D.close()

    ser_merilno = None
    ser_3D = None
    
    plt.figure(figsize=(8, 5))
    plt.imshow(kalibrirano, cmap="viridis", aspect="auto")

    for i in range(kalibrirano.shape[0]):  
        for j in range(kalibrirano.shape[1]): 
            plt.text(j, i, kalibrirano[i, j], ha="center", va="center", color="white")

    plt.colorbar(label="Value")
    plt.title("Heatmap of Photodiode Array")
    plt.xlabel("Columns")
    plt.ylabel("Rows")
    plt.xticks(ticks=np.arange(12), labels=np.arange(12))
    plt.yticks(ticks=np.arange(12), labels=np.arange(12))
    plt.show()
    return (f"Validation of photodiodes complete. Serial ports closed.")

def main():
    # Photodiode array COM port
    #port1 = 'COM4'        
    #baud_rate1 = 115200   
    #timeout1 = 0          
    #ser_merilno = serial.Serial(port1, baud_rate1, timeout=timeout1)

    # 3D printer COM port
    #port2 = 'COM5'        
    #baud_rate2 = 250000 
    #timeout2 = 1        
    #ser_3D = serial.Serial(port2, baud_rate2, timeout=timeout2)
    pass
