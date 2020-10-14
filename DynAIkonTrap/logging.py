from logging import getLogger, StreamHandler, Formatter, DEBUG, INFO

def get_logger(name):
    logger = getLogger(name)
    logger.setLevel(DEBUG)
    _ch = StreamHandler()
    _ch.setLevel(DEBUG)
    _ch.setFormatter(Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(_ch)
    return logger
