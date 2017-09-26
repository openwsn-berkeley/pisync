from __future__ import division
import csv


POSITIVE = 1
NEGATIVE = -1
PASS = 0

if __name__ == "__main__":
    unit_conversion = {
        's': 10**6,
        'ms': 10**3,
        'us': 10**0,
        'ns': 10**(-3),
    }

    input_filename = 'Data/test1.csv'
    output_filename = input_filename.rsplit('.',1)
    output_filename[0] += '_output'
    output_filename = output_filename[0] + '.csv'

    with open(input_filename, 'r') as raw_file, open(output_filename, 'w') as output_file:
        reader = csv.reader(raw_file)
        writer = csv.writer(output_file)
        next(reader)
        for row in reader:
            if row[1] == '1':
                direction = POSITIVE
            elif row[1] == '2':
                direction = NEGATIVE
            else:
                direction = PASS

            if direction != 0:
                delay_us = direction*float(row[2])*unit_conversion[row[3]]
                print("{} -> {}".format(row, delay_us))
                writer.writerow([delay_us])

            else:
                print("{}".format(row))

                # with open('output_filename', 'r') as output_file:
                #     reader = csv.reader(output_file)
                #     for row in reader:
                #         print row
