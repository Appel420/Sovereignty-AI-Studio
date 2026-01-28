The provided Python scripts include multiple overlapping and partially corrupted segments that need debugging. Here is a clean and functional refactored version of the AI Code Feedback tool that ensures proper logging, summary exports, and CSV support:

import datetime
import uuid
import ast
import csv

def is_code_clean(code_snippet: str) -> bool:
    """Check if the Python snippet is syntactically valid."""
    try:
        ast.parse(code_snippet)
        return True
    except SyntaxError:
        return False

def ai_feedback_on_code(is_clean: bool, log_file: str, session_id: str):
    """Provide feedback based on code cleanliness and log the result."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if is_clean:
        feedback = "✅ Great job! Your code is clean and syntactically correct."
        suggestion = "💡 Suggestions: Consider adding safety checks or optimizations for stability."
    else:
        feedback = "⚠️ The code could use improvements."
        suggestion = "💡 Suggestions: Work on readability, error handling, and security measures."

    print(feedback)
    print(suggestion)

    with open(log_file, "a") as f:
        f.write(f"[{timestamp}] [Session: {session_id}] {feedback} {suggestion}\n")

def log_session_summary(log_file: str, summary_file: str, csv_file: str,
                        session_id: str, positive: int, negative: int,
                        total_length: int, submissions: int) -> str:
    """Record a session summary in log, summary, and CSV files."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    avg_length = total_length / submissions if submissions else 0

    summary = (
        f"\n=== Session Summary [{session_id}] @ {timestamp} ===\n"
        f"Positive feedbacks: {positive}\n"
        f"Negative feedbacks: {negative}\n"
        f"Total submissions: {submissions}\n"
        f"Average code length: {avg_length:.2f} characters\n"
        "===============================\n"
    )

    with open(log_file, "a") as f:
        f.write(summary)
    with open(summary_file, "a") as f:
        f.write(summary)
    with open(csv_file, "a", newline="") as f:
        csv.writer(f).writerow([session_id, timestamp, positive, negative, submissions, f"{avg_length:.2f}"])

    return summary

def search_previous_summaries(log_file: str):
    """Display lines from log that look like session summaries."""
    print("\n=== Previous Session Summaries ===")
    try:
        with open(log_file, "r") as f:
            for line in f:
                if line.startswith("=== Session Summary") or any(
                    line.startswith(prefix) for prefix in ["Positive", "Negative", "Total", "Average"]):
                    print(line.strip())
    except FileNotFoundError:
        print("No previous logs found.")

def main():
    print("👋 Welcome to the AI Code Feedback Tool!")

    session_id = str(uuid.uuid4())[:8]
    log_file = input("Enter log filename (e.g., feedback_log.txt): ").strip() or "feedback_log.txt"
    summary_file = input("Enter summary filename (e.g., summary_log.txt): ").strip() or "summary_log.txt"
    csv_file = input("Enter CSV filename (e.g., summary_log.csv): ").strip() or "summary_log.csv"
    mode = input("Append or overwrite logs? (append/overwrite): ").strip().lower()

    if mode == "overwrite":
        open(log_file, "w").close()
        open(summary_file, "w").close()
        with open(csv_file, "w", newline="") as f:
            csv.writer(f).writerow(["Session ID", "Timestamp", "Positive", "Negative", "Submissions", "Average Code Length"])

    total_length = 0
    positive_count = 0
    negative_count = 0
    submissions = 0

    while True:
        print("\n=== Menu ===")
        print("1. Submit code snippet for feedback")
        print("2. View current feedback summary")
        print("3. Search previous session summaries")
        print("4. Exit session")

        choice = input("Select an option (1/2/3/4): ").strip()

        if choice == "1":
            code = input("Paste your code snippet: ").strip()
            clean = is_code_clean(code)
            ai_feedback_on_code(clean, log_file, session_id)

            submissions += 1
            total_length += len(code)
            if clean:
                positive_count += 1
            else:
                negative_count += 1

        elif choice == "2":
            avg_length = total_length / submissions if submissions else 0
            print(f"\nCurrent Feedback Summary:\nPositive: {positive_count}\nNegative: {negative_count}\nTotal Submissions: {submissions}\nAverage Code Length: {avg_length:.2f} characters")

        elif choice == "3":
            search_previous_summaries(log_file)

        elif choice == "4":
            print("👋 Exiting feedback loop. Have a great day!")
            print(log_session_summary(log_file, summary_file, csv_file, session_id, positive_count, negative_count, total_length, submissions))
            break

        else:
            print("❓ Invalid option. Please select 1, 2, 3, or 4.")

if __name__ == "__main__":
    main()

This version removes the corrupted function names (with asterisks), resolves variable inconsistencies, and ensures CSV and summary logging work correctly.
