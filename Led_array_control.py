import serial
import numpy as np
import time


def set_all_same_P(ser,power): 
    try: 
        if not (0 <= power <= 100):
            raise ValueError(f"Power out of bounds: Expected 0-100, but got {power}.")   

        command = f"-a_l[{int(power)}]\n\r"
        ser.write(command.encode())
        time.sleep(2)


    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


def set_one(ser,module,power):
    try: 
        if not (0 <= power <= 100):
            raise ValueError(f"Power out of bounds: Expected 0-100, but got {power}.")   
        
        if not (1 <= module <= 40):
            raise ValueError(f"Module number out of bounds: Expected 1-40, but got {module}.")   

        command = f"-s_l[{int(module)}][{int(power)}]\n\r"
        ser.write(command.encode())
        time.sleep(2)
        
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")


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


def main():
    
    port1 = 'COM11'        
    baud_rate1 = 115200   
    timeout1 = 1         
    ser_led_array = serial.Serial(port1, baud_rate1, timeout=timeout1)

    powers = np.zeros(40)
    powers[0:8] = 100

    module_powers = np.loadtxt("Weights/umetno_sonce_moci.txt")

    #TEST SEQUENCE 

   # set_all_same_P(ser_led_array,0)

    set_all_same_P(ser_led_array,10)
 
    #set_all_diff_P(ser_led_array,module_powers)
    #powers[8:16] = 100

    #set_all_diff_P(ser_led_array,powers)
    
    #set_all_same_P(ser_led_array,0)


if __name__ == "__main__":
    main()

