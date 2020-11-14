from flask import Blueprint, render_template
from flask import request, flash, redirect, url_for
import boto3
from datetime import datetime, timedelta
from operator import itemgetter

bp = Blueprint('load_balancer', __name__, template_folder='../templates')

MAXIMUN_WORKER_POOL_SIZE = 8
MINIMUM_WORKER_POOL_SIZE = 1


@bp.route('/', methods=['GET'])
def get_workers():
    elb_client = boto3.client('elbv2')
    cw_client = boto3.client('cloudwatch')
    ec2_resource = boto3.resource('ec2')

    dns_name = get_elb_dns(elb_client)
    dns_url = "http://" + dns_name

    worker_instances = get_worker_list(elb_client, ec2_resource)

    worker_stats = get_worker_num_graph(cw_client)

    return render_template("load_balancer.html", title="EC2 Manager",
                           dns_name=dns_name, dns_url=dns_url,
                           worker_instances=worker_instances, worker_stats = worker_stats,
                           max_pool_size=MAXIMUN_WORKER_POOL_SIZE,
                           min_pool_size=MINIMUM_WORKER_POOL_SIZE
                           )


def get_elb_dns(elb_client):
    elbs = elb_client.describe_load_balancers()['LoadBalancers']
    dns_name = elbs[0]['DNSName']
    return dns_name


def get_worker_list(elb_client, ec2):
    # Get target group ARN
    target_groups = elb_client.describe_target_groups()['TargetGroups']
    target_group_arn = target_groups[0]['TargetGroupArn']

    # Get target group instance list
    targets = elb_client.describe_target_health(TargetGroupArn=target_group_arn)['TargetHealthDescriptions']

    instance_id_list = []
    if not targets:
        target_instances = []
    else:
        for target in targets:
            instance_id_list.append(target['Target']['Id'])

        target_instances = ec2.instances.filter(InstanceIds=instance_id_list)
    return target_instances


def get_worker_num_graph(cw_client):
    statistic = 'Average'
    metric_name = 'HealthyHostCount'
    namespace = 'AWS/ApplicationELB'

    worker = cw_client.get_metric_statistics(
        Namespace=namespace,
        MetricName=metric_name,
        Dimensions=[
            {
                'Name': 'LoadBalancer',
                'Value': 'app/user-app-elb/4dca1eed08c3a83d'
            },
            {
                'Name': 'TargetGroup',
                'Value': 'targetgroup/user-app-target-group/86d3de612c7d4741'
            }
        ],
        StartTime=datetime.utcnow() - timedelta(seconds=30 * 60),
        EndTime=datetime.utcnow(),
        Period=30,
        Statistics=[statistic],

    )

    worker_stats = []
    print(worker)

    for point in worker['Datapoints']:
        hour = point['Timestamp'].hour
        minute = point['Timestamp'].minute
        time = hour + minute / 60
        worker_stats.append([time, point['Average']])

    worker_stats = sorted(worker_stats, key=itemgetter(0))

    return worker_stats


@bp.route('/shrink_pool', methods=['POST'])
def shrink_pool():
    global MAXIMUN_WORKER_POOL_SIZE
    MAXIMUN_WORKER_POOL_SIZE -= 1
    return redirect(url_for('worker.get_workers'))


@bp.route('/expand_pool', methods=['POST'])
def expand_pool():
    global MAXIMUN_WORKER_POOL_SIZE
    MAXIMUN_WORKER_POOL_SIZE += 1
    return redirect(url_for('worker.get_workers'))


@bp.route('/add_worker', methods=['POST'])
def add_worker():
    ec2_resource = boto3.resource('ec2')
    # Launch a new user-app worker
    new_instance = ec2_resource.create_instances(LaunchTemplate={'LaunchTemplateId': 'lt-0331e69509ec8b60c'},
                                                 MinCount=1, MaxCount=1)
    new_instance_id = new_instance[0].id

    # Register the new instance to target group
    waiter = boto3.client('ec2').get_waiter('instance_running')
    waiter.wait(InstanceIds=[new_instance_id])
    elb_client = boto3.client('elbv2')
    target_groups = elb_client.describe_target_groups()['TargetGroups']
    target_group_arn = target_groups[0]['TargetGroupArn']
    elb_client.register_targets(
        TargetGroupArn=target_group_arn,
        Targets=[
            {
                'Id': new_instance_id,
                'Port': 5000
            },
        ]
    )
    return redirect(url_for('worker.get_workers'))


@bp.route('/remove_worker/<id>', methods=['POST'])
def remove_worker(id):
    elb_client = boto3.client('elbv2')
    target_groups = elb_client.describe_target_groups()['TargetGroups']
    target_group_arn = target_groups[0]['TargetGroupArn']
    elb_client.deregister_targets(
        TargetGroupArn=target_group_arn,
        Targets=[
            {
                'Id': id,
                'Port': 5000
            },
        ]
    )
    ec2 = boto3.resource('ec2')
    ec2.instances.filter(InstanceIds=[id]).terminate()
    return redirect(url_for('worker.get_workers'))
