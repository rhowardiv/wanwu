#!/usr/bin/env python3
"""
Set up the Lambda
"""
import base64
import datetime
import hashlib
import json
import os
import tempfile
import zipfile
from typing import Dict
from typing import NamedTuple
from typing import Tuple

import boto3
import botocore

_ROLE = 'wanwu_lambda_role'
_NAME = 'wanwu_lambda'
_TIMEOUT = 5  # will be the lambda execution time limit!


class Role(NamedTuple):
    Path: str
    RoleName: str
    RoleId: str
    Arn: str
    CreateDate: datetime.datetime
    AssumeRolePolicyDocument: str
    Description: str


def build_lambda() -> Tuple[dict, dict]:
    """ Run through all Lambda setup steps """
    role = lambda_role(boto3.client('iam'), _ROLE)
    client = boto3.client('lambda')
    lamb = create_lambda(client, _NAME, role.Arn)
    return lamb, client


def add_lambda_permission():
    """ Grant invoke permissions to another AWS resource """


def lambda_role(
    iam_client,
    role_name: str
) -> Role:
    """
    The role the lambda will have
    Idempotent: creates it if it doesn't exist
    """
    try:
        boto_role: dict = iam_client.create_role(
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
            # operation: Role with name _ROLE already exists.
            boto_role = iam_client.get_role(
                RoleName=role_name
            )['Role']
        else:
            raise
    role = Role(**boto_role)
    assign_lambda_policy(iam_client, role.RoleName)
    return role


def assign_lambda_policy(iam_client, role_name: str) -> None:
    """
    Assign extra policy to the lambda IAM role
    It needs this policy to write CloudWatch logs
    """
    policy_arn = ('arn:aws:iam::aws:'
                  'policy/service-role/AWSLambdaBasicExecutionRole')
    iam_client.attach_role_policy(
        RoleName=role_name,
        PolicyArn=policy_arn,
    )


def create_lambda(
    lambda_client,
    name: str,
    role_arn: str,
) -> Dict[str, dict]:
    """
    Create/publish the lambda code.
    :arg lambda_client: The boto client
    :arg str name: Lambda name; will look for local file [name].py
    """
    package_filename = create_deploy_package(f'{name}.py')
    try:
        read_lambda = lambda_client.get_function(FunctionName=name)
    except botocore.exceptions.ClientError as err:
        if 'ResourceNotFoundException' not in str(err):
            raise
            # Expected when lambda not yet created:
            # botocore.exceptions.ClientError: An error occurred
            # (ResourceNotFoundException) when calling the GetFunction
            # operation: Function not found:
            # arn:aws:lambda:us-east-1:541056992659:function:_NAME
        # lambda does not exist -- create it
        with open(package_filename, 'rb') as package_handle:
            zip_file = package_handle.read()
        lambda_client.create_function(
            FunctionName=name,
            Runtime='python3.6',
            Role=role_arn,
            Handler=f'{name}.lambda_handler',
            Code={'ZipFile': zip_file},
            Timeout=_TIMEOUT,
        )
    else:
        if read_lambda['Configuration']['Timeout'] != _TIMEOUT:
            read_lambda['Configuration'] = (
                lambda_client.update_function_configuration(
                    FunctionName=name,
                    Timeout=_TIMEOUT,
                )
            )
        # check signatures to see if publish is needed
        local_sig = hashlib.sha256()
        with open(package_filename, 'rb') as package_content:
            local_sig.update(package_content.read())
        lambda_sig = read_lambda['Configuration']['CodeSha256']
        if base64.b64encode(local_sig.digest()) == lambda_sig:
            return read_lambda
        with open(package_filename, 'rb') as package_handle:
            zip_file = package_handle.read()
        lambda_client.update_function_code(
            FunctionName=name,
            ZipFile=zip_file,
        )
    read_lambda = lambda_client.get_function(FunctionName=name)
    return read_lambda


def create_deploy_package(from_file: str) -> str:
    """
    Create a zipfile Lambda deployment package in a temporary location
    """
    fd, fname = tempfile.mkstemp()
    z = zipfile.ZipFile(os.fdopen(fd, 'wb'), mode='w')
    z.write(from_file)
    z.close()
    return fname


if __name__ == '__main__':
    print(json.dumps(build_lambda(), default=str))
