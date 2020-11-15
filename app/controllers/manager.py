from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3
import os
from datetime import datetime, timedelta
from operator import itemgetter


bp = Blueprint('manager', __name__, template_folder='../templates')


MANAGER_ID = os.getenv('MANAGER_ID')
LOAD_BALANCER = os.getenv('LOAD_BALANCER')
TARGET_GROUP = os.getenv('TARGET_GROUP')
TARGET_GROUP_ARN = os.getenv('TARGET_GROUP_ARN')


@bp.route('/instances', methods=['GET'])
def get_instances():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    return render_template("instances.html", title="EC2 Manager", instances=instances)


@bp.route('/get_details/<id>', methods=['GET'])
def get_details(id):
    ec2 = boto3.resource('ec2')

    instance = ec2.Instance(id)

    cw_client = boto3.client('cloudwatch')

    cpu = cw_client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[
            {
                'Name': 'InstanceId',
                'Value': id
            }
        ],
        Statistics=['Average'],
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        Period=60,
        Unit='Percent'
    )

    cpu_stats = []
    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        cpu_stats.append([time, point['Average']])
    cpu_stats = sorted(cpu_stats, key=itemgetter(0))

    request_count = cw_client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='HttpRequestCount',
        Dimensions=[
            {
                'Name': 'InstanceID',
                'Value': 'i-02e7ced1f9e41c7cd'
            }
        ],
        Statistics=['Sum'],
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        Period=60
    )
    print(request_count)

    request_count_stats = []

    for point in request_count['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        request_count_stats.append([time, point['Sum']])
    request_count_stats = sorted(request_count_stats, key=itemgetter(0))

    return render_template("view.html", title="Instance Info",
                           instance=instance,
                           cpu_stats=cpu_stats,
                           request_count_stats=request_count_stats)


@bp.route('/destroy_instance/<id>', methods=['POST'])
def destroy_instance(id):
    ec2 = boto3.resource('ec2')
    ec2.instances.filter(InstanceIds=[id]).terminate()
    return redirect(url_for('get_instances'))


@bp.route('/stop_manager', methods=['POST'])
def stop_manager():
    # Terminate all workers
    elb_client = boto3.client('elbv2')
    ec2_client = boto3.client('ec2')

    # Get target group instance list
    targets = elb_client.describe_target_health(TargetGroupArn=TARGET_GROUP_ARN)['TargetHealthDescriptions']

    for target in targets:
        instance_id = target['Target']['Id']
        elb_client.deregister_targets(
            TargetGroupArn=TARGET_GROUP_ARN,
            Targets=[
                {
                    'Id': instance_id,
                    'Port': 5000
                },
            ]
        )
        ec2 = boto3.resource('ec2')
        ec2.instances.filter(InstanceIds=[instance_id]).terminate()

    # Stop Manager
    ec2_client.stop_instances(InstanceIds=[MANAGER_ID])
    return "Goodbye"
