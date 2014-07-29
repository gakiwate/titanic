#titanic: Mozilla Test Bisection

#About Titanic

Titanic is designed primarily around the Mozilla build and test systems. The 
goal of Titanic is to be able to bisect holes in tests for revisions submitted.
Long term, titanic is not only to be a standalone tool but also allow have
hooks for other tools to plug in.

The main idea is to lock into revisions for tests that did not run. Titanic
takes in a revision to begin the analysis from - this usually is a revision
that marks the start of issues for some tests. In addition to this, the branch,
platform and test are specified.

##Working

After this titanic will trudge through the revisions and find the all the
revisions for which the test did not successfuly run. It will also determine
if a build needs to be done for the revision and platform in question. 

#Installation

You'll need to install the Python 'requests' package

You can do this by running the following command after you have installed 'pip'
    pip install requests

To use titanic in analysis mode, you need to run the following command
    python titanic.py -r [revision] -b [branch] --bn [buildername] -d [range]

#Standalone Usage

    For the example below, titanic extracts information as follows

    python titanic.py -r 12b60cc85be1 -b mozilla-inbound -d 6 --bn "Ubuntu HW 12.04 mozilla-inbound pgo talos other"

    Revision: 12b60cc85be1
    Branch: mozilla-inbound
    Platform: Ubuntu HW 12.04
    Build Type: pgo
    Test: talos other

#Titanic as a Library
Titanic can also be used as a library. To use as a library you can simply import titanic and use one of the APIs listed below as per the needs.

    import titanic

##Branch
The branch is the tree on which the test and revision to be investigated was run.
Currently the branches can be one of the following
### mozilla-central
### mozilla-inbound
### b2g-inbound
### fx-team

##Buildername
The buildername is the buildername of the test you are investigating.
For example, a buildername like the one below can be supplied.

    'Windows XP 32-bit mozilla-inbound pgo talos svgr'

It is also important to note that, the buildername used in all the APIs are the buildernames for the tests that are being investigated; even for the build APIs, the API will take the normal buildername and return the appropriate build command that can be run manually or trigger the appropriate build after the completion of which you can retrigger the jobs.

##Revision
This is the revision that is under consideration

##Delta
This is the range - in days that Titanic runs the analysis for. Thus it is important to make sure that delta is big enough so as to get the window being investigated under analysis.

#The APIs
##runAnalysis
ARGUMENTS: branch, buildername, revision, delta
RETURN: revList, buildList
revList: List of revisions for which we need to retrigger the job.
buildList: List of revisions that we need to build before we trigger the job.
NOTE: Argument 'delta' is optional and will default to 7 if not provided.

    titanic.runAnalysis(branch, buildername, revision, delta)

The above command can be used after we import titanic.

##getBuildCommands
ARGUMENTS: branch, buildername, revision
RETURN: Command (string) that can be executed. The command will be a string that can be run on the terminal
You need to specify the buildername for test you would eventuallylike to run. Based on this getBuildCommands will return with the appropriate buildCommand that could be run

    titanic.getBuildCommands(branch, buildername, revision)

The above command can be used after we import titanic.

##getTriggerCommands
ARGUMENTS: branch, buildername, revision
RETURN: Command (string) that can be executed The command will be a string that can be run on the terminal

    titanic.getTriggerCommands(branch, buildername, revision):

The above command can be used after we import titanic.

##triggerBuild
ARGUMENTS: branch, buildername, revision
RETURN: status code
You need to specify the buildername for test you would like to run. Based on this triggerBuild will trigger off an appropriate build which will allow you to run the test once the build is completed

    titanic.triggerBuild(branch, buildername, revision):

The above command can be used after we import titanic.

##triggerJob
ARGUMENTS: branch, buildername, revision
RETURN: status code

    titanic.triggerJob(branch, buildername, revision):

The above command can be used after we import titanic.

#Common Issues

##Increasing Range

    Revision not found in the current range. Consider increasing range!

In this case, increase the range by increasing the number of days to analyze using '-d'

 
