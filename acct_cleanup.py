import subprocess
import string
import pandas as pd
import re
from datetime import date, timezone, datetime
import sys
import argparse
from prettytable import PrettyTable
import timeit

today = date.today()
#.strftime("%y")
y,m,d = (str(today).split('-'))
beginPeriod = f"{y}-{m}-01"
y, m = int(y), int(m)
endPeriod  = f"{y+(m==12)}-{m%12+1}-01"
now = datetime.now(timezone.utc).strftime("%a %b %d %Y %H:%M:%S %Z")


arg_parser= argparse.ArgumentParser()
arg_parser.add_argument('-c','--cluster', help="cluster to generate reports for")
arg_parser.add_argument('-u','--user', help="provide valid username for user based usage reports")
arg_parser.add_argument('-p','--project', help="provide project name or project based usage report")
#arg_parser.add_argument('--timeFmt',choices=['Hours','percent'], default='Hours', help="specify time format")
arg_parser.add_argument('--start', nargs='?', const=1, default=beginPeriod, help="bound info to provided time")
arg_parser.add_argument('--end', nargs='?', const=1, default=today, help="bound info to provided end time")

args = arg_parser.parse_args(args=None if sys.argv[1:] else ['--help'])

if args.user and (args.cluster is None):
    arg_parser.error("--user requires cluster option")

if args.project and (args.cluster is None):
    arg_parser.error("--project requires cluster option")


flgs = '-P -n'
clust = '--cluster={}' .format(args.cluster)
timefmt = '-t Hours'
if args.start:
    startTime = 'Start={}' .format(args.start)
if args.end:
    endTime = 'End={}' .format(args.end)
fmt = 'Format=Cluster,Login,Account,Used'


divider  = "{0:=<113}".format('')

showClust = ['sacctmgr', 'show', 'clusters', '-P', '-n', 'Format=Cluster']
allClusters = subprocess.run(showClust, text=True, stdout=subprocess.PIPE).stdout.splitlines()
def main():
    if not args.cluster in allClusters[0:4]:
        sys.exit("Error: Invalid cluster, please try again")
    if args.user:
        userReport(args.user)
    if args.project:
        try:
            projectReport(args.project)
        except IndexError:
            print("Invalid project. Please Try Again")


def userReport(user):

    #endTime = 'end=' .format(args.end) 
    users = 'Users={}' .format(user)
    cmd = " ".join(['sreport','cluster','UserUtilizationByAccount', flgs, clust, timefmt, users, startTime, endTime, fmt])

    try:
        result = subprocess.run(cmd, text=True, shell=True, check=True, stdout=subprocess.PIPE)
    except subprocess.CalledProcessError as e:
        print("Invalid User")
    temp = result.stdout
    temp = re.sub(' +', " ", temp)

    processed = temp.split('\n')


    for element in processed:
        if element:
            splitList = element.split('|')

    userInfo = [float(i) if i.isnumeric() else i for i in splitList]
    df = pd.DataFrame(userInfo,index = ['Cluster', 'User', 'Account', 'Used'], columns = ['UserReport'])
    pd.options.display.float_format = '{:,.0f}'.format
    print("\nReport Period Beginning: {}" .format(args.start))
    print("Report Period Ending: {}\n\n" .format(args.end))
    print(divider)
    print(df)

    #df = pd.DataFrame(processed, columns = ['Cluster', 'User','Account', 'Used'])

    #t = PrettyTable(['Cluster', 'User', 'Account', 'Used']) 

    #for element in processed: 
    #    if element:
    #        t.add_row(element.split('|'))
    #t.set_style("%.2f" % t.get_string(fields=["Used"]))
    #print(t)

def projectReport(project):

    accnt = 'account={}' .format(project)
    cmd = " ".join(['sreport', 'cluster', 'AccountUtilizationByUser', flgs, clust, timefmt, accnt, startTime, endTime, fmt])

    result = subprocess.run(cmd, text=True, shell=True, stdout=subprocess.PIPE).stdout.splitlines()
    projectUsage = []
    #for each entry in project report, remove delimiter and append each entry to new list
    #creating a list of lists for dataframe 
    for data in result:
        currentlist = data.split('|')
        projectUsage.append(currentlist)

    #convert core hours used to integer
    for element in projectUsage:
        element[3] = int(element[3])

    #collect each user name in project usage summary 
    users = [x[1] for x in projectUsage]


    #get job count for each user in list 
    jobUsage = getJobCount(users)

    PriorityFairshare = getFairshare(project, args.cluster)

    #initialize dataframe for project ussage 
    df = pd.DataFrame(projectUsage[1:], columns = ['Cluster', 'User', 'Account', 'Cr-HrUsed'])
    pd.options.display.float_format = '{:,.0f}'.format
    pd.set_option('display.max_colwidth', None)
    #add job usage to dataframe
    df['Jobs'] = jobUsage

    reportName = "Usage Report for {}" .format(project)

    summ = buildSumm(reportName, args.cluster, PriorityFairshare)
    print(divider)
    print(summ.to_string(header=False, index=False))
    print(divider)
    sumCol = ['Cr-HrUsed', 'Jobs']
    #Total = df[sumCol].sum()
    #print("Total\n",Total)
    df.loc['Total'] = df[sumCol].sum()
    print(df)
    #print(df.to_string(index=False))


if __name__=="__main__":
    start = timeit.default_timer()
    main()
    stop = timeit.default_timer()
    print('\nTotal Report Runtime: {0:>0,.2f} seconds\n' .format(stop-start))
