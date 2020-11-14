from sqlalchemy import desc
from app.models.configuration import Configuration
from app import db
from datetime import datetime, timedelta
import time
import boto3
import os

elb_client = boto3.client('elbv2')
cw_client = boto3.client('cloudwatch')
ec2_resource = boto3.resource('ec2')

MAXIMUN_WORKER_POOL_SIZE = os.getenv('MAXIMUN_WORKER_POOL_SIZE')
MINIMUM_WORKER_POOL_SIZE = os.getenv('MAXIMUN_WORKER_POOL_SIZE')

LAUNCH_TEMPLATE_ID = os.getenv('LAUNCH_TEMPLATE_ID')
TARGET_GROUP_ARN = os.getenv('TARGET_GROUP_ARN')


def get_workers_id_list():
    targets = elb_client.describe_target_health(TargetGroupArn=TARGET_GROUP_ARN)['TargetHealthDescriptions']
    instances_id = []
    if not targets:
        instances_id = []
    else:
        for target in targets:
            instances_id.append(target['Target']['Id'])
    return instances_id


def get_worker_cpu_utils(instance_id):
    cpu_stats = cw_client.get_metric_statistics(
        Namespace='AWS/EC2',
        MetricName='CPUUtilization',
        Dimensions=[{'Name': 'InstanceId', 'Value': instance_id}],
        StartTime=datetime.utcnow() - timedelta(seconds=2 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        Statistics=['Average'],
        Period=30,
        Unit='Percent'
    )

    total_utils = 0
    avg_utils = 0

    if 'Datapoints' in cpu_stats:
        for datapoint in cpu_stats['Datapoints']:
            total_utils += datapoint['Average']
        avg_utils = total_utils / len(cpu_stats['Datapoints'])
    return avg_utils


def launch_worker_by_ratio(ratio):
    curr_instance_num = len(get_workers_id_list())
    new_instance_num = int(curr_instance_num * (ratio - 1))

    if (curr_instance_num + new_instance_num) > MAXIMUN_WORKER_POOL_SIZE:
        new_instance_num = MAXIMUN_WORKER_POOL_SIZE - curr_instance_num

    for i in range(new_instance_num):
        # Launch a new instance
        new_instance = ec2_resource.create_instances(
            LaunchTemplate={'LaunchTemplateId': LAUNCH_TEMPLATE_ID},
            MinCount=1,
            MaxCount=1
        )
        new_instance_id = new_instance[0].id

        # Register the new instance to target group
        waiter = boto3.client('ec2').get_waiter('instance_running')
        waiter.wait(InstanceIds=[new_instance_id])

        elb_client.register_targets(
            TargetGroupArn=TARGET_GROUP_ARN,
            Targets=[
                {
                    'Id': new_instance_id,
                    'Port': 5000
                },
            ]
        )


def terminate_worker_by_ratio(ratio):
    instances_id = get_workers_id_list()
    curr_instance_num = len(instances_id)
    terminate_instance_num = int(curr_instance_num * (1 - ratio))

    if (curr_instance_num - terminate_instance_num) < MINIMUM_WORKER_POOL_SIZE:
        terminate_instance_num = 0

    if terminate_instance_num > 0:
        for i in range(terminate_instance_num):
            instance_id = instances_id[i]

            elb_client.deregister_targets(
                TargetGroupArn=TARGET_GROUP_ARN,
                Targets=[
                    {
                        'Id': instance_id,
                        'Port': 5000
                    },
                ]
            )

            ec2_resource.instances.filter(InstanceIds=[instance_id]).terminate()


if __name__ == '__main__':
    while True:
        # Get target group worker list
        workers_id = get_workers_id_list()
        worker_num = len(workers_id)

        # Calculate average CPU utilization
        total_cpu_utils = 0
        avg_cpu_utils = 0

        if worker_num > 0:
            for worker_id in workers_id:
                total_cpu_utils += get_worker_cpu_utils(worker_id)
            avg_cpu_utils = total_cpu_utils / worker_num

        # Get current config
        db.session.commit()
        config = Configuration.query.order_by(desc(Configuration.create_time)).first()

        # Scaling
        if not workers_id:
            time.sleep(10)
            print("no worker")
        elif avg_cpu_utils > config.grow_threshold:
            launch_worker_by_ratio(config.expand_ratio)
            print("auto add worker")
            time.sleep(300)
        elif avg_cpu_utils < config.shrink_threshold:
            terminate_worker_by_ratio(config.shrink_ratio)
            print("auto terminate worker")
            time.sleep(300)

        time.sleep(5)


