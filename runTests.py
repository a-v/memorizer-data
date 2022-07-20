from cgi import test
import os
import sys
import psutil
import argparse
import subprocess
from datetime import date
import time
import logging
import multiprocessing
import random
#global vars, duh
logger = 0
writingFlag = False
testGranularity = 1
runBeforePrint = 0
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
    global testGranularity
    global runBeforePrint
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
            runBeforePrint += 1
            #after <granularity> tests complete, produce a kmap
            if(runBeforePrint == testGranularity):
                runBeforePrint=0
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
    global testGranularity
    global runBeforePrint
    testCount = 0
    parser = argparse.ArgumentParser(description="Run some LTP tests")

    parser.add_argument('-t','--tests',action="extend",nargs="+",type=str,help="Specific group of tests that you want to run")
    parser.add_argument('-o','--omit',action="extend",nargs="+",type=str,help="Specific tests that you don't want run")
    parser.add_argument("-p","--path",type=str,help="path to the ./ltp installation, otherwise assumes in working directory")
    parser.add_argument("-r","--random",action='store_true',help="randomize order in which the tests are run")
    parser.add_argument("-n","--number",help="the number of tests to run")
    parser.add_argument("-g","--granularity",type=int,help="the number of tests to run before producing a kmap (DEFAULT=1)")
    args = parser.parse_args()

    #check for path arguement
    if args.path == None:
        ltpHome = "."
    else:
        ltpHome = args.path
    path = ltpHome + "/ltp/testcases/kernel"
    #path = "/memorizerTesting/ltp/testcases/kernel"

    #check for test group
    if args.tests == None:
        testGroups = os.listdir(path)
    else:
        testGroups = args.tests

    #check for omitted tests
    if args.omit == None:
        ignore = []
    else:
        ignore = args.omit
    
    #set number of tests to be ran
    if args.number != None:
        testCount = args.number
    else:
        testCount = 100000000
    #check if tests need to be shuffled (TODO: truly randomize test order, not just within subtests)
    if args.random:
        random.shuffle(testGroups)
        randomize = True
    else:
        randomize = False

    if args.granularity != None:
        testGranularity = args.granularity
        runBeforePrint = 0
    else:
        runBeforePrint=0
    print(path,testGroups,ignore)
    if os.path.exists(path) != 1:
        print("You don't have ltp installed or the path is incorrect!")
        return -1

    initializeLogger()

    testGroups = os.listdir(path)
    print(testGroups)

    global writingFlag
    #begin going through tests
    for currentTestGroup in testGroups:
        #check for ommitted tests and skip
        if os.path.isdir(path + "/" + currentTestGroup) != 1 or currentTestGroup == "kvm" or currentTestGroup in ignore:
            continue
        subTests = os.listdir(path +"/"+ currentTestGroup)
        if randomize:
            random.shuffle(subTests)
        for currentSubTest in subTests:
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
                if (1-availableMem/totalMem) > .8:
                    logger.error("Memorizer taking too much memory; killing test")
                    testingThread.terminate()
                    clearMemorizer()
                time.sleep(5)
                if(writingFlag == False):
                    print("Testing")
                    print(memoryUsage)
            testCount -= 1
            if testCount == 0:
                break

    print("Testing is complete")
main()
