#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deployment script that will deploy Postgres schemas to a given DB
Copyright (c) Affinitas GmbH

Usage:
  pgpm deploy (<connection_string> | set <environment_name> <product_name> ([--except] [<unique_name>...])
                [-u | --user <user_role>])
                [-m | --mode <mode>]
                [-o | --owner <owner_role>] [--usage <usage_role>...]
                [-f <file_name>...] [--add-config <config_file_path>] [--debug-mode]
                [--vcs-ref <vcs_reference>] [--vcs-link <vcs_link>]
                [--issue-ref <issue_reference>] [--issue-link <issue_link>]
                [--compare-table-scripts-as-int]
                [--log-file <log_file_name>] [--global-config <global_config_file_path>]
                [--auto-commit] [--send-email]
  pgpm execute (<connection_string> | set <environment_name> <product_name> ([--except] [<unique_name>...])
                --query <query>
                [-u | --user <user_role>])
                [--until-zero]
                [--log-file <log_file_name>] [--debug-mode] [--global-config <global_config_file_path>]
  pgpm remove <connection_string> --pkg-name <schema_name>
                <v_major> <v_minor> <v_patch> <v_pre>
                [--old-rev <old_rev>] [--log-file <log_file_name>]
  pgpm install (<connection_string> | set <environment_name> <product_name> ([--except] [<unique_name>...])
                [-u | --user <user_role>])
                [--upgrade] [--debug-mode]
                [--usage <usage_role>...]
                [--log-file <log_file_name>] [--global-config <global_config_file_path>]
  pgpm uninstall (<connection_string> | set <environment_name> <product_name> [-u | --user <user_role>])
                [--log-file <log_file_name>] [--global-config <global_config_file_path>]
                [--debug-mode]
  pgpm list set <environment_name> <product_name> ([--except] [<unique_name>...])
                [--log-file <log_file_name>] [--global-config <global_config_file_path>]
  pgpm -h | --help
  pgpm -v | --version

Arguments:
  <connection_string>       Connection string to postgres database.
                            Can be in any format psycopg2 would understand it
  <environment_name>        Name of an environment to be used to get connection strings from global-config file
  <product_name>            Name of a product. E.g. ed_live
  <unique_name>             Unique name that identifies DB within the set

Options:
  -h --help                 Show this screen.
  -v --version              Show version.
  -f <file_name>..., --file <file_name>...
                            Use it if you want to deploy only specific files (functions, types, etc).
                            In that case these files if exist will be overridden.
                            Should be followed by the list of names of files to deploy.
  -o <owner_role>, --owner <owner_role>
                            Role to which schema owner and all objects inside will be changed. User connecting to DB
                            needs to be a superuser. If omitted, user running the script
                            will be the owner of schema and all objects inside
                            If --mode flag is *overwrite* or --file flag is used then this is ignored
                            as no new schema is created
                            During installation a mandatory parameter to install on behalf of the specified user
  -u <user_role>, --user <user_role>
                            User name that connects to DB. Make sense only when used with `set` option.
                            If omitted than os user name is used.
  --usage <usage_role>...
                            Roles to which different usage privileges will be applied.
                            If omitted, default behaviour of DB applies
                            In case used with install command the following will be applied:
                            GRANT SELECT, INSERT, UPDATE, DELETE on all current tables and by default in the future
                            GRANT EXECUTE on all current functions and by default in the future
                            GRANT USAGE, SELECT on all current sequences and by default in the future
                            In case used with deploy command the following will be applied:
                            GRANT USAGE on the schema
                            GRANT EXECUTE on all current functions
  -m <mode>, --mode <mode>  Deployment mode. Can be:
                            * safe. Add constraints to deployment.
                            Will not deploy schema if it already exists in the DB
                            Will not deploy table script if it was deployed before (checking by filename)
                            * moderate. If schema exists, will try to rename it by adding suffix "_"
                            and deploy new schema with old name
                            * unsafe.
                            Allows cascade deleting of schema if it exists and adding new one
                            Allows redeploying of deploy script even if was deployed before
                            * overwrite. Will run scripts overwriting existing ones.
                            User have to make sure that overwriting is possible.
                            E.g. if type exists, rewriting should be preceded with dropping it first manually
                            [default: safe]
  --add-config <config_file_path>
                            Provides path to additional config file. Attributes of this file overwrite config.json
  --debug-mode              Debug level logging enabled if command is present. Otherwise Info level
  --upgrade                 Update pgpm to a newer version
  --vcs-ref <vcs_reference> Adds vcs reference to deployments log table
  --vcs-link <vcs_link>     Adds link to repository to deployments log table
  --issue-ref <issue_reference>
                            Adds issue reference to deployments log table
  --issue-link <issue_link> Adds link to issue tracking system to deployments log table
  --pkg-name <schema_name>  Package name to be removed
  --old-rev <old_rev>       If omitted all old revisions are deleted together with current revision.
                            If specified just the specified revision is deleted
  --compare-table-scripts-as-int
                            Flag says that when table scripts are running they should be ordered
                            but first their names are to be converted to int.
                            By default scripts are ordered by string comparison
  --log-file <log_file_name>
                            Log into a specified file. If not specified, logs are ignored
  --global-config <global_config_file_path>
                            path to a global-config file. If global gonfig exists also in ~/.pgpmconfig file then
                            two dicts are merged (file formats are JSON).
  --send-email              Send mail about deployment. Works only if email block exists in global config


"""
import logging
import os
import smtplib
from pprint import pprint

import pgpm.lib.install
import pgpm.lib.deploy
import pgpm.lib.execute
import pgpm.lib.utils.config
import pgpm.lib.utils.db
import pgpm.lib.utils.vcs
import sys
import colorama
import getpass
import pgpm.utils.config
import pgpm.utils.issue_trackers

from docopt import docopt

from pgpm import settings


# getting logging
logger = logging.getLogger(__name__)


def main():
    arguments = docopt(__doc__, version=settings.__version__)
    colorama.init()

    # setting logging
    formatter = logging.Formatter(settings.LOGGING_FORMATTER)
    if arguments['--debug-mode']:
        logger_level = logging.DEBUG
    else:
        logger_level = logging.INFO
    logger.setLevel(logger_level)
    if arguments['--log-file']:
        handler = logging.FileHandler(os.path.abspath(os.path.expanduser(arguments['--log-file'])))
        handler.setLevel(logger_level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    else:
        handler = logging.StreamHandler()
        handler.setLevel(logger_level)
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    # check if connecting user is set otherwise take os user
    connection_user = getpass.getuser()
    if arguments['--user']:
        connection_user = arguments['--user'][0]

    owner_role = None
    if arguments['--owner']:
        owner_role = arguments['--owner'][0]

    usage_roles = None
    if arguments['--usage']:
        usage_roles = arguments['--usage']

    sys.stdout.write('\033[2J\033[0;0H')
    if arguments['install']:
        if arguments['--global-config']:
            extra_config_file = arguments['--global-config']
        else:
            extra_config_file = None
        global_config = pgpm.utils.config.GlobalConfiguration('~/.pgpmconfig', extra_config_file)
        connections_list = global_config.get_list_connections(arguments['<environment_name>'],
                                                              arguments['<product_name>'],
                                                              arguments['<unique_name>'],
                                                              arguments['--except'])
        if arguments['set']:
            if len(connections_list) > 0:
                for connection_dict in connections_list:
                    connection_string = 'host=' + connection_dict['host'] + ' port=' + str(connection_dict['port']) + \
                                        ' dbname=' + connection_dict['dbname'] + ' user=' + connection_user
                    _install_schema(connection_string, arguments['--usage'], arguments['--upgrade'])
            else:
                _emit_no_set_found(arguments['<environment_name>'], arguments['<product_name>'])
        else:
            _install_schema(arguments['<connection_string>'], arguments['--usage'], arguments['--upgrade'])
    elif arguments['uninstall']:
        if arguments['--global-config']:
            extra_config_file = arguments['--global-config']
        else:
            extra_config_file = None
        global_config = pgpm.utils.config.GlobalConfiguration('~/.pgpmconfig', extra_config_file)
        connections_list = global_config.get_list_connections(arguments['<environment_name>'],
                                                              arguments['<product_name>'],
                                                              arguments['<unique_name>'],
                                                              arguments['--except'])
        if arguments['set']:
            if len(connections_list) > 0:
                for connection_dict in connections_list:
                    connection_string = 'host=' + connection_dict['host'] + ' port=' + str(connection_dict['port']) + \
                                        ' dbname=' + connection_dict['dbname'] + ' user=' + connection_user
                    _uninstall_schema(connection_string)
            else:
                _emit_no_set_found(arguments['<environment_name>'], arguments['<product_name>'])
        else:
            _uninstall_schema(arguments['<connection_string>'])
    elif arguments['execute']:
        if arguments['--global-config']:
            extra_config_file = arguments['--global-config']
        else:
            extra_config_file = None
        global_config = pgpm.utils.config.GlobalConfiguration('~/.pgpmconfig', extra_config_file)
        connections_list = global_config.get_list_connections(arguments['<environment_name>'],
                                                              arguments['<product_name>'],
                                                              arguments['<unique_name>'],
                                                              arguments['--except'])
        if arguments['set']:
            if len(connections_list) > 0:
                for connection_dict in connections_list:
                    connection_string = 'host=' + connection_dict['host'] + ' port=' + str(connection_dict['port']) + \
                                        ' dbname=' + connection_dict['dbname'] + ' user=' + connection_user
                    _execute(connection_string, arguments['--query'], arguments['--until-zero'])
            else:
                _emit_no_set_found(arguments['<environment_name>'], arguments['<product_name>'])
        else:
            _execute(arguments['<connection_string>'], arguments['--query'], arguments['--until-zero'])
    elif arguments['deploy']:
        deploy_result = {}
        if arguments['--global-config']:
            extra_config_file = arguments['--global-config']
        else:
            extra_config_file = None
        global_config = pgpm.utils.config.GlobalConfiguration('~/.pgpmconfig', extra_config_file)
        connections_list = global_config.get_list_connections(arguments['<environment_name>'],
                                                              arguments['<product_name>'],
                                                              arguments['<unique_name>'],
                                                              arguments['--except'])
        config_dict = {}
        if owner_role:
            config_dict['owner_role'] = owner_role
        if usage_roles:
            config_dict['usage_roles'] = usage_roles
        config_object = pgpm.lib.utils.config.SchemaConfiguration(
                os.path.abspath(settings.CONFIG_FILE_NAME), config_dict, os.path.abspath('.'))
        if arguments['set']:
            if len(connections_list) > 0:
                target_names_list = []
                for connection_dict in connections_list:
                    connection_string = 'host=' + connection_dict['host'] + ' port=' + str(connection_dict['port']) + \
                                        ' dbname=' + connection_dict['dbname'] + ' user=' + connection_user
                    deploy_result = _deploy_schema(connection_string,
                                   mode=arguments['--mode'][0], files_deployment=arguments['--file'],
                                   vcs_ref=arguments['--vcs-ref'], vcs_link=arguments['--vcs-link'],
                                   issue_ref=arguments['--issue-ref'], issue_link=arguments['--issue-link'],
                                   compare_table_scripts_as_int=arguments['--compare-table-scripts-as-int'],
                                   auto_commit=arguments['--auto-commit'],
                                   config_object=config_object)
                    if 'unique_name' in connection_dict and connection_dict['unique_name']:
                        target_names_list.append(connection_dict['unique_name'])
                    else:
                        target_names_list.append(connection_dict['dbname'])

                if deploy_result['deployed_files_count'] > 0:
                    target_str = 'environment: ' + connections_list[0]['environment'] + ', product: ' + \
                                 connections_list[0]['product'] + ', DBs: ' + ', '.join(target_names_list)
                    if arguments['--issue-ref'] and ('issue-tracker' in global_config.global_config_dict):
                        _comment_issue_tracker(arguments, global_config,
                                               target_str,
                                               config_object, deploy_result)
                    if arguments['--send-email'] and ('email' in global_config.global_config_dict):
                        _send_mail(arguments, global_config, target_str, config_object, deploy_result)
            else:
                _emit_no_set_found(arguments['<environment_name>'], arguments['<product_name>'])

        else:
            deploy_result = _deploy_schema(arguments['<connection_string>'],
                           mode=arguments['--mode'][0], files_deployment=arguments['--file'],
                           vcs_ref=arguments['--vcs-ref'], vcs_link=arguments['--vcs-link'],
                           issue_ref=arguments['--issue-ref'], issue_link=arguments['--issue-link'],
                           compare_table_scripts_as_int=arguments['--compare-table-scripts-as-int'],
                           auto_commit=arguments['--auto-commit'],
                           config_object=config_object)
            if deploy_result['deployed_files_count'] > 0:
                conn_parsed = pgpm.lib.utils.db.parse_connection_string_psycopg2(arguments['<connection_string>'])
                target_str = 'host: ' + conn_parsed['host'] + ', DB: ' + conn_parsed['dbname']
                if arguments['--issue-ref'] and ('issue-tracker' in global_config.global_config_dict):
                    _comment_issue_tracker(arguments, global_config, target_str,
                                           config_object, deploy_result)
                if arguments['--send-email'] and ('email' in global_config.global_config_dict):
                    _send_mail(arguments, global_config, target_str, config_object, deploy_result)

    elif arguments['list']:
        if arguments['set']:
            if arguments['--global-config']:
                extra_config_file = arguments['--global-config']
            else:
                extra_config_file = None
            global_config = pgpm.utils.config.GlobalConfiguration('~/.pgpmconfig', extra_config_file)
            connections_list = global_config.get_list_connections(arguments['<environment_name>'],
                                                                  arguments['<product_name>'])
            if len(connections_list) > 0:
                pprint(global_config.get_list_connections(arguments['<environment_name>'], arguments['<product_name>'],
                                                          arguments['<unique_name>'], arguments['--except']))
            else:
                _emit_no_set_found(arguments['<environment_name>'], arguments['<product_name>'])
    else:
        print(arguments)


def _install_schema(connection_string, user, upgrade):
    logger.info('Installing... {0}'.format(connection_string))
    sys.stdout.write(colorama.Fore.YELLOW + 'Installing...' + colorama.Fore.RESET +
                     ' | ' + connection_string)
    sys.stdout.flush()
    installation_manager = pgpm.lib.install.InstallationManager(connection_string, '_pgpm', 'basic',
                                                                logger)
    try:
        installation_manager.install_pgpm_to_db(user, upgrade)
    except:
        print('\n')
        print('Something went wrong, check the logs. Aborting')
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        print(sys.exc_info()[2])
        raise

    sys.stdout.write('\033[2K\r' + colorama.Fore.GREEN + 'Installed' + colorama.Fore.RESET +
                     ' | ' + connection_string)
    sys.stdout.write('\n')
    logger.info('Successfully installed {0}'.format(connection_string))
    return 0


def _uninstall_schema(connection_string):
    logger.info('Uninstalling pgpm... {0}'.format(connection_string))
    sys.stdout.write(colorama.Fore.YELLOW + 'Uninstalling pgpm...' + colorama.Fore.RESET +
                     ' | ' + connection_string)
    sys.stdout.flush()
    installation_manager = pgpm.lib.install.InstallationManager(connection_string, '_pgpm', 'basic',
                                                                logger)
    try:
        installation_manager.uninstall_pgpm_from_db()
    except:
        print('\n')
        print('Something went wrong, check the logs. Aborting')
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        print(sys.exc_info()[2])
        raise

    sys.stdout.write('\033[2K\r' + colorama.Fore.GREEN + 'Uninstalled pgpm' + colorama.Fore.RESET +
                     ' | ' + connection_string)
    sys.stdout.write('\n')
    logger.info('Successfully uninstalled pgpm from {0}'.format(connection_string))
    return 0


def _deploy_schema(connection_string, mode, files_deployment, vcs_ref, vcs_link, issue_ref, issue_link,
                   compare_table_scripts_as_int, auto_commit, config_object):
    deploy_result = {}
    deploying = 'Deploying...'
    deployed_files = 'Deployed {0} files out of {1}'
    logger.info('Deploying... {0}'.format(connection_string))
    sys.stdout.write(colorama.Fore.YELLOW + deploying + colorama.Fore.RESET +
                     ' | ' + connection_string)
    sys.stdout.flush()

    deployment_manager = pgpm.lib.deploy.DeploymentManager(
        connection_string=connection_string, source_code_path=os.path.abspath('.'), config_object=config_object,
        pgpm_schema_name='_pgpm', logger=logger)

    try:
        deploy_result = deployment_manager.deploy_schema_to_db(
            mode=mode, files_deployment=files_deployment, vcs_ref=vcs_ref, vcs_link=vcs_link,
            issue_ref=issue_ref, issue_link=issue_link, compare_table_scripts_as_int=compare_table_scripts_as_int,
            auto_commit=auto_commit)
    except:
        print('\n')
        print('Something went wrong, check the logs. Aborting')
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        print(sys.exc_info()[2])
        raise

    if deploy_result['code'] == deployment_manager.DEPLOYMENT_OUTPUT_CODE_OK \
            and deploy_result['deployed_files_count'] == deploy_result['requested_files_count']:
        sys.stdout.write('\033[2K\r' + colorama.Fore.GREEN +
                         deployed_files.format(deploy_result['deployed_files_count'],
                                               deploy_result['requested_files_count']) + colorama.Fore.RESET +
                         ' | ' + connection_string)
        sys.stdout.write('\n')
        logger.info('Successfully deployed {0}'.format(connection_string))
    elif deploy_result['code'] == deployment_manager.DEPLOYMENT_OUTPUT_CODE_NOT_ALL_DEPLOYED:
        sys.stdout.write('\033[2K\r' + colorama.Fore.YELLOW +
                         deployed_files.format(deploy_result['deployed_files_count'],
                                               deploy_result['requested_files_count']) + colorama.Fore.RESET +
                         ' | ' + connection_string)
        sys.stdout.write('\n')
        logger.warning('Not all files were deployed {0}'.format(connection_string))

    return deploy_result


def _execute(connection_string, query, until_zero=False):
    calling = 'Executing query {0}...'.format(query)
    called = 'Executed query {0}    '.format(query)
    logger.info('Deploying... {0}'.format(connection_string))
    sys.stdout.write(colorama.Fore.YELLOW + calling + colorama.Fore.RESET +
                     ' | ' + connection_string)
    sys.stdout.flush()

    query_manager = pgpm.lib.execute.QueryExecutionManager(
            connection_string=connection_string, logger=logger)
    try:
        query_manager.execute(query, until_zero=until_zero)
    except:
        print('\n')
        print('Something went wrong, check the logs. Aborting')
        print(sys.exc_info()[0])
        print(sys.exc_info()[1])
        print(sys.exc_info()[2])
        raise

    sys.stdout.write('\033[2K\r' + colorama.Fore.GREEN + called + colorama.Fore.RESET +
                     ' | ' + connection_string)
    sys.stdout.write('\n')
    logger.info('Successfully deployed {0}'.format(connection_string))

    return 0


def _emit_no_set_found(environment_name, product_name):
    """
    writes to std out and logs if no connection string is found for deployment
    :param environment_name:
    :param product_name:
    :return:
    """
    sys.stdout.write(colorama.Fore.YELLOW + 'No connections found in global config file '
                                            'in environment: {0} for product: {1}'
                     .format(environment_name, product_name) +
                     colorama.Fore.RESET)
    sys.stdout.write('\n')
    logger.warning('No connections found in environment: {0} for product: {1}'
                   .format(environment_name, product_name))


def _send_mail(arguments, global_config, target_string, config_object, deploy_result):
    if global_config.global_config_dict['email']['type'] == "SMTP":
        logger.info('Sending an email about deployment')

        issue_ref_subject_text = ''
        issue_ref_body_text = ''
        if arguments['--issue-ref']:
            issue_ref_subject_text = "({0})".format(arguments['--issue-ref'])
            if ("issue-tracker" in global_config.global_config_dict) and \
                    ("issue-path-template" in global_config.global_config_dict["issue-tracker"]):
                issue_ref_body_text = \
                    "({0})".format(global_config.global_config_dict["issue-tracker"]["issue-path-template"]
                                   .format(issue_ref=arguments['--issue-ref']))
        else:
            issue_ref_body_text = "({0})".format(arguments['--issue-ref'])

        _schema_row = ''
        if config_object.scope == config_object.SCHEMA_SCOPE:
            _schema_row += '<tr><th>Schema name</th><td>'
            if config_object.subclass == config_object.BASIC_SUBCLASS:
                _schema_row += config_object.name
            elif config_object.subclass == config_object.VERSIONED_SUBCLASS:
                _schema_row += config_object.name + '_' + config_object.version.to_string()
            _schema_row += '</td></tr>'

        _files_row = ''
        if arguments['--file']:
            _files_row += '<tr><th>Files deployed</th><td>'
            if deploy_result['function_scripts_deployed']:
                _files_row += ',<br />'.join(deploy_result['function_scripts_deployed'])
            if deploy_result['type_scripts_deployed']:
                _files_row += ',<br />'.join(deploy_result['type_scripts_deployed'])
            if deploy_result['view_scripts_deployed']:
                _files_row += ',<br />'.join(deploy_result['view_scripts_deployed'])
            if deploy_result['trigger_scripts_deployed']:
                _files_row += ',<br />'.join(deploy_result['trigger_scripts_deployed'])
            if deploy_result['table_scripts_deployed']:
                _files_row += ',<br />'.join(deploy_result['table_scripts_deployed'])
            _files_row += '</td></tr>'
        else:
            _files_row += '<tr><th>Files deployed</th><td>all</td></tr>'

        _git_commit_row = ''
        _git_repo_row = ''
        if pgpm.lib.utils.vcs.is_git_directory(os.path.abspath('.')):
            _git_repo_row += '<tr><th>GIT repo</th><td>'
            _git_repo_row += pgpm.lib.utils.vcs.get_git_remote_url(os.path.abspath('.'))
            _git_repo_row += '</td></tr>'
            if not arguments['--vcs-ref']:
                _git_commit_row += '<tr><th>GIT commit</th><td>'
                _git_commit_row += pgpm.lib.utils.vcs.get_git_revision_hash(os.path.abspath('.'))
                _git_commit_row += '</td></tr>'
        pkg_desc_text = """
        <table>
            <tr>
                <th>Package Name</th>
                <td>{0}</td>
            </tr>
            {1}
            {2}
            {3}
            {4}
        </table>
        """.format(config_object.name, _schema_row, _files_row, _git_repo_row, _git_commit_row)

        mail_message = "From: {0}\r\nTo: {1}\r\nMIME-Version: 1.0\r\nContent-type: text/html\r\nSubject: {2}\r\n{3}"\
            .format(global_config.global_config_dict['email']['from'], global_config.global_config_dict['email']['to'],
                    global_config.global_config_dict['email']['subject']
                    .format(issue_ref=issue_ref_subject_text, target_subject=target_string),
                    global_config.global_config_dict['email']['body']
                    .format(issue_ref=issue_ref_body_text, target=target_string, package_description=pkg_desc_text))

        smtp = smtplib.SMTP(global_config.global_config_dict['email']['host'],
                            global_config.global_config_dict['email']['port'])
        # smtp.set_debuglevel(1)
        if global_config.global_config_dict['email']['TLS'] == True:
            smtp.starttls()
        if 'credentials' in global_config.global_config_dict['email']:
            try:
                smtp.login(global_config.global_config_dict['email']['credentials']['username'],
                           global_config.global_config_dict['email']['credentials']['password'])
            except smtplib.SMTPAuthenticationError:
                logger.warning('SMTP authentication failed though required in the global config. '
                               'Will try to send email without authentication')
        smtp.sendmail(global_config.global_config_dict['email']['from'],
                      global_config.global_config_dict['email']['to'], mail_message)
        smtp.quit()


def _comment_issue_tracker(arguments, global_config, target_string, config_object, deploy_result):
    if global_config.global_config_dict['issue-tracker']['type'] == "JIRA":
        logger.info('Leaving a comment to JIRA issue {0} about deployment'.format(arguments['--issue-ref']))
        jira = pgpm.utils.issue_trackers.Jira(global_config.global_config_dict['issue-tracker']['url'], logger)

        _schema_row = ''
        if config_object.scope == config_object.SCHEMA_SCOPE:
            _schema_row += '\n||Schema name|'
            if config_object.subclass == config_object.BASIC_SUBCLASS:
                _schema_row += config_object.name
            elif config_object.subclass == config_object.VERSIONED_SUBCLASS:
                _schema_row += config_object.name + '_' + config_object.version.to_string()
            _schema_row += '|'

        _files_row = ''
        if arguments['--file']:
            _files_row += '\n||Files deployed|'
            if deploy_result['function_scripts_deployed']:
                _files_row += ',\n'.join(deploy_result['function_scripts_deployed'])
            if deploy_result['type_scripts_deployed']:
                _files_row += ',\n'.join(deploy_result['type_scripts_deployed'])
            if deploy_result['view_scripts_deployed']:
                _files_row += ',\n'.join(deploy_result['view_scripts_deployed'])
            if deploy_result['trigger_scripts_deployed']:
                _files_row += ',\n'.join(deploy_result['trigger_scripts_deployed'])
            if deploy_result['table_scripts_deployed']:
                _files_row += ',\n'.join(deploy_result['table_scripts_deployed'])
            _files_row += '|'
        else:
            _files_row += '\n||Files deployed|all|'

        _git_commit_row = ''
        _git_repo_row = ''
        if pgpm.lib.utils.vcs.is_git_directory(os.path.abspath('.')):
            _git_repo_row += '\n||GIT repo|'
            _git_repo_row += pgpm.lib.utils.vcs.get_git_remote_url(os.path.abspath('.'))
            _git_repo_row += '|'
            if not arguments['--vcs-ref']:
                _git_commit_row += '\n||GIT commit|'
                _git_commit_row += pgpm.lib.utils.vcs.get_git_revision_hash(os.path.abspath('.'))
                _git_commit_row += '|'

        comment_body = global_config.global_config_dict['issue-tracker']['comment-body']\
            .format(pkg_name=config_object.name, target=target_string, schema=_schema_row, files=_files_row,
                    git_repo=_git_repo_row, git_commit=_git_commit_row)
        jira.call_jira_rest("/issue/" + arguments['--issue-ref'] + "/comment",
                            global_config.global_config_dict['issue-tracker']['username'],
                            global_config.global_config_dict['issue-tracker']['password'], "POST",
                            {"body": comment_body})
        logger.info('Jira comment done')


if __name__ == '__main__':
    main()
