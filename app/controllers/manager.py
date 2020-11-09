from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3
from botocore.exceptions import ClientError

bp = Blueprint('manager', __name__, template_folder='../templates')


@bp.route('/display-worker', methods=['GET'])
def display_worker():
    ec2 = boto3.client('ec2')
    response = ec2.describe_instances()
    return response


@bp.route('/monitor-worker', methods=['GET'])
def monitor_worker():
    ec2 = boto3.client('ec2')
    response = ec2.monitor_instances(InstanceIds=['i-0e09ce78173db35f2'])
    return response


@bp.route('/start-worker', methods=['GET'])
def start_worker():
    instance_id = 'i-0e09ce78173db35f2'

    ec2 = boto3.client('ec2')

    # Do a dryrun first to verify permissions
    try:
        ec2.start_instances(InstanceIds=[instance_id], DryRun=True)
    except ClientError as e:
        if 'DryRunOperation' not in str(e):
            raise

    # Dry run succeeded, run start_instances without dryrun
    try:
        response = ec2.start_instances(InstanceIds=[instance_id], DryRun=False)
        print(response)
        return response
    except ClientError as e:
        print(e)


@bp.route('/stop-worker', methods=['GET'])
def stop_worker():
    instance_id = 'i-0e09ce78173db35f2'

    ec2 = boto3.client('ec2')

    # Do a dryrun first to verify permissions
    try:
        ec2.stop_instances(InstanceIds=[instance_id], DryRun=True)
    except ClientError as e:
        if 'DryRunOperation' not in str(e):
            raise

    # Dry run succeeded, call stop_instances without dryrun
    try:
        response = ec2.stop_instances(InstanceIds=[instance_id], DryRun=False)
        print(response)
        return response
    except ClientError as e:
        print(e)
