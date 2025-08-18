
import serial
import numpy as np
#import time

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


def value_calibration2D(array):
    avg_val = np.mean(array)
    factors = array/avg_val
    factors_arr = np.full((12,12), 1/factors)

    return factors_arr


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
            gcode_file.write("G1 Z32.7 F9000 ;move the platform down 32.7 mm\n")
            
            
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


def process_column(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, uncalibrated_array, output_file_raw):
   
    rows = range(11, -1, -1) if reverse else range(12)
    for row in rows:
        send_gcode_line(Gcode_input_path,ser_3D,line_to_send)
        time.sleep(1.2) #delay for the 3D printer to move
        
        if first_half:
            line_to_send += 1
        else:
            line_to_send -= 1

        for _ in range(10):
            time.sleep(0.1)    
            ser_merilno.write(b'pulse\n\r')  
            time.sleep(0.1)
            data_grid = read_from_port(ser_merilno)
      
            uncalibrated_array[row,col] = uncalibrated_array[row,col] + data_grid[row,col]

            with open(output_file_raw, "a") as file:
                file.write(f"ROW: {row} COL: {col}\n")
                file.write(np.array2string(data_grid) + '\n')
                file.write("\n")

    return line_to_send


def correct_coordinate_sys(x_off,y_off,array):
    array[:, 0] = array[:, 0] + x_off
    array[:, 1] = array[:, 1]+  y_off

    return array


def file_length(file_path):
    num_lines = 0
    with open(file_path, 'r') as file:
        num_lines = sum(1 for line in file)
    return num_lines

def main(port1, baud_rate1, timeout1, port2, baud_rate2, timeout2):
    # Photodiode array COM port
    #port1 = 'COM4'        
    #baud_rate1 = 115200   
    #timeout1 = 0          
    ser_merilno = serial.Serial(port1, baud_rate1, timeout=timeout1)

    # 3D printer COM port
    #port2 = 'COM5'        
    #baud_rate2 = 250000 
    #timeout2 = 1        
    ser_3D = serial.Serial(port2, baud_rate2, timeout=timeout2)

    return 23

    uncalibrated_array = np.zeros((12,12))

    Gcode_input_path = "Data/GCODE_output.gcode" #Gcode file 
    output_file_raw = "Logs/Calibration_za_3Dprinter_RAW.txt" #Log file
    loaded_array = np.loadtxt('Data/RAW_coordinates.csv') #Pick and Place photodiode coordinates
    

    #Offset between 3D printer C.S. and Photodiode array C.S
    x_offset = 0 #mm
    y_offset = -25 #mm


    corrected_offset = correct_coordinate_sys(x_offset,y_offset,loaded_array)

    array_to_gcode(corrected_offset, Gcode_input_path)

    with open(output_file_raw, "w") as file:
            file.write("RAW sample used for calculating the weights:\n\r")


    try:
       
        #Send first few Gcode lines that include settings and to move to (0,0)
        for i in range(3):
            send_gcode_line(Gcode_input_path,ser_3D,i)
            time.sleep(1)

    
        send_gcode_line(Gcode_input_path,ser_3D,3)
        time.sleep(15)

        send_gcode_line(Gcode_input_path,ser_3D,4)
        print("Insert board.")
        print("Press Enter to continue...")
        input()  
        print("Continuing execution...")

        send_gcode_line(Gcode_input_path,ser_3D,5)
        time.sleep(3)

        line_to_send = 5 #start of Photodiode coordinates

        for col in range(6):

            first_half = True
            reverse = (col % 2 != 0)
            line_to_send = process_column(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, uncalibrated_array, output_file_raw)


        print("Half of the calibration complete! Please turn the circuit around.")
        print("Press Enter to continue...")
        input()  
        print("Continuing execution...")
      
        line_to_send -=1

        for col in range(6,12):
            first_half = False
            reverse = (col % 2 == 0)
            line_to_send = process_column(col, line_to_send, reverse, first_half, Gcode_input_path, ser_3D, ser_merilno, uncalibrated_array, output_file_raw)


    finally:
    
        utezi = value_calibration2D(uncalibrated_array)
        
        kalibrarano = uncalibrated_array*utezi

        cal_avg = np.mean(kalibrarano)
        cal_avg = cal_avg / 10
        cal_avg = np.round(cal_avg)

        with open(output_file_raw, "a") as file:
            file.write("\n\rArray to be calibrated:\n\r")
            file.write(np.array2string(uncalibrated_array) + '\n')
            file.write("\n\rCalculated weights:\n\r")
            file.write(np.array2string(utezi) + '\n')
            file.write("\n\rCalculated calibrated array:\n\r")
            file.write(np.array2string(kalibrarano))


        np.savetxt('Weights/utezi_3D.txt', utezi) #saves Calibration weights

        np.savetxt('Weights/vrednost_1_sonce.txt', np.array([cal_avg])) #saves ADC value for 1 sun



        print("Calibration Completed!")

        ser_merilno.close()
        ser_3D.close()
        print("Serial ports closed.")


if __name__ == "__main__":
    main()
