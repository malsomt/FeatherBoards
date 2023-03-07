import board
import busio
import sdcardio
import storage
import os
from SilkStickProj import GPS

sdcard = sdcardio.SDCard(board.SPI(), board.D5)
vfs = storage.VfsFat(sdcard)
storage.mount(vfs, '/sd')
print(f'Mounting SD... {os.listdir("/sd")}')

uart = busio.UART(board.TX, board.RX, baudrate=9600)
gps = GPS.GPSParser()

while True:
    data = uart.readline()  # read up to 32 bytes
    # print(data)  # this is a bytearray type

    if data is not None:
        data_string = ''.join([chr(b) for b in data])
        for char in data_string:
            if gps.update(char) is not None:
                print(gps.latitude)
                print(gps.longitude)
                print(gps.timestamp)
                print(data_string)
                with open('/sd/file.txt', 'a') as f:
                    f.write(f'{gps.latitude}\n {gps.longitude}\n')
                    f.write(f'{gps.timestamp}\n\n')
