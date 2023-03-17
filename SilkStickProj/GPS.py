class GPSParser(object):
    """Most of this code is a stripped version of the microPyGPS library.
    In an order to streamline the size and speed of the library for running on the ESP32 M5 Stack device,
    functionality has been reduced and GPS coordinates will remain as ASCII strings due to the ESP32's Double precision
    float limits"""
    # Max Number of Characters a valid sentence can be (based on GGA sentence)
    SENTENCE_LIMIT = 90
    __HEMISPHERES = ('N', 'S', 'E', 'W')
    __NO_FIX = 1
    __FIX_2D = 2
    __FIX_3D = 3
    __DIRECTIONS = ('N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W',
                    'WNW', 'NW', 'NNW')
    __MONTHS = ('January', 'February', 'March', 'April', 'May',
                'June', 'July', 'August', 'September', 'October',
                'November', 'December')

    def __init__(self):
        #####################
        # Object Status Flags
        self.sentence_active = False
        self.active_segment = 0
        self.process_crc = False
        self.gps_segments = ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
        self.crc_xor = 0
        self.char_count = 0
        self.fix_time = 0

        #####################
        # Sentence Statistics
        self.crc_fails = 0
        self.clean_sentences = 0
        self.parsed_sentences = 0

        #####################
        # Data From Sentences
        # Time
        self._timestamp = ['', '', '']
        self._datestamp = ['', '', '']
        self.utc_string = ''

        # Position/Motion
        self._latitude = ['', '', '']
        self._longitude = ['', '', '']
        self.altitude = 0.0
        self.geoid_height = 0.0

        # GPS Info
        self.satellites_in_view = 0
        self.satellites_in_use = 0
        self.hdop = ''
        self.pdop = ''
        self.vdop = ''
        self.valid = False
        self.fix_stat = 0
        self.fix_type = 1

    @property
    def latitude(self):
        """Format Latitude Data Correctly"""
        """Return as ASCII string only due to ESP32 limit"""

        return self._latitude[0] + self._latitude[1] + self._latitude[2]

    @property
    def longitude(self):
        """Format Longitude Data Correctly"""
        """Return as ASCII string only due to ESP32 limit"""
        return self._longitude[0] + self._longitude[1] + self._longitude[2]

    @property
    def timestamp(self):
        """Hour, Min, Sec"""
        return self._timestamp

    @property
    def datestamp(self):
        """Day, Month , Year"""
        return self._datestamp

    @staticmethod
    def unsupported():
        return False

    def gpgga(self):
        """Parse Global Positioning System Fix Data (GGA) Sentence. Updates UTC timestamp, latitude, longitude,
        fix status, satellites in use, Horizontal Dilution of Precision (HDOP), altitude, geoid height and fix status"""

        try:
            # UTC Timestamp
            utc_string = self.gps_segments[1]

            # Skip timestamp if receiver doesn't have one yet
            if utc_string:
                hours = (str(utc_string[0:2]))
                minutes = str(utc_string[2:4])
                seconds = str(utc_string[4:])
            else:
                hours = '0'
                minutes = '0'
                seconds = '0.0'

            # Number of Satellites in Use
            satellites_in_use = int(self.gps_segments[7])

            # Get Fix Status
            fix_stat = int(self.gps_segments[6])

        except (ValueError, IndexError):
            return False

        try:
            # Horizontal Dilution of Precision
            hdop = str(self.gps_segments[8])
        except (ValueError, IndexError):
            hdop = ''

        # Process Location and Speed Data if Fix is GOOD
        if fix_stat:

            # Longitude / Latitude
            try:
                # Latitude
                l_string = self.gps_segments[2]
                lat_degs = l_string[0:2]
                lat_mins = l_string[2:]
                lat_hemi = self.gps_segments[3]

                # Longitude
                l_string = self.gps_segments[4]
                lon_degs = l_string[0:3]
                lon_mins = l_string[3:]
                lon_hemi = self.gps_segments[5]
            except ValueError:
                return False

            if lat_hemi not in self.__HEMISPHERES:
                return False

            if lon_hemi not in self.__HEMISPHERES:
                return False

            # Altitude / Height Above Geoid
            try:
                altitude = self.gps_segments[9]
                geoid_height = self.gps_segments[11]
            except ValueError:
                altitude = 0
                geoid_height = 0

            # Update Object Data
            self._latitude = [lat_degs, lat_mins, lat_hemi]
            self._longitude = [lon_degs, lon_mins, lon_hemi]
            self.altitude = altitude
            self.geoid_height = geoid_height

        # Update Object Data
        self._timestamp = [hours, minutes, seconds]
        self.satellites_in_use = satellites_in_use
        self.hdop = hdop
        self.fix_stat = fix_stat
        return True

    def gpzda(self):
        try:
            # UTC Timestamp
            utc_string = self.gps_segments[1]

            # Skip timestamp if receiver doesn't have one yet
            if utc_string:
                hours = (str(utc_string[0:2]))
                minutes = str(utc_string[2:4])
                seconds = str(utc_string[4:])
            else:
                hours = '0'
                minutes = '0'
                seconds = '0.0'

            day = self.gps_segments[2]
            month = self.gps_segments[3]
            year = self.gps_segments[4]

        except (ValueError, IndexError):
            print('Failed to Parse ZDA')
            return False

        self._timestamp = [hours, minutes, seconds]
        self._datestamp = [day, month, year]
        return True

    def new_sentence(self):
        """Adjust Object Flags in Preparation for a New Sentence"""
        self.gps_segments = ['', '', '', '', '', '', '', '', '', '', '', '', '', '', '']
        self.active_segment = 0
        self.crc_xor = 0
        self.sentence_active = True
        self.process_crc = True
        self.char_count = 0

    def update(self, new_char):
        """Process a new input char and updates GPS object if necessary based on special characters ('$', ',', '*')
        Function builds a list of received string that are validated by CRC prior to parsing by the appropriate
        sentence function. Returns sentence type on successful parse, None otherwise"""

        valid_sentence = False

        # Validate new_char is a printable char
        ascii_char = ord(new_char)

        if 10 <= ascii_char <= 126:
            self.char_count += 1
            # Check if a new string is starting ($)
            if new_char == '$':
                self.new_sentence()
                return None

            elif self.sentence_active:

                # Check if sentence is ending (*)
                if new_char == '*':
                    self.process_crc = False
                    self.active_segment += 1
                    # self.gps_segments.append('')
                    return None

                # Check if a section is ended (,), Create a new substring to feed
                # characters to
                elif new_char == ',':
                    self.active_segment += 1
                    self.gps_segments.append('')

                # Store All Other printable character and check CRC when ready
                else:
                    self.gps_segments[self.active_segment] += str(new_char)

                    # When CRC input is disabled, sentence is nearly complete
                    if not self.process_crc:

                        if len(self.gps_segments[self.active_segment]) == 2:
                            try:
                                final_crc = int(self.gps_segments[self.active_segment], 16)
                                if self.crc_xor == final_crc:
                                    valid_sentence = True
                                else:
                                    self.crc_fails += 1
                            except ValueError:
                                pass  # CRC Value was deformed and could not have been correct

                # Update CRC
                if self.process_crc:
                    self.crc_xor ^= ascii_char

                # If a Valid Sentence Was received and it's a supported sentence, then parse it!!
                if valid_sentence:
                    self.sentence_active = False  # Clear Active Processing Flag

                    if self.gps_segments[0] in self.supported_sentences:

                        # parse the Sentence Based on the message type, return True if parse is clean
                        if self.supported_sentences[self.gps_segments[0]](self):
                            # Let host know that the GPS object was updated by returning parsed sentence type
                            self.parsed_sentences += 1
                            return self.gps_segments[0]

                # Check that the sentence buffer isn't filling up with Garbage waiting for the sentence to complete
                if self.char_count > self.SENTENCE_LIMIT:
                    self.sentence_active = False
        # Tell Host no new sentence was parsed
        return None

    supported_sentences = {'GPRMC': unsupported, 'GLRMC': unsupported,
                           'GPGGA': gpgga, 'GLGGA': gpgga,
                           'GPVTG': unsupported, 'GLVTG': unsupported,
                           'GPGSA': unsupported, 'GLGSA': unsupported,
                           'GPGSV': unsupported, 'GLGSV': unsupported,
                           'GPGLL': unsupported, 'GLGLL': unsupported,
                           'GNGGA': gpgga, 'GNRMC': unsupported,
                           'GNVTG': unsupported, 'GNGLL': unsupported,
                           'GNGSA': unsupported, 'GNZDA': gpzda,
                           'GPZDA': gpzda, 'GLZDA': gpzda
                           }
