import argparse
import gzip
import json
import re
import shutil
from pathlib import Path

import peewee as pw

import cls

parser = argparse.ArgumentParser()
parser.add_argument('-w', help='work directory')
parser.add_argument('-d', help='HttpCanary main database path')
parser.add_argument('-r', action='store_true', help='remove old hcy files')
args = parser.parse_args()
workDir = args.w
dbPath = args.d
remove = args.r

workDirPath = Path(workDir)
hostsPath = workDirPath / 'hosts'
hostsPath.mkdir(exist_ok=True)
cls.HttpCaptureRecord._meta.database = pw.SqliteDatabase(dbPath)

for ipFolder in workDirPath.iterdir():
    if not re.search(r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', ipFolder.name):
        continue
    for file in ipFolder.iterdir():
        fileAttr = re.search(r'^http_(...)_(.+?)\.hcy$', file.name)
        if not fileAttr:
            print(f'Not valid http capture: {file.resolve()}')
            continue
        fileTypeStr = fileAttr.group(1)
        sessionId = fileAttr.group(2)
        record = cls.HttpCaptureRecord.get_or_none(cls.HttpCaptureRecord.SESSION_ID == sessionId)
        if not record:
            print(f'No such SESSION_ID in database: {file.resolve()}')
            exit()
        oldFile = file
        hostPath = hostsPath / record.HOST
        hostPath.mkdir(exist_ok=True)
        file = hostPath / f'{sessionId}_{fileTypeStr}.hcy'
        if remove:
            oldFile.replace(file)
            oldFile = file
        if fileTypeStr == 'req':
            fileContent1 = bytearray(oldFile.read_bytes())
            fileContent1[:fileContent1.index(b'\r\n')] = f'{record.URL} {record.METHOD} {record.REQ_PROTOCOL}'.encode()
            file.write_bytes(fileContent1)
        else:
            isGzip = False
            isImage = False
            if not record.RES_HEADERS:
                continue
            for header1 in json.loads(record.RES_HEADERS):
                if header1['name'].lower() == 'content-encoding':
                    if header1['value'] == 'gzip':
                        isGzip = True
                elif header1['name'].lower() == 'content-type':
                    if header1['value'].startswith('image/'):
                        isImage = True
            if isGzip and not isImage:
                fileContent2 = oldFile.read_bytes()
                responseHeaders = fileContent2[:record.RES_BODY_OFFSET]
                responseBody = fileContent2[record.RES_BODY_OFFSET:]
                if responseBody[:2] == b'\x1f\x8b':  # Magic code of gzip
                    responseRawBody = responseBody
                else:
                    responseRawBody = b''
                    while True:
                        index = responseBody.index(b'\r\n')
                        if index == 0:
                            responseBody = responseBody[index + 2:]
                            continue
                        length = int(responseBody[:index].decode(), 16)
                        if length == 0:
                            break
                        responseBody = responseBody[index + 2:]
                        responseRawBody += responseBody[:length]
                        responseBody = responseBody[length:]
                responseData = gzip.decompress(responseRawBody)
                with file.open('wb') as io4:
                    io4.write(responseHeaders)
                    io4.write(responseData)
            else:
                if not remove:
                    shutil.copy(oldFile, file)
    else:
        if remove:
            ipFolder.rmdir()
