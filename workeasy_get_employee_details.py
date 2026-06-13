from curl_cffi import requests


def run(headers, user_input):
    """Fetch employee details including personal info, employment data, and group assignments."""
    employee_id = user_input.get("employee_id")
    if not employee_id:
        return {"status_code": 400, "body": {"error": "employee_id is required"}}

    STATUS_MAP = {1: "Active", 2: "Pending", 3: "Inactive", 4: "Terminated"}
    EMPLOYEE_TYPE_MAP = {
        0: "Regular", 1: "Intern", 2: "Seasonal", 3: "Temporary",
        4: "Contractor", 5: "On Call", 6: "Vendor Employee",
    }
    IS_FULL_TIME_MAP = {0: "Part Time", 1: "Full Time"}
    PAY_TYPE_MAP = {0: "Salary", 1: "Hourly"}
    FLSA_CODE_MAP = {0: "Exempt", 1: "NonExempt"}
    RELATIONSHIP_MAP = {
        1: "Mother", 2: "Father", 3: "Son", 4: "Daughter", 5: "Uncle",
        6: "Aunt", 7: "Spouse", 8: "Grandparent", 9: "Cousin", 10: "Sibling",
        11: "Friend", 12: "Other", 13: "Wife", 14: "Husband", 15: "Brother",
        16: "Sister", 17: "Guardian", 18: "Grandfather", 19: "Grandmother",
        20: "Ex-Spouse", 21: "Ex-Husband", 22: "Ex-Wife", 23: "Relative",
        24: "Neighbor", 25: "Doctor",
    }

    try:
        details, employment, groups_raw = _fetch_employee_data(headers, employee_id)
    except AuthError:
        return {"status_code": 401, "body": {"error": "Session expired"}}
    except NotFoundError:
        return {"status_code": 404, "body": {"error": f"Employee {employee_id} not found"}}
    except ApiError as e:
        return {"status_code": e.status_code, "body": {"error": str(e)}}

    # Parse personal details
    def format_date(val):
        if not val:
            return None
        return val[:10] if "T" in val else val

    primary_address = details.get("PrimaryAddress") or {}
    emergency_contact_raw = details.get("FirstContactInformation") or {}
    secondary_contact_raw = details.get("SecondContactInformation") or {}

    def build_contact(raw):
        if not raw:
            return None
        rel_val = raw.get("RelationShip")
        return {
            "name": raw.get("Name"),
            "phone": raw.get("PhoneNumber"),
            "email": raw.get("Email"),
            "relationship": RELATIONSHIP_MAP.get(rel_val, str(rel_val) if rel_val is not None else None),
            "address": raw.get("Address"),
        }

    personal = {
        "employee_number": details.get("EmployeeNumber"),
        "first_name": details.get("FirstName"),
        "middle_name": details.get("MiddleName"),
        "last_name": details.get("LastName"),
        "preferred_name": details.get("PreferredName"),
        "birth_date": format_date(details.get("BirthDate")),
        "gender": details.get("Gender"),
        "marital_status": details.get("MaritalStatus"),
        "ssn": details.get("SSN"),
        "personal_phone": details.get("PersonalPhoneNumber"),
        "work_phone": details.get("WorkPhoneNumber"),
        "work_phone_ext": details.get("WorkPhoneNumberExt"),
        "home_phone": details.get("HomePhoneNumber"),
        "email": details.get("Email"),
        "personal_email": details.get("PersonalEmail"),
        "linkedin": details.get("LinkedIn"),
        "twitter": details.get("Twitter"),
        "facebook": details.get("Facebook"),
        "primary_address": {
            "address1": primary_address.get("Address1"),
            "address2": primary_address.get("Address2"),
            "city": primary_address.get("City"),
            "state": primary_address.get("State"),
            "zip_code": primary_address.get("ZipCode"),
            "country": primary_address.get("Country"),
        } if primary_address.get("Address1") else None,
        "emergency_contact": build_contact(emergency_contact_raw),
        "secondary_contact": build_contact(secondary_contact_raw),
    }

    # Parse employment data
    emp_status_list = employment.get("EmployeeStatus", [])
    emp_position_list = employment.get("EmployeePosition", [])
    emp_compensation_list = employment.get("EmployeeCompensation", [])

    # Get most recent (current) entries
    current_status = emp_status_list[0] if emp_status_list else {}
    current_position = emp_position_list[0] if emp_position_list else {}
    current_compensation = emp_compensation_list[0] if emp_compensation_list else {}

    status_val = current_status.get("Status")
    emp_type_val = current_position.get("EmployeeType")
    is_ft_val = current_position.get("IsFullTime")
    pay_type_val = current_compensation.get("PayType")
    flsa_val = current_compensation.get("FLSACode")

    pay_schedule = current_compensation.get("PaySchedule") or {}

    employment_data = {
        "status": STATUS_MAP.get(status_val, str(status_val) if status_val is not None else None),
        "hired_date": format_date(current_status.get("HiredDate")),
        "termination_date": format_date(current_status.get("TerminationDate")),
        "termination_note": current_status.get("TerminationNote"),
        "eligible_to_rehire": current_status.get("EligibleToRehire"),
        "employee_type": EMPLOYEE_TYPE_MAP.get(emp_type_val, str(emp_type_val) if emp_type_val is not None else None),
        "is_full_time": IS_FULL_TIME_MAP.get(is_ft_val, str(is_ft_val) if is_ft_val is not None else None),
        "job_title": (current_position.get("JobTitle") or {}).get("Name"),
        "pay_rate": current_compensation.get("PayRate"),
        "hourly_rate": current_compensation.get("HourlyRate"),
        "pay_type": PAY_TYPE_MAP.get(pay_type_val, str(pay_type_val) if pay_type_val is not None else None),
        "pay_schedule": pay_schedule.get("Name"),
        "flsa_code": FLSA_CODE_MAP.get(flsa_val, str(flsa_val) if flsa_val is not None else None),
    }

    # Parse group assignments
    groups = []
    for node_entry in groups_raw:
        node = node_entry.get("Node") or {}
        node_def = node.get("NodeDef") or {}
        groups.append({
            "group_type": node_def.get("Name"),
            "name": node.get("Name"),
        })

    return {
        "status_code": 200,
        "body": {
            "employee_id": employee_id,
            "personal": personal,
            "employment": employment_data,
            "groups": groups,
        },
    }


# === PRIVATE ===

class AuthError(Exception):
    pass

class NotFoundError(Exception):
    pass

class ApiError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        super().__init__(message)


def _fetch_employee_data(headers, employee_id):
    """Fetch employee details, employment, and group data from the API."""
    base_url = BASE_URL

    req_headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "authorization": headers.get("Authorization", ""),
        "cache-control": "no-cache",
        "origin": "https://app.workeasysoftware.com",
        "pragma": "no-cache",
        "referer": "https://app.workeasysoftware.com/",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
    }
    if headers.get("Cookie"):
        req_headers["cookie"] = headers["Cookie"]

    # 1. Fetch personal details
    details_resp = requests.get(
        f"{base_url}/employee-details/{employee_id}",
        headers=req_headers,
        impersonate="chrome110",
        timeout=30,
    )

    if details_resp.status_code == 401 or "/login" in details_resp.url:
        raise AuthError("Session expired")
    if details_resp.status_code in (404, 500):
        raise NotFoundError(f"Employee {employee_id} not found")
    if details_resp.status_code != 200:
        raise ApiError(details_resp.status_code, details_resp.text)

    details = details_resp.json()

    # 2. Fetch employment data
    employment_resp = requests.get(
        f"{base_url}/employment/{employee_id}",
        headers=req_headers,
        impersonate="chrome110",
        timeout=30,
    )
    employment = employment_resp.json() if employment_resp.status_code == 200 else {}

    # 3. Fetch group assignments
    groups_resp = requests.get(
        f"{base_url}/employees-in-nodes/now/object-id/{employee_id}",
        headers=req_headers,
        impersonate="chrome110",
        timeout=30,
    )
    groups_raw = groups_resp.json() if groups_resp.status_code == 200 else []

    return details, employment, groups_raw
