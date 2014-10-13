#titanic: Mozilla Test Bisection

#About Titanic

Titanic is designed around the Mozilla build and test systems. The goal of Titanic is to be able to bisect holes in tests for revisions submitted. Long term, titanic is not only to be a standalone tool but also allow have hooks for other tools to plug in.

The main idea is to lock into revisions for tests that did not run. Titanic takes in a revision to begin the analysis from. Titanic trudges back from that point to the last revision for which the test was successfully run.

## Working

After being given this data, titanic will trudge through the revisions and find the all the revisions for which the test did not successfully run. It will also determine if a build needs to be done for the revision and platform in question.

# Installation

To run ''Titanic'' you'll need to install the Python 'requests' and 'BeautifulSoup4' packages

You can do this by running the following command after you have installed 'pip'

    pip install requests
    pip install BeautifulSoup4

## Setting Up

To make use of the trigger commands that titanic provides you should add the following line in ~/.netrc

    machine secure.pub.build.mozilla.org login <email> password <password>

In case you don't want to do that you can manually enter the LDAP username and password when prompted!

## Installing the Server: Local Usage

In case you want to use the default server hosted by Mozilla and don't want to run your own small server then this section of the installation is optional.

To run the server you need to install 'flask'

    pip install flask

In addition to get the server running in apache, you need to create the database and assign it proper permissions:
```
ls -la db/backfill-db.sqlite
-rwxrwxr-- 1 www-data www-data 3072 Aug 26 18:23 db/backfill-db.sqlite
```

Here is an example Apache configuration:
```
<VirtualHost *:8314>
	ServerAdmin webmaster@localhost

	DocumentRoot /home/ubuntu/titanic/static

	<Directory /home/ubuntu/titanic/static/>
		Order allow,deny
		Allow from all
        Require all granted
        Header set Access-Control-Allow-Origin "*"
	</Directory>

	WSGIScriptAlias / /home/ubuntu/titanic/static/titanic.wsgi

	ErrorLog ${APACHE_LOG_DIR}/error.log

	# Possible values include: debug, info, notice, warn, error, crit,
	# alert, emerg.
	LogLevel warn

	CustomLog ${APACHE_LOG_DIR}/access.log combined
</VirtualHost>
```

# Usage

There are various ways to use Titanic.

## Using the WebUI

You can use the WebUI at the following location to make new requests. If you choose to use this, then the server will take care of the rest and trigger the builds and jobs as needed.

    New Requests: http://54.215.155.53:8314/new_request

You can look at the active jobs at the following location

    Active Requests: http://54.215.155.53:8314/active_jobs

This is the easiest way to use Titanic and if you are unsure of what to do, this is probably the way to go.

## Using Scripts

You can use titanic.startBackfill API to queue jobs with the server.

A good example would be to look at the code in https://github.com/gakiwate/titanic/blob/master/run.py You can use run.py using the following command.

    python run.py -r 894b7372561d --bn 'Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-2' -b 'mozilla-inbound'

## Using Locally with WebUI

You can use ''Titanic'' locally as well with the web interface. For that ensure you have installed flask. Start up the server using the command.

    python server.py

You will then we able to create requests and active jobs at

```
    New Requests: http://0.0.0.0:8314/new_request
    Active Requests: http://0.0.0.0:8314/active_jobs
```

However, to ensure that the requests get processed you need to run backfill.py in a cron job. A hack would be to run backfill.py in a while loop with some sleep thrown in.

You will also be able to use the scripts to queue jobs. All you need to do is change the server address to face the local server.

## Standalone Usage

To use titanic in the standalone mode, you need to run the following command

    python titanic.py -r [revision] -b [branch] --bn [buildername] -d [range]

== Example ==
For the example below we would like to know how to backfill mochitest-2 for Linux x64 <br>

    python titanic.py -r 894b7372561d --bn 'Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-2' -d 10 -b 'mozilla-inbound'

Titanic goes through the tests and figures no builds need to be made and the following tests need to be run! It prompts you the commands that can be used to run the tests. <br>

```
    python trigger.py --buildername "Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-2" --branch mozilla-inbound --rev 3a545eb9828b --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409081492/firefox-34.0a1.en-US.linux-x86_64.tar.bz2 --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409081492/firefox-34.0a1.en-US.linux-x86_64.tests.zip
    python trigger.py --buildername "Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-2" --branch mozilla-inbound --rev b005b4e38525 --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409081034/firefox-34.0a1.en-US.linux-x86_64.tar.bz2 --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409081034/firefox-34.0a1.en-US.linux-x86_64.tests.zip
    python trigger.py --buildername "Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-2" --branch mozilla-inbound --rev 4354d5ed2311 --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409080167/firefox-34.0a1.en-US.linux-x86_64.tar.bz2 --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409080167/firefox-34.0a1.en-US.linux-x86_64.tests.zip
    python trigger.py --buildername "Ubuntu VM 12.04 x64 mozilla-inbound debug test mochitest-2" --branch mozilla-inbound --rev 7f68752ffe1e --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409079043/firefox-34.0a1.en-US.linux-x86_64.tar.bz2 --file http://ftp.mozilla.org/pub/mozilla.org/firefox/tinderbox-builds/mozilla-inbound-linux64-debug/1409079043/firefox-34.0a1.en-US.linux-x86_64.tests.zip
```

#Common Issues
If you are using ''Titanic'' locally and get an error code of 401 it most probably means that you possibly could have supplied incorrect credentials either in ~/.netrc or in backfill.py

    Status Code: 401 -- Wrong username and password

#Titanic as a Library
Titanic can also be used as a library. To use as a library you can simply import titanic and use one of the APIs listed below as per the needs.

    import titanica

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
