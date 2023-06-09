import typing
from collections import defaultdict
import random as rnd
import string
import pickle
import os
import sys
import inspect

from ordered_set import OrderedSet


class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(Singleton, cls).__call__(
                *args, **kwargs)
        return cls._instances[cls]


def prefix_lst(prefix, lst):
    return any(prefix == lst[:i]
               for i in range(1, len(prefix) + 1))


def is_number(string_var):
    try:
        float(string_var)
        return True
    except ValueError:
        return False


def lst_get(lst, index=0, default=None):
    """Safely get an element from a list"""
    try:
        return lst[index]
    except IndexError:
        return default


def leading_spaces(input_string):
    """Count leading spaces of a string"""
    return len(input_string) - len(input_string.lstrip(' '))


def add_string_at(input_string, substring, pos):
    """Add a substring to the given position of the string"""
    return input_string[:pos] + substring + input_string[pos:]


def read_lines(path):
    lines = []
    with open(path, 'r') as infile:
        for line in infile:
            lines.append(line.rstrip('\n'))
    return lines


def mkdir(directory_name):
    """Safe mkdir
    """
    try:
        os.makedirs(directory_name, exist_ok=True)
    except Exception as e:
        print(e)
        sys.exit(0)


def fprint(text):
    """Full screen print"""
    try:
        terminal_width = os.get_terminal_size().columns
        print(text.center(int(terminal_width), "="))
    except OSError:  # This error may occur when run under cron
        print(text)


def translate_program(translator, program):
    translator.visit(program)
    return translator.result()


def load_program(path):
    with open(path, 'rb') as initial_bin:
        return pickle.load(initial_bin)


def dump_program(path, program):
    with open(path, 'wb') as out:
        pickle.dump(program, out)


def save_text(path, text):
    with open(path, 'w') as out:
        out.write(text)


def path2set(path):
    if os.path.isfile(path):
        with open(path, 'r') as f:
            return OrderedSet([
                line.strip()
                for line in f.readlines()
            ])
    else:
        return OrderedSet()


def get_reserved_words(resource_path, language):
    filename = "{}_keywords".format(language)
    path = os.path.join(resource_path, filename)
    return path2set(path)


# for debugging purposes
def random_inspect(random_fun):
    def inner(*args, **kwargs):
        curframe = inspect.currentframe()
        calframe = inspect.getouterframes(curframe, 2)
        from_ = calframe[1][1]
        line = calframe[1][2]
        caller = calframe[1][3]
        callings = calframe[1][4]
        result = random_fun(*args, **kwargs)
        str_ = "caller - {}:{}:{}; method - {}; args - {}, kwargs - {}, result - {}".format(from_, line, caller,
                                                                                            callings, args[1:], kwargs,
                                                                                            result)
        # print(str_)
        return result

    return inner


class RandomUtils():
    resource_path = os.path.join(os.path.split(__file__)[0], "resources")

    WORD_POOL_LEN = 10000
    # Construct a random word pool of size 'WORD_POOL_LEN'.
    WORDS: OrderedSet
    INITIAL_WORDS: OrderedSet

    previous_call: str
    call: str = ''
    previous_result: typing.Any
    result: typing.Any = None

    def __init__(self):
        self.seed = 9100202880737469383  # rnd.randrange(sys.maxsize)
        self.r = rnd.Random(self.seed)
        self.WORDS = OrderedSet(self.sample(
            read_lines(os.path.join(self.resource_path, 'words')), self.WORD_POOL_LEN))
        self.INITIAL_WORDS = OrderedSet(self.WORDS)

    def reset_random(self, seed=None):
        seed = seed if seed else self.seed
        self.r = rnd.Random(seed)

    def reset_word_pool(self):
        self.WORDS = OrderedSet(self.INITIAL_WORDS)

    @random_inspect
    def bool(self, prob=0.5):
        self.previous_result = self.result
        self.previous_call = self.call
        self.result = self.r.random() < prob
        self.call = "bool"
        return self.result

    @random_inspect
    def word(self):
        self.previous_result = self.result
        self.previous_call = self.call
        word = self.r.choice(tuple(self.WORDS))
        self.WORDS.remove(word)
        self.result = word
        self.call = "word"
        return word

    @random_inspect
    def remove_reserved_words(self, language):
        reserved_words = get_reserved_words(self.resource_path, language)
        self.INITIAL_WORDS = self.INITIAL_WORDS - reserved_words
        self.WORDS = self.WORDS - reserved_words

    @random_inspect
    def integer(self, min_int=0, max_int=10):
        self.previous_result = self.result
        self.previous_call = self.call
        self.result = self.r.randint(min_int, max_int)
        self.call = "integer {} {}".format(min_int, max_int)
        return self.result

    @random_inspect
    def char(self):
        self.previous_result = self.result
        self.previous_call = self.call
        self.result = self.r.choice(string.ascii_letters + string.digits)
        self.call = "char"
        return self.result

    @random_inspect
    def choice(self, choices):
        self.previous_result = self.result
        self.previous_call = self.call
        self.result = self.r.choice(choices)
        self.call = "choice {}".format(str(choices))
        return self.result

    @random_inspect
    def sample(self, choices, k=None):
        self.previous_result = self.result
        self.previous_call = self.call
        self.call = "sample {} k={}".format(str(choices), k)
        k = k or self.integer(0, len(choices))
        self.result = self.r.sample(choices, k)
        return self.result

    @random_inspect
    def str(self, length=5):
        self.previous_result = self.result
        self.previous_call = self.call
        self.result = ''.join(self.r.sample(
            string.ascii_letters + string.digits, length))
        self.call = "str {}".format(length)
        return self.result

    @random_inspect
    def caps(self, length=1, blacklist=None):
        self.previous_result = self.result
        self.previous_call = self.call
        blacklist = blacklist if blacklist is not None else []
        self.call = "caps {} {}".format(length, str(blacklist))
        while True:
            res = ''.join(self.r.sample(string.ascii_uppercase, length))
            if res not in blacklist:
                self.result = res
                return res

    @random_inspect
    def range(self, from_value, to_value):
        self.previous_result = self.result
        self.previous_call = self.call
        self.result = range(0, self.integer(from_value, to_value))
        self.call = "range {} {}".format(from_value, to_value)
        return self.result


randomUtil = RandomUtils()


class IdGen():
    def __init__(self):
        self._cache = defaultdict(lambda: 1)

    def get_node_id(self, node_id):
        if node_id not in self._cache:
            return node_id, None
        else:
            value = self._cache[node_id]
            self._cache[node_id] += 1
            return node_id, str(value)


class Namespace:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
