#!/usr/bin/env python3

import os
import sys
import argparse
import subprocess

import gitlab
import psycopg2

import aresutil


# for debug only
import pprint
pp = pprint.PrettyPrinter(indent=4)


debug      = 100                          # as the name suggests
operator   = os.environ['USER'] or "N/A"  # usernaem of the user doing this deployment
deployjira = "N/A"                        # default for filling depoyevents table
exitfuncname  = 'revert_hook'                # name of function to run before drop schema
initfuncname  = 'init_hook'                  # name of function to run after installation




# test connection to gitlab by creating a gitlab object
try:
    glab = gitlab.Gitlab("gitlab.affinitas.de", token="Zcz799pMXyj4S6DUauy7") # glab is my gitlabobject
except:
    print("failed: Can not connect to GITLAB")
    exit(1)

# test connection to ARESdb
# ares is treated sort of stateless one connetion per query
try:
    aresutil.ares_get("select %s", (1,))
except:
    print("failed: Can not connect to ARES")
    exit(1)


# parse arguments
parser = argparse.ArgumentParser(description="Install into managed databases")
# what to deploy
parser.add_argument( '-p', '--projectpath', help="project path group/project")                          # could be only arguments
parser.add_argument( '-b', '--branch'     , help="the branch to deploy")                                # is there a default ??
# where to deply
parser.add_argument( '-c','-f','--flavour', default="ed_live"  , help="The flavour of database you want to deploy to"      ) #
parser.add_argument( '-d', '--adgroup'    , action='append'    , help="AppDomainGroups to deploy to exclusive"             ) #  2 character style
parser.add_argument( '-e', '--exclude'    , action='append'    , help="AppDomainGoups you want excluded from deployment"   ) #  as before
parser.add_argument( '-a', '--concern'    , default="alpha"    , help="the area of concert the databases are selecetd from") #  only one, default is alpha
parser.add_argument( '-D', '--dbname'     , action='append'    , help="name of the database known to ARES"                 ) #  mult
# general switches
parser.add_argument( '-n', '--dryrun'     , action='store_true', help ="try installation but do finally rollback "         ) #
parser.add_argument( '-t', '--test'       , action='store_true', help="test commection to all selected databases"          ) #
parser.add_argument( '-v', '--verbose'    , action='store_true', help="more information on peocessing"                     ) #  really?
parser.add_argument( '-V', '--version'    , action='store_true', help="print version and exit")                              #
# from bash based deploy inherited
# parser.add_argument( '-f', '--file'       , help="")
# parser.add_argument( '-F', '--filelist'   , help="")
# parser.add_argument( '-u', '--user'       , help="override the database owner ")
# parser.add_argument( '-n', '--noreport'   , help="do not write report into deployevents")
args = parser.parse_args()

if args.verbose:
    debug = debug + 10

if  debug > 120:
    print(args, file=sys.stderr)


if args.version:
    print("Version: 00.00.00")
    exit(0)

if args.dryrun and debug > 1:
    print("Starting dry-run; will not commit")

if args.test:
    tgtlist = aresutil.ares_get("SELECT givenname, codecase, concern, connectstring FROM dba_resource.connect_deployment", ())
    for target in tgtlist:
        try:
            psycopg2.connect(target[3]).close()
            mark = 'connected'
        except:
            mark = 'failed'
        print( "DB: %-20s %-11s conn: %s" % (target[0], mark if target[2] in ('alpha','devel') else 'forbidden', target[3]))
    exit(0)

project = None
for p in  glab.getprojects():
    # print(p['path_with_namespace'])
    if p['path_with_namespace'] == args.projectpath:
        project = p
        break
else:
    print("No project %s found in gitlab" % args.projectpath)
    exit(1)

branch = None
for b in  glab.getbranches(project['id']):
    # pp.pprint(b)
    if b['name'] == args.branch:
        branch = b
        break
else:
    print("No branch %s found in repo  %s " % (args.branch, args.projectpath))
    exit(1)

# pp.pprint(args.branch)
# pp.pprint(branch)
# pp.pprint(project)



tgtquery = """SELECT givenname, codecase, concern, connectstring \
    FROM dba_resource.connect_deployment  WHERE TRUE \
    """
tgtparam = ()
# if dbnames are given explicit do not use selection hints
if args.dbname:
    tgtquery = tgtquery + " AND givenname IN %s "
    tgtparam = tgtparam + (tuple(args.dbname),)
else:
    tgtquery = tgtquery + " AND codecase = %s AND concern  = %s "
    tgtparam = tgtparam + (args.flavour, args.concern)
    if args.adgroup:
        tgtquery = tgtquery + " AND domaingroup IN %s "
        tgtparam = tgtparam + (tuple(args.adgroup),)
    if args.exclude:
        tgtquery = tgtquery + " AND domaingroup NOT IN %s "
        tgtparam = tgtparam + (tuple(args.exclude),)


# get connect-string and area of concern for target databases and remove forbidden targets
tgtlist = aresutil.ares_get(tgtquery, tgtparam)
tgtlist = [x for x in tgtlist if x[2] in ('alpha','devel')]

if debug > 10:
    pp.pprint(tgtlist)

### validate information and fill gaps
(labgroup, dummy, labschema)  = args.projectpath.rpartition('/')
lxpath    = "$HOME/tmp/gitlab.affinitas.de/" + labgroup
lrpath    = lxpath + labschema                              # local repository path
mybranch  = args.branch                                     # branch to install (this is the version)
dbschema  = labschema + "_" + branch['name']                # name of schema in database (with or without bransch version number)
mygitssh  = project['ssh_url_to_repo']                      # use for clone

if debug > 12:
    print("localrepo = ", lrpath, "; localxrepo = ", lxpath, file=sys.stderr)
    print("labschema = ", labschema, file=sys.stderr)
    print("branch = ", branch['name'], "; dbschema = ", dbschema,  file=sys.stderr)
    print("mygitssh = ", mygitssh, file=sys.stderr)



#  space between input files
divider  = "\n--\n-- script divider keep code from different files apart\n--\n"
preamble = "--"                                 \
    "-- start for composed deployment script\n" \
    "-- \n"                                     \
    "SET statement_timeout = 0;\n"              \
    "SET client_encoding = 'UTF8';\n"           \
    "SET standard_conforming_strings = off;\n"  \
    "SET check_function_bodies = false;\n"      \
    "SET client_min_messages = warning;\n"      \
    "SET escape_string_warning = off;\n"        \
    "\n"

# init the text of the update transaction
script = preamble + divider

# connect and check db for schema and recede() function
tgtcon = psycopg2.connect(tgtcstr)
tgtcur = tgtcon.cursor()

# check if schema exits. For alpha remove it, for others exit error)
tgtcur.execute("SELECT 1 FROM information_schema.schemata WHERE schema_name = %s", (fullschemaname,))
if tgtcur.rowcount > 0:    # any result indicates existenc of schema
    if debug > 10: print("schema exists", file=sys.stderr)
    if concern != "alpha":       ## adopt to current policy ??                                      # only alpha
        print("Schema replacement limited to alpha databases.\nThis database is ", concern, "!" )
        exit(1)

    # check for recede - function to call before drop
    tgtcur.execute("SELECT 1 FROM pg_proc JOIN pg_namespace ON pronamespace = pg_namespace.oid WHERE proname = %s AND nspname = %s", (exitfuncname, fullschemaname))
    if tgtcur.rowcount > 0:
        script =script + "\nPERFORM " + fullschemaname + ".retreat();\n"

    script = script + "\nDROP SCHEMA " + fullschemaname + " CASCADE;\n"
    print("will drop schema", file=sys.stderr)
tgtcur.close
tgtcon.close


# now prepare to read the new code
lrdir     = os.environ['HOME'] + "/tmp/" + lrpath
lcdir     = os.environ['HOME'] + "/tmp/" + lcpath

os.makedirs(lcdir, 0o755, True)    # make local clonedir
os.chdir(lcdir)                    # go to local clonedir
if debug > 12:
    print("CWD = ", os.getcwd(), file=sys.stderr)

# clone repository if not exist
try:
    os.chdir(lrdir)         # assume repo exist if we can cd into
except:
    subprocess.check_call("git clone " + mygitssh, shell=True)  # else clone and cd
    os.chdir(lrdir)
if debug > 12:
    print("CWD = ", os.getcwd(), file=sys.stderr)

# setup tracking branch or checkout and pull if repo not new
try:
    subprocess.check_call("git checkout --track origin/" + mybranch, shell=True)
except:
    subprocess.check_call("git checkout " + args.branch, shell=True)
    subprocess.check_call("git pull " , shell=True)

# now the repository represent the end of correct branch

script = script + "\nCREATE SCHEMA "         + fullschemaname + " ;\n"
script = script + "\nGRANT USAGE ON SCHEMA " + fullschemaname + " TO public;\n"
script = script + "\nSET search_path TO "    + fullschemaname + ", public;\n"


for root, dirs, files in os.walk("types"):
    try:
        with open(os.path.join(root, 'sequence.txt'), 'r') as f:    # first create object listed in sequence.txt
            hints = f.read().splitlines()
    except:
        hints = []
    for file in hints:
        if file.endswith(".sql"):
            thisfile = os.path.join(root, file)
            if debug > 10:
                print("HINT ", thisfile, file=sys.stderr)
            thistext = open(thisfile, 'r', -1, 'UTF-8').read()
            # print(thistext, file=sys.stderr)
            script = script + divider + thistext
    hints = set(hints)                                          # convert hints to set for easy lookup
    for file in sorted(files):                                  # if sorted u need less hints
        if file.endswith(".sql") and file not in hints:
            thisfile = os.path.join(root, file)
            if debug > 10:
                print("SELF ", thisfile, file=sys.stderr)
            thistext = open(thisfile, 'r', -1, 'UTF-8').read()
            # print(thistext, file=sys.stderr)
            script = script + divider + thistext

has_engage = False
for root, dirs, files in os.walk("functions"):
    for file in sorted(files):                                  # sort is just for fun found no reason to use hints
        if file.endswith(".sql"):
            thisfile = os.path.join(root, file)
            #print(thisfile, file=sys.stderr)
            thistext = open(thisfile, 'r', -1, 'UTF-8').read()
            # print(thistext, file=sys.stderr)
            script = script + divider + thistext
            if file == efuncname + '.sql':                                  # search engage function
                has_engage = True



# script is now the ddl for this branch

# get connect-string to database
tgtcon = psycopg2.connect(tgtcstr)
tgtcon.set_session(autocommit=False)
tgtcur = tgtcon.cursor()
if debug > 12:
    print(tgtcon.autocommit)

# set up entry for deployevents this statement will not be recorded
eventlogentry = tgtcur.mogrify("INSERT INTO deployment.deployevents VALUES ( now(), %s, %s, %s, %s, %s, %s);",
                                (glschema, operator, script, mybranch, deployjira, tgtname))
script = script + divider + eventlogentry.decode() + divider

if has_engage == True:
    script = script + divider + "\nPERFORM " + fullschemaname + ".init_hook();\n"   # should be the last


if debug > 8:                       # save full script
    f = open('script.sql', 'w')
    f.write(script)
    f.close()

# start the update transaction
deployed = False
try:
    tgtcur.execute(script)
except Exception as inst:
    if debug > 8:
        print("Exception Type:      ", type(inst))
        print("Exception Arguments: ", inst.args )
    print("Unknown Problem. Rolling back!")
    tgtcon.rollback()
else:
    if args.dryrun:
        print("This is a dry run: Rollback!")
        tgtcon.rollback()
    else:
        tgtcon.commit()
        deployed = True
        print("Deploy finished and committed!")
# end transaction
print("Success!")
tgtcur.close()
tgtcon.close()

# record success to git repository
if concern == 'prod' or concern == 'stage':    # annotated tags for production/staging
    tag_message = "Commited to: " + tgtname +"\nTimestamp: " + time.strftime('%Y-%m-%dT%H:%M:%S%z')  # ISO 8601
    tag_call = "git tag -a Final -m 'Commited to: " + tgtname + "\nTimestamp: " + time.strftime('%Y-%m-%dT%H:%M:%S%z') + "'"
else:
    tag_call = "git tag " + tgtname

subprocess.check_call(tag_call     , shell=True)
# subprocess.check_call("git commit" , shell=True)    # delay until all tags are written
subprocess.check_call("git push --tags"   , shell=True)    # delay until all targets are commited


# now the repository represent the end of correct branch



# timestamp
# database
#

#eof
