from RPLCD.i2c import CharLCD
import RPi.GPIO as GPIO
from datetime import datetime
from time import sleep
import time
import threading

#-------------------------------------define Variables and GPIO setup-------------------------------------#

#Edit if needed
main_display = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2) #Initialize LCD display

status_from_main = "status_files/status_to_main_display.status" #Path to the status file where the main program writes the alarm status
status_to_main = "status_files/status_from_main_display_to_main.status" #The file the script writes into the user set ringtime (e.g. 11:11)

ok_button = 16 #GPIO input for OK-Button
down_button= 18 #GPIO input for DOWN-BUTTON
up_button = 22 #GPIO input for UP-BUTTON
menu_button = 24 #GPIO input for MENU-BUTTON
daylight_resistor_pin = 11 #GPIO input for DAYLIGHT_RESISTOR

default_alarm_hour = 6 # Default alarm time displayed when opening the menu
default_alarm_minute = 0 # Default alarm time displayed when opening the menu

menu_time_increment = 1 #Time increment step when adjusting the alarm time (in minutes)


#Runtime Variables (updated dynamically). Do not edit!
alarm_active = False #Indicates if the alarm is currently set
ring_time = None #Stores the alarm time
ringing = False #Indicates if the alarm is currently ringing
last_display_content = False #Stores the last content displayed on the LCD
user_set_ringtime = None #Stores the alarm time set by the user
auto_backlight_control = True #Indicates if the backlight should be automaticly controlled or not

#GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(ok_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(down_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(up_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(menu_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#------------------------------------------------Functions------------------------------------------------#

#Opens and reads the alarm status file
#Only if the status file exists and contains exactly three lines:
#Writes the content of the status file into global variables
def read_alarm_status_from_main():
    global alarm_active, ring_time, ringing

    attempt = 0
    max_attempts = 3

    #Try up to max_attempts times to read the file
    while attempt < max_attempts:
        try:
            with open(status_from_main, "r") as status_file:
                #Read all lines and strip whitespace
                lines = [line.strip() for line in status_file.readlines()]

                #Ensure the file contains exactly 3 lines
                if len(lines) == 3:
                    ring_time = lines[0]                    #Line 1: Time when alarm is set (e.g. "07:30")
                    alarm_active = (lines[1] == "active")   #Line 2: Alarm status ("active" or inactive)
                    ringing = (lines[2] == "ringing")       #Line 3: Ringing status ("ringing" or not_ringing)
                    return
                else:
                    print(f"\033[33m Warning: '{status_from_main}' must contain exactly 3 lines. Retrying...\033[0m")

        except FileNotFoundError:
            #File not found, remind the user to run the main script first
            print(f"\033[91m Error: '{status_from_main}' does not exist. Try starting main script.\033[0m")

        attempt = attempt + 1
        sleep(1) # Wait 1 second before retrying

    print(f"\033[91m Error: Failed to read '{status_from_main}' after {max_attempts} attempts. Waiting 10 seconds and trying again...\033[0m")
    sleep(10)


#Returns the current date or time depending of the argument given to the function:
#"date" returns the current date, e.g. "Mo", "Di", ...
#"time" returnes the current time, e.g. 11:11
def get_time_date(time_or_date):

    week_days = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"]
    
    if (time_or_date == "time"):
        time = datetime.now()
        timenow = time.strftime("%H:%M")
        return timenow
    elif (time_or_date == "date"):
        date = datetime.now()
        datenow = int(date.strftime("%w"))
        return week_days[datenow]
    else:
        print(f"\033[91m Error: Please specify whether you want the <date> or the <time>\033[0m")


#Updating the content of the lcd display, only if the content has changed
def write_to_display(line1, line2):
    global last_display_content

    if (last_display_content != [line1 , line2]):
        main_display.cursor_pos = (0, 0)
        main_display.write_string(line1.ljust(16))
        main_display.cursor_pos = (1, 0)
        main_display.write_string(line2.ljust(16))
        last_display_content = [line1, line2]
        
        print("Wrote to Line 1 on main display: " + line1.strip())
        print("Wrote to Line 2 on main display: " + line2.strip())

#Writes selected ringtime to the status file for the main program to read
def write_to_main_status(ringtime):
    with open(status_to_main, "w") as status_file:
            status_file.write(ringtime)

#Measures the brightness level in the room using a light-dependent resistor and a capacitor. The charging time of the capacitor depends on the light intensity:
#The brighter it is, the faster it charges.
def get_brightnes():

    #Discharge the capacitor by setting the pin to output and driving it LOW
    GPIO.setup(daylight_resistor_pin, GPIO.OUT)
    GPIO.output(daylight_resistor_pin, GPIO.LOW)
    time.sleep(0.1)
    
    #Set the pin to input mode to start measuring the capacitor charging tim
    GPIO.setup(daylight_resistor_pin, GPIO.IN)
    currentTime = time.time()
    diff = 0
    
    #Wait until the capacitor has charged enough to pull the pin HIGH
    while(GPIO.input(daylight_resistor_pin) == GPIO.LOW):
        diff  = time.time() - currentTime

    #Convert the charging time to a brightness value (shorter time = more light)
    brightness = round(diff * 1000) #Convert seconds to milliseconds

    #Return the measured brightness value
    return brightness

def backlight_control ():
    while True:
        if(get_brightnes() > 100 and auto_backlight_control == True):
            main_display.backlight_enabled = False
        else:
            main_display.backlight_enabled = True
        sleep(2)
#---------------------------------------------Menu Functions----------------------------------------------#

#Opens a settings menu, where the user can make changes to the alarm ring time
#The user can adjust the ring time with the up/down arrows and confirm with ok
def main_display_menu_button_pressed():
    global default_alarm_hour, default_alarm_minute, menu_time_increment, user_set_ringtime

    if (alarm_active or ringing):
        print("Menu button pressed while alarm was armed")
        main_display.clear()
        main_display.cursor_pos = (0, 1)
        main_display.write_string("Wecker bereits")
        main_display.cursor_pos = (1, 4)
        main_display.write_string("gestellt")
        sleep(2)
        return

    main_display.clear()
    update_menu_time(default_alarm_hour, default_alarm_minute)
    print("Menu opend")

    #Main loop to capture user input for setting the alarm time
    while True:
        sleep(0.1)

        #UP button increases time
        if (GPIO.input(up_button) == GPIO.HIGH):
            press_time = time.time()
            while GPIO.input(up_button) == GPIO.HIGH:
                elapsed = time.time() - press_time
                if elapsed > 1:
                    adjust_menu_time(menu_time_increment * 5)
                else:
                    adjust_menu_time(menu_time_increment)
                    sleep(0.1)
            sleep(0.01)
        
        #DOWN button decreases time
        elif (GPIO.input(down_button) == GPIO.HIGH):
            press_time = time.time()
            while GPIO.input(down_button) == GPIO.HIGH:
                elapsed = time.time() - press_time
                if elapsed > 1:
                    adjust_menu_time(-menu_time_increment * 5)
                else:
                    adjust_menu_time(-menu_time_increment)
                    sleep(0.1)
            sleep(0.01)
        
        #MENU button exits the menu without saving
        elif(GPIO.input(menu_button) == GPIO.HIGH):
            sleep(0.1)
            user_set_ringtime = None
            print("Menu closed")
            break

        #OK button confirms the selected time
        elif(GPIO.input(ok_button) == GPIO.HIGH):
            user_set_ringtime = f"{default_alarm_hour:02}:{default_alarm_minute:02}"
            main_display.clear()
            main_display.cursor_pos = (0, 5)
            main_display.write_string("Wecker")
            main_display.cursor_pos = (1, 4)
            main_display.write_string("gestellt")
            write_to_main_status(user_set_ringtime)
            print("User set ringtime to: " + str(user_set_ringtime))
            sleep(2)
            break


#Updates the display with the currently selected alarm time in the menu.
def update_menu_time(hours, minutes):
    main_display.cursor_pos = (0, 3)
    main_display.write_string("<Weckzeit>")
    main_display.cursor_pos = (1, 5)
    main_display.write_string(f"{hours:02}:{minutes:02}")


#Adjusts the alarm time by the specified number of minutes.
#Ensures that hours and minutes remain within valid ranges. No alarm at 6:70 =)
def adjust_menu_time(minutes):
    global default_alarm_hour, default_alarm_minute

    added_minutes = default_alarm_minute + minutes
    added_hours = added_minutes // 60
    new_minutes = added_minutes % 60

    if new_minutes < 0:
        added_hours -= 1
        new_minutes += 60

    new_hours = (default_alarm_hour + added_hours) % 24

    default_alarm_hour = new_hours
    default_alarm_minute = new_minutes

    update_menu_time(new_hours, new_minutes)

#------------------------------------------------Main Code------------------------------------------------#

backlight_control_thread = threading.Thread(target=backlight_control, daemon=True)
backlight_control_thread.start()

while True:

    read_alarm_status_from_main()

    if(GPIO.input(menu_button) == GPIO.HIGH):
            auto_backlight_control = False #Stop the automatic backlight control
            main_display.backlight_enabled = True #Turn on the backlight
            main_display_menu_button_pressed()
            sleep(0.1)
            last_display_content = False #Reset display state to force update
            auto_backlight_control = True #Restart the automatic backlight control
            continue

    #Alarm is set but not ringing
    elif(alarm_active and not ringing):
        write_to_display("    " + get_time_date("date") + " " + get_time_date("time"), "Wecker um: " + ring_time)

    #Alarm is currently ringing
    elif(alarm_active and ringing):
        write_to_display("    " + get_time_date("date") + " " + get_time_date("time"), " (*) Wecker (*)")
    
    #No alarm set
    else:
        write_to_display("    " + get_time_date("date") + " " + get_time_date("time"), "  Keine Wecker")
#Feature request:
#Turn the screen off or on depending on brightness, and turn it back on when the button is pressed
