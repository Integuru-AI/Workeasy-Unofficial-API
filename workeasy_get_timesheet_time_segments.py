from curl_cffi import requests
import json


def run(headers, user_input):
    """Get time segments for a pay period — shifts with clock in/out times and earnings.

    Two-step flow:
    1. GET /timesheets/employees/{payPeriodId} — list employees with TimesheetIds
    2. POST /ta-open-resource-read/timesheets/output — bulk fetch timesheet data with segments
    Returns flattened time segments with timestamps, duration, and earnings per shift."""
    base_url = BASE_URL

    pay_period_id = user_input.get("pay_period_id")
    if not pay_period_id and pay_period_id != 0:
        return {"status_code": 400, "body": {"error": "pay_period_id is required"}}

    top = min(int(user_input.get("top", 50)), 100)
    skip = int(user_input.get("skip", 0))
    employee_id_filter = user_input.get("employee_id")

    req_headers = {**headers, "Accept": "application/json"}

    # Step 1: Get employees with timesheet IDs
    emp_url = f"{base_url}/timesheets/employees/{pay_period_id}?CheckExpirationDate=true&Top={top}&Skip={skip}&Count=false&OrderBy=PreferredName%20asc&timesheetArchived=false"
    emp_resp = requests.get(
        emp_url,
        headers=req_headers,
        impersonate="chrome131",
        timeout=30,
    )

    if emp_resp.status_code == 401:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if emp_resp.status_code != 200:
        return {
            "status_code": emp_resp.status_code,
            "body": {"error": f"API returned {emp_resp.status_code}", "detail": emp_resp.text[:500]},
        }

    try:
        employees = emp_resp.json()
    except Exception:
        return {"status_code": 500, "body": {"error": "Failed to parse employee list"}}

    if not employees:
        return {"status_code": 200, "body": []}

    # Build lookup and optionally filter by employee_id
    emp_lookup = {}
    timesheet_ids = []
    for emp in employees:
        if not isinstance(emp, dict):
            continue
        ts_id = emp.get("TimesheetId")
        eid = emp.get("EmployeeId")
        if employee_id_filter and eid != int(employee_id_filter):
            continue
        if ts_id:
            timesheet_ids.append(str(ts_id))
            emp_lookup[ts_id] = {
                "employeeId": eid,
                "employeeNumber": emp.get("EmployeeNumber"),
                "preferredName": emp.get("PreferredName"),
            }

    if not timesheet_ids:
        return {"status_code": 200, "body": []}

    # Step 2: Fetch full timesheet output
    ts_resp = requests.post(
        f"{base_url}/ta-open-resource-read/timesheets/output",
        headers={**req_headers, "Content-Type": "application/json"},
        data=json.dumps(",".join(timesheet_ids)),
        impersonate="chrome131",
        timeout=60,
    )

    if ts_resp.status_code == 401:
        return {"status_code": 401, "body": {"error": "Session expired"}}

    if ts_resp.status_code != 200:
        return {
            "status_code": ts_resp.status_code,
            "body": {"error": f"Timesheet output API returned {ts_resp.status_code}", "detail": ts_resp.text[:500]},
        }

    try:
        timesheets = ts_resp.json()
    except Exception:
        return {"status_code": 500, "body": {"error": "Failed to parse timesheet output"}}

    # Extract time segments — each TimeItem is a segment with start/end and nested payments
    segments = []
    for ts in timesheets:
        if not isinstance(ts, dict):
            continue

        ts_id = ts.get("Id")
        employee_info = emp_lookup.get(ts_id, {})

        entities = ts.get("TimesheetPayEntities", []) or []
        for entity in entities:
            if not isinstance(entity, dict):
                continue
            time_items = entity.get("TimeItems", []) or []
            for ti in time_items:
                if not isinstance(ti, dict):
                    continue

                duration_minutes = ti.get("Duration", 0) or 0
                hours = round(duration_minutes / 60, 4)

                # Extract earnings from nested PaymentItems
                total_earnings = 0.0
                rate = None
                for pi in (ti.get("PaymentItems", []) or []):
                    if isinstance(pi, dict) and "$ref" not in pi:
                        total_earnings += pi.get("Amount", 0) or 0
                        if rate is None:
                            rate = pi.get("Rate")

                time_code = ti.get("TimeCode")
                code_str = None
                is_overtime = False
                if isinstance(time_code, dict):
                    code_str = time_code.get("Code")
                    if (code_str or "").upper() in ("OT", "DT") or time_code.get("RateType", 0) > 1:
                        is_overtime = True

                segment = {
                    "timesheetId": ts_id,
                    "employeeId": employee_info.get("employeeId") or ts.get("EmployeeId"),
                    "employeeNumber": employee_info.get("employeeNumber"),
                    "workDay": ti.get("WorkDay"),
                    "start": ti.get("Start"),
                    "end": ti.get("End"),
                    "durationMinutes": duration_minutes,
                    "hours": hours,
                    "timeCodeId": ti.get("TimeCodeId"),
                    "timeCode": code_str,
                    "isOvertime": is_overtime,
                    "rate": rate,
                    "earnings": round(total_earnings, 2),
                    "jobId": ti.get("JobId"),
                    "locationId": ti.get("LocationId"),
                    "frozen": ti.get("Frozen"),
                }

                # Classify as regular or overtime earnings for convenience
                if is_overtime:
                    segment["regularHours"] = 0
                    segment["regularEarnings"] = 0
                    segment["overtimeHours"] = hours
                    segment["overtimeEarnings"] = round(total_earnings, 2)
                else:
                    segment["regularHours"] = hours
                    segment["regularEarnings"] = round(total_earnings, 2)
                    segment["overtimeHours"] = 0
                    segment["overtimeEarnings"] = 0

                segments.append(segment)

    return {"status_code": 200, "body": segments}
