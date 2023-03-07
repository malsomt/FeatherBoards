class LogFile:
    def __init__(self):
        self._filepath = '/sd'
        self._fileName = ''
        self._datafields = ['yyyymmdd', 'hhmmss', 'Row', 'Rng', 'Lat', 'Lon']
        self.entrycount = 0

    @property
    def fileName(self):
        return self._fileName

    @fileName.setter
    def fileName(self, fn):  # setting new filename updates internal properties
        if self._checkFormat(fn):
            filename = self._filepath + '/' + fn
            self._fileName = fn
            self.entrycount = sum(1 for _ in open(filename)) - 1  # Grab number of entries in file

    def CreateNewFile(self, fn):
        if self._checkFormat(fn):
            filename = self._filepath + '/' + fn
            try:
                with open(filename) as file:
                    for i in self._datafields:
                        header = header + i + ','
                    file.write(header)
            except Exception as err:
                print(err)
                return False
            self.fileName = fn
            return True
        else:
            return False

    @staticmethod
    def _checkFormat(fn):
        if len(fn.split('.')) == 2 and fn.split('.')[1] == 'txt':  # ensure filename is format 'abcdefg.txt'
            return True
        else:
            return False

    def addEntry(self, info):
        """Receive Dictionary of log information and format it to a CSV"""
        try:
            logstring = info['ymd'] + ',' + info['hms'] + ',' + info['Row'] + ',' + info['Rng'] + ',' + \
                        info['Lat'] + ', ' + info['Lon']
            with open(self._filepath + '/' + self._fileName, 'a') as file:
                file.write(logstring)
        except OSError as oserr:  # Most likely no SD Card
            print(oserr)
            return False
        self.entrycount = self.entrycount + 1  # increment the entry count manually
        return True  # Return True if successful

    def removeLastEntry(self):
        """Attempt to remove the last line of the current csv file"""
        pass

