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
    Serializuje data do JSONu a nahraje je na Google Drive.

    Args:
        data (dict | list): Data, která chcete uložit.
        file_name (str): Název souboru, pod kterým se uloží na Disku.
    """
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
        logger.error(f"Error uploading file ({file_name} to Drive: {e}")


if __name__ == '__main__':
    data = ["list", "list", {"key": "value"}]
    upload_json_to_drive(data, "test.json")
