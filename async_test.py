import asyncio
import board
import countio
import digitalio
import busio

import GPS
import Menu

Flags = {'BUTTON': False, 'D1': False, 'D2': False}


async def catch_interrupt(pin, edge, pull):
    global Flags
    # "pin" __str__ returns "board.D0"|| Split on "." and take the pin name
    key = str(pin).split('.')[1]
    with countio.Counter(pin, edge=edge, pull=pull) as interrupt:
        while True:
            if interrupt.count > 0 and Flags[key] is False:
                print(f'{key}')
                interrupt.reset()
                Flags[key] = True
            # Let another task run.
            await asyncio.sleep(.35)


async def MenuNav(display):
    global Flags
    navList = ['Free Run', 'Logging', 'Files', 'Config']
    menu = Menu.MenuScreen('Main', navList)
    display.show(menu.getDisplayGroup())
    while True:
        if Flags['BUTTON']:
            menu.navCW()
            menu.updateMenu()
            print(f'Flag D0 = {Flags["BUTTON"]}')
            Flags['BUTTON'] = False

        if Flags['D1']:
            print(f'Flag D1 = {Flags["D1"]}')
            Flags['D1'] = False

        if Flags['D2']:
            menu.navCCW()
            menu.updateMenu()
            print(f'Flag D2 = {Flags["D2"]}')
            Flags['D2'] = False

        await asyncio.sleep(0)


async def Running(display):
    gps = GPS.GPSParser()
    uart = busio.UART(board.TX, board.RX, baudrate=38400)

    menu = Menu.RunningScreen('Main')
    display.show(menu.getDisplayGroup())
    while True:
        data = uart.readline()
        if data is not None:
            data_string = ''.join([chr(b) for b in data])
            print(data_string)
            for char in data_string:
                if gps.update(char) is not None:
                    menu.displayValues[0] = gps.latitude
                    menu.displayValues[1] = gps.longitude
                    menu.updateValues()
        await asyncio.sleep(0)


async def main():
    button_D0 = asyncio.create_task(catch_interrupt(board.D0, edge=countio.Edge.FALL, pull=digitalio.Pull.UP))
    button_D1 = asyncio.create_task(catch_interrupt(board.D1, edge=countio.Edge.RISE, pull=digitalio.Pull.DOWN))
    button_D2 = asyncio.create_task(catch_interrupt(board.D2, edge=countio.Edge.RISE, pull=digitalio.Pull.DOWN))
    machine = asyncio.create_task(Running(board.DISPLAY))
    await asyncio.gather(button_D0, button_D1, button_D2, machine)




asyncio.run(main())