import json
import re
import time
import urllib.request
from typing import TypedDict

import boto3  # type: ignore
from validators import is_mp3_url, validate_event_body, validate_trackers  # type: ignore


class Insight(TypedDict):
    sentence_index: int
    start_word_index: int
    end_word_index: int
    tracker_value: str
    transcribe_value: str


class LambdaResponse(TypedDict):
    statusCode: int
    body: str


def lambda_handler(event, context) -> LambdaResponse:
    request_id = context.aws_request_id

    print(f"Started request {request_id}")

    try:
        event_body = validate_event_body(event_body=event.get("body", "{}"))
    except ValueError as e:
        return create_error_response(status_code=400, message=str(e))

    interaction_url = event_body.get("interaction_url")
    trackers = validate_trackers(event_body.get("trackers"))

    if not (interaction_url and trackers):
        return create_error_response(status_code=400, message="You need to provide valid trackers and url")

    if not is_mp3_url(interaction_url):
        return create_error_response(status_code=400, message="URL provided is not an mp3 file")

    job_name = f"transcribe-{request_id}"

    try:
        transcribed_text = transcribe_mp3_file_to_text(job_name=job_name, interaction_url=interaction_url)
    except (TimeoutError, ValueError) as e:
        return create_error_response(status_code=500, message=str(e))

    insights = extract_insights(text=transcribed_text, trackers=trackers)

    print(f"Ended request {request_id} with {len(insights)} insights.")

    response: LambdaResponse = {"statusCode": 200, "body": json.dumps({"insights": insights})}
    return response


def extract_insights(text: str, trackers: list[str]) -> list[Insight]:
    insights = []
    # Split transcript into sentences to better handle sentence indexing.
    sentences = text.split(".")
    for sentence_index, sentence in enumerate(sentences):
        for tracker in trackers:
            sentence = sentence.strip()
            # Use re.escape to safely use trackers as literals in regex
            pattern = r"\b" + re.escape(tracker) + r"\b"
            # re.IGNORECASE for case-insensitive matching
            matches = re.finditer(pattern, sentence, re.IGNORECASE)
            for match in matches:
                insight = Insight(
                    sentence_index=sentence_index,
                    start_word_index=len(re.findall(r"\w+", sentence[: match.start()])),
                    end_word_index=len(re.findall(r"\w+", sentence[: match.end()])) - 1,
                    tracker_value=tracker,
                    transcribe_value=sentence,
                )
                insights.append(insight)
    return insights


def transcribe_mp3_file_to_text(job_name: str, interaction_url: str) -> str:
    transcribe_client = boto3.client("transcribe")

    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name, Media={"MediaFileUri": interaction_url}, MediaFormat="mp3", LanguageCode="en-US"
    )
    max_retries = 50
    max_exponent_time = 10  # in seconds
    retries_count = 0
    url_to_transcribed_text = None

    while retries_count < max_retries:
        retries_count += 1
        job = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        job_status = job["TranscriptionJob"]["TranscriptionJobStatus"]

        # using print instead of logging for simplicity
        print(f"Attempt {retries_count}: Job {job_name} is {job_status}.")

        if job_status in ["COMPLETED", "FAILED"]:
            if job_status == "COMPLETED":
                url_to_transcribed_text = job["TranscriptionJob"]["Transcript"]["TranscriptFileUri"]
                print(f"Download the transcript from: {url_to_transcribed_text}")
            else:
                print(f"Transcription job failed for {job_name}")
                raise ValueError("Transcription job failed")
            break

        time.sleep(2 ** min(retries_count, max_exponent_time))  # Exponential backoff

    if url_to_transcribed_text:
        with urllib.request.urlopen(url_to_transcribed_text) as response:
            data = response.read().decode()
            try:
                return json.loads(data)["results"]["transcripts"][0]["transcript"]
            except KeyError as e:
                print(f"Error parsing transcript data: {e}")
                raise ValueError("Could not parse transcript data")
    else:
        raise TimeoutError("Transcription job did not complete within the time limit")


def create_error_response(status_code: int, message: str) -> LambdaResponse:
    return {"statusCode": status_code, "body": json.dumps({"message": message})}
