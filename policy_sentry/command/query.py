"""
Allow users to use specific pre-compiled queries against the action, arn, and condition tables from command line.
"""
import json
import click

from policy_sentry.util.access_levels import transform_access_level_text
from policy_sentry.querying.all import get_all_service_prefixes
from policy_sentry.shared.constants import DATABASE_FILE_PATH
from policy_sentry.shared.database import connect_db
from policy_sentry.querying.arns import get_arn_type_details, get_arn_types_for_service, get_raw_arns_for_service
from policy_sentry.querying.actions import get_actions_for_service, get_actions_with_access_level, \
    get_action_data, get_actions_that_support_wildcard_arns_only, \
    get_actions_matching_condition_key
from policy_sentry.querying.conditions import get_condition_keys_for_service, get_condition_key_details


@click.group()
def query():
    """Allow users to query the IAM tables from command line"""


@query.command(
    short_help='Query the action table based on access levels, conditions, or actions that only support wildcard '
               'resources.'
)
@click.option(
    '--service',
    type=str,
    required=True,
    help="Filter according to AWS service."
)
@click.option(
    '--name',
    type=str,
    required=False,
    help='The name of IAM Action. For example, if the action is "iam:ListUsers", supply "ListUsers" here.'
)
@click.option(
    '--access-level',
    type=click.Choice(['read', 'write', 'list', 'tagging',
                       'permissions-management']),
    required=False,
    help='If action table is chosen, you can use this to filter according to CRUD levels. '
         'Acceptable values are read, write, list, tagging, permissions-management'
)
@click.option(
    '--condition',
    type=str,
    required=False,
    help='If action table is chosen, you can supply a condition key to show a list of all IAM actions that'
         ' support the condition key.')
@click.option(
    '--wildcard-only',
    is_flag=True,
    required=False,
    help='If action table is chosen, show the IAM actions that only support '
         'wildcard resources - i.e., cannot support ARNs in the resource block.')
def action_table(name, service, access_level, condition, wildcard_only):
    """Query the Action Table from the Policy Sentry database"""
    db_session = connect_db(DATABASE_FILE_PATH)
    # Actions on all services
    if service == "all":
        all_services = get_all_service_prefixes(db_session)
        if access_level:
            level = transform_access_level_text(access_level)
            print(f"{access_level} actions across ALL services:\n")
            results = []
            for serv in all_services:
                output = get_actions_with_access_level(
                    db_session, serv, level)
                results.extend(output)
            for result in results:
                print(result)
        # Get a list of all services in the database
        else:
            print("All services in the database:\n")
            for item in all_services:
                print(item)
    elif name is None and access_level:
        print(
            f"All IAM actions under the {service} service that have the access level {access_level}:")
        level = transform_access_level_text(access_level)
        output = get_actions_with_access_level(db_session, service, level)
        print(json.dumps(output, indent=4))
    # Get a list of all IAM actions under the service that support the
    # specified condition key.
    elif condition:
        print(
            f"IAM actions under {service} service that support the {condition} condition only:")
        output = get_actions_matching_condition_key(
            db_session, service, condition)
        print(json.dumps(output, indent=4))
    # Get a list of IAM Actions under the service that only support resources = "*"
    # (i.e., you cannot restrict it according to ARN)
    elif wildcard_only:
        print(
            f"IAM actions under {service} service that support wildcard resource values only:")
        output = get_actions_that_support_wildcard_arns_only(
            db_session, service)
        print(json.dumps(output, indent=4))
    elif name and access_level is None:
        output = get_action_data(db_session, service, name)
        print(json.dumps(output, indent=4))
    else:
        print(f"All IAM actions available to {service}:")
        # Get a list of all IAM Actions available to the service
        action_list = get_actions_for_service(db_session, service)
        print(f"ALL {service} actions:")
        for item in action_list:
            print(item)


@query.command(
    short_help='Query the ARN table to show RAW ARNs, like `aws:s3:::bucket/object`. '
               'Use --list-arn-types ARN types, like `object`.')
@click.option(
    '--service',
    type=str,
    required=True,
    help="Filter according to AWS service."
)
@click.option(
    '--name',
    type=str,
    required=False,
    help='The short name of the resource ARN type. For example, `bucket` under service `s3`.'
)
@click.option(
    '--list-arn-types',
    is_flag=True,
    required=False,
    help='Show the short names of ARN Types. If empty, this will show RAW ARNs only.'
)
def arn_table(name, service, list_arn_types):
    """Query the ARN Table from the Policy Sentry database"""
    db_session = connect_db(DATABASE_FILE_PATH)
    # Get a list of all RAW ARN formats available through the service.
    if name is None and list_arn_types is False:
        raw_arns = get_raw_arns_for_service(db_session, service)
        for item in raw_arns:
            print(item)
    # Get a list of all the ARN types per service, paired with the RAW ARNs
    elif name is None and list_arn_types:
        output = get_arn_types_for_service(db_session, service)
        print(json.dumps(output, indent=4))
    # Get the raw ARN format for the `cloud9` service with the short name
    # `environment`
    else:
        output = get_arn_type_details(db_session, service, name)
        print(json.dumps(output, indent=4))


@query.command(
    short_help='Query the condition table.'
)
@click.option(
    '--name',
    type=str,
    required=False,
    help='Get details on a specific condition key. Leave this blank to get a list of all condition keys '
         'available to the service.')
@click.option(
    '--service',
    type=str,
    required=True,
    help="Filter according to AWS service."
)
def condition_table(name, service):
    """Query the condition keys table from the Policy Sentry database"""
    db_session = connect_db(DATABASE_FILE_PATH)
    # Get a list of all condition keys available to the service
    if name is None:
        condition_results = get_condition_keys_for_service(db_session, service)
        for item in condition_results:
            print(item)
    # Get details on the specific condition key
    else:
        output = get_condition_key_details(db_session, service, name)
        print(json.dumps(output, indent=4))
