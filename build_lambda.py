#!/usr/bin/env python
"""
Set up the Lambda
"""
import base64
import hashlib
import json
import os
import tempfile
import zipfile

import boto3
import botocore


def build_lambda():
    """ Run through all Lambda setup steps """
    role = create_lambda_ar_role(boto3.client('iam'),
                                 'wanwu_lambda_role')
    client = boto3.client('lambda')
    lamb = create_lambda(client, 'wanwu_lambda', role)
    return lamb, client


def add_lambda_permission():
    """ Grant invoke permissions to another AWS resource """


def create_lambda_ar_role(iam_client, role_name):
    """
    Idempotently create the Lambda execution role
    :return: role info dict
    """
    try:
        role = iam_client.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument="""{
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }"""
        )['Role']
    except botocore.exceptions.ClientError as err:
        if 'EntityAlreadyExists' in str(err):
            # Expected:
            # botocore.exceptions.ClientError: An error occurred
            # (EntityAlreadyExists) when calling the CreateRole
            # operation: Role with name wanwu_lambda_role already
            # exists.
            role = iam_client.get_role(
                RoleName=role_name
            )['Role']
        else:
            raise
    assign_lambda_policy(iam_client, role)
    return role


def assign_lambda_policy(iam_client, role):
    """
    Assign extra policy to the lambda IAM role
    It needs this policy to write CloudWatch logs
    """
    policy_arn = ('arn:aws:iam::aws:'
                  'policy/service-role/AWSLambdaBasicExecutionRole')
    iam_client.attach_role_policy(
        RoleName=role['RoleName'],
        PolicyArn=policy_arn,
    )


def create_lambda(lambda_client, name, role):
    """
    Create/publish the lambda code.
    :arg lambda_client: The boto client
    :arg str name: Lambda name; will look for local file [name].py
    """
    package_filename = create_deploy_package('{}.py'.format(name))
    try:
        read_lambda = lambda_client.get_function(FunctionName=name)
    except botocore.exceptions.ClientError as err:
        if 'ResourceNotFoundException' not in str(err):
            raise
            # Expected when lambda not yet created:
            # botocore.exceptions.ClientError: An error occurred
            # (ResourceNotFoundException) when calling the GetFunction
            # operation: Function not found:
            # arn:aws:lambda:us-east-1:541056992659:function:wanwu_lambda
        # lambda does not exist -- create it
        with open(package_filename) as package_handle:
            zip_file = package_handle.read()
        lambda_client.create_function(
            FunctionName=name,
            Runtime='python2.7',
            Role=role['Arn'],
            Handler='{}.handler'.format(name),
            Code={'ZipFile': zip_file},
        )
    else:
        # check signatures to see if publish is needed
        local_sig = hashlib.sha256()
        with open(package_filename) as package_content:
            local_sig.update(package_content.read())
        lambda_sig = read_lambda['Configuration']['CodeSha256']
        if base64.b64encode(local_sig.digest()) == lambda_sig:
            return read_lambda
        with open(package_filename) as package_handle:
            zip_file = package_handle.read()
        lambda_client.update_function_code(
            FunctionName=name,
            ZipFile=zip_file,
        )
    read_lambda = lambda_client.get_function(FunctionName=name)
    return read_lambda


def create_deploy_package(from_file):
    """
    Create a zipfile Lambda deployment package in a temporary location
    """
    fd, fname = tempfile.mkstemp()
    z = zipfile.ZipFile(os.fdopen(fd, 'w'), mode='w')
    z.write(from_file)
    z.close()
    return fname


if __name__ == '__main__':
    print json.dumps(build_lambda(), default=str)
