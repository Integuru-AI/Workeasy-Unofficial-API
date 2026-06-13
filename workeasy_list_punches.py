from curl_cffi import requests


def run(headers, user_input):
    """Get raw punches

    Official API: GET /punches
    Security scopes: tap.admin"""
    base_url = BASE_URL

    # Build query parameters
    params = {}

    # EmployeeId — Filter by employee
    employee_id = user_input.get("employee_id")
    if employee_id is not None:
        params["EmployeeId"] = str(int(employee_id))

    # ValueStartDate — Filter by "Value" field, it must be equals or greater than ValueStartDate
    value_start_date = user_input.get("value_start_date")
    if value_start_date is not None:
        params["ValueStartDate"] = str(value_start_date)

    # ValueEndDate — Filter by "Value" field, it must be equals or less than ValueEndDate
    value_end_date = user_input.get("value_end_date")
    if value_end_date is not None:
        params["ValueEndDate"] = str(value_end_date)

    # OriginalStartDate — Filter by "OriginalValue" field, it must be equals or greater than OriginalStartDate
    original_start_date = user_input.get("original_start_date")
    if original_start_date is not None:
        params["OriginalStartDate"] = str(original_start_date)

    # OriginalEndDate — Filter by "OriginalValue" field, it must be equals or less than OriginalEndDate
    original_end_date = user_input.get("original_end_date")
    if original_end_date is not None:
        params["OriginalEndDate"] = str(original_end_date)

    # Status — Filter by "Status" field, it must be equals to the filter. Possibles values are the Life cycle status values of punch (0-Created, 1-Frozen, 2-Edited, 3-Archived, 4-Requested to move)
    status = user_input.get("status")
    if status is not None:
        params["Status"] = str(int(status))

    # LastId — Filter by "Id" field, it must be greater than LastId
    last_id = user_input.get("last_id")
    if last_id is not None:
        params["LastId"] = str(int(last_id))

    # OriginId — Filter by "OriginId" field, it must equal than the filter
    origin_id = user_input.get("origin_id")
    if origin_id:
        params["OriginId"] = str(origin_id)

    # Origin — Filter by "Origin" field, it must equal than the filter 0-Employee, 1-Manager, 2-Web, 3-Mobile, 4-Timeclock, 5-System, 6-TimeClockKiosk, 7-Group clock, 8-Public API
    origin = user_input.get("origin")
    if origin is not None:
        params["Origin"] = str(int(origin))

    # LastModifiedStartDate — Filter by "LastModified" field, it must be equals or greater than LastModifiedStartDate
    last_modified_start_date = user_input.get("last_modified_start_date")
    if last_modified_start_date is not None:
        params["LastModifiedStartDate"] = str(last_modified_start_date)

    # LastModifiedEndDate — Filter by "LastModified" field, it must be equals or less than LastModifiedEndDate
    last_modified_end_date = user_input.get("last_modified_end_date")
    if last_modified_end_date is not None:
        params["LastModifiedEndDate"] = str(last_modified_end_date)

    # PayPeriodId — Filter by "PayPeriodId" field, it must equal than the filter
    pay_period_id = user_input.get("pay_period_id")
    if pay_period_id is not None:
        params["PayPeriodId"] = str(int(pay_period_id))

    # EmployeeNumber — Filter by "EmployeeNumber" field, it must equal than the filter
    employee_number = user_input.get("employee_number")
    if employee_number:
        params["EmployeeNumber"] = str(employee_number)

    top = user_input.get("top", 100)
    if top is not None:
        params["Top"] = str(min(int(top), 100))

    skip = user_input.get("skip")
    if skip is not None:
        params["Skip"] = str(int(skip))

    url = f"{base_url}/punches"

    # Build query string
    query_parts = []
    for key, value in params.items():
        if isinstance(value, list):
            for v in value:
                query_parts.append(f"{key}={v}")
        else:
            query_parts.append(f"{key}={value}")
    if query_parts:
        url += "?" + "&".join(query_parts)

    response = requests.get(
        url,
        headers={**headers, "Accept": "application/json"},
        impersonate="chrome131",
        timeout=30,
    )

    if response.status_code == 401:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {
            "status_code": response.status_code,
            "body": {"error": f"API returned {response.status_code}", "detail": response.text[:500]},
        }

    try:
        data = response.json()
    except Exception:
        return {"status_code": 200, "body": response.text[:2000]}

    return {"status_code": 200, "body": data}
