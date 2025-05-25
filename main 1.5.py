from http.server import BaseHTTPRequestHandler, HTTPServer
from datetime import datetime
import RPi.GPIO as GPIO
import time
from time import sleep
import urllib.parse
import subprocess
import threading
import os
import re

#-------------------------------------define Variables and GPIO setup-------------------------------------#

#Edit if needed

#HTTP endpoints for receiving alarm settings and stopping the alarm
settings_post_endpoint = "/send_data"
stop_alarm_endpoint = "/stop_alarm"
stop_alarm_command = "stop_alarm"

default_snooze_duration = 10 #Default snooze duration in seconds

#Server ports for handling alarm settings and stop requests
settings_server_port = 8080
stop_server_port = 8081

#File displayed when the alarm is successfully activated or stopped
success_set_timer_page = "success_set_timer.html"
success_stop_timer_page = "success_stop_timer.html"

# Path to audio files and allowed ringtones
ringtone_directory = "audios/"
allowed_ringtones = ["main_audio.wav", "audio1.wav", "audio2.wav", "audio3.wav", "audio4.wav", "custom_audio.wav"] #allowed ringtones

webserver_status_file = "status_files/alarm_webserver_status.status" #The file the script writes into if a alarm is set or not (Webserver uses it to display the correct page if the alarm was set)
to_main_display_status_file = "status_files/status_to_main_display.status" #The file the script writes into if a alarm is set, ringing or change in ring time
default_main_display_status = "11:11\ninactive\nnot_ringing" #Default content for the status file from the line above (time, status, ringing state)
from_main_display_status_file = "status_files/status_from_main_display_to_main.status" #Path to the status file where the main_display writes the user set tingtime into

# GPIO pin assignments for the stop and snooze buttons
stop_button = 8 #GPIO input for Stop-Button
snooze_button = 10 #GPIO input for Snooze-Button


#Runtime Variables (updated dynamically). Do not edit!
ring_time = None #Stores the ring time, set by the user
selected_ringtone = None #Stores the ring tone, set by the user
snooze_duration = None #Stores the snooze duration, set by the user
alarm_stop_requested = None
stop_stop_server_event = threading.Event() #If set, the stop server will shut down
stop_settings_server_event = threading.Event() #If set, the settings server will shut down

#GPIO setup
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(stop_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(snooze_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

#------------------------------------------------Webserver------------------------------------------------#

#HTTP handler for processing alarm settings
class SentSettingsHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        global ring_time, selected_ringtone, snooze_duration, stop_settings_server_event

        #Check if the correct endpoint was called
        if self.path == settings_post_endpoint:
            #Parse POST request to extract alarm settings from the web form
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)

            #Encode post data to utf-8 and save it in variables
            ring_time = urllib.parse.parse_qs(post_data.decode("utf-8")).get("ring_time", [""])[0]
            selected_ringtone = urllib.parse.parse_qs(post_data.decode("utf-8")).get("ring_tone", [""])[0]
            snooze_duration = urllib.parse.parse_qs(post_data.decode("utf-8")).get("snooze_time", [""])[0]

            #Load the success confirmation page and insert received values
            with open(success_set_timer_page, "r") as file:
                success_message = file.read()

            #Replace placeholders with actual data
            success_message = success_message.replace("{{ ring_time }}", ring_time)
            success_message = success_message.replace("{{ ring_tone }}", selected_ringtone)
            success_message = success_message.replace("{{ snooze_time }}", snooze_duration)

            #Send HTTP response with confirmation page
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(success_message.encode("utf-8"))

            #Signal that the server can shut down after processing
            stop_settings_server_event.set()

#Stop command receiver webserver
class StopAlarmHandler(BaseHTTPRequestHandler):

    def do_POST(self):
        global alarm_stop_requested

        #Check if the correct endpoint was called
        if (self.path == stop_alarm_endpoint):
            #Read and decode POST data
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            usable_data = urllib.parse.parse_qs(post_data.decode("utf-8"))

            #Check if value sent to server matches
            if ('action' in usable_data and usable_data['action'][0] == stop_alarm_command):
                alarm_stop_requested = True
                
            else: 
                print(f"\033[91m Wrong paramenter was sent by the HTTP server\033[0m")
        
        #Load the success confirmation page and sent response
        with open(success_stop_timer_page, "r") as file:
            success_message = file.read()

        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(success_message.encode("utf-8"))


#Start settings webserver
def run_settings_server():
    global ring_time, selected_ringtone, snooze_duration

    server_address = ('', settings_server_port)
    server = HTTPServer(server_address, SentSettingsHandler)
    server.timeout = 0.5

    print(f"\033[92mStarting settings post server on port:'{settings_server_port}'\033[0m")

    #Run the server until the stop_settings_server_event is set
    while not stop_settings_server_event.is_set():
        server.handle_request()

    #Stop server
    server.server_close()
    print("Stopping HTTP settings server")

#Start stop webserver
def run_stop_server():

    server_address = ('', stop_server_port)
    server = HTTPServer(server_address, StopAlarmHandler)
    server.timeout = 0.5

    print(f"\033[92mStarting stop post server on port:'{stop_server_port}'\033[0m")

    #Run the server until the stop_stop_server_event is set
    while not stop_stop_server_event.is_set():
            server.handle_request()

    #Stop server
    server.server_close()
    print("Stopping HTTP stop server")

#------------------------------------------------Set timer------------------------------------------------#

#Calculate the number of seconds until the alarm time
def calculate_wait_seconds(target_time):
    try:
        #Convert input string to a datetime object with today's date
        target_time = datetime.strptime(target_time, "%H:%M").replace(year=datetime.now().year, month=datetime.now().month, day=datetime.now().day)
        time_now = datetime.now()
        difference_time = (target_time - time_now).total_seconds()
    except:
        print(f"\033[91m Time has to be HH:MM\033[0m")

    #If the specified time is earlier than the current time, schedule the alarm for the next day
    if (difference_time < 0):
        difference_time += 86400

    return difference_time


#Start the alarm at the scheduled time
def set_alarm():
    global alarm_stop_requested

    #Check if ringtone is in allowed_rintones
    if (selected_ringtone in allowed_ringtones):
        time_now = time.time()
        check_time = 0.1

        #Check every 0.1 seconds if alarm_stop_requested == True or stop_button == HIGH and stop alarm if it's the case
        while time.time() - time_now < seconds:
            if alarm_stop_requested:
                print("Stopping alarm from HTTP request")
                return
            elif (GPIO.input(stop_button) == GPIO.HIGH):
                 print("Stopping alarm from stop button request")
                 return
            sleep(check_time)

        while not alarm_stop_requested:

            #Playing rintone
            print("Playing:", selected_ringtone)
            #Update alarm status to ringing so the main display reflect the correct state
            update_main_display_status_file(2, "ringing")
            ring_tone_playing_process = subprocess.Popen(["aplay", f"{ringtone_directory}{selected_ringtone}"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            #Alarm keeps playing until it is stopped or snoozed
            print("GPIO Mode: ", GPIO.getmode()) #Not sure why this GPIO setup is needed again, but it works =)
            while ring_tone_playing_process.poll() is None:
                if (GPIO.input(stop_button) == GPIO.HIGH or alarm_stop_requested):
                    print("Stop button pressed or stopped by HTTP sever")
                    ring_tone_playing_process.terminate()
                    print("Stopping alarm")
                    stop_stop_server_event.set()
                    alarm_stop_requested = None
                    sleep(0.1)
                    return
                
                elif (GPIO.input(snooze_button) == GPIO.HIGH):
                    print("Snooze button pressed")
                    #Update alarm status to not_ringing so the main display reflect the correct state
                    update_main_display_status_file(2, "not_ringing")
                    ring_tone_playing_process.terminate()
                    print("Snoozing for", snooze_duration, "seconds")
                    snooze_time_int = int(snooze_duration)
                    sleep(snooze_time_int)
                    break
    else:
        print(f"\032[91m ERROR: specified ringtone is not in allowed_ringtones!\033[0m")

#-------------------------------------------Update status files-------------------------------------------#

#Update the alarm status file to inform the webserver
def write_to_webserver_status(active):
    with open(webserver_status_file, "w") as status_file:
        if active:
            status_file.write("active")
        else:
            status_file.write("inactive")


def update_main_display_status_file(line, content):
        
        #Check if the status file exists, if not, create it with default content
        if (not os.path.exists(to_main_display_status_file)):
            print(f"\033[33m'{to_main_display_status_file}' does not exist, creating it...\033[0m")
            with open(to_main_display_status_file, "w") as status_file:
                    status_file.write(default_main_display_status)
        
        #Read the lines from the status file
        with open(to_main_display_status_file, "r") as status_file:
                line_count = status_file.readlines()

        #If the file has more than 3 lines, reset it to the default content
        if (len(line_count) != 3):
                print(f"\033[33m'{to_main_display_status_file}' has more than 3 lines. Writing default content with 3 lines...\033[0m")
                with open(to_main_display_status_file, "w") as status_file:
                    status_file.write(default_main_display_status)
                
                #Re-read the file after resetting it
                with open(to_main_display_status_file, "r") as status_file:
                    line_count = status_file.readlines()

        #Check if the specified line index is valid
        if (line < 0 or line >= len(line_count)):
                print(f"\033[33m'{to_main_display_status_file}' has fewer lines than expected or the line index is out of range. Writing default content with 3 lines...\033[0m")
                with open(to_main_display_status_file, "w") as status_file:
                    status_file.write(default_main_display_status)
        else:
            #Update the specified line with the new content
            line_count[line] = content + "\n"

            #Write the updated content back to the status file
            with open(to_main_display_status_file, "w") as status_file:
                status_file.writelines(line_count)
                print("writing status to: " + to_main_display_status_file)

def check_main_display_input():
     global ring_time, snooze_duration, selected_ringtone

    #Loop until the settings server is told to stop
     while not stop_settings_server_event.is_set():
        try:
                #Try to open and read the status file where the main display writes user-set alarm time
                with open(from_main_display_status_file, "r") as status_file:
                    file_content = status_file.read().strip()
        except FileNotFoundError:
               #If the file does not exist, just set file_content to empty string and continue
               file_content = ""
        
        #Use regex to check if the content matches HH:MM
        match = re.match(r"^([01]?\d|2[0-3]):([0-5]?\d)$", file_content)

        if match:
            #If a valid time was found, update global alarm settings accordingly
            ring_time = file_content
            snooze_duration = default_snooze_duration
            selected_ringtone = "main_audio.wav"
            print("Alarm set due to user imput form the main display")

            #Signal to stop the settings server
            stop_settings_server_event.set()
            break

#------------------------------------------------Main code------------------------------------------------#

#Main Loop: Runs indefinitely to handle alarm scheduling
while True:
    try:
        #Set alarm status to inactive so the webserver and main display displays the correct page
        #The ring time can be set to any value in HH:MM format — the specific time doesn't matter, only that a time is provided
        write_to_webserver_status(False)
        update_main_display_status_file(0, "6:00")
        update_main_display_status_file(1, "inactive")
        update_main_display_status_file(2, "not_ringing")

        #Start the settings server in a separate thread (waits for alarm configuration)
        settings_server_thread = threading.Thread(target=run_settings_server)
        settings_server_thread.start()

        #Start the watcher thread server in a separate thread (waits for main display to sent a user set ring time)
        main_display_thread = threading.Thread(target=check_main_display_input)
        main_display_thread.start()

        settings_server_thread.join()
        main_display_thread.join()

        #Print received alarm settings for debugging
        print("Ringtime set by user:", ring_time)
        print("Ringtone set by user:", selected_ringtone)
        print("Snooze time set by user:" ,snooze_duration)

        update_main_display_status_file(0, ring_time)

        #Calculate the number of seconds until the alarm should go off
        seconds = calculate_wait_seconds(ring_time)
        print(seconds, "until alarm sounds...")

        #Update alarm status to active so the webserver and main display reflect the correct state
        write_to_webserver_status(True)
        update_main_display_status_file(1, "active")

        #Start the stop-server in a separate thread (allows stopping the alarm remotely)
        stop_server_thread = threading.Thread(target=run_stop_server)
        stop_server_thread.start()
        
        #Activate the alarm (plays sound and checks for stop/snooze) and upades alarm status so the main display reflects the correct state
        set_alarm()

        #Stop the stop-server thread after the alarm is stoped
        stop_stop_server_event.set()
        stop_server_thread.join()
        
        #Reset alarm status to inactive and ringtime to none after the alarm is stopped
        write_to_webserver_status(False)
        update_main_display_status_file(1, "inactive")
        update_main_display_status_file(2, "not_ringing")
        with open(from_main_display_status_file, "w") as status_file:
             status_file.write("None")

        #Clear HTTP server events so that they can start again
        stop_settings_server_event.clear()
        stop_stop_server_event.clear()

    finally:
        
        #Clean up GPIO pins to prevent conflicts
        GPIO.cleanup()

        #Reset global variables to their initial state
        ring_time = None
        selected_ringtone = None
        snooze_duration = None
        alarm_stop_requested = None

        #Reinitialize GPIO settings for the next alarm cycle
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(stop_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(snooze_button, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        #Ensure alarm status is inactive for the webserver display
        write_to_webserver_status(False)

        print("End of program cycle. Waiting for settings server to start...")


#FixMe
#Alarm can't be stopped while snoozing
