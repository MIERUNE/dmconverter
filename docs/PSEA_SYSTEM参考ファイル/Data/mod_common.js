/// Copyright (C)2008 Mapcom Inc. All Rights Reserved. 
var ClassModCommon = {
 Name	: "Module 汎用"
,Last	: "2008.10.31"
,Ver	: "0.8.0.0010"
};
/* ---------------------------------------------------------------------------------------------*
 * class
 *  var obj = new com();
 * .............................................................................................
 * method
 *  obj.Object(ID)                          : オブジェクトの取得
 *  obj.ObjectI(ID, type)                   : オブジェクトの取得 for Iframe
 *
 *  obj.nZ()                                : Z-Index 用ライブラリ
 *
 *  obj.CheckNum(n)                         : 数値チェック 
 *
 *  obj.ArrayShiftR(array, nx, ny)          : 配列操作：ライトシフト
 *  obj.ArrayShiftL(array, nx, ny)          : 配列操作：レフトシフト
 *  obj.ArrayShiftU(array, nx, ny)          : 配列操作：アップシフト
 *  obj.ArrayShiftD(array, nx, ny)          : 配列操作：ダウンシフト
 *
 *  getCookie(key, val)                     : Cookie 設定
 *  setCookie(key, val, life)               : Cookie 取得
 * 
 *  obj.xmlEncode(src)                      : XML エンコード
 *  obj.urlResolve(srcURL, srcKey, srcVal)  : URL 引数解析
 * ---------------------------------------------------------------------------------------------*/
function com(){

  /* -------------------------------------------------------------------------------------------*
   * Private Valuable
   * -------------------------------------------------------------------------------------------*/
  this.temp     = null; // テンポラリ
  
  /* -------------------------------------------------------------------------------------------*
   * Public  Valuable
   * -------------------------------------------------------------------------------------------*/
  this.obj      = null; // Document Object
  this.objIWin  = null; // Iframe Window   Object
  this.objIDoc  = null; // Iframe Document Object
 
  /* -------------------------------------------------------------------------------------------*
   * Class Public：オブジェクト
   * -------------------------------------------------------------------------------------------*/
  /* オブジェクトの取得
   * arg
   *  string ID : オブジェクト名
   * return
   *  Object    : 取得オブジェクト or null
   */
  com.prototype.Object = function com_Object(ID){
    this.obj = null;
 	  if((ID != null && ID != '')){
	    if(     document.all           ){ this.obj = document.all(ID);            }	// IE
	    else if(document.getElementById){ this.obj = document.getElementById(ID); } // NN
	    else if(document.layers        ){ this.obj = ID.target;                   } // NN4.7
	  }
	  return this.obj;
  };
  
  /* オブジェクトの取得 for Iframe
   * arg
   *  string ID   : オブジェクト名
   *  string type : 取得タイプ
   *                window          : Window
   *                document / else : Document
   * return
   *  Object      : 取得オブジェクト or null
   */
  com.prototype.ObjectI = function com_ObjectI(ID, type){
    var obj = null;
 	  if((ID != null && ID != '')){
 	    // IE
	    if(document.all){
	      if(type == "window"){
	        obj = this.objIWin = document.getElementById(ID).contentWindow;
	      }
	      else{
	        obj = this.objIDoc = document.getElementById(ID).contentWindow.document;
	      }
	    }
	    // NN. NN4.7
	    else if(document.getElementById || document.layers){
	      if(type == "window"){
	        obj = this.objIWin = document.getElementById(ID).contentWindow;
	      }
	      else{
	        obj = this.objIDoc = document.getElementById(ID).contentDocument;	      
	      }
	    }
	  }
	  return obj;
  };
  
  /* オブジェクト変数チェック
   * arg
   *  object obj : チェックオブジェクト
   * return
   *  bool
   */
  com.prototype.ObjectDVal = function(obj){
    var ret = true;
    if(obj == undefined || obj == null){
      ret = false;
    }
    return ret;
  };
  
  /* オブジェクト変数チェック→オブジェクト取得
   * - obj.value
   * arg
   *  object obj : チェックオブジェクト / オブジェクトＩＤ
   * return
   *  bool
   */
  com.prototype.ObjectOVal_Value = function(obj){
    var ret = null;
    // object
    if(this.ObjectDVal(obj)){
      ret = obj;
      // string id
      if(!this.ObjectDVal(obj.value)){
        ret = this.Object(obj);
      }
    }
    return ret;
  };
  
  /* オブジェクト取得＆イベントキー処理
   * - obj.value
   * arg
   *  object obj：Input Object / Input Object ID
   * return
   *  bool      ：処理ステータス
   */
  com.prototype.ObjectEvtKey = function(obj){
    var ret  = false;
    try{
      var eKey = event.keyCode;

      obj = this.ObjectOVal_Value(obj);
      if(obj != null){
        if(eKey != 17 && eKey != 16 && eKey != 28 && eKey != 29  && eKey != 33 && eKey != 34 && eKey != 35 && eKey != 36 && eKey != 45 && eKey != 37 && eKey != 38 && eKey != 39 && eKey != 40){
          if(eKey != 8 && eKey != 46){
            this.temp = obj;
          }
          ret = true;
        }
      }
    }
    catch(e){
      ret = false;
    }
    return ret;
  };
  
  /* -------------------------------------------------------------------------------------------*
   * Class Public：Div
   * -------------------------------------------------------------------------------------------*/
  /* Div 操作：表示/非表示
   * arg
   *  string id : Div ID
   * [bool   sw]: 表示/非表示
   */
  com.prototype.DivDisplay = function(id, sw){
    var o = this.Object(id);
    if(o != null){
      var disp = "block";
      if(this.ObjectDVal(sw)){
        if(!sw){
          disp = "none";
        }
      }
      else{
        if(o.style.display == "block"){
          disp = "none";
        }
      }
      o.style.display = disp;  
    }
  };
  
  /* -------------------------------------------------------------------------------------------*
   * Class Public：Style
   * -------------------------------------------------------------------------------------------*/
  /* Z-Index 用ライブラリ
   * return
   *  string Z : Z 座標(８桁）
   */
  com.prototype.nZ = function(){
    var d      = new Date();
    var d_base = new Date(d.getFullYear(), d.getMonth() - 1, 1);
    var Z = Math.floor((d.getTime() - d_base.getTime()) * 0.01); 
    return Z;
  };
  
  /* Z-Index 用ライブラリ：最前面
   * arg
   *  int      : マイナス値
   * return
   *  string Z : Z 座標座標(８桁）
   */
  com.prototype.mZ = function(n){
    var Z = 99999999 - n;
    return Z;
  };
    
  
  /* -------------------------------------------------------------------------------------------*
   * Class Public：数値
   * -------------------------------------------------------------------------------------------*/
  /* 値を算出（単位削除）
   * arg
   *  string val : 値
   * return
   *  float      : 数値 or null
   */
  com.prototype.TrimUnit = function(val){
    var ret = null;
    if(this.CheckNum(val)){
      ret = val;
    }
    else{
      ret = val;
      if(ret != null && ret != ""){
        ret = ret.replace("cm", "");
        ret = ret.replace("in", "");
        ret = ret.replace("pt", "");
        ret = ret.replace("pc", "");
        ret = ret.replace("px", "");
        ret = ret.replace("em", "");
        ret = ret.replace("ex", "");   
      }
      try{
        ret = eval(ret);
      }
      catch(e){
        ret = null;
      }
    }
    return ret;    
  };
  
  /* 数値チェック & 変換
   * arg
   *  string n    : チェック文字列
   * [int    def] : 値
   * return
   *  object      : null, int
   */
  com.prototype.nInt = function(n, def){
    return this.nConvert(n, "int", def);
  };
  
  /* 数値チェック & 変換
   * arg
   *  string n    : チェック文字列
   * [int    def] : 値
   * return
   *  object      : null, float
   */
  com.prototype.nFloat = function(n, def){
    return this.nConvert(n, "float", def);
  };

  /* 数値チェック & 変換
   * arg
   *  string n    : チェック文字列
   *  string type : 変換[int, float]
   * [int    def ]: 値
   * return
   *  object      : null, int, float
   */
  com.prototype.nConvert = function(n, type, def){
    var ret = null;

    // 数値変換
    if(     type == "int"  ){ ret = parseInt(n, 10); }
    else if(type == "float"){ ret = parseFloat(n);   }

    if(isNaN(ret)){
      ret = null;
    }
    
    // 初期値をセット
    if(ret == undefined || ret == Number.NaN || ret == null){
      if(def != undefined){
        ret = def;
      }
    }
    return ret;
  };
   
  /* 数値変換：DMS を D へ変換
   * arg
   *  int   d : 度
   *  int   m : 分
   *  float s : 秒
   */
  com.prototype.nPointDMS2D = function GetDataLatLng(d, m, s){
    var pos = 0;
    var dv = 0;
    var mv = 0;
    var sv = 0;
    try{
      dv = parseInt(d, 10);
      mv = parseInt(m, 10);
      sv = parseFloat(s, 10);

      if(mv > 0){
        mv = (mv / 60);
      }
      if(sv != 0){
        sv = (sv / 3600);
      }
    }
    catch(e){

    }
    pos = dv + mv + sv;
//alert(pos);
    return pos;
  };

  /* 数値チェック
   * arg
   *  string n : チェック文字列
   * return
   *  bool
   */
  com.prototype.CheckNum = function(n){
    var ret = true;
    n += "";
    if(this.ObjectDVal(n)){
      if(n.match(/[^0-9]+/)){
        ret = false;
      }
    }
    return ret;
  };

  /* -------------------------------------------------------------------------------------------*
   * Class Public：数値：補間
   * -------------------------------------------------------------------------------------------*/
  /* 数値チェック：数値以外を省く
   * arg
   *  string n    : チェック文字列
   * return
   *  string      : 数値文字列
   */
  com.prototype.cInt = function(n){
    var ret = "";
    for(var i = 0; i < n.length; i++){
      var ci = n.charAt(i);
      if(this.nInt(ci) != null){
        ret += ci;
      }
    }
    return ret;
  };
  
  /* 数値チェック：数値以外を省く
   * arg
   *  string n    : チェック文字列
   * return
   *  string      : 数値文字列
   */
  com.prototype.cFloat = function(n){
    var ret = "";
    var f   = false;
    var imax = n.length;
    for(var i = 0; i < imax; i++){
      var ci = n.charAt(i);
      if(!f && i != 0 && ci == "."){
        f = true;
        ret += ci;
      }
      else if(this.nInt(ci) != null){
        ret += ci;
      }
    }
    return ret;
  };
  
  /* 数値チェック：数値以外を省き、３桁区切りに「,」を挿入
   * arg
   *  string n    : チェック文字列
   * return
   *  string      : 数値文字列
   */
  com.prototype.cMoney = function(n){    
    var ret = "";
    
    n = this.cInt(n);
    var imax = n.length;
    if(imax >= 4){
      imax--;
      var xi = 0;
      for(i = imax; i >= 0; i--, xi++){
        if(xi == 3){
          ret = "," + ret;
          xi = 0;
        }
        var c = n.charAt(i);
        ret = c + ret;
      }
    }
    else
      ret = n;
    
    return ret;
  };
  
  /* 日付チェック：数値以外を省く
   * arg
   *  string n    : チェック文字列
   * return
   *  string      : 数値文字列
   */
  com.prototype.cDate = function(n){
    var ret   = "";
    var nci   = 0;
    var yyyy  = "";
    var mm    = "";
    var dd    = "";
    for(var i = 0; i < n.length; i++){
      var ci = n.charAt(i);
      
      // 年
      if(i == 0 || i == 1 || i == 2 || i == 3){
        yyyy += ci;
      }
      // 月：一桁目
      if(i == 5){
        nci = parseInt(ci, 10);
        if(!(nci == 0 || nci == 1)){
          continue;
        }
        mm = ci;
      }
      // 月：二桁目
      else if(i == 6){
        nci = parseInt(ci, 10);
        if(mm == "0"){
          if(!(nci >= 1 && nci <= 9)){
            continue;
          }
        }
        if(mm == "1"){
          if(!(nci >= 0 && nci <= 2)){
            continue;
          }
        }
        mm += ci;
      }
      // 日：一桁目
      else if(i == 8){
        nci  = parseInt(ci, 10);
        yyyy = parseInt(yyyy, 10);
        mm   = parseInt(mm  , 10);
        if(!(nci == 0)){
          if(mm == 2){
            if(!(nci <= 2)){
              continue;
            }
          }
          else{
            if(!(nci <= 3)){
              continue;
            }
          }
        }
        dd = parseInt(ci, 10);
      }
      // 日：二桁目
      else if(i == 9){
        nci     = parseInt(ci, 10);
        var dd2 = new Date(yyyy, mm, 0).getDate();
            dd2 = parseInt((dd2 + "").substring(1, 2), 10);

        if(mm == 2){
          if(dd == 2){
            if(!(nci <= dd2)){
              continue;
            }
          }
        }
        else{
          if(dd == 3){
            if(!(nci <= dd2)){
              continue;
            }
          }
        }
      }

      // セパレート    
      if(i == 4 || i == 7){
        ret += "/";
        if(ci != "/"){
          ret += ci; 
        }
      }
      else{
        if(this.nInt(ci) != null){
          ret += ci;
          var eKey = event.keyCode;
          
          // セパレート：シーケンシャル入力時
          if(!(eKey == 8 || eKey == 46)){
            if((i == 3 || i == 6) && i + 1 == n.length){
              ret += "/"; 
            }
          }
        }
      }
    }
    return ret;
  };

  /* -------------------------------------------------------------------------------------------*
   * Class Public：数値：フォーム
   * -------------------------------------------------------------------------------------------*/
  /* 数値チェック：フォーム：数値以外を省く
   * arg
   *  object obj：Input Object / Input Object ID
   *  bool   sw ：true == Backspace, Delete を無視する
   * return
   *  bool      ：処理ステータス
   */
  com.prototype.fInt = function(obj, sw){
    var ret = this.ObjectEvtKey(obj);
    if(ret){
      var f = true;
      if(this.ObjectDVal(sw) && sw){
        var eKey = event.keyCode;
        if(eKey == 8 || eKey == 46){
          f = false;
        }
      }
      if(f && this.temp != null){
        this.temp.value = this.cInt(this.temp.value);
      }
    }
    return ret;
  };
  
  /* 数値チェック：フォーム：数値以外を省く
   * arg
   *  object obj：Input Object / Input Object ID
   *  bool   sw ：true == Backspace, Delete を無視する
   * return
   *  bool      ：処理ステータス
   */
  com.prototype.fFloat = function(obj, sw){
    var ret = this.ObjectEvtKey(obj);
    if(ret){
      var f = true;
      if(this.ObjectDVal(sw) && sw){
        var eKey = event.keyCode;
        if(eKey == 8 || eKey == 46){
          f = false;
        }
      }
      if(f && this.temp != null){
        this.temp.value = this.cFloat(this.temp.value);
      }
    }
    return ret;
  };
  
  /* 数値チェック：フォーム：金額
   * arg
   *  object obj：Input Object / Input Object ID
   *  bool   sw ：true == Backspace, Delete を無視する
   * return
   *  bool      ：処理ステータス
   */
  com.prototype.fMoney = function(obj, sw){
    var ret = this.ObjectEvtKey(obj);
    if(ret){
      var f = true;
      if(this.ObjectDVal(sw) && sw){
        var eKey = event.keyCode;
        if(eKey == 8 || eKey == 46){
          f = false;
        }
      }
      if(f && this.temp != null){
        this.temp.value = this.cMoney(this.temp.value);
      }
    }
    return ret;
  };  

  /* 日付チェック：フォーム：数値以外を省く
   * arg
   *  object obj：Input Object / Input Object ID
   * return
   *  bool      ：処理ステータス
   */
  com.prototype.fDate = function(obj){
    var ret = this.ObjectEvtKey(obj);
    if(ret){
      var eKey = event.keyCode;
      if(eKey != 8 && eKey != 46){
        ret = true;
        this.temp.value = this.cDate(this.temp.value);
      }
    }    
    return ret;
  };
  
  /* 日付チェック：フォーム：数値以外を省く（補間）
   * arg
   *  object obj：Input Object / Input Object ID
   * return
   *  bool      ：処理ステータス
   */
  com.prototype.fDateComplement = function(obj){
    obj = this.ObjectOVal_Value(obj);
    if(obj != null){
      var val = obj.value;
      if(val != ""){
        var n = val.length;
        if(n != 10){
          
          // 月が一桁でセットされた場合：
          var vAry = val.split("/");
          if(vAry.length == 3){
            if(val.length >= 8){
              if(vAry[0].length == 4){
                if(vAry[1].length == 1){
                  val = vAry[0] + "/" + "0" + vAry[1] + "/" + vAry[2]; 
                  n = val.length;
                }                  
              }
            }
          }
        
          // 順次チェック
          if(     n == 1){ val += "000/01/01";  }
          else if(n == 2){ val += "00/01/01";   }
          else if(n == 3){ val += "0/01/01";    }
          else if(n == 4){ val += "/01/01";     }
          else if(n == 5){ val += "01/01";      }
          else if(n == 6){
                           var nv = val.substr(5, 1);
                           if(nv == "0"){ val += "1";                         }
                           else         { val  = val.substr(0, 5) + "0" + nv; }
                           val += "/01";        }
          else if(n == 7){ val += "/01";        }
          else if(n == 8){ val += "01";         }
          else if(n == 9){ 
                           var nv = val.substr(8, 1);
                           if(nv == "0"){ val += "1";                         }
                           else         { val  = val.substr(0, 8) + "0" + nv; }
          }
          obj.value = val;
        }
      }
    }
  };
  
  /* -------------------------------------------------------------------------------------------*
   * Class Public：文字列
   * -------------------------------------------------------------------------------------------*/
  /* 文字チェック：半角英数以外を省く
   * arg
   *  string n    : チェック文字列
   * return
   *  string      : 半角英数文字列
   */
  com.prototype.cStringAlphanumeric = function(n){
    var ret = "";
    for(var i = 0; i < n.length; i++){
      var ci = n.charAt(i);
      if(ci.match(/[^0-9A-Za-z]+/) == null){
        ret += ci;
      }
    }
    return ret;
  };

  /* 数値チェック：フォーム：数値以外を省く
   * arg
   *  object obj：Input Object / Input Object ID
   *  bool   sw ：true == Backspace, Delete を無視する
   * return
   *  bool      ：処理ステータス
   */
  com.prototype.fStringAlphanumeric = function(obj, sw){
    var ret = this.ObjectEvtKey(obj);
    if(ret){
      var f = true;
      if(this.ObjectDVal(sw) && sw){
        var eKey = event.keyCode;
        if(eKey == 8 || eKey == 46){
          f = false;
        }
      }
      if(f && this.temp != null){
        this.temp.value = this.cStringAlphanumeric(this.temp.value);
      }
    }
    return ret;
  };

  /* 文字列変数チェック(１文字以上）
   * arg
   *  object obj : チェックオブジェクト
   * return
   *  bool
   */
  com.prototype.StringDVal = function(src){
    var ret = false;
    if(this.ObjectDVal(src) && src != "" && src.length > 1){
      ret = true;
    }
    return ret;
  };

  /* -------------------------------------------------------------------------------------------*
   * Class Public：配列
   * -------------------------------------------------------------------------------------------*/
  /* 配列長チェック
   * arg
   *  object obj : チェックオブジェクト
   *  int    n   : 必要配列数
   * return
   *  bool
   */
  com.prototype.ArrayDVal = function(obj, n){
    var ret = false;
    if(this.ObjectDVal(obj) && obj.length >= n){
      ret = true;
    }
    return ret;
  };

  /* 配列変数チェック
   * arg
   *  string src : 文字列
   *  string dlm : 区切文字
   *  int    n   : 必要配列数
   * return
   *  Array
   */
  com.prototype.ArraySpilt = function(src, dlm, n){
    var ret = null;
    if(this.StringDVal(src)){
      ret = src.split(dlm);
      if(n != undefined){
        if(!(ret.length >= n)){
          ret = null;
        }
      }
    }
    return ret;  
  };
   
  /* 配列操作：ライトシフト
   * arg
   *  array array  : 配列
   *  int   nx     : シフトＸ方向
   *  int   ny     : シフトＹ方向
   */
  com.prototype.ArrayShiftR = function(array, nx, ny){
	  for(var y = 0 ; y < ny; y++) {
		  var	a = array[nx - 1 + y * nx];
		  for(var x = nx - 1 ; x >= 1 ; x--){
			  array[x + y * nx] = array[ x - 1 + y * nx];
			}
		  array[0 + y * nx] = a;
	  }
  };

  /* 配列操作：レフトシフト
   * arg
   *  array array  : 配列
   *  int   nx     : シフトＸ方向
   *  int   ny     : シフトＹ方向
   */
  com.prototype.ArrayShiftL = function(array, nx, ny){
	  for(var y = 0 ; y < ny; y++){
		  var	a = array[0 + y * nx];
		  for(var x = 0 ; x < nx - 1 ; x++){
			  array[x + y * nx] = array[ x + 1 + y * nx];
			}
		  array[nx - 1 + y * nx] = a;
	  }
  };

  /* 配列操作：アップシフト
   * arg
   *  array array  : 配列
   *  int   nx     : シフトＸ方向
   *  int   ny     : シフトＹ方向
   */
  com.prototype.ArrayShiftH = function(array, nx, ny){
	  for(var x = 0 ; x < nx; x++){
		  var	a = array[x + (ny - 1) * nx];
		  for(var y = ny - 1 ; y >= 1 ; y--){
			  array[x + y * nx] = array[ x + (y - 1) * nx];
			}
		  array[x] = a;
	  }
  };
  
  /* 配列操作：ダウンシフト
   * arg
   *  array array  : 配列
   *  int   nx     : シフトＸ方向
   *  int   ny     : シフトＹ方向
   */
  com.prototype.ArrayShiftD = function(array, nx, ny){
	  for(var x = 0 ; x < nx; x++) {
		  var	a = array[x];
		  for(var y = 0 ; y < ny - 1 ; y++){
			  array[x + y * nx] = array[ x + (y + 1) * nx];
			}
		  array[x + (ny - 1) * nx] = a;
	  }
  };
   
  /* -------------------------------------------------------------------------------------------*
   * Class Public：Cookie
   * -------------------------------------------------------------------------------------------*/
  /* Cookie 取得
   * arg
   *  string key : キー
   *  string val : 値(取得がなかった場合のデフォルト)
   * return
   *  string     : 値
   */
  com.prototype.getCookie = function(key, val){
    var ret     = "";
    var	vCookie = document.cookie + ";";
    var	vVal    = vCookie.indexOf(key + "=" , 0);
    // 値取得
    if(vVal != null && vVal > -1){
	    vCookie = vCookie.substring(vVal, vCookie.length);
	    var	nS = vCookie.indexOf("=", 0) + 1;
	    var	nE = vCookie.indexOf(";", nS);
	    ret = unescape(vCookie.substring(nS, nE));
    }
    // デフォルト値
    if(ret == null || ret == ""){
      ret = val;
    }
    return ret;
  };
   
  /* Cookie 設定
   * arg
   *  string key : キー
   *  string val : 値
   *  int life   : 有効期限[日]
   */
  com.prototype.setCookie = function(key, val, life){
    // 有効期限
    if(life == undefined || life == null || life == ""){
      life = 30;
    }
    life = life * 24 * 60 * 60 * 1000;
    // [キー]=[値];[有効期限]
    var	tmNow  = new Date();
    var	tmLife = new Date(tmNow.getTime() + life);
    document.cookie = key + "=" + escape(val) + ";" + "expires=" + tmLife.toGMTString();
  };
   
  /* -------------------------------------------------------------------------------------------*
   * Class Public：XML
   * -------------------------------------------------------------------------------------------*/
  /* XML エンコード
   * arg
   *  string src : XML
   * return
   *  string     : エンコードされた XML
   */
  com.prototype.xmlEncode = function(src){
	  var	ret = "";
	  for(var i = 0; i < src.length ;i++){
		  var	c = src.charAt(i);
		  if(     c == '<' ){ ret += "&lt;";    }
		  else if(c == '>' ){ ret += "&gt;";    }
		  else if(c == '\''){ ret += "&apos;";  }
		  else if(c == '\"'){ ret += "&quot;";  }
		  else if(c == '&' ){ ret += "&amp;";   }
      else         			{ ret += c;         }
	  }
	  return ret;
  };
    
  /* -------------------------------------------------------------------------------------------*
   * Class Public：URL
   * -------------------------------------------------------------------------------------------*/
  /* URL 引数解析
   * arg
   *  string srcURL : 引数付き URL
   *  Array  srcKey : キー配列
   *  Array  srcVal : 値配列
   */
  com.prototype.urlResolve = function(srcURL, srcKey, srcVal){
	  if(srcURL.length > 0){
		  var	url = srcURL.substring(1);
		  var	arg = url.split("&");
		  for(var i = 0 ; i < arg.length ; i++){
			  var	val = arg[i].split("=");
			  if(val.length > 1){
				  n = srcKey.length;
				  srcKey[n]   = val[0];
				  srcVal[n] = val[1];
			  }
		  }
	  }
  };
  
  /* -------------------------------------------------------------------------------------------*
   * Class Public：Image Button
   * -------------------------------------------------------------------------------------------*/
  com.prototype.srcImage = function(id, dir, name, mode, ext){
    var obj = this.Object(id);
    if(obj != null){
      obj.src = dir + name + mode + ext;
    }
  };
};