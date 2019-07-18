import fileinput
import csv
reader = csv.reader(fileinput.input(mode='r'), delimiter=',')
for (linenum, rline), line in zip(enumerate(reader), fileinput.input(inplace=True, backup='.bak')): #openhook=fileinput.hook_encoded("utf-8")):
    if linenum != 0:
        rline = rline[::-1]
        rline.insert(2, 0)
        rline.insert(3, 0)
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
                output[index] = '"' + x + '"' 
        print(','.join(output))
    else:
        print(line, end="")
