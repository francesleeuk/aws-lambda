import boto3
import botocore
from datetime import datetime

ec2_client = boto3.client('ec2')
ec2_res = boto3.resource('ec2')
asg_client = boto3.client('autoscaling')

interfaces = {'-lan1':1,'-mgmt':2}
interface_failure = False

def lambda_handler(event, context):
    instance_id = event["detail"]["EC2InstanceId"]
    instance_name = get_instance_name(instance_id)
    for ints in interfaces:
        interface_id = get_interface(eni_desc=instance_name+ints)
        attachment = attach_interface(interface_id,instance_id,device_index=interfaces[ints])

    # For this simple example, there's no checking as to success of failure of above
    # You might want to check for success and ABANDON the lifecycle action depending on your use case
        
    try:
        asg_client.complete_lifecycle_action(
            LifecycleHookName = event['detail']['LifecycleHookName'],
            AutoScalingGroupName = event['detail']['AutoScalingGroupName'],
            LifecycleActionToken = event['detail']['LifecycleActionToken'],
            LifecycleActionResult = 'CONTINUE'
            )
    except botocore.exceptions.ClientError as e:
        log ("Error completing life cycle hook for instance {}: {}".format(instance_id,e.response['Error']['Code']))
            
def get_instance_name(instance_id):
    try:
        instance = ec2_res.Instance(instance_id)
        instance_name = next((item['Value'] for item in instance.tags if item['Key'] == 'Name'), None)
        log ("Instance name {}:".format(instance_name))
        
    except botocore.exceptions.ClientError as e:
        log("Error describing the instance {} : {}".format(instance_id,e.response['Error']['Code']))
        instance_name = None
    
    return instance_name
        
def get_interface(eni_desc):
    network_interface_id = None
    
    try:
        network_interface = ec2_client.describe_network_interfaces(Filters=[{'Name':'description','Values':[eni_desc]}])
        network_interface_id = network_interface['NetworkInterfaces'][0]['NetworkInterfaceId']
        log("Found network interface: {}".format(network_interface_id))
    except botocore.exceptions.ClientError as e:
        log("Error retrieving network interface: {}".format(e.response['Error']['Code']))
        
    return network_interface_id
    
def attach_interface(network_interface_id,instance_id,device_index):
    attachment = None
    
    if network_interface_id and instance_id:
        try:
            attach_interface = ec2_client.attach_network_interface (
                NetworkInterfaceId = network_interface_id,
                InstanceId = instance_id,
                DeviceIndex = device_index
            )
            attachment = attach_interface['AttachmentId']
            log("Created network attachment: {}".format(attachment))
        except botocore.exceptions.ClientError as e:
            log("Error attaching interface: {}".format(e.response['Error']['Code']))
            
        return attachment

def log(message):
    print (datetime.utcnow().isoformat() + 'Z ' + message)
