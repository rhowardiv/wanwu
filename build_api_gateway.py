#!/usr/bin/env python
"""
Set up the API Gateway
"""
from __future__ import absolute_import

import boto3
import botocore.exceptions

import build_lambda


def main(client):
    """
    Run through all API Gateway setup steps

    todo:

    - Create prod APIG stage
    - deploy to prod APIG stage

    For now do this manually...
    """
    gateway_id = create_gateway(client, 'wanwu')
    root = resource_by_path(client, gateway_id, '/')
    create_method(client, gateway_id, root['id'], 'GET')
    lamb, lamb_client = build_lambda.build_lambda()
    create_integration(client,
                       lamb_client,
                       gateway_id,
                       root['id'],
                       'GET',
                       lamb)
    child = wild_child(client, gateway_id, root['id'])
    create_method(client, gateway_id, child['id'], 'GET')
    create_integration(client,
                       lamb_client,
                       gateway_id,
                       child['id'],
                       'GET',
                       lamb)


def create_gateway(client, name):
    """
    Create an API Gateway with the given name idempotently
    :return: The API Gateway ID
    """
    limit = 100
    _ = client.get_rest_apis(limit=limit)
    gateways = _['items']
    if len(gateways) >= limit:
        raise OverflowError(
            "There may be more API Gateways configured; according to "
            "https://boto3.readthedocs.io/en/latest/reference/services"
            "/apigateway.html#APIGateway.Client.get_rest_apis, you can "
            "raise the limit to 500",
        )
    for gateway in gateways:
        if gateway['name'] == name:
            # The API Gateway exists
            return gateway['id']
    created = client.create_rest_api(name=name)
    return created['id']


def resource_by_path(client, gateway_id, path):
    """
    Fetch the "/" resource on an API Gateway
    :return: dict resource entry
    """
    limit = 100
    response = client.get_resources(restApiId=gateway_id, limit=limit)
    resources = response['items']
    if len(resources) >= limit:
        raise OverflowError(
            "There may be more resources configured; according to "
            "https://boto3.readthedocs.io/en/latest/reference/services/"
            "apigateway.html#APIGateway.Client.get_resources, you can "
            "raise the limit to 500",
        )
    for resource in resources:
        if resource['path'] == path:
            return resource
    raise RuntimeError("{} resource not found. How odd".format(path))


def wild_child(client, gateway_id, parent_resource_id):
    """
    The wildcard resource, only child of the root resource
    """
    try:
        return _new_wild_child(client, gateway_id, parent_resource_id)
    except botocore.exceptions.ClientError as err:
        if 'ConflictException' not in str(err):
            # Expected:
            # botocore.exceptions.ClientError: An error occurred
            # (ConflictException) when calling the CreateResource
            # operation: Another resource with the same parent already
            # has this name: [name]
            raise
        return resource_by_path(client, gateway_id, '/{proxy+}')


def _new_wild_child(client, gateway_id, parent_resource_id):
    """
    Create a wildcard child resource
    """
    response = client.create_resource(restApiId=gateway_id,
                                      parentId=parent_resource_id,
                                      pathPart='{proxy+}')
    return response


def create_method(client, gateway_id, resource_id, method):
    """
    Idempotently create a method on an API Gateway resource
    :return: dict method info
    """
    try:
        client.get_method(restApiId=gateway_id,
                          resourceId=resource_id,
                          httpMethod=method)
    except botocore.exceptions.ClientError as err:
        if 'NotFoundException' not in str(err):
            # Expected:
            # botocore.exceptions.ClientError: An error occurred
            # (NotFoundException) when calling the GetMethod operation:
            # Invalid Method identifier specified
            raise
    else:
        return client.get_method(restApiId=gateway_id,
                                 resourceId=resource_id,
                                 httpMethod=method)
    return client.put_method(restApiId=gateway_id,
                             resourceId=resource_id,
                             httpMethod=method,
                             authorizationType='NONE')


def create_integration(gateway_client,
                       lambda_client,
                       gateway_id,
                       resource_id,
                       method,
                       lamb):
    """
    Idempotently create an integration with a lambda

    Missing a permission step! In the web console, when you make the
    integration, "You are about to give API Gateway permission to invoke
    your Lambda function" also happens...
    """
    arn = lambda_arn_parts(lamb['Configuration']['FunctionArn'])
    args = dict(
        restApiId=gateway_id,
        resourceId=resource_id,
        httpMethod=method,
        type='AWS_PROXY',
        # req'd for AWS{_PROXY} type
        # see https://github.com/aws/aws-sdk-js/issues/769
        integrationHttpMethod='POST',
        uri='arn:aws:apigateway:{region}:'
        'lambda:path/2015-03-31/functions/'
        'arn:aws:lambda:{region}:{account_id}:function:{function_name}'
        '/invocations'.format(**arn)
    )
    integration = gateway_client.put_integration(**args)
    statement_id = '{}-{}-{}-{}'.format(gateway_id,
                                        resource_id,
                                        method,
                                        arn['function_name'])
    lambda_client.add_permission(
        FunctionName=arn['function_name'],
        StatementId=statement_id,
        Action='lambda:InvokeFunction',
        Principal='apigateway.amazonaws.com',
        # might need SourceArn
        # eg arn:aws:execute-api:us-east-1:aws-acct-id:api-id/*/POST/DynamoDBManager
        # see http://docs.aws.amazon.com/lambda/latest/dg/with-on-demand-https-example-configure-event-source.html
    )
    return integration


def lambda_arn_parts(arn):
    """
    Take an ARN and return its labelled parts
    :arg arn: eg arn:aws:lambda:us-east-1:541056992659:function:wanwu_lambda
    :rtype: dict
    """
    return dict(zip(['"arn"',
                     '"aws"',
                     '"lambda"',
                     'region',
                     'account_id',
                     '"function"',
                     'function_name'],
                    arn.split(':')))


if __name__ == '__main__':
    main(boto3.client('apigateway'))
