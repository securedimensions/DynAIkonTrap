# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2021 Miklas Riechmann

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from typing import Dict, Tuple, Type, Union
from math import cos, pi

import DynAIkonTrap.sensor as sensor
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.ursense.structure import ursense_map, reading_type_map


logger = get_logger(__name__)

EARTH_CIRCUMFERENCE_KM = 40000
EPSILON = 1e-5
TAU = 2 * pi


def _deg_to_rad(x: float) -> float:
    return (x * TAU) / 360


def _rad_to_deg(x: float) -> float:
    return (x * 360) / TAU


class UrSenseParser:
    """Parse the textual response from a UrSense board

    Some of the returned results may be sensitive information, such as the GPS location. Functionality is provided to provide a quantised version of the GPS position so exact position cannot be determined. It is the user's responsibility not to publish raw sensor data that may lead to leakage of sensitive information.
    """

    def __init__(self, obfuscation_distance_km: float = 2):
        """
        Args:
            obfuscation_distance_km (float): Dimension of squares for quantising GPS location
        """
        self._obfuscation_distance_km = obfuscation_distance_km
        self._init_lat_rad = None
        self._init_lon_rad = None

    def _quantise_gps(
        self,
        lat: "sensor.Reading",
        lon: "sensor.Reading",
    ) -> "Tuple[sensor.Reading, sensor.Reading]":
        if self._obfuscation_distance_km == 0:
            return (lat, lon)

        # Cap obfuscation distance to EARTH_CIRCUMFERENCE_KM / 8 to avoid strange and
        # unexpected things happening. We are saying at this point the user has simply
        # asked for "large" obfuscation
        _obfuscation_distance_km = (
            self._obfuscation_distance_km
            if self._obfuscation_distance_km < EARTH_CIRCUMFERENCE_KM / 8
            else EARTH_CIRCUMFERENCE_KM / 8
        )

        lat_rad = _deg_to_rad(lat.value * (1 if lat.units == "N" else -1))
        lon_rad = _deg_to_rad(lon.value * (1 if lon.units == "E" else -1))

        yquant = _obfuscation_distance_km / EARTH_CIRCUMFERENCE_KM
        if yquant < 1e-3 / EARTH_CIRCUMFERENCE_KM:
            # i.e.,  obfuscation distance of less than 1mm and divide by 0 check
            latqu = lat_rad
        else:
            latqu = round(lat_rad / (yquant * TAU)) * yquant * TAU

        xquant = _obfuscation_distance_km / (
            cos(latqu) * EARTH_CIRCUMFERENCE_KM + EPSILON
        )
        if xquant < 1e-3 / EARTH_CIRCUMFERENCE_KM:
            # i.e.,  obfuscation distance of less than 1mm and divide by 0 check
            lonqu = lon_rad
        else:
            lonqu = round(lon_rad / (xquant * TAU)) * xquant * TAU

        ## Make sure everything is still in range
        # latitude [-tau/4, tau/4]
        if latqu > TAU / 4:
            latqu = TAU / 4
        elif latqu < -TAU / 4:
            latqu = -TAU / 4

        # longitude [-tau/2, tau/2)
        if lonqu >= TAU / 2:
            lonqu -= TAU
        elif lonqu < -TAU / 2:
            lonqu += TAU

        return (
            sensor.Reading(_rad_to_deg(abs(latqu)), "N" if latqu >= 0 else "S"),
            sensor.Reading(_rad_to_deg(abs(lonqu)), "E" if lonqu >= 0 else "W"),
        )

    def parse(self, data: str) -> "Union[Dict[str, sensor.Reading], Type[None]]":
        """Parse the serial results output by a urSense 1.28 board as specified in the `user documentation v1.21 <https://gitlab.dynaikon.com/dynaikontrap/urSense/-/raw/5390d8a6e14e6b6ba625061637ba8d1961a15d2d/ursense-user-manual-v1.pdf>`_.

        The methodology is to start with a list of fields. Then process the first element of the list to figure out what type of reading it is and how many fields to consume. Format this appropriately and return it as a :class:`~Reading`. Repeat the process with the processed fields removed from the front of the list. Once the list reaches a length of zero, precessing the line is complete. For each :class:`~Reading` an attribute -- specified by the :data:`~DynAIkonTrap.ursense.structure.ursense_map` -- of the final :class:`~DynAIkonTrap.sensor.SensorLog` is set.

        Args:
            data (str): The serial data output from the urSense board
        Returns:
            Union[SensorLog, Type[None]]: The current data as a :class:`~DynAIkonTrap.sensor.SensorLog` or ``None`` if the input could not be parsed.
        """

        fields = data.strip().split(" ")

        ## Preamble
        if not fields[0].startswith("sel"):
            # This happens on start-up
            return None

        fields = fields[4:]

        ## Sensor readings
        sensor_log = {}
        if len(fields) <= 4:
            logger.debug("Sensor responded with no readings")
            return None

        while len(fields) > 0:
            field_info = ursense_map.get(fields[0])
            if field_info == None:
                # Check if weekday or latitude
                if fields[0] in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]:
                    # Time parsing
                    reading = sensor.Reading(" ".join(fields[:4]))
                    sensor_log["GPS_TIME"] = reading
                    fields = fields[4:]

                elif fields[0].endswith(("S", "N")):
                    # Position parsing
                    lat = fields[0]
                    lon = fields[1]

                    lat = sensor.Reading(float(lat[:-1]), lat[-1])
                    lon = sensor.Reading(float(lon[:-1]), lon[-1])

                    latq, lonq = self._quantise_gps(lat, lon)

                    sensor_log["GPS_POSITION_LATITUDE_RAW"] = lat
                    sensor_log["GPS_POSITION_LONGITUDE_RAW"] = lon
                    sensor_log["GPS_POSITION_LATITUDE_QUANTISED"] = latq
                    sensor_log["GPS_POSITION_LONGITUDE_QUANTISED"] = lonq
                    fields = fields[2:]

                else:
                    logger.warning("Unknown sensor field: `{}`".format(fields[0]))
                    fields = fields[1:]
                continue

            # Standard field
            parse_result = reading_type_map[field_info["reading_type"]]["parser"](
                fields
            )
            sensor_log[field_info["var_name"]] = parse_result.reading
            fields = parse_result.remaining_fields

        return sensor_log
