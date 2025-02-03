# -*- coding: utf-8 -*- 

# Coded for Koha 23.11

# external imports
import os
import dotenv
import json
import csv
from typing import Dict, List
from enum import Enum
import pymarc

# Internal imports
from Koha_REST_API_Client import KohaRESTAPIClient, Content_Type, Status as Koha_Api_Status, Errors as Koha_Api_Errors, validate_int

# Load paramaters
dotenv.load_dotenv()

AUTH_TYPE=os.getenv("AUTH_TYPE")
AUTH_NB_LIMIT = validate_int(os.getenv("AUTH_NB_LIMIT"), 3000)
AUTH_NB_RES_PER_PAGE = validate_int(os.getenv("AUTH_NB_RES_PER_PAGE"), 50)
AUTH_NAME_FIELD_TAG = validate_int(os.getenv("AUTH_NAME_FIELD_TAG"), 200)

# ----------------- Enum definition -----------------
class Error_Types(Enum):
    REQUESTS_GET_ERROR = 0
    NO_RECORD = 10
    NO_AUTH_ID_IN_RECORD = 11
    NO_AUTH_WITH_THIS_ID = 20

class Link_Type(Enum):
    RELATED = 0
    PARENT = 1
    CHILD = 2

# ----------------- Classes definition -----------------
class Error_File(object):
    def __init__(self, file_path:str) -> None:
        self.file = open(file_path, "w", newline="", encoding='utf-8')
        self.headers = ["error_type", "id", "index", "message"]
        self.writer = csv.DictWriter(self.file, extrasaction="ignore", fieldnames=self.headers, delimiter=";")
        self.writer.writeheader()

    def write(self, error_type:Error_Types, page:int=None, index:int=None, id:int=None, msg:str=None):
        self.writer.writerow({
            "error_type":error_type.name,
            "id":str(id),
            "index":f"Page {page}, n°{index}",
            "message":str(msg)
            })

    def close(self):
        self.file.close()

class Authority(object):
    def __init__(self, record:pymarc.record.Record):
        self.id:int = validate_int(record.get("001").data)
        self.name:str = None
        self.define_name(record)
        self.parent:int = None
        self.children:List[int] = []
        self.related:List[int] = []
        self.define_relations(record)

    def define_name(self, record:pymarc.record.Record):
        """Defines the name of the authority ($a of env var AUTH_NAME_FIELD_TAG)"""
        if record.get(str(AUTH_NAME_FIELD_TAG)):
            if record.get(str(AUTH_NAME_FIELD_TAG)).control_field:
                self.name = record.get(str(AUTH_NAME_FIELD_TAG)).data
            else:
                self.name = record.get(str(AUTH_NAME_FIELD_TAG)).get("a")
        # If no data, force a default value
        if not self.name:
            self.name = "[NAME NOT FOUND]"
    
    def define_relations(self, record:pymarc.record.Record):
        """Gets all relationships IDs"""
        for field in record.get_fields("550"):
            # Get the auth ID
            auth_id = validate_int(field.get("9"))
            # get relationship
            rel = field.get("5")
            if not rel:
                self.related.append(auth_id)
            elif rel == "g":
                self.parent = auth_id
            elif rel == "h":
                self.children.append(auth_id)

class Authority_Index(object):
    def __init__(self):
        self.index:Dict[int, str] = {}
    
    def add_auth_list_to_index(self, raw_marc:str, page:int):
        """Adds the authorities contained in the raw marc to the index"""
        reader = pymarc.MARCReader(raw_marc, to_unicode=True, force_utf8=True)
        # Loop through records
        for record_index, record in enumerate(reader):
            # If record is invalid
            if record is None:
                ERRORS_FILE.write(Error_Types.NO_RECORD, page=page, index=record_index, msg="Record is invalid")
                continue # Fatal error, skipp

            # Gets the auth ID
            if not record.get("001"):
                ERRORS_FILE.write(Error_Types.NO_AUTH_ID_IN_RECORD, page=page, index=record_index, msg="Authority had no 001")
                continue
            
            # Adds the authority to the index
            auth = Authority(record)
            self.index[auth.id] = auth

class Missing_Link_File(object):
    def __init__(self, file_path:str) -> None:
        self.file = open(file_path, "w", newline="", encoding='utf-8')
        self.headers = ["original_id", "original_name", "link_type", "linked_id", "linked_name", "message"]
        self.writer = csv.DictWriter(self.file, extrasaction="ignore", fieldnames=self.headers, delimiter=";")
        self.writer.writeheader()

    def write(self, original_auth:Authority, link_type:Link_Type, linked_auth:Authority):
        self.writer.writerow({
            "original_id":original_auth.id,
            "original_name":original_auth.name,
            "link_type":link_type.name,
            "linked_id":linked_auth.id,
            "linked_name":linked_auth.name,
            "message":self.__output_message(original_auth, link_type, linked_auth)
            })

    def close(self):
        self.file.close()

    def __output_message(self, original_auth:Authority, link_type:Link_Type, linked_auth:Authority) -> str:
        action = ""
        if link_type == Link_Type.RELATED:
            action = "as a related term."
        elif link_type == Link_Type.PARENT:
            action = "as a child term."
        elif link_type == Link_Type.CHILD:
            action = "as a parent term."
        return f"{linked_auth.name} (ID {linked_auth.id}) is not linking {original_auth.name} (ID {original_auth.id}) {action}"

# ----------------- Functions definition -----------------
def get_auth_by_id(id:int) -> Authority|None:
    """Returns the authority for this int"""
    if id in AUTH_INDEX.index:
        return AUTH_INDEX.index[id]
    return None

# ----------------- Preparing Main -----------------
KOHA = KohaRESTAPIClient(os.getenv("KOHA_URL"), os.getenv("KOHA_CLIENT_ID"), os.getenv("KOHA_CLIENT_SECRET"))
if KOHA.status != Koha_Api_Status.SUCCESS:
    print(r"/!\ Failed to connect to Koha /!\ ")
    exit()
AUTH_INDEX = Authority_Index()
ERRORS_FILE = Error_File(os.path.abspath(os.getenv("ERRORS_FILE")))
MISSING_LINKS_FILE = Missing_Link_File(os.path.abspath(os.getenv("MISSING_LINKS_FILE")))


# ----------------- Main -----------------
# Retrieve all authorities
for starting_nb in range(0, AUTH_NB_LIMIT, AUTH_NB_RES_PER_PAGE):
    page = int(starting_nb/AUTH_NB_RES_PER_PAGE)+1
    raw_authority_list = KOHA.list_auth(format=Content_Type.RAW_MARC, page=page, nb_res=AUTH_NB_RES_PER_PAGE, auth_type=AUTH_TYPE)
    if type(raw_authority_list) == Koha_Api_Errors:
        ERRORS_FILE.write(Error_Types.REQUESTS_GET_ERROR, page=page)
        print("error")
        continue
    # Pymarc is not reading records because of the new lines
    # So decode the string, remove them, then reencode the string
    # Make sure to only remove \n at the end of record, otherwise record length won't match
    AUTH_INDEX.add_auth_list_to_index(raw_authority_list.decode().replace("\x1e\x1d\n", "\x1e\x1d").encode(), page)

# Iterate through all authorities to check reciprocity in links
for auth_id in AUTH_INDEX.index:
    auth_inst = get_auth_by_id(auth_id)
    # Check if parent links back
    if auth_inst.parent:
        parent_inst = get_auth_by_id(auth_inst.parent)
        if not parent_inst:
            ERRORS_FILE.write(Error_Types.NO_AUTH_WITH_THIS_ID, id=auth_inst.parent, msg=f"{auth_inst.id} links {auth_inst.parent} as its parent, but no authority was found with this ID")
        else:
            # The parent auth was found, check if the original ID is in children
            if not auth_inst.id in parent_inst.children:
                MISSING_LINKS_FILE.write(auth_inst, Link_Type.PARENT, parent_inst)
    # Check if children link back as parent
    for child_id in auth_inst.children:
        child_inst = get_auth_by_id(child_id)
        if not child_inst:
            ERRORS_FILE.write(Error_Types.NO_AUTH_WITH_THIS_ID, id=child_id, msg=f"{auth_inst.id} links {child_id} as its child, but no authority was found with this ID")
        else:
            # The child auth was found, check if the original ID is the parent
            if auth_inst.id != child_inst.parent:
                MISSING_LINKS_FILE.write(auth_inst, Link_Type.CHILD, child_inst)
    # Check if related link back as related
    for related_id in auth_inst.related:
        related_inst = get_auth_by_id(related_id)
        if not related_inst:
            ERRORS_FILE.write(Error_Types.NO_AUTH_WITH_THIS_ID, id=related_id, msg=f"{auth_inst.id} links {related_id} as its relative, but no authority was found with this ID")
        else:
            # The related auth was found, check if the original ID is the parent
            if not auth_inst.id in related_inst.related:
                MISSING_LINKS_FILE.write(auth_inst, Link_Type.RELATED, related_inst)

ERRORS_FILE.close()
MISSING_LINKS_FILE.close()    
    
