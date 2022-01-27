import logging
import os
import re
import json
import dpath.util

import boto3
import requests
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler()]
)


class ImproperlyConfigured(Exception):
    def __init__(self, detail: str) -> None:
        Exception.__init__(self)

        self.detail = detail

    def __str__(self) -> str:
        return self.detail


COVERAGE_FILE = os.getenv("INPUT_COVERAGE_FILE", "")
BADGE_NAME = os.getenv("INPUT_BADGE_NAME", "")
UPLOAD_COVERAGE_FILE = os.getenv("INPUT_UPLOAD_COVERAGE_FILE", "False").lower() in ("true", "1", "t", "y", "yes")
BUCKET_NAME = os.getenv("INPUT_BUCKET_NAME", "")
ACCESS_KEY = os.getenv("INPUT_AWS_ACCESS_KEY", "")
SECRET_KEY = os.getenv("INPUT_AWS_SECRET_KEY", "")
COVERAGE_PERCENTAGE_REGEX = os.getenv("INPUT_COVERAGE_PERCENTAGE_REGEX", "")
COVERAGE_PERCENTAGE_JSON_PATH = os.getenv("INPUT_COVERAGE_PERCENTAGE_JSON_PATH", "").replace(".", "/")

BRIGHT_GREEN_PERCENTAGE_THRESHOLD = 90
GREEN_PERCENTAGE_THRESHOLD = 80
YELLOW_GREEN_PERCENTAGE_THRESHOLD = 70
YELLOW_PERCENTAGE_THRESHOLD = 60
ORANGE_PERCENTAGE_THRESHOLD = 50


def get_coverage() -> float:
    """
    Get coverage percentage from parsed coverage file.

    :return: The extracted coverage
    :rtype: float
    """
    logging.info(
        f"Extracting coverage from {COVERAGE_FILE} on "
        f"regex/json path {COVERAGE_PERCENTAGE_REGEX or COVERAGE_PERCENTAGE_JSON_PATH}"
    )
    if COVERAGE_PERCENTAGE_JSON_PATH:
        with open(COVERAGE_FILE) as f:
            coverage = round(
                float(
                    dpath.util.get(
                        json.load(f),
                        COVERAGE_PERCENTAGE_JSON_PATH
                    )
                ), 2
            )
    else:
        with open(COVERAGE_FILE) as f:
            coverage = round(
                float(
                    re.findall(COVERAGE_PERCENTAGE_REGEX, f.read())[0].replace(
                        "%",
                        ""
                    )
                ), 2
            )
    return coverage


def get_badge_color(coverage: float) -> str:
    """
    Get badge color based on coverage value.

    :param float coverage: The coverage percentage
    :return: The color of the badge
    :rtype: str
    """
    if coverage < ORANGE_PERCENTAGE_THRESHOLD:
        logging.info(f"{coverage} < {ORANGE_PERCENTAGE_THRESHOLD}")
        return "red"
    elif ORANGE_PERCENTAGE_THRESHOLD <= coverage < YELLOW_PERCENTAGE_THRESHOLD:
        logging.info(f"{ORANGE_PERCENTAGE_THRESHOLD} <= {coverage} < {YELLOW_PERCENTAGE_THRESHOLD}")
        return "orange"
    elif YELLOW_PERCENTAGE_THRESHOLD <= coverage < YELLOW_GREEN_PERCENTAGE_THRESHOLD:
        logging.info(f"{YELLOW_PERCENTAGE_THRESHOLD} <= {coverage} < {YELLOW_GREEN_PERCENTAGE_THRESHOLD}")
        return "yellow"
    elif YELLOW_GREEN_PERCENTAGE_THRESHOLD <= coverage < GREEN_PERCENTAGE_THRESHOLD:
        logging.info(f"{YELLOW_GREEN_PERCENTAGE_THRESHOLD} <= {coverage} < {GREEN_PERCENTAGE_THRESHOLD}")
        return "yellowgreen"
    elif GREEN_PERCENTAGE_THRESHOLD <= coverage < BRIGHT_GREEN_PERCENTAGE_THRESHOLD:
        logging.info(f"{GREEN_PERCENTAGE_THRESHOLD} <= {coverage} < {BRIGHT_GREEN_PERCENTAGE_THRESHOLD}")
        return "green"
    else:
        logging.info(f"{coverage} >= {BRIGHT_GREEN_PERCENTAGE_THRESHOLD}")
        return "brightgreen"


def download_badge(coverage: float, color: str, download_file_path: str) -> str:
    """
    Download badge file from shields.io.

    :param int coverage: The coverage percentage
    :param str color: Color of the badge
    :param str download_file_path: Path to download the badge to
    :return: The path where the badge has been downloaded to.
    :rtype: str
    """
    logging.info(
        f"{color.capitalize()} badge with {coverage}% to be "
        f"downloaded on {download_file_path}"
    )
    response = requests.get(
        url=f"https://img.shields.io/badge/coverage-{coverage}%25-{color}")
    with open(download_file_path, "wb") as f:
        f.write(response.content)
    return download_file_path


def upload_file(
    file_name: str,
    bucket: str,
    content_type: str = "text/plain",
    object_name: str = ""
) -> bool:
    """
    Upload a file to an S3 bucket.

    :param str file_name: File to upload
    :param str bucket: Bucket to upload to
    :param str content_type: Content type of file to be uploaded
    :param str object_name: S3 object name. If not specified then
        file_name is used
    :return: True if file was uploaded, else False
    :rtype: bool
    """
    logging.info(
        f"Upload {file_name} to {bucket} "
        f"as {object_name or file_name}"
    )
    # If S3 object_name was not specified, use file_name
    if not object_name:
        object_name = file_name

    # Upload the file
    s3_client = boto3.client(
        service_name="s3",
        region_name="us-east-1",
        aws_access_key_id=ACCESS_KEY,
        aws_secret_access_key=SECRET_KEY,
    )
    try:
        s3_client.upload_file(
            file_name,
            bucket,
            object_name,
            ExtraArgs={
                "ContentType": content_type,
                "CacheControl": "no-cache",
            }
        )
    except ClientError as e:
        logging.error(e)
        return False
    return True


def upload_coverage_file(
    coverage_percentage: float,
    badge_name: str,
    bucket: str
) -> bool:
    """
    Upload a file with the coverage percentage to an S3 bucket.

    :param int coverage_percentage: Current coverage  percentage
    :param str badge_name: Name of the badge file
    :param str bucket: Bucket to upload to
    :return: True if file was uploaded, else False
    :rtype: bool
    """
    coverage_file = os.path.splitext(badge_name)[0] + ".txt"
    temp_coverage_file = "coverage-percentage.txt"
    logging.info(
        f"Writing coverage percentage to file {coverage_file} to {bucket}."
    )
    with open(temp_coverage_file, "w") as f:
        logging.info(f"Coverage: {coverage_percentage}")
        f.write(str(coverage_percentage))

    # Upload the file
    return upload_file(
        file_name=temp_coverage_file,
        bucket=bucket,
        content_type="text/plain",
        object_name=coverage_file
    )


def main() -> None:
    """
    Parse coverage file, create appropriate badge and upload to S3.
    """
    if not any([COVERAGE_PERCENTAGE_REGEX, COVERAGE_PERCENTAGE_JSON_PATH]):
        raise ImproperlyConfigured(
            detail="At least one of the arguments `coverage_percentage_regex` "
                   "or `coverage_percentage_json_path` must be set in order "
                   "for the action to run."
        )
    coverage = get_coverage()
    color = get_badge_color(coverage)
    temp_badge = "badge.svg"
    download_badge(coverage, color, temp_badge)
    upload_file(temp_badge, BUCKET_NAME, "image/svg+xml", BADGE_NAME)
    if UPLOAD_COVERAGE_FILE:
        upload_coverage_file(
            coverage,
            BADGE_NAME,
            BUCKET_NAME,
        )


if __name__ == "__main__":
    main()
