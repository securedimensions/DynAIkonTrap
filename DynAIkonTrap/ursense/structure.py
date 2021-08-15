# DynAIkonTrap is an AI-infused camera trapping software package.
# Copyright (C) 2021 Stefan Rüger, Miklas Riechmann

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

from dataclasses import dataclass
from typing import Callable, Dict, List, Union
import DynAIkonTrap.sensor as sensor

ursense_map = {
    'usid': {
        'reading_type': 'HX',
        'units': '',
        'var_name': 'UNIQUE_ID',
        'description': '48 bit unique id [hex]',
    },
    'c-id': {
        'reading_type': 'HX',
        'units': '',
        'var_name': 'CONFIG_ID',
        'description': 'config id [hex] or board id or serial no (24 bit)',
    },
    'meid': {
        'reading_type': 'UN',
        'units': '',
        'var_name': 'MEASUREMENT_ID',
        'description': 'measurement id [u] 0, 1, 2, ... (24 bit)',
    },
    'uptm': {
        'reading_type': 'DY',
        'units': '',
        'var_name': 'UPTIME',
        'description': 'uptime [d] in h (sensor uptime), given as <n>d<hh>, eg, 132d03',
    },
    'loof': {
        'reading_type': 'SI',
        'units': 'Hz',
        'var_name': 'LOOP_FREQUENCY',
        'description': 'loop frequency [Hz]',
    },
    'cpuf': {
        'reading_type': 'SI',
        'units': 'Hz',
        'var_name': 'CPU_FREQUENCY',
        'description': 'CPU frequency [Hz]',
    },
    'irqf': {
        'reading_type': 'SI',
        'units': 'Hz',
        'var_name': 'IRQ_FREQUENCY',
        'description': 'IRQ frequency [Hz]',
    },
    'meaf': {
        'reading_type': 'SI',
        'units': 'Hz',
        'var_name': 'MEASUREMENT_FREQUENCY',
        'description': 'measurement frequency [Hz]',
    },
    'irqd': {
        'reading_type': 'FX',
        'units': 'us',
        'var_name': 'IRQ_DURATION',
        'description': 'IRQ duration [us]',
    },
    'mead': {
        'reading_type': 'FX',
        'units': 'us',
        'var_name': 'MEASUREMENT_DURATION',
        'description': 'measurement duration [us]',
    },
    'codd': {
        'reading_type': 'FX',
        'units': 'us',
        'var_name': 'CODE_DURATION',
        'description': 'code duration [us]',
    },
    'vbat': {
        'reading_type': 'FX',
        'units': 'V',
        'var_name': 'BATTERY_VOLTAGE',
        'description': 'battery voltage [V]',
    },
    'v-cc': {
        'reading_type': 'FX',
        'units': 'V',
        'var_name': 'VCC',
        'description': 'Vcc [V]',
    },
    'atpr': {
        'reading_type': 'FX',
        'units': 'mbar',
        'var_name': 'RAW_ATMOSPHERIC_PRESSURE',
        'description': 'raw atmospheric pressure [mbar], needs converting to pressure at sea level for weather report values',
    },
    'humi': {
        'reading_type': 'PC',
        'units': '%',
        'var_name': 'HUMIDITY',
        'description': 'humidity [%] in [0, 100%]',
    },
    'brig': {
        'reading_type': 'PC',
        'units': '%',
        'var_name': 'BRIGHTNESS',
        'description': 'brightness [%] in [0, 100%]',
    },
    'pirs': {
        'reading_type': 'EE',
        'units': '',
        'var_name': 'PIR',
        'description': 'PIR sensors [edge] 2 bit printed per sensor: 00 (no movement), 11 (movement), 10 (just no longer moving), 01 (just triggered)',
    },
    'door': {
        'reading_type': 'EE',
        'units': '',
        'var_name': 'DOOR',
        'description': 'door sensors [edge] 2 bit printed per sensor: 00 (closed), 11 (open), 10 (closing), 01 (opening)',
    },
    'wndw': {
        'reading_type': 'EE',
        'units': '',
        'var_name': 'WINDOW',
        'description': 'window sensors [edge] 2 bit printed per sensor: 00 (closed), 11 (open), 10 (closing), 01 (opening)',
    },
    'swit': {
        'reading_type': 'EE',
        'units': '',
        'var_name': 'SWITCH',
        'description': 'switch sensors [edge] 2 bit printed per sensor: 00 (off), 11 (on), 10 (switching off), 01 (switching on)',
    },
    'lght': {
        'reading_type': 'EE',
        'units': '',
        'var_name': 'LIGHT',
        'description': 'light sensors [edge] 2 bit printed per sensor: 00 (off), 11 (on), 10 (switching off), 01 (switching on)',
    },
    'sckt': {
        'reading_type': 'EE',
        'units': '',
        'var_name': 'SOCKET',
        'description': 'socket sensors [edge] 2 bit printed per sensor: 00 (unused), 11 (used), 10 (stopping use), 01 (starting use)',
    },
    'rain': {
        'reading_type': 'FX',
        'units': 'mm',
        'var_name': 'RAINFALL',
        'description': 'rainfall [mm]',
    },
    'rair': {
        'reading_type': 'FX',
        'units': 'mm/h',
        'var_name': 'RAINFALL_RATE',
        'description': 'rainfall rate [mm/h]',
    },
    'snow': {
        'reading_type': 'FX',
        'units': 'mm',
        'var_name': 'SNOWFALL',
        'description': 'snowfall [mm]',
    },
    'snor': {
        'reading_type': 'FX',
        'units': 'mm/h',
        'var_name': 'SNOWFALL_RATE',
        'description': 'snowfall rate [mm/h]',
    },
    'vflw': {
        'reading_type': 'FX',
        'units': 'l/s',
        'var_name': 'WATERFLOW',
        'description': 'waterflow [l/s] rivers and streams',
    },
    'mflw': {
        'reading_type': 'FX',
        'units': 'kg/s',
        'var_name': 'MASSFLOW',
        'description': 'massflow [kg/s] compressible gasses',
    },
    'wtdp': {
        'reading_type': 'FX',
        'units': 'm',
        'var_name': 'WATERDEPTH',
        'description': 'water depth [m] wells and rain collectors',
    },
    'tidp': {
        'reading_type': 'FX',
        'units': 'm',
        'var_name': 'TIDEDEPTH',
        'description': 'tide depth [m]',
    },
    'soil': {
        'reading_type': 'PC',
        'units': '%',
        'var_name': 'SOIL_MOISTURE',
        'description': 'soil moisture [%] in [0, 100%]',
    },
    'leaf': {
        'reading_type': 'BB',
        'units': '',
        'var_name': 'LEAF_WETNESS',
        'description': 'leaf wetness [binary] 1 bit printed per sensor: either 0 (leaf dry) or 1 (leaf wet)',
    },
    'lfdu': {
        'reading_type': 'PC',
        'units': '%',
        'var_name': 'LEAF_WETNESS_DURATION',
        'description': 'leaf wetness duration [%] proportion of a day the leaf is wet',
    },
    'dirr': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'DIRECTION',
        'description': 'direction [rad] in [0, TAU): N=0, E=TAU/4, S=TAU/2, W=3TAU/4',
    },
    'dirt': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'DIRECTION_TURNS',
        'description': 'direction [turns] in [0,1): N=0, E=1/4, S=1/2, W=3/4',
    },
    'wspd': {
        'reading_type': 'FX',
        'units': 'm/s',
        'var_name': 'WIND_SPEED',
        'description': 'wind speed [m/s]',
    },
    'clcv': {
        'reading_type': 'PC',
        'units': '%',
        'var_name': 'CLOUD_COVER',
        'description': 'cloud cover [%] in [0, 100%], sky obstructed from view = 100%',
    },
    'clht': {
        'reading_type': 'FX',
        'units': 'm',
        'var_name': 'CLOUD_HEIGHT',
        'description': 'cloud height [m]',
    },
    'lcol': {
        'reading_type': 'HX',
        'units': '',
        'var_name': 'LIGHT_COLOUR',
        'description': 'light colour [hex, RRGGBB]',
    },
    'solr': {
        'reading_type': 'FX',
        'units': 'W/m^2',
        'var_name': 'SOLAR_RADIATION',
        'description': 'solar radiation [W/m^2] typ maximum of 1000 W/m^2',
    },
    'soli': {
        'reading_type': 'FX',
        'units': 'psh',
        'var_name': 'SOLAR_INSOLATION',
        'description': 'solar insolation [psh] in kWh/m^2/day aka peak sun hours = num of hours at 1000 W/m^2',
    },
    'uvrd': {
        'reading_type': 'FX',
        'units': 'W/m^2',
        'var_name': 'UV_RADIATION',
        'description': 'UV radiation [W/m^2] typ midday summer value is 250 mW/m^2',
    },
    'uvin': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'UV_INDEX',
        'description': 'UV index [n] in [0, 20] = UV radiation/(25 mW/m^2), typ midday summer max 10',
    },
    'irrd': {
        'reading_type': 'FX',
        'units': 'W/m^2',
        'var_name': 'INFRARED',
        'description': 'infrared [W/m^2]',
    },
    'rdcm': {
        'reading_type': 'FX',
        'units': 'cpm',
        'var_name': 'RADIOACTIVITY_CPM',
        'description': 'radioactivity cpm [cpm] in counts per minute',
    },
    'rdrd': {
        'reading_type': 'FX',
        'units': 'uSv/h',
        'var_name': 'RADIOACTIVE_RADIATION',
        'description': 'radioactive radiation [uSv/h] background radiation is 0.081 uSv/h',
    },
    'seis': {
        'reading_type': 'PC',
        'units': '%',
        'var_name': 'SEISMIC_ACTIVITY',
        'description': 'seismic activity [%] in [0, 100%) uncalibrated sensor output',
    },
    'rich': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'RICHTER_SCALE',
        'description': 'Richter scale [n] in [0, 10+) no strict upper limit',
    },
    'acet': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'ACETONE',
        'description': 'acetone [G]',
    },
    'airq': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'AIR_QUALITY',
        'description': 'air quality [G]',
    },
    'alco': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'ALCOHOL',
        'description': 'alcohol [G]',
    },
    'ammo': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'AMMONIA',
        'description': 'ammonia [G]',
    },
    'bnze': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'BENZENE',
        'description': 'benzene [G]',
    },
    'bnzi': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'BENZINE',
        'description': 'benzine [G]',
    },
    'buta': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'BUTANE',
        'description': 'butane [G]',
    },
    'co2-': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'CARBON_DIOXIDE',
        'description': 'carbon dioxide [G]',
    },
    'co--': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'CARBON_MONOXIDE',
        'description': 'carbon monoxide [G]',
    },
    'coal': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'COAL_GAS',
        'description': 'coal gas [G]',
    },
    'comb': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'COMBUSTIBLE_GASSES',
        'description': 'combustible gasses [G]',
    },
    'cng-': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'COMPRESSED_NATURAL_GAS',
        'description': 'compressed natural gas (CNG) [G]',
    },
    'etha': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'ETHANOL',
        'description': 'ethanol [G]',
    },
    'flam': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'FLAMMABLE_GASSES',
        'description': 'flammable gasses [G]',
    },
    'form': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'FORMALDEHYDE_GAS',
        'description': 'formaldehyde gas [G]',
    },
    'h2--': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'HYDROGEN_GAS',
        'description': 'hydrogen gas [G]',
    },
    'h2s-': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'HYDROGEN_SULFIDE_GAS',
        'description': 'hydrogen sulfide gas [G]',
    },
    'lpg-': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'LIQUEFIED_PETROLEUM_GAS',
        'description': 'liquefied petroleum gas (LPG) [G]',
    },
    'meth': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'METHANE',
        'description': 'methane [G]',
    },
    'natg': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'NATURAL_GAS',
        'description': 'natural gas [G]',
    },
    'ozon': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'OZONE',
        'description': 'ozone [G]',
    },
    'prop': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'PROPANE',
        'description': 'propane [G]',
    },
    'smok': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'SMOKE',
        'description': 'smoke [G]',
    },
    'tolu': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'TOLUENE',
        'description': 'toluene [G]',
    },
    'mq-2': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ2',
        'description': 'mq2 [G] methane, butane, LPG, smoke',
    },
    'mq-3': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ3',
        'description': 'mq3 [G] alcohol, ethanol, smoke',
    },
    'mq-4': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ4',
        'description': 'mq4 [G] methane, CNG',
    },
    'mq-5': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ5',
        'description': 'mq5 [G] natural gas, LPG',
    },
    'mq-6': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ6',
        'description': 'mq6 [G] LPG, butane',
    },
    'mq-7': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ7',
        'description': 'mq7 [G] carbon monoxide',
    },
    'mq-8': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ8',
        'description': 'mq8 [G] hydrogen gas',
    },
    'mq-9': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ9',
        'description': 'mq9 [G] carbon monoxide, flammable gasses',
    },
    'q131': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ131',
        'description': 'mq131 [G] ozone',
    },
    'q135': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ135',
        'description': 'mq135 [G] air quality',
    },
    'q136': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ136',
        'description': 'mq136 [G] hydrogen sulfide gas',
    },
    'q137': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ137',
        'description': 'mq137 [G] ammonia',
    },
    'q138': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ138',
        'description': 'mq138 [G] benzene, toluene, alcohol, acetone, propane, formaldehyde, hydrogen gas',
    },
    'q214': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ214',
        'description': 'mq214 [G] methane, natural gas',
    },
    'q216': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MQ216',
        'description': 'mq216 [G] natural gas, coal gas',
    },
    'g811': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'MG811',
        'description': 'mg811 [G] carbon dioxide',
    },
    'q104': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'AQ104',
        'description': 'aq104 [G] air quality',
    },
    'aq-2': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'AQ2',
        'description': 'aq2 [G] flammable gasses, smoke',
    },
    'aq-3': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'AQ3',
        'description': 'aq3 [G] alcohol, benzine',
    },
    'aq-7': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'AQ7',
        'description': 'aq7 [G] carbon monoxide',
    },
    'gsu0': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'GAS_USER_TYPE0',
        'description': 'gas user type0 [G]',
    },
    'gsu1': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'GAS_USER_TYPE1',
        'description': 'gas user type1 [G]',
    },
    'gsu2': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'GAS_USER_TYPE2',
        'description': 'gas user type2 [G]',
    },
    'gsu3': {
        'reading_type': 'GS',
        'units': '(%|ppt|ppm|ppb)',
        'var_name': 'GAS_USER_TYPE3',
        'description': 'gas user type3 [G]',
    },
    'trxt': {
        'reading_type': 'HR',
        'units': '',
        'var_name': 'TIMESINCE_RXT',
        'description': '[h] time since last successful reception of external time printed as <n>h<mm>, eg, 0h12',
    },
    'tgns': {
        'reading_type': 'HR',
        'units': '',
        'var_name': 'TIMESINCE_GNSS',
        'description': '[h] time since last successful reception of GNSS time printed as <n>h<mm>, eg, 4h19',
    },
    'tdcf': {
        'reading_type': 'HR',
        'units': '',
        'var_name': 'TIMESINCE_DCF',
        'description': '[h] time since last successful reception of radio time printed as <n>h<mm>, eg, 0h31',
    },
    'dcfs': {
        'reading_type': 'HX',
        'units': '',
        'var_name': 'DCF_STATUS',
        'description': 'DCF77 last status [hex]',
    },
    'tnsc': {
        'reading_type': 'UN',
        'units': '',
        'var_name': 'TIME_NUM_SET_CLOCK',
        'description': 'number of setClock() calls [u] (24 bit)',
    },
    'tnad': {
        'reading_type': 'UN',
        'units': '',
        'var_name': 'TIME_NUM_ADJUSTMENTS',
        'description': 'number of clock speed adjustments [u] (24 bit)',
    },
    'leng': {
        'reading_type': 'SI',
        'units': 'm',
        'var_name': 'LENGTH',
        'description': 'length [m]',
    },
    'mass': {
        'reading_type': 'FX',
        'units': 'kg',
        'var_name': 'MASS',
        'description': 'mass [kg]',
    },
    'tmpk': {
        'reading_type': 'FX',
        'units': 'K',
        'var_name': 'TEMPERATURE_K',
        'description': 'temperature [K]',
    },
    'amnt': {
        'reading_type': 'SI',
        'units': 'mol',
        'var_name': 'AMOUNT',
        'description': 'amount [mol]',
    },
    'area': {
        'reading_type': 'FX',
        'units': 'm^2',
        'var_name': 'AREA',
        'description': 'area [m^2]',
    },
    'volu': {
        'reading_type': 'FX',
        'units': 'm^3',
        'var_name': 'VOLUME',
        'description': 'volume [m^3]',
    },
    'freq': {
        'reading_type': 'SI',
        'units': 'Hz',
        'var_name': 'FREQUENCY',
        'description': 'frequency [Hz]',
    },
    'wavl': {
        'reading_type': 'SI',
        'units': 'm',
        'var_name': 'WAVELENGTH',
        'description': 'wavelength [m]',
    },
    'engy': {
        'reading_type': 'SI',
        'units': 'J',
        'var_name': 'ENERGY',
        'description': 'energy [J]',
    },
    'powr': {
        'reading_type': 'SI',
        'units': 'W',
        'var_name': 'POWER',
        'description': 'power [W]',
    },
    'lnce': {
        'reading_type': 'SI',
        'units': 'cd/m^2',
        'var_name': 'LUMINANCE',
        'description': 'luminance [cd/m^2]',
    },
    'illu': {
        'reading_type': 'SI',
        'units': 'lx',
        'var_name': 'ILLUMINANCE',
        'description': 'illuminance [lx]',
    },
    'lext': {
        'reading_type': 'SI',
        'units': 'lx',
        'var_name': 'LUMINOUS_EXITANCE',
        'description': 'luminous exitance [lx]',
    },
    'lint': {
        'reading_type': 'SI',
        'units': 'cd',
        'var_name': 'LUMINOUS_INTENSITY',
        'description': 'luminous intensity [cd]',
    },
    'lflx': {
        'reading_type': 'SI',
        'units': 'lm',
        'var_name': 'LUMINOUS_FLUX',
        'description': 'luminous flux [lm]',
    },
    'legy': {
        'reading_type': 'SI',
        'units': 'lm s',
        'var_name': 'LUMINOUS_ENERGY',
        'description': 'luminous energy [lm s]',
    },
    'lexp': {
        'reading_type': 'SI',
        'units': 'lx s',
        'var_name': 'LUMINOUS_EXPOSURE',
        'description': 'luminous exposure [lx s]',
    },
    'radi': {
        'reading_type': 'SI',
        'units': 'Bq',
        'var_name': 'RADIOACTIVITY',
        'description': 'radioactivity [Bq]',
    },
    'ados': {
        'reading_type': 'SI',
        'units': 'Gy',
        'var_name': 'ABSORBED_DOSE',
        'description': 'absorbed dose [Gy]',
    },
    'edos': {
        'reading_type': 'SI',
        'units': 'Sv',
        'var_name': 'EQUIVALENT_DOSE',
        'description': 'equivalent dose [Sv]',
    },
    'cata': {
        'reading_type': 'SI',
        'units': 'kat',
        'var_name': 'CATALYTIC_ACTIVITY',
        'description': 'catalytic activity [kat]',
    },
    'entr': {
        'reading_type': 'SI',
        'units': 'J/K',
        'var_name': 'ENTROPY',
        'description': 'entropy [J/K] note 1 bit = k ln(2) = 9.569928e-24 J/K',
    },
    'info': {
        'reading_type': 'SI',
        'units': 'B',
        'var_name': 'INFORMATION_BYTE',
        'description': 'information [B] in byte',
    },
    'an00': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE00',
        'description': 'analogue 00 [n]',
    },
    'an01': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE01',
        'description': 'analogue 01 [n]',
    },
    'an02': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE02',
        'description': 'analogue 02 [n]',
    },
    'an03': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE03',
        'description': 'analogue 03 [n]',
    },
    'an04': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE04',
        'description': 'analogue 04 [n]',
    },
    'an05': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE05',
        'description': 'analogue 05 [n]',
    },
    'an06': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE06',
        'description': 'analogue 06 [n]',
    },
    'an07': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE07',
        'description': 'analogue 07 [n]',
    },
    'an08': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE08',
        'description': 'analogue 08 [n]',
    },
    'an09': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE09',
        'description': 'analogue 09 [n]',
    },
    'an10': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE10',
        'description': 'analogue 10 [n]',
    },
    'an11': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE11',
        'description': 'analogue 11 [n]',
    },
    'an12': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE12',
        'description': 'analogue 12 [n]',
    },
    'an13': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE13',
        'description': 'analogue 13 [n]',
    },
    'an14': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE14',
        'description': 'analogue 14 [n]',
    },
    'an15': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANALOGUE15',
        'description': 'analogue 15 [n]',
    },
    'dig0': {
        'reading_type': 'BN',
        'units': '',
        'var_name': 'DIGITAL0',
        'description': 'digital ports 0 [b] (24 bit)',
    },
    'dig1': {
        'reading_type': 'BN',
        'units': '',
        'var_name': 'DIGITAL1',
        'description': 'digital ports 1 [b] (24 bit)',
    },
    'dig2': {
        'reading_type': 'BN',
        'units': '',
        'var_name': 'DIGITAL2',
        'description': 'digital ports 2 [b] (24 bit)',
    },
    'dig3': {
        'reading_type': 'BN',
        'units': '',
        'var_name': 'DIGITAL3',
        'description': 'digital ports 3 [b] (24 bit)',
    },
    'uid0': {
        'reading_type': 'HX',
        'units': '',
        'var_name': 'UNIQUE_ID0',
        'description': '48 bit unique id part 0 [hex] (24 bit)',
    },
    'uid1': {
        'reading_type': 'HX',
        'units': '',
        'var_name': 'UNIQUE_ID1',
        'description': '48 bit unique id part 1 [hex] (24 bit)',
    },
    'airr': {
        'reading_type': 'SI',
        'units': 'Ohm',
        'var_name': 'AIR_QUALITY_RESISTANCE',
        'description': 'air quality resistance [Ohm]',
    },
    'cput': {
        'reading_type': 'FX',
        'units': 'C',
        'var_name': 'CPU_TEMPERATURE',
        'description': 'CPU temperature [C]',
    },
    'radt': {
        'reading_type': 'FX',
        'units': 'C',
        'var_name': 'RADIO_TEMPERATURE',
        'description': 'radio frequency module temperature [C]',
    },
    'rtct': {
        'reading_type': 'FX',
        'units': 'C',
        'var_name': 'RTC_TEMPERATURE',
        'description': 'rtc temperature [C]',
    },
    'humt': {
        'reading_type': 'FX',
        'units': 'C',
        'var_name': 'HUMIDITY_TEMPERATURE',
        'description': 'humidity temperature [C]',
    },
    'prst': {
        'reading_type': 'FX',
        'units': 'C',
        'var_name': 'PRESSURE_TEMPERATURE',
        'description': 'pressure temperature [C]',
    },
    'tpha': {
        'reading_type': 'FX',
        'units': 'us',
        'var_name': 'TIMEDIFF_OWN_EXTERNAL',
        'description': 'time phase own time minus external time [us]',
    },
    'tpgn': {
        'reading_type': 'FX',
        'units': 'us',
        'var_name': 'TIMEDIFF_OWN_GNSS',
        'description': 'time phase own time minus GNSS [us]',
    },
    'tpdc': {
        'reading_type': 'FX',
        'units': 'us',
        'var_name': 'TIMEDIFF_OWN_DCF',
        'description': 'time phase own time minus radio time [us]',
    },
    'dcgn': {
        'reading_type': 'FX',
        'units': 'us',
        'var_name': 'TIMEDIFF_DCF_GNSS',
        'description': 'time difference radio time minus GNSS [us]',
    },
    'clks': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'CLOCK_SKEW',
        'description': 'software clock skew [n] signed Bresenham correction value',
    },
    'clka': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'CLOCK_AGEING',
        'description': 'RTC clock ageing register [n]',
    },
    'tmpc': {
        'reading_type': 'FX',
        'units': 'C',
        'var_name': 'TEMPERATURE',
        'description': 'temperature [C]',
    },
    'volt': {
        'reading_type': 'SI',
        'units': 'V',
        'var_name': 'VOLTAGE',
        'description': 'voltage [V]',
    },
    'curr': {
        'reading_type': 'SI',
        'units': 'A',
        'var_name': 'AMPERE',
        'description': 'ampere [A]',
    },
    'time': {
        'reading_type': 'SI',
        'units': 's',
        'var_name': 'TIME',
        'description': 'time [s]',
    },
    'ster': {
        'reading_type': 'FX',
        'units': 'st',
        'var_name': 'SOLID_ANGLE',
        'description': 'solid angle [st] in [0, 2TAU] steradian',
    },
    'forc': {
        'reading_type': 'SI',
        'units': 'N',
        'var_name': 'FORCE',
        'description': 'force [N]',
    },
    'pres': {
        'reading_type': 'SI',
        'units': 'Pa',
        'var_name': 'PRESSURE',
        'description': 'pressure [Pa]',
    },
    'chrg': {
        'reading_type': 'SI',
        'units': 'As',
        'var_name': 'ELECTRIC_CHARGE',
        'description': 'electric charge [As]',
    },
    'capa': {
        'reading_type': 'SI',
        'units': 'F',
        'var_name': 'ELECTRIC_CAPACITANCE',
        'description': 'electric capacitance [F]',
    },
    'rest': {
        'reading_type': 'SI',
        'units': 'Ohm',
        'var_name': 'RESISTANCE',
        'description': 'resistance [Ohm]',
    },
    'irst': {
        'reading_type': 'SI',
        'units': 'Ohm',
        'var_name': 'IM_RESISTANCE',
        'description': 'imaginary part of complex impedance [Ohm]',
    },
    'cond': {
        'reading_type': 'SI',
        'units': 'S',
        'var_name': 'ELECTRICAL_CONDUCTANCE',
        'description': 'electrical conductance [S]',
    },
    'mflx': {
        'reading_type': 'SI',
        'units': 'Wb',
        'var_name': 'MAGNETIC_FLUX',
        'description': 'magnetic flux [Wb]',
    },
    'mfld': {
        'reading_type': 'SI',
        'units': 'T',
        'var_name': 'MAGNETIC_FIELD',
        'description': 'magnetic field [T]',
    },
    'indu': {
        'reading_type': 'SI',
        'units': 'H',
        'var_name': 'INDUCTANCE',
        'description': 'inductance [H]',
    },
    'posi': {
        'reading_type': 'SI',
        'units': 'm',
        'var_name': 'POSITION',
        'description': 'position [m]',
    },
    'velo': {
        'reading_type': 'FX',
        'units': 'm/s',
        'var_name': 'VELOCITY',
        'description': 'velocity [m/s]',
    },
    'acce': {
        'reading_type': 'FX',
        'units': 'm/s^2',
        'var_name': 'ACCELERATION',
        'description': 'acceleration [m/s^2]',
    },
    'jerk': {
        'reading_type': 'FX',
        'units': 'm/s^3',
        'var_name': 'JERK',
        'description': 'jerk [m/s^3], 3rd derivative of position',
    },
    'snap': {
        'reading_type': 'FX',
        'units': 'm/s^4',
        'var_name': 'SNAP',
        'description': 'snap [m/s^4], 4th derivative of position',
    },
    'angd': {
        'reading_type': 'FX',
        'units': 'deg',
        'var_name': 'ANGLE_DEG',
        'description': 'angle [deg] in [-180, 180)',
    },
    'angr': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'ANGLE',
        'description': 'angle [rad] in [-TAU/2, TAU/2)',
    },
    'angt': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'ANGLE_TURNS',
        'description': 'angle [turns] in [-1/2, 1/2)',
    },
    'avel': {
        'reading_type': 'FX',
        'units': 'rad/s',
        'var_name': 'ANGULAR_VELOCITY',
        'description': 'angular velocity [rad/s]',
    },
    'aacc': {
        'reading_type': 'FX',
        'units': 'rad/s^2',
        'var_name': 'ANGULAR_ACCELERATION',
        'description': 'angular acceleration [rad/s^2]',
    },
    'ajrk': {
        'reading_type': 'FX',
        'units': 'rad/s^3',
        'var_name': 'ANGULAR_JERK',
        'description': 'angular jerk [rad/s^3]',
    },
    'asnp': {
        'reading_type': 'FX',
        'units': 'rad/s^4',
        'var_name': 'ANGULAR_SNAP',
        'description': 'angular snap [rad/s^4]',
    },
    'alti': {
        'reading_type': 'FX',
        'units': 'm',
        'var_name': 'ALTITUDE_ABOVE_SEA',
        'description': 'altitude above sea [m]',
    },
    'long': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'LONGITUDE',
        'description': 'longitude [rad] in [-TAU/2, TAU/2)',
    },
    'lati': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'LATITUDE',
        'description': 'latitude [rad] in [-TAU/4, TAU/4]',
    },
    'hdop': {
        'reading_type': 'NO',
        'units': '',
        'var_name': 'HDOP',
        'description': 'hdop [n] horizontal dilution of precision: 1 is ideal, 5 is good, 20+ is poor',
    },
    'spd-': {
        'reading_type': 'FX',
        'units': 'm/s',
        'var_name': 'SPEED_ABOVE_GROUND',
        'description': 'speed above ground [m/s]',
    },
    'vmg-': {
        'reading_type': 'FX',
        'units': 'm/s',
        'var_name': 'VELOCITY_MADE_GOOD',
        'description': 'velocity made good [m/s]',
    },
    'dist': {
        'reading_type': 'SI',
        'units': 'm',
        'var_name': 'DISTANCE',
        'description': 'distance [m]',
    },
    'cour': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'COURSE',
        'description': 'course [rad] in [-TAU/2, TAU/2): N=0, E=TAU/4, S=+/-TAU/2, W=-TAU/4',
    },
    'head': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'HEADING',
        'description': 'heading [rad] in [-TAU/2, TAU/2)',
    },
    'skwt': {
        'reading_type': 'FX',
        'units': 'C',
        'var_name': 'SKEW_TEMPERATURE',
        'description': 'skew temperature [C]',
    },
    'eamf': {
        'reading_type': 'FX',
        'units': 'uT',
        'var_name': 'EARTH_MAGNETIC_FIELD',
        'description': 'earth magnetic field [uT]',
    },
    'sazi': {
        'reading_type': 'FX',
        'units': '',
        'var_name': 'SUN_AZIMUTH',
        'description': 'deg',
    },
    'salt': {
        'reading_type': 'FX',
        'units': '',
        'var_name': 'SUN_ALTITUDE',
        'description': '[wrd]',
    },
    'qalt': {
        'reading_type': 'FX',
        'units': 'm',
        'var_name': 'QUANTISED_ALTITUDE_ABOVE_SEA',
        'description': 'quantised altitude above sea [m]',
    },
    'qlon': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'QUANTISED_LONGITUDE',
        'description': 'quantised longitude [rad] in [-TAU/2, TAU/2)',
    },
    'qlat': {
        'reading_type': 'FX',
        'units': 'rad',
        'var_name': 'QUANTISED_LATITUDE',
        'description': 'quantised latitude [rad] in [-TAU/4, TAU/4]',
    },
    'qsaz': {
        'reading_type': 'FX',
        'units': '[wrd]',
        'var_name': 'QUANTISED_SUN_AZIMUTH',
        'description': 'quantised sun azimuth [deg] followed by corresponding wind rose direction instead of unit deg',
    },
    'qsal': {
        'reading_type': 'FX',
        'units': 'deg',
        'var_name': 'QUANTISED_SUN_ALTITUDE',
        'description': 'quantised sun altitude [deg] in [-90, 90]',
    },
}
"""Table defining all possible fields in the sensor board output.

The format is:

.. code:: python

   {
       'field_name': {
           'reading_type': 'XY',
           'units': '',
           'var_name': 'NAME_FOR_READING',
           'description': '',
       }
   }

The ``'field_name'`` is the name of the field as output by the sensor board. The ``'reading_type'`` dictates how to parse the reading according to :data:`reading_type_map`.
"""


@dataclass
class UrSenseParseResult:
    """Parsing according to one of the methods from the `reading_type_map` will return this object with the frontmost field as a `DynAIkonTrap.sensor.Reading` and the rest as a list of strings."""

    reading: 'sensor.Reading'
    """Reading for currently parsed field"""
    remaining_fields: List[str]
    """List of fields left to be parsed after the current field"""


def _parse_DY(fields: List[str]) -> UrSenseParseResult:
    days, hours = fields[1].split('d')
    return UrSenseParseResult(
        sensor.Reading(int(days) + int(hours) / 24.0, 'days'), fields[2:]
    )


def _parse_GS(fields: List[str]) -> UrSenseParseResult:
    reading = fields[1]
    if reading.endswith('%'):
        return UrSenseParseResult(sensor.Reading(float(reading[:-1]), '%'), fields[2:])
    else:
        return UrSenseParseResult(sensor.Reading(float(reading), fields[2]), fields[3:])


def _parse_HR(fields: List[str]) -> UrSenseParseResult:
    hours, mins = fields[1].split('h')
    return UrSenseParseResult(
        sensor.Reading(int(hours) + int(mins) / 60.0, 'hours'), fields[2:]
    )


reading_type_map: Dict[
    str, Dict[str, Union[str, Callable[..., UrSenseParseResult]]]
] = {
    'BB': {
        'description': 'binary field, one bit per sensor (length according to number of sensors)',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(int(fields[1], 2)), fields[2:]
        ),
    },
    'BN': {
        'description': 'binary number',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(int(fields[1], 2)), fields[2:]
        ),
    },
    'DY': {
        'description': 'days printed as <n>d<hh>, for example 123d03 meaning 123 days and 3 hours',
        'parser': _parse_DY,
    },
    'EE': {
        'description': 'binary field, two bit per sensor (length according to number of sensors)',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(int(fields[1], 2)), fields[2:]
        ),
    },
    'FX': {
        'description': 'floating point number followed by a fixed unit',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(float(fields[1]), fields[2]), fields[3:]
        ),
    },
    'GS': {
        'description': 'gas concentration: either a percentage (see PC) or a floating point number followed by the unit ppt, ppm or ppb',
        'parser': _parse_GS,
    },
    'HR': {
        'description': 'hours printed as <n>h<mm>, eg, 79h02 meaning 79 hours and 2 minutes',
        'parser': _parse_HR,
    },
    'HX': {
        'description': 'hexadecimal number either 48 bit, 32 bit or 24 bit',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(int(fields[1], 16)), fields[2:]
        ),
    },
    'NO': {
        'description': 'a number which can be an integer or a floating point number',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(float(fields[1])), fields[2:]
        ),
    },
    'PC': {
        'description': 'percentage as floating point number followed by %% sign without space',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(float(fields[1][:-1]), '%'), fields[2:]
        ),
    },
    'SI': {
        'description': 'floating point number followed by a unit that may have SI prefixes; the unit may differ from measurement to measurement, ie, 980 Ohm and 1.02 kOhm',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(float(fields[1]), fields[2]), fields[3:]
        ),
    },
    'UN': {
        'description': 'unsigned number (24 bit)',
        'parser': lambda fields: UrSenseParseResult(
            sensor.Reading(int(fields[1])), fields[2:]
        ),
    },
}
""" Table defining reading types and by what methodology the field in question is parsed.

The format is:

.. code:: python

   {
       'XY': {
           'description': '',
           'parser': parsing_function_for_XY,
       }
   }

Where ``'XY'`` is the type of reading, e.g., ``'SI'``. The ``'parser'`` is the function that does the actual parsing.
"""
