# kobitonote.py - Kobitoで編集したアイテムをEvernoteに同期保存

## これは何？

Kobitoで編集したアイテムをEvernoteにも保存するpythonスクリプト

## 何が嬉しいの？

Evernoteではmarkdownでのテキスト作成ができないけれどKobitoとなら！

KobitoでレンダリングされたHTMLをそのままEvernoteに保存します。
Kobitoで更新したアイテムについては、該当するEvernoteノートを更新します。
Kobito側のタグもEvernoteに反映します。
アイテムをQiitaで公開すると、公開URLがEvernoteにも反映されます。

## メモ

Kobitoで最近更新されたアイテムをEvernoteに保存します。
保存先ノートブックは`Kobito`です。無ければ作られます。
「最近」判定は、スクリプトを実行したディレクトリに作られるファイル`last_kobito`に保存されるタイムスタンプで行います。

Evernoteとのやり取りはAppleScriptです。

更新監視は行なっていませんので、各自cron等で定期実行してください。

## 既知の問題点

* コードが崩れる →直した

## 注意事項

保証なしです。
Kobito/Evernote上のコンテンツを失うようなコードではないはずですが、どうか自己責任で。

Kobitoの仕様が変わったら突然動かなくなるかもしれません。

## 作者

`@naoya_t`
