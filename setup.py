import googleapiclient.discovery
import googleapiclient.http
import google.auth.exceptions
import google.auth.transport.requests
import google.oauth2.credentials
import google.oauth2.service_account
import google_auth_oauthlib.flow
import hashlib
import json
import magic
import os
import shutil
import subprocess
import time
import typing


def configFileDl(configFile: str) -> None:
    fileUrl = 'https://docs.google.com/uc?export=download&id={}'.format(envVars[getFileIdKey(configFile)])
    if os.path.exists(configFile):
        os.remove(configFile)
    subprocess.run(['aria2c', fileUrl, '--quiet=true', '--out=' + configFile])
    timeElapsed = 0
    while timeElapsed <= float(envVars['dlWaitTime']):
        if os.path.exists(configFile):
            print(f"Downloaded '{configFile}' !")
            break
        else:
            time.sleep(0.1)
            timeElapsed += 0.1


def getFileHash(filePath: str) -> str:
    hashSum = hashlib.sha256()
    blockSize = 128 * hashSum.block_size
    fileStream = open(filePath, 'rb')
    fileChunk = fileStream.read(blockSize)
    while fileChunk:
        hashSum.update(fileChunk)
        fileChunk = fileStream.read(blockSize)
    return hashSum.hexdigest()


def getFileIdKey(fileName: str) -> str:
    splitList = fileName.split('.')
    fileIdKeyStr = splitList[0]
    if len(splitList) > 1:
        for i in range(1, len(splitList)):
            fileIdKeyStr += splitList[i].capitalize()
    fileIdKeyStr += keySuffixId
    return fileIdKeyStr


def getFileHashKey(fileName: str) -> str:
    fileHashKeyStr = getFileIdKey(fileName).replace(keySuffixId, keySuffixHash)
    return fileHashKeyStr


def jsonFileLoad(jsonFileName: str) -> typing.Dict:
    return json.loads(open(jsonFileName, 'rt', encoding='utf-8').read())


def jsonFileWrite(jsonFileName: str, jsonDict: dict) -> None:
    open(jsonFileName, 'wt', encoding='utf-8').write(json.dumps(jsonDict, indent=2) + '\n')


def authorizeApi() -> None:
    global configVars, oauthCreds
    if isUserAuth:
        if not oauthCreds or not oauthCreds.valid:
            try:
                if oauthCreds and oauthCreds.expired and oauthCreds.refresh_token:
                    oauthCreds.refresh(google.auth.transport.requests.Request())
                else:
                    raise google.auth.exceptions.RefreshError
            except google.auth.exceptions.RefreshError:
                appFlow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(configVars['googleDriveAuth']['authInfos']['credsJson'], oauthScopes)
                oauthCreds = appFlow.run_console()
            finally:
                configVars['googleDriveAuth']['authInfos']['tokenJson'] = json.loads(oauthCreds.to_json())


def buildService() -> typing.Any:
    return googleapiclient.discovery.build(serviceName='drive', version='v3', credentials=oauthCreds, cache_discovery=False)


def getUpData(fileName: str) -> (typing.Dict, googleapiclient.http.MediaIoBaseUpload):
    filePath = os.path.join(os.getcwd(), fileName)
    fileMimeType = magic.Magic(mime=True).from_file(filePath)
    fileMetadata = {'name': fileName, 'mimeType': fileMimeType}
    mediaBody = googleapiclient.http.MediaIoBaseUpload(fd=open(filePath, 'rb'), mimetype=fileMimeType, resumable=False)
    return fileMetadata, mediaBody


def filePatch(fileName: str) -> str:
    fileId = envVars[getFileIdKey(fileName)]
    fileMetadata, mediaBody = getUpData(fileName)
    fileOp = driveService.files().update(fileId=fileId, body=fileMetadata, media_body=mediaBody).execute()
    print(f"Synced: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]")
    return fileOp['id']


def fileUpload(fileName: str) -> str:
    fileMetadata, mediaBody = getUpData(fileName)
    fileMetadata['parents'] = [envVars['configFolderId']]
    fileOp = driveService.files().create(body=fileMetadata, media_body=mediaBody).execute()
    print(f"Uploaded: [{fileOp['id']}] [{fileName}] [{os.path.getsize(fileName)} bytes]")
    return fileOp['id']


configJsonFile = 'config.json'
configJsonBakFile = configJsonFile + '.bak'
dynamicJsonFile = 'dynamic.json'
fileidJsonFile = 'fileid.json'
credsJsonFile = 'creds.json'
saJsonFile = 'sa.json'
tokenJsonFile = 'token.json'
configFiles: typing.List[str] = \
    [
        configJsonFile,
        configJsonBakFile
    ]
oauthCreds = None
oauthScopes: typing.List[str] = \
    [
        'https://www.googleapis.com/auth/drive'
    ]
driveService: typing.Any
chunkSize: int = 32 * 1024 * 1024
keySuffixId = 'Id'
keySuffixHash = 'Hash'
inputQueries: typing.List[str] = \
    [
        'Do You Want to Use Dynamic Config? ',
        'Do You Want to Update Config? ',
        'Do You Want to Use User Account Auth? '
    ]
inputsFalsy: typing.List[str] = \
    [
        'N',
        'n'
    ]
inputsTruthy: typing.List[str] = \
    [
        'Y',
        'y',
        ''
    ]
isDynamicConfig: bool
isUpdateConfig: bool
isUserAuth: bool
configVars: typing.Dict
configTemplateJsonFile = 'config.template.json'
configTemplateVars: typing.Dict = \
    {
        'botToken': '',
        'botOwnerId': '',
        'telegramApiId': '',
        'telegramApiHash': '',
        'googleDriveAuth': {
            'authType': '',
            'authInfos': {
                'credsJson': {},
                'saJson': {},
                'tokenJson': {}
            }
        },
        'googleDriveUploadFolderIds': {},
        'ariaConf': {
            'allow-overwrite': 'true',
            'follow-torrent': 'false',
            'max-connection-per-server': '8',
            'min-split-size': '8M',
            'split': '8'
        },
        'authorizedChats': {},
        'dlRootDir': 'dl',
        'logLevel': 'INFO',
        'megaAuth': {
            'apiKey': '',
            'emailId': '',
            'passPhrase': ''
        },
        'qbitTorrentConf': {
            'BitTorrent': {
                'Session': {
                    'AsyncIOThreadsCount': '8',
                    'MultiConnectionsPerIp': 'true',
                    'SlowTorrentsDownloadRate': '100',
                    'SlowTorrentsInactivityTimer': '600'
                }
            },
            'LegalNotice': {
                '': {
                    'Accepted': 'true'
                }
            },
            'Preferences': {
                'Advanced': {
                    'AnnounceToAllTrackers': 'true',
                    'AnonymousMode': 'false',
                    'IgnoreLimitsLAN': 'true',
                    'RecheckOnCompletion': 'true',
                    'LtTrackerExchange': 'true'
                },
                'Bittorrent': {
                    'AddTrackers': 'false',
                    'MaxConnecs': '-1',
                    'MaxConnecsPerTorrent': '-1',
                    'MaxUploads': '-1',
                    'MaxUploadsPerTorrent': '-1',
                    'DHT': 'true',
                    'DHTPort': '6881',
                    'PeX': 'true',
                    'LSD': 'true',
                    'sameDHTPortAsBT': 'true'
                },
                'Downloads': {
                    'DiskWriteCacheSize': '32',
                    'PreAllocation': 'true',
                    'UseIncompleteExtension': 'true'
                },
                'General': {
                    'PreventFromSuspendWhenDownloading': 'true'
                },
                'Queueing': {
                    'IgnoreSlowTorrents': 'true',
                    'MaxActiveDownloads': '100',
                    'MaxActiveTorrents': '50',
                    'MaxActiveUploads': '50',
                    'QueueingEnabled': 'false'
                },
                'WebUI': {
                    'Enabled': 'true',
                    'Port': '8400',
                    'LocalHostAuth': 'false'
                }
            }
        },
        'statusUpdateInterval': '5',
        'trackersListUrl': 'https://trackerslist.com/all.txt',
        'ytdlFormat': 'best/bestvideo+bestaudio'
    }
envVars: typing.Dict = \
    {
        'dlWaitTime': '5'
    }

if __name__ == '__main__':
    jsonFileWrite(configTemplateJsonFile, configTemplateVars)
    print(f"Generated '{configTemplateJsonFile}' !")
    isDynamicConfig = (True if input(inputQueries[0]) in inputsTruthy else False)
    isUpdateConfig = (True if input(inputQueries[1]) in inputsTruthy else False)
    isUserAuth = (True if input(inputQueries[2]) in inputsTruthy else False)
    if isDynamicConfig:
        if isUpdateConfig:
            envVars[getFileIdKey(dynamicJsonFile)] = input(f"Enter FileId of '{dynamicJsonFile}': ")
            for jsonFile in [dynamicJsonFile, fileidJsonFile, *configFiles]:
                configFileDl(jsonFile)
                if not os.path.exists(jsonFile):
                    print(f"Download Failed '{jsonFile}' ! Exiting...")
                    exit(1)
                if jsonFile in [dynamicJsonFile, fileidJsonFile]:
                    envVars = {**envVars, **jsonFileLoad(jsonFile)}
                    os.remove(jsonFile)
            print(f"Make Necessary Changes to '{configJsonFile}' in this Directory.")
            time.sleep(1.0)
            if not input('Made Necessary Changes? ') in inputsTruthy:
                exit(1)
        else:
            envVars['configFolderId'] = input('Enter Google Drive Parent Folder ID: ')
    if not os.path.exists(configJsonFile):
        print(f"Place '{configJsonFile}' in the Current Working Directory and Re-run the Setup !")
        exit(0)
    configVars = {**configTemplateVars, **jsonFileLoad(configJsonFile)}
    # TODO: may be add checkConfigVars() function
    for jsonFile in [credsJsonFile, saJsonFile, tokenJsonFile]:
        if os.path.exists(jsonFile):
            authInfoKey = getFileIdKey(jsonFile).replace(keySuffixId, '')
            configVars['googleDriveAuth']['authInfos'][authInfoKey] = jsonFileLoad(jsonFile)
            os.remove(jsonFile)
    if isUserAuth:
        configVars['googleDriveAuth']['authType'] = 'userAuth'
        if not configVars['googleDriveAuth']['authInfos']['credsJson']:
            print(f"Place '{credsJsonFile}' in the Current Working Directory and Re-run the Setup !")
            exit(0)
        if configVars['googleDriveAuth']['authInfos']['tokenJson']:
            oauthCreds = google.oauth2.credentials.Credentials.from_authorized_user_info(configVars['googleDriveAuth']['authInfos']['tokenJson'], oauthScopes)
    else:
        configVars['googleDriveAuth']['authType'] = 'saAuth'
        if not configVars['googleDriveAuth']['authInfos']['saJson']:
            print(f"Place '{saJsonFile}' in the Current Working Directory and Re-run the Setup !")
            exit(0)
        oauthCreds = google.oauth2.service_account.Credentials.from_service_account_info(configVars['googleDriveAuth']['authInfos']['saJson'])
    authorizeApi()
    jsonFileWrite(configJsonFile, configVars)
    if os.path.exists(configJsonBakFile):
        os.remove(configJsonBakFile)
    shutil.copy(os.path.join(os.getcwd(), configJsonFile), os.path.join(os.getcwd(), configJsonBakFile))
    print(f"Copied: '{configJsonFile}' -> '{configJsonBakFile}'")
    if isDynamicConfig:
        driveService = buildService()
        fileidJsonDict: typing.Dict[str, str] = {}
        for configFile in configFiles:
            fileidJsonDict[getFileIdKey(configFile)] = (filePatch(configFile) if isUpdateConfig else fileUpload(configFile))
            fileidJsonDict[getFileHashKey(configFile)] = getFileHash(configFile)
        jsonFileWrite(fileidJsonFile, fileidJsonDict)
        dynamicJsonDict: typing.Dict[str, str] = \
            {
                'configFolderId': envVars['configFolderId'],
                'dlWaitTime': envVars['dlWaitTime'],
                getFileIdKey(fileidJsonFile): (filePatch(fileidJsonFile) if isUpdateConfig else fileUpload(fileidJsonFile))
            }
        jsonFileWrite(dynamicJsonFile, dynamicJsonDict)
        (filePatch(dynamicJsonFile) if isUpdateConfig else fileUpload(dynamicJsonFile))
        if input('Do You Want to Delete the Local Config Files? ') in inputsTruthy:
            for configFile in [*configFiles, dynamicJsonFile, fileidJsonFile]:
                os.remove(configFile)
                print(f"Deleted: '{configFile}' !")
    print('Setup Completed !')
    exit(0)
