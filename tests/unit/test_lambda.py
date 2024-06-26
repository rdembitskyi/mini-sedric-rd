import json
from dataclasses import dataclass

import pytest

from audio_parser.app import Insight, extract_insights, lambda_handler


@pytest.fixture()
def apigw_event():
    """Generates API GW Event"""

    return {
        "body": '{ "test": "body"}',
        "resource": "/{proxy+}",
        "requestContext": {
            "resourceId": "123456",
            "apiId": "1234567890",
            "resourcePath": "/{proxy+}",
            "httpMethod": "POST",
            "requestId": "c6af9ac6-7b61-11e6-9a41-93e8deadbeef",
            "accountId": "123456789012",
            "identity": {
                "apiKey": "",
                "userArn": "",
                "cognitoAuthenticationType": "",
                "caller": "",
                "userAgent": "Custom User Agent String",
                "user": "",
                "cognitoIdentityPoolId": "",
                "cognitoIdentityId": "",
                "cognitoAuthenticationProvider": "",
                "sourceIp": "127.0.0.1",
                "accountId": "",
            },
            "stage": "prod",
        },
        "queryStringParameters": {"foo": "bar"},
        "headers": {
            "Via": "1.1 08f323deadbeefa7af34d5feb414ce27.cloudfront.net (CloudFront)",
            "Accept-Language": "en-US,en;q=0.8",
            "CloudFront-Is-Desktop-Viewer": "true",
            "CloudFront-Is-SmartTV-Viewer": "false",
            "CloudFront-Is-Mobile-Viewer": "false",
            "X-Forwarded-For": "127.0.0.1, 127.0.0.2",
            "CloudFront-Viewer-Country": "US",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Upgrade-Insecure-Requests": "1",
            "X-Forwarded-Port": "443",
            "Host": "1234567890.execute-api.us-east-1.amazonaws.com",
            "X-Forwarded-Proto": "https",
            "X-Amz-Cf-Id": "aaaaaaaaaae3VYQb9jd-nvCd-de396Uhbp027Y2JvkCPNLmGJHqlaA==",
            "CloudFront-Is-Tablet-Viewer": "false",
            "Cache-Control": "max-age=0",
            "User-Agent": "Custom User Agent String",
            "CloudFront-Forwarded-Proto": "https",
            "Accept-Encoding": "gzip, deflate, sdch",
        },
        "pathParameters": {"proxy": "/examplepath"},
        "httpMethod": "POST",
        "stageVariables": {"baz": "qux"},
        "path": "/examplepath",
    }


@dataclass
class Context:
    aws_request_id: str


class TestLambda:
    def test_lambda_handler_no_values(self, apigw_event):
        context = Context(aws_request_id="123456")
        ret = lambda_handler(apigw_event, context)
        data = json.loads(ret["body"])

        assert ret["statusCode"] == 400
        assert "message" in ret["body"]
        assert data["message"] == "You need to provide valid trackers and url"


@pytest.fixture
def sample_transcript():
    return "This is a test. Thank you for your contribution."


@pytest.fixture
def sample_trackers():
    return ["test", "thank you"]


class TestExtractInsights:
    def test_extract_insights_basic(self, sample_transcript, sample_trackers):
        insights = extract_insights(sample_transcript, sample_trackers)
        assert len(insights) == 2
        assert insights[0] == Insight(
            sentence_index=0,
            start_word_index=3,
            end_word_index=3,
            tracker_value="test",
            transcribe_value="This is a test",
        )
        assert insights[1] == Insight(
            sentence_index=1,
            start_word_index=0,
            end_word_index=1,
            tracker_value="thank you",
            transcribe_value="Thank you for your contribution",
        )

    def test_extract_insights_case_insensitivity(self):
        transcript = "Hello world. HELLO WORLD."
        trackers = ["hello"]
        insights = extract_insights(transcript, trackers)
        assert len(insights) == 2
        assert all(insight["tracker_value"] == "hello" for insight in insights)
        assert all(insight["transcribe_value"].lower() == "hello world" for insight in insights)

    def test_extract_insights_no_match(self):
        transcript = "Completely unrelated text."
        trackers = ["nonexistent"]
        insights = extract_insights(transcript, trackers)
        assert len(insights) == 0

    def test_extract_insights_empty_transcript(self):
        transcript = ""
        trackers = ["anything"]
        insights = extract_insights(transcript, trackers)
        assert len(insights) == 0

    def test_extract_insights_empty_trackers(self):
        transcript = "Some text with potential content."
        trackers = []
        insights = extract_insights(transcript, trackers)
        assert len(insights) == 0
