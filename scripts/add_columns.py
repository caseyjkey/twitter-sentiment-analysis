import fileinput
import codecs
import csv
import sys

def inplace(orig_path, encoding='utf-8'):
    """Modify a file in-place, with a consistent encoding."""
    new_path = orig_path + '.modified'
    with codecs.open(orig_path, encoding=encoding, errors='ignore') as orig:
        with codecs.open(new_path, 'w', encoding=encoding, errors='ignore') as new:
            for line in orig:
                yield line, new
    os.rename(new_path, orig_path)

with codecs.open(sys.argv[1], 'r', encoding='utf-8', errors='ignore') as f:
    reader = csv.reader(f, delimiter=',')
    for (linenum, rline), (line, new) in zip(enumerate(reader), inplace(sys.argv[1])): # fileinput.input(inplace=True, backup='.bak', openhook=fileinput.hook_encoded("utf-8"))):
        if linenum != 0:
            rline = rline[::-1]
            #rline.insert(2, 0)
            #rline.insert(3, 0)
            rline = rline[::-1]
            if rline[1]:
                rline[1] = str(rline[1])
            rline[2] = str(rline[2])
            rline[3] = str(rline[3])
            rline[6] = str(rline[6])
            rline[7] = str(rline[7])
            indexes = [1,2,3,6,7]
            output = [str(x) for x in rline]
            for index, x in enumerate(rline):
                if index in indexes and x is not str:
                    output[index] = '"' + x.replace('"', '').replace("'", "") + '"' 
            new.write(','.join(output) + '\n')
        else:
            new.write(line)
