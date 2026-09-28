from opspilot_api import jobs as _jobs

process_event_job = _jobs.process_event_job
sync_gmail_job = _jobs.sync_gmail_job


if __name__ == "__main__":
    print("OpsOS worker ready; listening on Redis queue")
