import sys, traceback

def debug_trace():
    tb = sys.exc_info()[2]
    traceback.print_tb(tb)
    del tb