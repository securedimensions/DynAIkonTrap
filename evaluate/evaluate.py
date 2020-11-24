import argparse
from logging import getLogger
from multiprocessing import Queue
from queue import Empty
from time import sleep, time
import sys
from pickle import load

sys.path.append('./')
from DynAIkonTrap.camera import Frame


class MockCamera:
    def __init__(self, settings, data):
        self.framerate = settings.framerate
        self._data = data
        self._queue = Queue()

        for i, d in enumerate(self._data):
            self._queue.put(Frame(d['image'], d['motion'], i))

    def get(self):
        return self._queue.get_nowait()


class Tester:
    def __init__(self, data, truth):
        self.tpr = None
        self.tnr = None
        self.precision = None
        self._data = data
        self._truth = truth

    def test(self):

        ## Set up the pipeline
        from signal import signal, SIGINT

        from DynAIkonTrap.filtering import Filter
        from DynAIkonTrap.settings import load_settings

        # Make Ctrl-C quit gracefully
        def handler(signal_num, stack_frame):
            exit(0)

        signal(SIGINT, handler)

        settings = load_settings()
        getLogger().setLevel('ERROR')
        
        settings.camera.framerate = self._data['framerate']
        settings.camera.resolution = self._data['resolution']

        camera = MockCamera(settings.camera, self._data['frames'])

        t_start = time()
        filters = Filter(read_from=camera, settings=settings.filter)

        ## Wait until processing is complete
        while True:
            sleep(0.1)
            if filters._motion_queue.is_idle() and camera._queue.qsize() == 0:
                break
        t_stop = time() - 0.1

        ## Retrieve the detected animal frames
        frames = []
        while True:
            try:
                frame = filters._motion_queue._output_queue.get(timeout=1)
                if frame is None:
                    continue

                frames.append(frame)

            except Empty:
                break

        ## Generate the result for each frame
        positives = list(map(lambda f: int(f.timestamp), frames))
        results = []
        for i, _ in enumerate(self._truth):
            results.append(i in positives)

        ## Calculate the constituents for the scoring
        tp = list(map(lambda x, y: x and y, results, self._truth)).count(True)
        tn = list(map(lambda x, y: (not x) and (not y), results, self._truth)).count(
            True
        )
        fp = list(map(lambda x, y: x and (not y), results, self._truth)).count(True)
        fn = list(map(lambda x, y: (not x) and y, results, self._truth)).count(True)

        self.tpr = tp / (tp + fn)
        self.tnr = tn / (tn + fp)
        self.precision = tp / (tp + fp) if (tp + fp) != 0 else float('nan')

        print(
            '{} of {} frames deemed to contain an animal'.format(
                sum(results), len(self._data['frames'])
            )
        )
        print(
            'Processed @ (average) {:.2f}FPS'.format(
                len(self._data['frames']) / (t_stop - t_start)
            )
        )

    def score(self, alpha: float) -> float:
        """Weighted harmonic mean of true-negative rate (TNR)
        and true-positive rate (TPR).

        Formula:
        ```
                  1
        ---------------------
         alpha   (1 - alpha)
         ----- + -----------
          TNR        TPR
        ```

        Args:
            alpha (float): The weighting parameter in interval [0...1]. An alpha of 0 collapses to TPR aka. recall, whilst alpha of 1 collapses to TNR.

        Returns:
            float: Score for the current test run
        """

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
        data = load(f)
    return data


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        'data',
        metavar='DATA_FILENAME',
        help='Name of input file with the recorded data e.g. `data.pk`',
    )
    parser.add_argument(
        'truth',
        metavar='TRUTH_FILENAME',
        help='Name of input file with the user-generated truth e.g. `data.truth.pk`',
    )
    args = parser.parse_args()

    tester = Tester(load_pickle(args.data), load_pickle(args.truth))

    tester.test()

    print('| Metric            | Score / % |')
    print('|-------------------|-----------|')
    print('| alpha = 0 (TPR)   | {: 9.2f} |'.format(tester.score(0) * 100))
    print('| alpha = 0,1       | {: 9.2f} |'.format(tester.score(0.1) * 100))
    print('| alpha = 0,5       | {: 9.2f} |'.format(tester.score(0.5) * 100))
    print('| alpha = 0,9       | {: 9.2f} |'.format(tester.score(0.9) * 100))
    print('| alpha = 1 (TNR)   | {: 9.2f} |'.format(tester.score(1) * 100))
    print('| Precision         | {: 9.2f} |'.format(tester.precision * 100))
