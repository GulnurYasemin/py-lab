import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Tuple


# === CHANGE THESE BEFORE SUBMITTING ===
STUDENT_ID = "123456"        # <-- kendi student id
STUDENT_NAME = "Name"        # <-- kendi adın
STUDENT_LASTNAME = "Lastname"  # <-- kendi soyadın


def validate_flight_row(fields: List[str]) -> Tuple[bool, Dict, List[str]]:
    """
    Validate a list of CSV fields representing one flight.
    Returns (is_valid, flight_dict_or_empty, error_messages_list).
    """
    errors = []

    # Basic field count check
    if len(fields) < 6:
        errors.append("missing required fields")
        return False, {}, errors

    # Take only first 6, ignore extra columns if any
    flight_id, origin, destination, dep_str, arr_str, price_str = [f.strip() for f in fields[:6]]

    # Check for missing individual required fields
    if not flight_id:
        errors.append("missing flight_id field")
    if not origin:
        errors.append("missing origin field")
    if not destination:
        errors.append("missing destination field")
    if not dep_str:
        errors.append("missing departure_datetime field")
    if not arr_str:
        errors.append("missing arrival_datetime field")
    if not price_str:
        errors.append("missing price field")

    # Only continue with format checks if all required fields are present
    if errors:
        return False, {}, errors

    # Validate flight_id: 2–8 alphanumeric
    if not (2 <= len(flight_id) <= 8) or not flight_id.isalnum():
        if len(flight_id) > 8:
            errors.append("flight_id too long (more than 8 characters)")
        else:
            errors.append("flight_id must be 2–8 alphanumeric characters")

    # Validate origin/destination: 3 uppercase letters
    if not (len(origin) == 3 and origin.isalpha() and origin.isupper()):
        errors.append("invalid origin code")
    if not (len(destination) == 3 and destination.isalpha() and destination.isupper()):
        errors.append("invalid destination code")

    # Validate datetimes
    dep_dt = None
    arr_dt = None
    try:
        dep_dt = datetime.strptime(dep_str, "%Y-%m-%d %H:%M")
    except ValueError:
        errors.append("invalid departure datetime")
    try:
        arr_dt = datetime.strptime(arr_str, "%Y-%m-%d %H:%M")
    except ValueError:
        errors.append("invalid arrival datetime")

    if dep_dt and arr_dt:
        if arr_dt <= dep_dt:
            errors.append("arrival before departure")

    # Validate price: positive float
    try:
        price_val = float(price_str)
        if price_val < 0:
            errors.append("negative price value")
        elif price_val == 0:
            errors.append("non-positive price value")
    except ValueError:
        errors.append("invalid price value")
        price_val = None

    if errors:
        return False, {}, errors

    flight = {
        "flight_id": flight_id,
        "origin": origin,
        "destination": destination,
        "departure_datetime": dep_str,
        "arrival_datetime": arr_str,
        "price": price_val,
    }
    return True, flight, []


def parse_csv_file(path: str) -> Tuple[List[Dict], List[str]]:
    """
    Parse a single CSV file.
    Returns (valid_flights, error_lines) where error_lines are ready-to-write strings.
    """
    valid_flights: List[Dict] = []
    error_lines: List[str] = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, raw_line in enumerate(f, start=1):
                line = raw_line.rstrip("\n")
                stripped = line.strip()

                # Ignore completely empty lines (no error output)
                if stripped == "":
                    continue

                # Header line
                if line_num == 1 and stripped.lower().startswith("flight_id,origin,destination"):
                    continue

                # Comment line
                if stripped.startswith("#"):
                    msg = f"Line {line_num}: {line} \u2192 comment line, ignored for data parsing"
                    error_lines.append(msg)
                    continue

                # Parse CSV fields (simple split is enough here)
                fields = [field.strip() for field in line.split(",")]

                is_valid, flight, row_errors = validate_flight_row(fields)
                if is_valid:
                    valid_flights.append(flight)
                else:
                    reason = ", ".join(row_errors)
                    msg = f"Line {line_num}: {line} \u2192 {reason}"
                    error_lines.append(msg)
    except FileNotFoundError:
        print(f"ERROR: File not found: {path}", file=sys.stderr)
    except OSError as e:
        print(f"ERROR: Could not read file {path}: {e}", file=sys.stderr)

    return valid_flights, error_lines


def parse_csv_folder(folder: str) -> Tuple[List[Dict], List[str]]:
    """
    Parse all .csv files in a folder.
    """
    all_valid: List[Dict] = []
    all_errors: List[str] = []

    if not os.path.isdir(folder):
        print(f"ERROR: Not a directory: {folder}", file=sys.stderr)
        return [], []

    for name in sorted(os.listdir(folder)):
        if not name.lower().endswith(".csv"):
            continue
        full_path = os.path.join(folder, name)
        vf, errs = parse_csv_file(full_path)
        all_valid.extend(vf)
        all_errors.extend(errs)

    return all_valid, all_errors


def write_json_db(flights: List[Dict], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(flights, f, indent=2)
    print(f"Saved {len(flights)} valid flights to {output_path}")


def write_errors_file(errors: List[str], output_path: str) -> None:
    # If no errors, still create a small informative file
    with open(output_path, "w", encoding="utf-8") as f:
        if not errors:
            f.write("No errors found.\n")
        else:
            for line in errors:
                f.write(line + "\n")
    print(f"Saved error report to {output_path}")


def load_json_db(path: str) -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        else:
            print("ERROR: JSON database must be a list of flight objects.", file=sys.stderr)
            return []
    except FileNotFoundError:
        print(f"ERROR: JSON database not found: {path}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse JSON database: {e}", file=sys.stderr)
    return []


def load_query_file(path: str) -> List[Dict]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data
        print("ERROR: Query file must contain an object or a list of objects.", file=sys.stderr)
        return []
    except FileNotFoundError:
        print(f"ERROR: Query file not found: {path}", file=sys.stderr)
    except json.JSONDecodeError as e:
        print(f"ERROR: Failed to parse query file: {e}", file=sys.stderr)
    return []


def parse_datetime_safe(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except (TypeError, ValueError):
        return None


def match_query_on_flight(query: Dict, flight: Dict) -> bool:
    """
    Check if a single flight matches a query according to rules.
    """
    for key, value in query.items():
        if key in {"flight_id", "origin", "destination"}:
            if str(flight.get(key)) != str(value):
                return False
        elif key == "departure_datetime":
            q_dt = parse_datetime_safe(str(value))
            f_dt = parse_datetime_safe(flight.get("departure_datetime"))
            if not (q_dt and f_dt and f_dt >= q_dt):
                return False
        elif key == "arrival_datetime":
            q_dt = parse_datetime_safe(str(value))
            f_dt = parse_datetime_safe(flight.get("arrival_datetime"))
            if not (q_dt and f_dt and f_dt <= q_dt):
                return False
        elif key == "price":
            try:
                q_price = float(value)
                f_price = float(flight.get("price"))
            except (TypeError, ValueError):
                return False
            if f_price > q_price:
                return False
        else:
            # Unknown field in query -> ignore it (do not fail)
            pass
    return True


def run_queries(db: List[Dict], queries: List[Dict]) -> List[Dict]:
    responses = []
    for q in queries:
        matches = [flight for flight in db if match_query_on_flight(q, flight)]
        responses.append({
            "query": q,
            "matches": matches
        })
    return responses


def build_response_filename() -> str:
    now = datetime.now()
    timestamp = now.strftime("%Y%m%d_%H%M")
    # You MUST change the constants at the top of this file!
    return f"response_{STUDENT_ID}_{STUDENT_NAME}_{STUDENT_LASTNAME}_{timestamp}.json"


def main():
    parser = argparse.ArgumentParser(
        description="Flight Schedule Parser and Query Tool"
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--input", help="Path to a CSV file with flights")
    group.add_argument("-d", "--directory", help="Path to a folder with CSV files")
    parser.add_argument("-o", "--output", help="Output JSON path for valid flights")
    parser.add_argument("-j", "--jsondb", help="Use existing JSON database instead of parsing CSV")
    parser.add_argument("-q", "--query", help="Path to query JSON file")

    args = parser.parse_args()

    # Basic argument checks
    if args.jsondb and (args.input or args.directory):
        print("ERROR: Use either -j (JSON database) OR -i / -d (CSV parsing), not both.", file=sys.stderr)
        sys.exit(1)

    if not args.jsondb and not (args.input or args.directory):
        parser.print_help()
        sys.exit(1)

    db: List[Dict] = []
    errors: List[str] = []

    # 1) Load or build database
    if args.jsondb:
        db = load_json_db(args.jsondb)
        if not db:
            print("No flights loaded from JSON database.", file=sys.stderr)
    else:
        # Parse CSV(s)
        if args.input:
            db, errors = parse_csv_file(args.input)
        elif args.directory:
            db, errors = parse_csv_folder(args.directory)

        # Decide paths
        output_db_path = args.output if args.output else "db.json"
        if args.output:
            errors_path = os.path.join(os.path.dirname(args.output) or ".", "errors.txt")
        else:
            errors_path = "errors.txt"

        write_json_db(db, output_db_path)
        write_errors_file(errors, errors_path)

    # 2) Optionally run queries
    if args.query:
        if not db:
            print("ERROR: No database loaded to run queries on.", file=sys.stderr)
            sys.exit(1)
        queries = load_query_file(args.query)
        if not queries:
            print("No valid queries loaded.", file=sys.stderr)
            sys.exit(1)
        responses = run_queries(db, queries)
        response_file = build_response_filename()
        with open(response_file, "w", encoding="utf-8") as f:
            json.dump(responses, f, indent=2)
        print(f"Saved query responses to {response_file}")


if __name__ == "__main__":
    main()
