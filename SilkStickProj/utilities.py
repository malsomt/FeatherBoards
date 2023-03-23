import time


def printInline(mes):
    """ Print the message in line by prepending a return carriage and change the newline ending to nothing """
    return print('\r' + mes, end='')


class LogFile:
    def __init__(self):
        self._filepath = '/sd'
        self._fileName = ''
        self._datafields = ['yyyymmdd', 'hhmmss', 'Row', 'Rng', 'Lat', 'Lon']
        self._entryCount = 0

    @property
    def fileName(self):
        return self._fileName

    @fileName.setter
    def fileName(self, fn):  # setting new filename updates internal properties
        if self._checkFormat(fn):
            filename = self._filepath + '/' + fn
            self._fileName = fn
            self._entryCount = sum(1 for _ in open(filename)) - 1  # Grab number of entries in file
        else:
            raise ValueError(self._filepath + '/' + fn)

    def CreateNewFile(self, fn):
        if self._checkFormat(fn):
            filename = self._filepath + '/' + fn
            with open(filename, 'x') as file:
                header = ''
                for i in self._datafields:
                    header = header + i + ','
                file.write(header)
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
            logstring = info['ymd'] + ',' + info['hms'] + ',' + str(info['Row']) + ',' + str(info['Rng']) + ',' +\
                    info['Lat'] + ', ' + info['Lon'] + '\n'
            with open(self._filepath + '/' + self._fileName, 'a') as file:
                file.write(logstring)
        except OSError as oserr:  # Most likely no SD Card
            print(oserr)
            return False
        self._entryCount = self._entryCount + 1  # increment the entry count manually
        return True  # Return True if successful

    def removeLastEntry(self):
        """Attempt to remove the last line of the current csv file"""
        pass

    @property
    def entryCount(self):
        return self._entryCount


class Timer:
    """Create a PLC type timer resembling a TON function block from IEC 61131-3"""
    def __init__(self):
        self._EN = False  # enable
        self._DN = False  # done
        self._TT = False  # timer timing
        self._ACC = 0.0  # accumulated time
        self._PRE = 0
        self._start_time = 0.0
        self.__initialized = True

    def __call__(self, *args, **kwargs):
        self._scan(*args, **kwargs)
        self._EN = False  # cyclically reset EN for automatic reset

    def _scan(self):
        if self._EN and not self._DN:  # Is timer enabled
            self.__initialized = False
            if not self._TT:
                self._start_time = time.monotonic()
                self._TT = True
            self._ACC = time.monotonic() - self._start_time
            if self._ACC >= self._PRE:
                self._DN = True
                self._TT = False

        elif self._EN and self._DN:
            pass  # Do nothing to maintain info

        else:
            if not self.__initialized:
                self.__init__()  # reset all

    @property
    def EN(self):
        return self._EN

    @EN.setter
    def EN(self, flag):
        if isinstance(flag, bool):
            self._EN = flag
        else:
            raise TypeError("Timer 'EN' must be of type bool")

    @property
    def DN(self):
        return self._DN

    @property
    def TT(self):
        return self._TT

    @property
    def ACC(self):
        return self._ACC

    @property
    def PRE(self):
        return self._PRE

    @PRE.setter
    def PRE(self, pre):
        if isinstance(pre, int):
            self._PRE = float(pre)
        elif isinstance(pre, float):
            self._PRE = pre
        else:
            raise TypeError("PRE must be a float of seconds.")


class Scaling:
    def __init__(self):
        self._setup = {'Raw_Upr': 1000, 'Raw_Lwr': 0, 'Eng_Upr': 15, 'Eng_Lwr': 0}
        self._m = None
        self._b = None

    def __call__(self, *args, **kwargs):
        return self.scale(*args, **kwargs)

    def scale(self, x):
        # use y= mx + b
        # y = engineering unit
        # x = raw unit
        # m is scale/slope
        # b is eng unit offset
        # y = mx + b
        return float(self._m * x + self._b)

    def _solve(self):
        if self._m is None or self._b is None:
            try:
                # m = (y2 - y1)/(x2 - x1)
                self._m = (self._setup['eu_upr'] - self._setup['eu_lwr'])/(self._setup['raw_upr'] - self._setup['raw_lwr'])
                # b = y - mx
                self._b = self._setup['eu_lwr'] - (self._m * self._setup['raw_lwr'])

            except ZeroDivisionError or TypeError:
                return False

    @property
    def setup(self):
        return self._setup

    @setup.setter
    def setup(self, d):
        if not isinstance(d, dict):
            raise TypeError('Assigned value must be of type Dictionary')
        # setter takes in dictionary and will update any valid keys
        for key in d:
            if key in self._setup:
                if self._setup[key] != d[key]:
                    self._setup[key] = d[key]
            else:
                raise KeyError(f'Key - "{key}" does not exist the scaling configuration.')
        self._solve()  # Update scaling formula




