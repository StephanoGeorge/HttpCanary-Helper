import peewee as pw


class HttpCaptureRecord(pw.Model):
    class Meta:
        table_name = 'HTTP_CAPTURE_RECORD'
        primary_key = False
        only_save_dirty = True

    SESSION_ID = pw.TextField()
    URL = pw.TextField()
    HOST = pw.TextField()
    METHOD = pw.TextField()
    REQ_PROTOCOL = pw.TextField()
    RES_HEADERS = pw.TextField()
    REQ_BODY_OFFSET = pw.IntegerField()
    RES_BODY_OFFSET = pw.IntegerField()
