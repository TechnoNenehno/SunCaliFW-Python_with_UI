import numpy as np
import time
import os
from datetime import datetime
import serial
from scipy.optimize import lsq_linear

#Global variables
ser_merilno = None
ser_led_array = None

#LED array control functions
def set_all_diff_P(ser, all_powers):
    #all_powers: power factors of LED modules in order 1-40, length 40!
    try: 
        if len(all_powers) != 40:
            raise ValueError(f"Wrong length: Expected 40, but got {len(all_powers)}.")
        
        if not np.all((all_powers >= 0) & (all_powers <= 100)):

            invalid_values = all_powers[(all_powers < 0) | (all_powers > 100)]
            raise ValueError(f"Power array out of bounds: Expected 0-100, but got {invalid_values}")

        output = ','.join(str(value) for value in all_powers)
        command = f"-h[{output}]\n\r"
        ser.write(command.encode())

        while ser.out_waiting > 0:  # Check if the output buffer is empty
            time.sleep(0.01) 
        time.sleep(2)
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

#Read data from photodiode array serial port
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


def get_initial_weights10(ser_merilno, ser_led_array, photodiode_weights):

    initial_weights = np.zeros((144,40))
    data_grid = np.zeros((12,12))

    try:
        for module in range(0,40):
            
            whole_dg = np.zeros((12,12))

            powers = np.zeros(40, dtype=int)
            powers[module] = 100
            #print(module)
            #print("Sending led command")
            set_all_diff_P(ser_led_array, powers)
            
            for _ in range(10):
                time.sleep(0.1) 

                ser_merilno.write(b'pulse\n\r') 
                time.sleep(0.1) 
                data_grid = read_from_port(ser_merilno)
                data_grid = data_grid * photodiode_weights
                whole_dg = whole_dg + data_grid

            whole_dg = whole_dg / 10


            array_144x1 = whole_dg.reshape(144, 1)
            array_144x1 = array_144x1 / 100 

            initial_weights[:, module] = array_144x1[:, 0]

        return initial_weights

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}") 


def get_initial_weights1(ser_merilno, ser_led_array, photodiode_weights):

    initial_weights = np.zeros((144,40))
    data_grid = np.zeros((12,12))
    #nastavljanje modulov in merjenje
    try:
        for module in range(0,40):
            
            powers = np.zeros(40, dtype=int)
            powers[module] = 100
            #print(module)
            #print("Sending led command")
            set_all_diff_P(ser_led_array, powers)
            

           
            ser_merilno.write(b'pulse\n\r') 
            time.sleep(0.1)
            data_grid = read_from_port(ser_merilno)
            data_grid = data_grid * photodiode_weights
            
            array_144x1 = data_grid.reshape(144, 1)
            #zakaj je tu 100? spodi pa module_powers[module]
            array_144x1 = array_144x1 / 100 

            initial_weights[:, module] = array_144x1[:, 0]

        return initial_weights

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}") 


def get_iterative_weights(ser_merilno, ser_led_array, photodiode_weights, module_powers, initial_weights):

    weights = np.zeros((144,40))
    data_grid = np.zeros((12,12))

    try:
        for module in range(0,40):
            
            if module_powers[module] == 0:
                weights[:, module] = initial_weights[:, module]
            else:
                powers = np.zeros(40, dtype=int)
                #kaj je ta vrednost?
                powers[module] = module_powers[module]
                #print(module)
            
                #print("Sending led command")
                set_all_diff_P(ser_led_array, powers)
            
                ser_merilno.write(b'pulse\n\r') 
                time.sleep(0.1) 
                data_grid = read_from_port(ser_merilno)
                data_grid = data_grid * photodiode_weights
                
                array_144x1 = data_grid.reshape(144, 1)
                array_144x1 = array_144x1 / module_powers[module]

                weights[:, module] = array_144x1[:, 0]

        return weights

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}") 


def measure_intensity_specific_power(ser_merilno, ser_led_array, photodiode_weights, module_powers):
   
    data_grid = np.zeros((12,12))

    try:
        set_all_diff_P(ser_led_array, module_powers)

        ser_merilno.write(b'pulse\n\r') 
        time.sleep(0.1) 
        data_grid = read_from_port(ser_merilno)
        data_grid = data_grid * photodiode_weights
        data_grid = np.round(data_grid)

        return data_grid

    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}") 


def calculate_statistics(array):
    all_stats = np.zeros(4)

    all_stats[0] = np.min(array) #MIN
    all_stats[1] = np.max(array) #MAX
    all_stats[2] = np.mean(array) #MEAN
    all_stats[3] = all_stats[1] - all_stats[0] #delta

    return all_stats


def write_to_log(output_file_raw, measured_values, statistics):

    with open(output_file_raw, "a") as file:
        file.write("\n\rPhotodiode array values:\n\r")
        file.write(np.array2string(measured_values, max_line_width=5000) + '\n')
        file.write("\nMIN: " + np.array2string(statistics[0]) + '\n')
        file.write("MAX: " + np.array2string(statistics[1]) + '\n')
        file.write("DELTA: " + np.array2string(statistics[3]) + '\n')
        file.write("MEAN: " + np.array2string(statistics[2]) + '\n')


def calculate_module_powers(weights, target_homogeneity):
   
    module_powers = np.zeros(40)

    result = lsq_linear(weights, target_homogeneity, bounds=(0, 100))
    module_powers = result.x
    module_powers = module_powers.round()

    return module_powers

####################################################################
def open_serial_port(port, baud_rate, timeout):
    ser = serial.Serial(port, baud_rate, timeout=timeout)
    if ser.is_open:
        return ser
    else:
        pass

#Helper function to open serial ports
def Photodiode_serial(port, baud_rate, timeout):
    ser_merilno = open_serial_port(port, baud_rate, timeout)
    return ser_merilno

def Led_array_serial(port, baud_rate, timeout):
    ser_led_array = open_serial_port(port, baud_rate, timeout)
    return ser_led_array


def calibrate_Sun_in_realtime(ser_merilno, ser_led_array):
    ###############################################################################
    #Set the path of the raw file where it check if it already exists
    output_file_raw = os.path.join(os.path.dirname(__file__), "Logs", "Realtime_sun_calibration_RAW.txt") #Calibration file
    if(output_file_raw == None):
        return("Calibration file path is not set. Please set the Calibration file path.")
    # Check if file exists
    if os.path.exists(output_file_raw):
        # Append date(YYYYMMDD)
        base, ext = os.path.splitext(output_file_raw)
        date_str = datetime.now().strftime("%Y%m%d")
        output_file_raw = f"{base}_{date_str}{ext}"
    ###############################################################################        
    #Set the path of Calibration weights for Photodiode array
    # Find all files matching "utezi_3D*.txt" in the Weights directory
    data_dir = os.path.join(os.path.dirname(__file__), "Weights")
    raw_files = [f for f in os.listdir(data_dir) if f.startswith("utezi_3D") and f.endswith(".txt")]

    if not raw_files:
        raise FileNotFoundError("No raw files found in Weights directory.")

    # Get the latest file by creation time
    weights_files_full = [os.path.join(data_dir, f) for f in raw_files]
    output_file_weights = max(weights_files_full, key=os.path.getctime)
    if(output_file_weights == None):
        return("Weights file path is not set. Please set the Weights file path.")
    photodiode_weights = np.loadtxt(output_file_weights) #Calibration weights for Photodiode array
    ###############################################################################    
    #Set the path of one sun value
    # Find all files matching "utezi_3D*.txt" in the Weights directory
    data_dir = os.path.join(os.path.dirname(__file__), "Weights")
    sun_value_files = [f for f in os.listdir(data_dir) if f.startswith("vrednost_1_sonce") and f.endswith(".txt")]

    if not sun_value_files:
        raise FileNotFoundError("No sun value files found in Weights directory.")

    # Get the latest file by creation time
    sun_files_full = [os.path.join(data_dir, f) for f in sun_value_files]
    output_file_sun = max(sun_files_full, key=os.path.getctime)
    if(output_file_sun == None):
        return("Sun value file path is not set. Please set the Sun value file path.")
    vrednost_sonca = np.loadtxt(output_file_sun) #Calibration weights for Photodiode array
    ###############################################################################
    #nastavi vrednost sončne obsevanosti, 1 pomeni 1000 W/m2 torej eno sonce
    zeljena_vrednost = 1 
    obsevanost = zeljena_vrednost * vrednost_sonca
    obsevanost = obsevanost.round()
    #preveri z tjazem zka je tu 144?
    target_homogeneity= np.full(144, obsevanost)  # Target constant homogeneity value, set value accordingly

    #ZACETEK PRVE KALIBRACIJE    
    weights = get_initial_weights1(ser_merilno, ser_led_array, photodiode_weights)
    module_powers = calculate_module_powers(weights, target_homogeneity)

    with open(output_file_raw, "w") as file:
        file.write("Initial calculated LED module powers:\n\r")
        file.write(np.array2string(module_powers) + '\n')
    
    measured_values = measure_intensity_specific_power(ser_merilno, ser_led_array, photodiode_weights, module_powers)
    statistics = calculate_statistics(measured_values)
    write_to_log(output_file_raw, measured_values, statistics)
    #KONEC PRVE KALIBRACIJE

    #ZACETEK ITERATIVNE KALIBRACIJE
    for _ in range(2): #length can be shortened, number of iterations

        weights = get_iterative_weights(ser_merilno, ser_led_array, photodiode_weights, module_powers, weights)
        module_powers = calculate_module_powers(weights, target_homogeneity)

        with open(output_file_raw, "a") as file:
            file.write("Calculated module Powers:\n\r")
            file.write(np.array2string(module_powers) + '\n')
        
        measured_values = measure_intensity_specific_power(ser_merilno, ser_led_array, photodiode_weights, module_powers)
        statistics = calculate_statistics(measured_values)
        write_to_log(output_file_raw, measured_values, statistics)
    #KONEC ITERATIVNE KALIBRACIJE

    #Shrani utezi in moci
    # Prepare file paths
    utezi_dir = os.path.join(os.path.dirname(__file__), "Weights")
    if not os.path.exists(utezi_dir):
        os.makedirs(utezi_dir)

    utezi_path = os.path.join(utezi_dir, "povezovalne_utezi.txt")
    sonce_moci_path = os.path.join(utezi_dir, "umetno_sonce_moci.txt")

    # If file exists, add date to filename
    if os.path.exists(utezi_path):
        date_str = datetime.now().strftime("%Y%m%d")
        utezi_path = os.path.join(utezi_dir, f"povezovalne_utezi_{date_str}.txt")
    if os.path.exists(sonce_moci_path):
        date_str = datetime.now().strftime("%Y%m%d")
        sonce_moci_path = os.path.join(utezi_dir, f"umetno_sonce_moci_{date_str}.txt")
    
    np.savetxt(utezi_path, weights) #zadnje povezovale utezi
    np.savetxt(sonce_moci_path, module_powers) #LED array powers

    #led.set_all_same_P(ser_led_array,0)
    set_all_diff_P(ser_led_array, module_powers)

    ser_merilno.close()
    ser_led_array.close()


    ser_merilno = None
    ser_led_array = None
    
    return (f"Sun calibration complete. Serial ports closed. Check weights in Weights directory and realtime calculated values in Logs directory.")


def main():
    # Photodiode array COM port
    #port1 = 'COM56'        
    #baud_rate1 = 115200   
    #timeout1 = 0          
    #ser_merilno = serial.Serial(port1, baud_rate1, timeout=timeout1)
    #LED array COM port
    #port2 = 'COM33'        
    #baud_rate2 = 115200   
    #timeout2 = 0     
    #ser_led_array = serial.Serial(port2, baud_rate2, timeout=timeout2)
    #calibrate_Sun_in_realtime(ser_merilno, ser_led_array)
    pass

#if __name__ == "__main__":
#    main()