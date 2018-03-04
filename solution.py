from datetime import datetime
from datetime import timedelta
import re
import sys      # for cmd line args
import getopt
import os.path  # for checking file existence


class LogEntry(object):

    """one log entry (represented as one line in the log file)"""

    def __init__(self, timestamp, endpoint, status_code):
        self.timestamp = timestamp
        self.endpoint = endpoint
        self.status_code = status_code


def read_file(log, filename, start_time, end_time):

    """ read the lines between start and stop times and add them to the log """

    if start_time is not None and end_time is not None:

        with open(filename) as log_file:
            for line in log_file:

                # skip times < start
                if get_date(line) < start_time:
                    continue

                # read until the end
                if get_date(line) > end_time:
                    break

                add_entry(log, line)

    elif start_time is not None:

        with open(filename) as log_file:
            for line in log_file:

                # skip times < start
                if get_date(line) < start_time:
                    continue
                add_entry(log, line)

    elif end_time is not None:

        with open(filename) as log_file:
            for line in log_file:

                # read until the end
                if get_date(line) > end_time:
                    break
                add_entry(log, line)

    else:

        with open(filename) as log_file:
            for line in log_file:
                add_entry(log, line)


def add_entry(log, string):

    """ gets the required fields from the string (line) and adds a corresponding
        entry in the log """

    timestamp = get_date(string)

    # get the first field between ""
    endpoint = ((string.split('"', 1)[1]).split('"', 1)[0]).split(None)[1]
    # match it only until ?/#/ or blank"
    expr = re.compile('(?:(?![?#" ]).)*')
    search_buffer = expr.search(endpoint)
    endpoint = search_buffer.group(0)

    # get the first word after the first "" group
    status_code = string.split('"', 2)[-1].split(None)[0]

    log.append(LogEntry(timestamp, endpoint, status_code))


def get_date(line):

    # get the first field between []
    timestamp = line.split('[', 1)[1].split(']', 1)[0]
    # remove the timezone
    timestamp = timestamp.split(None, 1)[0]
    # parse it using datetime

    return datetime.strptime(timestamp, '%d/%b/%Y:%H:%M:%S')


def calculate_percent(flagged, not_flagged):

    return round(flagged * 100 / (flagged + not_flagged), 2)


def generate_print_info(timestamp, endpoint_name, err_no, success_no):

    """ makes a list from the description information of an endpoint,
        which will be printed later """

    return [timestamp,
            endpoint_name,
            '%.2f' % calculate_percent(success_no, err_no)
            ]


def display_buffer(interval_length, buff):

    # displays the print buffer in the required format

    buff = sorted(buff, key=lambda x: x[1])  # sort by endpoint name
    buff = sorted(buff, key=lambda x: x[0])  # sort by timestamp

    for info in buff:

        print(datetime.strftime(info[0], '%Y-%m-%dT%H:%M'),
              interval_length, info[1], info[2])


def is_error(status_code, success_regex):

    return not re.match(success_regex, status_code)


def ignore_seconds(timestamp):

    return timestamp.replace(second=0)


def argv_to_regex(string):

    """ converts a string of format '2xx,30x' to equivalent regex '2..|30.' """

    # replace 'x' with regex equivalent for any character
    string = string.lower().replace('x', '.')
    # chain all reg expressions with the | operator
    generalised_regex = "|".join(string.split(','))

    return re.compile(generalised_regex)


def main(argv):

    interval_length = '1'  # implicit interval is 1 minute
    start = ''
    end = ''
    success_regex = re.compile('2..')  # default success codes are 2xx

    # get cmd line arguments
    short_params = 'i:s:e:c:'
    long_params = ['interval=', 'start=', 'end=', 'success=']

    try:

        options, values = getopt.getopt(argv[2:], short_params, long_params)

    except getopt.GetoptError:

        print("ERROR: optional params should be interval/start/end/success")
        sys.exit(2)

    for option, value in options:

        if option in ("-i", "--interval"):
            interval_length = value
        elif option in ("-s", "--start"):
            start = value
        elif option in ("-e", "--end"):
            end = value
        elif option in ("-c", "--success"):
            success_regex = argv_to_regex(value)

    # turn start and end strings into datetime objects

    start_time = None
    end_time = None

    if start != '':
        start_time = datetime.strptime(start, '%Y-%m-%dT%H:%M')
    if end != '':
        end_time = datetime.strptime(end, '%Y-%m-%dT%H:%M')

    log = []

    # read log from file

    if len(argv) < 2:
        print("ERROR: no file name argument inserted")
        sys.exit(2)
    elif os.path.exists(argv[1]):
        read_file(log, argv[1], start_time, end_time)
    else:
        print("ERROR: wrong file name", argv[1])
        sys.exit(2)

    timeline = dict()
    counter = dict()

    # for every minute in timeline,
    # add the active endpoints and their status codes

    for entry in log:

        crt_stamp = ignore_seconds(entry.timestamp)

        if crt_stamp not in timeline:
            timeline[crt_stamp] = dict()

        if entry.endpoint in timeline[crt_stamp]:
            timeline[crt_stamp][entry.endpoint].append(entry.status_code)

        else:
            timeline[crt_stamp][entry.endpoint] = [entry.status_code]

    # iterate through the timeline and count success ratio for each endpoint
    # if a time longer than interval_length has passed,
    # print the endpoint's stats

    interval_length = int(interval_length)

    for minute, endpoints in sorted(timeline.items()):

        print_buffer = []
        expired = []

        # check every minute if we have expired objects in the counter,
        # add them to the print_buffer
        for endpoint, description in counter.items():

            if minute - description[2] >= timedelta(minutes=interval_length):
                # add to print buffer
                print_buffer.append(generate_print_info(description[2],
                                                        endpoint,
                                                        description[0],
                                                        description[1]))
                expired.append(endpoint)

        # remove all the expired keys from the counter
        counter = {key: counter[key] for key in counter if key not in expired}

        # calculate stats for each endpoint
        for endpoint, codes in endpoints.items():

            if endpoint not in counter:
                counter[endpoint] = [0, 0, minute]
                # [ errors, not errors, first occurrence]

            for code in codes:

                if is_error(code, success_regex):
                    counter[endpoint][0] += 1
                else:
                    counter[endpoint][1] += 1

        # print the buffer for the current minute
        display_buffer(interval_length, print_buffer)

    # print remaining endpoints
    # some might not have had the chance to expire if the interval has ended
    print_buffer = []

    for endpoint, description in counter.items():
        # add to print buffer
        print_buffer.append(generate_print_info(description[2],
                                                endpoint,
                                                description[0],
                                                description[1]))

    display_buffer(interval_length, print_buffer)


if __name__ == "__main__":
    main(sys.argv)
