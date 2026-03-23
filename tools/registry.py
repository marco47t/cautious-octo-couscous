from tools.web_search import search_web
from tools.fetch_url_tool import fetch_url
from tools.datetime_tool import get_current_datetime
from tools.calculator_tool import run_python_expression
from tools.weather_tool import get_weather
from tools.github_tool import get_github_repo_info, get_github_recent_commits, get_github_open_issues
from tools.filesystem import search_files, read_file, list_directory
from tools.file_sender import send_file_to_user
from tools.email_tool import read_emails, open_email, send_email, search_emails
from tools.scheduler_tool import schedule_reminder, list_reminders, cancel_reminder
from tools.system_tool import get_system_info, get_top_processes
from tools.shell_tool import run_shell_command
from tools.memory_tools import retrieve_memory, retrieve_fact, list_all_facts
from tools.challenge_tool import (
    configure_challenges, stop_challenges,
    get_challenge_status, mark_challenge_solved, send_challenge_solution
)
from tools.tool_builder import create_tool, list_dynamic_tools, delete_dynamic_tool
from tools.dynamic_loader import load_all_dynamic_tools

def get_tools() -> list:
    base_tools = [
        # Knowledge
        search_web, fetch_url, get_current_datetime,
        run_python_expression, get_weather,
        # Memory
        retrieve_memory, retrieve_fact, list_all_facts,
        # GitHub
        get_github_repo_info, get_github_recent_commits, get_github_open_issues,
        # Files
        search_files, read_file, list_directory, send_file_to_user,
        # Email
        read_emails, open_email, send_email, search_emails,
        # Scheduling
        schedule_reminder, list_reminders, cancel_reminder,
        # Server
        get_system_info, get_top_processes, run_shell_command,
        # Challenges
        configure_challenges, stop_challenges,
        get_challenge_status, mark_challenge_solved, send_challenge_solution,
        # Tool builder
        create_tool, list_dynamic_tools, delete_dynamic_tool,
    ]
    # Append any tools created in previous sessions
    dynamic = load_all_dynamic_tools()
    return base_tools + dynamic
