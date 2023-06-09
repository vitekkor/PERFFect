import argparse
import os
import sys

from src.generators.config import cfg
from src.utils import randomUtil

cwd = os.getcwd()

parser = argparse.ArgumentParser()
parser.add_argument(
    "-d", "--debug",
    action="store_true"
)
parser.add_argument(
    "-L", "--log",
    action="store_true",
    help="Keep logs for each transformation (bugs/session/logs)"
)

args = parser.parse_args()

args.options = {
    "Generator": {
    },
    'Translator': {
    },
    "TypeErasure": {
    },
    "TypeOverwriting": {
    }
}
