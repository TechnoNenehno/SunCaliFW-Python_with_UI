import serial
import numpy as np
import time
import Calibration_1sample as cal


def main():

    port = 'COM4'        
    baud_rate = 115200   
    timeout = 0          
    ser = serial.Serial(port, baud_rate, timeout=timeout)

    output_file_raw = "Logs/Calibration_10s_RAW.txt"

    uncalibrated_array = np.zeros((12,12))

    with open(output_file_raw, "w") as file:
        file.write("RAW sample used for calculating the weights:\n\r")


    #10 sample calibration !!!
    try:
        for i in range(10):
            ser.write(b'pulse\n\r')  
            print(i,end=' ')
            data_grid= cal.read_from_port(ser)
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
        ser.close()
        print("Serial port closed.")


if __name__ == "__main__":
    main()

