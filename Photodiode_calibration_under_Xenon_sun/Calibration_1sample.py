import serial
import numpy as np
import time


def read_from_port(ser):

    temp_data_grid =np.zeros((12,12))
    print(f"Receiving data on {ser.port}...")
    try:
        while True:
            if ser.in_waiting > 0:  # Check if there's data to read
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

def value_calibration2D(array):
    avg_val = np.mean(array)
    factors = array/avg_val
    factors_arr = np.full((12,12), 1/factors)

    return factors_arr


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

ser_merilno = None

def main():
    #ports were setup individually in LabVIEW
    # Photodiode array COM port
    #port1 = 'COM4'        
    #baud_rate1 = 115200   
    #timeout1 = 0   

    #1 sample calibration !!!
    try:
        ser_merilno.write(b'pulse\n\r')  
        uncalibrated_array = read_from_port(ser_merilno)
        time.sleep(0.05)

        
    finally: 
        
        utezi = value_calibration2D(uncalibrated_array)
        
        kalibrarano = uncalibrated_array*utezi
        
        with open("Logs/Calibration_1s_RAW.txt", "w") as file:
            file.write("RAW sample used for calculating the weights: \n \r")
            file.write(np.array2string(uncalibrated_array) + '\n')
            file.write("\n\rCalculated weights: \n \r")
            file.write(np.array2string(utezi) + '\n')
            file.write("\n\rCalculated calibrated array: \n \r")
            file.write(np.array2string(kalibrarano))
            file.flush()


        np.savetxt('Weights/utezi_1s.txt', utezi)

        print("Calibration Completed!")
        ser_merilno.close()
        print("Serial port closed.")
        ser_merilno = None
    return (f"Calibration 1 sample complete.")

if __name__ == "__main__":
    main()


