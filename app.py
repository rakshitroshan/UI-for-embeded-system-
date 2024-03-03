import sys
import os
import pandas as pd
from PyQt5.QtWidgets import QApplication,QGraphicsScene,QWidget,QVBoxLayout,QGraphicsView,QGraphicsObject, QGraphicsItemGroup,QHBoxLayout, QPushButton, QDesktopWidget, QMainWindow, QLabel, QCheckBox, QFormLayout, QInputDialog, QLineEdit, QComboBox
from PyQt5 import QtCore
from PyQt5.QtCore import Qt,QRectF,QPropertyAnimation,QPointF,QEasingCurve
import serial
import serial.tools.list_ports
from PyQt5.QtGui import QPainter, QColor, QPen, QPainterPath, QFont, QPixmap, QBrush
from PyQt5.QtWidgets import QMessageBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from datetime import datetime

class BatteryApp(QGraphicsView):
    class IonItem(QGraphicsObject):
        def __init__(self, circle_x, circle_y_pos):
            super().__init__()
            self.circle_x = circle_x
            self.circle_y_pos = circle_y_pos
           
        def boundingRect(self):
            radius = 7
            return QRectF(-radius, -radius, 2 * radius, 2 * radius)    
           
        def paint(self, painter, option, widget):
            painter.setPen(Qt.white)
            painter.setBrush(QColor("red"))
            painter.drawEllipse(self.boundingRect())
            painter.drawText(self.boundingRect(), Qt.AlignCenter, "Li⁺")

    class BatteryItem(QGraphicsItemGroup):
        def boundingRect(self):
            return QRectF(-self.width / 2, -self.height / 2, self.width, self.height)


        def __init__(self, width, height):
            super().__init__()
           
            self.width = width
            self.height = height


            self.left_image_path = './Grapc-rb.png'  # Replace with the actual path to your left image
            self.right_image_path = './rPO-rb.png'  # Replace with the actual path to your right image
            self.lpng_width = 85  # Set the width of the image
            self.lpng_height = 90
            self.rpng_width = 125  # Set the width of the image
            self.rpng_height = 130


            self.circle_radius = 3
            self.circle_y = -self.height / 4
            self.circle_spacing = 29


        def move_ions(self):
            self.ion_items = []
            for i in range(3):
                for j in range(3):
                    circle_x = self.width / 5 + (j * self.circle_spacing)
                    circle_y_pos = self.circle_y * 1.2 + (i * (self.circle_radius + self.circle_spacing))


                    ion_item = BatteryApp.IonItem(circle_x, circle_y_pos)
                    ion_item.setPos(circle_x, circle_y_pos)


                    self.addToGroup(ion_item)
                    animation = QPropertyAnimation(ion_item, b'pos')
                    animation.setDuration(5000)  # 5000 milliseconds (5 seconds)
                    animation.setStartValue(QPointF(circle_x, circle_y_pos))
                    animation.setEndValue(QPointF(-self.width / 1.7 + circle_x, circle_y_pos))
                    animation.setEasingCurve(QEasingCurve.Linear)


                    self.ion_items.append((ion_item, animation))


                    animation.start()


        def paint(self, QPainter, option, widget):


            # Draw the battery body
            gradient = QColor(200, 200, 200)
            QPainter.setBrush(gradient)
            pen = QPen(Qt.black, 2)
            QPainter.setPen(pen)


            # Draw left portion in orange
            left_rect = QRectF(-self.width / 2, -self.height / 2, self.width / 2, self.height)
            left_path = QPainterPath()
            left_path.addRect(left_rect)
            QPainter.fillPath(left_path, QColor("green"))


            # Draw right portion in red
            right_rect = QRectF(0, -self.height / 2, self.width / 2, self.height)
            right_path = QPainterPath()
            right_path.addRect(right_rect)
            QPainter.fillPath(right_path, QColor("blue"))


            # Draw a thick line in the middle
            line_rect = QRectF(-5, -self.height / 2, 10, self.height)
            line_path = QPainterPath()
            line_path.addRect(line_rect)
            QPainter.fillPath(line_path, QColor("black"))


            font = QFont(QPainter.font())
            font.setPixelSize(1)  # Adjust the size as needed
            QPainter.setFont(font)




            # Draw left image
            left_image = QPixmap(self.left_image_path)
            QPainter.drawPixmap(int(-self.width / 4 - self.lpng_width / 2), int(-self.height / 2),
                            int(self.lpng_width), int(self.lpng_height), left_image)


            # Draw right image
            right_image = QPixmap(self.right_image_path)
            QPainter.drawPixmap(int(self.rpng_width / 6), int(-self.height/1.45),
                            int(self.rpng_width), int(self.rpng_height), right_image)


    def __init__(self):
        super().__init__()


        self.init_ui()


    def init_ui(self):
        self.setGeometry(50, 70, 800, 800)
        self.setWindowTitle('Battery Design')


        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)


        battery_width = 190
        battery_height = 100


        # Set the initial position of the battery
        battery_item = self.BatteryItem(battery_width, battery_height)
        battery_item.setPos(self.width() // 2 - battery_width / 2, self.height() // 2 - battery_height / 2)


        self.scene.addItem(battery_item)
        battery_item.move_ions()


class MyWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.init_ui()
        # self.setWindowFlags(self.windowFlags() & ~Qt.WindowMaximizeButtonHint)
        self.setWindowState(Qt.WindowMaximized)


        self.arduino = serial.Serial()
        self.arduino.timeout = 0.5
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_values)
        self.is_recording = False
        self.toggle_button_clicked = False        
        self.update_available_ports()
        self.timer.start(1000)
        self.recorded_data = []
        self.time_values = []
        self.voltage_values = []
        self.soc_values=[]
        self.center_window()
        self.plot_graph()


    def init_ui(self):
       
        self.battery_app = BatteryApp()  
        self.battery_app.setStyleSheet("border: none;")
        central_widget = QWidget(self)
        central_widget.setStyleSheet("background-color: orange;")
        # Add the EmCog Solutions label in the top right corner
        emcog_label = QLabel('<font size="6" color="black"><b>EmCog Solutions</b></font>')
        emcog_label.setStyleSheet("margin-top: 2px; margin-right: 2px;")
        heading_label = QLabel('<font size="120" color="black"><b>LiFePO4 Battery Management System</b></font>')
        heading_layout = QHBoxLayout()
        heading_label.setStyleSheet("margin-left:210px; font-size: 18px;")
        heading_layout.addWidget(heading_label, alignment = Qt.AlignTop | Qt.AlignHCenter)
        heading_layout.addWidget(emcog_label, alignment=Qt.AlignTop | Qt.AlignRight)
           
       
        timestamp = QLabel('<font size="5"><b>Time</b></font>')
        voltage_label = QLabel('<font size="5"><b>Cell Voltage</b></font>')
        temp_label = QLabel('<font size="5"><b>Cell Temperature</b></font>')
        per_label = QLabel('<font size="5"><b>State Of Charge</b></font>')
       
        v_layout = QFormLayout()
        v_layout.setContentsMargins(100, 10, 0, 0)
        v_layout.setVerticalSpacing(20)
        self.timevalue = QLineEdit()
        self.timevalue.setMaximumSize(90, 50)
        self.timevalue.setStyleSheet("background-color: white;")
        self.timevalue.setReadOnly(True)        
        timeu_label = QLabel('s')
        timeu_label.setStyleSheet("font-size: 15px;color: black;")
        t_layout = QHBoxLayout()
        t_layout.addWidget(self.timevalue)
        t_layout.addSpacing(10)
        t_layout.addWidget(timeu_label)


        self.temp_value = QLineEdit()
        self.temp_value.setMaximumSize(90, 50)
        self.temp_value.setStyleSheet("background-color: white;")
        self.temp_value.setReadOnly(True)
        tempu_label = QLabel('°C')
        tempu_label.setStyleSheet("font-size: 15px;color: black;")
        te_layout = QHBoxLayout()
        te_layout.addWidget(self.temp_value)
        te_layout.addSpacing(10)
        te_layout.addWidget(tempu_label)  
       
        self.per_value = QLineEdit()
        self.per_value.setMaximumSize(90, 50)
        self.per_value.setStyleSheet("background-color: white;")
        self.per_value.setReadOnly(True)
        perc_label = QLabel('%')
        perc_label.setStyleSheet("font-size: 15px;color: black;")
        pe_layout = QHBoxLayout()
        pe_layout.addWidget(self.per_value)
        pe_layout.addSpacing(10)
        pe_layout.addWidget(perc_label)




        self.voltage_value = QLineEdit()
        self.voltage_value.setMaximumSize(90, 50)
        self.voltage_value.setStyleSheet("background-color: white;")
        self.voltage_value.setReadOnly(True)
        volt_label = QLabel('V')
        volt_label.setStyleSheet("font-size: 15px;color: black;")
        volt_layout = QHBoxLayout()
        volt_layout.addWidget(self.voltage_value)
        volt_layout.addSpacing(10)
        volt_layout.addWidget(volt_label)




        Charging = QCheckBox('Charging')
        self.Charging = Charging
       
        Discharging = QCheckBox('Discharging')
        self.Discharging = Discharging
       
        for radio in [Charging,Discharging]:
            radio.setStyleSheet("font-size: 15px;")
        c_layout = QHBoxLayout()
        c_layout.addWidget(Charging)
        c_layout.addWidget(Discharging)
        c_layout.addStretch()




        v_layout.addRow(timestamp,t_layout)
        v_layout.addRow(temp_label,te_layout)
        v_layout.addRow(per_label,pe_layout)
        v_layout.addRow(voltage_label,volt_layout)
        v_layout.addRow(c_layout)
       
        self.toggle_button = QPushButton('START',self)
        self.toggle_button.setCheckable(True)
        self.toggle_button.clicked.connect(self.toggle_recording)
        self.toggle_button.setStyleSheet("background-color: green; color: white; font-size: 20px;")
        port_label = QLabel('<font size="5" color="grey"><b>COM Port:</b></font>')
        self.com_port_dropdown = QComboBox()
        update_ports_button = QPushButton('Update Ports', self)
        update_ports_button.clicked.connect(self.update_available_ports)
        clear_button = QPushButton('Clear Graph', self)
        clear_button.clicked.connect(self.clear_graph)
        clear_button.setStyleSheet("background-color: #2196F3; color: white; font-size: 15px;")


        v_layout_battery = QVBoxLayout()    
        v_layout_battery.addWidget(self.battery_app)
        r_layout = QVBoxLayout()
        r_layout.addWidget(self.toggle_button)
        r_layout.addWidget(port_label)
        r_layout.addWidget(self.com_port_dropdown)
        r_layout.addWidget(update_ports_button)
        r_layout.addWidget(clear_button)
        r_layout.addStretch(0)
        h_layout = QHBoxLayout()      
        h_layout.addLayout(v_layout)
        h_layout.addLayout(v_layout_battery)
        h_layout.addLayout(r_layout)      




        m_layout = QVBoxLayout(central_widget)
        m_layout.addLayout(heading_layout)
        m_layout.addStretch(0)
        # m_layout.addStretch(0)
        m_layout.addLayout(h_layout)
        m_layout.addStretch(0)
        self.canvas = FigureCanvas(Figure(figsize=(5, 3)))
        m_layout.addWidget(self.canvas,1)
        self.setCentralWidget(central_widget)
        central_layout = QVBoxLayout(central_widget)  # Create a QVBoxLayout for the central widget
        central_layout.setContentsMargins(0, 0, 0, 0)


    # def add_battery_app_to_layout(self):
    #     self.battery_app.setStyleSheet("border: none;")
    #     battery_layout = QVBoxLayout()
    #     battery_layout.addWidget(self.battery_app)
    #     self.centralWidget().layout().insertLayout(1, battery_layout)
   
    def toggle_recording(self):
        if self.toggle_button.isChecked():
            self.start_recording()
            self.toggle_button.setText('STOP')
            self.toggle_button.setStyleSheet("background-color: red; color: white; font-size: 20px;")
        else:
            self.toggle_button.setText('START')
            self.toggle_button.setStyleSheet("background-color: green; color: white; font-size: 20px;")
            self.stop_recording()




    def center_window(self):
        screen_geometry = QDesktopWidget().screenGeometry()
        center_point = screen_geometry.center()
        self.setGeometry(center_point.x() - self.width() // 2, center_point.y() - self.height() // 2, self.width(),
                         self.height())




    def plot_graph(self):
        # Clear the existing plots
        self.canvas.figure.clf()
        fig = Figure(figsize=(20, 20))
        # Create subplots for the voltage-time graph and the second graph
        ax = self.canvas.figure.add_subplot(211)
        ax2 = self.canvas.figure.add_subplot(212)
        # Plot the voltage-time graph
        ax.plot_date(self.time_values, self.voltage_values, fmt='o-',markersize=3)
        ax.set_title('Voltage-Time Graph')
        ax.set_xlabel('Time')
        ax.set_ylabel('Voltage')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
        ax.set_ylim(0, 30)




        # Plot the second graph
        ax2.plot(self.soc_values, self.voltage_values, 'o-',markersize=3)
        ax2.set_title('Voltage vs. SOC')
        ax2.set_xlabel('SOC')
        ax2.set_ylabel('Voltage')
        ax2.set_ylim(0, 30)
        # Adjust the height of the graphs dynamically
        self.canvas.figure.tight_layout(pad=3.0)
        fig.subplots_adjust(hspace=0.5)
        self.canvas.draw()








    def show_alert_dialog(self, title, message):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setWindowTitle(title)
        msg_box.setText(message)
        msg_box.exec_()








    def update_values(self):
        if not self.arduino.is_open:
            com_port = self.com_port_dropdown.currentText()
            baudrate = 115200
            self.arduino = serial.Serial(com_port, baudrate, timeout=1)




        try:
            data = self.arduino.readline().decode('utf-8').strip().split(',')
            print(data)
            if len(data) == 6:
                self.timevalue.setText(data[0])
                self.voltage_value.setText(data[1])
                self.per_value.setText(data[2])
                self.temp_value.setText(data[3])




                if data[4] == '1' and data[5]=='0':
                    self.Charging.setChecked(True)
                    self.Discharging.setChecked(False)
                if data[4] == '0' and data[5]=='1':
                    self.Charging.setChecked(False)
                    self.Discharging.setChecked(True)
                if data[5]=='1' and data[4]=='1':
                    self.Charging.setChecked(False)
                    self.Discharging.setChecked(False)
                if  data[5]=='0' and data[4]=='0':
                    self.Charging.setChecked(False)
                    self.Discharging.setChecked(False)




                if self.is_recording:
                    # Append data to recorded_data for CSV file
                    self.recorded_data.append({
                        'Sensor 1': data[0],
                        'Sensor 2': data[1],
                        'Sensor 3': data[2],
                        'Sensor 4': data[3],
                        'Sensor 5': data[4],
                        'Sensor 6': data[5]
                    })




                # Update the voltage-time graph
                self.time_values.append(datetime.now())
                self.voltage_values.append(float(data[1]))
                self.soc_values.append(float(data[2]))
                # Only update the graph when recording is active
               
                self.plot_graph()
                return data
        except serial.SerialException:
            print("Error reading data from Arduino.")




    def show_filename_dialog(self):
        text, ok = QInputDialog.getText(self, 'File Name', 'Enter file name:')
        if ok:
            return text.strip()
        return None
   
    def save_recorded_data(self):
        while True:
            file_name = self.show_filename_dialog()
            if not file_name:
                print("Please enter a file name.")
                return




            if os.path.exists(f"{file_name}.csv"):
                # Show an alert if the file already exists
                self.show_alert_dialog("Alert", "File already exists. Choose a different name.")
                continue




            break
       
        df = pd.DataFrame(self.recorded_data)
        df.to_csv(f"{file_name}.csv", index=False)




        print(f"Sensor data recorded and saved to {file_name}.csv")




    def clear_graph(self):
    # Clear the existing data
        self.time_values = []
        self.voltage_values = []
        self.soc_values = []  
    # Update the graph
        self.plot_graph()




    def start_recording(self):
        if not self.is_recording:
            # If not already recording, start recording
            self.is_recording = True
            self.toggle_button_clicked = True  # Set the flag indicating the record button is clicked
            self.recorded_data = []  # Reset recorded data
            self.timer.start(1000)
        else:
            self.is_recording = False
            self.toggle_button_clicked = False  # Reset the flag when the Stop button is clicked
            self.timer.stop()
            self.save_recorded_data()




    def stop_recording(self):
        self.is_recording = False
        self.toggle_button_clicked = False
        self.save_recorded_data()
        self.recorded_data=[]
   
    def get_available_ports(self):
        return [port.device for port in serial.tools.list_ports.comports()]
   
    def update_available_ports(self):
        available_ports = self.get_available_ports()
        self.com_port_dropdown.clear()
        self.com_port_dropdown.addItems(available_ports)
       
       
             
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MyWindow()
    window.setWindowTitle("LiFePO4 Cell Analyser")
    window.show()
    sys.exit(app.exec_())
