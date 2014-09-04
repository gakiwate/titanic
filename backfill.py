import titanic
import requests
import json
import time
import os

'''
Status
    new
    updated
    building
    running
    done
    bounds-error
'''

# Optinally you can direct it to your own local server
# server = 'http://0.0.0.0:8314/'
server = 'http://54.215.155.53:8314/'
auth = None
# auth = ('<username>@mozilla.com', '<password>')
credsfile = os.path.expanduser('~/.titanic')
if os.path.exists(credsfile):
    with open(credsfile, 'r') as f:
        lines = f.readlines()
    if len(lines) == 2:
        auth = (lines[0].strip(), lines[1].strip())

def updateJob(job, delta=30):
    revList, buildList = titanic.runAnalysis(
        job['branch'], job['buildername'], job['revision'], delta)
    revCount = len(revList)
    buildCount = len(buildList)
    retVal = 'updated'
    if(buildCount > 5 or revCount > 10 ):
        retVal = 'bounds-error'

    buildRevs = ','.join(buildList)
    revs = ','.join(revList)

    data = {'id': job['id'], 'buildrevs': buildRevs, 'analyzerevs': revs}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(server + 'update', data=json.dumps(data), headers=headers)

    if r.status_code in [requests.codes.ok, requests.codes.accepted]:
        job['buildrevs'] = buildRevs
        job['analyzerevs'] = revs

    return job,retVal

def updateStatus(job, status):
    data = {'id': job['id'], 'status': status}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(server + 'update_status', data=json.dumps(data), headers=headers)

    if r.status_code in [requests.codes.ok, requests.codes.accepted]:
        job['status'] = status

    return job

def processJob(job):
   if job['status'] == 'new':
        print 'New Job...'
        job,retVal = updateJob(job)
        if(retVal == 'bounds-error'):
            job = updateStatus(job, 'bounds-error')
            print 'Updated Job..'
        else:
            job = updateStatus(job, 'updated')
            print 'Updated Job...'

    if job['status'] == 'updated':
        if (job['buildrevs'] == '') and (job['analyzerevs'] == ''):
            job = updateStatus(job, 'done')
            return

        if not (job['buildrevs'] == ''):
            buildList = job['buildrevs'].split(',')
            for rev in buildList:
                if not (titanic.isBuildPending(job['branch'], job['buildername'], rev, auth) \
                        or titanic.isBuildRunning(job['branch'], job['buildername'], rev, auth)):
                    titanic.triggerBuild(job['branch'], job['buildername'], rev, auth)

        job = updateStatus(job, 'building')
        print 'Building for Job...'

    if job['status'] == 'building':
        print 'Builds are triggered!'
        buildFlag = 1
        revList = job['analyzerevs'].split(',')
        for rev in revList:
            if (titanic.isBuildPending(job['branch'], job['buildername'], rev, auth) \
                    or titanic.isBuildRunning(job['branch'], job['buildername'], rev, auth)):
                buildFlag = 0
                continue

            elif not titanic.isBuildSuccessful(job['branch'], job['buildername'], rev):
                print 'Error: For ' + rev + ' ' + job['buildername']
                job = updateStatus(job, 'error')
                buildFlag = 0
                continue

        if buildFlag:
            print 'Builds are done!'
            for rev in revList:
                titanic.triggerJob(job['branch'], job['buildername'], rev, auth)
                if 'talos' in job['buildername']:
                    titanic.triggerJob(job['branch'], job['buildername'], rev, auth)
                    titanic.triggerJob(job['branch'], job['buildername'], rev, auth)

            job = updateStatus(job, 'running')
            print 'Running Jobs...'


    if job['status'] == 'running':
        doneFlag = 1
        revList = job['analyzerevs'].split(',')
        for rev in revList:
            if (titanic.isJobPending(job['branch'], job['buildername'], rev, auth) \
                    or titanic.isJobRunning(job['branch'], job['buildername'], rev, auth)):
                doneFlag = 0

        if doneFlag:
            job = updateStatus(job, 'done')
            print 'Done'

    if job['status'] == 'error':
        return
    
    if job['status'] == 'bounds-error':
        print 'Too many builds or revisions to be analyzed'
        return

def processCron():
    jobsJSON = requests.get(server + 'active_jobs')
    jobs = json.loads(jobsJSON.text)
    for job in jobs['jobs']:
        processJob(job)

# Schedule backfill.py to run every few minutes!
if __name__ == '__main__':
    processCron()
