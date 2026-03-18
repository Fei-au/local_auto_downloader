from datetime import datetime
import logging
import os
import sys
import time
import uuid
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import requests
from requests.exceptions import RequestException
from google.cloud import storage
from google.cloud.sql.connector import Connector, IPTypes
import sqlalchemy
from sqlalchemy import text


GOOGLE_APPLICATION_CREDENTIALS = "C:\\Users\\KY\\Desktop\\local_auto_downloader\\glass-gasket-415918-b30506c4d63f.json"
INSTANCE_CONNECTION_NAME = "glass-gasket-415918:us-central1:ruitowh"
SQL_USER = "root"
SQL_PASSWORD = "root"
SQL_DATABASE_NAME = "ruito"
BUCKET = "rt-staff-files"


logger = logging.getLogger("auto_download_imagex")
logger.setLevel(logging.INFO)

if not logger.handlers:
	stream_handler = logging.StreamHandler(sys.stdout)
	stream_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s"))
	logger.addHandler(stream_handler)

logger.propagate = False

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

connector = Connector()


def get_mysql_conn():
	return connector.connect(
		INSTANCE_CONNECTION_NAME,
		"pymysql",
		user=SQL_USER,
		password=SQL_PASSWORD,
		db=SQL_DATABASE_NAME,
		ip_type=IPTypes.PUBLIC,
	)


engine = sqlalchemy.create_engine(
	"mysql+pymysql://",
	creator=get_mysql_conn,
    pool_pre_ping=True,
    pool_recycle=3600,
)


def get_extension_from_url(image_url):
	parsed_url = urlparse(image_url)
	_, file_extension = os.path.splitext(parsed_url.path)
	return file_extension


def upload_to_gcs(source_file, destination_blob_name):
	storage_client = storage.Client()
	bucket = storage_client.bucket(BUCKET)
	blob = bucket.blob(destination_blob_name)
	blob.upload_from_file(source_file, content_type="image/jpeg")


def download_image_to_gcs(image_url, max_retries=3):
	extension = get_extension_from_url(image_url) or ".jpg"

	for attempt in range(1, max_retries + 1):
		try:
			response = requests.get(image_url, timeout=10)
			response.raise_for_status()

			with NamedTemporaryFile() as temp_file:
				temp_file.write(response.content)
				temp_file.flush()
				temp_file.seek(0)

				date_prefix = datetime.now().strftime("%Y%m%d")
				file_path = f"temp_image/{date_prefix}/{uuid.uuid4()}{extension}"
				upload_to_gcs(temp_file, file_path)
				return file_path
		except RequestException as exc:
			logger.warning(
				"Download attempt %s/%s failed for %s: %s",
				attempt,
				max_retries,
				image_url,
				exc,
			)
			if attempt < max_retries:
				time.sleep(2)
			else:
				raise


def fetch_last_day_missing_image_entries():
	query = text(
		"""
		SELECT id, image1, image2, image3, image1_url, image2_url, image3_url
		FROM inventory_temp_item
		WHERE add_date >= DATE_SUB(NOW(), INTERVAL 30 DAY)
		  AND (
			(image1_url IS NOT NULL AND image1 IS NULL)
			OR (image2_url IS NOT NULL AND image2 IS NULL)
			OR (image3_url IS NOT NULL AND image3 IS NULL)
		  )
		ORDER BY id ASC
		"""
	)

	with engine.connect() as connection:
		return connection.execute(query).mappings().all()



def update_image_fields(entry_id, updates):
	valid_columns = {"image1", "image2", "image3"}
	if not updates:
		return

	for column in updates:
		if column not in valid_columns:
			raise ValueError(f"Invalid image column: {column}")

	set_clauses = ", ".join([f"{column} = :{column}" for column in updates.keys()])
	params = {"entry_id": entry_id}
	params.update(updates)

	query = text(
		f"""
		UPDATE inventory_temp_item
		SET {set_clauses}
		WHERE id = :entry_id
		"""
	)

	with engine.connect() as connection:
		connection.execute(query, params)
		connection.commit()


def main():
	updated_image_count = 0
	failed_count = 0

	entries = fetch_last_day_missing_image_entries()
	logger.info("Found %s entries to process.", len(entries))

	for entry in entries:
		entry_id = entry["id"]
		entry_updates = {}

		logger.info("Processing entry id=%s", entry_id)

		try:
			for idx in (1, 2, 3):
				image_column = f"image{idx}"
				url_column = f"image{idx}_url"
				image_value = entry[image_column]
				image_url = entry[url_column]

				if image_url is not None and image_value is None:
					try:
						image_path = download_image_to_gcs(image_url)
						logger.info("Downloaded %s for id=%s to %s", image_column, entry_id, image_path)
						entry_updates[image_column] = image_path
					except RequestException as exc:
						logger.error("Failed to download %s for id=%s: %s", image_column, entry_id, exc)
					finally:
						# Sleep after finishing one image download attempt.
						time.sleep(3)

			if entry_updates:
				update_image_fields(entry_id, entry_updates)
				updated_image_count += len(entry_updates)
				logger.info("Updated id=%s with columns=%s", entry_id, list(entry_updates.keys()))

		except Exception as exc:
			failed_count += 1
			logger.error("Failed processing id=%s: %s", entry_id, exc)
		finally:
			# Sleep after finishing one entry (success or fail).
			time.sleep(3)

	completed_entries = len(entries) - failed_count

	return {
		"entries_checked": len(entries),
		"completed_entries": completed_entries,
		"failed_entries": failed_count,
		"updated_images": updated_image_count,
	}


if __name__ == "__main__":
	cycle_count = 0
	total_entries_checked = 0
	total_completed_entries = 0
	total_failed_entries = 0
	total_updated_images = 0

	try:
		while True:
			stats = main()
			cycle_count += 1
			total_entries_checked += stats["entries_checked"]
			total_completed_entries += stats["completed_entries"]
			total_failed_entries += stats["failed_entries"]
			total_updated_images += stats["updated_images"]

			logger.info(
				"Running total after cycles=%s: completed entries=%s, failed entries=%s, entries checked=%s, updated images=%s",
				cycle_count,
				total_completed_entries,
				total_failed_entries,
				total_entries_checked,
				total_updated_images,
			)
			time.sleep(300)
	except KeyboardInterrupt:
		logger.info("Stopped by user.")
	finally:
		connector.close()
