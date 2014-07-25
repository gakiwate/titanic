import titanic

buildername = 'Windows XP 32-bit mozilla-inbound pgo talos svgr'
branch = 'mozilla-inbound'
delta = 30

# NOTE: This API might take long to run. This usually takes around a minute to run
revList, buildList = titanic.runAnalysis(branch, buildername, 'ceff7d54080f', delta)

# for buildRev in buildList:
#     print titanic.getBuildCommands(branch, buildername, buildRev)
# 
# for rev in revList:
#     print titanic.getTriggerCommands(branch, buildername, rev)
