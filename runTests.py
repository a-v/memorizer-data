from cgi import test
import os
import sys
import psutil
import subprocess
from datetime import date
import time
import logging
import multiprocessing
#global vars, duh
logger = 0

def clearMemorizer():
    cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_dead_objs"
    retVal = subprocess.call(cmd,shell=True)

    cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_print_list"
    retVal = subprocess.call(cmd,shell=True)

    cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_log_access"
    retVal = subprocess.call(cmd,shell=True)

    cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_enabled"
    retVal = subprocess.call(cmd,shell=True)
    return
def initializeLogger():

    os.remove("test_logs.txt")

    logging.basicConfig(filename="test_logs.txt",
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(messages)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

    logging.info("------Initializing Logger------")
    logger = logging.getLogger()
    return

def runTest(testGroup, subTest):
    #clear memorizer data
    try:
        logger.info("Clearing and Initializing Memorizer")

        cmd = "echo 1 > /sys/kernel/debug/memorizer/cfg_log_on"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/cfgmap"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/stack_track_on"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_dead_objs"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_print_list"
        retVal = subprocess.call(cmd,shell=True)

        #turn the memorizer on
        cmd = "echo 1 > /sys/kernel/debug/memorizer/memorizer_log_access"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/memorizer_enabled"
        retVal = subprocess.call(cmd,shell=True)
    except:
        logger.error("Cannot initialize the memorizer")
        return

    #start test
    try:
        logger.info("Beginning Test: " + testGroup + " " + subTest)
        cmd = "/opt/ltp/runtp -f " + testGroup + " -s " + subTest
        retVal = subprocess.call(cmd,shell=True)
    except:
        logger.error("Test_" + testGroup + "_" + subTest + "Failed")
        return
    #produce kmap
    try:
        today = date.today()
        logger.info("Producing KMAP")
        cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_log_access"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_enabled"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "cat /sys/kernel/debug/memorizer/memorizer_log_access > " + testGroup + "_" + subTest + "_" + today.strftime("%m_%d_%Y")
    except:
        logger.error("Cannot create kmap!")
        return

    return

def main():
    path = "/opt/ltp/testcases"
    testGroups  = []
    if os.path.exists(path) != 1:
        print("You don't have ltp installed!")
        return -1

    initializeLogger()

    testGroups = os.listdir(path)

    #begin going through tests
    for currentTestGroup in testGroups:
        if os.path.isdir(currentTestGroup) != 1:
            continue
        for currentSubTest in os.listdir(currentTestGroup):
            testingThread = multiprocessing.Process(target=runTest,args=(currentTestGroup,currentSubTest,))
            testingThread.start()
            while testingThread.is_alive():
                memoryUsage = psutil.virtual_memory()
                availableMem = memoryUsage[1]
                totalMem = memoryUsage[0]
                #reap test if memorizer is about to crash the system
                if availableMem/totalMem < .1:
                    logger.error("Memorizer taking too much memory; killing test")
                    testingThread.terminate()
                    clearMemorizer()
                time.sleep(5)

    print("Testing is complete")
main()