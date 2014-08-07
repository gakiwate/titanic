import titanic

buildername = 'Ubuntu HW 12.04 x64 mozilla-inbound pgo talos svgr'
branch = 'mozilla-inbound'
delta = 30

# NOTE: This API might take long to run.
# Usually takes around a minute to run, may take longer
revList, buildList = titanic.runAnalysis(
    branch, buildername, '6ffcd2030ed8', delta)

# NOTE: runAnalysis argument 'delta' is optional.  If not provided, it will default to 7.
# See example below:
# revList, buildList = titanic.runAnalysis(
#     branch, buildername, 'ceff7d54080f')

for buildRev in buildList:
    print titanic.getBuildCommands(branch, buildername, buildRev)

for rev in revList:
    print titanic.getTriggerCommands(branch, buildername, rev)

# Uncomment the following lines if you want to test the trigger functionality 
# of the code
# print 'Building Rev ' + str(buildList[0])
# titanic.triggerBuild(branch, buildername, buildList[0])
# print 'You should find the status at this URL: \
#     https://secure.pub.build.mozilla.org/buildapi/self-serve/mozilla-inbound/rev/' \
#     + str(buildList[0])
