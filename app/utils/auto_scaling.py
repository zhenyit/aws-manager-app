from sqlalchemy import desc
from ..models
from app.models.configuration import Configuration
from app import db
from datetime import datetime, timedelta

import time
import boto3
import os

elb_client = boto3.client('elbv2')
cw_client = boto3.client('cloudwatch')
ec2_resource = boto3.resource('ec2')


MAXIMUN_WORKER_POOL_SIZE = 8
MINIMUM_WORKER_POOL_SIZE = 1

LAUNCH_TEMPLATE_ID = 'lt-0359893f0160ff648'

TARGET_GROUP_ARN = 'arn:aws:elasticloadbalancing:us-east-1:446845854592:targetgroup/user-app-target-group/d0bf322c6a58726b'


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
        StartTime=datetime.utcnow() - timedelta(seconds=3 * 60),
        EndTime=datetime.utcnow() - timedelta(seconds=0 * 60),
        Statistics=['Average'],
        Period=60
    )

    total_utils = 0
    avg_utils = 0

    if 'Datapoints' in cpu_stats:
        for datapoint in cpu_stats['Datapoints']:
            total_utils += datapoint['Average']
        if len(cpu_stats['Datapoints']) > 0:
            avg_utils = total_utils / len(cpu_stats['Datapoints'])
    return avg_utils


def launch_one_worker():
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


def launch_worker_by_ratio(ratio):
    curr_instance_num = len(get_workers_id_list())
    new_instance_num = int(curr_instance_num * (ratio - 1))

    if (curr_instance_num + new_instance_num) > MAXIMUN_WORKER_POOL_SIZE:
        new_instance_num = MAXIMUN_WORKER_POOL_SIZE - curr_instance_num
        print("#Worker(after growing) >  Maximum pool size")
        print(" Expand to maximum pool size")
    else:
        print("#Worker(after growing) <= Maximum pool size")
        print(" Expand by ratio")

    for i in range(new_instance_num):
        # Launch a new instance
        launch_one_worker()


def terminate_worker_by_ratio(ratio):
    instances_id = get_workers_id_list()
    curr_instance_num = len(instances_id)
    terminate_instance_num = int(curr_instance_num * (1 - ratio))

    if (curr_instance_num - terminate_instance_num) < MINIMUM_WORKER_POOL_SIZE:
        terminate_instance_num = curr_instance_num - MINIMUM_WORKER_POOL_SIZE
        print("#Worker(after shrinking) <  Minimum pool size")
        print(" Shrink to minimum pool size")
    else:
        print("#Worker(after shrinking) >= Minimum pool size")
        print(" Shrink by ratio")

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

    print("$Terminate worker")


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
                util = get_worker_cpu_utils(worker_id)
                total_cpu_utils = total_cpu_utils + util
            avg_cpu_utils = total_cpu_utils / worker_num

        print("Average CPU utilization = {0:.2%}".format(0.01*avg_cpu_utils))

        # Get current config
        db.session.commit()
        config = Configuration.query.order_by(desc(Configuration.create_time)).first()

        # Scaling
        if not workers_id:
            launch_one_worker()
            time.sleep(100)
            print("No worker in the pool")
            print("$Launch one worker")
        elif not config:
            print("No Auto scaling configuration")
            print("$No Operation!")
        elif avg_cpu_utils > config.grow_threshold:
            launch_worker_by_ratio(config.expand_ratio)
            print("Average CPU utilization >= {0:.2%}".format(0.01 * config.grow_threshold))
            print("$Launch worker")
            time.sleep(120)
        elif avg_cpu_utils < config.shrink_threshold:
            print("Average CPU utilization <= {0:.2%}".format(0.01 * config.shrink_threshold))
            if len(workers_id) > MINIMUM_WORKER_POOL_SIZE:
                terminate_worker_by_ratio(config.shrink_ratio)
                time.sleep(120)
            else:
                print("#Worker not larger than minimum pool size")
                print("$No Operation!")
        else:
            print("$No Operation!")

        time.sleep(5)


