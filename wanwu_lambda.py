"""
Lambda handler for wanwu requests
"""
import json


def handler(event, context):
    """
    The entry point for the lambda
    :arg dict event: {
        "isBase64Encoded": False,
        "path": "/",
        "body": None,
        "resource": "/",
        "requestContext": {
            "stage": "prod",
            "identity": {
                "accountId": None,
                "sourceIp": "66.234.34.100",
                "cognitoAuthenticationProvider": None,
                "cognitoIdentityId": None,
                "apiKey": None,
                "userArn": None,
                "cognitoAuthenticationType": None,
                "accessKey": None,
                "caller": None,
                "userAgent": "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/55.0.2883.87 Safari/537.36",
                "user": None,
                "cognitoIdentityPoolId": None
            },
            "accountId": "541056992659",
            "requestId": "40fc7e97-d229-11e6-8949-99c4d5e523c8",
            "httpMethod": "GET",
            "resourcePath": "/",
            "apiId": "1han4u97l0",
            "resourceId": "z8npftrr5d"
        },
        "queryStringParameters": None,
        "httpMethod": "GET",
        "pathParameters": None,
        "headers": {
            "Accept-Encoding": "gzip, deflate, sdch, br",
            "CloudFront-Forwarded-Proto": "https",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/55.0.2883.87 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/webp,*/*;q=0.8",
            "CloudFront-Viewer-Country": "US",
            "X-Forwarded-For": "66.234.34.100, 204.246.180.48",
            "CloudFront-Is-Mobile-Viewer": "false",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-Tablet-Viewer": "false",
            "Accept-Language": "en-US,en;q=0.8",
            "Via": "1.1 f348970492a18bf5c630c5acc86c1ee3.cloudfront.net "
                "(CloudFront)",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-Port": "443",
            "Host": "1han4u97l0.execute-api.us-east-1.amazonaws.com",
            "X-Forwarded-Proto": "https",
            "Referer": "https://console.aws.amazon.com/apigateway/home"
                "?region=us-east-1",
            "Cache-Control": "max-age=0",
            "X-Amz-Cf-Id": "TqUFzq7aH3maNpH3Ih_98Hr8j4tz"
                "7HjZrYf8BL7N2K1yNbtBkpjPBA=="
        },
        "stageVariables": None

    }
    :arg LambdaContext context: see
        http://docs.aws.amazon.com/lambda/latest/dg/python-context-object.html
    """
    body = json.dumps(dict(
        event=event,
        context=context,
    ), default=str)
    return dict(
        statusCode=200,
        body=body,
        headers={
            'Content-Language': 'en',
            'Content-Length': len(body),
            'Content-Type': 'application/json; charset=utf-8',
        },
    )
