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

#Installation and Usage

To run titanic you don't need to install any additional packages except Python.

To use titanic in analysis mode, you need to run the following command
    python titanic.py -r [revision] -b [branch] --bn [buildername] -d [range]

##Example

    For the example below, titanic extracts information as follows

    python titanic.py -r 12b60cc85be1 -b mozilla-inbound -d 6 --bn "Ubuntu HW 12.04 mozilla-inbound pgo talos other"

    Revision: 12b60cc85be1
    Branch: mozilla-inbound
    Platform: Ubuntu HW 12.04
    Build Type: pgo
    Test: talos other

#Common Issues

##Increasing Range

    Revision not found in the current range. Consider increasing range!

In this case, increase the range by increasing the number of days to analyze using '-d'

 
