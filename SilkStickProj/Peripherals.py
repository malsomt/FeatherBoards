import time

from adafruit_seesaw import seesaw, rotaryio, digitalio
from adafruit_ht16k33 import ht16k33, segments
import countio
import analogio
from digitalio import DigitalInOut, Direction, DriveMode, Pull
import adafruit_ads1x15.ads1015 as ADS
from adafruit_ads1x15.analog_in import AnalogIn


class CharacterDisplay:
    def __init__(self, i2c):
        self._display = segments.Seg7x4(i2c)
        self._message = '0000'

    @property
    def message(self):
        return self._message

    @message.setter
    def message(self, input):
        try:
            mes = input
        except TypeError:
            raise TypeError("Pass an iterable with two items (characters, decimal count)")
        else:
            self._message = mes
            out = str(self._message)
            if len(out) < 5:  # Avoid character shifting by adding a zero
                out = '0' + out
            self._display.print(out)
            self._display.show()


class StringPot:
    def __init__(self, i2c):
        self._ADS = ADS.ADS1015(i2c)  # Default Address 0x40
        self._ADS.mode = ADS.Mode.CONTINUOUS  # Set the ADS device to continuous sample
        self._device = AnalogIn(self._ADS, ADS.P0)  # Analog Channel A0
        self._voltage = 0
        self._value = 0

    def __call__(self, *args, **kwargs):
        self.scan(*args, **kwargs)

    def scan(self):
        self._voltage = self._device.voltage
        self._value = self._device.value

    @property
    def value(self):
        return self._value

    @property
    def voltage(self):
        return self._voltage


class Button:
    def __init__(self, pin, pull=Pull.UP):
        self.val = DigitalInOut(pin)
        self.val.switch_to_input(pull)

        self._press = False
        self._release = False
        self._held = False
        self._longPress = False
        self._shortPress = False
        self.holdCount = 0

    def __call__(self, *args, **kwargs):
        self.scan(*args, **kwargs)

    def scan(self, longPressTime=0.5):
        # Button Pressed
        btn = self.val.value

        if btn and not self._press and not self._held:  # Press Event
            self._press = True
            self._held = True
            self._release = False

        elif btn and self._press:  # Press Event Over, still held
            self._press = False
            self._held = True
            self._release = False

        elif not btn and self._held:  # Press Released Event
            self._press = False
            self._held = False
            self._release = True

        elif not btn and not self._held:  # Press Release Over
            self._press = False
            self._held = False
            self._release = False

        if self._longPress:  # Ensure longPress is only on for a single scan event
            self._longPress = False

        if self._shortPress:  # Ensure longPress is only on for a single scan event
            self._shortPress = False

        if self._held and self.holdCount == 0:
            self.holdCount = time.monotonic()

        if self._held and self.holdCount != 0:
            count = time.monotonic() - self.holdCount
            if count >= longPressTime:
                self._longPress = True

        if self._release:  # release event resets hold counter
            count = time.monotonic() - self.holdCount
            if count < longPressTime:
                self._shortPress = True
            self.holdCount = 0

    @property
    def press(self):
        return self._press

    @property
    def release(self):
        return self._release

    @property
    def held(self):
        return self._held

    @property
    def shortPress(self):
        return self._shortPress

    @property
    def longPress(self):
        return self._longPress


class SelectWheel:
    def __init__(self, i2c):
        self.rotaryEncoder = seesaw.Seesaw(i2c, addr=0x36)  # 0x36 is the default address for the rotary encoder
        self.rotaryEncoder.pin_mode(24,
                                    self.rotaryEncoder.INPUT_PULLUP)  # Set the pinmode for pin 24 on the Encoder backpack tied to the center 'push/click' of the encoder button.
        self._iEncoder_btn = digitalio.DigitalIO(self.rotaryEncoder, 24)  # assign a Digital IO class to the pin
        self._iEncoder_wheel = rotaryio.IncrementalEncoder(self.rotaryEncoder)
        self.last_position = -self._iEncoder_wheel.position
        self._up = False
        self._dwn = False
        self._press = False
        self._release = False
        self._held = False
        self._longPress = False
        self._shortPress = False
        self.holdCount = 0

    def __call__(self, *args, **kwargs):
        self.scan(*args, **kwargs)

    def scan(self, longPressTime=0.5):

        position = self._iEncoder_wheel.position  # Invert encoder pos to make CW motion positive
        if position != self.last_position:
            if position > self.last_position:
                self._up = True
            if position < self.last_position:
                self._dwn = True
            self.last_position = position
        else:
            self._up = False
            self._dwn = False

        # Button Pressed
        btn = not self._iEncoder_btn.value  # Button is active low

        if btn and not self._press and not self._held:  # Press Event
            self._press = True
            self._held = True
            self._release = False

        elif btn and self._press:  # Press Event Over, still held
            self._press = False
            self._held = True
            self._release = False

        elif not btn and self._held:  # Press Released Event
            self._press = False
            self._held = False
            self._release = True

        elif not btn and not self._held:  # Press Release Over
            self._press = False
            self._held = False
            self._release = False

        if self._longPress:  # Ensure longPress is only on for a single scan event
            self._longPress = False

        if self._shortPress:  # Ensure longPress is only on for a single scan event
            self._shortPress = False

        if self._held and self.holdCount == 0:
            self.holdCount = time.monotonic()

        if self._held and self.holdCount != 0:
            count = time.monotonic() - self.holdCount
            if count >= longPressTime:
                self._longPress = True

        if self._release:  # release event resets hold counter
            count = time.monotonic() - self.holdCount
            if count < longPressTime:
                self._shortPress = True
            self.holdCount = 0

    @property
    def up(self):
        return self._up

    @property
    def dwn(self):
        return self._dwn

    @property
    def press(self):
        return self._press

    @property
    def release(self):
        return self._release

    @property
    def held(self):
        return self._held

    @property
    def shortPress(self):
        return self._shortPress

    @property
    def longPress(self):
        return self._longPress






