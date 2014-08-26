import titanic
import requests
import json
import time

'''
Status
    new
    updated
    building
    running
    done
'''

server = 'http://0.0.0.0:8314/'
auth = None
# auth = ('<username>@mozilla.com', '<password>')

def updateJob(jobID, branch, buildername, revision, delta=7):
    revList, buildList = titanic.runAnalysis(
        branch, buildername, revision, delta)

    print revList
    print buildList

    if not (revList or buildList):
        return 401

    buildRevs = ','.join(buildList)
    revs = ','.join(revList)

    data = {'id': jobID, 'buildrevs': buildRevs, 'analyzerevs': revs}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(server + 'update', data=json.dumps(data), headers=headers)
    print r.status_code
    return r.status_code

def updateStatus(jobID, status):
    data = {'id': jobID, 'status': status}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(server + 'update_status', data=json.dumps(data), headers=headers)

def processJob(job):
    if job['status'] == 'error':
        return

    if job['status'] == 'new':
        print 'New Job...'
        updateJob(job['id'], job['branch'], job['buildername'], job['revision'])
        updateStatus(job['id'], 'updated')
        print 'Updated Job...'

    if job['status'] == 'updated':
        if not (job['buildrevs'] == ''):
            buildList = job['buildrevs'].split(',')
            for rev in buildList:
                print rev
                titanic.triggerBuild(job['branch'], job['buildername'], rev, auth)
        updateStatus(job['id'], 'building')
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

            elif not titanic.isBuildSuccessful(job['branch'], job['buildername'], rev, auth):
                print 'Error: For ' + rev + ' ' + job['buildername']
                updateStatus(job['id'], 'error')
                buildFlag = 0
                continue

        if buildFlag:
            print 'Builds are done!'
            for rev in revList:
                titanic.triggerJob(job['branch'], job['buildername'], rev, auth)
                if not (titanic.isJobPending(job['branch'], job['buildername'], rev, auth) \
                        or titanic.isJobRunning(job['branch'], job['buildername'], rev, auth)):
                    updateStatus(job['id'], 'error')

                updateStatus(job['id'], 'running')
            print 'Running Jobs...'


    if job['status'] == 'running':
        doneFlag = 1
        revList = job['analyzerevs'].split(',')
        for rev in revList:
            if (titanic.isJobPending(job['branch'], job['buildername'], rev, auth) \
                    or titanic.isJobRunning(job['branch'], job['buildername'], rev, auth)):
                doneFlag = 0

        if doneFlag:
            updateStatus(job['id'], 'done')
            print 'Done'

def processCron():
    jobsJSON = requests.get(server + 'active_jobs')
    jobs = json.loads(jobsJSON.text)
    for job in jobs['jobs']:
        processJob(job)

# Schedule backfill.py to run every few minutes!
if __name__ == '__main__':
    processCron()
