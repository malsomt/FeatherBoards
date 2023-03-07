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
            except Exception:
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
