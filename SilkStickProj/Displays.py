import terminalio
from adafruit_display_text import label, scrolling_label
import displayio
from GPS import GPSParser

WHT = 0xFFFFFF
BLK = 0x000000
GRY = 0x555555
YEL = 0xFFFF00
GRN = 0x00FF00
RED = 0xFF0000

'''Concept of the Menu Navigation screen is as follows.
---Use the navUp and Dwn functions to increment the displayed menu items
---The displayed labels are hard coded to only show three items at a time with the center label representing the active selection.
---To build the menu list, pass a list of strings into the class on instantiation that will be used to display as navigation items and find the other screens
'''


class SplashScreen:
    def __init__(self, screenName, defaultTextColor=WHT, defaultBackgroundColor=BLK, ack=True):
        self.screenName = screenName
        self.defaultTextColor = defaultTextColor
        self.defaultBackgroundColor = defaultBackgroundColor
        self.ack = ack
        self._buildDisplay()

    def _buildDisplay(self):
        self.displayItems = displayio.Group()
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', scale=2,
                                             anchor_point=(0.5, 0.5), anchored_position=(120, 15),
                                             background_color=self.defaultBackgroundColor,
                                             color=self.defaultTextColor, padding_left=2))

        self.displayItems.append(label.Label(font=terminalio.FONT, text='', scale=2,
                                             anchor_point=(0.5, 0.5), anchored_position=(120, 40),
                                             background_color=self.defaultBackgroundColor,
                                             color=self.defaultTextColor, padding_left=2))

        self.displayItems.append(label.Label(font=terminalio.FONT, text='', scale=2,
                                             anchor_point=(0.5, 0.5), anchored_position=(120, 65),
                                             background_color=self.defaultBackgroundColor,
                                             color=self.defaultTextColor, padding_left=2))

        self.displayItems.append(label.Label(font=terminalio.FONT, text='', scale=2,
                                             anchor_point=(0.5, 0.5), anchored_position=(120, 90),
                                             background_color=self.defaultBackgroundColor,
                                             color=self.defaultTextColor, padding_left=2))
        if self.ack:  # Do not generate this message ack is not allowed
            self.displayItems.append(label.Label(font=terminalio.FONT, text='Press any Button to Acknowledge',
                                                 scale=1, anchor_point=(0.5, 1.0), anchored_position=(120, 130),
                                                 background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))

    def setDisplayText(self, text, color=None, bgcolor=None):
        color = color if color is not None else self.defaultTextColor
        bgcolor = bgcolor if bgcolor is not None else self.defaultTextColor
        textList = str.split(text, ' ')
        line0 = ''
        line1 = ''
        line2 = ''
        line3 = ''
        for word in textList:
            if len(line0) + len(word) < 18:
                line0 = line0 + word + ' '
            elif len(line1) + len(word) < 18:
                line1 = line1 + word + ' '
            elif len(line2) + len(word) < 18:
                line2 = line2 + word + ' '
            else:
                line3 = line3 + word + ' '

        self.displayItems[0].text, self.displayItems[1].text, self.displayItems[2].text, self.displayItems[3].text = \
            line0, line1, line2, line3
        self.displayItems[0].color, self.displayItems[1].color, self.displayItems[2].color, self.displayItems[3].color = \
            color, color, color, color
        self.displayItems[0].bgcolor, self.displayItems[1].bgcolor, self.displayItems[2].bgcolor, \
        self.displayItems[3].bgcolor = bgcolor, bgcolor, bgcolor, bgcolor

    def getDisplayGroup(self):
        return self.displayItems


class MenuScreen:
    def __init__(self, screenName, navList, selectIndex=0, defaultTextColor=WHT, defaultBackgroundColor=BLK):
        self.screenName = screenName
        self.navList = navList
        self.selectIndex = selectIndex
        self.defaultTextColor = defaultTextColor
        self.defaultBackgroundColor = defaultBackgroundColor
        # Build menu display
        self._buildDisplay()
        self.updateMenu()

    def getDisplayGroup(self):
        # Function returns the DisplayGroup for the Board.Display.show() function
        return self.displayItems

    def updateMenu(self):
        self.displayItems[0].text = self.navList[self.selectIndex - 1] if self.selectIndex != 0 else ''
        self.displayItems[1].text = self.navList[self.selectIndex]
        self.displayItems[2].text = self.navList[self.selectIndex + 1] if self.selectIndex <= len(
            self.navList) - 2 else ''

    def navCCW(self):
        index = self.selectIndex
        if self.selectIndex > 0:
            self.selectIndex = self.selectIndex - 1
        else:
            self.selectIndex = 0
        if index != self.selectIndex:
            self.updateMenu()

    def navCW(self):
        index = self.selectIndex
        if self.selectIndex >= len(self.navList) - 1:
            self.selectIndex = len(self.navList) - 1
        else:
            self.selectIndex = self.selectIndex + 1
        if index != self.selectIndex:
            self.updateMenu()

    def getSelected(self):
        # Return selected String in the menu navigation list
        return self.navList[self.selectIndex]

    def _buildDisplay(self):
        self.displayItems = displayio.Group()
        # Nav menu will have three hard coded visible labels
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', scale=2,
                                             anchor_point=(0.0, 0.0), anchored_position=(2, 0),
                                             background_color=BLK, color=WHT, padding_left=2,
                                             padding_right=1))
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', scale=2,
                                             anchor_point=(0.0, 0.5), anchored_position=(2, 67),
                                             background_color=WHT, color=BLK, padding_left=2,
                                             padding_right=1))
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', scale=2,
                                             anchor_point=(0.0, 1.0), anchored_position=(2, 135),
                                             background_color=BLK, color=WHT, padding_left=2,
                                             padding_right=1))


class NewLog:
    def __init__(self, screenName, charCount=15, defaultColor_text=WHT, defaultColor_bg=BLK,
                 highlightColor_text=BLK, highlightColor_bg=WHT):
        self.screenName = screenName
        self.selectIndex = 3
        self.defaultColor_text = defaultColor_text
        self.defaultColor_bg = defaultColor_bg
        self.highlightColor_text = highlightColor_text
        self.highlightColor_bg = highlightColor_bg
        self.static_offset = 13
        self.charCount = charCount
        # Build menu display
        self.fileString = ''
        self._buildDisplay()
        self._updateNavHighlight()

    def _buildDisplay(self):
        self.displayItems = displayio.Group()
        # Insert the display string into the group first so it is always index 0
        """0"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=self.fileString + '.txt',
                                             scale=2, anchor_point=(0.5, 0.5), anchored_position=(120, 35),
                                             background_color=BLK, color=YEL))
        """1"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='File Name...',
                                             scale=2, anchor_point=(0.5, 0.5),
                                             background_color=BLK, color=GRY, anchored_position=(120, 10)))
        """2"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Edit->',
                                             scale=2, anchor_point=(1.0, 0.5),
                                             background_color=BLK, color=GRY, anchored_position=(100, 80)))
        """3"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='0',
                                             scale=2, anchor_point=(0.5, 0.5),
                                             background_color=GRY, color=BLK, anchored_position=(120, 80),
                                             padding_right=1, padding_left=2))
        """4"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='<-Bcksp',
                                             scale=2, anchor_point=(1.0, 0.5),
                                             background_color=GRY, color=BLK, anchored_position=(240, 80),
                                             padding_left=1))
        """5"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Save',
                                             scale=2, anchor_point=(1.0, 1.0),
                                             background_color=GRY, color=BLK, anchored_position=(240, 135),
                                             padding_left=1))
        """6"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Ins',
                                             scale=2, anchor_point=(0.5, 1.0),
                                             background_color=GRY, color=BLK, anchored_position=(120, 135),
                                             padding_left=1))
        """7"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Esc',
                                             scale=2, anchor_point=(0.0, 1.0),
                                             background_color=GRY, color=BLK, anchored_position=(2, 135),
                                             padding_left=2))

    def getDisplayGroup(self):
        # Function returns the DisplayGroup for the Board.Display.show() function
        return self.displayItems

    def navCW(self):
        if self.selectIndex >= len(self.displayItems) - 1:
            self.selectIndex = 3  # Loop back to first selectable item
        else:
            self.selectIndex = self.selectIndex + 1
        self._updateNavHighlight()

    def navCCW(self):
        if self.selectIndex > 3:
            self.selectIndex = self.selectIndex - 1
        else:
            self.selectIndex = 7  # Loop back to last selectable item
        self._updateNavHighlight()

    def _updateNavHighlight(self):
        for i in range(len(self.displayItems)):
            if i >= 3:
                self.displayItems[i].background_color = GRY
        self.displayItems[self.selectIndex].background_color = WHT

    def getNavItem(self):
        # Return the current highlighted navigation text
        return self.displayItems[self.selectIndex].text

    def getFileName(self):
        # Return the fileString with .txt appended
        return self.fileString + '.txt'

    def setEdit(self, flag):
        # selectIndex in this function should always be the character edit
        if flag:
            self.displayItems[self.selectIndex].background_color = GRN
        else:
            self._updateNavHighlight()

    def editCW(self):
        # function called when editing characters of the selected string encoder input CW
        # inverse selection index to count from right of string.
        newchar = self._charUpdate(self.displayItems[3].text, 1)
        self.displayItems[3].text = newchar
        self.displayItems[0].text = self.fileString + newchar + '.txt'

    def editCCW(self):
        newchar = self._charUpdate(self.displayItems[3].text, -1)
        self.displayItems[3].text = newchar
        self.displayItems[0].text = self.fileString + newchar + '.txt'

    def _charUpdate(self, character, step):
        # Return the next allowed ASII character
        num = ord(character) + step
        if num < 32:  # Wrap to a space
            num = 122
        elif 32 < num < 48:  # Skip ASCII characters 33 - 47
            num = 48 if step == 1 else 32
        elif 57 < num < 65:  # Skip ASCII characters 58 - 64
            num = 65 if step == 1 else 57
        elif 90 < num < 95:  # Skip ASCII characters 91 - 94
            num = 95 if step == 1 else 90
        elif 95 < num < 97:  # Skip ASCII characters 58 - 64
            num = 97 if step == 1 else 95
        elif num > 122:  # Wrap to a space
            num = 32
        return chr(num)

    def addChar(self):
        # fileString = str(self.displayItems[0].text).replace('.txt', '')
        fileString = self.fileString
        newchar = self._charUpdate(self.displayItems[3].text, 0)
        self.displayItems[0].text = fileString + newchar + '.txt'
        self.fileString = fileString + newchar
        print('Added Character...')

    def addStr(self, insert):
        fileString = str(self.displayItems[0].text).replace('.txt', '')
        self.displayItems[0].text = fileString + insert + '.txt'
        self.fileString = fileString + insert

    def subtractChar(self):
        fileString = str(self.displayItems[0].text).replace('.txt', '')[:-1]
        self.displayItems[0].text = fileString + '.txt'
        self.fileString = fileString

    def Debug(self, str):
        print(f'{self.__class__} - {str} called.')


class Config:
    def __init__(self, screenName, config, defaultColor_text=GRY, defaultColor_bg=BLK,
                 highlightColor_text=BLK, highlightColor_bg=WHT):
        self.screenName = screenName
        self._config = config  # Config should be dict passed of vales editable in this screen
        self.selectIndex = 0
        self.defaultColor_text = defaultColor_text
        self.defaultColor_bg = defaultColor_bg
        self.highlightColor_text = highlightColor_text
        self.highlightColor_bg = highlightColor_bg
        self.static_offset = 13
        # Build menu display
        self._buildDisplay()
        self._updateNavHighlight()

    def _buildDisplay(self):
        self.displayItems = displayio.Group()
        y = 5  # Top of screen start point
        _y = 22  # Spacing
        keys = list(sorted(self._config.keys()))
        self._address = {}
        # Build out the display text and graphics for initialization
        """0"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=keys[0],
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y),
                                             background_color=BLK, color=GRY, padding_left=1))
        """1"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self._config[keys[0]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[0].text] = 1
        """2"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=keys[1],
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 1)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        """3"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self._config[keys[1]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 1)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[2].text] = 3

        """4"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=keys[2],
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 2)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        """5"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self._config[keys[2]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 2)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[4].text] = 5

        """6"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=keys[3],
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 3)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        """7"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self._config[keys[3]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 3)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[6].text] = 7

        """8"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Cancel',
                                             scale=2, anchor_point=(0.5, 0.0), anchored_position=(120, y + (_y * 4)),
                                             background_color=BLK, color=RED, padding_left=0, padding_bottom=1))
        """9"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Press = Select || Hold = Save & Exit',
                                             scale=1, anchor_point=(0.5, 1.0), anchored_position=(120, 130),
                                             background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))

        self.selectableItems = len(self.displayItems) - 2  # get a length of the group list that is navigable
        self.helpLabelIndex = len(self.displayItems) - 1  # Get the index of the quick help label

    def _updateNavHighlight(self):
        # Reset all backgrounds to default
        for i in range(len(self.displayItems)):
            if i != self.helpLabelIndex:
                if self.displayItems[i].color != self.defaultColor_text:
                    self.displayItems[i].color = self.defaultColor_text
                    self.displayItems[i].background_color = self.defaultColor_bg
        # Highlight selected index menu item
        self.displayItems[self.selectIndex].color = self.highlightColor_text
        self.displayItems[self.selectIndex].background_color = self.highlightColor_bg

    def getDisplayGroup(self):
        # Function returns the DisplayGroup for the Board.Display.show() function
        return self.displayItems

    def navCCW(self):
        # navigate index by evens only
        if self.selectIndex >= self.selectableItems:
            self.selectIndex = 0  # Loop back to first selectable item
        else:
            self.selectIndex = self.selectIndex + 2
        self._updateNavHighlight()

    def navCW(self):
        # navigate index by evens only
        if self.selectIndex >= 2:
            self.selectIndex = self.selectIndex - 2
        else:
            self.selectIndex = self.selectableItems  # Loop back to last selectable item
        self._updateNavHighlight()

    def setEdit(self, flag):
        # selectIndex in this function should always be the character edit
        if flag:
            self.displayItems[self.selectIndex].background_color = GRY
            self.displayItems[self.selectIndex].color = GRN
            self.displayItems[self.selectIndex + 1].background_color = GRY
            self.displayItems[self.selectIndex + 1].color = GRN
            key = self.displayItems[self.selectIndex].text
            if key == 'Raw_Upr' or key == 'Raw_Lwr':
                self.displayItems[self.helpLabelIndex].text = 'Press = Save & Exit || Hold = Poll Sensor'
            else:
                self.displayItems[self.helpLabelIndex].text = 'Press = Save & Exit'

        else:
            self._updateNavHighlight()
            self.displayItems[self.helpLabelIndex].text = 'Press = Select || Hold = Save & Exit'

    def editCW(self):  # Function looks to selected option and increments on a fixed value
        key = self.displayItems[self.selectIndex].text
        if key == 'Eng_Upr' or key == 'Eng_Lwr':
            self._config[key] = self._config[key] + .125  # Engineering units increment by 1/8
        else:
            self._config[key] = self._config[key] + 1  # Raw units increment by 1

        self._updateDisplay(key)

    def editCCW(self):  # Function looks to selected option and increments on a fixed value
        key = self.displayItems[self.selectIndex].text
        if key == 'Eng_Upr' or key == 'Eng_Lwr':
            self._config[key] = self._config[key] - .125  # Engineering units increment by 1/8
        else:
            self._config[key] = self._config[key] - 1  # Raw units increment by 1

        self._updateDisplay(key)

    def recordVal(self, value):  # Function looks to selected option and records the sent value if valid
        key = self.displayItems[self.selectIndex].text
        if key == 'Raw_Upr' or key == 'Raw_Lwr':
            self._config[key] = value

        self._updateDisplay(key)

    def _updateDisplay(self, key):
        self.displayItems[self._address[key]].text = str(self._config[key])

    def getSelected(self):
        return self.displayItems[self.selectIndex].text

    @property
    def config(self):
        return self._config

    @config.setter
    def config(self, d):
        if not isinstance(d, dict):
            raise TypeError('passed data must be of type dictionary')
        for key in d:
            if self._config[key] != d[key]:
                self._config[key] = d[key]
                self._updateDisplay(key)


class Runtime:
    def __init__(self, screenName, defaultColor_text=YEL, defaultColor_bg=BLK,
                 highlightColor_text=BLK, highlightColor_bg=WHT):
        self.screenName = screenName
        """Static Definition for the dictionary displayed"""
        """Dictionaries return no particular order, declaring labels must be done statically"""
        self._items = {'Lat': '', 'Lon': '', 'File': 'example.txt', 'Row': 0, 'Rng': 0, 'Entry': 0, 'GPS': ''}
        """Address book for display items in order to access the displayGroups to update values"""
        self._address = {}  # Built dynamically in the screen config
        self.selectIndex = 6
        self.defaultColor_text = defaultColor_text
        self.defaultColor_bg = defaultColor_bg
        self.highlightColor_text = highlightColor_text
        self.highlightColor_bg = highlightColor_bg
        self.static_offset = 13  # spacing for display items
        # Build menu display
        self._buildDisplay()
        self._updateNavHighlight()

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, d):  # setter takes in dictionary and will update any valid keys
        for key in d:
            if key in self._items:
                if self._items[key] != d[key]:
                    self._items[key] = d[key]
                    # Use Address of display group item to find appropriate text to edit for the Key label
                    self.displayItems[self._address[key]].text = str(self._items[key])
            else:
                print(f'Key - "{key}" does not exist in the runtime screen.')
                raise KeyError

    def _buildDisplay(self):
        self.displayItems = displayio.Group()
        self._address = {}
        y = 5  # Top of screen start point
        _y = 22  # Spacing
        # Build out the display text and graphics for initialization
        """0"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='File:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y),
                                             background_color=BLK, color=WHT, padding_left=1))
        """1"""
        self.displayItems.append(
            label.Label(font=terminalio.FONT, text=str(self._items[self.displayItems[0].text[:-1]]),
                        scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y),
                        background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[0].text[:-1]] = 1

        """2"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Entry:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 1)),
                                             background_color=BLK, color=RED, padding_left=1, padding_bottom=1))
        """3"""
        self.displayItems.append(
            label.Label(font=terminalio.FONT, text=str(self._items[self.displayItems[2].text[:-1]]),
                        scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 1)),
                        background_color=BLK, color=RED, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[2].text[:-1]] = 3

        """4"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Row:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 2)),
                                             background_color=BLK, color=YEL, padding_left=1, padding_bottom=1))
        """5"""
        self.displayItems.append(
            label.Label(font=terminalio.FONT, text=str(self._items[self.displayItems[4].text[:-1]]),
                        scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 2)),
                        background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[4].text[:-1]] = 5
        """6"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Rng:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 3)),
                                             background_color=BLK, color=YEL, padding_left=1, padding_bottom=1))
        """7"""
        self.displayItems.append(
            label.Label(font=terminalio.FONT, text=str(self._items[self.displayItems[6].text[:-1]]),
                        scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 3)),
                        background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[6].text[:-1]] = 7
        """8"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='GPS:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 4)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        """9"""
        self.displayItems.append(
            label.Label(font=terminalio.FONT, text=str(self._items[self.displayItems[8].text[:-1]]),
                        scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 4)),
                        background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[8].text[:-1]] = 9
        """10"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Press = Select || Hold = Exit',
                                             scale=1, anchor_point=(0.5, 1.0), anchored_position=(120, 130),
                                             background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))

        self.selectableItems = (4, 8)  # tuple indicates selectable limits
        self.helpLabelIndex = len(self.displayItems) - 1  # Get the index of the quick help label

    def _updateNavHighlight(self):
        # Reset all backgrounds to default
        for i in range(len(self.displayItems)):
            if self.selectableItems[0] <= i <= self.selectableItems[1]:
                if self.displayItems[i].color != self.defaultColor_text:
                    self.displayItems[i].color = self.defaultColor_text
                    self.displayItems[i].background_color = self.defaultColor_bg
        # Highlight selected index menu item
        self.displayItems[self.selectIndex].color = self.highlightColor_text
        self.displayItems[self.selectIndex].background_color = self.highlightColor_bg

    def getDisplayGroup(self):
        # Function returns the DisplayGroup for the Board.Display.show() function
        return self.displayItems

    def getSelected(self):
        return self.displayItems[self.selectIndex].text[:-1]

    def navCCW(self):
        # navigate index by evens only
        if self.selectIndex >= self.selectableItems[1]:
            self.selectIndex = self.selectableItems[1]
        else:
            self.selectIndex = self.selectIndex + 2
        self._updateNavHighlight()

    def navCW(self):
        # navigate index by evens only
        if self.selectIndex <= self.selectableItems[0]:
            self.selectIndex = self.selectableItems[0]
        else:
            self.selectIndex = self.selectIndex - 2
        self._updateNavHighlight()

    def setEdit(self, flag):
        # Set the appropriate color schemes and labels for edit mode
        if flag:
            self.displayItems[self.selectIndex].background_color = GRY
            self.displayItems[self.selectIndex].color = GRN
            self.displayItems[self.selectIndex + 1].background_color = GRY
            self.displayItems[self.selectIndex + 1].color = GRN

            self.displayItems[self.helpLabelIndex].text = 'Press = Save & Exit'

        else:
            # Reset the appropriate color schemes to exit the edit mode
            self._updateNavHighlight()
            self.displayItems[self.helpLabelIndex].text = 'Press = Select || Hold = Exit'

    def editCW(self):
        key = self.displayItems[self.selectIndex].text[:-1]  # Ensure to strip ':' character from the label
        self._items[key] = self._items[key] + 1  # Raw units increment by 1

        self.displayItems[self.selectIndex + 1].text = str(self._items[key])

    def editCCW(self):
        key = self.displayItems[self.selectIndex].text[:-1]  # Ensure to strip ':' character from the label
        if self._items[key] >= 1:
            self._items[key] = self._items[key] - 1  # Raw units increment by 1

        self.displayItems[self.selectIndex + 1].text = str(self._items[key])


class GPSDetails:
    def __init__(self, screenName):
        self.screenName = screenName
        self.static_offset = 13  # spacing for display items
        self.items = {'Lat': '', 'Lon': '', 'Fix': '', 'Msg Count': 0, 'Time': ''}
        # Build menu display
        self._buildDisplay()

    def _buildDisplay(self):
        self.displayItems = displayio.Group()
        y = 5  # Top of screen start point
        _y = 22  # Spacing
        self._address = {}
        # Build out the display text and graphics for initialization
        """0"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Lat:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y),
                                             background_color=BLK, color=WHT, padding_left=1))
        """1"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self.items[self.displayItems[0].text[:-1]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[0].text[:-1]] = 1

        """2"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Lon:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 1)),
                                             background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))
        """3"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self.items[self.displayItems[2].text[:-1]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 1)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[2].text[:-1]] = 3

        """4"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Fix:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 2)),
                                             background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))
        """5"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self.items[self.displayItems[4].text[:-1]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 2)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[4].text[:-1]] = 5
        """6"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Msg Count:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 3)),
                                             background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))
        """7"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self.items[self.displayItems[6].text[:-1]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 3)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[6].text[:-1]] = 7
        """8"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Time:',
                                             scale=2, anchor_point=(0.0, 0.0), anchored_position=(2, y + (_y * 4)),
                                             background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))
        """9"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text=str(self.items[self.displayItems[8].text[:-1]]),
                                             scale=2, anchor_point=(1.0, 0.0), anchored_position=(238, y + (_y * 4)),
                                             background_color=BLK, color=GRY, padding_left=1, padding_bottom=1))
        self._address[self.displayItems[8].text[:-1]] = 9

        """10"""
        self.displayItems.append(label.Label(font=terminalio.FONT, text='Press = Exit',
                                             scale=1, anchor_point=(0.5, 1.0), anchored_position=(120, 130),
                                             background_color=BLK, color=WHT, padding_left=1, padding_bottom=1))

        self.selectableItems = [4, 8]  # tuple indicates selectable limits
        self.helpLabelIndex = len(self.displayItems) - 1  # Get the index of the quick help label

    def getDisplayGroup(self):
        # Function returns the DisplayGroup for the Board.Display.show() function
        return self.displayItems

    def updateDisplay(self, gps):
        if isinstance(gps, GPSParser):
            self.displayItems[self._address['Lat']].text = gps.latitude
            self.displayItems[self._address['Lon']].text = gps.longitude
            self.displayItems[self._address['Fix']].text = gps.fix_stat
            self.displayItems[self._address['Msg Count']].text = str(gps.parsed_sentences)
            self.displayItems[self._address['Time']].text = gps.timestamp[0] + ':' + gps.timestamp[1] + ':' + \
                                                            gps.timestamp[2]
        else:
            raise TypeError('Object type passed to screen must be type "GPSParser"')
