変更履歴
===============================================================================

Ver 2
-------------------------------------------------------------------------------

ver 2.11.1 [2019-05-18]
* ポーズから、次のラベルまでの時間を引けるオプションを追加
* 44100以外のフレームレートのwavにも対応
* wxPython 4 を使用するように変更
* インストーラの設定が変わった（新しい環境では前の設定だとエラーになった）


ver 2.10.7 [2017-01-01]
* あけましておめでとうございます
* 設定ファイルの読み込み時エラーのメッセージをわかりやすくした


ver 2.10.6 [2015-02-17]
* 音声ファイルが壊れて出力されるバグを修正


ver 2.10.5 [2015-02-09]
* 2.10.4の修正でポーズ情報保存ボタンがおかしくなったバグを修正


ver 2.10.4 [2015-01-09]
* ツールバーに「ポーズ音声作成」を追加。メッセージのみ表示。左下の「ポーズ音声作成」ボタンを押したあとは、次回起動時から表示されない。
* 「ヘルプ」メニューに「マニュアル」を追加。インターネット上のマニュアルをブラウザで開く


ver 2.10.3 [2014-05-17]
* やっぱり ffmpeg.exe も同梱した。


ver 2.10.2 [2014-02-03]
* aboutダイアログを作成し、バージョン番号を確認できるようにした
* 節分の豆がなかったのでピンクの小粒コーラックを庭に投げた


ver 2.10.1 [2014-02-01]
* ffmpegがないのにwav以外を読込もうとした場合にメッセージを表示するようにした


ver 2.10.0 [2014-01-22]
* 全体的に見た目や機能などが微妙に変わった
* 音声の保存先を選べるようにした
* 音声フォルダに置いていたポーズ情報をデータフォルダへ移動した
* ffmpeg.exeを外した。
  wav以外を読み書きするにはユーザがffmpegを用意しないといけない


ver 2.04 [2013-12-16]
* [重大なバグの修正] 波形の表示が後半に行くほどずれることがあるバグを修正。
　ずっとmp3変換側のしわざだと思い込んでましたが、ただの自分側のミスでした。


ver 2.03 [2013-12-05]
* ffmpegの引数間違いを修正(-rを-arへ)。間違ってても動くみたいやけど、一応修正


ver 2.02 [2013-12-01]
* 音声の削除機能をわかりやすくした
* ffmpegを使うときにコンソールがでないようにした


ver 2.01 [2013-11-30]
* Windows Vista以降でインストーラからインストールしたinspauseが実行できない
* エラーを修正。（私の環境ではUACを切ってたので気づきませんでした）
* wav以外の形式の読み書き方法を変えた(ffmpegを使うようにした)
* 無音レベルと無音認識時間を設定できるようにした


ver 2.00 [2013-04-08]
＜重要な変更箇所＞
* 自動ずれ補正機能を追加
* 読み込めるファイル形式を増やした
* mp3の読み込み速度を上げた
* mp3の書き込み機能を追加
* 拡大・縮小しても波形の見え方が変わらないように修正
* 再生や現在位置の精度をあげた
* 最初から使えるポーズ情報をいくつか追加
* 共有しやすいようにzipを作成する機能を追加
* ユーザインタフェース


＜削除した機能＞
* ポーズ音声ファイルからポーズ情報をつくる機能
* 固定ポーズ


＜その他の変更箇所＞
* ポーズの長さによって色をかえる（光の波長と色の関係と同じようにした）
* リピート再生
* 次回起動時でも拡大率が同じになるようにした
* 矢印キーでの移動方法を変更
* その他細かいこと


Ver 1
-------------------------------------------------------------------------------

ver 1.17 [2013-02-10]
* インストーラ作成
* inspause.exeが入ったフォルダにいっぱいファイルがあるのをやめた
* ショートカットを作成してもすぐ実行できるようにした。
　（前は「作業フォルダ」の変更が必要だった）


ver 1.16 [2013-02-08]
* 左下のラベルをクリックして位置を移動しても再生すると位置が移動されていない
　バグを修正


ver 1.15 [2012-11-04]
* ver1.13～14のみのバグ（ポーズ情報を新規につくったときに変更が保存されない）を修正


ver 1.14 [2012-10-28]
* ver1.11～13のみのバグ（ポーズモード再生のポーズ時間が半分になる）を修正
* 設定でポーズ時間の長さを変更したら、ラベル一覧画面での実効時間も変更
　するように修正


ver 1.13 [2012-10-17]
* 波形の下にカット候補を追加


ver 1.12 [2012-10-16]
* Windowsのみmp3の読み込みに対応


ver 1.11 [2012-10-15]
* CDからの音の取り込み方によって音の位置が微妙にずれるので、
  「ラベルをずらす」機能を追加
* UIを変更
* 新たなラベル形式「固定ポーズ」を追加


ver 1.10 [2012-09-30]
* windowsで再生できなかった環境でも、再生できる可能性を増やした。
  でも、実際は増えてなかった。


ver 1.09 [2012-09-24]
* settings.iniでカスタマイズができるようにした
* ポーズ音声からポーズファイルをつくる処理を改善した
* 「境界を再生」ボタンを「もしカット再生」に変更
  （もしカットした場合にどんな感じでポーズが入るか確認するため）


ver 1.08 [2012-09-19]
* 手作業でつくったポーズ音声からポーズファイルをつくる機能を追加


ver 1.07 [2012-09-17]
* Momentum Design Labのアイコンを使うように変更
* ウィンドウサイズや前回開いていたファイルを記憶するよう修正
* 範囲再生を廃止
* いきなり音で始まっていたり、音がある状態で終わるwavのポーズを検索できない
  バグを修正
* Ubuntuで波形をスクロールできなかったバグを修正
* 多重起動禁止（Windowsのみ）するよう修正
* スプリッターの動きを改善
* ドラッグスクロール時のマウスキャプチャバグ修正


ver 1.06 [2012-09-15]
* 『境界を再生』（選択範囲の最後当たりを短いポーズ入りで再生）を追加
* ドラッグでスクロールするように修正


ver 1.05 [2012-09-14]
* 入力できる数字の桁を変更
* 『無音の最低長さ』が短くても機能するように修正
* 範囲移動のつまみが有効なときに線を表示するよう修正
* 『もとに戻す』ショートカットキー追加
* Shiftキーを押しながら範囲を移動すると、隣り合った範囲と重ならないように修正
* Ctrlキーを押しながら範囲を移動すると、隣り合った近い範囲と同時移動するよう修正


ver 1.04 [2012-09-12]
* フォルダをドラッグしたとき、１番上のファイルの波形を表示
* アイコンの変更（誰かかっこいいアイコンつくってよ）
* ショートカットキーをいくつか追加


ver 1.03 [2012-09-11]
* Ubuntuでも無音レベルを操作できるようにバグ修正


ver 1.02 [2012-09-11]
* wavファイルもドラッグ可能に修正
* iconエラーを無視するよう修正


ver 1.01 [2012-09-11]
* ラベルファイルがなくてもポーズ音声を作れるように修正


ver 1.00 [2012-09-05]
* 公開

