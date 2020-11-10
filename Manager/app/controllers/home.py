from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3
from datetime import timedelta, datetime

from app import cw


bp = Blueprint('home', __name__, template_folder='../templates')


@bp.route('/', methods=['GET', 'POST'])
def root():
    ec2 = boto3.resource('ec2')
    instances = ec2.instances.all()
    num_workers_stats = get_num_workers()
    return render_template('home.html', num_workers_stats=num_workers_stats, instances=instances)


@bp.route('/worker_info/<id>', methods=['GET', 'POST'])
def worker_info(id):
    cpu_stats = get_total_cpu_utilization(id)
    http_stats = get_http_request_rate(id)
    return render_template('worker_info.html', cpu_stats=cpu_stats, http_stats=http_stats)


@bp.route('/worker_destroy/<id>', methods=['GET', 'POST'])
def worker_destroy(id):
    ec2 = boto3.resource('ec2')    
    ec2.instances.filter(InstanceIds=[id]).terminate()
    return redirect(url_for('home.root'))


# @bp.route('/manager', methods=['GET', 'POST'])
# def manager():
    
#     return render_template('manager.html')



def get_num_workers():
    client = boto3.client('cloudwatch')
    workers = client.get_metric_statistics(
        Period = 60,
        StartTime = datetime.utcnow() - timedelta(seconds=30*60),
        EndTime = datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName = 'NumWorkers',
        Namespace = 'AWS/EC2',
        Statistics = ['Average'],
        Dimensions = [{'Name': 'InstanceId', 'Value': 'i-03a0d1e856d0e7a8b'}]
    )
    return processing_data(workers, 'Average')


def get_total_cpu_utilization(id):
    client = boto3.client('cloudwatch')
    cpu = client.get_metric_statistics(
        Period=1 * 60,
        StartTime=datetime.utcnow() - timedelta(seconds=60 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName='CPUUtilization',
        Namespace='AWS/EC2',  # Unit='Percent',
        Statistics=['Average'],
        Dimensions=[{'Name': 'InstanceId', 'Value': id}]
    )
    return processing_data(cpu, 'Average')


def get_http_request_rate(id):
    client = boto3.client('cloudwatch')
    http = client.get_metric_statistics(
        Period = 60,
        StartTime = datetime.utcnow() - timedelta(seconds=30*60),
        EndTime = datetime.utcnow() - timedelta(seconds=0 * 60),
        MetricName = 'HttpRequestCount',
        Namespace='AWS/EC2',
        Statistics = ['Sum'],
        Dimensions = [{'Name': 'InstanceId', 'Value': id}]
    )
    return processing_data(http, 'Sum')


def processing_data(metric, method):
    data_stats = []

    for point in metric['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute/60
        data_stats.append([time, point[method]])

    data_stats = sorted(metric, key=itemgetter(0))
    return data_stats