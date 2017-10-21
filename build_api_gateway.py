#!/usr/bin/env python3
"""
Set up the API Gateway as a lambda proxy
It's referred to as a "proxy" because it does nothing with the incoming
request, only hands it off to the lambda. This is a special
configuration of API Gateways that was made available some time after
the main API Gateway functionality.
"""
import boto3
import botocore.exceptions

import build_lambda

_NAME = 'wanwu'


def main(client):
    """
    Run through all API Gateway setup steps
    """
    gateway_id = create_gateway(client, _NAME)
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
    client.create_deployment(restApiId=gateway_id,
                             stageName='prod')
    print(client.update_stage(restApiId=gateway_id,
                              stageName='prod',
                              patchOperations=[
                                  {'op': 'replace',
                                   'path': r'/*/*/metrics/enabled',
                                   'value': 'true'}
                              ]))


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
    Fetch the resource at the given path on an API Gateway
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
    This resource must exist (I think) for the proxy to apply to any
    request paths besides "/".
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
    try:
        lambda_client.add_permission(
            FunctionName=arn['function_name'],
            StatementId=statement_id,
            Action='lambda:InvokeFunction',
            Principal='apigateway.amazonaws.com',
            # might need SourceArn
            # eg arn:aws:execute-api:us-east-1:aws-acct-id:api-id/*/POST/DynamoDBManager
            # see
            # http://docs.aws.amazon.com/lambda/latest/dg/with-on-demand-https-example-configure-event-source.html
        )
    except botocore.exceptions.ClientError as err:
        if 'ConflictException' in str(err):
            # Expected:
            # botocore.errorfactory.ResourceConflictException: An error
            # occurred (ResourceConflictException) when calling the
            # AddPermission operation: The statement id
            # (nbjigrc4w0-4ocvc4dgok-POST-halloween_chatbot) provided
            # already exists. Please provide a new statement id, or
            # remove the existing statement.
            pass
        else:
            raise
    return integration


def lambda_arn_parts(arn):
    """
    Take an ARN and return its labelled parts
    :arg arn: eg arn:aws:lambda:us-east-1:541056992659:function:my_lamb
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
