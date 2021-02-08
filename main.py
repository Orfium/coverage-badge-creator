import logging
import os
import re

import boto3
import requests
from botocore.exceptions import ClientError

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler()])

COVERAGE_FILE = os.getenv("INPUT_COVERAGE_FILE", "coverage.txt")
S3_PATH = os.getenv("INPUT_S3_PATH")
BADGE_NAME = os.getenv("INPUT_BADGE_NAME")
BUCKET_NAME = os.getenv("INPUT_BUCKET_NAME")
ACCESS_KEY = os.getenv("INPUT_AWS_ACCESS_KEY")
SECRET_KEY = os.getenv("INPUT_AWS_SECRET_KEY")
COVERAGE_PERCENTAGE_REGEX = os.getenv("INPUT_COVERAGE_PERCENTAGE_REGEX")

GREEN_PERCENTAGE_THRESHOLD = 80
ORANGE_PERCENTAGE_THRESHOLD = 50


def compute_coverage():
    """
    Compute coverage percentage by parsing coverage file with a regex.

    :return: The computed coverage
    :rtype: int
    """
    logging.info(
        f"Computing coverage from {COVERAGE_FILE} using "
        f"REGEX {COVERAGE_PERCENTAGE_REGEX}")
    with open(COVERAGE_FILE) as f:
        return int(
            float(
                re.findall(COVERAGE_PERCENTAGE_REGEX, f.read())[0].replace(
                    "%",
                    "")
            )
        )


def get_badge_color(coverage):
    """
    Get badge color depending on coverage value.

    :param int coverage: The coverage percentage
    :return: The color of the badge
    :rtype: str
    """
    if coverage < ORANGE_PERCENTAGE_THRESHOLD:
        logging.info(f"{coverage} < {ORANGE_PERCENTAGE_THRESHOLD}")
        return "red"
    elif coverage >= GREEN_PERCENTAGE_THRESHOLD:
        logging.info(f"{coverage} >= {GREEN_PERCENTAGE_THRESHOLD}")
        return "green"
    else:
        logging.info(
            f"{coverage} < {GREEN_PERCENTAGE_THRESHOLD} "
            f"and > {ORANGE_PERCENTAGE_THRESHOLD}"
        )
        return "orange"


def download_badge(coverage, color, download_file_path):
    """
    Download badge file from shields.io.

    :param int coverage: The coverage percentage
    :param str color: Color of the badge
    :param str download_file_path: Path to download the badge to
    :return: The path where the badge has been downloaded to.
    :rtype: str
    """
    logging.info(
        f"{color} Badge with {coverage}% to be "
        f"downloaded on {download_file_path}"
    )
    response = requests.get(
        url=f"https://img.shields.io/badge/coverage-{coverage}%25-{color}")
    with open(download_file_path, 'wb') as f:
        f.write(response.content)
    return download_file_path


def upload_file(file_name, bucket, object_name=None):
    """
    Upload a file to an S3 bucket.

    :param str file_name: File to upload
    :param str bucket: Bucket to upload to
    :param str|None object_name: S3 object name. If not specified then
        file_name is used
    :return: True if file was uploaded, else False
    :rtype: bool
    """
    logging.info(
        f"Upload {file_name} to {bucket} "
        f"as {object_name or file_name}"
    )
    # If S3 object_name was not specified, use file_name
    if object_name is None:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client('s3',
                             region_name="us-east-1",
                             aws_access_key_id=ACCESS_KEY,
                             aws_secret_access_key=SECRET_KEY)
    try:
        s3_client.upload_file(file_name, bucket, object_name,
                              ExtraArgs={'ContentType': 'image/svg+xml'})
    except ClientError as e:
        logging.error(e)
        return False
    return True


def main():
    """
    Parse coverage file, create appropriate badge and upload to S3.
    """
    coverage = compute_coverage()
    color = get_badge_color(coverage)
    temp_badge = 'badge.svg'
    download_badge(coverage, color, temp_badge)
    upload_file(temp_badge, BUCKET_NAME, BADGE_NAME)


if __name__ == "__main__":
    main()
