from tools.web_search import search_web
from tools.filesystem import search_files, read_file, list_directory
from tools.file_sender import send_file_to_user
from tools.email_tool import read_emails, send_email, search_emails
from tools.scheduler_tool import schedule_reminder, list_reminders, cancel_reminder

def get_tools() -> list:
    return [
        search_web,
        search_files,
        read_file,
        list_directory,
        send_file_to_user,
        read_emails,
        send_email,
        search_emails,
        schedule_reminder,
        list_reminders,
        cancel_reminder,
    ]
