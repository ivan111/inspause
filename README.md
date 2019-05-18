InsPause
===============================================================================

> このソフトをテレンス・リーさんに捧げます。

![Screenshot](https://github.com/ivan111/inspause/raw/master/inspause.png)

目次
-------------------------------------------------------------------------------
* [機能](#desc)
* [動作環境](#requirements)
* [インストール](#install)
* [アンインストール](#uninstall)
* [実行方法](#run)
* [使い方](#how_to_use)
* [ショートカットキー](#shortcuts)
* [ライセンス](#license)
* [作者](#author)
* [THANKS](#thanks)
* [変更履歴](#changes)
* [開発者向け情報](#fordev)

<a name="desc"></a> 機能
-------------------------------------------------------------------------------

InsPauseは、repeating用の音声を作成するためのsoftwareです。  
CDからripしたsoundやDownloadしたsoundをloadし、節やsentenceの終了位置を自動的に見つけpause（無音）をinsertします。


<a name="requirements"></a> 動作環境
-------------------------------------------------------------------------------

Windows, Mac, Linux  


<a name="install"></a> インストール
-------------------------------------------------------------------------------

### インストーラ版
ダウンロードしたファイルを実行するだけです。

### Windowsのzip版
ダウンロードしたファイルを解凍してできたフォルダを好きな場所に置いてください。

### ソースファイル版
zip版と同じです。


<a name="uninstall"></a> アンインストール
-------------------------------------------------------------------------------

### ソフト自体の削除
インストーラを使ってインストールした方は、スタートメニューから「Uninstall inspause」を選択してアンインストールするか、Windowsのコントロールパネルからアンインストールします。

インストーラを使ってない場合は、インストール時に配置したフォルダを削除してください。設定ファイルも自動的に作成されているのでそれも削除します。

設定フォルダの場所は以下のとおりです。
* Windows: マイドキュメントのinspauseフォルダ
* それ以外: ホームディレクトリの.inspauseフォルダ


### データの削除
マイドキュメントのinspauseフォルダにデータが残っているので手動で削除してください。Windows以外の方はホームディレクトリの中の「.inspause」ディレクトリがデータフォルダになります。


<a name="run"></a> 実行方法
-------------------------------------------------------------------------------

### インストーラ版
デスクトップのinspauseファイルをダブルクリックするか、スタートメニューからinspauseを選択して実行します。


### Windowsのzip版
inspause.exeをダブルクリックして実行します。

起動するときに、「このアプリケーションの構成が正しくないため、アプリケーションを開始できませんでした」というエラーメッセージが出た場合は、「Microsoft Visual C++ 2008 再頒布可能パッケージ (x86)」もインストールしてください。


### ソースファイル版
以下をインストールしておきます。
* Python 2系
* wxPython
* pyaudio
* （オプション）ffmpeg

コンソールで、inspause.pyがあるディレクトリへ移動後、以下を実行します。

    $ python inspause.py



<a name="shortcuts"></a> ショートカットキー
-------------------------------------------------------------------------------

### 再生
* スペース         : 再生／一時停止
* Shift + スペース : ポーズ再生
* b                : もしカット再生（分割できる場所でのみ）
* s                : 選択末尾再生

### 現在位置の変更
* Home           : 先頭へ移動
* 右矢印         : 0.002秒進む（停止中のみ）
* Ctrl + 右矢印  : 0.02秒進む（停止中のみ）
* Shift + 右矢印 : 1秒進む（停止中のみ）
* 左矢印         : 0.002秒戻る（停止中のみ）
* Ctrl + 左矢印  : 0.02秒戻る（停止中のみ）
* Shift + 左矢印 : 1秒戻る（停止中のみ）

### 編集
それぞれのコマンドが使用できるような位置にいるときのみ有効
* c        : 分割
* i        : ポーズを挿入
* l        : 左と結合
* r        : 右と結合
* Del      : 選択ポーズを削除
* Ctrl + s : ポーズ情報を保存
* Ctrl + z : 元に戻す
* Ctrl + y : やり直し（元に戻すのを元に戻す）

### 表示
* ＋       : 表示拡大
* ー       : 表示縮小
* End      : 末尾を表示
* PageUp   : 一画面左を表示
* PageDown : 一画面右を表示
* 上矢印   : 波形の下の方を拡大表示
* 下矢印   : 全体が見えるように波形を縮小


<a name="license"></a> ライセンス
-------------------------------------------------------------------------------

Icon : Attribution-Share Alike license  
others : GPL2（詳しくはLICENSE.txtを御覧ください）


<a name="author"></a> 作者
-------------------------------------------------------------------------------

NAME : Ivan Ivanovich Ivanov (vanya)  
WEB : http://vanya.jp.net/  
MAIL : i@vanya.jp.net  


<a name="thanks"></a> THANKS
-------------------------------------------------------------------------------

* Icon
by Momentum Design Lab  
http://momentumdesignlab.com/  
License : Attribution-Share Alike license  

ツールバーのアイコンとプログラムアイコンに使用しています。一部修正しています。


<a name="changes"></a> 変更履歴
-------------------------------------------------------------------------------

[CHANGES.md](https://github.com/ivan111/inspause/blob/master/CHANGES.md)を参照してください。


<a name="fordev"></a> 開発者向け情報
-------------------------------------------------------------------------------

[DEV_NOTE.md](https://github.com/ivan111/inspause/blob/master/DEV_NOTE.md)を参照してください。
