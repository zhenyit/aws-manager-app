from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3
from datetime import datetime, timedelta
from operator import itemgetter


bp = Blueprint('manager', __name__, template_folder='../templates')


@bp.route('/instances', methods=['GET'])
def get_instances():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    return render_template("instances.html", title="EC2 Instances", instances=instances)


@bp.route('/get_details/<id>', methods=['GET'])
def get_details(id):
    ec2 = boto3.resource('ec2')

    instance = ec2.Instance(id)

    client = boto3.client('cloudwatch')

    metric_name = 'CPUUtilization'

    #    CPUUtilization, NetworkIn, NetworkOut, NetworkPacketsIn,
    #    NetworkPacketsOut, DiskWriteBytes, DiskReadBytes, DiskWriteOps,
    #    DiskReadOps, CPUCreditBalance, CPUCreditUsage, StatusCheckFailed,
    #    StatusCheckFailed_Instance, StatusCheckFailed_System

    namespace = 'AWS/EC2'
    statistic = 'Average'  # could be Sum,Maximum,Minimum,SampleCount,Average

    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName=metric_name,
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    cpu_stats = []

    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        cpu_stats.append([time, point['Average']])

    cpu_stats = sorted(cpu_stats, key=itemgetter(0))

    statistic = 'Sum'  # could be Sum,Maximum,Minimum,SampleCount,Average

    network_in = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='NetworkIn',
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    net_in_stats = []

    for point in network_in['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        net_in_stats.append([time, point['Sum']])

    net_in_stats = sorted(net_in_stats, key=itemgetter(0))

    network_out = client.get_metric_statistics(
        Period=5 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='NetworkOut',
        Namespace=namespace,  # Unit='Percent',
        Statistics=[statistic],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )

    net_out_stats = []

    for point in network_out['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        net_out_stats.append([time, point['Sum']])

        net_out_stats = sorted(net_out_stats, key=itemgetter(0))

    return render_template("view.html", title="Instance Info",
                           instance=instance,
                           cpu_stats=cpu_stats,
                           net_in_stats=net_in_stats,
                           net_out_stats=net_out_stats)


@bp.route('/destroy_instance/<id>', methods=['POST'])
def destroy_instance(id):
    ec2 = boto3.resource('ec2')
    ec2.instances.filter(InstanceIds=[id]).terminate()
    return redirect(url_for('get_instances'))


@bp.route('/launch_instance', methods=['POST'])
def launch_instance():
    ec2 = boto3.resource('ec2')
    ec2.create_instances(LaunchTemplate={'LaunchTemplateId': 'lt-0331e69509ec8b60c'}, MinCount=1, MaxCount=1)
    return redirect(url_for('manager.get_instances'))

# @bp.route('/create', methods=['POST'])
# def ec2_create():
#     ec2 = boto3.resource('ec2')
#     ec2.create_instances(ImageId=config.ami_id, MinCount=1, MaxCount=1,
#                          InstanceType='t2.small', SubnetId=config.subnet_id)
#     return redirect(url_for('ec2_list'))
#
#
# @bp.route('/start-worker', methods=['GET'])
# def start_worker():
#     instance_id = 'i-0e09ce78173db35f2'
#
#     ec2 = boto3.client('ec2')
#
#     # Do a dryrun first to verify permissions
#     try:
#         ec2.start_instances(InstanceIds=[instance_id], DryRun=True)
#     except ClientError as e:
#         if 'DryRunOperation' not in str(e):
#             raise
#
#     # Dry run succeeded, run start_instances without dryrun
#     try:
#         response = ec2.start_instances(InstanceIds=[instance_id], DryRun=False)
#         print(response)
#         return response
#     except ClientError as e:
#         print(e)
#
#
# @bp.route('/stop-worker', methods=['GET'])
# def stop_worker():
#     instance_id = 'i-0e09ce78173db35f2'
#
#     ec2 = boto3.client('ec2')
#
#     # Do a dryrun first to verify permissions
#     try:
#         ec2.stop_instances(InstanceIds=[instance_id], DryRun=True)
#     except ClientError as e:
#         if 'DryRunOperation' not in str(e):
#             raise
#
#     # Dry run succeeded, call stop_instances without dryrun
#     try:
#         response = ec2.stop_instances(InstanceIds=[instance_id], DryRun=False)
#         print(response)
#         return response
#     except ClientError as e:
#         print(e)
