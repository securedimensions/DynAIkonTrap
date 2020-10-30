from time import time
import pickle
import subprocess
from multiprocessing import Queue, Process, Value
from queue import Full
from unittest import TestCase

from DynAIkonTrap.camera import Frame, Camera
from DynAIkonTrap.filtering import Filter
from DynAIkonTrap.comms import Sender
from DynAIkonTrap.sensor import SensorLogs
from DynAIkonTrap.settings import load_settings, OutputMode


class Tester:
    def __init__(self, data, truth):
        self.tpr = None
        self.tnr = None
        self.precision = None
        self._data = data['frames']
        self._truth = truth
        self.verbose = False
        self.time = None

    def test(self, fn):

        self.time = 0

        results = []
        for d in self._data:

            t_start = time()
            result = fn(d)
            t_stop = time()
            self.time += t_stop - t_start

            if result is None:
                continue
            elif type(result) is list:
                results += result
            else:
                results.append(result)

        while len(results) != len(self._data):
            t_start = time()
            result = fn(None)
            t_stop = time()
            self.time += t_stop - t_start

            if result is None:
                continue
            elif type(result) is list:
                results += result
            else:
                results.append(result)

        tp = list(map(lambda x, y: x and y, results, self._truth)).count(True)
        tn = list(map(lambda x, y: (not x) and (not y), results, self._truth)).count(
            True
        )
        fp = list(map(lambda x, y: x and (not y), results, self._truth)).count(True)
        fn = list(map(lambda x, y: (not x) and y, results, self._truth)).count(True)

        if self.verbose:
            print('truth = ', self._truth)
            print('predictions = ', results)

        self.tpr = tp / (tp + fn)
        self.tnr = tn / (tn + fp)
        self.precision = tp / (tp + fp) if (tp + fp) != 0 else float('nan')

    def i_score(self, alpha=0.1):
        """Weighted harmonic mean of true-negative rate (TNR)
        and tre-positive rate (TPR).

        An alpha of 0 collapses to TPR aka. recall,
        whilst alpha of 1 collapses to TNR.

        :param alpha: weighting factor in range [0..1]
        :type alpha: float
        :return: Weighted harmonic mean scoring
        :rtype: float
        """

        '''
                      1
        I = ---------------------
             alpha   (1 - alpha)
             ----- + -----------
              TNR        TPR
        '''

        if self.tnr == 0:
            if alpha == 0:
                tnr_part = 0
            else:
                return 0
        else:
            tnr_part = alpha / self.tnr

        if self.tpr == 0:
            if (1 - alpha) == 0:
                tpr_part = 0
            else:
                return 0
        else:
            tpr_part = (1 - alpha) / self.tpr

        return 1 / (tnr_part + tpr_part)


def load_pickle(filename):
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data


def purge_cache():
    subprocess.run(
        'sync; echo 3 | sudo tee /proc/sys/vm/drop_caches',
        shell=True,
        stdout=subprocess.DEVNULL,
    )


class MockCamera(Camera):
    """A mock camera to be used only for testing. This is expected to be removed in the future."""

    def __init__(self, **kwargs):
        self.resolution = (640, 480)
        self.framerate = 20
        self._output = Queue()

        data = load_pickle('test/data/dog2.pk')
        truth = load_pickle('test/data/dog2.pk.truth')

        # tester = Tester(data, truth)

        def runner(frame):
            if frame is None:
                return False
            self._output.put(Frame(frame['image'], frame['motion'], time()))
            return False

        def proc():
            # sleep(30)
            # while True:
            # print('{} frames on queue'.format(self._output.qsize()))
            tester = Tester(data, truth)
            try:
                tester.test(runner)
            except Full:
                print('Queue full: {} frames on queue'.format(self._output.qsize()))
                quit(-1)

        process = Process(target=proc, daemon=True)
        process.start()


class SenderMock(Sender):
    def __init__(self, settings, read_from):
        self.call_count = Value('i', 0)
        super().__init__(settings, read_from)

    def send(self, **kwargs):
        with self.call_count.get_lock():
            self.call_count.value += 1


class IntegrationStillsOutTestCase(TestCase):
    def test_integration_at_least_one_animal_frame(self):
        settings = load_settings()
        settings.sender.output_mode = OutputMode.STILL
        camera = MockCamera()
        filters = Filter(read_from=camera, settings=settings.filter)
        sensor_logs = SensorLogs(settings=settings.sensor)
        self.sender = SenderMock(
            settings=settings.sender, read_from=(filters, sensor_logs)
        )

        t_start = time()

        while True:

            if self.sender.call_count.value >= 1:
                self.assertTrue(True)
                break

            if time() - t_start >= 50:
                self.assertTrue(False, 'Timed out')
                break
