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
writingFlag = False
def clearMemorizer():
    cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_dead_objs"
    retVal = subprocess.call(cmd,shell=True)

    cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_printed_list"
    retVal = subprocess.call(cmd,shell=True)

    cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_log_access"
    retVal = subprocess.call(cmd,shell=True)

    cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_enabled"
    retVal = subprocess.call(cmd,shell=True)
    return
def initializeLogger():

    if os.path.exists("test_logs.txt"):
        os.remove("test_logs.txt")

    logging.basicConfig(filename="test_logs.txt",
                        filemode='a',
                        format='%(asctime)s,%(msecs)d %(name)s %(message)s',
                        datefmt='%H:%M:%S',
                        level=logging.DEBUG)

    logging.info("------Initializing Logger------")
    global logger
    logger = logging.getLogger()
    return

def runTest(testGroup, subTest):
    #clear memorizer data
    worked = False
    try:
        logger.info("Clearing and Initializing Memorizer")

        cmd = "echo 1 > /sys/kernel/debug/memorizer/cfg_log_on"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/cfgmap"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/stack_trace_on"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_dead_objs"
        retVal = subprocess.call(cmd,shell=True)

        cmd = "echo 1 > /sys/kernel/debug/memorizer/clear_printed_list"
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
        cmd = "/opt/ltp/runltp -f " + testGroup + " -s " + subTest
        retVal = subprocess.call(cmd,shell=True)
        if retVal == 0:
            worked = True
            print("itWorked!")
    except:
        logger.error("Test_" + testGroup + "_" + subTest + "Failed")
        return
    #produce kmap
    try:
        if worked:
            today = date.today()
            logger.info("Producing KMAP")
            cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_log_access"
            retVal = subprocess.call(cmd,shell=True)

            cmd = "echo 0 > /sys/kernel/debug/memorizer/memorizer_enabled"
            retVal = subprocess.call(cmd,shell=True)

            cmd= "cp /sys/kernel/debug/memorizer/kmap " + testGroup + "_" + subTest + "_" + today.strftime("%m_%d_%Y") + ".kmap"
            retVal = subprocess.call(cmd,shell=True)
    except:
        logger.error("Cannot create kmap!")
        return

    return

def main():
    path = "/memorizerTesting/ltp/testcases/kernel"
    testGroups  = []
    if os.path.exists(path) != 1:
        print("You don't have ltp installed!")
        return -1

    initializeLogger()

    testGroups = os.listdir(path)
    print(testGroups)

    global writingFlag
    #begin going through tests
    for currentTestGroup in testGroups:
        if os.path.isdir(path + "/" + currentTestGroup) != 1 or currentTestGroup == "kvm":
            print(path + "/"+ currentTestGroup)
            continue
        print(currentTestGroup)
        for currentSubTest in os.listdir(path +"/"+ currentTestGroup):
            if os.path.isdir(path + "/" + currentTestGroup + "/" + currentSubTest != 1):
                continue
            testingThread = multiprocessing.Process(target=runTest,args=(currentTestGroup,currentSubTest,))
            testingThread.start()
            count = 0
            while testingThread.is_alive():
                count +=1
                memoryUsage = psutil.virtual_memory()
                availableMem = memoryUsage[1]
                totalMem = memoryUsage[0]
                #reap test if memorizer is about to crash the system
                if availableMem/totalMem < .3:
                    logger.error("Memorizer taking too much memory; killing test")
                    testingThread.terminate()
                    clearMemorizer()
                time.sleep(5)
                if(writingFlag == False):
                    print("Testing")
                    print(memoryUsage)

    print("Testing is complete")
main()
