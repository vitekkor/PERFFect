import argparse
import os

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
args.test_directory = os.path.join(cwd, "logs")

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
