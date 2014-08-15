import os
import json
import httplib
import re
import urllib
import argparse
import sys
import datetime
import bisect
import requests

branchPaths = {
    'mozilla-central': 'mozilla-central',
    'mozilla-inbound': 'integration/mozilla-inbound',
    'b2g-inbound': 'integration/b2g-inbound',
    'fx-team': 'integration/fx-team'
}

platforms = ['linux32', 'linux64', 'osx10.6', 'osx10.7',
             'osx10.8', 'winxp', 'win7', 'win764', 'win8']

platformXRef = {
    'Linux': 'linux32',
    'Ubuntu HW 12.04': 'linux32',
    'Ubuntu VM 12.04': 'linux32',
    'Rev3 Fedora 12': 'linux32',
    'Linux x86-64': 'linux64',
    'Rev3 Fedora 12x64': 'linux64',
    'Ubuntu VM 12.04 x64': 'linux64',
    'Ubuntu HW 12.04 x64': 'linux64',
    'Ubuntu ASAN VM 12.04 x64': 'linux64',
    'Rev4 MacOSX Snow Leopard 10.6': 'osx10.6',
    'Rev4 MacOSX Lion 10.7': 'osx10.7',
    'OS X 10.7': 'osx10.7',
    'Rev5 MacOSX Mountain Lion 10.8': 'osx10.8',
    'WINNT 5.2': 'winxp',
    'Windows XP 32-bit': 'winxp',
    'Windows 7 32-bit': 'win7',
    'Windows 7 64-bit': 'win764',
    'WINNT 6.1 x86-64': 'win764',
    'WINNT 6.2': 'win8',
    'Android Armv6': 'android-armv6',
    'Android 2.2 Armv6': 'android-armv6',
    'Android Armv6 Tegra 250': 'android-armv6',
    'Android X86': 'android-x86',
    'Android 2.2': 'android2.2',
    'Android 2.2 Tegra': 'android2.2',
    'Android 2.3 Emulator': 'android2.3',
    'Android no-ionmonkey': 'android-no-ion',
    'Android 4.0 Panda': 'android4.0',
    'b2g_emulator_vm': 'b2g-vm',
    'b2g_ubuntu64_vm': 'b2g-vm',
    'b2g_ubuntu32_vm': 'b2g-vm',
    'b2g_ics_armv7a_gecko_emulator_vm': 'b2g-vm',
    'b2g_ics_armv7a_gecko_emulator': 'b2g-emulator'
}

#
# The following platforms were not considered
# We might want to add them in the future
#
'''
b2g_mozilla-central_macosx64_gecko build opt
b2g_mozilla-central_macosx64_gecko-debug build opt
b2g_macosx64 opt gaia-ui-test

linux64-br-haz_mozilla-central_dep opt

Android 4.2 x86 build
Android 4.2 x86 Emulator opt androidx86-set-4

b2g_mozilla-central_win32_gecko-debug build opt
b2g_mozilla-central_win32_gecko build opt
b2g_mozilla-central_linux32_gecko build opt
b2g_mozilla-central_linux32_gecko-debug build opt

b2g_mozilla-central_emulator-kk_periodic opt
b2g_mozilla-central_emulator-kk-debug_periodic opt
b2g_mozilla-central_emulator-kk_nonunified opt
b2g_mozilla-central_emulator-kk-debug_nonunified opt

b2g_mozilla-central_emulator-jb-debug_dep opt
b2g_mozilla-central_emulator_dep opt
b2g_mozilla-central_emulator-debug_dep opt
b2g_mozilla-central_emulator-jb_dep opt
b2g_mozilla-central_emulator_nonunified opt
b2g_mozilla-central_emulator-debug_nonunified opt
b2g_mozilla-central_emulator-jb-debug_nonunified opt
b2g_mozilla-central_emulator-jb_nonunified opt

b2g_mozilla-central_nexus-4_periodic opt
b2g_mozilla-central_nexus-4_eng_periodic opt

b2g_mozilla-central_linux64_gecko build opt
b2g_mozilla-central_linux64_gecko-debug build opt

b2g_mozilla-central_hamachi_eng_dep opt
b2g_mozilla-central_hamachi_periodic opt

b2g_mozilla-central_flame_eng_dep opt
b2g_mozilla-central_flame_periodic opt

b2g_mozilla-central_helix_periodic opt

b2g_mozilla-central_wasabi_periodic opt
'''

# getPushLog looks at the input branch and returns a list of all revisions, in
# chronological order, that have been committed since the input start date.
# This list is used to find all revisions that come after the revision that
# caused the failure and that need to be investigated.
def getPushLog(branch, startDate):
    """Looks at input branch and returns a list of all revisions
	committed since the input start date, sorted chronologically
	by commit date.
	"""
    # Example
    # Get PushLog for 2014-06-16
    # https://hg.mozilla.org/integration/mozilla-inbound/json-pushes?startdate=2014-06-18

    conn = httplib.HTTPSConnection('hg.mozilla.org')
    pushLogURL = "/%s/json-pushes?startdate=%s" % (
        branchPaths[branch], startDate)

    conn.request("GET", pushLogURL)
    pushLogResponse = conn.getresponse()

    pushAll = []
    entries = []

    pushLogJSON = pushLogResponse.read()
    pushLogResponse.close()
    pushLog = json.loads(pushLogJSON)

    # For whatever reason the JSON Loads disturbs the ordering of the entries.
    # The ordering of the entries is crucial since we consider it to be the
    # chronological order of the revisions.
    # We add a step so as to have the final revisions in chronological order
    for entry in pushLog:
        bisect.insort_left(entries, entry, 0, len(entries))

    # pushLog has a ID associated with each push. Each push also has a
    # date associated with it.
    # For now we ignore the dates while considering the pushLogs.
    # Every push also has a set of revision numbers associated with it.
    # We are interested in the last of the revision numbers and only the first
    # 12 characters.
    for entry in entries:
        pushAll.insert(0, pushLog[entry]['changesets'][-1][:12])

    return pushAll

# parseBuildInfo takes input string, buildInfo (buildername), and breaks
# it down into separate strings by platform, build type, and test type.
# Input, branch, is used only to remove the branch from the buildername.
# The buildername is broken down into separate strings so they can be
# used as inputs for other functions.
# Example:
# Input: parseBuildInfo('Windows XP 32-bit mozilla-inbound pgo talos svgr', 'mozilla-inbound')
# Output: ('Windows XP 32-bit', 'opt', 'talos svgr')
def parseBuildInfo(buildInfo, branch):
    """Splits string buildername by branch to return strings platform,
    build type, and test type.
    """
    buildInfoList = buildInfo.split(" " + branch + " ")
    platform = buildInfoList[0]
    buildType = branch.join(buildInfoList[1:])

    types = buildType.split('test')
    buildType, testType = types[0].strip(), 'test'.join(types[1:]).strip()
    buildType = buildType.strip()

    if buildType not in ['opt', 'debug', 'build'] and not testType:
        testType = buildType
        buildType = 'opt'

    for p in platformXRef:
        if re.match(p, platform.strip()):
            return p, buildType, testType
    return '', '', ''

# getMatch takes an input string and list.  The function returns True
# if the string is in the list or if the list is empty.
def getMatch(string, refList):
    """Returns true if refList is empty list or input string is in refList."""
    # If the list is empty default to 'all' and return True.
    if (refList == []):
        return True

    for item in refList:
        # We need exact matches for test bisection.
        # However, if we'd like to have more flexibility we
        # could potentially use regular expresssions to look for matches.
        # if re.match(string.lower(), item.lower()):
        #    return True
        if string == item:
            return True
    return False

# downloadCSetResults takes input strings, branch and revision, and
# downloads all test results for the given revision.
def downloadCSetResults(branch, rev):
    """Downloads all test results for input revision on input branch.
	Returns dictionary containing test results.
	"""
    # Example
    # Get Results for CSet Revision: 3b75b48cbaca
    # https://tbpl.mozilla.org/php/getRevisionBuilds.php?branch=mozilla-inbound&rev=3b75b48cbaca

    conn = httplib.HTTPSConnection('tbpl.mozilla.org')
    csetURL = "/php/getRevisionBuilds.php?branch=%s&rev=%s&showall=1" % (
        branch, rev)
    conn.request("GET", csetURL)
    csetResponse = conn.getresponse()

    csetData = csetResponse.read()
    csetResponse.close()

    try:
        ret = json.loads(csetData)
    except:
        print "Error loading results in JSON Format"
        ret = {}
    return ret

# getCSetReults downloads the test results for the revision and
# saves them in a list.
def getCSetResults(branch, getPlatforms, getTests, getBuildType, rev):
    """Downloads test results dictionary, converts it into a list,
	and returns that list.
	"""
    csetResults = []

    resultData = downloadCSetResults(branch, rev)

    for entry in resultData:
        notes = ''
        if 'result' not in entry:
            continue

        result = entry['result']
        platform, buildType, testType = parseBuildInfo(
            entry['buildername'], branch)

        if not platform:
            continue
        if entry['notes']:
            notes = entry['notes'][0]['note'].replace("'", '')

        if getMatch(testType, getTests) and getMatch(
            platform, getPlatforms) and getMatch(
                buildType, [getBuildType]):

            csetResults.append([
                result, platform, buildType,
                testType, entry['buildername'], notes])
    return csetResults

# runTitanicNormal prints the test results for all revisions
# that were committed starting 'delta' days before the 
# current time.
def runTitanicNormal(runArgs, allPushes):
    """Prints the test results for all revisions that were
	committed starting 'delta' days before the current time.
	"""
    for push in allPushes:
        print 'Getting Results for %s' % (push)
        results = getCSetResults(
            runArgs['branch'], runArgs['platform'],
            runArgs['tests'], runArgs['buildType'], push)
        for i in results:
            print i

# getPotentialPlatforms returns a list of all platforms that the input,
# buildInfo, could have been built on.  First the base platform is
# found by looking in platformXRef, then a list of all potential platforms
# is created by finding all platforms in platformXRef that share the same
# base platform.
def getPotentialPlatforms(builderInfo, branch):
    """Splits buildername to find platform.  Looks in platformXRef to find
	platform's base platform.  Loops though platform XRef to find all platforms
	that share the same base platform and returns a list of those platforms.
	"""
    platform, t, b = parseBuildInfo(builderInfo, branch)
    basePlatform = platformXRef[platform]
    potBuildP = [k for k, v in platformXRef.iteritems() if v == basePlatform]

    # For Windows and OSX the builds are all done on one platform and then
    # the tests are run on the actual desired platform.
    if platformXRef[platform] == 'win7' or platformXRef[platform] == 'win8':
        potBuildP.append('WINNT 5.2')
        potBuildP.append('Windows XP 32-bit')
    elif platformXRef[platform] == 'osx10.6' or \
            platformXRef[platform] == 'osx10.8':
        potBuildP.append('Rev4 MacOSX Lion 10.7')
        potBuildP.append('OS X 10.7')

    return potBuildP

# findIfBuilt determines whether input push has been built already
# by getting all test results for the push.  If there are no results
# or the result was not a success, findIfBuilt returns False.
def findIfBuilt(push, runArgs):
    """Gets test results for push.  If there are no results or the
	result was not a success, returns False.
	"""
    # Possible BuilderName
    # p, t, b = parseBuildInfo(
    #   'Linux x86-64 mozilla-inbound build', args.branch)
    # print p + " : " + t + " : " + b
    # WINNT 5.2 : leak : build
    # WINNT 5.2 : opt : pgo-build
    # Linux x86-64 : opt : debug asan build
    platforms = getPotentialPlatforms(
        runArgs['buildername'], runArgs['branch'])
    if 'pgo' in runArgs['buildername'].lower():
        results = getCSetResults(
            runArgs['branch'], platforms, ['opt'], ['pgo-build'], push)
    elif 'asan' in runArgs['buildername'].lower() and \
            platformXRef[runArgs['platform'][0]] == 'linux64':
        results = getCSetResults(
            runArgs['branch'], platforms, ['opt'], ['asan build'], push)
        # TODO: Figure out what to do with debug asan
        # results = getCSetResults(
        # args.branch, platforms, ['opt'], ['debug asan build'], push)
    elif ' debug ' in runArgs['buildername'].lower():
        results = getCSetResults(
            runArgs['branch'], platforms, ['leak'], ['build'], push)
    else:
        results = getCSetResults(
            runArgs['branch'], platforms, ['build'], [''], push)

    if (results == []) or (results[0] != 'success'):
        return False
    return True

# constructBuildName takes input dictionary, runArgs, that contains
# information on a build and finds relevant info (platform, branch,
# build type) to return a string, buildername, for use in other
# functions.
def constructBuildName(runArgs):
    """Finds relevant info in runArgs dictionary and combines it
	into one string, buildername, which it then returns.
	"""
    if platformXRef[runArgs['platform'][0]] == 'linux32':
        platform = 'Linux'
    elif platformXRef[runArgs['platform'][0]] == 'linux64':
        platform = 'Linux x86-64'
    elif platformXRef[runArgs['platform'][0]] == 'winxp' or 'win7' or 'win8':
        platform = 'WINNT 5.2'
    else:
        platform = platformXRef[runArgs['platform'][0]]

    if 'pgo' in runArgs['buildername'].lower():
        return platform + ' ' + \
            runArgs['branch'] + ' ' + 'pgo-build'
    if 'asan' in runArgs['buildername'].lower() and \
            platformXRef[runArgs['platform'][0]] == 'linux64':
        return platform + ' ' + runArgs['branch'] + \
            ' ' + 'asan build'
    # TODO: Figure out what to do with debug asan
    if ' debug ' in runArgs['buildername'].lower():
        return platform + ' ' + runArgs['branch'] + \
            ' ' + 'leak test build'

# runTitanicAnalysis checks if revision argument is found within the
# specified date range.  If it is not found, runTitanicAnalysis will give
# an error.  Otherwise, runTitanicAnalysis will get test results for each revision
# that comes after the input revision chronologically.  If there are test results,
# the test result is a success, and the revision has a build associated with it,
# runTitanicAnalysis will return.  The outputs of runTitanicAnalysis are two lists;
# a list of all revisions that come after the input revision, up to the
# revision that caused runTitanicAnalysis to return, and a subset of the first list
# that contains all revisions that have no build associated with them.
def runTitanicAnalysis(runArgs, allPushes):
    """Loops through all revisions committed after the input revision
	until it finds a revision with 'success' test results and a build
	associated with it.  Returns two lists; one containing all revisions
	that were seen before the 'success' revision, the other containing all revisions in the 
	first list that have not been built yet.
	"""
    if runArgs['revision'] not in allPushes:
        print 'Revision not found in the current range.'
        print 'Consider increasing range!'
        sys.exit(1)

    unBuiltRevList = []
    revPos = allPushes.index(runArgs['revision'])
    for push in allPushes[revPos+1:]:
        pushResults = getCSetResults(
            runArgs['branch'], runArgs['platform'],
            runArgs['tests'], runArgs['buildType'], push)
        # print pushResults

        if (len(pushResults) > 0):
            revLastPos = allPushes.index(push)
            if (pushResults[0][0] == 'success') and (pushResults[0][2] != ''):
                return allPushes[revPos+1:revLastPos], unBuiltRevList
        if not findIfBuilt(push, runArgs):
            unBuiltRevList.append(push)

    print 'Revision that successfully passed ' + str(runArgs['tests']) + \
        ' not found in the current range. Consider increasing range!'
    sys.exit(1)

# printCommands prints command line arguments that can be input
# when running titanic.
def printCommands(revList, unBuiltRevList, runArgs):
    """Prints command line arguments that can be input when 
	running titanic.
	"""
    for rev in unBuiltRevList:
        builderName = constructBuildName(runArgs)
        print 'python trigger.py --buildername "' + builderName + \
            '" --branch ' + str(runArgs['branch']) + ' --rev ' + str(rev)
    for rev in revList:
        print 'python trigger.py --buildername "' + str(runArgs['buildername']) + \
            '" --branch ' + str(runArgs['branch']) + ' --rev ' + str(rev)

# runTitanic finds all revisions on the input branch that were committed
# starting 'delta' days ago.  If a revision was given as an argument to
# titanic, runTitanic will print command line arguments that can then be
# run for each revision that needs to be investigated.  If no revision
# was given, runTitanic will print test results for all revisions committed
# starting 'delta' days ago.
def runTitanic(runArgs):
    """Checks if a revision was input into titanic.  If so, prints potential
	command line arguments that can be run for each revision that was committed
	after the input revision.  Otherwise, prints test results for all revisions
	committed in the specified date range.
	""" 
    # Default to a range of 1 day
    startDate = datetime.datetime.utcnow() - \
        datetime.timedelta(hours=(runArgs['delta']*24))

    allPushes = getPushLog(runArgs['branch'], startDate.strftime('%Y-%m-%d'))
    # print allPushes

    if runArgs['revision']:
        revList, unBuiltRevList = runTitanicAnalysis(runArgs, allPushes)
        printCommands(revList, unBuiltRevList, runArgs)
    else:
        runTitanicNormal(runArgs, allPushes)

# populateArgs enters input data (branch, buildername, revision, delta) 
# into dictionary (runArgs).  populateArgs also breaks buildername into
# platform, test, and build type, then adds that data to runArgs.  
# runArgs will give an error if the buildername is blank or the
# branch is not in the buildername.
def populateArgs(branch, buildername, revision, delta):
    """Splits buildername into platform, build type, and test.  Then
	enters those 3 parameters, along with all other arguments into
	dictionary, runArgs, and returns it.
	"""
    if buildername == '':
        print 'You need to specify the buildername!'
        sys.exit(1)
    if branch not in buildername:
        print 'Please specify the branch you are interested in.'
        print 'Branch defaults to \'mozilla-central\''
        sys.exit(1)

    runArgs = {
        'branch': branch,
        'revision': revision,
        'delta': delta,
        'buildername': buildername,
        'platform': [],
        'tests': [],
        'buildType': ''
    }

    platform, buildType, test = parseBuildInfo(buildername, branch)

    runArgs['platform'] = [platform]
    runArgs['tests'] = [test]
    runArgs['buildType'] = buildType

    return runArgs

# verifyArgs confirms whether or not the titanic arguments are valid before running.
# If the branch or platform is unknown, verifyArgs will give an error.  Otherwise,
# a dictionary, runArgs, is populated with the verified input data and is returned.
def verifyArgs(args):
    """Confirms whether or not input branch and platforms are valid.  If not, 
	prints an error message and exits.  Otherwise populates a dictionary with input
	data and returns it.
	"""
    if args.branch not in branchPaths:
        print 'error: unknown branch: %s' % (args.branch)
        sys.exit(1)

    flag = True
    for p in args.platform:
        flag = flag and getMatch(p, platforms)
        if flag is False:
            print 'error: unknown platform: %s' % (p)
            sys.exit(1)

    runArgs = {
        'branch': args.branch,
        'platform': args.platform,
        'tests': args.tests,
        'revision': args.revision,
        'buildType': args.buildType,
        'delta': args.delta,
        'buildername': args.buildername
    }

    if args.revision:
        return populateArgs(
            args.branch, args.buildername, args.revision, args.delta)

    return runArgs

# setupArgsParser creates the command line arguments that are valid
# when running titanic.
def setupArgsParser():
    """Defines what command line arguments titanic can accept."""
    parser = argparse.ArgumentParser(description='Run Titanic')
    parser.add_argument(
        '-b', action='store', dest='branch', default='mozilla-central',
        help='Branch for which to retrieve results.')
    parser.add_argument('-t', action='append', dest='tests', default=[],
                        help='Tests for which to retreive results. \
                             You can specify more than one if you are \
                             not running in analysis mode.')
    parser.add_argument('-p', action='append', dest='platform', default=[],
                        help='Platforms for which to retrieve results. \
                             You can specify more than one if you are \
                             not running in analysis mode.')
    parser.add_argument('-n', action='store', dest='buildType', default='opt',
                        help='Platforms for which to retrieve results.')
    parser.add_argument('-d', action='store', dest='delta', default=1,
                        type=int, help='Range for which to retrieve results. \
                             Range in days.')
    parser.add_argument('-r', action='store', dest='revision', default=0,
                        help='Revision for which to start bisection with!')
    parser.add_argument('--bn', action='store', dest='buildername', default='',
                        help='Buildername for which to run analysis.')
    return parser.parse_args()


# API: runAnalysis
# ARGUMENTS: branch, buildername, revision, delta
# RETURN: revList, buildList
#     revList : List of revisions that we need to retrigger the job.
#     buildList: List of revisions that we need to build before we
#         trigger the job.
# NOTE: Argument 'delta' is optional and will default to 7 if not provided.
def runAnalysis(branch, buildername, revision, delta=7):
    runArgs = populateArgs(branch, buildername, revision, delta)
    startDate = datetime.datetime.utcnow() - \
        datetime.timedelta(hours=(runArgs['delta']*24))
    allPushes = getPushLog(runArgs['branch'], startDate.strftime('%Y-%m-%d'))
    return runTitanicAnalysis(runArgs, allPushes)


# API: getBuildCommands
# ARGUMENTS: branch, buildername, revision
# RETURN: Command (string) that can be executed
#     The command will be a string that can be run on the terminal
# NOTE: You need to specify the buildername for test you would like to run.
# For example, 'Windows XP 32-bit mozilla-inbound pgo talos svgr' is
# a buildername that can be supplied.
# Based on this getBuildCommands will revrt back with the appropriate
# buildCommand that could be run
def getBuildCommands(branch, buildername, revision):
    runArgs = populateArgs(branch, buildername, revision, 1)
    buildName = constructBuildName(runArgs)
    return 'python trigger.py --buildername "' + buildName + '" --branch ' \
        + str(runArgs['branch']) + ' --rev ' + str(revision)


# API: getTriggerCommands
# ARGUMENTS: branch, buildername, revision
# RETURN: Command (string) that can be executed
#     The command will be a string that can be run on the terminal
def getTriggerCommands(branch, buildername, revision):
    runArgs = populateArgs(branch, buildername, revision, 1)
    return 'python trigger.py --buildername "' + buildername + '" --branch ' \
        + branch + ' --rev ' + str(revision)


# API: triggerBuild
# ARGUMENTS: branch, buildername, revision
# RETURN: status code
# NOTE: You need to specify the buildername for test you would like to run.
# For example, 'Windows XP 32-bit mozilla-inbound pgo talos svgr' is
# a buildername that can be supplied.
# Based on this triggerBuild will trigger off an appropriate build which
# will allow you to run the test once the build is complete
def triggerBuild(branch, buildername, revision):
    runArgs = populateArgs(branch, buildername, revision, 1)
    buildName = constructBuildName(runArgs)
    return triggerJob(branch, buildName, revision)


# API: triggerJob
# ARGUMENTS: branch, buildername, revision
# RETURN: status code
def triggerJob(branch, buildername, revision):
    payload = {}
    payload['properties'] = json.dumps(
        {"branch": branch, "revision": revision})

    url = r'''https://secure.pub.build.mozilla.org/buildapi/self-serve/%s/builders/%s/%s''' % (
        branch, buildername, revision)
    r = requests.post(url, data=payload)
    return r.status_code


if __name__ == '__main__':
    args = setupArgsParser()
    runArgs = verifyArgs(args)
    runTitanic(runArgs)
