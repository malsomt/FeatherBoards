"""
Silk Stick Main Entry Code
Author: Tyler Malsom
Date: 05/2023
Overview: Software to operate the "Silk Stick" apparatus that utilizes various inputs to measure height in conjunction
with relevant information such as GPS and manual data input from operator.
Scan Structure operate under principal
Init --> Input --> Sequence
           ^----------v

Most variables will be globally scoped to the controller to maintain operations
 as this code will operate single threaded.

"""


import time
import adafruit_pcf8523
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio
from adafruit_lc709203f import LC709203F, PackSize
import Menu
from Peripherals import SelectWheel, CharacterDisplay, Button, StringPot
from Menu import MenuScreen, NewLog, Config, Runtime, SplashScreen
import gc
import sdcardio
import storage
import os
import GPS
from utilities import LogFile, Timer, Scaling, printInline
from digitalio import Pull

import json

# ---CONSTANTS---
MAIN = 0
SPLASH = 9000
GPSCHECK = 10000

# ---Global Setup---
SystemInitialized = False
enableGPS = False
rtcSink = True
circuitPy = None
state = 0
state_return = 0
selectedMenu = ''
selectedFile = ''
navList = ['New Log', 'Continue Log', 'No Log', 'Config', 'Battery']
quickStrings = ['file', 'row', 'range', 'field', 'Rng', 'Row', 'Eng']
jsonConfig = {'Raw_Upr': 1000, 'Raw_Lwr': 0, 'Eng_Upr': 15, 'Eng_Lwr': 0}
newFileName = ''
logger = LogFile()
loggingData = {'ymd': '', 'hms': '', 'Row': 0, 'Rng': 0, 'Lat': '', 'Lon': ''}

scrnMainMenu = MenuScreen('Main', navList)
scrnDirList = None
scrnNewLog = NewLog('New Log')
scrnStrInsert = MenuScreen('String Insert', quickStrings)
scrnConfig = Config('Config', jsonConfig)
scrnRuntime = Runtime('Runtime')
scrnSplashScreen = SplashScreen('SplashScreen')
scrnSplashNoAck = SplashScreen('Splash No Ack', ack=False)

Timer1 = Timer()  # Create a global timer for simple delays

Scaling = Scaling()  # Instantiate the scaling block

selectedString = ''
display = board.DISPLAY
# seesaw is the pre-made firmware running the SAMD09U microcontroller used as the backbone for the rotary encoder board
i2c = board.STEMMA_I2C()  # Use STEMMA or standard I2C if switching to the GPIO pins
selectWheel = SelectWheel(i2c)
rtc = adafruit_pcf8523.PCF8523(i2c)

adc = ADS.ADS1015(i2c)  # Default Address 0x40
adc.mode = ADS.Mode.CONTINUOUS  # Set ADC to sample continuously.
strPot = AnalogIn(adc, ADS.P0)
#battery_monitor = LC709203F(i2c)
#battery_monitor.pack_size = PackSize.MAH3000

uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.1)
gps = GPS.GPSParser()

btnGreen = Button(board.A3, pull=Pull.DOWN)
btnRed = Button(board.A2, pull=Pull.DOWN)
stringPot = StringPot(board.A0)

display2 = CharacterDisplay(i2c)
display2.message = 123.4, 1

try:
    sdcard = sdcardio.SDCard(board.SPI(), board.D10)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, '/sd')
    print(f'Mounting SD... {os.listdir("/sd")}')
except OSError:
    print("No SD Card on SPI Bus...")
    sdcard = None
"""
if sdcard is not None:
    if os('/sd/config.json'):
        try:
            with open('/sd/config.json') as file:         
                jsonConfig = json.loads(file)
        except OSError:
            
            Use Os.stat to get file info
"""


def inputs():
    """Input routine used for any cyclical scanning of I/O"""
    """Declare Global references below"""
    global selectWheel
    global display2
    global btnGreen
    global btnRed
    global gps
    global loggingData
    global uart
    global rtc
    global rtcSink
    global enableGPS
    global Timer1
    global stringPot
    """-------"""
    """------Discrete Inputs------"""
    # Calling instance as a function defaults to an internal cyclical scan function
    selectWheel(longPressTime=0.5)
    btnGreen(longPressTime=0.4)
    btnRed(longPressTime=0.8)

    """------Timers------"""
    Timer1()  # Cyclically scanned - Interface with .EN and .PRE similar to PLC
    """------Gps Receiver Input------"""

    if enableGPS:
        uartData = uart.read(16)
        if uartData is not None:
            uartData = ''.join([chr(b) for b in uartData])
            "Parse GPS data until a new message is complete"
            for char in uartData:
                result = gps.update(char)
                if result is not None and result == 'GNZDA':
                    "Update rtc clock on the first good GPS ZDA timestamp after bootup"
                    if rtcSink:
                        # year, mon, date, hour, min, sec, wday, yday, isdst
                        rtc.datetime = time.struct_time((int(gps.datestamp[2]), int(gps.datestamp[1]),
                                                         int(gps.datestamp[0]), int(gps.timestamp[0]),
                                                         int(gps.timestamp[1]), int(gps.timestamp[2][:2]), 0, -1, -1))
                        rtcSink = False

    "Update the Dictionaries logger Info"
    t = rtc.datetime
    loggingData['ymd'] = f'{t.tm_year}:{t.tm_mon}:{t.tm_mday}'
    loggingData['hms'] = f'{t.tm_hour}:{t.tm_min}:{t.tm_sec}'
    loggingData['Lat'] = gps.latitude if enableGPS else ''
    loggingData['Lon'] = gps.longitude if enableGPS else ''


def sequence():
    """ Main sequence logic utilizes state based logic to manage flow through program and displays """
    " Alias local vars to global scope "
    global state
    global state_return
    global btnGreen
    global btnRed
    global selectWheel
    global scrnMainMenu
    global scrnDirList
    global scrnNewLog
    global scrnStrInsert
    global scrnSplashScreen
    global scrnSplashNoAck
    global display
    global selectedMenu
    global selectedFile
    global selectedString
    global newFileName
    global logger
    global loggingData
    global Timer1
    global enableGPS
    global gps_sentenceCount

    # Start State Logic Control

    """Main Menu Logic Start"""
    if state == 0:
        " Display Main Menu "
        gc.collect()  # Run Garbage collection on memory
        display.show(scrnMainMenu.getDisplayGroup())
        state = 10
        # -___-___-___-___-

    elif state == 10:
        " Monitor selection Wheel for inputs "
        if selectWheel.up:  # Encoder CW
            scrnMainMenu.navCCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnMainMenu.navCW()
        if selectWheel.shortPress:  # Encoder Pressed
            selectedMenu = scrnMainMenu.getSelected()
            state = 20
        # -___-___-___-___-

    elif state == 20:
        " Branch to the new selected screen state "
        if selectedMenu == 'New Log':  # New Log
            state = 1000

        elif selectedMenu == 'Continue Log':  # Continue Log
            if sdcard is None:
                scrnSplashScreen.setDisplayText('No SDCard Detected', Menu.YEL)
                state_return = 0
                state = 9000
            else:
                state = 1500

        elif selectedMenu == 'No Log':  # No Log
            state = 2000

        elif selectedMenu == 'Config':  # Config
            state = 3000

        elif selectedMenu == 'Battery':  # Get Battery Info
            state = 30
        # -___-___-___-___-

        if state == 30:
            " Set to Display Battery Info on Splash Screen "
            """
            displaytext1 = "Battery Percent: {:.2f} %".format(battery_monitor.cell_percent)
            displaytext2 = "Battery Voltage: {:.2f} V".format(battery_monitor.cell_voltage)
            scrnSplashScreen.setDisplayText(displaytext1 + '\n' + displaytext2, Menu.YEL)
            """
            scrnSplashScreen.setDisplayText('Feature is currently unavailable...', Menu.YEL)
            state_return = 0
            state = 9000
            # -___-___-___-___-
        """###### Main Menu Logic END ######"""

        """--------------------------------------"""

        """###### New_Log Screen Logic Start ######"""
    elif state == 1000:
        " Set the display screen "
        display.show(scrnNewLog.getDisplayGroup())
        state = 1010
        # -___-___-___-___-

    elif state == 1010:
        " Monitor selection Wheel for inputs "
        if selectWheel.up:  # Encoder CW
            scrnNewLog.navCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnNewLog.navCCW()
        if selectWheel.shortPress:
            item = scrnNewLog.getNavItem()
            if item == 'Esc':  # Escape the screen
                state = 0
            elif item == '<-Bcksp':  # Backspace for file string
                scrnNewLog.subtractChar()
            elif item == 'Save':  # Save the file
                newFileName = scrnNewLog.getFileName()
                state = 1200
            elif item == 'Ins':  # Quick Insert Strings
                state = 1030
            else:  # character edit
                state = 1020
        # -___-___-___-___-

    elif state == 1020:
        """ Set the screen to edit mode """
        scrnNewLog.setEdit(True)
        state = 1100
        # -___-___-___-___-

    elif state == 1030:
        """ Display the menu for quick string inserts """
        display.show(scrnStrInsert.getDisplayGroup())
        state = 1040
        # -___-___-___-___-

    elif state == 1040:
        """ Monitor the encoder wheel inputs for navigation """
        if selectWheel.up:  # Encoder CCW
            scrnStrInsert.navCCW()
        elif selectWheel.dwn:  # Encoder CW
            scrnStrInsert.navCW()
        if selectWheel.shortPress:  # Encoder Pressed
            scrnNewLog.addStr(scrnStrInsert.getSelected())
            state = 1000

    elif state == 1100:
        """ Monitor the encoder wheel inputs for character selection """
        if selectWheel.up:  # Encoder CW
            scrnNewLog.editCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnNewLog.editCCW()
        if selectWheel.shortPress:
            state = 1120
        if selectWheel.longPress:
            state = 1110
        # -___-___-___-___-

    elif state == 1110:
        """ Reset the screen out of edit mode """
        scrnNewLog.setEdit(False)
        state = 1010
        # -___-___-___-___-

    elif state == 1120:
        """ Add selected character to the string"""
        scrnNewLog.addChar()
        state = 1100
        # -___-___-___-___-

    elif state == 1200:
        """ Save selected, check all for name interference"""
        files = os.listdir("/sd")
        state = 1300
        for file in files:
            if file == newFileName:  # check if filename exists
                state = 99999999  # existing file found
        # -___-___-___-___-

    elif state == 1300:
        """ Create new .txt file with proper headers for .csv interpretation """
        if logger.CreateNewFile(newFileName):  # Returns True if successful
            state = 4000
        else:
            # Something went wrong
            state = 999999999999
        # -___-___-___-___-

        """###### New_Log Screen Logic End ######"""

        """--------------------------------------"""

        """###### Continue_Log Screen Start ######"""
    elif state == 1500:
        "Collect list of .txt files on the SD card for display"
        dir = os.listdir('/sd')
        dir = list(filter(lambda i: i.endswith('.txt'), dir))  # filter out files not ending '.txt'
        scrnDirList = MenuScreen('Directory List', dir)
        display.show(scrnDirList.getDisplayGroup())
        state = 1510
        # -___-___-___-___-

    elif state == 1510:
        "Monitor Navigation Inputs"
        if selectWheel.up:  # Encoder CCW
            scrnDirList.navCCW()
        elif selectWheel.dwn:  # Encoder CW
            scrnDirList.navCW()
        if selectWheel.shortPress:  # Encoder Pressed
            selectedFile = scrnDirList.getSelected()
            state = 1520
        elif selectWheel.longPress:
            state = 0
        # -___-___-___-___-

    elif state == 1520:
        logger.fileName = selectedFile
        if logger.fileName == selectedFile:
            state_return = 4000
            state = 10000
        else:
            state = 999999
        # -___-___-___-___-

        """###### Continue_Log Screen END ######"""

        """--------------------------------------"""

        """###### No_Log Screen Start ######"""
    elif state == 2000:
        display.show(scrnRuntime.getDisplayGroup())
        gc.collect()  # Run Garbage collection on memory
        state = 2010
        # -___-___-___-___-

    elif state == 2010:
        " Monitor the encoder wheel inputs for navigation "
        if selectWheel.up:  # Encoder CW
            scrnRuntime.navCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnRuntime.navCCW()
        if selectWheel.shortPress:
            if scrnRuntime.getSelected() == 'GPS':
                state = 2040  # Go to GPS Detail Screen
            else:
                state = 2020  # Go to Edit Mode
        if selectWheel.longPress:
            state = 0
        # -___-___-___-___-

    elif state == 2020:
        " Set the menu screen to highlight selection "
        scrnRuntime.setEdit(True)
        state = 2030
        # -___-___-___-___-

    elif state == 2030:
        " Monitor the encoder wheel inputs for editing values "
        if selectWheel.up:  # Encoder CW
            scrnRuntime.editCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnRuntime.editCCW()
        if selectWheel.shortPress:
            state = 2100
        if selectWheel.longPress:
            pass
        # -___-___-___-___-

    elif state == 2040:
        " Bring up GPS Details Screen"
        gc.collect()
        display.show(scrnRuntime.getDisplayGroup())
        state = 2050
        # -___-___-___-___-

    elif state == 2050:
        " Bring up GPS Details "
        pass
        # -___-___-___-___-

    elif state == 2100:
        " Set update Done "
        scrnRuntime.setEdit(False)
        state = 2010
        # -___-___-___-___-

        """###### No_Log Screen END ######"""

        """--------------------------------------"""

        """###### Configuration Screen Start ######"""
    elif state == 3000:
        " Set the display screen "
        display.show(scrnConfig.getDisplayGroup())
        gc.collect()  # Run Garbage collection on memory
        state = 3010
        # -___-___-___-___-

    elif state == 3010:
        " Monitor the encoder wheel inputs for navigation "
        if selectWheel.up:  # Encoder CW
            scrnConfig.navCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnConfig.navCCW()
        if selectWheel.shortPress:
            state = 3020
        if selectWheel.longPress:
            state = 0
        # -___-___-___-___-

    elif state == 3020:
        " Set the menu screen to highlight selection "
        scrnConfig.setEdit(True)
        state = 3030
        # -___-___-___-___-

    elif state == 3030:
        " Monitor the encoder wheel inputs for editing values "
        if selectWheel.up:  # Encoder CW
            scrnConfig.editCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnConfig.editCCW()
        if selectWheel.shortPress:
            state = 3040
        if selectWheel.longPress:
            pass
        # -___-___-___-___-

    elif state == 3040:
        " Update JSON Config file "
        pass
        state = 3100
        # -___-___-___-___-

    elif state == 3100:
        " Set update Done "
        scrnConfig.setEdit(False)
        state = 3010
        # -___-___-___-___-

    elif state == 4000:
        """ Open up Running Log Display """
        scrnRuntime.items = {'File': logger.fileName, 'Entry': logger.entryCount}  # Update FileName
        display.show(scrnRuntime.getDisplayGroup())
        gc.collect()
        state = 4010
        # -___-___-___-___-

    elif state == 4010:
        "Cyclically update displayed Info"
        if loggingData['Lat'] != scrnRuntime.items['Lat'] or loggingData['Lon'] != scrnRuntime.items['Lon']:
            scrnRuntime.items = {'Lat': loggingData['Lat'], 'Lon': loggingData['Lon']}

        " Monitor the encoder wheel inputs for navigation "
        " Monitor Record Buttons for info grabbing"
        if selectWheel.up:  # Encoder CW
            scrnRuntime.navCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnRuntime.navCCW()
        if selectWheel.shortPress:
            if scrnRuntime.getSelected() == 'GPS':
                state = 4040  # Go to GPS Detail Screen
            else:
                state = 4020  # Go to Edit Mode
        if selectWheel.longPress:
            state = 0
        if btnGreen.shortPress:
            state = 4200
        elif btnRed.longPress:
            state = 4300
        # -___-___-___-___-

    elif state == 4020:
        " Set the menu screen to highlight selection "
        scrnRuntime.setEdit(True)
        state = 4030
        # -___-___-___-___-

    elif state == 4030:
        " Monitor the encoder wheel inputs for editing values "
        if selectWheel.up:  # Encoder CW
            scrnRuntime.editCW()
        elif selectWheel.dwn:  # Encoder CCW
            scrnRuntime.editCCW()
        if selectWheel.shortPress:
            state = 4100
        if selectWheel.longPress:
            pass
        # -___-___-___-___-

    elif state == 4040:
        " Bring up GPS Details Screen"
        gc.collect()
        display.show(scrnRuntime.getDisplayGroup())
        state = 4050
        # -___-___-___-___-

    elif state == 4050:
        pass
        """if selectWheel.shortPress or selectWheel.longPress:"""
        state = 4000
        # -___-___-___-___-

    elif state == 4100:
        " Set update Done "
        scrnRuntime.setEdit(False)
        loggingData['Rng'] = scrnRuntime.items['Rng']
        loggingData['Row'] = scrnRuntime.items['Row']
        state = 4010
        # -___-___-___-___-

    elif state == 4200:
        " Sample the current entry  "
        if logger.addEntry(loggingData):
            scrnRuntime.items = {'Entry': logger.entryCount}
            state = 4210
        else:
            scrnSplashScreen.setDisplayText('Error Occurred During Write to Log')
            state_return = 4000
            state = 9000
        # -___-___-___-___-

    elif state == 4210:
        " Do something for Confirmation "
        """"Make a beep, flash a light...do something"""
        state = 4010
        # -___-___-___-___-

    elif state == 9000:
        " Show Splash screen and message"
        display.show(scrnSplashScreen.getDisplayGroup())
        state = 9010
        # -___-___-___-___-

    elif state == 9010:
        " Monitor common inputs to move to next screen"
        if selectWheel.shortPress or selectWheel.longPress:
            state = state_return
        if btnGreen.shortPress or btnRed.shortPress:
            state = state_return
        # -___-___-___-___-

    elif state == 10000:
        "Start into this state from a restart, check GPS and other inputs to ensure function"
        print(f"Checking for GPS Device...")
        enableGPS = True
        gps_sentenceCount = gps.parsed_sentences
        display.show(scrnSplashNoAck.getDisplayGroup())
        state = 10010
        # -___-___-___-___-

    elif state == 10010:
        "Wait for serial log data to update"
        Timer1.PRE = 10
        Timer1.EN = True  # Hold Timer True to Time
        """Check for GPS signals before the Timer1.DN turns on"""
        printInline(f'Checking for GPS {Timer1.ACC:.2f}s/{Timer1.PRE}s')
        scrnSplashNoAck.setDisplayText(f'Checking for GPS {Timer1.ACC:.2f}s/{Timer1.PRE}s')

        if Timer1.DN:
            """No GPS detected, Disable the scanning to avoid overhead and set flag"""
            print('\nNo GPS packets detected, setting GPS state to OFF...')
            enableGPS = False
            scrnSplashScreen.setDisplayText('Warning No GPS signals detected.')
            state = 9000
        if gps.parsed_sentences != gps_sentenceCount:
            """check to see if GPS is parsing sentences, if so maintain the GPS enabled"""
            enableGPS = True
            state = state_return
        # -___-___-___-___-


def main():
    global state
    global SystemInitialized
    global stringPot
    global scrnRuntime

    while True:
        inputs()
        laststate = state
        if SystemInitialized:
            sequence()
        if state != laststate or not SystemInitialized:
            print(f'Main State: {state}')
            print(str(gc.mem_free()) + 'bytes')
            print(scrnRuntime.items)
        SystemInitialized = True

        print('1: ' + str(strPot.value)+ ', ' + str(strPot.voltage))
        time.sleep(0.3)


main()
