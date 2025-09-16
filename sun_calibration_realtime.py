import numpy as np
import time
import serial
from scipy.optimize import lsq_linear

import Led_array_control as led
import Calibration_3Dprinter as cal


def get_initial_weights10(ser_merilno, ser_led_array, photodiode_weights):

    initial_weights = np.zeros((144,40))
    data_grid = np.zeros((12,12))

    try:
        for module in range(0,40):
            
            whole_dg = np.zeros((12,12))

            powers = np.zeros(40, dtype=int)
            powers[module] = 100
            print(module)
        
            print("Sending led command")
            led.set_all_diff_P(ser_led_array, powers)
            

            for _ in range(10):
                time.sleep(0.1) 

                ser_merilno.write(b'pulse\n\r') 
                time.sleep(0.1) 
                data_grid = cal.read_from_port(ser_merilno)
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
            led.set_all_diff_P(ser_led_array, powers)
            

           
            ser_merilno.write(b'pulse\n\r') 
            time.sleep(0.1) 
            data_grid = cal.read_from_port(ser_merilno)
            data_grid = data_grid * photodiode_weights
            
            array_144x1 = data_grid.reshape(144, 1)
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
                powers[module] = module_powers[module]
                print(module)
            
                print("Sending led command")
                led.set_all_diff_P(ser_led_array, powers)
                

            
                ser_merilno.write(b'pulse\n\r') 
                time.sleep(0.1) 
                data_grid = cal.read_from_port(ser_merilno)
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
        led.set_all_diff_P(ser_led_array, module_powers)

        ser_merilno.write(b'pulse\n\r') 
        time.sleep(0.1) 
        data_grid = cal.read_from_port(ser_merilno)
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
        file.write(np.array2string(measured_values) + '\n')
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
    try:
        ser = serial.Serial(port, baud_rate, timeout=timeout)
        return ser
    except serial.SerialException as e:
        return None

#Helper function to open serial ports
def Photodiode_serial(port, baud_rate, timeout):
    ser_merilno = open_serial_port(port, baud_rate, timeout)
    if ser_merilno is None:
        return (f"Failed to open serial port {port}.")
    else:
        return (f"Serial port {port} opened successfully.")

def Led_array_serial(port, baud_rate, timeout):
    ser_led_array = open_serial_port(port, baud_rate, timeout)
    if ser_led_array is None:
        return (f"Failed to open serial port {port}.")
    else:
        return (f"Serial port {port} opened successfully.")

#Global variables
ser_merilno = None
ser_led_array = None

def main():

    # Photodiode array COM port
    port1 = 'COM56'        
    baud_rate1 = 115200   
    timeout1 = 0          
    ser_merilno = serial.Serial(port1, baud_rate1, timeout=timeout1)

    #LED array COM port
    port2 = 'COM33'        
    baud_rate2 = 115200   
    timeout2 = 0     
    ser_led_array = serial.Serial(port2, baud_rate2, timeout=timeout2)

    output_file_raw ="Logs/Realtime_sun_calibration_RAW.txt" #Log file
    photodiode_weights = np.loadtxt("Weights/utezi_3D.txt") #Calibration weights for Photodiode array

    vrednost_sonca = np.loadtxt("Weights/vrednost_1_sonce.txt")

    zeljena_vrednost = 1 # nastavi vrednost sončne obsevanosti, 1 pomeni 1000 W/m2

    obsevanost = zeljena_vrednost * vrednost_sonca
    obsevanost = obsevanost.round()


    target_homogeneity= np.full(144, obsevanost)  # Target constant homogeneity value, set value accordingly

    #zacetek kalibracije
    try: 
        
        weights = get_initial_weights1(ser_merilno, ser_led_array, photodiode_weights)
        module_powers = calculate_module_powers(weights, target_homogeneity)

        with open(output_file_raw, "w") as file:
            file.write("\n\rInitial calculated LED module powers:\n\r")
            file.write(np.array2string(module_powers) + '\n')
        
        measured_values = measure_intensity_specific_power(ser_merilno, ser_led_array, photodiode_weights, module_powers)
        statistics = calculate_statistics(measured_values)
        write_to_log(output_file_raw, measured_values, statistics)


        for _ in range(2): #length can be shortened, number of iterations

            weights = get_iterative_weights(ser_merilno, ser_led_array, photodiode_weights, module_powers, weights)
            module_powers = calculate_module_powers(weights, target_homogeneity)

            with open(output_file_raw, "a") as file:
                file.write("Calculated module Powers:\n\r")
                file.write(np.array2string(module_powers) + '\n')

            
            measured_values = measure_intensity_specific_power(ser_merilno, ser_led_array, photodiode_weights, module_powers)
            statistics = calculate_statistics(measured_values)
            write_to_log(output_file_raw,measured_values,statistics)
           

        np.savetxt('Weights/umetno_sonce_moci.txt', module_powers) # LED array powers
        np.savetxt('Weights/povezovalne_utezi.txt', weights) # zadnje povezovale utezi

    
    finally:
        
        #led.set_all_same_P(ser_led_array,0)
        led.set_all_diff_P(ser_led_array,module_powers)

        ser_merilno.close()
        ser_led_array.close()
        print("Serial ports closed.")
        ser_merilno = None
        ser_led_array = None
    
    return (f"Sun calibration complete.")

if __name__ == "__main__":
    main()
