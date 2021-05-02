# python-nodered-mqtt-boilerplate
Template for setting up python-nodered link via mqtt

$ python3.7 -m cProfile -o testing.prof debugging_tools.py
$ python3.7 -m pstats testing.prof

testing.prof% help
testing.prof% strip
testing.prof% sort cumtime
testing.prof% stats 10

testing.prof% sort tottime
testing.prof% stats 10

testing.prof% stats <function name>

$ pyprof2calltree -k -i latest_tutorial.prof

# This command will convert latest_tutorial.prof and open KCacheGrind to analyze the data.

'''
Note that line profiling takes time and adds a fair bit of overhead to your runtime. A more standard workflow is first to use cProfile to identify which functions to look at and then run line_profiler on those functions. line_profiler is not part of the standard library, so you should first follow the installation instructions to set it up.

git clone https://github.com/rkern/line_profiler.git
find line_profiler -name '*.pyx' -exec cython {} \;
cd line_profiler
pip install . --user

Before you run the profiler, you need to tell it which functions to profile. You do this by adding a @profile decorator inside your source code. 


@profile                    # Delete when you're done
def function():
    print('stuff here')

Then run with
$ kernprof -l latest_tutorial.py

The default behavior of kernprof is to put the results into a binary file script_to_profile.py.lprof . You can tell kernprof to immediately view the formatted results at the terminal with the [-v/--view] option. Otherwise, you can view the results later like so:

$ python3.7 -m line_profiler script_to_profile.py.lprof

Time will be in msec