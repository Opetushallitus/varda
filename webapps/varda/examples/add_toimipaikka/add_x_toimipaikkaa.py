#!/usr/bin/env python3

"""
Varda, example of REST API usage

- Give an X "toimipaikkaa" as an input, and insert that data into the centralized-DB
- Requires a valid API-key (taken from environment variable: VARDA_API_KEY)
- Requires a correct server-hostname (taken from environment variable: VARDA_HOST)
- Requires following python-packages to be installed:
  $ pip install requests

Returns:

- Number of successful POST-requests to DB
- Possible errors and error codes in case of problems
"""

import os
import sys
import json
import requests


def usage():
    print("Usage: add_x_toimipaikkaa.py -I|--input <datafile>, where <datafile> = valid JSON-file containing of X toimipaikkaa")


def get_result_dictionary(status_ok, result):
    if status_ok:
        return {"STATUS": "OK", "RESULT": result}
    else:
        return {"STATUS": "NOK", "RESULT": result}


def parse_jsonfile(datafile):
    try:
        with open(datafile) as f:
            return get_result_dictionary(True, json.load(f))
    except (FileNotFoundError, ValueError) as e:
        return get_result_dictionary(False, ("invalid json: %s" % e))


def post_data(toimipaikka, hostname, api_key):
    headers = {'Accept': 'application/json', 'Authorization': 'Token ' + api_key}
    data = toimipaikka
    base_url = hostname
    url = base_url + '/api/v1/toimipaikat/'

    try:
        response = requests.post(url, json=data, headers=headers)
    except requests.exceptions.RequestException as e:
        print("Error:", e)
        sys.exit(7)

    return {"status_code": response.status_code, "text": response.text}


def do_requests_and_print_results(input_json, hostname, api_key):
    successful_tries = 0
    error_situations = []
    for item in input_json:
        # Check that "nimi" is found from the input-json. Without checking,
        # and if missing, the following error-message fails.
        if "nimi" in item:
            result = post_data(item, hostname, api_key)
        else:
            print("Error: some of the mandatory fields are missing from the input. Please check JSON-schema.")
            sys.exit(8)

        if result["status_code"] == 403:
            print("Error: request forbidden. " + result["text"])
            sys.exit(9)
        elif result["status_code"] == 201:
            successful_tries += 1
        else:
            error_situations.append({"toimipaikka": item["nimi"],
                                     "status_code": result["status_code"],
                                     "text": result["text"]}
                                    )

    print("Successful POST-requests: " + str(successful_tries) + " / " + str(len(input_json)))

    if error_situations:
        print("\nErrors:")
        print(error_situations)


def main(argv):
    if len(sys.argv) < 3:
        usage()
        sys.exit(2)

    if sys.argv[1] != "-I" and sys.argv[1] != "--input":
        usage()
        sys.exit(3)

    try:
        hostname = os.environ['VARDA_HOST']
    except KeyError:
        print("Error: VARDA_HOST missing")
        sys.exit(4)

    try:
        api_key = os.environ['VARDA_API_KEY']
    except KeyError:
        print("Error: VARDA_API_KEY missing")
        sys.exit(5)

    parsed_json = parse_jsonfile(sys.argv[2])
    if parsed_json["STATUS"] == "NOK":
        print(parsed_json["RESULT"])
        sys.exit(6)

    # Input-file is parsed, and valid json
    do_requests_and_print_results(parsed_json["RESULT"], hostname, api_key)


if __name__ == "__main__":
    main(sys.argv[1:])
