import titanic
import sys

buildername = 'Windows 7 32-bit mozilla-central debug test mochitest-1'
branch = 'mozilla-central'
delta = 30
revision = 'cd2acc7ab2f8'

revList, buildList = titanic.runAnalysis(
    branch, buildername, revision, delta)

for rev in buildList:
    if not (titanic.isBuildPending(branch, buildername, rev) \
            or titanic.isBuildRunning(branch, buildername, rev)):
        titanic.triggerBuild(branch, buildername, rev)
    else:
        if not titanic.isBuildSuccessful(branch, buildername, revision):
            print 'Builds are yet to be completed for revision ' + rev + ' ...'
            print 'If the builds have been running for a very long time make sure the builds have not failed!'

if buildList != []:
    sys.exit(1)

print 'All builds are completed. Starting Jobs...'

for rev in revList:
    if not (titanic.isJobPending(branch, buildername, rev) \
            or titanic.isJobRunning(branch, buildername, rev)):
        titanic.triggerJob(branch, buildername, rev)
    else:
        print 'Job has already been triggered'
