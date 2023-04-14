"""
Silk Stick Main Entry Code
Author: Tyler Malsom
Date: 05/2023
Overview: Software to operate the "Silk Stick" apparatus that utilizes various inputs to measure height in conjunction
with relevant information such as GPS and manual data input from operator.
Scan Structure operates under principal
Init --> Input --> Sequence --> Output
           ^----------------------v

Most variables will be globally scoped to the controller to maintain operations
 as this code will operate single threaded.

"""


import time
import adafruit_pcf8523
import board
import busio
from adafruit_max1704x import MAX17048
import Menu
from Peripherals import SelectWheel, CharacterDisplay, Button, StringPot, Beeper
from Menu import MenuScreen, NewLog, Config, Runtime, SplashScreen, GPSDetails
import gc
import sdcardio
import storage
import os
import GPS
from Utilities import LogFile, Timer, Scaling, printInline
from digitalio import Pull

import json

# ---CONSTANTS---
"""------Global Variable Setup------"""
SystemInitialized = False
enableGPS = False
rtcSink = True
circuitPy = None
state = 0
state_return = 0
selectedMenu = ''
selectedFile = ''
selectedString = ''
gps_sentenceCount = None
navList = ['New Log', 'Continue Log', 'Config', 'Battery']
quickStrings = ['file', 'row', 'range', 'field', 'Rng', 'Row', 'Eng', 'Exp']
jsonConfig = {'Raw_Upr': 25500, 'Raw_Lwr': 2000, 'Eng_Upr': 10, 'Eng_Lwr': 42}
newFileName = ''
logger = LogFile()
loggingData = {'ymd': '', 'hms': '', 'Row': 0, 'Rng': 0, 'Lat': '', 'Lon': ''}

"""------Screen Setups------"""
scrnMainMenu = MenuScreen('Main', navList)
scrnDirList = None
scrnNewLog = NewLog('New Log')
scrnStrInsert = MenuScreen('String Insert', quickStrings)
scrnConfig = Config('Config', jsonConfig)
scrnRuntime = Runtime('Runtime')
scrnSplashScreen = SplashScreen('SplashScreen')
scrnSplashNoAck = SplashScreen('Splash No Ack', ack=False)
scrnGPSDetails = GPSDetails('GPS Details')
"""------"""

tmrStandby = Timer()  # Create Timers globally to allow input and sequence usage
tmrdisplayDelay = Timer()
tmrGPSTimeout = Timer()
tmrGPSDetailUpdate = Timer()
scaling = Scaling()  # Instantiate the scaling block


"""------I2C Setup------"""
# seesaw is the pre-made firmware running the SAMD09U microcontroller used as the backbone for the rotary encoder board
i2c = board.STEMMA_I2C()  # Use STEMMA or standard I2C if switching to the GPIO pins
display = board.DISPLAY  # Integral TFT display 240 x 135
try:
    selectWheel = SelectWheel(i2c)
except ValueError:
    raise ValueError('Rotory Encoder Selection Wheel is not detected or address error has occurred.')
try:
    rtc = adafruit_pcf8523.PCF8523(i2c)
except ValueError:
    raise ValueError('Real Time Clock device is not detected or address error has occurred.')
try:
    stringPot = StringPot(i2c)
except ValueError:
    raise ValueError('ADC String-Pot device is not detected or address error has occurred.')
try:
    display2 = CharacterDisplay(i2c)
except ValueError:
    raise ValueError('7 segment character display device is not detected or address error has occurred.')
"""------"""
"""
battery_monitor = MAX17048(i2c)
"""

"""------UART Setup------"""
uart = busio.UART(board.TX, board.RX, baudrate=115200, timeout=0.1)
gps = GPS.GPSParser()
"""------"""

btnGreen = Button(board.A2, pull=Pull.DOWN)
btnRed = Button(board.A3, pull=Pull.DOWN)
beeper = Beeper(board.A0)

"""------Single Scan Startup Logic------"""
"""------SD Card------"""
try:
    sdcard = sdcardio.SDCard(board.SPI(), board.D10)
    vfs = storage.VfsFat(sdcard)
    storage.mount(vfs, '/sd')
    print(f'Mounting SD... {os.listdir("/sd")}')
except OSError:
    print("No SD Card on SPI Bus...")
    sdcard = None
"""-------JSON Config File------"""
if sdcard is not None:
    dir = os.listdir('/sd')
    dir = list(filter(lambda i: i.endswith('.json'), dir))  # filter out files not ending '.json'
    print(f'Json Files: {dir}')
    if len(dir) > 0:
        with open(f'/sd/{dir[0]}', 'r') as config:
            jsonConfig = json.load(config)
            scaling.setup = jsonConfig
            print(f'Loading Config...{jsonConfig}')
    else:
        with open('/sd/config.json', 'w') as file:
            json.dump(jsonConfig, file)
"""-------"""


def outputs():
    """Output Routine used for any cyclical output peripheral updates."""
    global beeper
    beeper()


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
    global tmrStandby
    global tmrdisplayDelay
    global stringPot
    global tmrGPSTimeout
    global tmrGPSDetailUpdate
    """-------"""

    """------Timers------"""
    tmrStandby()  # Cyclically scanned - Interface with .EN and .PRE similar to PLC
    tmrdisplayDelay()
    tmrGPSTimeout()
    tmrGPSDetailUpdate()

    """------Discrete Inputs------"""
    # Calling instance as a function defaults to an internal cyclical scan function
    selectWheel(longPressTime=0.5)
    btnGreen(longPressTime=0.4)
    btnRed(longPressTime=0.8)

    """------I2C Analog Inputs------"""
    stringPot()  # Cyclical update of internal vars
    if not tmrdisplayDelay.EN:
        tmrdisplayDelay.PRE = 0.1
        tmrdisplayDelay.EN = True
    if tmrdisplayDelay.EN and tmrdisplayDelay.DN:
        try:
            displayVal = round(scaling(stringPot.value), 2)
            printInline(str(displayVal))
            display2.message = f'{displayVal:.2f}'  # Update lcd display to the string pot display
            loggingData['Height'] = f'{displayVal:.2f}'

        except ValueError:
            display2.message = (99.99, 2)
        tmrdisplayDelay.EN = False

    """------Gps Receiver Input------"""
    if enableGPS:
        uartData = uart.read(16)
        if uartData is not None:
            tmrGPSTimeout.EN = False # reset timer
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
        else:
            tmrGPSTimeout.PRE = 3.0
            tmrGPSTimeout.EN = True

    """------"""

    "Update the Dictionaries logger Info"
    t = rtc.datetime
    loggingData['ymd'] = f'{t.tm_year}:{t.tm_mon}:{t.tm_mday}'
    loggingData['hms'] = f'{t.tm_hour}:{t.tm_min}:{t.tm_sec}'
    loggingData['Lat'] = gps.latitude if enableGPS else ''
    loggingData['Lon'] = gps.longitude if enableGPS else ''
    loggingData['Lat_Maj'] = gps.latitude_list[0] if enableGPS else ''
    loggingData['Lat_Min'] = gps.latitude_list[1] if enableGPS else ''
    loggingData['Lon_Maj'] = gps.longitude_list[0] if enableGPS else ''
    loggingData['Lon_Min'] = gps.longitude_list[1] if enableGPS else ''


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
    global tmrStandby
    global tmrGPSDetailUpdate
    global enableGPS
    global gps_sentenceCount
    global jsonConfig
    global beeper
    #global battery_monitor

    # Start State Logic Control

    """Main Menu Logic Start"""
    if state == 0:
        " Display Main Menu "
        gc.collect()  # Run Garbage collection on memory
        display.show(scrnMainMenu.getDisplayGroup())
        enableGPS = False
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

            #displaytext1 = "Battery Percent: {:.2f} %".format(battery_monitor.cell_percent)
            #displaytext2 = "Battery Voltage: {:.2f} V".format(battery_monitor.cell_voltage)
            #scrnSplashScreen.setDisplayText(displaytext1 + '\n' + displaytext2, Menu.YEL)

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
                scrnSplashScreen.setDisplayText('Error: File Name Already Exists...')  # existing file found
                state_return = 1000
                state = 9000
                break
        # -___-___-___-___-

    elif state == 1300:
        """ Create new .txt file with proper headers for .csv interpretation """
        if logger.CreateNewFile(newFileName):  # Returns True if successful
            state = 4000
        else:
            scrnSplashScreen.setDisplayText('Failed to create ')  # existing file found
            state_return = 1000
            state = 9000
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
            scrnSplashScreen.setDisplayText('Error occurred attempting to change the logger data...')
            state_return = 0
            state = 9000
        # -___-___-___-___-

        """###### Continue_Log Screen END ######"""

        """--------------------------------------"""

        """###### No_Log Screen Start ######"""
        """REMOVED """
        """
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
    """
        """###### No_Log Screen END ######"""

        """--------------------------------------"""

        """###### Configuration Screen Start ######"""
    elif state == 3000:
        " Set the display screen "
        scrnConfig.config = jsonConfig
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
            if scrnConfig.getSelected() == 'Cancel':
                state = 0
            else:
                state = 3020
        if selectWheel.longPress:
            state = 3200
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
            state = 3100
        if selectWheel.longPress:
            state = 3040
        # -___-___-___-___-

    elif state == 3040:
        " If selected items allows, record value from reading"
        scrnConfig.recordVal(stringPot.value)
        state = 3100

    elif state == 3100:
        " Set update Done "
        scrnConfig.setEdit(False)
        state = 3010
        # -___-___-___-___-

    elif state == 3200:
        " Update JSON Config file "
        jsonConfig = scrnConfig._config
        state = 3300
        # -___-___-___-___-

    elif state == 3300:
        " Write new values to json file in SD card "
        try:
            with open('/sd/config.json', 'w') as file:
                json.dump(jsonConfig, file)
            state = 3310
        except OSError:
            state_return = 0
            scrnSplashScreen.setDisplayText('Unable to write out new params to SD card.')
            state = 9000
        # -___-___-___-___-

    elif state == 3310:
        " update the scaling block "
        scaling.setup = jsonConfig
        state = 0

    elif state == 4000:
        """ Open up Running Log Display """
        scrnRuntime.items = {'File': logger.fileName, 'Entry': logger.entryCount}  # Update FileName
        display.show(scrnRuntime.getDisplayGroup())
        enableGPS = True
        gc.collect()
        state = 4010
        # -___-___-___-___-

    elif state == 4010:
        if not tmrGPSTimeout.DN:
            "Cyclically update displayed Info"
            if loggingData['Lat'] != scrnRuntime.items['Lat'] or loggingData['Lon'] != scrnRuntime.items['Lon']:
                scrnRuntime.items = {'GPS': gps.fix_stat}
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
        else:
            gps.fix_stat = 0
            state = 10000
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
        "Bring up Runtime screen"
        gc.collect()
        display.show(scrnGPSDetails.getDisplayGroup())
        state = 4050
        # -___-___-___-___-

    elif state == 4050:
        "Cyclically Update display info, monitor for input"
        if not tmrGPSDetailUpdate.DN:
            tmrGPSDetailUpdate.PRE = 1.0
            tmrGPSDetailUpdate.EN = True
        else:
            tmrGPSDetailUpdate.EN = False
            scrnGPSDetails.updateDisplay(gps)
        if selectWheel.shortPress:
            state = 4000
        if selectWheel.longPress:
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
        " Sample the current entry "
        if logger.addEntry(loggingData):
            scrnRuntime.items = {'Entry': logger.entryCount}
            state = 4210
        else:
            scrnSplashScreen.setDisplayText('Error Occurred During Write to Log')
            state_return = 4000
            state = 9000
        # -___-___-___-___-

    elif state == 4210:
        " Short tone for confirmation "
        beeper.beep(duration=0.10)  # beep...
        state = 4010
        # -___-___-___-___-

    elif state == 4300:
        logger.removeLastEntry()
        state = 4310

    elif state == 4310:
        " Long tone for confirmation "
        beeper.beep(duration=0.3)  # beeeeeep...
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
        tmrStandby.PRE = 6
        tmrStandby.EN = True  # Hold Timer True to Time
        """Check for GPS signals before the Timer1.DN turns on"""
        printInline(f'Checking for GPS {tmrStandby.ACC:.2f}s/{tmrStandby.PRE}s')
        scrnSplashNoAck.setDisplayText(f'Checking for GPS {tmrStandby.ACC:.2f}s/{tmrStandby.PRE}s')

        if tmrStandby.DN:
            """No GPS detected, Disable the scanning to avoid overhead and set flag"""
            print('\nNo GPS packets detected, setting GPS state to OFF...')
            enableGPS = False
            scrnSplashScreen.setDisplayText('Warning! No GPS signals detected.')
            state_return = 0
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
        laststate = state
        """INPUT -- SEQUENCE -- OUTPUT"""
        inputs()
        if SystemInitialized:
            sequence()
        outputs()
        """INPUT -- SEQUENCE -- OUTPUT"""

        if state != laststate or not SystemInitialized:
            print(f'Main State: {state}')
            print(str(gc.mem_free()) + 'bytes')
        SystemInitialized = True


main()
