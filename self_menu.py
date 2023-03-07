import terminalio
from adafruit_display_text import label
import displayio

WHITE = 0xFFFFFF
BLACK = 0x000000

'''Concept of the Menu Navigation screen is as follows.
---Use the navUp and Dwn functions to increment the displayed menu items
---The displayed labels are hard coded to only show three items at a time with the center label representing the active selection.
---To build the menu list, pass a list of strings into the class on instantiation that will be used to display as navigation items and find the other screens
'''


class MenuScreen:
    def __init__(self, screenName, navList, selectIndex=0, defaultTextColor=WHITE, defaultBackgroundColor=BLACK):
        self.screenName = screenName
        self.navList = navList
        self.selectIndex = selectIndex
        self.defaultTextColor = defaultTextColor
        self.defaultBackgroundColor = defaultBackgroundColor
        # Build menu display
        self._buildMenuDisplay()
        self.updateMenu()

    def getDisplayGroup(self):
        # Function returns the DisplayGroup for the Board.Display.show() function
        return self.displayItems

    def updateMenu(self):
        self.displayItems[0].text = self.navList[self.selectIndex-1] if self.selectIndex != 0 else ''
        self.displayItems[1].text = self.navList[self.selectIndex]
        self.displayItems[2].text = self.navList[self.selectIndex + 1] if self.selectIndex <= len(self.navList) -2 else ''

    def navUp(self):
        if self.selectIndex > 0:
            self.selectIndex = self.selectIndex - 1
        else:
            self.selectIndex = 0

    def navDwn(self):
        if self.selectIndex >= len(self.navList) - 1:
            self.selectIndex = len(self.navList) - 1
        else:
            self.selectIndex = self.selectIndex + 1

    def _buildMenuDisplay(self):
        self.displayItems = displayio.Group()
        # Nav menu will have three hard coded visible labels
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', x=0, y=10, scale=2))
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', x=0, y=20, scale=3))
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', x=0, y=30, scale=2))


"""       
class ValueMenuScreen(MenuScreen):
    def __init__(self, screenName, navList):
        super().__init__(screenName, navList)

    def _buildMenuDisplay(self):
        self.displayItems = displayio.Group()
        # Nav menu will have three hard coded visible labels
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', x=0, y=10, scale=2))
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', x=0, y=20, scale=3))
        self.displayItems.append(label.Label(font=terminalio.FONT, text='', x=0, y=30, scale=2))
        
        
"""