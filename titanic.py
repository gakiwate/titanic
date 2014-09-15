import os
import json
import httplib
import re
import urllib
import argparse
import sys
import datetime
import glob
import re
import bisect
import requests

#
# The following strings are used to
# read version infromation from the build directory
#
VERSION_GLOB = '*-*.*'
VERSION_RE = "(?<=-)[0-9]+\.\w*"
DEFAULT_VERSION = "35.0a1"

branchPaths = {
    'mozilla-aurora': 'releases/mozilla-aurora',
    'mozilla-beta': 'releases/mozilla-beta',
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

def getPushLog(branch, startDate):
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


def parseBuildInfo(buildInfo, branch):
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


def getMatch(string, refList):
    # If the list is empty default to 'all' and return True.
    if (refList == []):
        return True

    if (string == '') and (refList == ['']):
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


def downloadCSetResults(branch, rev):
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


def getBuildLoc(logLoc):
    return logLoc.rsplit('/', 1)[0]


def getCSetResultsBuild(branch, getPlatforms, getTests, getBuildType, rev):
    csetResults = []

    resultData = downloadCSetResults(branch, rev)

    for entry in resultData:
        notes = ''
        if 'result' not in entry:
            continue

        result = entry['result']
        platform, testType, buildType = parseBuildInfo(
            entry['buildername'], branch)

        if not platform:
            continue
        if entry['notes']:
            notes = entry['notes'][0]['note'].replace("'", '')

        if getMatch(testType, getTests) and getMatch(
            platform, getPlatforms) and getMatch(
                buildType, getBuildType):

            buildLoc = getBuildLoc(entry['log'])
            csetResults.append([
                result, platform, buildType,
                testType, entry['buildername'], buildLoc, notes])
    return csetResults


def getCSetResults(branch, getPlatforms, getTests, getBuildType, rev):
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

            buildLoc = getBuildLoc(entry['log'])
            csetResults.append([
                result, platform, buildType,
                testType, entry['buildername'], buildLoc, notes])
    return csetResults


def runTitanicNormal(runArgs, allPushes):
    for push in allPushes:
        print 'Getting Results for %s' % (push)
        results = getCSetResults(
            runArgs['branch'], runArgs['platform'],
            runArgs['tests'], runArgs['buildType'], push)
        for i in results:
            print i


def getPotentialPlatforms(builderInfo, branch):
    platform, t, b = parseBuildInfo(builderInfo, branch)
    basePlatform = platformXRef[platform]
    potBuildP = [k for k, v in platformXRef.iteritems() if v == basePlatform]

    # For Windows and OSX the builds are all done on one platform and then
    # the tests are run on the actual desired platform.
    if platformXRef[platform] == 'win7' or platformXRef[platform] == 'win8':
        potBuildP.append('WINNT 5.2')
        potBuildP.append('Windows XP 32-bit')
    elif platformXRef[platform] == 'osx10.6' or \
            platformXRef[platform] == 'osx10.7' or \
            platformXRef[platform] == 'osx10.8':
        potBuildP.append('OS X 10.7')
        potBuildP.append('Rev4 MacOSX Lion 10.7')

    return potBuildP


def findBuildStatus(push, runArgs, statusType):
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
        # In the mozilla-aurora and mozilla-beta branches
        # all builds are PGO thus we do not specifically
        # need to build a PGO build
        if runArgs['branch'] == 'mozilla-aurora' or \
                runArgs['branch'] == 'mozilla-beta':
            results = getCSetResultsBuild(
                runArgs['branch'], platforms, ['build'], [''], push)
        else:
            results = getCSetResultsBuild(
                runArgs['branch'], platforms, ['opt'], ['pgo-build'], push)
    elif 'asan' in runArgs['buildername'].lower() and \
            platformXRef[runArgs['platform'][0]] == 'linux64':
        results = getCSetResultsBuild(
            runArgs['branch'], platforms, ['opt'], ['asan build'], push)
        # TODO: Figure out what to do with debug asan
        # results = getCSetResults(
        # args.branch, platforms, ['opt'], ['debug asan build'], push)
    elif ' debug ' in runArgs['buildername'].lower():
        results = getCSetResultsBuild(
            runArgs['branch'], platforms, ['leak'], ['build'], push)
    else:
        results = getCSetResultsBuild(
            runArgs['branch'], platforms, ['build'], [''], push)

    if (results == []):
        return [False, None]

    for result in results:
        if result[0] == statusType:
            return [True,result]

    return [False, None]


def constructBuildName(runArgs):
    if platformXRef[runArgs['platform'][0]] == 'linux32':
        platform = 'Linux'
    elif platformXRef[runArgs['platform'][0]] == 'linux64':
        platform = 'Linux x86-64'
    elif platformXRef[runArgs['platform'][0]] == 'winxp' or \
            platformXRef[runArgs['platform'][0]] == 'win7' or \
            platformXRef[runArgs['platform'][0]] == 'win8':
        platform = 'WINNT 5.2'
    elif platformXRef[runArgs['platform'][0]] == 'osx10.6' or \
            platformXRef[runArgs['platform'][0]] == 'osx10.7' or \
            platformXRef[runArgs['platform'][0]] == 'osx10.8':
        platform = 'OS X 10.7'
    else:
        platform = platformXRef[runArgs['platform'][0]]

    if 'pgo' in runArgs['buildername'].lower():
        # In the mozilla-aurora and mozilla-beta branches
        # all builds are PGO thus we do not specifically
        # need to build a PGO build
        if runArgs['branch'] == 'mozilla-aurora' or \
                runArgs['branch'] == 'mozilla-beta':
            return platform + ' ' + runArgs['branch'] + \
                ' ' + 'build'

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

    return platform + ' ' + runArgs['branch'] + \
        ' ' + 'build'


def runTitanicAnalysis(runArgs, allPushes,revLimit = 10):
    if runArgs['revision'] not in allPushes:
        print 'Revision not found in the current range.'
        print 'Consider increasing range!'
        # FIXME: Need to return an error
        return '',''

    unBuiltRevList = []
    revPos = allPushes.index(runArgs['revision'])

    for push in allPushes[revPos+1:]:
        pushResults = getCSetResults(
            runArgs['branch'], runArgs['platform'],
            runArgs['tests'], runArgs['buildType'], push)

        if (len(pushResults) > 0):
            revLastPos = allPushes.index(push)
            if (pushResults[0][0] == 'success') and (pushResults[0][2] != ''):
                return allPushes[revPos+1:revLastPos], unBuiltRevList
        if not findBuildStatus(push, runArgs, 'success')[0]:
            unBuiltRevList.append(push)

    print 'Revision that successfully passed ' + str(runArgs['tests']) + \
        ' not found in the current range. Consider increasing range!'
    # FIXME: Need to return an error
    return '',''


def printCommands(revList, unBuiltRevList, runArgs):
    for rev in unBuiltRevList:
        print getBuildCommands(runArgs['branch'], runArgs['buildername'], rev)

    if unBuiltRevList != []:
        print 'Trigger Builds. Wait for all builds to complete before proceeding...'
        return

    for rev in revList:
        print getTriggerCommands(runArgs['branch'], runArgs['buildername'], rev)


def runTitanic(runArgs):
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


def populateArgs(branch, buildername, revision, delta):
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
        'buildType': '',
    }

    platform, buildType, test = parseBuildInfo(buildername, branch)

    runArgs['platform'] = [platform]
    runArgs['tests'] = [test]
    runArgs['buildType'] = buildType

    return runArgs


def verifyArgs(args):
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
        'buildername': args.buildername,
    }

    if args.revision:
        return populateArgs(
            args.branch, args.buildername, args.revision, args.delta)

    return runArgs


def setupArgsParser():
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


# Can be sped up by http://requests-cache.readthedocs.org/en/latest/user_guide.html
def taskStatus(branch, buildername, revision, statusType, auth = None):
    url = ('https://secure.pub.build.mozilla.org/builddata/buildjson/builds-%s.js') % (statusType)
    r = requests.get(url)

    if 400 <= int(r.status_code) < 500:
        print 'The task could not be triggered.'
        return False

    try:
        tasks = json.loads(r.text)
    except:
        return False

    if branch not in tasks[statusType]:
        return False

    if revision not in tasks[statusType][branch]:
        return False

    for task in tasks[statusType][branch][revision]:
        if task['buildername'] == buildername:
            return True

    return False


def isBuildPending(branch, buildername, revision, auth = None):
    runArgs = populateArgs(branch, buildername, revision, 1)
    buildName = constructBuildName(runArgs)
    return isJobPending(branch, buildName, revision, auth)


def isBuildRunning(branch, buildername, revision, auth = None):
    runArgs = populateArgs(branch, buildername, revision, 1)
    buildName = constructBuildName(runArgs)
    return isJobRunning(branch, buildName, revision, auth)


def isJobPending(branch, buildername, revision, auth = None):
    return taskStatus(branch, buildername, revision, 'pending', auth)


def isJobRunning(branch, buildername, revision, auth = None):
    return taskStatus(branch, buildername, revision, 'running', auth)


def isBuildSuccessful(branch, buildername, revision):
    runArgs = populateArgs(branch, buildername, revision, 1)
    return findBuildStatus(revision, runArgs, 'success')[0]


def findBuildLocation(branch, buildername, revision):
    runArgs = populateArgs(branch, buildername, revision, 1)
    status, result = findBuildStatus(revision, runArgs, 'success')
    if not status:
        print 'Please make sure that there is a build for revision: ' + revision
        ## FIXME: Needs to return a proper error
        return ''

    return result[5]

def getVersionInfo(buildLocation):
    files = glob.glob('%s/%s' % (buildLocation, VERSION_GLOB))

    if not files:
      ## if no files are found to extract version number
      ## return the default version number
      return DEFAULT_VERSION

    targetFile = files[0] ## any one of the file is fine. Using the first one
    version_re = re.search(VERSION_RE, targetFile)

    if not version_re:
      ## if extracting version number from the filename fails
      ## return the default version number
      return DEFAULT_VERSION

    version = version_re.group(0)

    return version

def getBuildInfo(branch, buildername, revision):
    runArgs = populateArgs(branch, buildername, revision, 1)
    ftp = findBuildLocation(branch, buildername, revision)
    version = getVersionInfo(ftp)

    version = getVersionInfo(ftp)

    if platformXRef[runArgs['platform'][0]] == 'winxp' or \
            platformXRef[runArgs['platform'][0]] == 'win7':
        extension = 'zip'
        platform = 'win32'
    elif platformXRef[runArgs['platform'][0]] == 'osx10.6' or \
            platformXRef[runArgs['platform'][0]] == 'osx10.7' or \
            platformXRef[runArgs['platform'][0]] == 'osx10.8':
        extension = 'dmg'
        platform = 'mac'
        if runArgs['buildType'] == 'debug':
            platform = 'mac64'
    elif platformXRef[runArgs['platform'][0]] == 'linux64':
        extension = 'tar.bz2'
        platform = 'linux-x86_64'
    elif platformXRef[runArgs['platform'][0]] == 'linux32':
        extension = 'tar.bz2'
        platform = 'linux-i686'

    return ftp, version, platform, extension


def getInstallerLoc(branch, buildername, revision):
    ftp, version, platform, extension = getBuildInfo(branch, buildername, revision)
    buildLoc = "%s/firefox-%s.en-US.%s.%s" % (ftp, version, platform, extension)
    return buildLoc


def getTestsZipLoc(branch, buildername, revision):
    ftp, version, platform, extension = getBuildInfo(branch, buildername, revision)
    testLoc = "%s/firefox-%s.en-US.%s.tests.zip" % (ftp, version, platform)
    return testLoc


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
    buildName = constructBuildName(runArgs)
    return 'python trigger.py --buildername "' + buildName + '" --branch ' \
        + str(branch) + ' --rev ' + str(revision)


# API: getTriggerCommands
# ARGUMENTS: branch, buildername, revision
# RETURN: Command (string) that can be executed
#     The command will be a string that can be run on the terminal
def getTriggerCommands(branch, buildername, revision):
    if 'talos' in buildername:
        return 'python trigger.py --buildername "' + str(buildername) + \
                '" --branch ' + str(branch) + ' --rev ' + str(revision) + \
                ' --file ' + getInstallerLoc(branch, buildername, revision) 
    else:
        return 'python trigger.py --buildername "' + str(buildername) + \
                '" --branch ' + str(branch) + ' --rev ' + str(revision) + \
                ' --file ' + getInstallerLoc(branch, buildername, revision) + \
                ' --file ' + getTestsZipLoc(branch,buildername, revision) 

# API: triggerBuild
# ARGUMENTS: branch, buildername, revision
# RETURN: status code
# NOTE: You need to specify the buildername for test you would like to run.
# For example, 'Windows XP 32-bit mozilla-inbound pgo talos svgr' is
# a buildername that can be supplied.
# Based on this triggerBuild will trigger off an appropriate build which
# will allow you to run the test once the build is complete
def triggerBuild(branch, buildername, revision, auth = None):
    runArgs = populateArgs(branch, buildername, revision, 1)
    buildName = constructBuildName(runArgs)
    payload = {}
    payload['properties'] = json.dumps(
        {"branch": branch, "revision": revision})
    return triggerTask(branch, buildName, revision, payload, auth)


def triggerJob(branch, buildername, revision, auth = None):
    files = []
    payload = {}
    payload['properties'] = json.dumps(
        {"branch": branch, "revision": revision})

    files.append(getInstallerLoc(branch, buildername, revision))
    if 'talos' not in buildername:
        files.append(getTestsZipLoc(branch, buildername, revision))
    payload['files'] = json.dumps(files)
    return triggerTask(branch, buildername, revision, payload, auth)


# API: triggerTask
# ARGUMENTS: branch, buildername, revision
# RETURN: status code
def triggerTask(branch, buildername, revision, payload, auth = None):

    url = r'''https://secure.pub.build.mozilla.org/buildapi/self-serve/%s/builders/%s/%s''' % (
        branch, buildername, revision)
    r = requests.post(url, data=payload, auth=auth)
    if 400 <= int(r.status_code) < 500:
        print 'The task could not be triggered.'
        return r.status_code

    print 'Your return code is: %s' % r.status_code
    print 'https://secure.pub.build.mozilla.org/buildapi/revision/%s/%s' % (branch, revision)
    return r.status_code

# API: rangeFill
# ARGUMENTS: branch, buildername, startRev, endRev, delta
# Return: revBetweenList, revBuildLast
# rangeFill take in a start revision and an end revision
# then return a list of revisions between the two revision
# and a list of builds that are needed
def rangeFill(branch, buildername, startRev, endRev, delta=30):
    ## 1. get all push logs
    allPushes = []
    startDate = datetime.datetime.utcnow() - \
                    datetime.timedelta(hours=delta*24)
    allPushes = getPushLog(branch, startDate.strftime('%Y-%m-%d'))

    ## 2. look for existence of startRev/endRev
    if startRev not in allPushes or endRev not in allPushes:
        return [], []

    ## 3. conduct analysis. adapted from runTitanicAnalysis
    unBuiltRevList = []

    ## note:
    ## startRev = revision to begin searching. That is, this is an older revision than endRev
    ## endRev   = revision to "stop" search. That is, the is a newer revision than startRev
    ## However, allPushes is sorted reverse-chronologically. Hence we have
    ## allPushses = [..., endRev, ..., startRev, ...]
    ## Hence, revPos_start looks for the index of endRev, and vice versa
    revPos_start = allPushes.index(endRev)
    revPos_end = allPushes.index(startRev)

    if revPos_start > revPos_end:
        print "warning: startRev is more recent than endRev (did you reverse them?)"
        return [], []

    pushesToAnalyze = allPushes[revPos_start:revPos_end+1]
    runArgs = {'buildername': buildername, "branch": branch}
    for push in pushesToAnalyze:
        print "analyzing", push
        if not findBuildStatus(push, runArgs, 'success')[0]:
            unBuiltRevList.append(push)

    return allPushes[revPos_start:revPos_end+1], unBuiltRevList

# server = '54.215.155.53:8314/'
def startBackfill(branch, buildername, revision, server):
    data = {'branch': branch, 'buildername': buildername, 'revision': revision}
    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}
    r = requests.post(server + 'new_request', data=json.dumps(data), headers=headers)
    return r.status_code

if __name__ == '__main__':
    args = setupArgsParser()
    runArgs = verifyArgs(args)
    runTitanic(runArgs)
