import csv
import os
import sys
import getopt
import xml.dom.minidom
import time
import datetime
import platform
from operator import itemgetter, attrgetter

#{process_name,(totole, times)}
processes = {}
#{(model_name@function_name,inclusive, exclusive, source file)}
profiles = []
TOP = 100
MINITIME = 10
TOTALTIME = 'TotalTime'
ENVIRONMENT = 'Environment'
BUILDNUMBER = 'BN'
PROCESSTIME = 'ProcessTime'
PROCESS = 'Process'
FUNCTIONS = 'Functions'

PROFILEFILTER = ('.', 'log4net', 'QuickGraph', '')
SYSTEM_INFO_NAME = ['Host Name', 'OS Name', 'OS Version', 'System Type', 'Processor(s)',
                    'Total Physical Memory', 'Available Physical Memory', 'Virtual Memory']

def PrepareCSV(csvfile, csvfiles, profile=False):
    if csvfile[-4:] == '.csv':
        if not profile and csvfile[:5] != 'perf_':
            #print "1:" + csvfile
            csvfiles.append(csvfile)
        elif profile and csvfile[:5] == 'perf_':
            #print "2:" + csvfile
            csvfiles.append(csvfile)


def ParseCSV(reader):
    #print 'parse csv'
    for row in reader:
        process_name = row[0]
        process_time = row[1]
        #print process_name + ":" + process_time
        
        if not process_time.isdigit():
            continue
        
        if process_name in processes:
            #print  int(process_time) + processes[process_name][0]
            _total = processes[process_name][0] + int(process_time)
            #print "total:" + _total
            _times = processes[process_name][1] + 1
            #print "times:" + _times
            processes[process_name] = (_total, _times)
            #print repr(processes[process_name])
        else:
            processes[process_name] = (int(process_time), 1)
    #print repr(processes)

def ParseProfileCSV(reader):
    for row in reader:
        #print repr(row)
        profile_func = row[0]   #function name
        profile_inc  = row[1]   #inclusive
        profile_exc  = row[2]   #exclusive
        profile_src  = row[5]   #source file
        profile_mod  = row[8]   #module
        
        if profile_func.split('.')[0] in PROFILEFILTER:
            continue
        
        #print '::'.join([profile_func, profile_inc, profile_exc, profile_src, profile_mod])
        if profile_inc.isdigit() and profile_exc.isdigit():
            _profile_inc = int(profile_inc)
            _profile_exc = int(profile_exc)
            
            if profile_inc < MINITIME and profile_exc < MINITIME:
                continue
            profiles.append((profile_mod + '@' + profile_func, _profile_inc, _profile_exc, profile_src))
    #print repr(profiles)


def SortProfileCSV(sortExclude=True, hasSrcFile=False):
    if sortExclude:
        hasSrcFile and profiles.sort(key = itemgetter(2), reverse = True) or profiles.sort(key = itemgetter(2, 3), reverse = True)
    else:
        hasSrcFile and profiles.sort(key = itemgetter(1), reverse = True) or profiles.sort(key = itemgetter(1, 3), reverse = True)


def ProcessCSV(csvdir):
    #print 'process csv'
    #read csv file
    csvfiles = []
    [PrepareCSV(file, csvfiles) for file in os.listdir(csvdir)]
    
    if len(csvfiles) == 0:
        print '\nNo csv files found'
        sys.exit()

    for csvfile in csvfiles:
        #print repr(csvdir + os.sep + csvfile)
        with open(csvdir + os.sep + csvfile) as f:
            reader = csv.reader(f, delimiter=',')
            ParseCSV(reader)
    #print repr(processes)

def ProcessProfile(csvdir):
    #print 'profile csv'
    #read csv file
    csvfiles = []
    [PrepareCSV(file, csvfiles, True) for file in os.listdir(csvdir)]

    #print repr(csvfiles)
    if len(csvfiles) == 0:
        print '\nNo profile csv file found.'
        sys.exit()

    for csvfile in csvfiles:
        with open(csvdir + os.sep + csvfile) as f:
            reader = csv.reader(f, delimiter=',')
            ParseProfileCSV(reader)
    #print 'sort'
    SortProfileCSV()


def AddSystemInfo(env, doc):
    sysinfo = os.popen("systeminfo").readlines()
    def filtInfo(f):
        _info = f.replace('\n', '').split(':')
        if len(_info) == 2 and _info[0] in SYSTEM_INFO_NAME:
            if _info[0] == 'Processor(s)':
                CreateTextNode(_info[0], platform.processor() , env, doc)
            else:
                CreateTextNode(_info[0], _info[1].strip(), env, doc)
        elif len(_info) == 3 and _info[0] in SYSTEM_INFO_NAME:
            #print _info[:]
            CreateTextNode(':'.join(_info[:2]), _info[2].strip(), env ,doc)
    map(filtInfo, sysinfo)
    
def CreateTextNode(name, value, root, doc):
    node = doc.createElement('ENV')
    node.setAttribute('name', name)
    node.appendChild(doc.createTextNode(value))
    root.appendChild(node)

def GenerateDataXmlStruct():
    impl = xml.dom.minidom.getDOMImplementation()
    doc = impl.createDocument(None, 'PerfData', None)
    root = doc.documentElement
    
    totaltime = doc.createElement(TOTALTIME)
    root.appendChild(totaltime)
    
    buildNumber = doc.createElement(BUILDNUMBER)
    buildNumber.setAttribute('name', '')
    buildNumber.appendChild(doc.createTextNode(''))
    root.appendChild(buildNumber)
    
    env = doc.createElement(ENVIRONMENT)
    AddSystemInfo(env, doc)
    root.appendChild(env)

    processTime = doc.createElement(PROCESSTIME)
    root.appendChild(processTime)
    return doc, root

def GetTotalTime(start, end):
    #print start, end
    def _parser(t):
        v = [int(tt) for tt in t.replace('.', ':').split(':')]
        return datetime.datetime(1,1,1,v[0], v[1], v[2], v[3]) #we don't care year/month/day
    return reduce(lambda x,y:(y-x).seconds, map(_parser, [start, end]))

def GeneratePerformanceData(csvdir, start, end):
    #print 'performance data'
    doc = root = None
    prof_data_xml = csvdir + os.sep + r'PerfData.xml'
    if not os.path.exists(prof_data_xml):
        doc, root = GenerateDataXmlStruct()
    else:
        doc = xml.dom.minidom.parse(prof_data_xml)
        root = doc.documentElement

    #set current time
    root.setAttribute('modified', time.strftime('%b %d %H:%M:%S %Y %Z'))

    #write total time
    totaltime = root.getElementsByTagName(TOTALTIME)
    if len(totaltime) < 1:
        print '/nNo total time node.'
        sys.exit() #should never hit
    
    tt = '%d' % GetTotalTime(start, end)
    totaltime = totaltime[0]
    if len(totaltime.childNodes) == 0:
        totaltime_value = doc.createTextNode(tt)
        totaltime.appendChild(totaltime_value)
    else:
        totaltime.childNodes[0].data = ','.join([totaltime.childNodes[0].data, tt])
      
    ##write process time
    proctime = root.getElementsByTagName(PROCESSTIME)
    if len(proctime) < 1:
        print '/nNo process time node.'
        sys.exit() #should never hit

    proctime = proctime[0]
    for procname, procvalue in processes.iteritems():
        _node = proctime.getElementsByTagName(PROCESS)
        _cnode = filter(lambda n: procname == n.getAttribute('name'), _node)
        if len(_cnode) == 0: #create a new proc node
            procNode = doc.createElement(PROCESS)
            procNode.setAttribute('name', procname)
            procNodeValue = doc.createTextNode('%d' % procvalue[0])
            procNode.appendChild(procNodeValue)
            proctime.appendChild(procNode)
        else: #update proc node
            _cnode[0].childNodes[0].data = ','.join([_cnode[0].childNodes[0].data, '%d' % procvalue[0]]) #append new time
    
    #write function time
    functime = root.getElementsByTagName(FUNCTIONS)
    if len(functime) != 0:
        root.removeChild(functime[0])
    
    functime = doc.createElement(FUNCTIONS)
    root.appendChild(functime)
    
    for func in profiles[:TOP]:
        _node = doc.createElement('Function')
        _funcs = func[0].split('@')
        _node.setAttribute('name', _funcs[1]) #func name
        _node.setAttribute('model', _funcs[0])#func model
        _nodevalue = doc.createTextNode('|'.join(['%s' % s for s in func[1:]]))
        _node.appendChild(_nodevalue)
        functime.appendChild(_node)

    with open(prof_data_xml, 'w') as f:
        doc.writexml(f)
    print '********Performance data done!*********'

def Run(csvdir, start, end):
    if not os.path.exists(csvdir):
        print '\n%s not found' % csvdir
        sys.exit()

    try:
        ProcessCSV(csvdir)
        ProcessProfile(csvdir)
        GeneratePerformanceData(csvdir, start, end)
    except:
        print repr(sys.exc_info())
        sys.exit()

if __name__ == "__main__":
    if len(sys.argv) < 1:
        sys.exit()

    CSVDIR=None
    STARTTIME=None
    ENDTIME=None
    
    try:
        opts, args = getopt.getopt(sys.argv[1:], "p:s:e", ["csvpath=", "starttime=", "endtime="])
        for xOpt, xArg in opts:
            if xOpt in ("-p", "--csvpath"):
                CSVDIR = xArg
            elif xOpt in ("-s", "--starttime"):
                STARTTIME = xArg
            elif xOpt in ("-e", "--endtime"):
                ENDTIME = xArg
            else:
                assert False, "unhandled xOption"
    except:
        print 'wrong'
        sys.exit()
    
    Run(CSVDIR, STARTTIME, ENDTIME)
