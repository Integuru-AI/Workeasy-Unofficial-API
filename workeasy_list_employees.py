from curl_cffi import requests


def run(headers, user_input):
    """List employees from WorkEasy with optional filtering and pagination.

    Matches the official WorkEasy Public API documentation:
    GET /employees — List of employees
    Security scopes: hrp.admin

    Supports all documented query parameters: SearchValue, Archived,
    Status, EmployeeType, FullTime, LegalGender, MaritalStatus, Top, Skip.
    Max 100 records per call (API limit).
    """
    base_url = BASE_URL

    # Build query parameters matching official API spec (PascalCase)
    params = {}

    # SearchValue — Filter by names or employee number
    search_value = user_input.get("search_value")
    if search_value:
        params["SearchValue"] = search_value

    # Archived — Filter by active employees, removed or all
    archived = user_input.get("archived")
    if archived is not None:
        params["Archived"] = str(archived).lower()

    # Status — Filter by employee statuses (multiple selection)
    # 1=Active, 2=Pending, 3=Inactive, 4=Terminated
    status = user_input.get("status")
    if status is not None:
        if isinstance(status, list):
            for s in status:
                params.setdefault("Status", [])
                params["Status"].append(str(s))
        else:
            params["Status"] = str(status)

    # EmployeeType — Filter by employee type (multiple selection)
    # 0=Regular, 1=Intern, 2=Seasonal, 3=Temporary, 4=Contractor, 5=OnCall, 6=VendorEmployee
    employee_type = user_input.get("employee_type")
    if employee_type is not None:
        if isinstance(employee_type, list):
            for et in employee_type:
                params.setdefault("EmployeeType", [])
                params["EmployeeType"].append(str(et))
        else:
            params["EmployeeType"] = str(employee_type)

    # FullTime — Filter by full-time employees, part-time or all
    full_time = user_input.get("full_time")
    if full_time is not None:
        params["FullTime"] = str(full_time).lower()

    # LegalGender — Filter by legal genders (multiple selection)
    # 1=Male, 2=Female, 3=Other
    legal_gender = user_input.get("legal_gender")
    if legal_gender is not None:
        if isinstance(legal_gender, list):
            for lg in legal_gender:
                params.setdefault("LegalGender", [])
                params["LegalGender"].append(str(lg))
        else:
            params["LegalGender"] = str(legal_gender)

    # MaritalStatus — Filter by marital statuses (multiple selection)
    # 0=Single, 1=Married, 2=CommonLaw, 3=DomesticPartnership, 4=Other
    marital_status = user_input.get("marital_status")
    if marital_status is not None:
        if isinstance(marital_status, list):
            for ms in marital_status:
                params.setdefault("MaritalStatus", [])
                params["MaritalStatus"].append(str(ms))
        else:
            params["MaritalStatus"] = str(marital_status)

    # Top — Records per page (max 100 per API docs)
    top = user_input.get("top", 100)
    if top is not None:
        top = min(int(top), 100)
        params["Top"] = str(top)

    # Skip — Records to skip for pagination
    skip = user_input.get("skip")
    if skip is not None:
        params["Skip"] = str(int(skip))

    # Build query string — handle array params properly
    query_parts = []
    for key, value in params.items():
        if isinstance(value, list):
            for v in value:
                query_parts.append(f"{key}={v}")
        else:
            query_parts.append(f"{key}={value}")

    query_string = "&".join(query_parts)

    try:
        response = _call_api(base_url, query_string, headers)
    except Exception as e:
        return {"status_code": 500, "body": {"error": str(e)}}

    # Detect expired session
    if response.status_code == 401:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if response.status_code != 200:
        return {
            "status_code": response.status_code,
            "body": {"error": f"API returned {response.status_code}", "detail": response.text[:500]},
        }

    employees = response.json()

    return {"status_code": 200, "body": employees}


# === PRIVATE ===


def _call_api(base_url, query_string, headers):
    """Make the GET request to the employees endpoint."""
    url = f"{base_url}/employees"
    if query_string:
        url = f"{url}?{query_string}"

    response = requests.get(
        url,
        headers={
            **headers,
            "Accept": "application/json",
        },
        impersonate="chrome131",
        timeout=30,
    )
    return response
