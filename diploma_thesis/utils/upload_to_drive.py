import io
import json

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from diploma_thesis.settings import NIH_EMAIL, PACKAGE_DIR, logger

credentials = service_account.Credentials.from_service_account_file(PACKAGE_DIR.parent / "credentials.json",
                                                                    scopes=[
                                                                        "https://www.googleapis.com/auth/drive"
                                                                    ])
drive_service = build("drive", "v3", credentials=credentials)


def upload_json_to_drive(data: list | dict, file_name: str) -> None:
    """
    Serialize to JSON, upload to Google Drive, and share the file with the email address from settings.

    Args:
        data (dict | list): Data to save.
        file_name (str): File name under which the data saves to the Drive.
    """
    if type(data) is dict:
        data = [data]
    json_data = json.dumps(data, indent=4, ensure_ascii=False)
    file_stream = io.BytesIO(json_data.encode("utf-8"))

    file_metadata = {
        "name": file_name,
        "mimeType": "application/json"
    }

    media = MediaIoBaseUpload(
        file_stream,
        mimetype="application/json",
        resumable=True
    )

    try:
        file = drive_service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id"
        ).execute()

        permission = {
            "type": "user",
            "role": "writer",
            "emailAddress": NIH_EMAIL
        }
        drive_service.permissions().create(fileId=file.get("id"), body=permission).execute()

    except Exception as e:
        logger.exception(f"Error uploading file ({file_name}) to the Drive: {e}")


if __name__ == '__main__':
    data = ["string", "string", {"key": "value"}]
    upload_json_to_drive(data, "test.json")
