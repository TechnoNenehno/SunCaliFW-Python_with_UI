import serial
import numpy as np
import time
import Photodiode_calibration_under_Xenon_sun.Calibration_1sample as cal

################################################################
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

    #port = 'COM4'        
    #baud_rate = 115200   
    #timeout = 0          

    output_file_raw = "Logs/Calibration_10s_RAW.txt"

    uncalibrated_array = np.zeros((12,12))

    with open(output_file_raw, "w") as file:
        file.write("RAW sample used for calculating the weights:\n\r")


    #10 sample calibration !!!
    try:
        for i in range(10):
            ser_merilno.write(b'pulse\n\r')  
            print(i,end=' ')
            data_grid= cal.read_from_port(ser_merilno)
            time.sleep(0.05)

            with open(output_file_raw, "a") as file:
                file.write(np.array2string(data_grid) + '\n')
                file.write("\n")
    

            uncalibrated_array += data_grid

    finally: 
    
        utezi = cal.value_calibration2D(uncalibrated_array) 

        kalibrarano = data_grid*utezi
    
        with open(output_file_raw, "a") as file:
            file.write("\n\rArray to be calibrated:\n\r")
            file.write(np.array2string(uncalibrated_array) + '\n')
            file.write("\n\rCalculated weights:\n\r")
            file.write(np.array2string(utezi) + '\n')
            file.write("\n\rCalculated calibrated array:\n\r")
            file.write(np.array2string(kalibrarano))



        np.savetxt('Weights/utezi_10s.txt', utezi)
        print("Calibration Completed!")
        ser_merilno.close()
        print("Serial port closed.")

        ser_merilno = None
    return (f"Calibration 10 samples complete.")

if __name__ == "__main__":
    main()

