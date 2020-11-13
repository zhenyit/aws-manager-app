from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3
from datetime import datetime, timedelta
from operator import itemgetter

bp = Blueprint('worker', __name__, template_folder='../templates')


@bp.route('/get_workers', methods=['GET'])
def get_workers():
    # Get workers list
    elb_client = boto3.client('elbv2')
    ec2 = boto3.resource('ec2')

    instances = []

    # Get ELB DNS name
    elbs = elb_client.describe_load_balancers()['LoadBalancers']
    dns_name = elbs[0]['DNSName']

    # Get target group ARN
    target_groups = elb_client.describe_target_groups()['TargetGroups']
    target_group_arn = target_groups[0]['TargetGroupArn']

    # Get target group instance list
    targets = elb_client.describe_target_health(TargetGroupArn=target_group_arn)['TargetHealthDescriptions']

    instance_id_list = []
    for target in targets:
        instance_id_list.append(target['Target']['Id'])

    target_instances = ec2.instances.filter(InstanceIds=instance_id_list)

    return render_template("workers.html", title="EC2 Instances", instances=target_instances)
