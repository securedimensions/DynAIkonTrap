from time import sleep
from unittest import TestCase
from collections import OrderedDict

from DynAIkonTrap.sensor import SensorLogs, SensorLog
from DynAIkonTrap.settings import SensorSettings


class SensorMock:
    def __init__(self):
        self._i = 0

    def read(self) -> SensorLog:
        ret = SensorLog(self._i, self._i + 1, self._i + 2, self._i + 3, self._i + 4)
        self._i += 5
        return ret


class LogNowAddsToLogsTestCase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_logs_added(self):
        self._sl._log_now()
        self._sl._log_now()
        self._sl._log_now()
        self.assertEqual(self._sl._storage[0], SensorLog(0, 1, 2, 3, 4))
        self.assertEqual(self._sl._storage[5], SensorLog(5, 6, 7, 8, 9))
        self.assertEqual(self._sl._storage[10], SensorLog(10, 11, 12, 13, 14))


class RemoveLogsTestcase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_remove_logs_when_none_exist(self):
        self._sl._storage.clear()
        with self.assertRaises(KeyError):
            self._sl._remove_logs([0])

    def test_remove_logs_with_given_timestamps(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        self._sl._log_now()
        self._sl._remove_logs([0, 5])
        self.assertEqual(len(self._sl._storage), 1)
        self.assertEqual(self._sl._storage[10], SensorLog(10, 11, 12, 13, 14))


class FindKeyTestCase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_find_exact_key(self):
        res = self._sl._find_closest_key([0.1, 1.1, 2.1], 0.1)
        self.assertEqual(res, (0.1, 0))

    def test_lookup_just_larger_than_key(self):
        res = self._sl._find_closest_key([0, 1, 2], 0.1)
        self.assertEqual(res, (0, 0))

    def test_lookup_just_smaller_than_key(self):
        res = self._sl._find_closest_key([0, 1, 2], 0.9)
        self.assertEqual(res, (1, 1))

    def test_only_one_key(self):
        res = self._sl._find_closest_key([0], 1)
        self.assertEqual(res, (0, 0))

    def test_lookup_smaller_than_smallest_entry(self):
        res = self._sl._find_closest_key([0, 1, 2], -1)
        self.assertEqual(res, (0, 0))

    def test_lookup_larger_than_largest_entry(self):
        res = self._sl._find_closest_key([0, 1, 2], 3)
        self.assertEqual(res, (2, 2))


class LookupAndDeleteTestCase(TestCase):
    def setUp(self):
        class MySensorLogs(SensorLogs):
            def __init__(self):
                super().__init__(SensorSettings('', 0, 0.1))
                self._sensor = SensorMock()
                self._logger.terminate()

        self._sl = MySensorLogs()

    def test_returns_closest_log1(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        ret = self._sl._lookup(0.1)
        self.assertEqual(ret, SensorLog(0, 1, 2, 3, 4))

    def test_returns_closest_log2(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        ret = self._sl._lookup(4.9)
        self.assertEqual(ret, SensorLog(5, 6, 7, 8, 9))

    def test_returns_closest_log3(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        ret = self._sl._lookup(5.1)
        self.assertEqual(ret, SensorLog(5, 6, 7, 8, 9))

    def test_removes_only_logs_older_than_requested_time(self):
        self._sl._storage.clear()
        self._sl._log_now()
        self._sl._log_now()
        self._sl._lookup(5.1)
        self.assertEqual(len(self._sl._storage), 1)
        self.assertEqual(self._sl._storage, OrderedDict({5: SensorLog(5, 6, 7, 8, 9)}))
