# HttpCanary Helper

Organize capture files

组织抓包文件

- store files by host but not ip

  按 host 而非 ip 存放文件

- put session id at the beginning of the file name

   将 session id 置于文件名开头

- decompress gzip response

  解压 gzip 响应

- format JSON response

  格式化 JSON 响应

- change request uri to full url

  将请求的 uri 改为完整 url

- format query parameters

  格式化查询参数

- (optional) delete processed files

  (可选) 删除处理过的文件

# Running

```shell script
python3 main.py -w <work-directory> -d <HttpCanary-main-database-path> [-r]
```
