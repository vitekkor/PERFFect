import logging
import os

from src.args import args

FORMAT = "%(asctime)s [%(module)s] %(levelname)s  %(message)s"
filename = os.path.join(args.test_directory, "codeGenerator.log")
logging.basicConfig(filename=filename, format=FORMAT, datefmt='%Y-%m-%d %H:%M:%S', level="INFO")


class Logger:
    def __init__(self, name, stdout=False):
        self.name = name
        self.stdout = stdout
        if not self.stdout:
            self.logger_ = logging.getLogger(self.name)

    def log(self, msg):
        log_message = f"{self.name} - {msg}"
        if self.stdout:
            print(log_message)
        else:
            self.logger_.info(log_message)


def log(logger_: Logger, msg: str):
    if logger_ is not None:
        logger_.log(msg)
