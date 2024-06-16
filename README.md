# mediverse-watcher
File watcher and dicom upload service for Mediverse PACS
MEDIVERSE PACS FILE UPLOADER SERVICE:

1. Watcher.py is a python script to be run as a service to watch folders on a server and upload them to an orthanc server instance (or any other API endpoint for that mattter).

2. Config.json is the config file for watcher.py, specifying which folders to watch, and which endpoints to upload them to, as well as the authentication method for the destination endpoints, and any callback urls to send received data to
3. custom data can be added to the upload or callback requests using the custom_data_* fields in the config.json file

4. install_watcher.sh is the Bash script for running the service. It installs python, all dependencies, and also creates a systemd service file to ensure the script runs at system start.

## Ensure that any path to status files in the config.json are accessible and created before running the installer
