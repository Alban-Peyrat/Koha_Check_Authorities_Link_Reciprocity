# Check authorities link reciprocity in Koha

This script retrieves authorities from Koha and analyzes if every authority linked in an authority links back to it.

_Designed for ArchiRès thesaurus, designed for Koha 23.11_

## Requirements

* Uses [`Alban-Peyrat/Koha_API_interface/Koha_REST_API_Client.py`](https://github.com/Alban-Peyrat/Koha_API_interface/blob/main/Koha_REST_API_Client.py) (2025-01-31 version)
* Uses `pymarc` 5.2.0

## Environment variables

* `KOHA_URL` : Koha intranet domain name
* `KOHA_CLIENT_ID` : Koha Client ID of an account with `catalogue` permission
* `KOHA_CLIENT_SECRET` : Koha Client secret of an account with `catalogue` permission
* `AUTH_NB_LIMIT` : maximum number of authority to retrieve
* `AUTH_NB_RES_PER_PAGE` : number of authorities returned per page
* `AUTH_TYPE` : authority type code
* `AUTH_NAME_FIELD_TAG` : name field tag for this authority type (for datafield, will retrieve the first subfield with code `a`)
* `ERRORS_FILE` : full path to the error output file
* `MISSING_LINKS_FILE` : full path to the missing link output file

## Output files

All output files are `.csv` using `;` as a delimiter.

### Error file content

This file contains all the errors other than missing links.
4 columns :

* `error_type` :
  * `REQUESTS_GET_ERROR` : an error occurred while trying to retrieve authorities
  * `NO_RECORD` : an error occurred when trying to parse a MARC record
  * `NO_AUTH_ID_IN_RECORD` : no `001` was found in the authority record
  * `NO_AUTH_WITH_THIS_ID` : an authority links to this authority ID, yet this authority was not retrieved from Koha
* `id` : in the case of a `NO_AUTH_WITH_THIS_ID` error, the authority ID that was not found
* `index` : except for `NO_AUTH_WITH_THIS_ID`, the page number with the index of the record that triggered the error (if relevant)
* `message` : details of the error

### Missing links file content

This file contains only the missing links errors.
6 columns :

* `original_id` : ID of the authority linking to another one whom does not link back
* `original_name` : name of the authority linking to another one whom does not link back
* `link_type` :
  * `RELATED` : related terms
  * `PARENT` : the `original` authority is a broader concept of the `linked` authority
  * `CHILD` : the `original` authority is a narrower concept of the `linked` authority
* `linked_id` : ID of the authority who is not linking back
* `linked_name` : name of the authority who is not linking back
* `message` : a written version of the 5 first columns
