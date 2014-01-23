# -*- coding: utf-8 -*-

'''
ダブルバッファリングウィンドウ
'''

from time import sleep

import wx

import wx_utils


BG_COLOUR = 'white'

class BufferedWindow(wx.ScrolledWindow):
    '''
    ダブルバッファリングウィンドウ

    ＜説明＞
    描画内容が複雑な場合、画面がちらついたり、
    描画している過程が見えてしまうことがある。
    それを防ぐために、まずメモリー上にある画面に表示されていないビットマップに
    描画しておく。
    そして、全部描き終わったあとに、ビットマップを画面にコピーする。
    この処理をダブルバッファリングという。

    ＜レイヤ機能＞
    Ubuntuでテストしたときはふつうに動いたけど、
    Windowsだと動作が遅かったのでレイヤ機能を追加した。

    本当は違うけど、レイヤはセル画のようなものと考えてもいい。
    inspauseでは２つのレイヤを持っている。
    １つ目（L1とする）はVolumeWindowがボリューム波形を描くために使う。
    ２つ目（L2とする）はLabelsWindowがラベルを描くために使う。
    L2は、L1の内容をコピーしてから描いている。
    ラベル範囲を変えたり、ラベルを分割したり、波形は変更されずラベルのみ
    変更される場合はL2のみを更新すればいい（UpdateDrawing(2)で可能）。
    これにより波形を描き直す処理が省略できる。

    ＜CallAfter＞
    CallAfterは画面を描画するためのコールバック関数。
    レイヤにより画面の描画を更新したあとの最後の仕上げとしてCallAfterが呼ばれる。
    inspauseでは再生位置を描画するために使われている。
    これにより、再生位置だけが変わる場合はレイヤの更新をしなくて済む。

    ＜使い方＞
    ・BufferedWindowのサブクラスを作り、
    Draw(dc)メソッドをオーバーライドすることで独自の描画ができる。
    引数としてデバイスコンテキストをとる。

    ・再描画が必要な場合は、UpdateDrawingを呼び出す。

    ・BufferedWindow.__init__が呼ばれる前に、
    Drawに必要なデータを初期化しておくこと。

    ＜参考＞
    http://wiki.wxpython.org/DoubleBufferedDrawing
    『wxPython In Action』
    '''

    binder = wx_utils.bind_manager()

    def __init__(self, *args, **kwargs):
        # MS Windowsで、リサイズ時の画面のちらつきを抑えるために、
        # wx.NO_FULL_REPAINT_ON_RESIZEを設定する。
        default = wx.NO_FULL_REPAINT_ON_RESIZE
        kwargs['style'] = kwargs.setdefault('style', default)
        kwargs['style'] |= wx.NO_FULL_REPAINT_ON_RESIZE
        wx.ScrolledWindow.__init__(self, *args, **kwargs)

        self.binder.bindall(self)

        self.SetBackgroundColour(BG_COLOUR)

        self._nlayers = 1
        self._call_after = None

        # 環境によっては起動時に２度バッファが初期化されるが問題はない。
        self.InitBuffer()

    def AddLayer(self):
        self._nlayers += 1
        self.buffers.append(wx.EmptyBitmap(self.w, self.h))

    def SetCallAfter(self, func):
        self._call_after = func

    def InitBuffer(self):
        '''
        バッファの初期化をする。
        バッファのサイズはクライアント領域のサイズと同じ。
        '''

        size = self.GetClientSize()
        self.w = size[0]
        self.h = size[1]

        self.buffers = []
        for i in range(self._nlayers):
            self.buffers.append(wx.EmptyBitmap(*size))

            dc = wx.BufferedDC(None, self.buffers[i])

            self.Draw(dc, i+1)

            del dc

        self.reInitBuffer = False

    def SaveToFile(self, filename, filetype=wx.BITMAP_TYPE_PNG):
        self.buffer.SaveFile(filename, filetype)

    #--------------------------------------------------------------------------
    # 描画

    def Draw(self, dc, nlayer):
        '''
        描画処理
        これをサブクラスで独自の描画にオーバーライドする。
        そのとき、背景を描画してほしい場合には、まず親メソッドを呼ぶ。
        '''

        if nlayer != 0:
            return

        dc.SetBackground(wx.Brush(self.GetBackgroundColour()))
        dc.Clear()

    def UpdateDrawing(self, nlayer=1):
        '''
        描画が必要なときに呼び出す。

        @param nlayer 更新するレイヤを指定する。
                      指定したレイヤ以上のすべてのレイヤが更新される
        '''

        nlayers = range(nlayer, self._nlayers+1)

        #import inspect
        #print 'UpdateDrawing:', nlayers, 'from', inspect.stack()[1][3]

        # ちょっと遅らせるほうがちらつかない
        sleep(0.01)

        for i in nlayers:
            dc = wx.MemoryDC()
            dc.SelectObject(self.buffers[i-1])
            self.Draw(dc, i)

            del dc  # Update() が呼ばれる前に MemoryDC を解放する必要がある

        self.Refresh()
        self.Update()
        if self._call_after:
            self._call_after()

    def GetTopLayerDC(self):
        dc = wx.MemoryDC()
        dc.SelectObject(self.buffers[-1])
        return dc

    def DrawBase(self, dc, nlayer):
        dc.DrawBitmap(self.buffers[nlayer-1], 0, 0)

    #--------------------------------------------------------------------------
    # イベントハンドラ

    @binder(wx.EVT_SIZE)
    def OnSize(self, evt):
        self.reInitBuffer = True

    @binder(wx.EVT_IDLE)
    def OnIdle(self, evt):
        if self.reInitBuffer:
            self.InitBuffer()
            # Falseを指定することで、再描画する際にシステムが背景を消さない。
            # これで画面のちらつきを抑えることができる。
            self.Refresh(False)

    @binder(wx.EVT_PAINT)
    def OnPaint(self, evt):
        '''
        描画イベント。
        一番トップのレイヤを描画する。
        '''

        # dcがスコープ外に外れたときにデストラクタが呼ばれて
        # バッファの内容が画面にコピーされる。
        wx.BufferedPaintDC(self, self.buffers[-1])
