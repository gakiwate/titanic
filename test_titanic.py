import titanic

buildername = 'Windows XP 32-bit mozilla-inbound pgo talos svgr'
branch = 'mozilla-inbound'
delta = 30

# NOTE: This API might take long to run.
# Usually takes around a minute to run, may take longer
revList, buildList = titanic.runAnalysis(
    branch, buildername, 'ceff7d54080f', delta)

# NOTE: runAnalysis argument 'delta' is optional.  If not provided, it will default to 7.
# See example below:
# revList, buildList = titanic.runAnalysis(
#     branch, buildername, 'ceff7d54080f')	
	
for buildRev in buildList:
    print titanic.getBuildCommands(branch, buildername, buildRev)

for rev in revList:
    print titanic.getTriggerCommands(branch, buildername, rev)
