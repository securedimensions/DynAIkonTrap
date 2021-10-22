from dataclasses import dataclass
from typing import List
from enum import Enum
from multiprocessing import Event, Process, Queue, Value
from multiprocessing.queues import Queue as QueueType
from time import sleep, time

from DynAIkonTrap.camera import Frame
from DynAIkonTrap.logging import get_logger
from DynAIkonTrap.settings import AnimalFilterSettings, MotionQueueSettings
from DynAIkonTrap.filtering.animal import AnimalFilter, ImageFormat
from DynAIkonTrap.filtering.remember_from_disk import EventRememberer, EventData

logger = get_logger(__name__)

class EventProcessor():

    def __init__(self, read_from: EventRememberer, settings_animal: AnimalFilterSettings):
        self._input_queue = read_from
        self._output_queue: QueueType[EventData] = Queue()
        self._animal_filter = AnimalFilter(settings_animal)
        
        self._usher = Process(target=self._handle_input, daemon=True)
        self._usher.start()

    def _handle_input(self):
        while True:
            try:
                event = self._input_queue.get()
                self._process_event(event)
            except Exception as e:
                print(e)
                sleep(1)
                continue

    def _process_event(self, event:EventData) -> bool:
        lst_indx_frames = list(enumerate(event.raw_raster_frames))      
        middle_idx = len(lst_indx_frames) // 2
        lst_indx_frames.sort(key = lambda x :abs( middle_idx - x[0]))
        for index, frame in lst_indx_frames:
            is_animal = self._animal_filter.run(frame, format=ImageFormat.RGBA)
            if is_animal:
                return True
        return False
        
            
