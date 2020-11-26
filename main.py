import argparse
import gzip
import json
import re
import shutil
from pathlib import Path
from urllib import parse

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
pw.SqliteDatabase(dbPath).bind([cls.HttpCaptureRecord])

for ipFolder in workDirPath.iterdir():
    if not re.search(r'^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}$', ipFolder.name):
        continue
    for file in ipFolder.iterdir():
        fileAttr = re.search(r'^http_(...)_(.+?)\.hcy$', file.name)
        if not fileAttr:
            oldFile = file
            hostPath = hostsPath / ipFolder.name
            hostPath.mkdir(exist_ok=True)
            file = hostPath / file.name
            if remove:
                oldFile.replace(file)
            else:
                shutil.copy(oldFile, file)
            continue
        fileTypeStr = fileAttr.group(1)
        sessionId = fileAttr.group(2)
        record = cls.HttpCaptureRecord.get_or_none(cls.HttpCaptureRecord.SESSION_ID == sessionId)
        if not record:
            print(f'No such SESSION_ID in database: {file.resolve()}')
            continue
        oldFile = file
        hostPath = hostsPath / record.HOST
        hostPath.mkdir(exist_ok=True)
        file = hostPath / f'http_{sessionId}_{fileTypeStr}.hcy'
        if remove:
            oldFile.replace(file)
            oldFile = file
        if fileTypeStr == 'req':
            fileContent1 = bytearray(oldFile.read_bytes())
            urlSplitResult = parse.urlsplit(record.URL)
            queries = '\r\n'.join([f'{key} = {value}' for key, value in parse.parse_qsl(urlSplitResult.query)])
            queries = f'{queries}\r\n' if queries else ''
            fileContent1[:fileContent1.index(b'\r\n')] = f'{record.METHOD} {record.REQ_PROTOCOL}\r\n{record.URL}\r\n' \
                                                         f'{queries}'.encode()
            file.write_bytes(fileContent1)
        else:
            isGzip = False
            contentType = ''
            if not record.RES_HEADERS:
                continue
            for header1 in json.loads(record.RES_HEADERS):
                if header1['name'].lower() == 'content-encoding':
                    if header1['value'] == 'gzip':
                        isGzip = True
                elif header1['name'].lower() == 'content-type':
                    contentType = header1['value']
            fileContent2 = oldFile.read_bytes()
            responseHeaders = fileContent2[:record.RES_BODY_OFFSET]
            responseBody = fileContent2[record.RES_BODY_OFFSET:]
            rewrite = False
            if isGzip:
                rewrite = True
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
                responseBody = gzip.decompress(responseRawBody)
            if contentType.startswith('application/json'):
                rewrite = True
                try:
                    responseBody = json.dumps(json.loads(responseBody), ensure_ascii=False, indent=4).encode()
                except json.decoder.JSONDecodeError:
                    pass
            if not remove or rewrite:
                with file.open('wb+') as io4:
                    io4.write(responseHeaders)
                    io4.write(responseBody)
    else:
        if remove:
            try:
                ipFolder.rmdir()
            except OSError:
                pass
