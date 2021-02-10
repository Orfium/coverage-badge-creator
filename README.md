# coverage-badge-creator

Create a coverage badge without third parties as proposed in https://itnext.io/github-actions-code-coverage-without-third-parties-f1299747064d. 

## Description

This actions performs the following tasks sequentially:

* reads a file containing the coverage information 
* finds the coverage percentage using a specified regex
* calls shields.io API in order to download a proper badge based on the parsed coverage.
* uploads the badge in an AWS S3 bucket, 

## Usage

An example usage of the action is the following:

## Sample Workflow

```yaml
name: CI

on:
  push:
    branches:

jobs:
    unittest:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code Repository
        uses: actions/checkout@v2
      - name: Build the Stack
        run:  docker-compose -f local.yml build
      - name: Make DB Migrations
        run:  docker-compose -f local.yml run --rm django python manage.py migrate
      - name: Run the Stack
        run:  docker-compose -f local.yml up -d
      - name: Run Django Tests
        run: docker-compose -f local.yml exec -T django coverage run --rcfile=.pre-commit/setup.cfg -m pytest --disable-pytest-warnings;
      - name: Print Coverage
        run: docker-compose -f local.yml exec -T django coverage report
      - name: Print Coverage to txt file
        run: docker-compose -f local.yml exec -T django coverage report > coverage.txt
      - name: Tear down the Stack
        run: docker-compose -f local.yml down
      - name: Update Coverage badge
        uses: Orfium/coverage-badge-creator@master
        with:
          coverage_file: coverage.txt
          badge_name: "code-cov-prod.svg"
          bucket_name: "orfium-badges-bucket"
          aws_access_key: ${{ secrets.BADGES_AWS_ACCESS_KEY_ID }}
          aws_secret_key: ${{ secrets.BADGES_AWS_SECRET_ACCESS_KEY }}
          coverage_percentage_regex: ${{ secrets.COVERAGE_PERCENTAGE_REGEX }}
        if: github.ref == 'refs/heads/develop'
      
```

## Input Variables

| Name                        | Description                                  | Default |
| --------------------------- | ---------------------------------------------| ------- |
| `coverage_file`             | Path to coverage file                        | -       |
| `badge_name`                | Name of the badge file                       | -       |
| `bucket_name`               | Name of the bucket to upload the badge to    | -       |
| `aws_access_key`            | AWS Access Key                               | -       |
| `aws_secret_key`            | AWS Secret Key                               | -       |
| `coverage_percentage_regex` | Regex to use in order to retrieve coverage   | -       |

