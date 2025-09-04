import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
from matplotlib.widgets import Slider
from matplotlib.animation import FuncAnimation
import threading
import serial
import numpy as np
import sys
import io

################################################################
def open_serial_port(port, baud_rate, timeout):
    try:
        ser = serial.Serial(port, baud_rate, timeout=timeout)
        return ser
    except serial.SerialException as e:
        return None
    
#Helper function to open serial ports
def Misko_serial(port, baud_rate, timeout):
    ser_misko = open_serial_port(port, baud_rate, timeout)
    if ser_misko is None:
        return (f"Failed to open serial port {port}.")
    else:
        return (f"Serial port {port} opened successfully.")


def read_from_port():
    global data_grid
    temp_data_grid =np.zeros((12,12))

    with open("Logs/incoming_data.txt", "w") as file:
        print(f"Receiving data on {port}...")
        try:
            while not stop_event.is_set():
                if ser_misko.in_waiting > 0:                 
                    data = ser_misko.readline().decode('utf-8').strip()

                    col_values_dict = {}
                
                    for i in range(12):  
                        col_name = f"COL{i}:"  
                        if data.startswith(col_name):
                            col_values_dict[f"COL{i}"] = list(map(int, data.split(":")[1].split(',')))

                            for rowin in range(12):
                                temp_data_grid[rowin, i] = col_values_dict[f"COL{i}"][rowin]

                            file.write(data + '\n')
                            file.flush()

                            if (col_name == "COL11:"):
                                with data_lock:
                                    data_grid = temp_data_grid * skalirne_utezi
                                                                    
        except KeyboardInterrupt:
            print("Stopped reading by user.")



def send_to_port():
    try:
        while not stop_event.is_set():
            user_input = input("Enter data to send (or type 'exit' to quit): ")
            if user_input.lower() == 'exit':
                stop_event.set()
                print("Exiting")
                break
        
            ser_misko.write((user_input + '\n\r').encode('utf-8'))  # Send data to serial port
            print(f"Sent: {user_input}")
    except KeyboardInterrupt:
        print("Stopped sending by user.")


def toggle_command(event):
    global is_running
    if is_running:
        ser_misko.write(b'stop\n\r')  # Send the stop command to the serial port
        print("Sent: stop")
        button.label.set_text("Začetek meritve")
    else:
        ser_misko.write(b'start\n\r')  # Send the start command to the serial port
        print("Sent: start")
        button.label.set_text("Prekinitev meritve")
    is_running = not is_running


def update_heatmap(frame):
    selected_data =np.zeros((12, 12), dtype=int) 

    if is_running:
        with data_lock:

            selected_data = data_grid.copy()
            selected_data = selected_data / vrednost_sonca
            selected_data = selected_data.round()

            data_history.append(selected_data)

            slider.valmax = len(data_history) - 1  # Update slider range
            slider.ax.set_xlim(slider.valmin, slider.valmax)  # Redraw slider range
            slider.set_val(slider.valmax)
    else:
        frame = int(slider.val)  # Get the frame number from the slider
        selected_data = data_history[frame]
   
    min_val = int(np.min(selected_data))
    max_val = int(np.max(selected_data))
    avg_val = np.mean(selected_data)
    avg_val = int(avg_val.round())
    delta_val = max_val - min_val
    if(min_val != 0 or max_val != 0):
        homo_val = 100* delta_val /(max_val + min_val)
    else:
        homo_val = 100    
    

    heatmap.set_data(selected_data)

    for i in range(12):
        for j in range(12):
            annotations[i][j].set_text(f"{int(selected_data[i, j])}")

    update_heatmap.stats_text_obj = update_stats_text(ax, min_val, max_val, avg_val, delta_val, homo_val,  getattr(update_heatmap, 'stats_text_obj', None))

    return [heatmap] + [ann for row in annotations for ann in row]


def update_stats_text(ax, min_val, max_val, avg_val, delta_val, homo_val, text_obj=None):
    stats_text = f"Minimum: {min_val}\nMaksimum: {max_val}\nDelta: {delta_val}\nPovprečje: {avg_val}\nNehomogenost: {homo_val:.1f}%"
    if text_obj is not None:
        text_obj.set_text(stats_text)
    else:
        text_obj = ax.text(
            1.17, 0.5, stats_text, transform=ax.transAxes, fontsize=14,
            verticalalignment='center', bbox=dict(boxstyle="round", alpha=0.5, color='lightblue')
        )
    return text_obj


def plot_cell_history(cell_row, cell_coll):
    
    plt.figure()

    colors = ['blue', 'green', 'red']
    line_styles = ['-', '--']

    for i in range(0,3):
        for j in range(0,2):
            data = [frame[3*cell_row + i, 2*cell_coll + j] for frame in data_history]
            
            label = f'Vrstica {3*cell_row + i}, Stolpec {2*cell_coll + j}'
            plt.plot(data, label=label, color=colors[i], linestyle=line_styles[j])    

    plt.title(f"Zgodovina obsevanosti za celico: {cell_row}, {cell_coll}", fontsize=14)
    plt.xlabel("Vzorec",fontsize=14)
    plt.ylabel(r"Obsevanost (W/m$^2$)", fontsize=14)
    plt.grid(True)
    plt.legend()
    plt.show(block=True)


def on_click(event):
    if event.inaxes == ax:
        col = int(event.xdata + 0.5)
        row = int(event.ydata + 0.5)

        cell_row = row // 3 
        cell_coll = col // 2

        plot_cell_history(cell_row, cell_coll)

#merilnik in ne misko

#port = 'COM8'        
#baud_rate = 115200   
#timeout = 0          
ser_misko = None

def main():
    
    data_grid = np.zeros((12, 12), dtype=int)  
    data_history = [data_grid.copy()]

    data_lock = threading.Lock()

    stop_event = threading.Event()



    # Flag to track the start/stop state
    is_running = False

    #Import calibration weights
    skalirne_utezi = np.loadtxt("Weights/utezi_10s.txt")


    #Import unit conversion
    vrednost_sonca = np.loadtxt("Weights/vrednost_1_sonce.txt")
    vrednost_sonca = vrednost_sonca / 1000

    # Visualization setup
    fig, ax = plt.subplots()
    plt.subplots_adjust(bottom=0.2)  # Make space for the slider
    heatmap = ax.imshow(data_grid, cmap='viridis', vmin=900, vmax=1800, aspect='auto')
    plt.title("Toplotni zemljevid obsevanosti polja fotodiod", fontsize=14)
    cbar = plt.colorbar(heatmap)
    cbar.set_label(r"Obsevanost (W/m$^2$)", fontsize=14) 
    plt.xlabel("Stolpec", fontsize=14)
    plt.ylabel("Vrstica", fontsize=14)



    ax.set_xticks(np.arange(12))
    ax.set_yticks(np.arange(12))
    ax.set_xticklabels([f'{i}' for i in range(12)])
    ax.set_yticklabels([f'{i}' for i in range(12)])

    for col in range(2, 12, 2):  
        ax.axvline(col - 0.5, color='black', linewidth=2)
    for row in range(3, 12, 3):
        ax.axhline(row - 0.5, color='black', linewidth=2)


    # Create a button axis
    button_ax = plt.axes([0.86, 0.4, 0.06, 0.05])  
    button = Button(button_ax, "Začetek meritve") 
    button.on_clicked(toggle_command)


    annotations = [[ax.text(j, i, '', ha='center', va='center', color='white') for j in range(12)] for i in range(12)]

    fig.canvas.mpl_connect("button_press_event", on_click)


    ax_slider = plt.axes([0.2, 0.05, 0.6, 0.03], facecolor='lightgrey') 
    slider = Slider(ax_slider, 'Vzorec', 0, len(data_history), valinit=0, valstep=1)

    ani = FuncAnimation(fig, update_heatmap, interval=50, blit=False, cache_frame_data=False)

    ###########################################################################################
    
    try:
        read_thread = threading.Thread(target=read_from_port)
        #send_thread = threading.Thread(target=send_to_port)

        read_thread.start()
        #send_thread.start()

        plt.show()
        
        stop_event.set()

        read_thread.join()
        #send_thread.join()

    finally:
        ser_misko.close()
        print("Serial port closed. \n")

        ser_misko = None
        
if __name__ == "__main__":
    main()
