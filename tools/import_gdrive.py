from googleapiclient.http import MediaIoBaseUpload
from lore.api.resource import objid_matcher, full_objid_matcher
from tools.batch import Batch, Column, bulk_update
from lore.model.asset import get_gdrive_api, FileAsset, get_google_urls
from datetime import timezone
from unicodedata import normalize
from distutils.util import strtobool
import csv
import pprint

# TODO
# [ ] Check that we match to a file that is public, and if not, that we warn or inform that the user has to make it public first
# [ ] Or automatically set to public https://stackoverflow.com/questions/11665215/is-it-possible-to-share-a-file-publicly-through-google-drive-api
# [ ] Other alt is to implement the GDrive API so we can serve files on a Lore URL, and then use that to fix share with Cloudinary or similar
# [ ] Check if a file in GridFS is used at all. If not used, we can delete it instead. Used means referenced in other objects or
# referenced by slug in article texts
# [ ] Filter by filename and type


def size_in_mb(size):
    return f"{size / (1024*1024):.2f} MB"


def build_gdrive_index(gdrive_api):
    """As Gdrive can have a huge number of files, and we want to check each for metadata, we need to preload an index instead of
    asking for each file. This function creates a CSV file that can act as an index.
    Args:
        gdrive_api ([type]): [description]
    """

    # The returned File resources don't have a field declaring visibility, e.g. if shareable publically, even if visibility status can be queried.
    # We found that we could read visibility on a File by checking if permissionIds contain certain strings, but that failed when we
    # saw that not all Files had a permissionIds field populated, even though it should
    # In the end we solve it by first querying all files, and then querying only public files, and merging the results.
    files_list_req = gdrive_api.list(
        # A shortened list of mimeTypes here to reduce the total index size
        q="trashed = false and (mimeType contains 'png' or mimeType contains 'jpeg' or mimeType contains 'pdf' or mimeType contains 'zip')",
        pageSize=1000,  # 1000 is max. If permissions field is included, it will be capped at 100 per page
        fields="nextPageToken, files(id, md5Checksum, name)",
    )

    file_data_map = {}
    tot = 0
    while files_list_req is not None:
        results = files_list_req.execute()
        file_data_map.update((f["id"], f) for f in results["files"])
        tot += len(results["files"])
        print(f"Read {tot} files into index")
        files_list_req = gdrive_api.list_next(files_list_req, results)

    files_list_req = gdrive_api.list(
        q="(visibility = 'anyoneWithLink' or visibility = 'anyoneCanFind') and trashed = false and (mimeType contains 'png' or mimeType contains 'jpeg' or mimeType contains 'pdf' or mimeType contains 'zip')",
        pageSize=1000,
        fields="nextPageToken, files(id)",
    )
    while files_list_req is not None:
        results = files_list_req.execute()
        for f in results["files"]:
            if f["id"] in file_data_map:
                file_data_map[f["id"]]["public"] = True
        files_list_req = gdrive_api.list_next(files_list_req, results)

    with open("gdrive_index.csv", "w") as handle:
        writer = csv.writer(handle, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow(("GID", "MD5", "Name", "Public"))
        for item in file_data_map.values():
            writer.writerow((item["id"], item.get("md5Checksum", ""), item["name"], item.get("public", False)))


def import_all_gridfs(folder_id, limit, commit, log_level, build=False, **kwargs):

    columns = [
        Column("Filename", "attachment_filename", "name"),
        Column("ID", "id", "google_id"),
        Column("Size", "length", "size"),
        Column("Exists", result_key="exists"),
    ]

    if limit < 1:
        limit = 10000  # limit=0 should work but doesn't
    gridfile_assets = FileAsset.objects(file_data__exists=True).limit(limit)
    gdrive_api = get_gdrive_api().files()

    if build:
        build_gdrive_index(gdrive_api)

    gdrive_index_by_md5 = {}
    gdrive_index_by_name = {}
    with open("gdrive_index.csv", "r") as handle:
        reader = csv.reader(handle, delimiter=";")
        reader.__next__()  # Skip first header row
        for row in reader:
            gid = row[0]
            md5 = row[1]
            name = row[2]
            public = bool(strtobool(row[3]))
            # Special logic as several Google Docs can have same MD5 and we don't just want the last one to win
            # We overwrite if dict has no record or if old record is private while new is public
            if md5 not in gdrive_index_by_md5 or (public is True and gdrive_index_by_md5[md5][1] is False):
                gdrive_index_by_md5[md5] = (gid, public)
            if name not in gdrive_index_by_name or (public is True and gdrive_index_by_name[name][1] is False):
                gdrive_index_by_name[name] = (gid, public)

    batch = Batch(
        "Importing all GridFS data from database",
        dry_run=not commit,
        log_level=log_level,
        table_columns=columns,
        folder_id=folder_id,
        gdrive_api=gdrive_api,
        gdrive_index_by_md5=gdrive_index_by_md5,
        gdrive_index_by_name=gdrive_index_by_name,
        sum_size=0,
        **kwargs,
    )
    batch.process(gridfile_assets, import_gridfs_job)

    print(batch.summary_str())
    print(size_in_mb(batch.context["sum_size"]))


def check_gdrive_id(google_id):
    gdrive_api = get_gdrive_api().files()
    pp = pprint.PrettyPrinter(indent=4)
    file_data = gdrive_api.get(
        fileId=google_id,
        fields="*",
    ).execute()
    pp.pprint(file_data)


def import_one_gridfs(objid, folder_id):
    assert objid_matcher.match(objid) or full_objid_matcher.match(objid)
    fa = FileAsset.objects(id=objid).get()
    import_gridfs_job(job=None, data=fa, folder_id=folder_id)


def import_gridfs_job(job, data, commit=False, **kwargs):

    folder_id = kwargs.get("folder_id") or job.context.get("folder_id")
    api = job.context["gdrive_api"]
    gdrive_index_by_md5 = job.context.get("gdrive_index_by_md5", {})
    gdrive_index_by_name = job.context.get("gdrive_index_by_name", {})

    gridfile = data.file_data.get()

    file_metadata = {
        # File names, esp from MacOS, can include other forms of unicode which messes up length and other stuff
        "name": normalize("NFC", data.source_filename or data.attachment_filename or gridfile.filename),
        "description": data.description,
        "mimeType": gridfile.content_type,
        "parents": [folder_id],
        # We get naive (tz missing, but utc implied) datetimes from mongo
        "createdTime": data.created_date.replace(tzinfo=timezone.utc).isoformat(),
    }

    gdrive_urls = {}
    results_metadata = {}
    results_metadata["size"] = size_in_mb(gridfile.length)  # For the job to print the size

    # Status of a file in Gdrive can be:
    # unknown: no index created)
    # miss: not found at all
    # similar_private: miss, but similar name found for private file
    # similar_public: miss, but similar name found for public file
    # private: found by checksum but not only privately shared
    # public: found by checksum and publically shared
    in_index = gridfile.md5 in gdrive_index_by_md5
    exist_status = "miss"
    if not gdrive_index_by_md5:
        exist_status = "unknown"
    elif gridfile.md5 in gdrive_index_by_md5:
        exist_status = "public" if gdrive_index_by_md5[gridfile.md5][1] else "private"
        gdrive_urls = get_google_urls(id=gdrive_index_by_md5[gridfile.md5][0])
    elif file_metadata["name"] in gdrive_index_by_name:
        exist_status = "similar_public" if gdrive_index_by_name[file_metadata["name"]][1] else "similar_private"
        gdrive_urls = get_google_urls(id=gdrive_index_by_name[file_metadata["name"]][0])

    results_metadata["exists"] = exist_status

    if exist_status == "miss" or exist_status == "unknown":
        job.context["sum_size"] += gridfile.length
        if commit:
            media = MediaIoBaseUpload(gridfile, mimetype=gridfile.content_type, chunksize=1024 * 1024, resumable=True)
            file = api.create(body=file_metadata, media_body=media, fields="id").execute()
            gdrive_urls = get_google_urls(id=file["id"])
            # Change the file asset to now link to Google Drive instead
            data.source_file_url = gdrive_urls["direct"]
            data.file_data.delete()
            data.file_data = None
            data.save()
    else:
        # Update Fileasset to point to the Gdrive file we found
        if exist_status == "public":
            if commit:
                data.source_file_url = gdrive_urls["direct"]
                data.file_data.delete()
                data.file_data = None
                data.save()
        elif exist_status == "private":
            job.warn("File found but is not public, need to make it public before we can link it")
        elif exist_status.startswith("similar"):
            job.warn("Found a similar file by name but need to check manually")

    return {**file_metadata, **gdrive_urls, **results_metadata}
