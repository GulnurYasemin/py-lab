import argparse
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Tuple


STUDENT_ID = "231ADB101"          
STUDENT_NAME = "Gulnur Yasemin"          
STUDENT_LASTNAME = "Uygun"  



# VALIDATION FUNCTION
 
def validate_flight_row(fields: List[str]) -> Tuple[bool, Dict, List[str]]:
    """
    Validate one CSV line (after splitting by comma).

    Returns:
      - is_valid (bool)
      - flight_dict (dict if valid, {} if not)
      - error_messages (list of readable error strings)
    """
    errors = []

    # CSV must contain exactly 6 fields
    if len(fields) < 6:
        errors.append("missing required fields")
        return False, {}, errors

    # Extract & clean fields
    flight_id, origin, destination, dep_str, arr_str, price_str = [f.strip() for f in fields[:6]]

    # Check required fields are not empty
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

    # Stop early if missing essential fields
    if errors:
        return False, {}, errors

    # Validate flight_id (2–8 alphanumeric characters)
    if not (2 <= len(flight_id) <= 8 and flight_id.isalnum()):
        if len(flight_id) > 8:
            errors.append("flight_id too long (more than 8 characters)")
        else:
            errors.append("flight_id must be 2–8 alphanumeric characters")

    # Validate IATA airport codes: must be 3 uppercase letters
    if not (len(origin) == 3 and origin.isalpha() and origin.isupper()):
        errors.append("invalid origin code")
    if not (len(destination) == 3 and destination.isalpha() and destination.isupper()):
        errors.append("invalid destination code")

    # Validate datetime fields
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

    # Ensure arrival > departure
    if dep_dt and arr_dt:
        if arr_dt <= dep_dt:
            errors.append("arrival before departure")

    # Validate price
    try:
        price_val = float(price_str)
        if price_val < 0:
            errors.append("negative price value")
    except ValueError:
        errors.append("invalid price value")
        price_val = None

    # Return errors if found
    if errors:
        return False, {}, errors

    # Return valid flight dictionary
    flight = {
        "flight_id": flight_id,
        "origin": origin,
        "destination": destination,
        "departure_datetime": dep_str,
        "arrival_datetime": arr_str,
        "price": price_val,
    }

    return True, flight, []



# PARSE SINGLE CSV FILE

def parse_csv_file(path: str) -> Tuple[List[Dict], List[str]]:
    """
    Parse a single CSV file and return:
      - list of valid flights
      - list of error lines (ready to write into errors.txt)
    """
    valid_flights = []
    error_lines = []

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line_num, raw_line in enumerate(f, start=1):
                line = raw_line.rstrip("\n")
                stripped = line.strip()

                # Ignore empty lines
                if stripped == "":
                    continue

                # Skip header line
                if line_num == 1 and stripped.lower().startswith("flight_id,origin"):
                    continue

                # Identify comment lines
                if stripped.startswith("#"):
                    error_lines.append(
                        f"Line {line_num}: {line} → comment line, ignored for data parsing"
                    )
                    continue

                # Split CSV (simple split is OK here)
                fields = [field.strip() for field in line.split(",")]

                # Validate row
                is_valid, flight, row_errs = validate_flight_row(fields)

                if is_valid:
                    valid_flights.append(flight)
                else:
                    msg = f"Line {line_num}: {line} → {', '.join(row_errs)}"
                    error_lines.append(msg)

    except FileNotFoundError:
        print(f"ERROR: File not found: {path}", file=sys.stderr)
    except OSError as e:
        print(f"ERROR: Could not read file {path}: {e}", file=sys.stderr)

    return valid_flights, error_lines



# PARSE ALL CSV FILES IN FOLDER

def parse_csv_folder(folder: str) -> Tuple[List[Dict], List[str]]:
    """
    Parse all .csv files inside a folder (alphabetical order).
    """
    all_valid = []
    all_errors = []

    if not os.path.isdir(folder):
        print(f"ERROR: Not a directory: {folder}", file=sys.stderr)
        return [], []

    for name in sorted(os.listdir(folder)):
        if name.lower().endswith(".csv"):
            path = os.path.join(folder, name)
            vf, errs = parse_csv_file(path)
            all_valid.extend(vf)
            all_errors.extend(errs)

    return all_valid, all_errors



# WRITE JSON DATABASE

def write_json_db(flights: List[Dict], output_path: str):
    """
    Save valid flights into a JSON file.
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(flights, f, indent=2)
    print(f"Saved {len(flights)} valid flights to {output_path}")



# WRITE ERRORS TXT FILE

def write_errors_file(errors: List[str], output_path: str):
    """
    Write all error lines to errors.txt.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        if not errors:
            f.write("No errors found.\n")
        else:
            for line in errors:
                f.write(line + "\n")
    print(f"Saved error report to {output_path}")



# LOAD EXISTING db.json

def load_json_db(path: str) -> List[Dict]:
    """
    Load a JSON database file.
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        print("ERROR: JSON database must contain an array of flights.")
        return []
    except Exception as e:
        print(f"ERROR reading JSON database: {e}")
        return []



# QUERY FUNCTIONS

def load_query_file(path: str) -> List[Dict]:
    """
    Load queries from a JSON file (either object or array).
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        if isinstance(data, dict):
            return [data]
        if isinstance(data, list):
            return data

        print("ERROR: Query file must contain an object or a list.")
        return []
    except Exception as e:
        print(f"ERROR reading query file: {e}")
        return []


def parse_datetime_safe(s: str):
    """Convert string to datetime safely (returns None if invalid)."""
    try:
        return datetime.strptime(s, "%Y-%m-%d %H:%M")
    except:
        return None


def match_query_on_flight(query: Dict, flight: Dict) -> bool:
    """
    Determine if a flight matches the query conditions.
    Implements required filtering logic.
    """
    for key, value in query.items():
        if key in {"flight_id", "origin", "destination"}:
            if str(flight.get(key)) != str(value):
                return False

        elif key == "departure_datetime":
            q = parse_datetime_safe(value)
            f = parse_datetime_safe(flight["departure_datetime"])
            if not (q and f and f >= q):
                return False

        elif key == "arrival_datetime":
            q = parse_datetime_safe(value)
            f = parse_datetime_safe(flight["arrival_datetime"])
            if not (q and f and f <= q):
                return False

        elif key == "price":
            try:
                if float(flight["price"]) > float(value):
                    return False
            except:
                return False

        # Ignore unknown fields
    return True


def run_queries(db: List[Dict], queries: List[Dict]) -> List[Dict]:
    """
    Apply all queries to the database and return results.
    """
    results = []
    for q in queries:
        matches = [f for f in db if match_query_on_flight(q, f)]
        results.append({"query": q, "matches": matches})
    return results


def build_response_filename() -> str:
    """Generate required timestamped response filename."""
    now = datetime.now().strftime("%Y%m%d_%H%M")
    return f"response_{STUDENT_ID}_{STUDENT_NAME}_{STUDENT_LASTNAME}_{now}.json"



# MAIN PROGRAM / CLI LOGIC

def main():
    parser = argparse.ArgumentParser(description="Flight Schedule Parser and Query Tool")

    # Mutually exclusive group: either -i OR -d OR -j
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-i", "--input", help="Path to a CSV file")
    group.add_argument("-d", "--directory", help="Folder containing CSV files")
    group.add_argument("-j", "--jsondb", help="Use existing JSON database instead of CSV")

    parser.add_argument("-o", "--output", help="Custom output path for db.json")
    parser.add_argument("-q", "--query", help="Path to query JSON file")

    args = parser.parse_args()

    db = []
    errors = []

    # Prevent conflicting arguments
    if args.jsondb and (args.input or args.directory):
        print("ERROR: Use -j OR -i/-d, not both.")
        sys.exit(1)

    # Nothing selected?
    if not args.jsondb and not (args.input or args.directory):
        parser.print_help()
        sys.exit(1)

    # Load database (JSON or CSV parsing)
    if args.jsondb:
        db = load_json_db(args.jsondb)
    else:
        if args.input:
            db, errors = parse_csv_file(args.input)
        elif args.directory:
            db, errors = parse_csv_folder(args.directory)

        # Save parsed results
        output_path = args.output if args.output else "db.json"
        write_json_db(db, output_path)

        errors_path = os.path.join(os.path.dirname(output_path) or ".", "errors.txt")
        write_errors_file(errors, errors_path)

    # Run queries if provided
    if args.query:
        if not db:
            print("ERROR: No database loaded for querying.")
            sys.exit(1)

        queries = load_query_file(args.query)
        responses = run_queries(db, queries)

        response_filename = build_response_filename()
        with open(response_filename, "w", encoding="utf-8") as f:
            json.dump(responses, f, indent=2)

        print(f"Saved query results to {response_filename}")


if __name__ == "__main__":
    main()
