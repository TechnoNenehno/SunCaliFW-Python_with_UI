
import serial
import numpy as np
import time
import matplotlib.pyplot as plt
import Calibration_3Dprinter as cal

def process_column_test(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, uncalibrated_array, output_file_raw):
   
    rows = range(11, -1, -1) if reverse else range(12)
    for row in rows:
        cal.send_gcode_line(Gcode_input_path,ser_3D,line_to_send)
        time.sleep(1.2) 
        
        if first_half:
            line_to_send += 1
        else:
            line_to_send -= 1

        
        ser_merilno.write(b'pulse\n\r')  
        time.sleep(0.1)
        data_grid = cal.read_from_port(ser_merilno)
      
        uncalibrated_array[row,col] = data_grid[row,col]

        with open(output_file_raw, "a") as file:
            file.write(f"ROW: {row} COL: {col}\n")
            file.write(np.array2string(data_grid) + '\n')
            file.write("\n")

    return line_to_send


def calculate_statistics(array):
    all_stats = np.zeros(4)

    all_stats[0] = np.min(array) #MIN
    all_stats[1] = np.max(array) #MAX
    all_stats[2] = np.mean(array) #MEAN
    all_stats[3] = all_stats[1] - all_stats[0] #delta

    return all_stats


def main():
    
    # Photodiode array COM port
    port1 = 'COM4'        
    baud_rate1 = 115200   
    timeout1 = 0          
    ser_merilno = serial.Serial(port1, baud_rate1, timeout=timeout1)

    # 3D printer COM port
    port2 = 'COM5'        
    baud_rate2 = 250000 
    timeout2 = 1        
    ser_3D = serial.Serial(port2, baud_rate2, timeout=timeout2)

    
    uncalibrated_array = np.zeros((12,12))

    Gcode_input_path = "Data/GCODE_output.gcode" #Gcode file 
    output_file_raw = "Logs/Calibration_za_3Dprinter_TEST_RAW.txt" #Log file
    loaded_array = np.loadtxt('Data/RAW_coordinates.csv')  #Pick and Place photodiode coordinates
    utezi = np.loadtxt('Weights/utezi_3D.txt') #Calibration weights to be tested
    

    #Offset between 3D printer C.S. and Photodiode array C.S
    x_offset = 0 #mm
    y_offset = -25 #mm


    corrected_offset = cal.correct_coordinate_sys(x_offset,y_offset,loaded_array)

    cal.array_to_gcode(corrected_offset, Gcode_input_path)

    with open(output_file_raw, "w") as file:
            file.write("RAW sample used for calculating the weights:\n\r")


    try:
    
        for i in range(3):
            cal.send_gcode_line(Gcode_input_path,ser_3D,i)
            time.sleep(1)

        cal.send_gcode_line(Gcode_input_path,ser_3D,3)
        time.sleep(15)
        cal.send_gcode_line(Gcode_input_path,ser_3D,4)
        print("Insert board.")
        print("Press Enter to continue...")
        input()  
        print("Continuing execution...")
        cal.send_gcode_line(Gcode_input_path,ser_3D,5)
        time.sleep(3)

        line_to_send = 5 

        for col in range(6):

            first_half = True
            reverse = (col % 2 != 0)
            line_to_send = process_column_test(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, uncalibrated_array, output_file_raw)


        print("Half of the calibration complete! Please turn the circuit around.")
        print("Press Enter to continue...")
        input()  
        print("Continuing execution...")
      
        line_to_send -=1

        for col in range(6,12):
            first_half = False
            reverse = (col % 2 == 0)
            line_to_send = process_column_test(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, uncalibrated_array, output_file_raw)



    finally:
    
        kalibrirano = uncalibrated_array*utezi
        kalibrirano = kalibrirano.round()

        statistics = calculate_statistics(kalibrirano)

        with open(output_file_raw, "a") as file:
            file.write("\n\rMeasured Array:\n\r")
            file.write(np.array2string(uncalibrated_array) + '\n')
            file.write("\n\rCalculated calibrated array:\n\r")
            file.write(np.array2string(kalibrirano) + '\n')
            file.write("\nMIN: " + np.array2string(statistics[0]) + '\n')
            file.write("MAX: " + np.array2string(statistics[1]) + '\n')
            file.write("DELTA: " + np.array2string(statistics[3]) + '\n')
            file.write("MEAN: " + np.array2string(statistics[2]) + '\n')


        ser_merilno.close()
        ser_3D.close()
        print("Serial ports closed.")


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



if __name__ == "__main__":
    main()
