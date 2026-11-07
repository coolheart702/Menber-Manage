@echo off
rem メンバー管理プログラム起動バッチ
rem
rem "%~dp0" は「このバッチファイルが存在するフォルダの絶対パス」に自動で置き換わる特殊変数。
rem これによりバッチファイルをどの場所から実行しても同じフォルダ内にある member_print_preview_zoom.py を確実に指定できる。

python "%~dp0member_print_preview_zoom.py"
rem pause