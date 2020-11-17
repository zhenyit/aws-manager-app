from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3
import os
import collections
from datetime import datetime, timedelta
from operator import itemgetter

from app import db
from ..models.configuration import HttpRequestCount
from ..settings import BUCKET_NAME


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


@bp.route('/test', methods=['GET'])
def test():

    cw_client = boto3.client('cloudwatch')
    

    return "success"
    

@bp.route('/get_details/<id>', methods=['GET'])
def get_details(id):
    ec2 = boto3.resource('ec2')

    instance = ec2.Instance(id)

    cw_client = boto3.client('cloudwatch')

    cpu = cw_client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': id}],
        Statistics=['Average'],
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        Period=60
    )

    cpu_stats = []
    for point in cpu['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        cpu_stats.append([time, point['Average']])
    cpu_stats = sorted(cpu_stats, key=itemgetter(0))

    # Get http request data
    start_time = datetime.utcnow() - timedelta(seconds=30 * 60)
    start_timestamp = int(round(datetime.timestamp(start_time)))

    end_time = datetime.utcnow()
    end_timestamp = int(round(datetime.timestamp(end_time)))
    
    http_stats = HttpRequestCount.query.filter(HttpRequestCount.instance_id == id)\
                    .filter(HttpRequestCount.created_at >= start_time)\
                    .filter(HttpRequestCount.created_at <= end_time)\
                    .with_entities(HttpRequestCount.created_at).all()
    
    metric_data = []
    
    timestamps = list(map(lambda x: int(round(datetime.timestamp(x[0]))), http_stats))
    timestamps_dict = collections.Counter(timestamps)
    for minute_start_time in range(start_timestamp, end_timestamp, 120):
        http_req_per_minute = 0
        for second in range(minute_start_time, minute_start_time + 120):
            http_req_per_minute += timestamps_dict[second]
        metric_data.append({
                'MetricName': 'HttpRequestCount',
                'Dimensions': [
                    {
                        'Name': 'InstanceID',
                        'Value': id
                    },
                ],
                'Timestamp': datetime.fromtimestamp(minute_start_time),
                'Value': http_req_per_minute,
                'Unit': 'Count',
                'StorageResolution': 60,
            })

    cw_client.put_metric_data(
        Namespace='AWS/EC2',
        MetricData=metric_data
    )
    
    request_count = cw_client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='HttpRequestCount',
        Dimensions=[
            {
                'Name': 'InstanceID',
                'Value': id
            }
        ],
        Statistics=['Average'],
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        Period=60
    )

    request_count_stats = []

    for point in request_count['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        request_count_stats.append([time, point['Average']])
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


@bp.route('/delete_all_data', methods=['POST'])
def delete_all_data():
    # delete S3
    s3_client = boto3.resource('s3')
    bucket = s3_client.Bucket(BUCKET_NAME)
    bucket.objects.delete()

    # delete RDS
    db.drop_all()

    flash("All data deleted successfully")
    return redirect(url_for('get_instances'))