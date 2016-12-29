"""
Lambda handler for wanwu requests
"""


def handler(event, context):
    del context
    return dict(
        statusCode=200,
        body="Hello world",
        headers={
            'Content-Language': 'en',
            'Content-Length': 11,
            'Content-Type': 'text/plain; charset=utf-8',
        },
    )
