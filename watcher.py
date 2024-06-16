import os
import time
import json
import sys
import signal
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import requests
from requests.auth import HTTPBasicAuth
from tenacity import retry, stop_after_attempt, wait_exponential
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import schedule

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

class Watcher:
    def __init__(self, config):
        self.observer = Observer()
        self.config = config
        self.load_status()

    def load_status(self):
        if os.path.exists(self.config['status_file']):
            with open(self.config['status_file'], 'r') as file:
                self.status = json.load(file)
        else:
            self.status = {}

    def save_status(self):
        with open(self.config['status_file'], 'w') as file:
            json.dump(self.status, file, indent=4)

    def retry_failed_uploads(self):
        for file_path, uploaded in self.status.items():
            if not uploaded:
                logging.info(f"Retrying upload for {file_path}")
                handler = Handler(self.config)
                handler.process_event(file_path)

    def send_notification(self, message):
        msg = MIMEMultipart()
        msg['From'] = 'noreply@yourcompany.com'
        msg['To'] = self.config['email']
        msg['Subject'] = 'Failed Upload Notification'
        body = message
        msg.attach(MIMEText(body, 'plain'))
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('noreply@yourcompany.com', 'password123')
        text = msg.as_string()
        server.sendmail(msg['From'], msg['To'], text)
        server.quit()

    def run(self):
        event_handler = Handler(self.config)
        self.observer.schedule(event_handler, self.config['directory_to_watch'], recursive=True)
        self.observer.start()
        schedule.every().day.at("00:00").do(self.retry_failed_uploads)
        try:
            while True:
                schedule.run_pending()
                time.sleep(1)
                self.save_status()
        except:
            self.observer.stop()
            logging.info("Observer Stopped")
        self.observer.join()

class Handler(FileSystemEventHandler):
    def __init__(self, config):
        self.config = config

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
    def upload_file(self, file_path):
        url = self.config['orthanc_server']
        headers = {}
        auth = None
        data = self.config.get('custom_data_send', {})

        if self.config['auth']['type'] == 'basic':
            user = self.config['auth']['user']
            password = self.config['auth']['password']
            auth = HTTPBasicAuth(user, password)
        elif self.config['auth']['type'] == 'bearer':
            token = self.config['auth']['token']
            headers['Authorization'] = f'Bearer {token}'
        elif self.config['auth']['type'] == 'custom':
            token = self.config['auth']['token']
            header_name = self.config['auth']['header_name']
            headers[header_name] = token

        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(url, files=files, headers=headers, auth=auth, data=data)

        if response.status_code == 200:
            logging.info(f"Successfully uploaded {file_path}")
            if 'callback_url' in self.config and self.config['callback_url']:
                self.send_callback(response.content)
            return True
        else:
            logging.error(f"Failed to upload {file_path}: {response.status_code} - {response.text}")
            response.raise_for_status()
            return False

    def send_callback(self, response_content):
        callback_url = self.config['callback_url']
        custom_data = self.config.get('custom_data_callback', {})
        headers = {'Content-Type': 'application/json'}
        payload = {**custom_data, 'response': response_content.decode('utf-8')}

        try:
            response = requests.post(callback_url, json=payload, headers=headers)
            if response.status_code == 200:
                logging.info("Callback sent successfully")
            else:
                logging.error(f"Failed to send callback: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Exception during callback: {str(e)}")

def load_configs(config_file):
    with open(config_file, 'r') as file:
        configs = json.load(file)
    return configs

def reload_signal_handler(signum, frame):
    logging.info('Received reload signal, reloading configurations...')
    global configs
    configs = load_configs('config.json')
    logging.info('Configurations reloaded successfully.')

if __name__ == '__main__':
    signal.signal(signal.SIGHUP, reload_signal_handler)
    config_file = sys.argv[1] if len(sys.argv) > 1 else 'config.json'
    configs = load_configs(config_file)
    watchers = [Watcher(config) for config in configs]
    for watcher in watchers:
        watcher.run()
