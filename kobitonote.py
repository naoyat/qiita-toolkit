#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
## kobitonote - KobitoのアイテムをEvernoteにも保存する
##
## (c)2012 by @naoya_t
##
import os
import re
import sqlite3
import subprocess
import sys
import time

## 保存先ノートブック
NOTEBOOK_FOR_KOBITO = 'Kobito'

## Kobito.db の所在PATH
DB_PATH = os.environ['HOME'] + '/Library/Kobito/Kobito.db'

## Kobito.db 内部時刻のオフセット
TIME_OFFSET = 978307200.0 # time.mktime(time.strptime("Mon Jan 1 09:00:00 2001"))

## 最後に処理したタイムスタンプ
LAST_KOBITO = './last_kobito'

## 秒 → ISO-8601フォーマット
def iso_8601_jst(t):
    return time.strftime('%Y-%m-%dT%H:%M:%S+09:00', time.localtime(t))

## AppleScript生成
def make_script(title, body, created_at, updated_at, tags, url=None):
    def osa_escape(string):
        return string.replace('\\', '\\\\').replace('"', '\\"').replace('\n', ' ')
    def my_datetime(t):
        return time.strftime('my datetime(%Y,%m,%d,%H,%M,%S)', time.localtime(t))
    def make_tag_list(tags):
        return '{' + ','.join(['"'+osa_escape(tag)+'"' for tag in tags]) + '}'

    return """
on datetime(year, mon, day, hour, min, sec)
  set d to current date
  set d's year to year
  set d's month to mon
  set d's day to day
  set d's hours to hour
  set d's minutes to min
  set d's seconds to sec
  return d
end datetime

tell application "Evernote"
  set notebookStr to "%s"
  set titleStr to "%s"
  set htmlStr to "%s"
  set createdAt to %s
  set updatedAt to %s
  set tagNameList to %s
  set urlStr to %s

  set tagList to {}
  repeat with aTagName in tagNameList
    if exists tag aTagName then
      set aTag to tag aTagName
    else
      set aTag to make new tag with properties {name:aTagName}
    end if
    set end of tagList to aTag
  end repeat

  set destNote to null
  repeat with aNote in (find notes "notebook:" & notebookStr & " intitle:\\"" & titleStr & "\\"")
    if aNote's creation date = createdAt then
      set destNote to aNote
    end if
  end repeat

  if destNote = null then
    set destNote to (create note with html htmlStr title titleStr notebook notebookStr created createdAt tags tagList)
  else
    set destNote's title to titleStr
    set destNote's HTML content to htmlStr
    set destNote's tags to tagList
  end if
  set destNote's modification date to updatedAt
  if not urlStr is equal to "" then
    set destNote's source URL to urlStr
  end if
end tell
""" % (NOTEBOOK_FOR_KOBITO,
       osa_escape(title),
       osa_escape(body),
       my_datetime(created_at),
       my_datetime(updated_at),
       make_tag_list(tags),
       '"'+url+'"' if url else '""')

## AppleScriptを実行
def run_osascript(script, *args):
    p = subprocess.Popen(['arch', '-i386', 'osascript', '-e', script] +
                         [unicode(arg).encode('utf8') for arg in args],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    err = p.wait()
    if err:
        raise RuntimeError(err, p.stderr.read()[:-1].decode('utf8'))
    return p.stdout.read()[:-1].decode('utf8')

## Kobitoアイテムクラス
class KobitoItem :
    def __init__(self, row, items_tags={}):
        z_pk, z_ent, z_opt, zprivate, zcreated_at, zposted_at, zupdated_at, \
            zbody, zlinked_file, zraw_body, ztitle, zurl, zuuid = row
        self._pk         = z_pk
        self._ent        = z_ent
        self._opt        = z_opt
        self.private     = zprivate
        self.created_at  = TIME_OFFSET + zcreated_at if zcreated_at else None
        self.posted_at   = TIME_OFFSET + zposted_at if zposted_at else None
        self.updated_at  = TIME_OFFSET + zupdated_at if zupdated_at else None
        self.body        = zbody.encode('utf-8')
        self.linked_file = zlinked_file
        self.raw_body    = zraw_body.encode('utf-8')
        self.title       = ztitle.encode('utf-8')
        self.url         = zurl.encode('utf-8') if zurl else None
        self.uuid        = zuuid  #
        self.tags        = items_tags[z_pk] if items_tags.has_key(z_pk) else []

    def save_in_evernote(self):
        title = self.title
        body = self.body \
            .replace("<!DOCTYPE HTML>\n", "") \
            .replace('rel="stylesheet" href="',
                     'rel="stylesheet" href="/Applications/Kobito.app/Contents/Resources/')
        body = re.sub(r'[ \t]*<script[^\n]*</script>\n', r'', body)
        body = re.sub(r'  <body>\n<h1>[^\n]*</h1>', r'<body>', body)

        script = make_script(title, body, self.created_at, self.updated_at, self.tags, self.url)
        # print script

        sys.stderr.write(iso_8601_jst(self.updated_at))
        sys.stderr.write("「" + self.title + "」")
        sys.stderr.write(" ".join(self.tags) + "\n")
        run_osascript(script)

## Kobito側のタグを取得
def get_kobito_tags(conn):
    c = conn.cursor()
    c.execute(u"select * from ZTAG")
    tags = {}
    for _pk, _ent, _opt, name in c:
        tags[_pk] = name.encode('utf-8')
    return tags

## Kobitoのアイテムに付加されたタグを取得
## {アイテムID1: [タグID1, タグID2, ...], アイテムID2: [...], ...}
## タグ取得済みなら、タグIDを文字列に置換
## {アイテムID1: [タグ1, タグ2, ...], アイテムID2: [...], ...}
def get_kobito_items_tags(conn, tags=None):
    items_tags = {}
    c = conn.cursor()
    c.execute(u"select * from Z_1TAGS")
    for _1items, _2tags in c:
        if tags:
            _2tags = tags[_2tags]
        if items_tags.has_key(_1items):
            items_tags[_1items].append(_2tags)
        else:
            items_tags[_1items] = [_2tags]
    return items_tags

## Kobitoのアイテムを取得
def get_kobito_items(conn, last, items_tags=None):
    c = conn.cursor()
    c.execute(u"select * from ZITEM where ZUPDATED_AT > %s" % str(last))
    return [KobitoItem(row, items_tags) for row in c]

## 最近（＝最後にこのスクリプトを走らせた時以降）の更新アイテムをevernoteに保存
## Evernote の重複排除は created_at と title のみで照合
def save_recent_to_evernote():
    def last_kobito_time():
        if os.path.exists(LAST_KOBITO):
            with open(LAST_KOBITO, 'r') as fp:
                return float(fp.readline().rstrip())
        else:
            return 0
    def save_current_kobito_time():
        current_kobito_time = time.time() - TIME_OFFSET
        with open(LAST_KOBITO, 'w') as fp:
            fp.write(str(current_kobito_time) + '\n')

    conn = sqlite3.connect(DB_PATH)

    tags = get_kobito_tags(conn)
    items_tags = get_kobito_items_tags(conn, tags)
    for item in get_kobito_items(conn, last_kobito_time(), items_tags):
        item.save_in_evernote()

    conn.close()
    save_current_kobito_time()


if __name__ == '__main__':
    save_recent_to_evernote()
