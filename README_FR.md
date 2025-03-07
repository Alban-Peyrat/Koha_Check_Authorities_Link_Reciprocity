# Vérifier la réciprocité des liens d'autorités dans Koha

Ce script récupèrent des autorités de Koha et analyse si chaque autorité liée à une autorité renvoie vers elle.

_Créé pour le thésaurus ArchiRès, créé pour Koha 23.11_

## Requirements

* Utilise [`Alban-Peyrat/Koha_API_interface/Koha_REST_API_Client.py`](https://github.com/Alban-Peyrat/Koha_API_interface/blob/main/Koha_REST_API_Client.py) (version du 2025-01-31)
* Utilise `pymarc` 5.2.0

## Variables d'environnement

* `KOHA_URL` : nom de domaine de l'intranet Koha
* `KOHA_CLIENT_ID` : ID Client Koha d'un compte avec la permission `catalogue`
* `KOHA_CLIENT_SECRET` : Secret Client Koha d'un compte avec la permission `catalogue`
* `AUTH_NB_LIMIT` : nombre maximal d'autorités à récupérer
* `AUTH_NB_RES_PER_PAGE` : nombre d'autorités récupérées par page
* `AUTH_TYPE` : code du type d'autorité
* `AUTH_NAME_FIELD_TAG` : zone UNIMARC contenant le nom pour ce type d'autorité (pour les _datafields_, récupère le premier sous-champ au code `a`)
* `ERRORS_FILE` : chemin complet pour le fichier de sortie d'erreurs
* `MISSING_LINKS_FILE` : chemin complet pour le fichier de sortie des liens absents

## Fichiers de sortie

Tous les fichiers de sortie sont des `.csv` utilisant `;` comme délimiteur.

### Contenu du fichiers d'erreurs

Ce fichier contient toutes les erreurs qui ne sont pas des liens absents.
4 colonnes :

* `error_type` :
  * `REQUESTS_GET_ERROR` : une erreur a eu lieu pendant la récupération des autorités
  * `NO_RECORD` : une erreur a eu lieu lors de la lecture de la notice MARC
  * `NO_AUTH_ID_IN_RECORD` : aucune `001` n'a été trouvée dans la notice d'autorité
  * `NO_AUTH_WITH_THIS_ID` : une autorité possède un lien vers cet ID d'autorité, mais cette autorité n'a pas été récupérée de Koha
* `id` : dans le cas d'une erreur `NO_AUTH_WITH_THIS_ID`, l'ID de l'autorité qui n'a pas été trouvée
* `index` : sauf pour `NO_AUTH_WITH_THIS_ID`, le numéro de page avec l'index de la notice qui a déclenché l'erreur (si pertinent)
* `message` : détails de l'erreur (en anglais)

### Contenu du fichier de sortie des liens absents

Ce fichier contient uniquement les erreurs de liens absents.
6 colonnes :

* `original_id` : ID de l'autorité faisant un lien vers une autre qui ne renvoie pas vers elle en retour
* `original_name` : nom de l'autorité faisant un lien vers une autre qui ne renvoie pas vers elle en retour
* `link_type` :
  * `RELATED` : termes associés
  * `PARENT` : l'autorité `original` est un terme générique de l'autorité `linked`
  * `CHILD` : l'autorité `original` est un terme spécifique de l'autorité `linked`
* `linked_id` : ID de l'autorité qui ne renvoie pas en retour
* `linked_name` : nom de l'autorité qui ne renvoie pas en retour
* `message` : une version écrite des 5 première colonnes (en anglais) :
  * `Linked name (ID linked) is not linking Original name (ID original) as a parent term.` : _Autorité liée_ (son ID) ne renvoie pas vers _Autorité originale_ (son ID) en tant que terme générique
  * `Linked name (ID linked) is not linking Original name (ID original) as a child term.` : _Autorité liée_ (son ID) ne renvoie pas vers _Autorité originale_ (son ID) en tant que terme spécifique
  * `Linked name (ID linked) is not linking Original name (ID original) as a related term.` : _Autorité liée_ (son ID) ne renvoie pas vers _Autorité originale_ (son ID) en tant que terme associé
