from RPLCD.i2c import CharLCD
import RPi.GPIO as GPIO
from datetime import datetime
from time import sleep
import time

#-------------------------------------define Variables and GPIO setup-------------------------------------#

#Edit if needed
main_display = CharLCD(i2c_expander='PCF8574', address=0x27, port=1, cols=16, rows=2) #Initialize LCD display

status_from_main = "status_files/status_to_main_display.status" #Path to the status file where the main program writes the alarm status
status_to_main = "status_files/status_from_main_display_to_main.status" #The file the script writes into the user set ringtime (e.g. 11:11)

ok_button = 16 #GPIO input for OK-Button
down_button= 18 #GPIO input for DOWN-BUTTON
up_button = 22 #GPIO input for UP-BUTTON
menu_button = 24 #GPIO input for MENU-BUTTON

default_alarm_hour = 6 # Default alarm time displayed when opening the menu
default_alarm_minute = 0 # Default alarm time displayed when opening the menu

menu_time_increment = 1 #Time increment step when adjusting the alarm time (in minutes)


#Runtime Variables (updated dynamically). Do not edit!
alarm_active = False #Indicates if the alarm is currently set
ring_time = None #Stores the alarm time
ringing = False #Indicates if the alarm is currently ringing
last_display_content = False #Stores the last content displayed on the LCD
user_set_ringtime = None #Stores the alarm time set by the user

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

    try:
        with open(status_from_main, "r") as status_file:
            
            lines = [line.strip() for line in status_file.readlines()]

            if (len (lines) == 3):
                ring_time = lines[0]
                alarm_active = (lines[1] == "active")
                ringing = (lines[2] == "ringing")
            else:
                print("Error: " + status_from_main + " has to have exactly 3 lines")

    except FileNotFoundError:
        print("Error: " + status_from_main + " does not exist. Try starting main scirpt")


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
        print("Please specify whether you want the <date> or the <time>")


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

def write_to_main_status(ringtime):
    with open(status_to_main, "w") as status_file:
            status_file.write(ringtime)

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

    #Waits for user imput and performes actions
    while True:
        sleep(0.1)

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
            
        elif (GPIO.input(down_button) == GPIO.HIGH):
            press_time = time.time()
            while GPIO.input(down_button) == GPIO.HIGH:
                elapsed = time.time() - press_time
                if elapsed > 1:
                    adjust_menu_time(menu_time_increment * 5)
                else:
                    adjust_menu_time(menu_time_increment)
                    sleep(0.1)
            sleep(0.01)
        
        elif(GPIO.input(menu_button) == GPIO.HIGH):
            sleep(0.1)
            user_set_ringtime = None
            print("Menu closed")
            break
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


while True:
    read_alarm_status_from_main()

    if(GPIO.input(menu_button) == GPIO.HIGH):
             main_display_menu_button_pressed()
             sleep(0.1)
             last_display_content = False
             continue
    
    elif(alarm_active and not ringing):
        write_to_display("    " + get_time_date("date") + " " + get_time_date("time"), "Wecker um: " + ring_time)
    elif(alarm_active and ringing):
        write_to_display("    " + get_time_date("date") + " " + get_time_date("time"), " (*) Wecker (*)")
    
    else:
        write_to_display("    " + get_time_date("date") + " " + get_time_date("time"), "  Keine Wecker")


#Bildschirm je nach Helligkeit ein oder ausschalten unnd wenn auf knopf gedrückt wird wieder einschalten