import time

import adafruit_pcf8523
import board
import busio

import Menu
from Peripherals import SelectWheel, CharacterDisplay, Button
from Menu import MenuScreen, NewLog, Config, Runtime, SplashScreen
import gc
import sdcardio
import storage
import os
import GPS
from utilities import LogFile
from digitalio import Pull

import json

# ---Global Setup---

SystemInitialized = False
rtcSink = False
circuitPy = None
state = 0
state_return = 0
selectedMenu = ''
selectedFile = ''
navList = ['New Log', 'Continue Log', 'No Log', 'Config']
quickStrings = ['file', 'row', 'range', 'field', 'Rng', 'Row', 'Eng']
jsonConfig = {'Raw_Upr': 1000, 'Raw_Lwr': 0, 'Eng_Upr': 15, 'Eng_Lwr': 0}
newFileName = ''
logger = LogFile()
loggingData = {'ymd': '', 'hms': '', 'Row': '', 'Rng': '', 'Lat': '', 'Lon': ''}
scrnMainMenu = MenuScreen('Main', navList)
scrnDirList = None
scrnNewLog = NewLog('New Log')
scrnStrInsert = MenuScreen('String Insert', quickStrings)
scrnConfig = Config('Config', jsonConfig)
scrnRuntime = Runtime('Runtime')
scrnSplashScreen = SplashScreen('SplashScreen')
"""
contLog = ContinueLog(navList[1])
noLog = NoLog(navList[2])
"""


selectedString = ''
display = board.DISPLAY
# seesaw is the pre-made firmware running the SAMD09U microcontroller used as the backbone for the rotary encoder board
i2c = board.STEMMA_I2C()  # Use STEMMA or standard I2C if switching to the GPIO pins
selectWheel = SelectWheel(i2c)
rtc = adafruit_pcf8523.PCF8523(i2c)

uart = busio.UART(board.TX, board.RX, baudrate=57600)
gps = GPS.GPSParser()

btnGreen = Button(board.A3, pull=Pull.DOWN)
btnRed = Button(board.A2, pull=Pull.DOWN)

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


def inputs():
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
    """-------"""

    # Calling instance as a function defaults to an internal cyclical scan function
    selectWheel(longPressTime=0.5)
    btnGreen(longPressTime=0.4)
    btnRed(longPressTime=0.8)
    """

    uartData = uart.readline()
    if uartData is not None:
        uartData = ''.join([chr(b) for b in uartData])
        "Parse GPS data until a new message is complete"
        for char in uartData:
            if gps.update(char) is not None:
                "Update rtc clock on the first good GPS message timestamp of a bootup"
                if not rtcSink:
                    rtc.datetime = time.struct_time(("Insert Tuple to format string",))
                    rtcSink = True
                "Update the Dictionaries of Info"
                t = rtc.datetime
                loggingData['ymd'] = f'{t.tm_year}:{t.tm_mon}:{t.tm_mday}'
                loggingData['hms'] = f'{t.tm_hour}:{t.tm_min}:{t.tm_sec}'
                loggingData['Lat'] = gps.latitude
                loggingData['Lon'] = gps.longitude
    """


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
    global display
    global selectedMenu
    global selectedFile
    global selectedString
    global newFileName
    global logger
    global loggingData

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
            state = 4000
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
        scrnRuntime.items = {'File': logger.fileName, 'Entry': logger.entrycount}  # Update FileName
        display.show(scrnRuntime.getDisplayGroup())
        state = 4010
        # -___-___-___-___-

    elif state == 4010:
        " Monitor the encoder wheel inputs for navigation "
        "Monitor Record Buttons for info grabbing"
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
        if btnGreen.longPress:
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
        if selectWheel.shortPress or selectWheel.longPress:
            state = 4000
        # -___-___-___-___-

    elif state == 4100:
        " Set update Done "
        scrnRuntime.setEdit(False)
        state = 4010
        # -___-___-___-___-

    elif state == 4200:
        " Sample the current entry  "
        if logger.addEntry(loggingData):
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
        if btnGreen or btnRed:
            state = state_return


def main():
    global state
    global SystemInitialized

    while True:
        inputs()
        laststate = state
        if SystemInitialized:
            sequence()
        if state != laststate or not SystemInitialized:
            print(f'Main State: {state}')
            print(str(gc.mem_free()) + 'bytes')
        SystemInitialized = True


main()
