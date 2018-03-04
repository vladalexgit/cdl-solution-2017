# cdl-solution-2017
My solution for the 2017 ROSEdu CDL Challenge. The challenge can be found here: https://github.com/rosedu/problema-cdl-2017

I have solved the problem using Python3

The command line options can be provided in any order:

  - example: ```./log_stats file --interval 2 --start 2017-02-22T18:45 --end 2017-02-22T18:48 --success 20X,401,3X0```
  - or in short format: ```./log_stats file -i 2 -s 2017-02-22T18:45 -e 2017-02-22T18:48 -c 20X,401,3X0```

Some sample input files can be found here: https://github.com/rosedu/problema-cdl-2017/tree/master/tests

Implementation details:

- The program parses the input file line by line and creates instances of the LogEntry class for each entry
- The LogEntry objects are inserted into a dictionary that has the timestamps as keys, each one of the logs has a list of status codes associated to it
- Iterating over this dictionary:
  - the errors for each endpoint are counted
  - enpoints older than the maximum value of the interval are eliminated and appended to a buffer for later use
  - the buffer is sorted alphabetically and the success percent for each endpoint is shown
