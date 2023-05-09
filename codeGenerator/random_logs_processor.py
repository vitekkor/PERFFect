import re
import sys

input_file = sys.argv[1]
output_file = sys.argv[2] if 2 < len(sys.argv) else re.sub('\.[^.]*$', '', input_file) + '_processed.txt'

random_logs_file = open(input_file, 'r')
random_logs = random_logs_file.readlines()

processed_logs = open(output_file, 'w+')

for log in random_logs:
    pre_processed = log.replace('(java-builtin)', '(kotlin-builtin)') \
        .replace('Object', 'Any') \
        .replace('Integer(kotlin-builtin)', 'Int(kotlin-builtin)') \
        .replace('Character(kotlin-builtin)', 'Char(kotlin-builtin)') \
        .replace('void(kotlin-builtin)', 'Unit(kotlin-builtin)')
    processed_logs.write(re.sub('0x[^>]*', '0x', pre_processed))

processed_logs.close()
