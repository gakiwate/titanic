import titanic
import sys
import argparse

# Optinally you can direct it to your own local server
# server = 'http://0.0.0.0:8314/'
server = 'http://54.215.155.53:8314/'

def run(args):
    titanic.startBackfill(args.branch, args.buildername, args.revision, server)
    print 'Job Queued...'
    print 'The jobs should be listed at: ' + server + 'active_jobs'


def verifyArgs(args):
    if not args.revision:
        print 'Issue with revision.'
        return False
    if args.branch not in args.buildername:
        print 'Make sure buildername and branches match'
        return False

    return True


def setupArgsParser():
    parser = argparse.ArgumentParser(description='Run Titanic')
    parser.add_argument(
        '-b', action='store', dest='branch', default='mozilla-central',
        help='branch on which to run backfill')
    parser.add_argument(
        '-r', action='store', dest='revision', default=0,
        help='Revision for which to start bisection with!')
    parser.add_argument(
        '--bn', action='store', dest='buildername', default='',
        help='buildername for which to run analysis.')
    return parser.parse_args()

if __name__ == '__main__':
    args = setupArgsParser()
    if not verifyArgs(args):
        print 'Look up Usage...'
        sys.exit(1)
    run(args)
